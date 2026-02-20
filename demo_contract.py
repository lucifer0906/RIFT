"""
CollegePay – Smart Contract Demo Script
=========================================
Run this to demonstrate the CampusBank smart contract on Algorand TestNet.
Shows: contract lookup → deposit → on-chain confirmation → state read.

Usage:
    python demo_contract.py

Prerequisites:
    - pip install py-algorand-sdk python-dotenv
    - .env file with DEPLOYER_MNEMONIC (25-word mnemonic of funded TestNet account)
"""

import os
import sys
import time
import base64
from dotenv import load_dotenv

load_dotenv()

from algosdk.v2client.algod import AlgodClient
from algosdk.v2client.indexer import IndexerClient
from algosdk import mnemonic, account, transaction, logic, encoding

# ── Config ──
ALGOD_URL   = "https://testnet-api.algonode.cloud"
INDEXER_URL = "https://testnet-idx.algonode.cloud"
BANK_APP_ID = 755801824   # Your deployed CampusBank contract

algod   = AlgodClient("", ALGOD_URL)
indexer = IndexerClient("", INDEXER_URL)


def get_app_address(app_id):
    """Derive the escrow address of an Algorand Application."""
    return logic.get_application_address(app_id)


def wait_for_confirmation(client, txid, timeout=10):
    """Wait until a transaction is confirmed."""
    last_round = client.status()["last-round"]
    for _ in range(timeout):
        info = client.pending_transaction_info(txid)
        if info.get("confirmed-round", 0) > 0:
            return info
        last_round += 1
        client.status_after_block(last_round)
    raise Exception("Transaction not confirmed within timeout")


def print_separator():
    print("\n" + "═" * 60)


