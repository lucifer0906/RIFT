"""
CampaFi – Advanced Algorand Features
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
    return encoding.msgpack_encode(txn)


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
    app_args = [bytes.fromhex("b8843568")]  # selector: deposit()uint64

    app_txn = ApplicationCallTxn(
        sender, params, app_id,
        transaction.OnComplete.NoOpOC,
        app_args=app_args,
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
    
    # Selector: withdraw(address,uint64)void -> 13ff1ce9
    # Args: [selector, receiver_bytes (32), amount_uint64 (8)]
    # Note: receiver argument is the address receiving funds, passed as bytes
    # But in the contract it's an abi.Address argument.
    
    # We will assume the sender wants to withdraw to themselves for simplicity, 
    # or expose a 'receiver' param. The current signature only takes 'sender'.
    # If the UI implies withdrawing TO the sender, we use sender address.
    receiver_bytes = encoding.decode_address(sender)
    amount_bytes = amount_microalgo.to_bytes(8, 'big')
    
    app_args = [
        bytes.fromhex("13ff1ce9"),
        receiver_bytes,
        amount_bytes
    ]

    txn = ApplicationCallTxn(
        sender, params, app_id,
        transaction.OnComplete.NoOpOC,
        app_args=app_args,
    )
    return {"txn_b64": _txn_to_b64(txn)}


# ──────────────────────────────────────────────────────────────────────────
# Submit helper (receives signed bytes from frontend)
# ──────────────────────────────────────────────────────────────────────────

def submit_signed_transaction(signed_b64: str) -> dict:
    """Submit a base64-encoded signed transaction and return its txid."""
    client = get_client()
    try:
        txid = client.send_raw_transaction(signed_b64)
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
        combined = b"".join(base64.b64decode(s) for s in signed_b64_list)
        txid = client.send_raw_transaction(base64.b64encode(combined).decode())
        wait_for_confirmation(client, txid)
        return {"success": True, "tx_id": txid}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ──────────────────────────────────────────────────────────────────────────
# Lockbox / Time-Locked Savings helpers
# ──────────────────────────────────────────────────────────────────────────

def build_lockbox_deploy_txn(
    sender: str,
    goal_name: str,
    target_microalgo: int,
    unlock_timestamp: int,
) -> dict:
    """
    Build an unsigned ApplicationCreateTxn for a Lockbox contract.
    
    Uses a minimal TEAL program that stores goal metadata in global state
    and enforces time-locked withdrawals via inner transactions.
    """
    # Minimal approval TEAL for lockbox
    # Stores: goal_name, target_amount, unlock_time, total_deposited, is_released
    approval_teal = """#pragma version 8
txn ApplicationID
int 0
==
bnz handle_create

txn OnCompletion
int NoOp
==
bnz handle_noop

txn OnCompletion
int DeleteApplication
==
bnz handle_delete

err

handle_create:
int 1
return

handle_noop:
txna ApplicationArgs 0
byte "setup"
==
bnz handle_setup

txna ApplicationArgs 0
byte "deposit"
==
bnz handle_deposit

txna ApplicationArgs 0
byte "withdraw"
==
bnz handle_withdraw

txna ApplicationArgs 0
byte "force_release"
==
bnz handle_force_release

err

handle_setup:
txn Sender
global CreatorAddress
==
assert
byte "goal_name"
txna ApplicationArgs 1
app_global_put
byte "target_amount"
txna ApplicationArgs 2
btoi
app_global_put
byte "unlock_time"
txna ApplicationArgs 3
btoi
app_global_put
byte "total_deposited"
int 0
app_global_put
byte "is_released"
int 0
app_global_put
int 1
return

handle_deposit:
byte "is_released"
app_global_get
int 0
==
assert
byte "total_deposited"
byte "total_deposited"
app_global_get
int 1
+
app_global_put
int 1
return

handle_withdraw:
txn Sender
global CreatorAddress
==
assert
global LatestTimestamp
byte "unlock_time"
app_global_get
>=
assert
byte "is_released"
app_global_get
int 0
==
assert
itxn_begin
int pay
itxn_field TypeEnum
txna ApplicationArgs 1
itxn_field Receiver
txna ApplicationArgs 2
btoi
itxn_field Amount
int 0
itxn_field Fee
itxn_submit
byte "is_released"
int 1
app_global_put
int 1
return

handle_force_release:
txn Sender
global CreatorAddress
==
assert
byte "is_released"
app_global_get
int 0
==
assert
itxn_begin
int pay
itxn_field TypeEnum
txna ApplicationArgs 1
itxn_field Receiver
txna ApplicationArgs 2
btoi
itxn_field Amount
int 0
itxn_field Fee
itxn_submit
byte "is_released"
int 1
app_global_put
int 1
return

handle_delete:
txn Sender
global CreatorAddress
==
return
"""
    
    clear_teal = """#pragma version 8
int 1
return
"""
    
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
        global_schema=StateSchema(num_uints=4, num_bytes=1),
        local_schema=StateSchema(num_uints=0, num_bytes=0),
        note=f"CampaFi Lockbox: {goal_name}".encode(),
    )
    return {"txn_b64": _txn_to_b64(txn)}

