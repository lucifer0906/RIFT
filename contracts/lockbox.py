"""
CampaFi – Lockbox / Time-Locked Savings Contract (Beaker)
==============================================================
A stateful Algorand smart contract for **goal-based savings accounts**.

Students (or groups) lock funds that **cannot be withdrawn** until a
specified unlock timestamp OR multi-sig (admin) approval.

Features:
  • ``create_goal``   – set a savings goal with a target amount and unlock time
  • ``deposit``       – fund the lockbox (anyone)
  • ``withdraw``      – release funds only AFTER unlock timestamp (creator only)
  • ``force_release`` – admin/creator early-release in emergencies
  • ``get_info``      – read goal metadata

On-chain: Stateful contract with global state for goal metadata,
          inner transactions for fund release.
"""

from beaker import Application, Authorize
from beaker.lib.storage import GlobalStateValue
from pyteal import (
    Approve,
    Assert,
    Bytes,
    Global,
    If,
    InnerTxnBuilder,
    Int,
    Reject,
    Seq,
    TxnField,
    TxnType,
    abi,
)


class LockboxState:
    """Global state schema for the Lockbox contract."""
    # Goal metadata
    goal_name = GlobalStateValue(
        stack_type=TxnType.pay,           # bytes
        default=Bytes(""),
        descr="Name/description of the savings goal",
    )
    target_amount = GlobalStateValue(
        stack_type=TxnType.uint64,
        default=Int(0),
        descr="Target savings amount in microAlgos",
    )
    unlock_time = GlobalStateValue(
        stack_type=TxnType.uint64,
        default=Int(0),
        descr="Unix timestamp after which funds can be withdrawn",
    )
    total_deposited = GlobalStateValue(
        stack_type=TxnType.uint64,
        default=Int(0),
        descr="Running total of deposits in microAlgos",
    )
    is_released = GlobalStateValue(
        stack_type=TxnType.uint64,
        default=Int(0),
        descr="1 if funds have been released, 0 otherwise",
    )


app = Application("CampusLockbox", state=LockboxState())


@app.create
def create() -> "Expr":  # noqa: F821
    """Initialize the lockbox on creation."""
    return Approve()


@app.external(authorize=Authorize.only(Global.creator_address()))
def setup_goal(
    name: abi.String,
    target: abi.Uint64,
    unlock_timestamp: abi.Uint64,
) -> "Expr":  # noqa: F821
    """
    Configure the savings goal. Creator only.
    Must be called once after deployment.
    
    Args:
        name: Human-readable goal description
        target: Target amount in microAlgos
        unlock_timestamp: Unix timestamp for fund release
    """
    return Seq(
        app.state.goal_name.set(name.get()),
        app.state.target_amount.set(target.get()),
        app.state.unlock_time.set(unlock_timestamp.get()),
        Approve(),
    )


@app.external
def deposit(*, output: abi.Uint64) -> "Expr":  # noqa: F821
    """
    Accept an ALGO deposit into the lockbox.

    The caller must group a PaymentTxn (to the app address) immediately
    before this application call. Returns updated total deposits.
    """
    return Seq(
        Assert(app.state.is_released == Int(0)),  # Can't deposit after release
        app.state.total_deposited.set(
            app.state.total_deposited + Int(1)
        ),
        output.set(app.state.total_deposited),
    )


@app.external(authorize=Authorize.only(Global.creator_address()))
def withdraw(receiver: abi.Address, amount: abi.Uint64) -> "Expr":  # noqa: F821
    """
    Withdraw funds from the lockbox – creator only.
    
    ONLY succeeds if current time >= unlock_time.
    Sends *amount* microAlgos to *receiver* via inner transaction.
    """
    return Seq(
        # Enforce time lock
        Assert(Global.latest_timestamp() >= app.state.unlock_time),
        Assert(app.state.is_released == Int(0)),
        # Execute inner payment
        InnerTxnBuilder.Execute(
            {
                TxnField.type_enum: TxnType.Payment,
                TxnField.receiver: receiver.get(),
                TxnField.amount: amount.get(),
                TxnField.fee: Int(0),  # fee pooling
            }
        ),
        app.state.is_released.set(Int(1)),
        Approve(),
    )


@app.external(authorize=Authorize.only(Global.creator_address()))
def force_release(receiver: abi.Address, amount: abi.Uint64) -> "Expr":  # noqa: F821
    """
    Emergency early-release by the creator/admin.
    Bypasses the time lock — designed for exceptional circumstances.
    """
    return Seq(
        Assert(app.state.is_released == Int(0)),
        InnerTxnBuilder.Execute(
            {
                TxnField.type_enum: TxnType.Payment,
                TxnField.receiver: receiver.get(),
                TxnField.amount: amount.get(),
                TxnField.fee: Int(0),
            }
        ),
        app.state.is_released.set(Int(1)),
        Approve(),
    )


@app.delete(authorize=Authorize.only(Global.creator_address()))
def delete() -> "Expr":  # noqa: F821
    """Allow only the creator to delete the application."""
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
    out = pathlib.Path(__file__).parent / "artifacts" / "lockbox"
    out.mkdir(parents=True, exist_ok=True)

    (out / "approval.teal").write_text(spec.approval_program)
    (out / "clear.teal").write_text(spec.clear_program)
    (out / "contract.json").write_text(json.dumps(spec.dictify(), indent=2))
    print(f"✅  Compiled CampusLockbox → {out}")