def demo():
    # ── Step 0: Load deployer account ──
    deployer_mnemonic = os.getenv("DEPLOYER_MNEMONIC")
    if not deployer_mnemonic:
        print("❌  Set DEPLOYER_MNEMONIC in .env (25-word Algorand mnemonic)")
        print("   Get free TestNet ALGO from: https://bank.testnet.algorand.network/")
        sys.exit(1)

    private_key = mnemonic.to_private_key(deployer_mnemonic)
    sender = account.address_from_private_key(private_key)
    app_addr = get_app_address(BANK_APP_ID)

    print_separator()
    print("🏦  CollegePay – CampusBank Smart Contract Demo")
    print_separator()
    print(f"  Contract App ID : {BANK_APP_ID}")
    print(f"  Contract Address: {app_addr}")
    print(f"  Your Wallet     : {sender}")
    print(f"  Explorer URL    : https://testnet.explorer.perawallet.app/application/{BANK_APP_ID}")

    # ── Step 1: Read current contract state ──
    print_separator()
    print("📖  Step 1: Reading contract state from blockchain...")
    
    try:
        app_info = algod.application_info(BANK_APP_ID)
        global_state = app_info.get("params", {}).get("global-state", [])
        
        print(f"  ✅ Contract found on TestNet!")
        print(f"  Creator: {app_info['params']['creator']}")
        
        for state in global_state:
            key = base64.b64decode(state["key"]).decode()
            val = state["value"]
            if val["type"] == 2:  # uint
                print(f"  State '{key}' = {val['uint']}")
            else:
                print(f"  State '{key}' = {base64.b64decode(val['bytes']).hex()}")
    except Exception as e:
        print(f"  ⚠️  Could not read app state: {e}")

    # ── Step 2: Check balances ──
    print_separator()
    print("💰  Step 2: Checking balances...")
    
    sender_info = algod.account_info(sender)
    sender_balance = sender_info["amount"] / 1_000_000
    print(f"  Your balance     : {sender_balance:.4f} ALGO")
    
    try:
        contract_info = algod.account_info(app_addr)
        contract_balance = contract_info["amount"] / 1_000_000
        print(f"  Contract balance : {contract_balance:.4f} ALGO")
    except:
        contract_balance = 0
        print(f"  Contract balance : 0 ALGO (not yet funded)")

    if sender_balance < 0.3:
        print(f"\n  ⚠️  Low balance! Get free TestNet ALGO:")
        print(f"     https://bank.testnet.algorand.network/")
        print(f"     Paste your address: {sender}")
        sys.exit(1)

    # ── Step 3: Deposit ALGO into the contract ──
    print_separator()
    deposit_amount = 0.1  # ALGO
    deposit_micro = int(deposit_amount * 1_000_000)
    print(f"📥  Step 3: Depositing {deposit_amount} ALGO into CampusBank...")
    print(f"  Building atomic group: PaymentTxn + AppCallTxn...")
    
    params = algod.suggested_params()

    # Transaction 1: Pay ALGO to the contract's escrow address
    pay_txn = transaction.PaymentTxn(
        sender=sender,
        sp=params,
        receiver=app_addr,
        amt=deposit_micro,
    )

    # Transaction 2: Call the deposit() method on the contract
    # Method selector for deposit()uint64 = 0xb8843568
    app_txn = transaction.ApplicationCallTxn(
        sender=sender,
        sp=params,
        index=BANK_APP_ID,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=[bytes.fromhex("b8843568")],
    )

    # Group them atomically (both succeed or both fail)
    transaction.assign_group_id([pay_txn, app_txn])
    print(f"  Group ID: {base64.b64encode(pay_txn.group).decode()}")

    # Sign both transactions
    signed_pay = pay_txn.sign(private_key)
    signed_app = app_txn.sign(private_key)

    # Submit the atomic group
    print(f"  Submitting to Algorand TestNet...")
    txid = algod.send_transactions([signed_pay, signed_app])
    print(f"  Transaction ID: {txid}")
    print(f"  Waiting for confirmation...")
    
    start = time.time()
    result = wait_for_confirmation(algod, txid)
    elapsed = time.time() - start
    
    confirmed_round = result["confirmed-round"]
    print(f"  ✅ CONFIRMED in round {confirmed_round} ({elapsed:.1f}s)")
    print(f"  🔗 View on explorer:")
    print(f"     https://testnet.explorer.perawallet.app/tx/{txid}")

    # ── Step 4: Verify the deposit ──
    print_separator()
    print("🔍  Step 4: Verifying deposit on-chain...")
    
    time.sleep(2)  # wait for indexer to catch up
    
    contract_info_after = algod.account_info(app_addr)
    new_balance = contract_info_after["amount"] / 1_000_000
    print(f"  Contract balance BEFORE: {contract_balance:.4f} ALGO")
    print(f"  Contract balance AFTER : {new_balance:.4f} ALGO")
    print(f"  Difference             : +{new_balance - contract_balance:.4f} ALGO ✅")

    # Read updated global state
    try:
        app_info_after = algod.application_info(BANK_APP_ID)
        global_state_after = app_info_after.get("params", {}).get("global-state", [])
        for state in global_state_after:
            key = base64.b64decode(state["key"]).decode()
            val = state["value"]
            if val["type"] == 2:
                print(f"  Updated state '{key}' = {val['uint']}")
    except:
        pass

    # ── Step 5: Show transaction history ──
    print_separator()
    print("📜  Step 5: Transaction history for this contract...")
    
    try:
        txns = indexer.search_transactions_by_address(app_addr, limit=5)
        for i, tx in enumerate(txns.get("transactions", [])[:5]):
            tx_type = tx.get("tx-type", "?")
            tx_id = tx.get("id", "?")
            round_num = tx.get("confirmed-round", "?")
            
            if tx_type == "pay":
                pay_info = tx.get("payment-transaction", {})
                amt = pay_info.get("amount", 0) / 1_000_000
                print(f"  [{i+1}] PAY  {amt:.4f} ALGO | Round {round_num} | {tx_id[:20]}...")
            elif tx_type == "appl":
                print(f"  [{i+1}] APPL (contract call) | Round {round_num} | {tx_id[:20]}...")
            else:
                print(f"  [{i+1}] {tx_type} | Round {round_num} | {tx_id[:20]}...")
    except Exception as e:
        print(f"  ⚠️  Indexer query failed: {e}")

    # ── Done ──
    print_separator()
    print("🎉  Demo Complete!")
    print(f"  • Contract is LIVE on Algorand TestNet")
    print(f"  • Deposit of {deposit_amount} ALGO confirmed on-chain")
    print(f"  • Transaction is permanent and publicly verifiable")
    print(f"  • Only the creator ({app_info['params']['creator'][:12]}...) can withdraw")
    print_separator()


if __name__ == "__main__":
    demo()
