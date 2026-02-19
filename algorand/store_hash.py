"""
CampusTrust – On-chain note storage helpers
=============================================
Builds **unsigned** transactions that the client (Pera Wallet) must sign.
Also provides a server-side submission helper for already-signed txns.
"""

import base64
import random
import string

from algosdk.error import AlgodHTTPError
from algosdk.transaction import PaymentTxn, write_to_file

from .connect import get_client, get_suggested_params


def wait_for_confirmation(client, txid, max_rounds=20):
    """Wait for transaction confirmation on TestNet (fast, usually <10 s)."""
    current_round = client.status()["last-round"]
    for _ in range(max_rounds):
        try:
            pending = client.pending_transaction_info(txid)
            if pending.get("confirmed-round", 0) > 0:
                return pending["confirmed-round"]
        except AlgodHTTPError:
            pass
        current_round += 1
        client.status_after_block(current_round)
    raise TimeoutError("Transaction not confirmed within timeout")


def build_note_txn(sender: str, note: str) -> dict:
    """
    Build an unsigned 0-ALGO payment-to-self carrying *note*.

    Returns ``{"txn_bytes": bytes, "txn_b64": str}`` — the msgpack-encoded
    unsigned transaction ready for client-side signing.
    """
    params = get_suggested_params()
    txn = PaymentTxn(
        sender=sender,
        sp=params,
        receiver=sender,
        amt=0,
        note=note.encode("utf-8")[:1024],
    )
    txn_bytes = txn.dictify()          # algosdk msgpack encoding
    import msgpack
    raw = msgpack.packb(txn_bytes, use_bin_type=True)
    return {
        "txn_bytes": raw,
        "txn_b64": base64.b64encode(raw).decode(),
    }


def submit_signed_txn(signed_b64: str) -> str:
    """
    Submit a **signed** transaction (base64) to the network.

    Returns the confirmed transaction ID.
    """
    client = get_client()
    signed_bytes = base64.b64decode(signed_b64)
    txid = client.send_raw_transaction(signed_bytes)
    wait_for_confirmation(client, txid)
    return txid


# ---------------------------------------------------------------------------
# Legacy helper — keeps old call-sites working with a mock fallback
# ---------------------------------------------------------------------------
def store_on_chain(note: str, sender: str | None = None) -> str:
    """
    If *sender* is provided, returns the unsigned txn as base64 (client must
    sign).  Without a sender, returns a MOCK transaction ID so that features
    that record on-chain activity don't crash when no wallet is connected.
    """
    if sender:
        result = build_note_txn(sender, note)
        return result["txn_b64"]
    # Mock mode – no wallet connected
    mock_txid = "MOCK_" + "".join(
        random.choices(string.ascii_uppercase + string.digits, k=52)
    )
    return mock_txid
