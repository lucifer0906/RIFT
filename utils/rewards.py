"""
CampusTrust – Campus Token / Rewards system
=============================================
Tracks the CampusToken ASA and provides helpers to build
unsigned reward transactions for Pera Wallet signing.

🔒 **No server-side private keys.**
"""

import json
import os
import sqlite3

from algorand.connect import get_client, get_suggested_params

# Token metadata
TOKEN_NAME = "CampusToken"
TOKEN_UNIT = "CAMPUS"
STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "system_state.json")


# ──────────────────────────────────────────────────────────────────────────
# DB / state persistence helpers
# ──────────────────────────────────────────────────────────────────────────

def get_db_connection():
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "campus.db")
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)


# ──────────────────────────────────────────────────────────────────────────
# Token helpers
# ──────────────────────────────────────────────────────────────────────────

def ensure_campus_token() -> int | None:
    """
    Return the CampusToken ASA ID from persisted state.

    Token **creation** now happens via the ``/api/prepare_asset_creation``
    endpoint + Pera Wallet signing flow.  This function only reads the
    stored ID.
    """
    state = load_state()
    asset_id = state.get("campus_token_id")
    if asset_id:
        return int(asset_id)
    print(f"[{TOKEN_NAME}] Not configured yet.  Create it from the Wallet page.")
    return None


def set_campus_token(asset_id: int):
    """Persist the CampusToken ASA ID after the admin creates it."""
    state = load_state()
    state["campus_token_id"] = asset_id
    save_state(state)
    print(f"[{TOKEN_NAME}] Saved Asset ID: {asset_id}")


# ──────────────────────────────────────────────────────────────────────────
# Reward distribution – unsigned tx builder
# ──────────────────────────────────────────────────────────────────────────

def build_reward_txn(sender: str, receiver_address: str, amount: int, reason: str = "Reward") -> dict | None:
    """
    Build an unsigned ASA transfer transaction for reward distribution.

    Returns ``{"txn_b64": str}`` or ``None`` if token is not configured.
    """
    import base64
    from algosdk.transaction import AssetTransferTxn, encoding

    asset_id = ensure_campus_token()
    if not asset_id:
        return None

    params = get_suggested_params()
    txn = AssetTransferTxn(
        sender=sender,
        sp=params,
        receiver=receiver_address,
        amt=amount,
        index=asset_id,
        note=reason.encode(),
    )
    return {"txn_b64": base64.b64encode(encoding.msgpack_encode(txn)).decode()}


def distribute_reward(user_id, amount, reason="Reward"):
    """
    Legacy helper – looks up user wallet but can no longer sign server-side.

    Returns a mock confirmation string.  Real reward distribution should
    go through the Pera Wallet signing flow.
    """
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()

    if not user or not user["wallet_address"]:
        print(f"User {user_id} has no wallet. Cannot send reward.")
        return None

    # In production, this would queue a notification for the admin
    # to sign the reward txn via their Pera Wallet.
    print(f"[reward] queued {amount} {TOKEN_UNIT} → {user['wallet_address']} ({reason})")
    return f"QUEUED_{user_id}_{amount}"


# ──────────────────────────────────────────────────────────────────────────
# Wallet generation (still useful for creating *addresses* – but
# mnemonic should ONLY be stored client-side / Pera Wallet)
# ──────────────────────────────────────────────────────────────────────────

def generate_student_wallet() -> tuple[str, str]:
    """Generate a new Algorand account.  Returns ``(address, mnemonic)``."""
    from algosdk import account, mnemonic
    private_key, address = account.generate_account()
    passphrase = mnemonic.from_private_key(private_key)
    return address, passphrase


def build_opt_in_txn(sender: str, asset_id: int) -> dict:
    """Build an unsigned opt-in (0-amount self-transfer) transaction."""
    import base64
    from algosdk.transaction import AssetTransferTxn, encoding

    params = get_suggested_params()
    txn = AssetTransferTxn(
        sender=sender, sp=params, receiver=sender, amt=0, index=asset_id,
    )
    return {"txn_b64": base64.b64encode(encoding.msgpack_encode(txn)).decode()}


def opt_in_asset(user_mnemonic=None, asset_id=None):
    """
    Legacy helper.  Real opt-in now goes through Pera Wallet signing.

    Kept for backward compatibility – returns False (no server signing).
    """
    print("[opt_in_asset] Server-side signing removed.  Use Pera Wallet.")
    return False
