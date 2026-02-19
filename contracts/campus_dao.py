"""
CampusTrust – Simple DAO Contract (Beaker)
============================================
A minimal on-chain treasury / DAO contract.
• The **creator** can send ALGO from the contract to any recipient
  (e.g. to fund approved proposals, reimburse students, etc.).

Migrated from raw PyTeal to Beaker Application class for AlgoKit compatibility.
"""

from beaker import Application, Authorize
from beaker.lib.storage import GlobalStateValue
from pyteal import (
    Approve,
    Global,
    InnerTxnBuilder,
    Int,
    Seq,
    TxnField,
    TxnType,
    abi,
)


class DAOState:
    """Global state schema for the Simple DAO contract."""
    total_disbursements = GlobalStateValue(
        stack_type=TxnType.uint64,
        default=Int(0),
        descr="Running count of disbursement transactions",
    )


app = Application("CampusDAO", state=DAOState())


@app.external(authorize=Authorize.only(Global.creator_address()))
def disburse(receiver: abi.Address, amount: abi.Uint64) -> "Expr":  # noqa: F821
    """
    Send ALGO from the DAO treasury to *receiver*.

    Only the creator (DAO admin) may call this.
    """
    return Seq(
        InnerTxnBuilder.Execute(
            {
                TxnField.type_enum: TxnType.Payment,
                TxnField.receiver: receiver.get(),
                TxnField.amount: amount.get(),
                TxnField.fee: Int(0),
            }
        ),
        app.state.total_disbursements.set(
            app.state.total_disbursements + Int(1)
        ),
        Approve(),
    )


@app.delete(authorize=Authorize.only(Global.creator_address()))
def delete() -> "Expr":  # noqa: F821
    return Approve()


@app.clear_state
def clear_state() -> "Expr":  # noqa: F821
    return Approve()


# ---------------------------------------------------------------------------
# Standalone compilation helper
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json, pathlib

    spec = app.build()
    out = pathlib.Path(__file__).parent / "artifacts" / "campus_dao"
    out.mkdir(parents=True, exist_ok=True)

    (out / "approval.teal").write_text(spec.approval_program)
    (out / "clear.teal").write_text(spec.clear_program)
    (out / "contract.json").write_text(json.dumps(spec.dictify(), indent=2))
    print(f"✅  Compiled CampusDAO → {out}")
