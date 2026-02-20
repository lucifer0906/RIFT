"""
CampaFi – Simple Bank Contract (Beaker)
============================================
A minimal on-chain escrow / savings contract.
• Any user can **deposit** ALGO (payment grouped with an app call).
• Only the **creator** (admin) can **withdraw** ALGO via inner transactions.

Migrated from raw PyTeal to Beaker Application class for AlgoKit compatibility.
"""

from beaker import Application, Authorize
from beaker.state import GlobalStateValue
from pyteal import (
    Approve,
    Global,
    InnerTxnBuilder,
    Int,
    Reject,
    Seq,
    TxnField,
    TealType,
    TxnType,
    abi,
    Expr,
)


class BankState:
    """Global state schema for the Simple Bank contract."""
    total_deposits = GlobalStateValue(
        stack_type=TealType.uint64,
        default=Int(0),
        descr="Running total of deposits in microAlgos",
    )


app = Application("CampusBank", state=BankState())


@app.external
def deposit(*, output: abi.Uint64) -> Expr:
    """
    Accept an ALGO deposit.

    The caller must group a PaymentTxn (to the app address) immediately
    before this application call.  The contract simply records success;
    the payment itself funds the application account.

    Returns the current total deposits (informational).
    """
    return Seq(
        app.state.total_deposits.set(
            app.state.total_deposits + Global.group_size()
        ),
        output.set(app.state.total_deposits),
    )


@app.external(authorize=Authorize.only(Global.creator_address()))
def withdraw(receiver: abi.Address, amount: abi.Uint64) -> Expr:
    """
    Withdraw ALGO from the contract – creator only.

    Sends *amount* microAlgos to *receiver* via an inner transaction.
    """
    return Seq(
        InnerTxnBuilder.Execute(
            {
                TxnField.type_enum: TxnType.Payment,
                TxnField.receiver: receiver.get(),
                TxnField.amount: amount.get(),
                TxnField.fee: Int(0),  # use fee pooling
            }
        ),
        Approve(),
    )


@app.delete(authorize=Authorize.only(Global.creator_address()))
def delete() -> Expr:
    """Allow only the creator to delete the application."""
    return Approve()


@app.clear_state
def clear_state() -> Expr:
    return Approve()


# ---------------------------------------------------------------------------
# Standalone compilation helper (used by deploy.py / AlgoKit)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json, pathlib

    spec = app.build()
    out = pathlib.Path(__file__).parent / "artifacts" / "campus_bank"
    out.mkdir(parents=True, exist_ok=True)

    (out / "approval.teal").write_text(spec.approval_program)
    (out / "clear.teal").write_text(spec.clear_program)
    (out / "contract.json").write_text(json.dumps(spec.dictify(), indent=2))
    print(f"✅  Compiled CampusBank → {out}")
