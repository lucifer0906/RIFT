"""
CampaFi – Certificate Store Contract (Beaker)
===================================================
Stores and manages certificate hashes using **Box Storage** (AVM v8+).
• ``add_certificate``  – stores a hash + metadata JSON in a box
• ``delete_certificate`` – removes a box (creator only)
• ``verify_certificate`` – checks if a box (hash) exists

Migrated from raw PyTeal to Beaker Application class for AlgoKit compatibility.
"""

from beaker import Application, Authorize
from pyteal import (
    App,
    Approve,
    Bytes,
    Global,
    If,
    Int,
    Reject,
    Seq,
    abi,
    Expr,
    Pop,
    Assert,
)


app = Application("CertificateStore")


@app.external
def add_certificate(cert_hash: abi.String, metadata: abi.String) -> Expr:
    """
    Store a certificate hash with associated metadata in a box.

    ``cert_hash`` is used as the box name so look-ups are O(1).
    ``metadata`` is a JSON string stored as the box value.
    """
    return Seq(
        App.box_put(cert_hash.get(), metadata.get()),
        Approve(),
    )


@app.external(authorize=Authorize.only(Global.creator_address()))
def delete_certificate(cert_hash: abi.String) -> Expr:
    """Delete a certificate box – creator / admin only."""
    return Seq(
        Pop(App.box_delete(cert_hash.get())),
        Approve(),
    )


@app.external(read_only=True)
def verify_certificate(cert_hash: abi.String, *, output: abi.Bool) -> Expr:
    """
    Returns ``True`` if a box with the given hash exists, ``False`` otherwise.
    Uses box_length to check existence without loading the entire content.
    """
    # App.box_length returns a MaybeValue (length, exists)
    # We only care if it exists.
    length = App.box_length(cert_hash.get())
    return Seq(
        Assert(length.hasValue()),
        output.set(Int(1))
    )


@app.delete(authorize=Authorize.only(Global.creator_address()))
def delete() -> Expr:
    return Approve()


@app.clear_state
def clear_state() -> Expr:
    return Approve()


# ---------------------------------------------------------------------------
# Standalone compilation helper
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json, pathlib

    spec = app.build()
    out = pathlib.Path(__file__).parent / "artifacts" / "certificate_store"
    out.mkdir(parents=True, exist_ok=True)

    (out / "approval.teal").write_text(spec.approval_program)
    (out / "clear.teal").write_text(spec.clear_program)
    (out / "contract.json").write_text(json.dumps(spec.dictify(), indent=2))
    print(f"✅  Compiled CertificateStore → {out}")
