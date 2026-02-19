"""
Tests for CampaFi Wallet features – v2.0 (client-side signing).

The new architecture uses JSON API endpoints that build unsigned
transactions on the server; the client signs them via Pera Wallet.
Legacy form-POST routes redirect with an informational flash message.
"""

import unittest
import sys
import os
import json
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app


class WalletFeaturesTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test'
        self.client = app.test_client()

    # ------------------------------------------------------------------
    # Page access
    # ------------------------------------------------------------------
    def test_wallet_page_access(self):
        response = self.client.get('/wallet')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Campus Wallet', response.data)

    # ------------------------------------------------------------------
    # Legacy form-POST routes now redirect with flash messages
    # ------------------------------------------------------------------
    def test_legacy_wallet_pay_redirects(self):
        response = self.client.post('/wallet/pay', data={
            'receiver': 'TEST_ADDR', 'amount': '1.0', 'note': 'Test'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Pera Wallet', response.data)

    def test_legacy_wallet_create_asset_redirects(self):
        response = self.client.post('/wallet/create_asset', data={
            'unit_name': 'TEST', 'asset_name': 'Coin', 'total': '100', 'decimals': '0'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Pera Wallet', response.data)

    def test_legacy_wallet_mint_nft_redirects(self):
        response = self.client.post('/wallet/mint_nft', data={
            'unit_name': 'NFT', 'asset_name': 'Test NFT', 'ipfs_url': 'ipfs://test'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Pera Wallet', response.data)

    def test_legacy_wallet_contract_deploy_redirects(self):
        response = self.client.post('/wallet/contract/deploy', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'AlgoKit', response.data)

    def test_legacy_wallet_contract_interact_redirects(self):
        response = self.client.post('/wallet/contract/interact', data={
            'app_id': '789', 'action': 'deposit', 'amount': '1.0'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Pera Wallet', response.data)

    # ------------------------------------------------------------------
    # JSON API: /api/prepare_payment
    # ------------------------------------------------------------------
    @patch('app.build_payment_txn')
    def test_api_prepare_payment(self, mock_build):
        mock_build.return_value = {'unsigned_txn': 'base64txn', 'txn_id': 'TXN123'}

        response = self.client.post('/api/prepare_payment',
            data=json.dumps({
                'sender': 'ADDR1', 'receiver': 'ADDR2',
                'amount': 1.5, 'note': 'hi'
            }),
            content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('unsigned_txn', data)
        mock_build.assert_called_once()

    def test_api_prepare_payment_missing_fields(self):
        response = self.client.post('/api/prepare_payment',
            data=json.dumps({'sender': 'ADDR1'}),
            content_type='application/json')
        self.assertEqual(response.status_code, 400)

    # ------------------------------------------------------------------
    # JSON API: /api/submit_transaction
    # ------------------------------------------------------------------
    @patch('app.submit_signed_transaction')
    def test_api_submit_transaction(self, mock_submit):
        mock_submit.return_value = {'success': True, 'tx_id': 'CONFIRMED_TX'}

        response = self.client.post('/api/submit_transaction',
            data=json.dumps({'signed_txn': 'base64signed'}),
            content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('txId', data)
        self.assertEqual(data['txId'], 'CONFIRMED_TX')

    # ------------------------------------------------------------------
    # Contract history (still server-rendered)
    # ------------------------------------------------------------------
    @patch('app.get_contract_history')
    def test_wallet_contract_history(self, mock_history):
        mock_history.return_value = {
            'success': True,
            'history': [{'round': 100, 'action': 'Deposit', 'amount': 10,
                         'user': 'User1', 'tx_id': 'TX1'}]
        }

        response = self.client.post('/wallet/contract/history', data={'app_id': '789'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Deposit', response.data)
        self.assertIn(b'User1', response.data)


if __name__ == '__main__':
    unittest.main()
