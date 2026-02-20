import os
from dotenv import load_dotenv
from algosdk import account, mnemonic
from algosdk.v2client import algod

load_dotenv()

def check_balance():
    mn = os.getenv("DEPLOYER_MNEMONIC")
    if not mn:
        print("No mnemonic found in .env")
        return

    try:
        pk = mnemonic.to_private_key(mn)
        address = account.address_from_private_key(pk)
        print(f"Checking balance for: {address}")

        algod_address = os.getenv("ALGOD_ADDRESS", "https://testnet-api.algonode.cloud")
        algod_token = os.getenv("ALGOD_TOKEN", "")
        client = algod.AlgodClient(algod_token, algod_address)

        account_info = client.account_info(address)
        microalgos = account_info.get('amount')
        algos = microalgos / 1_000_000
        print(f"Balance: {algos} ALGO")
        
        if algos < 1:
            print("❌ Insufficient funds for deployment (need at least 1-2 ALGO).")
        else:
            print("✅ Wallet funded!")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_balance()
