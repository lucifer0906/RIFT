"""
CampusCoin – The CampaFi Stablecoin ASA
============================================
A standard Algorand Standard Asset (ASA) that serves as the campus reward
and payment token.  Deploy this once to create the ASA on TestNet, then set
the resulting Asset ID in your .env as CAMPUS_COIN_ID.

Token Parameters:
  - Name:      CampusCoin
  - Unit:      CCOIN
  - Decimals:  6  (same as ALGO – 1 CCOIN = 1_000_000 micro-units)
  - Total:     1_000_000_000 CCOIN  (1 billion)

Usage:
  python contracts/campus_coin.py --deploy          # deploy new ASA
  python contracts/campus_coin.py --asset-id 12345  # verify existing ASA
"""

import argparse
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from algorand.connect import get_client, get_suggested_params


# ── ASA parameters ──────────────────────────────────────────────────
CAMPUS_COIN_NAME = "CampusCoin"
CAMPUS_COIN_UNIT = "CCOIN"
CAMPUS_COIN_DECIMALS = 6
CAMPUS_COIN_TOTAL = 1_000_000_000  # 1 billion (before decimals factor)
CAMPUS_COIN_URL = "https://campafi.io/coin"
CAMPUS_COIN_NOTE = b"CampaFi CampusCoin ASA"


def build_campus_coin_create_txn(creator_address: str) -> dict:
    """
    Build an unsigned ASA-create transaction for CampusCoin.
    Returns dict with base64-encoded unsigned transaction bytes.
    """
    import base64
    from algosdk.transaction import AssetConfigTxn

    params = get_suggested_params()

    txn = AssetConfigTxn(
        sender=creator_address,
        sp=params,
        total=CAMPUS_COIN_TOTAL * (10 ** CAMPUS_COIN_DECIMALS),
        decimals=CAMPUS_COIN_DECIMALS,
        default_frozen=False,
        unit_name=CAMPUS_COIN_UNIT,
        asset_name=CAMPUS_COIN_NAME,
        url=CAMPUS_COIN_URL,
        manager=creator_address,
        reserve=creator_address,
        freeze=creator_address,
        clawback=creator_address,
        note=CAMPUS_COIN_NOTE,
        strict_empty_address_check=False,
    )

    unsigned_bytes = base64.b64encode(
        txn.dictify() if hasattr(txn, "dictify") else bytes(txn)
    ).decode()

    # Prefer the SDK-standard encoding
    import msgpack
    unsigned_bytes = base64.b64encode(
        msgpack.packb(txn.dictify(), use_bin_type=True)
    ).decode()

    return {
        "unsigned_txn": unsigned_bytes,
        "type": "asset_config",
        "asset_name": CAMPUS_COIN_NAME,
        "unit_name": CAMPUS_COIN_UNIT,
        "total": CAMPUS_COIN_TOTAL,
        "decimals": CAMPUS_COIN_DECIMALS,
    }


def verify_campus_coin(asset_id: int) -> dict:
    """Read-only: fetch ASA info from the network."""
    client = get_client()
    try:
        info = client.asset_info(asset_id)
        params = info.get("params", info.get("asset", {}).get("params", {}))
        return {
            "success": True,
            "asset_id": asset_id,
            "name": params.get("name"),
            "unit_name": params.get("unit-name"),
            "total": params.get("total"),
            "decimals": params.get("decimals"),
            "creator": params.get("creator"),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── CLI entry ──────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CampusCoin ASA helper")
    parser.add_argument("--deploy", action="store_true", help="Print unsigned create-txn (base64)")
    parser.add_argument("--asset-id", type=int, help="Verify an existing CampusCoin ASA")
    args = parser.parse_args()

    if args.deploy:
        addr = input("Creator address (Pera Wallet): ").strip()
        result = build_campus_coin_create_txn(addr)
        print("\n✅ Unsigned ASA-create transaction (base64):")
        print(result["unsigned_txn"][:80] + "…")
        print(f"\nSign this in Pera Wallet, then submit via /api/submit_transaction")
        print(f"Set the returned Asset ID in .env as CAMPUS_COIN_ID")

    elif args.asset_id:
        info = verify_campus_coin(args.asset_id)
        if info["success"]:
            print(f"✅ CampusCoin ASA #{info['asset_id']}")
            print(f"   Name:     {info['name']}")
            print(f"   Unit:     {info['unit_name']}")
            print(f"   Total:    {info['total']}")
            print(f"   Decimals: {info['decimals']}")
            print(f"   Creator:  {info['creator']}")
        else:
            print(f"❌ {info['error']}")
    else:
        parser.print_help()
