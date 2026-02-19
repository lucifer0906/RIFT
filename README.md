# CampaFi — Blockchain-Powered Campus Management System

[![Algorand](https://img.shields.io/badge/Blockchain-Algorand-00D4AA?style=for-the-badge&logo=algorand)](https://www.algorand.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3+-000000?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com/)
[![PyTeal](https://img.shields.io/badge/PyTeal-Smart_Contracts-00D4AA?style=for-the-badge)](https://pyteal.readthedocs.io/)
[![Pera Wallet](https://img.shields.io/badge/Pera_Wallet-Client_Signing-FFDE59?style=for-the-badge)](https://perawallet.app/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

> A decentralized campus management platform with a wallet-first dashboard. Connect Pera Wallet to send/receive ALGO, view token holdings, track transactions, verify certificates, vote in elections, and collaborate in groups — all anchored on Algorand TestNet with zero server-side signing.

---

## Table of Contents

- [Project Overview](#-project-overview)
- [System Architecture](#-system-architecture)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Installation & Setup](#-installation--setup)
- [API Reference](#-api-reference)
- [Smart Contracts](#-smart-contracts)
- [Cost Breakdown](#-cost-breakdown)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Security](#-security)
- [Future Roadmap](#-future-roadmap)
- [Contributing](#-contributing)
- [License](#-license)
- [Acknowledgments](#-acknowledgments)

---

## 📌 Project Overview

### The Problem

Traditional campus management systems suffer from:

- **Certificate Fraud** — fake diplomas are trivially created and hard to verify
- **Election Manipulation** — centralized voting lacks transparency and can be tampered with
- **No Student Wallet** — no unified way to send/receive campus payments
- **Trust Deficit** — no immutable proof of achievements or participation
- **Collaboration Opacity** — group work lacks verifiable tracking

### Our Solution

CampaFi is built around a **wallet-first** design using Algorand blockchain:

| Capability | How It Works |
|---|---|
| **Campus Wallet** | Connect Pera Wallet → live ALGO balance, ASA tokens, QR receive, quick send |
| **Certificate NFTs** | Upload cert → SHA-256 hash → stored on-chain → QR verification |
| **Blockchain Elections** | Votes recorded as Algorand transactions → tamper-proof results |
| **Group Collaboration** | Tasks & milestones logged on-chain → verifiable contributions |
| **CampusCoin (CCOIN)** | Custom ASA token for campus rewards & payments |
| **AI Chatbot** | Gemini-powered CampusBot with attendance analytics |
| **Face ID Attendance** | Biometric check-in with face-api.js ML models |

### Why Algorand?

| Traditional DB | Algorand |
|---|---|
| ❌ Centralized control | ✅ Decentralized verification |
| ❌ Mutable records | ✅ Immutable proof |
| ❌ Single point of failure | ✅ 4.5s finality, Pure PoS |
| ❌ No public audit | ✅ Transparent transaction history |
| ❌ ~$0.50/verification | ✅ ~$0.0003/transaction |

### Real-World Use Cases

1. **Universities** — Issue tamper-proof digital certificates
2. **Student Organizations** — Conduct transparent elections
3. **Recruiters** — Instantly verify candidate credentials
4. **International Students** — Prove qualifications across borders
5. **Campus Groups** — Track collaborative projects with blockchain-backed milestones
6. **Token Economies** — Create loyalty tokens or campus currencies

---

## 🧠 System Architecture

### High-Level Architecture

```mermaid
graph TB
    subgraph "Client - Browser"
        A[Dashboard + Wallet UI] --> B[wallet.js – Balance, History, QR, Send]
        B --> C[Pera Wallet Connect – Client-side Signing]
        A --> D[wallet_features.html – ASA, NFT, Contracts]
    end

    subgraph "Server - Flask"
        E[app.py – Routes + API] --> F[SQLite – Users, Certs, Elections]
        E --> G["/api/prepare_*" – Unsigned Tx Builders]
        E --> H["/api/submit_transaction" – Relay Signed Tx]
    end

    subgraph "Blockchain - Algorand TestNet"
        I[AlgoNode RPC] --> J[Algod API]
        I --> K[Indexer API]
        L[Beaker Smart Contracts]
        M[CampusCoin ASA]
    end

    C -->|Sign Txn| G
    G -->|Build Unsigned Txn| J
    H -->|Submit Signed Txn| J
    B -->|Fetch Balance| J
    B -->|Fetch History| K
```

### Key Design Principle: No Server-Side Signing

```
User → Server builds UNSIGNED tx → Pera Wallet SIGNS → Server relays
```

All private key operations happen in the user's Pera Wallet. The server never touches mnemonics for user transactions.

### On-Chain vs Off-Chain Logic

| Component | Storage | Reason |
|---|---|---|
| User credentials | Off-Chain (SQLite) | Privacy, fast auth |
| Certificate hashes | On-Chain (Algorand) | Immutable proof, public verification |
| Election votes | On-Chain (Algorand) | Transparency, tamper-proof |
| Group milestones | On-Chain (Algorand) | Permanent achievement records |
| Token metadata | On-Chain (ASA) | Decentralized asset management |
| Smart contract state | On-Chain (App State) | Trustless execution |
| Transaction logs | Hybrid (DB + Chain) | Audit trail redundancy |

### Transaction Lifecycle

```mermaid
sequenceDiagram
    participant User
    participant wallet.js
    participant Flask API
    participant Pera Wallet
    participant Algorand

    User->>wallet.js: Click "Send 5 ALGO"
    wallet.js->>Flask API: POST /api/prepare_payment
    Flask API->>Flask API: build_payment_txn() → unsigned bytes
    Flask API-->>wallet.js: {unsigned_txn: base64}
    wallet.js->>wallet.js: algosdk.decodeUnsignedTransaction()
    wallet.js->>Pera Wallet: peraWallet.signTransaction()
    Pera Wallet-->>wallet.js: signedTxn bytes
    wallet.js->>Flask API: POST /api/submit_transaction
    Flask API->>Algorand: algod.send_raw_transaction()
    Algorand-->>Flask API: txId
    Flask API-->>wallet.js: {txId}
    wallet.js->>wallet.js: refreshWalletDashboard()
```

---

## 🚀 Features

### 1. Wallet-First Dashboard

The dashboard displays your wallet prominently at the top:

- **Balance Card** — live ALGO balance from AlgoNode API
- **Receive QR** — scannable QR code of your Algorand address
- **Quick Send** — 3-field form for instant ALGO payments
- **Token Holdings** — all ASAs held (name, unit, amount)
- **Transaction History** — last 8 txns with type, amount, date, explorer links
- Auto-toggles between "Connect Wallet" CTA and full wallet panel

### 2. Certificate Verification System

- Upload PDF/image → SHA-256 hash → stored on Algorand as note
- QR code per certificate linking to Lora Explorer
- Delete support via Beaker `certificate_store` contract
- Public verification at `/verify` — upload file, hash compared on-chain
- Cost: ~0.001 ALGO per certificate

```python
# Simplified flow
file_hash = hashlib.sha256(file_content).hexdigest()
note = f"CERT|user:{user_id}|hash:{file_hash}|timestamp:{timestamp}"
tx = PaymentTxn(sender=wallet, receiver=wallet, amt=0, note=note.encode())
tx_id = algod_client.send_transaction(signed_tx)
```

### 3. Decentralized Elections

- Admin creates elections with candidates
- Students vote once per election, recorded on-chain
- Transparent tallying from blockchain data
- Results verifiable by anyone via Indexer

### 4. Group Collaboration & DAO

- Create/join project groups, assign tasks/milestones
- Task completions logged on-chain as immutable records
- DAO treasury per group (Beaker `campus_dao` contract)
- Full proposal lifecycle: create → vote → approve → execute (on-chain disbursement)

### 5. Advanced Wallet Features (`/wallet/features`)

Four-tab interface:

- **Send ALGO** — payment with custom notes
- **Create Token** — fungible ASA with configurable supply/decimals
- **Mint NFT** — unique achievement badges with IPFS URLs
- **Smart Contract** — deploy & interact with bank contracts

### 6. CampusCoin (CCOIN)

- Custom Algorand Standard Asset: `CampusCoin` / `CAMPUS` / 6 decimals
- Deploy via `/api/prepare_campus_coin_deploy` + Pera signing
- Used for campus rewards, attendance incentives, group payments
- State persisted in `system_state.json`

### 7. Attendance with Face ID

- Instructor creates session → students check in via webcam
- Face recognition using face-api.js ML models (68-point landmarks)
- Attendance percentage analytics per course
- On-chain attendance records with blockchain-backed timestamps

### 8. Feedback Collection

- Create anonymous/named feedback forms with custom questions
- Submit responses with blockchain-anchored timestamps
- Analytics dashboard with response visualizations

### 9. AI Chatbot (CampusBot)

- Gemini 2.0 Flash powered with retries across multiple models
- Queries user's real attendance data, groups, DAO info
- Exponential backoff on rate limits (tries `gemini-2.0-flash-lite` → `gemini-1.5-flash` → `gemini-2.0-flash`)
- Context-aware: injects per-course attendance breakdown into system prompt

---

## 🏗️ Tech Stack

### Blockchain

| Technology | Purpose |
|---|---|
| **Algorand TestNet** | Layer-1 blockchain (4.5s finality, ~$0.001/tx) |
| **py-algorand-sdk 2.0+** | Build unsigned transactions server-side |
| **algosdk.js 2.4.0 (CDN)** | Decode transactions client-side |
| **Pera Wallet Connect 1.5+** | Client-side transaction signing |
| **Beaker (PyTeal)** | Smart contracts: campus_bank, campus_dao, certificate_store |
| **AlgoNode** | Free RPC (algod + indexer) — no API key needed |

### Backend

| Technology | Purpose |
|---|---|
| **Flask 2.3+** | Web framework & REST API |
| **SQLite** | User data, certificates, elections, groups |
| **Gunicorn** | Production WSGI server |
| **python-dotenv** | Environment variable management |
| **google-generativeai** | Gemini AI for chatbot |

### Frontend

| Technology | Purpose |
|---|---|
| **Bootstrap 5.3** | Responsive UI framework |
| **wallet.js** | Wallet core: balance, history, QR, send, toasts |
| **Pera Wallet bundle** | Webpack-compiled `@perawallet/connect` |
| **qrcodejs** | QR code generation for addresses & certificates |
| **Font Awesome 6** | Icons |
| **Jinja2** | Server-side templating |
| **face-api.js** | Face recognition ML models |

---

## 📂 Project Structure

```
CampaFi-blockchain/
│
├── contracts/                     # AlgoKit / Beaker smart contracts
│   ├── campus_bank.py             # Deposit/withdraw ALGO (Beaker Application)
│   ├── campus_dao.py              # DAO treasury + disburse (Beaker Application)
│   ├── certificate_store.py       # Certificate hash box storage (Beaker Application)
│   ├── campus_coin.py             # CampusCoin ASA deployment helper
│   ├── deploy.py                  # AlgoKit CLI deploy script (--compile / --deploy)
│   └── __init__.py
│
├── algorand/                      # Blockchain integration layer
│   ├── connect.py                 # get_client(), get_indexer(), get_suggested_params()
│   ├── store_hash.py              # build_note_txn(), submit_signed_txn()
│   ├── advanced_features.py       # Unsigned tx builders + submit helpers
│   ├── deploy_certificate.py      # Certificate contract deployment
│   ├── update_contract.py         # Contract update utility
│   └── contracts/                 # Original PyTeal source contracts
│       ├── simple_bank.py         # PyTeal bank contract
│       ├── simple_dao.py          # PyTeal DAO contract
│       ├── certificate_contract.py# PyTeal certificate contract
│       └── debug_contract.py      # Debug contract utility
│
├── utils/                         # Server-side helpers
│   ├── hash_utils.py              # SHA-256 file hashing
│   ├── blockchain_utils.py        # Certificate store/verify/delete (unsigned txn builders)
│   ├── rewards.py                 # CampusCoin reward system (unsigned txn builders)
│   └── auth_utils.py              # Authentication helpers
│
├── templates/                     # Jinja2 HTML templates
│   ├── base.html                  # Layout: navbar, CDN scripts, chatbot widget
│   ├── dashboard.html             # Wallet-first dashboard + campus feature tabs
│   ├── wallet_features.html       # Advanced: Send ALGO, Create ASA, Mint NFT, Contracts
│   ├── upload_cert.html           # Certificate upload form
│   ├── verify_cert.html           # Public certificate verification
│   ├── election.html              # Election listing & voting
│   ├── create_election.html       # Election creation (admin)
│   ├── attendance_*.html          # Sessions, reports, Face ID check-in
│   ├── feedback_*.html            # Forms, results, analytics
│   ├── group_*.html               # Create, detail, discover, admin
│   ├── login.html / register.html # Authentication pages
│   ├── setup_face.html            # Face ID registration
│   └── public_logs.html           # On-chain transaction browser
│
├── static/
│   ├── css/style.css              # Custom styles + wallet dashboard CSS
│   ├── js/
│   │   ├── wallet.js              # Wallet core v2.0 (connect, balance, history, QR, send)
│   │   ├── perawallet-bundle.js   # Webpack-compiled Pera SDK
│   │   ├── chat.js                # Gemini AI chatbot client
│   │   └── script.js              # Legacy utilities
│   └── models/                    # face-api.js ML models for Face ID
│
├── tests/
│   ├── test_fixes.py              # Core feature tests (15 tests)
│   ├── test_wallet.py             # Wallet API tests (7 tests)
│   └── test_analytics.py          # Analytics tests
│
├── app.py                         # Main Flask application (~2500 lines)
├── requirements.txt               # Python dependencies
├── package.json                   # Node deps (Pera Wallet SDK, webpack)
├── webpack.config.js              # Webpack → perawallet-bundle.js
├── pera_entry.js                  # Webpack entry point
├── system_state.json              # CampusCoin state persistence
├── Procfile                       # Production deployment (Gunicorn)
└── README.md                      # This file
```

---

## ⚙️ Installation & Setup

### Prerequisites

- **Python 3.8+** with pip
- **Node.js 16+** with npm (for webpack / Pera bundle)
- **Pera Wallet** mobile app ([iOS](https://apps.apple.com/app/pera-algo-wallet/id1459898525) / [Android](https://play.google.com/store/apps/details?id=com.algorand.android))

### Step 1: Clone & Install

```bash
git clone https://github.com/Helly121/CampaFi-blockchain.git
cd CampaFi-blockchain

# Python dependencies
pip install -r requirements.txt

# Node dependencies (Pera Wallet SDK + Webpack)
npm install
npm run build
```

### Step 2: Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:

```bash
# Required
FLASK_SECRET_KEY=your-random-secret-key

# Algorand RPC (defaults to AlgoNode TestNet — no API key needed)
ALGOD_ADDRESS=https://testnet-api.algonode.cloud
INDEXER_ADDRESS=https://testnet-idx.algonode.cloud

# Certificate Store App ID
CERT_APP_ID=755556381

# CampusCoin ASA ID (set after deploying via wallet)
# CAMPUS_COIN_ID=

# Optional: Gemini AI chatbot
# GEMINI_API_KEY=your-key
```

> ⚠️ **No `ALGO_MNEMONIC` needed!** All transaction signing happens in Pera Wallet on the client side.

### Step 3: Fund Your Pera Wallet

1. Open Pera Wallet → Settings → Developer → Switch to **TestNet**
2. Visit [Algorand TestNet Dispenser](https://dispenser.testnet.aws.algorand.com/)
3. Paste your address → receive free TestNet ALGO

### Step 4: Run

```bash
python app.py
# → http://127.0.0.1:5000
```

1. Register an account at `/register`
2. Click **Connect Wallet** in the navbar → scan QR with Pera
3. Dashboard shows live balance, receive QR, transaction history
4. Use **Wallet** nav link for advanced features (ASA, NFT, contracts)

### Step 5: Deploy Smart Contracts (Optional)

```bash
# Compile Beaker contracts to TEAL
python contracts/deploy.py --compile

# Deploy to TestNet (requires DEPLOYER_MNEMONIC in .env)
python contracts/deploy.py --deploy
```

### Step 6: Deploy CampusCoin (Optional)

1. Connect Pera Wallet on the site
2. POST to `/api/prepare_campus_coin_deploy` with `{sender: "YOUR_ADDRESS"}`
3. Sign the returned transaction in Pera
4. Submit via `/api/submit_transaction`
5. Set the returned Asset ID as `CAMPUS_COIN_ID` in `.env`

---

## 🔌 API Reference

### Unsigned Transaction Builders

All return `{unsigned_txn: base64, ...metadata}`. Sign with Pera, submit via `/api/submit_transaction`.

| Endpoint | Method | Body | Description |
|---|---|---|---|
| `/api/prepare_payment` | POST | `{sender, receiver, amount, note}` | ALGO payment |
| `/api/prepare_asset_creation` | POST | `{sender, asset_name, unit_name, total, decimals, url}` | Create ASA |
| `/api/prepare_nft_minting` | POST | `{sender, asset_name, unit_name, ipfs_url}` | Mint NFT |
| `/api/prepare_bank_deposit` | POST | `{sender, app_id, amount}` | Bank deposit (group txns) |
| `/api/prepare_bank_withdraw` | POST | `{sender, app_id, amount}` | Bank withdraw |
| `/api/prepare_campus_coin_deploy` | POST | `{sender}` | Deploy CampusCoin ASA |

### Transaction Submission

| Endpoint | Method | Body | Returns |
|---|---|---|---|
| `/api/submit_transaction` | POST | `{signed_txn: base64}` or `{signed_txns: [base64]}` | `{txId}` or `{txId, assetId}` |

### Read-Only

| Endpoint | Method | Description |
|---|---|---|
| `/api/campus_coin_info` | GET | CampusCoin ASA details |
| `/api/chat` | POST | AI chatbot (Gemini) |

### Example: Send ALGO from JavaScript

```javascript
// 1. Build unsigned txn
const resp = await fetch("/api/prepare_payment", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sender: address, receiver: "ABC...", amount: 1.5, note: "lunch" })
});
const { unsigned_txn } = await resp.json();

// 2. Decode & sign with Pera
const txnBytes = Uint8Array.from(atob(unsigned_txn), c => c.charCodeAt(0));
const decoded = algosdk.decodeUnsignedTransaction(txnBytes);
const signed = await peraWallet.signTransaction([[{ txn: decoded }]]);

// 3. Submit
const result = await fetch("/api/submit_transaction", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ signed_txn: btoa(String.fromCharCode(...signed[0])) })
});
const { txId } = await result.json();
console.log("Transaction:", txId);
```

---

## 🔐 Smart Contracts

### CampusBank (`contracts/campus_bank.py`)

- `deposit()` — accept ALGO via atomic grouped payment + app call
- `withdraw()` — inner transaction sends ALGO to caller (creator only)
- Global state: `Creator` address for access control

### CampusDAO (`contracts/campus_dao.py`)

- `disburse(recipient, amount)` — distribute funds from DAO treasury
- Creator-controlled access for group treasuries
- Inner transactions for automated payments
- Tracks `total_disbursements` in global state

### CertificateStore (`contracts/certificate_store.py`)

- `add_certificate(hash, owner)` — store cert hash in Algorand box storage (AVM v8+)
- `delete_certificate(hash)` — remove cert (owner only)
- `verify_certificate(hash)` — read-only on-chain verification
- O(1) lookup via box storage

### Security Features

- Access control: only creator can withdraw/disburse
- Reentrancy protection: Algorand atomic transactions by design
- Integer overflow protection: PyTeal safe math
- Fee pooling: inner transactions share fee budget

---

## ⛽ Cost Breakdown

| Operation | Cost (ALGO) | ~USD* |
|---|---|---|
| Certificate upload (note txn) | 0.001 | $0.0003 |
| Election vote | 0.001 | $0.0003 |
| ALGO payment | 0.001 | $0.0003 |
| ASA creation | 0.1 | $0.03 |
| NFT mint | 0.1 | $0.03 |
| Contract deployment | 0.1 | $0.03 |
| Bank deposit/withdraw | 0.002 | $0.0006 |

*Assuming 1 ALGO ≈ $0.30 USD

---

## 🧪 Testing

```bash
# Run all tests
python -m unittest discover tests/

# Specific suites
python tests/test_wallet.py     # 7 wallet API tests
python tests/test_fixes.py      # 15 core feature tests
python tests/test_analytics.py  # Analytics tests
```

All blockchain calls are mocked — no TestNet ALGO required for testing.

### Test Coverage

| Module | Tests | Coverage |
|---|---|---|
| Wallet Features | 7 tests | Payment, ASA, NFT, Contracts |
| Core Fixes | 15 tests | Auth, Elections, Groups |
| Analytics | Varies | Attendance, feedback analytics |

---

## 🌍 Deployment

### Local Development

```bash
python app.py
# → http://127.0.0.1:5000 (debug mode)
```

### Production (Heroku / Railway / Render)

```bash
# Procfile already configured:
# web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 3

# Set env vars in hosting dashboard, then:
git push heroku main
```

### Rebuild Pera Wallet Bundle

```bash
npm run build     # production build (one-time)
npm run dev       # watch mode for development
```

### MainNet Migration

1. Update `ALGOD_ADDRESS` and `INDEXER_ADDRESS` to mainnet endpoints
2. Fund wallet with real ALGO
3. Redeploy contracts via `contracts/deploy.py --deploy`
4. Redeploy CampusCoin ASA
5. Update `CERT_APP_ID` and `CAMPUS_COIN_ID` in `.env`

---

## 🔐 Security

| Concern | Mitigation |
|---|---|
| **Private keys** | Never on server — all signing via Pera Wallet |
| **SQL injection** | Parameterized queries throughout |
| **XSS** | Jinja2 auto-escaping enabled |
| **CSRF** | Flask session with secret key |
| **Reentrancy** | Algorand atomic transactions prevent by design |
| **Mnemonic exposure** | No `ALGO_MNEMONIC` needed; optional `DEPLOYER_MNEMONIC` for CLI only |
| **Rate limiting** | Gemini API retries with exponential backoff |
| **Integer overflow** | PyTeal safe math operations |

---

## 📊 Future Roadmap

- [ ] Multi-signature wallets for critical transactions
- [ ] Delegated voting in elections
- [ ] IPFS integration for large file storage
- [ ] React Native mobile app with WalletConnect
- [ ] MainNet production deployment
- [ ] Algorand State Proofs for cross-chain verification
- [ ] Redis caching for frequently accessed data
- [ ] Token-based governance (DAO proposals)

---

## 🤝 Contributing

1. Fork → `git checkout -b feature/your-feature`
2. Follow PEP 8, add tests, update docs
3. Commit format: `feat:`, `fix:`, `docs:`, `refactor:`
4. Push → Create PR

---

## 📜 License

MIT License — see [LICENSE](LICENSE).

---

## 🙏 Acknowledgments

- **Algorand Foundation** — blockchain infrastructure
- **AlgoNode** — free RPC services (no API key needed)
- **Pera Wallet** — client-side signing SDK
- **AlgoKit / Beaker** — smart contract framework
- **Flask Community** — web framework & documentation
- **Google Gemini** — AI chatbot engine

---

**Built with ❤️ for transparent, decentralized campus management — wallet first.**
