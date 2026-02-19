"""
CampaFi – Blockchain utility functions
============================================
Builds notes / unsigned transactions for Algorand blockchain storage.
Certificate box-storage operations now build unsigned txns that the
client-side Pera Wallet signs.

🔒 **No server-side private keys.**
"""

import base64
import os
import random
import string

from algosdk import transaction, logic
from algosdk.error import AlgodHTTPError
from algosdk.transaction import encoding

from algorand.connect import get_client, get_suggested_params
from algorand.store_hash import store_on_chain, wait_for_confirmation


# ──────────────────────────────────────────────────────────────────────────
# Note builder helpers
# ──────────────────────────────────────────────────────────────────────────

def generate_record_note(record_type: str, **fields) -> str:
    """
    Generate a standardised note for blockchain storage.
    Format: RECORD_TYPE|field1:value1|field2:value2|…
    """
    note_parts = [record_type]
    for key, value in fields.items():
        note_parts.append(f"{key}:{value}")
    return "|".join(note_parts)


# ──────────────────────────────────────────────────────────────────────────
# Record helpers  (return MOCK tx-id when no wallet is connected)
# ──────────────────────────────────────────────────────────────────────────

def _mock_txid() -> str:
    return "MOCK_" + "".join(random.choices(string.ascii_uppercase + string.digits, k=52))


def record_attendance_on_chain(session_id, user_id, status, marked_by, face_hash=None):
    """Build note and store on-chain (mock if no sender)."""
    fields = {"session_id": session_id, "user_id": user_id, "status": status, "marked_by": marked_by}
    if face_hash:
        fields["face_hash"] = face_hash
    note = generate_record_note("ATTENDANCE", **fields)
    return store_on_chain(note)


def record_feedback_on_chain(form_id, user_id, question_id, response_hash):
    note = generate_record_note(
        "FEEDBACK", form_id=form_id, user_id=user_id,
        question_id=question_id, hash=response_hash,
    )
    return store_on_chain(note)


def record_group_task_on_chain(group_id, task_id, user_id):
    note = generate_record_note(
        "TASK", group_id=group_id, task_id=task_id,
        user_id=user_id, status="completed",
    )
    return store_on_chain(note)


def record_group_milestone_on_chain(group_id, milestone_id, proof_hash, completed_timestamp):
    note = generate_record_note(
        "MILESTONE", group_id=group_id, milestone_id=milestone_id,
        proof_hash=proof_hash, completed_at=completed_timestamp,
    )
    return store_on_chain(note)


# ──────────────────────────────────────────────────────────────────────────
# Certificate Box Storage  (deployed App ID)
# ──────────────────────────────────────────────────────────────────────────
CERT_APP_ID = int(os.environ.get("CERT_APP_ID", "755556381"))


def _txn_to_b64(txn) -> str:
    return base64.b64encode(encoding.msgpack_encode(txn)).decode()


def build_store_certificate_txns(sender: str, file_hash_bytes: bytes, metadata_str: str) -> dict:
    """
    Build unsigned grouped txns to store a certificate hash in box storage.

    Returns ``{"txns_b64": [pay_b64, app_b64]}`` for client signing.
    """
    box_name = file_hash_bytes
    box_value = metadata_str.encode("utf-8")
    box_mbr = 2500 + 400 * (len(box_name) + len(box_value))

    params = get_suggested_params()
    app_address = logic.get_application_address(CERT_APP_ID)

    ptxn = transaction.PaymentTxn(sender=sender, sp=params, receiver=app_address, amt=box_mbr)
    atxn = transaction.ApplicationNoOpTxn(
        sender=sender, sp=params, index=CERT_APP_ID,
        app_args=[b"add", box_name, box_value],
        boxes=[(0, box_name)],
    )

    transaction.assign_group_id([ptxn, atxn])

    return {"txns_b64": [_txn_to_b64(ptxn), _txn_to_b64(atxn)]}


def store_certificate_hash(file_hash_bytes, metadata_str):
    """
    Legacy helper – returns a MOCK transaction ID.

    Real certificate storage now goes through the ``/api/prepare_cert_store``
    endpoint → Pera Wallet → ``/api/submit_transaction`` flow.
    """
    mock_txid = _mock_txid()
    print(f"[store_certificate_hash] mock mode → {mock_txid}")
    return mock_txid


def verify_certificate_on_chain(file_hash_bytes) -> dict:
    """Read-only: check if a certificate box exists (no signing needed)."""
    client = get_client()

    if isinstance(file_hash_bytes, str):
        if len(file_hash_bytes) == 64:
            try:
                file_hash_bytes = bytes.fromhex(file_hash_bytes)
            except ValueError:
                pass

    try:
        box_response = client.application_box_by_name(CERT_APP_ID, file_hash_bytes)
        value_bytes = base64.b64decode(box_response["value"])
        metadata = value_bytes.decode("utf-8")
        return {"verified": True, "metadata": metadata}
    except AlgodHTTPError:
        return {"verified": False, "metadata": None}
    except Exception as e:
        print(f"Verification error: {e}")
        return {"verified": False, "error": str(e)}


def build_delete_certificate_txn(sender: str, file_hash_bytes: bytes) -> dict:
    """Build an unsigned ApplicationNoOpTxn to delete a certificate box."""
    params = get_suggested_params()
    atxn = transaction.ApplicationNoOpTxn(
        sender=sender, sp=params, index=CERT_APP_ID,
        app_args=[b"delete", file_hash_bytes],
        boxes=[(0, file_hash_bytes)],
    )
    return {"txn_b64": _txn_to_b64(atxn)}


def delete_certificate_on_chain(file_hash_bytes):
    """Legacy helper – returns MOCK txid.  Real flow uses Pera signing."""
    mock_txid = _mock_txid()
    print(f"[delete_certificate_on_chain] mock mode → {mock_txid}")
    return mock_txid
