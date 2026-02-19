"""
CampaFi – Contract Deployment Script (AlgoKit)
====================================================
Compiles all Beaker contracts and optionally deploys them to the
configured Algorand network (TestNet by default).

Usage
-----
    # Compile only (writes TEAL + ABI JSON to contracts/artifacts/)
    python -m contracts.deploy --compile

    # Compile + deploy (requires DEPLOYER_MNEMONIC in .env)
    python -m contracts.deploy --deploy

    # Deploy a single contract
    python -m contracts.deploy --deploy --contract campus_bank

Environment variables (in .env)
-------------------------------
    DEPLOYER_MNEMONIC   – 25-word mnemonic of the deployer account
    ALGOD_ADDRESS       – Algorand node URL  (default: https://testnet-api.algonode.cloud)
    ALGOD_TOKEN         – node API token     (default: empty for AlgoNode)
"""

import argparse
import json
import pathlib
import sys

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Contract registry
# ---------------------------------------------------------------------------
CONTRACTS = {}

def _register_contracts():
    """Lazy-import Beaker apps so PyTeal compiles only when needed."""
    from contracts.campus_bank import app as bank_app
    from contracts.campus_dao import app as dao_app
    from contracts.certificate_store import app as cert_app

    CONTRACTS["campus_bank"] = bank_app
    CONTRACTS["campus_dao"] = dao_app
    CONTRACTS["certificate_store"] = cert_app


# ---------------------------------------------------------------------------
# Compile
# ---------------------------------------------------------------------------
def compile_all(only: str | None = None):
    """Write TEAL + ABI artefacts for each contract."""
    _register_contracts()
    targets = {only: CONTRACTS[only]} if only else CONTRACTS

    for name, beaker_app in targets.items():
        spec = beaker_app.build()
        out = pathlib.Path(__file__).parent / "artifacts" / name
        out.mkdir(parents=True, exist_ok=True)

        (out / "approval.teal").write_text(spec.approval_program)
        (out / "clear.teal").write_text(spec.clear_program)
        (out / "contract.json").write_text(json.dumps(spec.dictify(), indent=2))
        print(f"  ✅  {name} → {out}")


# ---------------------------------------------------------------------------
# Deploy  (requires algokit-utils + funded deployer account)
# ---------------------------------------------------------------------------
def deploy_all(only: str | None = None):
    """Compile then deploy contracts using AlgoKit utilities."""
    import os
    from algosdk import mnemonic as mn
    from algosdk.v2client.algod import AlgodClient
    from algokit_utils import ApplicationClient, get_algod_client

    _register_contracts()
    targets = {only: CONTRACTS[only]} if only else CONTRACTS

    deployer_mnemonic = os.getenv("DEPLOYER_MNEMONIC")
    if not deployer_mnemonic:
        print("❌  Set DEPLOYER_MNEMONIC in .env to deploy contracts.")
        sys.exit(1)

    private_key = mn.to_private_key(deployer_mnemonic)
    algod = get_algod_client()          # reads ALGOD_ADDRESS / ALGOD_TOKEN from env

    for name, beaker_app in targets.items():
        print(f"\n🚀  Deploying {name} …")
        client = ApplicationClient(
            client=algod,
            app=beaker_app,
            signer=private_key,
        )
        app_id, app_addr, txid = client.create()
        print(f"  ✅  App ID : {app_id}")
        print(f"  📌  Address: {app_addr}")
        print(f"  🔗  TxID   : {txid}")

        # Persist app id so the web app can read it
        id_file = pathlib.Path(__file__).parent / "artifacts" / name / "app_id.txt"
        id_file.write_text(str(app_id))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="CampaFi contract tooling")
    parser.add_argument("--compile", action="store_true", help="Compile TEAL artefacts")
    parser.add_argument("--deploy", action="store_true", help="Compile + deploy to network")
    parser.add_argument("--contract", type=str, default=None, help="Target a single contract by name")
    args = parser.parse_args()

    if args.deploy:
        print("📦  Compiling contracts …")
        compile_all(only=args.contract)
        deploy_all(only=args.contract)
    elif args.compile:
        print("📦  Compiling contracts …")
        compile_all(only=args.contract)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
