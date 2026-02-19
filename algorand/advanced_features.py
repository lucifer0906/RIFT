"""
CampusTrust – Advanced Algorand Features
==========================================
Builds **unsigned** transactions for the client to sign via Pera Wallet.
Also provides read-only helpers (indexer queries, compile, etc.).

🔒 **No server-side private keys.**
"""

import base64

from algosdk import transaction
from algosdk.logic import get_application_address
from algosdk.transaction import (
    ApplicationCallTxn,
    ApplicationCreateTxn,
    AssetConfigTxn,
    PaymentTxn,
    StateSchema,
    encoding,
)

from .connect import get_client, get_indexer, get_suggested_params
from .store_hash import wait_for_confirmation


# ──────────────────────────────────────────────────────────────────────────
# Read-only helpers
# ──────────────────────────────────────────────────────────────────────────

def get_contract_history(app_id: int) -> dict:
    """Fetch recent history for a smart-contract / bank app via the indexer."""
    try:
        idx = get_indexer()
        app_addr = get_application_address(app_id)
        response = idx.search_transactions_by_address(app_addr, limit=10)
        txns = response.get("transactions", [])

        history = []
        for txn in txns:
            txtype = txn.get("tx-type")
            sender = txn.get("sender")

            if txtype == "pay":
                pay = txn.get("payment-transaction", {})
                amt = pay.get("amount", 0) / 1_000_000
                rcv = pay.get("receiver")

                action = "Unknown"
                if rcv == app_addr:
                    action = "Deposit"
                elif sender == app_addr:
                    action = "Withdrawal"

                history.append({
                    "round": txn.get("confirmed-round"),
                    "tx_id": txn.get("id"),
                    "action": action,
                    "amount": amt,
                    "user": sender if action == "Deposit" else rcv,
                })

        return {"success": True, "history": history}
    except Exception as e:
        return {"success": False, "error": str(e)}


def compile_program(client, source_code: str) -> bytes:
    """Compile TEAL source via the algod compile endpoint."""
    compile_response = client.compile(source_code)
    return base64.b64decode(compile_response["result"])


# ──────────────────────────────────────────────────────────────────────────
# Unsigned transaction builders  (client signs via Pera Wallet)
# ──────────────────────────────────────────────────────────────────────────

def _txn_to_b64(txn) -> str:
    """Encode an unsigned Transaction to base64 msgpack."""
    return base64.b64encode(encoding.msgpack_encode(txn)).decode()


def build_payment_txn(sender: str, receiver: str, amount_algo: float, note: str = "") -> dict:
    """Build an unsigned ALGO payment transaction."""
    params = get_suggested_params()
    amount_microalgo = int(float(amount_algo) * 1_000_000)

    txn = PaymentTxn(
        sender=sender,
        sp=params,
        receiver=receiver,
        amt=amount_microalgo,
        note=note.encode() if note else None,
    )
    return {"txn_b64": _txn_to_b64(txn)}


def build_asa_create_txn(
    sender: str,
    unit_name: str,
    asset_name: str,
    total: int,
    decimals: int,
    url: str | None = None,
) -> dict:
    """Build an unsigned ASA creation transaction."""
    params = get_suggested_params()
    txn = AssetConfigTxn(
        sender=sender,
        sp=params,
        total=int(total),
        decimals=int(decimals),
        default_frozen=False,
        unit_name=unit_name,
        asset_name=asset_name,
        manager=sender,
        reserve=sender,
        freeze=sender,
        clawback=sender,
        url=url,
    )
    return {"txn_b64": _txn_to_b64(txn)}


def build_nft_mint_txn(
    sender: str,
    unit_name: str,
    asset_name: str,
    ipfs_url: str,
) -> dict:
    """Build an unsigned NFT (ASA total=1, decimals=0) creation transaction."""
    params = get_suggested_params()
    txn = AssetConfigTxn(
        sender=sender,
        sp=params,
        total=1,
        decimals=0,
        default_frozen=False,
        unit_name=unit_name,
        asset_name=asset_name,
        manager=sender,
        reserve=sender,
        freeze=sender,
        clawback=sender,
        url=ipfs_url,
    )
    return {"txn_b64": _txn_to_b64(txn)}


def build_deploy_contract_txn(
    sender: str,
    approval_teal: str,
    clear_teal: str,
    global_ints: int = 0,
    global_bytes: int = 1,
    local_ints: int = 0,
    local_bytes: int = 0,
) -> dict:
    """Build an unsigned ApplicationCreateTxn."""
    client = get_client()
    approval_program = compile_program(client, approval_teal)
    clear_program = compile_program(client, clear_teal)

    params = get_suggested_params()
    txn = ApplicationCreateTxn(
        sender=sender,
        sp=params,
        on_complete=transaction.OnComplete.NoOpOC,
        approval_program=approval_program,
        clear_program=clear_program,
        global_schema=StateSchema(num_uints=global_ints, num_bytes=global_bytes),
        local_schema=StateSchema(num_uints=local_ints, num_bytes=local_bytes),
    )
    return {"txn_b64": _txn_to_b64(txn)}


def build_bank_deposit_txns(sender: str, app_id: int, amount_algo: float) -> dict:
    """
    Build a *grouped* pair of unsigned txns for bank deposit:
      [0] PaymentTxn  → app address
      [1] ApplicationCallTxn → "deposit"
    """
    params = get_suggested_params()
    amount_microalgo = int(float(amount_algo) * 1_000_000)
    app_addr = get_application_address(app_id)

    pay_txn = PaymentTxn(sender, params, app_addr, amount_microalgo)
    app_txn = ApplicationCallTxn(
        sender, params, app_id,
        transaction.OnComplete.NoOpOC,
        app_args=["deposit"],
    )

    transaction.assign_group_id([pay_txn, app_txn])

    return {
        "txns_b64": [_txn_to_b64(pay_txn), _txn_to_b64(app_txn)],
    }


def build_bank_withdraw_txn(sender: str, app_id: int, amount_algo: float) -> dict:
    """Build an unsigned withdraw ApplicationCallTxn (creator-only)."""
    params = get_suggested_params()
    params.fee = 2000  # cover inner-txn fee

    amount_microalgo = int(float(amount_algo) * 1_000_000)
    txn = ApplicationCallTxn(
        sender, params, app_id,
        transaction.OnComplete.NoOpOC,
        app_args=["withdraw", amount_microalgo],
    )
    return {"txn_b64": _txn_to_b64(txn)}


# ──────────────────────────────────────────────────────────────────────────
# Submit helper (receives signed bytes from frontend)
# ──────────────────────────────────────────────────────────────────────────

def submit_signed_transaction(signed_b64: str) -> dict:
    """Submit a base64-encoded signed transaction and return its txid."""
    client = get_client()
    try:
        raw = base64.b64decode(signed_b64)
        txid = client.send_raw_transaction(raw)
        wait_for_confirmation(client, txid)
        # Try to extract asset/app ID from pending info
        ptx = client.pending_transaction_info(txid)
        result: dict = {"success": True, "tx_id": txid}
        if "asset-index" in ptx:
            result["asset_id"] = ptx["asset-index"]
        if "application-index" in ptx:
            result["app_id"] = ptx["application-index"]
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


def submit_signed_group(signed_b64_list: list[str]) -> dict:
    """Submit a group of signed transactions."""
    client = get_client()
    try:
        raw_list = [base64.b64decode(s) for s in signed_b64_list]
        txid = client.send_transactions(raw_list)
        wait_for_confirmation(client, txid)
        return {"success": True, "tx_id": txid}
    except Exception as e:
        return {"success": False, "error": str(e)}

