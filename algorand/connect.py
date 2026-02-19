"""
CampaFi – Algorand Client Helpers
======================================
Provides read-only / unsigned-transaction helpers.

🔒 **No server-side private keys.**
   All signing happens client-side in Pera Wallet.
"""

import os

from algosdk.v2client.algod import AlgodClient
from algosdk.v2client.indexer import IndexerClient


def get_client() -> AlgodClient:
    """Return an AlgodClient pointed at the configured network."""
    algod_address = os.environ.get(
        "ALGOD_ADDRESS", "https://testnet-api.algonode.cloud"
    )
    algod_token = os.environ.get("ALGOD_TOKEN", "")
    return AlgodClient(algod_token, algod_address)


def get_indexer() -> IndexerClient:
    """Return an IndexerClient for querying historical data."""
    indexer_address = os.environ.get(
        "INDEXER_ADDRESS", "https://testnet-idx.algonode.cloud"
    )
    indexer_token = os.environ.get("INDEXER_TOKEN", "")
    return IndexerClient(indexer_token, indexer_address)


def get_suggested_params():
    """Fetch current suggested transaction parameters from the network."""
    return get_client().suggested_params()
