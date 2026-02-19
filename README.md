# 🛡️ CampusTrust — Blockchain-Powered Campus Wallet & Student Services# 🛡️ CampusTrust - Blockchain-Powered Campus Management System



[![Algorand](https://img.shields.io/badge/Blockchain-Algorand-00D4AA?style=for-the-badge&logo=algorand)](https://www.algorand.com/)[![Algorand](https://img.shields.io/badge/Blockchain-Algorand-00D4AA?style=for-the-badge&logo=algorand)](https://www.algorand.com/)

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)

[![Flask](https://img.shields.io/badge/Flask-2.3+-000000?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com/)[![Flask](https://img.shields.io/badge/Flask-2.0+-000000?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com/)

[![AlgoKit](https://img.shields.io/badge/AlgoKit-Beaker-00D4AA?style=for-the-badge)](https://developer.algorand.org/algokit/)[![PyTeal](https://img.shields.io/badge/PyTeal-Smart_Contracts-00D4AA?style=for-the-badge)](https://pyteal.readthedocs.io/)

[![Pera Wallet](https://img.shields.io/badge/Pera_Wallet-Client_Signing-FFDE59?style=for-the-badge)](https://perawallet.app/)[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

> **A decentralized campus management platform leveraging Algorand blockchain for transparent certificate verification, democratic elections, group collaboration, and advanced token operations.**

> **A decentralized campus management platform with a wallet-first dashboard. Connect Pera Wallet to send/receive ALGO, view token holdings, track transactions, verify certificates, vote in elections, and collaborate in groups — all anchored on Algorand TestNet. Zero server-side signing.**

---

---

## 📌 Project Overview

## 📌 Project Overview

### **The Problem**

### **The Problem**Traditional campus management systems face critical challenges:

Traditional campus management systems suffer from:- **Certificate Fraud**: Fake certificates are easily created and hard to verify

- **Certificate Fraud** — fake diplomas are trivially created- **Election Manipulation**: Centralized voting systems lack transparency and can be tampered with

- **Election Manipulation** — centralized voting lacks transparency- **Data Integrity**: Student records can be altered without audit trails

- **No Student Wallet** — no unified way to send/receive campus payments- **Trust Deficit**: No immutable proof of achievements or participation

- **Trust Deficit** — no immutable proof of achievements or participation- **Collaboration Opacity**: Group activities lack transparent tracking

- **Collaboration Opacity** — group work lacks verifiable tracking

### **Why Blockchain?**

### **Our Solution — v2.0 Architecture**CampusTrust uses **Algorand blockchain** instead of traditional databases because:



CampusTrust v2.0 is built around a **wallet-first** design:| Traditional Database | Blockchain (Algorand) |

|---------------------|----------------------|

| Capability | How It Works || ❌ Centralized control | ✅ Decentralized verification |

|---|---|| ❌ Mutable records | ✅ Immutable proof |

| 💰 **Campus Wallet** | Connect Pera Wallet → live ALGO balance, ASA tokens, QR receive, quick send || ❌ Single point of failure | ✅ Distributed consensus |

| 📜 **Certificate NFTs** | Upload cert → SHA-256 hash → stored on-chain → QR verification || ❌ Trust required in admin | ✅ Cryptographic verification |

| 🗳️ **Blockchain Elections** | Votes recorded as Algorand transactions → tamper-proof results || ❌ No public audit trail | ✅ Transparent transaction history |

| 👥 **Group Collaboration** | Tasks & milestones logged on-chain → verifiable contributions || ❌ Slow international verification | ✅ Instant global verification |

| 🪙 **CampusCoin (CCOIN)** | Custom ASA stablecoin for campus rewards & payments |

| 🤖 **AI Chatbot** | Gemini-powered CampusBot with attendance analytics |### **Real-World Use Cases**

1. **Universities**: Issue tamper-proof digital certificates

### **Why Algorand?**2. **Student Organizations**: Conduct transparent elections

3. **Recruiters**: Instantly verify candidate credentials

| Traditional DB | Algorand |4. **International Students**: Prove qualifications across borders

|---|---|5. **Campus Groups**: Track collaborative projects with blockchain-backed milestones

| ❌ Centralized control | ✅ Decentralized verification |6. **Token Economies**: Create loyalty tokens or campus currencies

| ❌ Mutable records | ✅ Immutable proof |

| ❌ Single point of failure | ✅ 4.5s finality, Pure PoS |---

| ❌ No public audit | ✅ Transparent transaction history |

| ❌ ~$0.50/verification | ✅ ~$0.0003/transaction |## 🧠 System Architecture



---### **High-Level Architecture**



## 🧠 System Architecture```mermaid

graph TB

### **High-Level Architecture**    subgraph "Frontend Layer"

        A[Web Browser] --> B[Flask Templates]

```mermaid        B --> C[Bootstrap UI]

graph TB    end

    subgraph "Client - Browser"    

        A[Dashboard + Wallet UI] --> B[wallet.js – Balance, History, QR, Send]    subgraph "Application Layer"

        B --> C[Pera Wallet Connect – Client-side Signing]        D[Flask Backend] --> E[SQLite Database]

        A --> D[wallet_features.html – ASA, NFT, Contracts]        D --> F[Blockchain Utils]

    end        D --> G[Advanced Features]

    end

    subgraph "Server - Flask"    

        E[app.py – Routes + API] --> F[SQLite – Users, Certs, Elections]    subgraph "Blockchain Layer"

        E --> G["/api/prepare_*" – Unsigned Tx Builders]        F --> H[Algorand SDK]

        E --> H["/api/submit_transaction" – Relay Signed Tx]        G --> H

    end        H --> I[Algorand TestNet]

        I --> J[AlgoNode API]

    subgraph "Blockchain - Algorand TestNet"    end

        I[AlgoNode RPC] --> J[Algod API]    

        I --> K[Indexer API]    subgraph "Smart Contracts"

        L[Beaker Smart Contracts]        K[PyTeal Contracts]

        M[CampusCoin ASA]        K --> L[Simple Bank Contract]

    end        L --> I

    end

    C -->|Sign Txn| G    

    G -->|Build Unsigned Txn| J    subgraph "Storage"

    H -->|Submit Signed Txn| J        E --> M[User Data]

    B -->|Fetch Balance| J        E --> N[Certificates]

    B -->|Fetch History| K        E --> O[Elections]

```        E --> P[Groups]

        I --> Q[Transaction Hashes]

### **Key Design Principle: No Server-Side Signing**        I --> R[Asset IDs]

        I --> S[Contract State]

```    end

OLD (v1): User → Server builds & SIGNS tx with server mnemonic → Submits    

NEW (v2): User → Server builds UNSIGNED tx → Pera Wallet SIGNS → Server relays    A --> D

```    D --> K

```

All private key operations happen in the user's Pera Wallet. The server never touches mnemonics.

### **On-Chain vs Off-Chain Logic**

### **On-Chain vs Off-Chain Logic**

| Component | Storage Location | Reason |

| Component | Storage | Reason ||-----------|-----------------|--------|

|---|---|---|| **User Credentials** | Off-Chain (SQLite) | Privacy, GDPR compliance, fast authentication |

| User credentials | Off-Chain (SQLite) | Privacy, fast auth || **Certificate Hashes** | On-Chain (Algorand) | Immutable proof, public verification |

| Certificate hashes | On-Chain (Algorand) | Immutable proof, public verification || **Election Votes** | On-Chain (Algorand) | Transparency, tamper-proof results |

| Election votes | On-Chain (Algorand) | Transparency, tamper-proof || **Group Milestones** | On-Chain (Algorand) | Permanent achievement records |

| Group milestones | On-Chain (Algorand) | Permanent achievement records || **Token Metadata** | On-Chain (ASA) | Decentralized asset management |

| Token metadata | On-Chain (ASA) | Decentralized asset management || **Smart Contract State** | On-Chain (App State) | Trustless execution |

| Smart contract state | On-Chain (App State) | Trustless execution || **Transaction Logs** | Hybrid (DB + File + Chain) | Audit trail redundancy |

| Transaction logs | Hybrid (DB + Chain) | Audit trail redundancy |

### **Transaction Lifecycle**

### **Transaction Lifecycle**

```mermaid

```mermaidsequenceDiagram

sequenceDiagram    participant User

    participant User    participant Flask

    participant wallet.js    participant SQLite

    participant Flask API    participant AlgoSDK

    participant Pera Wallet    participant Algorand

    participant Algorand    participant Indexer

    

    User->>wallet.js: Click "Send 5 ALGO"    User->>Flask: Submit Action (e.g., Upload Certificate)

    wallet.js->>Flask API: POST /api/prepare_payment    Flask->>SQLite: Store Metadata

    Flask API->>Flask API: build_payment_txn() → unsigned bytes    Flask->>AlgoSDK: Generate Transaction

    Flask API-->>wallet.js: {unsigned_txn: base64}    AlgoSDK->>Algorand: Submit to Network

    wallet.js->>wallet.js: algosdk.decodeUnsignedTransaction()    Algorand-->>AlgoSDK: Transaction ID

    wallet.js->>Pera Wallet: peraWallet.signTransaction()    AlgoSDK-->>Flask: Confirmation

    Pera Wallet-->>wallet.js: signedTxn bytes    Flask->>SQLite: Log TX ID

    wallet.js->>Flask API: POST /api/submit_transaction    Flask-->>User: Success + Explorer Link

    Flask API->>Algorand: algod.send_raw_transaction()    

    Algorand-->>Flask API: txId    Note over User,Indexer: Verification Flow

    Flask API-->>wallet.js: {txId}    User->>Flask: Request Verification

    wallet.js->>wallet.js: refreshWalletDashboard()    Flask->>Indexer: Query Transaction

```    Indexer-->>Flask: On-Chain Data

    Flask-->>User: Verified Result

---```



## 🚀 Features---



### 1. **Wallet-First Dashboard**## 🚀 Core Features

The dashboard displays your wallet prominently at the top:

- **Balance Card** — live ALGO balance from AlgoNode API (purple gradient)### 1. **Certificate Verification System**

- **Receive QR** — scannable QR code of your Algorand address

- **Quick Send** — 3-field form for instant ALGO payments#### **What It Does**

- **Token Holdings** — all ASAs held (name, unit, amount)- Students upload academic certificates (PDF/Image)

- **Transaction History** — last 8 txns with type, amount, date, explorer links- System generates SHA-256 hash of the file

- Auto-toggles between "Connect Wallet" CTA and full wallet panel- Hash is stored on Algorand blockchain as transaction note

- QR code generated linking to AlgoExplorer transaction

### 2. **Certificate Verification System**- Anyone can verify certificate authenticity by uploading the file

- Upload PDF/image → SHA-256 hash → stored on Algorand as note

- QR code per certificate linking to Lora Explorer#### **Why It's Needed**

- Delete support via Beaker `certificate_store` contract- Prevents certificate forgery (changing 1 bit changes entire hash)

- Public verification at `/verify` — upload file, hash compared on-chain- Enables instant verification by employers/universities

- Cost: ~0.001 ALGO per certificate- Creates permanent, tamper-proof record

- No central authority needed for verification

### 3. **Decentralized Elections**

- Admin creates elections with candidates#### **Blockchain Logic**

- Students vote once per election, recorded on-chain```python

- Transparent tallying from blockchain data# Simplified flow

- Results verifiable by anyone via Indexerfile_hash = hashlib.sha256(file_content).hexdigest()

note = f"CERT|user:{user_id}|hash:{file_hash}|timestamp:{timestamp}"

### 4. **Group Collaboration & DAO**tx = PaymentTxn(sender=wallet, receiver=wallet, amt=0, note=note.encode())

- Create/join project groups, assign tasks/milestonestx_id = algod_client.send_transaction(signed_tx)

- Task completions logged on-chain as immutable records```

- DAO treasury per group (Beaker `campus_dao` contract)

- Milestone tracking with blockchain-backed proofs#### **Gas Implications**

- **Cost**: ~0.001 ALGO per certificate (~$0.0003 USD)

### 5. **Advanced Wallet Features** (`/wallet/features`)- **Optimization**: Uses 0 ALGO payment-to-self (only network fee)

Four-tab interface:- **Note Field**: 1024 bytes max (sufficient for hash + metadata)

- **Send ALGO** — payment with custom notes

- **Create Token** — fungible ASA with configurable supply/decimals#### **Security Considerations**

- **Mint NFT** — unique achievement badges with IPFS URLs- Hash collision resistance (SHA-256 = 2^256 possibilities)

- **Smart Contract** — deploy & interact with bank contracts- Ownership binding prevents certificate reuse

- Timestamp prevents backdating

### 6. **CampusCoin (CCOIN)**- Public verification without exposing file content

- Custom Algorand Standard Asset: `CampusCoin` / `CCOIN` / 6 decimals / 1B supply

- Deploy via `/api/prepare_campus_coin_deploy`---

- Used for campus rewards, attendance incentives, group payments

- Verify via `/api/campus_coin_info`### 2. **Decentralized Elections**



### 7. **Attendance with Face ID**#### **What It Does**

- Instructor creates session → students check in via webcam- Admin creates elections with candidates

- Face recognition using face-api.js ML models- Students vote once per election

- Attendance percentage analytics per course- Votes recorded on blockchain with encrypted candidate ID

- On-chain attendance records- Results calculated transparently from blockchain data



### 8. **AI Chatbot (CampusBot)**#### **Why It's Needed**

- Gemini 2.0 Flash powered with retries across multiple models- Eliminates vote manipulation

- Queries user's real attendance data, groups, DAO info- Provides public audit trail

- Exponential backoff on rate limits- Prevents double-voting (enforced by smart contract logic)

- Instant, verifiable results

---

#### **Transaction Flow**

## 🏗️ Tech Stack```

Student → Select Candidate → Flask validates eligibility → 

### **Blockchain**Generate vote hash → Submit to Algorand → 

Store TX ID in DB → Update vote count → Display confirmation

| Technology | Purpose |```

|---|---|

| **Algorand TestNet** | Layer-1 blockchain (4.5s finality, ~$0.001/tx) |#### **Example Input/Output**

| **py-algorand-sdk 2.0+** | Build unsigned transactions server-side |```python

| **algosdk.js 2.4.0 (CDN)** | Decode transactions client-side |# Input

| **Pera Wallet Connect 1.5+** | Client-side transaction signing |{

| **Beaker (PyTeal)** | Smart contracts: campus_bank, campus_dao, certificate_store |  "election_id": 5,

| **AlgoKit** | Contract compilation & deployment CLI |  "candidate_id": 12,

| **AlgoNode** | Free RPC (algod + indexer) — no API key needed |  "voter_id": 101

}

### **Backend**

# Blockchain Note

| Technology | Purpose |"VOTE|election:5|voter:101|candidate:ENCRYPTED|timestamp:2026-02-12T20:00:00"

|---|---|

| **Flask 2.3+** | Web framework & REST API |# Output

| **SQLite** | User data, certificates, elections, groups |{

| **Gunicorn** | Production WSGI server |  "success": true,

| **python-dotenv** | Environment variable management |  "tx_id": "XYZABC123...",

| **google-generativeai** | Gemini AI for chatbot |  "explorer_url": "https://testnet.algoexplorer.io/tx/XYZABC123"

}

### **Frontend**```



| Technology | Purpose |---

|---|---|

| **Bootstrap 5.3** | Responsive UI framework |### 3. **Group Collaboration & Milestones**

| **wallet.js (437 lines)** | Full wallet core: balance, history, QR, send, toasts |

| **Pera Wallet bundle** | Webpack-compiled `@perawallet/connect` |#### **What It Does**

| **qrcodejs** | QR code generation for addresses & certificates |- Students create/join project groups

| **Font Awesome 6** | Icons |- Group leads assign tasks and milestones

| **Jinja2** | Server-side templating |- Completions recorded on blockchain

| **face-api.js** | Face recognition ML models |- Transparent contribution tracking



---#### **Smart Contract Logic**

- Uses standardized note format for milestone records

## 📂 Project Structure- Immutable timestamp of achievements

- Queryable via Algorand Indexer

```

campustrust-blockchain/---

│

├── contracts/                     # AlgoKit / Beaker smart contracts### 4. **Advanced Algorand Features**

│   ├── campus_bank.py             # Deposit/withdraw ALGO (Beaker Application)

│   ├── campus_dao.py              # DAO treasury + disburse (Beaker Application)#### **4.1 ALGO Payments**

│   ├── certificate_store.py       # Certificate hash box storage (Beaker Application)- Send ALGO to any address with custom notes

│   ├── campus_coin.py             # CampusCoin ASA deployment helper- Real-time transaction confirmation

│   ├── deploy.py                  # AlgoKit CLI deploy script (--compile / --deploy)- Explorer integration for tracking

│   └── __init__.py

│#### **4.2 ASA (Algorand Standard Asset) Creation**

├── algorand/                      # Blockchain integration layer- Create custom fungible tokens (loyalty points, campus currency)

│   ├── connect.py                 # get_client(), get_indexer(), get_suggested_params()- Configurable supply, decimals, and metadata

│   ├── store_hash.py              # build_note_txn(), submit_signed_txn()- Use cases: Reward systems, stablecoins, governance tokens

│   ├── advanced_features.py       # Unsigned tx builders + submit helpers

│   └── contracts/                 # Original PyTeal source contracts#### **4.3 NFT Minting**

│       ├── simple_bank.py         # PyTeal bank contract- Mint unique NFTs (badges, achievements, certificates)

│       ├── simple_dao.py          # PyTeal DAO contract- IPFS integration for metadata

│       └── certificate_contract.py # PyTeal certificate contract- Permanent ownership records

│

├── utils/                         # Server-side helpers#### **4.4 Smart Contracts (PyTeal)**

│   ├── hash_utils.py              # SHA-256 file hashing- **Simple Bank Demo**: Deposit/withdraw ALGO

│   ├── blockchain_utils.py        # Certificate store/verify/delete (unsigned txn builders)- Stateful contract with global state management

│   ├── rewards.py                 # CampusCoin reward system (unsigned txn builders)- Inner transactions for automated payments

│   └── auth_utils.py              # Authentication helpers

│#### **4.5 Indexer Integration**

├── templates/                     # Jinja2 HTML templates- Query transaction history

│   ├── base.html                  # Layout: navbar, CDN scripts, chatbot widget- Track contract interactions

│   ├── dashboard.html             # Wallet-first dashboard + campus feature tabs- Audit deposit/withdrawal flows

│   ├── wallet_features.html       # Advanced: Send ALGO, Create ASA, Mint NFT, Contracts

│   ├── upload_cert.html           # Certificate upload form---

│   ├── verify_cert.html           # Public certificate verification

│   ├── election.html              # Election listing & voting## 🏗️ Tech Stack

│   ├── create_election.html       # Election creation (admin)

│   ├── attendance_*.html          # Sessions, reports, Face ID check-in### **Blockchain Layer**

│   ├── feedback_*.html            # Forms, results, analytics

│   ├── group_*.html               # Create, detail, discover, admin| Technology | Purpose | Why Chosen | Alternatives |

│   ├── login.html / register.html # Authentication pages|-----------|---------|------------|--------------|

│   ├── setup_face.html            # Face ID registration| **Algorand** | Layer-1 blockchain | ✅ 4.5s finality<br>✅ Low fees (~$0.001/tx)<br>✅ Carbon negative<br>✅ Pure PoS consensus | Ethereum (slower, expensive), Polygon (less decentralized) |

│   └── public_logs.html           # On-chain transaction browser| **PyTeal** | Smart contract language | ✅ Python-based (team expertise)<br>✅ Compiles to TEAL<br>✅ Type safety | Reach (less mature), TEAL (low-level) |

│| **AlgoSDK (Python)** | Blockchain interaction | ✅ Official SDK<br>✅ Comprehensive API<br>✅ Active maintenance | JavaScript SDK (different language) |

├── static/| **AlgoNode** | RPC Provider | ✅ Free tier<br>✅ High reliability<br>✅ TestNet + MainNet | Purestake (rate limits), Local node (maintenance overhead) |

│   ├── css/style.css              # Custom styles + wallet dashboard CSS

│   ├── js/### **Backend**

│   │   ├── wallet.js              # Wallet core v2.0 (connect, balance, history, QR, send)

│   │   ├── perawallet-bundle.js   # Webpack-compiled Pera SDK| Technology | Purpose | Why Chosen | Alternatives |

│   │   ├── chat.js                # Gemini AI chatbot client|-----------|---------|------------|--------------|

│   │   └── script.js              # Legacy utilities| **Flask** | Web framework | ✅ Lightweight<br>✅ Easy integration<br>✅ Rapid prototyping | Django (overkill), FastAPI (async not needed) |

│   └── models/                    # face-api.js ML models for Face ID| **SQLite** | Relational database | ✅ Zero configuration<br>✅ File-based<br>✅ Perfect for MVP | PostgreSQL (deployment complexity), MongoDB (not relational) |

│| **Werkzeug** | Password hashing | ✅ Built into Flask<br>✅ Secure defaults | bcrypt (extra dependency) |

├── tests/

│   ├── test_fixes.py              # Core feature tests (15 tests)### **Frontend**

│   ├── test_wallet.py             # Wallet API tests (7 tests)

│   └── test_analytics.py          # Analytics tests| Technology | Purpose | Why Chosen | Alternatives |

│|-----------|---------|------------|--------------|

├── app.py                         # Main Flask application (~2480 lines)| **Bootstrap 5** | UI framework | ✅ Responsive design<br>✅ Pre-built components<br>✅ Accessibility | TailwindCSS (more config), Material UI (React-focused) |

├── requirements.txt               # Python dependencies| **Jinja2** | Templating | ✅ Flask native<br>✅ Server-side rendering | React (overkill for this project) |

├── package.json                   # Node deps (Pera Wallet SDK, webpack)| **Font Awesome** | Icons | ✅ Comprehensive library<br>✅ CDN delivery | Material Icons (less variety) |

├── webpack.config.js              # Webpack → perawallet-bundle.js

├── pera_entry.js                  # Webpack entry point### **Testing & Deployment**

├── .algokit.toml                  # AlgoKit project config

├── .env.example                   # Environment variable template| Technology | Purpose | Why Chosen |

├── .gitignore                     # Git ignore rules|-----------|---------|------------|

├── Procfile                       # Production deployment (Gunicorn)| **unittest** | Testing framework | ✅ Python standard library<br>✅ No dependencies |

├── system_state.json              # CampusCoin state persistence| **Mock** | Blockchain mocking | ✅ Isolate tests from network<br>✅ Fast execution |

└── README.md                      # This file

```---



---## 📂 Project Structure



## ⚙️ Installation & Setup```

campus-trust/

### **Prerequisites**│

- **Python 3.8+** with pip├── algorand/                      # Blockchain integration layer

- **Node.js 16+** with npm (for webpack / Pera bundle)│   ├── connect.py                 # Algorand client & wallet setup

- **Pera Wallet** mobile app ([iOS](https://apps.apple.com/app/pera-algo-wallet/id1459898525) / [Android](https://play.google.com/store/apps/details?id=com.algorand.android))│   ├── store_hash.py              # Core transaction submission logic

│   ├── advanced_features.py       # ASA, NFT, Smart Contract functions

### **Step 1: Clone & Install**│   ├── deploy_certificate.py      # Certificate contract deployment

│   ├── update_contract.py         # Contract update utility

```bash│   └── contracts/

git clone https://github.com/Helly121/campustrust-blockchain.git│       ├── certificate_contract.py # PyTeal certificate box storage contract

cd campustrust-blockchain│       ├── simple_bank.py         # PyTeal smart contract (deposit/withdraw)

│       ├── simple_dao.py          # PyTeal DAO treasury contract

# Python dependencies│       └── debug_contract.py      # Debug contract utility

pip install -r requirements.txt│

├── utils/                         # Helper utilities

# Node dependencies (Pera Wallet SDK + Webpack)│   ├── hash_utils.py              # SHA-256 file hashing

npm install│   ├── blockchain_utils.py        # Standardized note formatting & cert logic

npm run build│   ├── rewards.py                 # Campus Token reward distribution

```│   └── auth_utils.py              # Authentication helpers

│

### **Step 2: Configure Environment**├── templates/                     # Jinja2 HTML templates

│   ├── base.html                  # Base layout (navbar, footer)

```bash│   ├── dashboard.html             # Main user dashboard

cp .env.example .env│   ├── wallet_features.html       # Advanced blockchain features UI

```│   ├── upload_cert.html           # Certificate submission form

│   ├── verify_cert.html           # Public verification page

Edit `.env`:│   ├── election.html              # Election listing & voting

```bash│   ├── create_election.html       # Election creation (admin)

# Required│   ├── attendance_create.html     # Attendance session creation

FLASK_SECRET_KEY=your-random-secret-key│   ├── attendance_session.html    # Attendance check-in with Face ID

│   ├── attendance_list.html       # Attendance sessions list

# Algorand RPC (defaults to AlgoNode TestNet)│   ├── attendance_report.html     # Attendance analytics

ALGOD_ADDRESS=https://testnet-api.algonode.cloud│   ├── feedback_create.html       # Feedback form creation

INDEXER_ADDRESS=https://testnet-idx.algonode.cloud│   ├── feedback_form.html         # Feedback submission

│   ├── feedback_list.html         # Feedback forms list

# Certificate Store App ID│   ├── feedback_results.html      # Feedback analytics & sentiment

CERT_APP_ID=755556381│   ├── group_create.html          # Student group creation

│   ├── group_admin_create.html    # Admin group creation

# CampusCoin ASA ID (set after deploying via wallet)│   ├── group_detail.html          # Group detail with tasks/milestones/DAO

# CAMPUS_COIN_ID=│   ├── group_discover.html        # Group discovery & search

│   ├── login.html                 # User login

# Optional: Gemini AI chatbot│   ├── register.html              # User registration

# GEMINI_API_KEY=your-key│   ├── setup_face.html            # Face ID registration

│   └── public_logs.html           # Blockchain transaction logs

# Optional: CLI contract deployment only│

# DEPLOYER_MNEMONIC="your 25 word mnemonic"├── static/                        # Static assets

```│   ├── css/style.css              # Custom styles

│   ├── js/

> ⚠️ **No `ALGO_MNEMONIC` needed!** All transaction signing happens in Pera Wallet on the client side.│   │   ├── script.js              # Main JavaScript

│   │   ├── chat.js                # Gemini AI chatbot

### **Step 3: Fund Your Pera Wallet**│   │   ├── wallet.js              # Pera Wallet integration

│   │   └── perawallet-bundle.js   # Pera Wallet SDK bundle

1. Open Pera Wallet → Settings → Developer → Switch to **TestNet**│   └── models/                    # Face recognition ML models

2. Visit [Algorand TestNet Dispenser](https://dispenser.testnet.aws.algorand.com/)│

3. Paste your address → receive free TestNet ALGO├── database/                      # SQLite database (auto-created)

│   └── campus.db                  # Main database file

### **Step 4: Run**│

├── tests/                         # Unit tests

```bash│   ├── test_fixes.py              # Core functionality tests

python app.py│   ├── test_wallet.py             # Wallet feature tests

# → http://127.0.0.1:5000│   └── test_analytics.py          # Analytics tests

```│

├── app.py                         # Main Flask application

1. Register an account at `/register`├── requirements.txt               # Python dependencies

2. Click **Connect Wallet** in the navbar → scan QR with Pera├── .env.example                   # Environment variable template

3. Dashboard shows live balance, receive QR, transaction history├── system_state.json              # Campus Token state persistence

4. Use **Wallet** nav link for advanced features (ASA, NFT, contracts)├── transaction_logs.txt           # File-based audit log

├── package.json                   # Node.js deps (Pera Wallet)

### **Step 5: Deploy Smart Contracts (Optional)**├── webpack.config.js              # Webpack config for JS bundling

└── README.md                      # This file

```bash```

# Compile Beaker contracts to TEAL

python contracts/deploy.py --compile### **How Components Connect**



# Deploy to TestNet (requires DEPLOYER_MNEMONIC in .env)1. **User Request** → `app.py` (Flask routes)

python contracts/deploy.py --deploy2. **Database Query** → `SQLite` via `get_db_connection()`

```3. **Blockchain Action** → `algorand/` modules

4. **Transaction Submission** → `AlgoSDK` → Algorand TestNet

### **Step 6: Deploy CampusCoin (Optional)**5. **Confirmation** → `wait_for_confirmation()` → Update DB

6. **Response** → Render `templates/` with data

1. Connect Pera Wallet on the site

2. POST to `/api/prepare_campus_coin_deploy` with `{sender: "YOUR_ADDRESS"}`---

3. Sign the returned transaction in Pera

4. Submit via `/api/submit_transaction`## ⚙️ Installation & Setup

5. Set the returned Asset ID as `CAMPUS_COIN_ID` in `.env`

### **Prerequisites**

---

- **Python**: 3.8 or higher

## 🔌 API Reference- **pip**: Latest version

- **Git**: For cloning repository

### **Unsigned Transaction Builders**- **Algorand Wallet**: TestNet account with ALGO



All return `{unsigned_txn: base64, ...metadata}`. Sign with Pera, submit via `/api/submit_transaction`.### **Step 1: Clone Repository**



| Endpoint | Method | Body | Description |```bash

|---|---|---|---|git clone https://github.com/Helly121/campustrust-blockchain.git

| `/api/prepare_payment` | POST | `{sender, receiver, amount, note}` | ALGO payment |cd campustrust-blockchain

| `/api/prepare_asset_creation` | POST | `{sender, asset_name, unit_name, total, decimals, url}` | Create ASA |```

| `/api/prepare_nft_minting` | POST | `{sender, asset_name, unit_name, ipfs_url}` | Mint NFT |

| `/api/prepare_bank_deposit` | POST | `{sender, app_id, amount}` | Bank deposit (group txns) |### **Step 2: Install Dependencies**

| `/api/prepare_bank_withdraw` | POST | `{sender, app_id, amount}` | Bank withdraw |

| `/api/prepare_campus_coin_deploy` | POST | `{sender}` | Deploy CampusCoin ASA |```bash

pip install -r requirements.txt

### **Transaction Submission**```



| Endpoint | Method | Body | Returns |**Dependencies:**

|---|---|---|---|```

| `/api/submit_transaction` | POST | `{signed_txn: base64}` or `{signed_txns: [base64]}` | `{txId}` or `{txId, assetId}` |Flask>=2.3.0

py-algorand-sdk>=2.0.0

### **Read-Only**pyteal>=0.24.0              # Optional, for smart contract compilation

python-dotenv>=1.0.0

| Endpoint | Method | Description |google-generativeai>=0.8.0  # For Gemini AI chatbot

|---|---|---|msgpack>=1.0.0

| `/api/campus_coin_info` | GET | CampusCoin ASA details |Werkzeug>=2.3.0

| `/api/chat` | POST | AI chatbot (Gemini) |```



### **Example: Send ALGO from JavaScript**### **Step 3: Set Up Algorand Wallet**



```javascript#### **3.1 Create TestNet Account**

// 1. Build unsigned txn

const resp = await fetch("/api/prepare_payment", {Visit [Algorand Dispenser](https://dispenser.testnet.aws.algorand.com/) and:

    method: "POST",1. Click "Generate Account"

    headers: { "Content-Type": "application/json" },2. **SAVE YOUR 25-WORD MNEMONIC SECURELY** ⚠️

    body: JSON.stringify({ sender: address, receiver: "ABC...", amount: 1.5, note: "lunch" })3. Fund account with TestNet ALGO (free)

});

const { unsigned_txn } = await resp.json();#### **3.2 Configure Wallet**



// 2. Decode & sign with PeraCopy the environment template and fill in your values:

const txnBytes = Uint8Array.from(atob(unsigned_txn), c => c.charCodeAt(0));

const decoded = algosdk.decodeUnsignedTransaction(txnBytes);```bash

const signed = await peraWallet.signTransaction([[{ txn: decoded }]]);cp .env.example .env

```

// 3. Submit

const result = await fetch("/api/submit_transaction", {Edit `.env`:

    method: "POST",

    headers: { "Content-Type": "application/json" },```bash

    body: JSON.stringify({ signed_txn: btoa(String.fromCharCode(...signed[0])) })ALGO_MNEMONIC="your 25 word mnemonic phrase here"

});FLASK_SECRET_KEY=your-random-secret-key

const { txId } = await result.json();GEMINI_API_KEY=your-gemini-api-key    # Optional, for AI chatbot

console.log("Transaction:", txId);```

```

> **🔐 SECURITY WARNING**: 

---> - NEVER commit your `.env` file to Git

> - Use environment variables in production

## 🔐 Smart Contracts (Beaker)> - TestNet mnemonics are for testing only



### **CampusBank** (`contracts/campus_bank.py`)### **Step 4: Initialize Database**

- `deposit()` — accept ALGO via atomic grouped payment + app call

- `withdraw()` — inner transaction sends ALGO to caller (creator only)```bash

- Global state: `Creator` address for access controlpython app.py

```

### **CampusDAO** (`contracts/campus_dao.py`)

- `disburse(recipient, amount)` — distribute funds from DAO treasuryThis automatically creates `database/campus.db` with all tables.

- Creator-controlled access for group treasuries

- Inner transactions for automated payments### **Step 5: Access Application**



### **CertificateStore** (`contracts/certificate_store.py`)```bash

- `add_certificate(hash, owner)` — store cert hash in Algorand box storage# Application runs on http://127.0.0.1:5000

- `delete_certificate(hash)` — remove cert (owner only)```

- `verify_certificate(hash)` — read-only on-chain verification

**Default Admin Credentials:**

### **Security Features**- Username: `admin`

- Access control: only creator can withdraw/disburse- Password: `admin`

- Reentrancy protection: Algorand atomic transactions by design

- Integer overflow protection: PyTeal safe math### **Step 6: Verify Blockchain Connection**

- Fee pooling: inner transactions share fee budget

```bash

---python get_address.py

```

## ⛽ Cost Breakdown

Expected output:

| Operation | Cost (ALGO) | ~USD* |```

|---|---|---|Wallet Address: ABCD1234...

| Certificate upload (note txn) | 0.001 | $0.0003 |Balance: 10.0 ALGO

| Election vote | 0.001 | $0.0003 |```

| ALGO payment | 0.001 | $0.0003 |

| ASA creation | 0.1 | $0.03 |---

| NFT mint | 0.1 | $0.03 |

| Contract deployment | 0.1 | $0.03 |## 🔐 Smart Contract Details

| Bank deposit/withdraw | 0.002 | $0.0006 |

### **Simple Bank Contract** (`algorand/contracts/simple_bank.py`)

*Assuming 1 ALGO ≈ $0.30 USD

#### **Purpose**

---Demonstrates stateful smart contract with:

- Global state management

## 🧪 Testing- Inner transactions

- Access control

```bash- Deposit/withdrawal logic

# Run all tests

python -m unittest discover tests/#### **State Variables**



# Specific suites```python

python tests/test_wallet.py     # 7 wallet API tests# Global State

python tests/test_fixes.py      # 15 core feature testsCreator: Bytes  # Address of contract deployer

python tests/test_analytics.py  # Analytics tests```

```

#### **Functions**

All blockchain calls are mocked — no TestNet ALGO required for testing.

| Function | Type | Description | Access Control |

---|----------|------|-------------|----------------|

| `on_creation` | NoOp | Initialize contract, store creator | Anyone (once) |

## 🌍 Deployment| `deposit` | NoOp | Accept ALGO via grouped payment | Anyone |

| `withdraw` | NoOp | Send ALGO from contract to caller | Creator only |

### **Local Development**| `on_optin` | OptIn | Allow users to opt into contract | Anyone |

```bash| `on_closeout` | CloseOut | Remove user from contract | Anyone |

python app.py

# → http://127.0.0.1:5000 (debug mode)#### **Deposit Flow**

```

```python

### **Production (Heroku / Railway / Render)**# User creates atomic transaction group:

```bash# 1. Payment: User → Contract (X ALGO)

# Procfile already configured:# 2. App Call: "deposit" with no args

# web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 3

# Contract verifies:

# Set env vars in hosting dashboard, then:Assert(Gtxn[0].type_enum() == TxnType.Payment)

git push heroku mainAssert(Gtxn[0].receiver() == Global.current_application_address())

```Assert(Gtxn[0].amount() > Int(0))

Assert(Txn.group_index() == Int(1))  # App call is 2nd in group

### **Rebuild Pera Wallet Bundle**```

```bash

npm run build     # production build (one-time)#### **Withdrawal Flow**

npm run dev       # watch mode for development

``````python

# User calls "withdraw" with amount

### **MainNet Migration**# Contract executes inner transaction:

1. Update `ALGOD_ADDRESS` and `INDEXER_ADDRESS` to mainnet endpoints

2. Fund wallet with real ALGOInnerTxnBuilder.Begin()

3. Redeploy contracts via `contracts/deploy.py --deploy`InnerTxnBuilder.SetFields({

4. Redeploy CampusCoin ASA    TxnField.type_enum: TxnType.Payment,

5. Update `CERT_APP_ID` and `CAMPUS_COIN_ID` in `.env`    TxnField.receiver: Txn.sender(),

    TxnField.amount: withdraw_amount,

---    TxnField.fee: Int(0)  # Pooled fee

})

## 🔐 SecurityInnerTxnBuilder.Submit()

```

| Concern | Mitigation |

|---|---|#### **Security Measures**

| **Private keys** | Never on server — all signing via Pera Wallet |

| **SQL injection** | Parameterized queries throughout |- **Access Control**: Only creator can withdraw (prevents theft)

| **XSS** | Jinja2 auto-escaping enabled |- **Reentrancy Protection**: Algorand's atomic transactions prevent reentrancy

| **CSRF** | Flask session with secret key |- **Overflow Protection**: PyTeal uses safe integer operations

| **Reentrancy** | Algorand atomic transactions prevent by design |- **Fee Pooling**: Inner transactions share fee budget

| **Mnemonic exposure** | No `ALGO_MNEMONIC`; optional `DEPLOYER_MNEMONIC` for CLI only |

| **Rate limiting** | Gemini API retries with exponential backoff |---



---## 📜 Contract Interaction



## 📊 Future Roadmap### **Via Python (AlgoSDK)**



- [ ] Multi-signature wallets for critical transactions```python

- [ ] Delegated voting in electionsfrom algorand.advanced_features import deploy_smart_contract, call_bank_deposit

- [ ] IPFS integration for large file storage

- [ ] React Native mobile app with WalletConnect# Deploy contract

- [ ] MainNet production deploymentresult = deploy_smart_contract(approval_teal, clear_teal)

- [ ] Algorand State Proofs for cross-chain verificationapp_id = result['app_id']  # e.g., 123456

- [ ] Redis caching for frequently accessed data

- [ ] Token-based governance (DAO proposals)# Deposit 5 ALGO

deposit_result = call_bank_deposit(app_id, amount_algo=5.0)

---print(deposit_result['tx_id'])  # Transaction ID

```

## 🤝 Contributing

### **Via Indexer (Query History)**

1. Fork → `git checkout -b feature/your-feature`

2. Follow PEP 8, add tests, update docs```python

3. Commit format: `feat:`, `fix:`, `docs:`, `refactor:`from algorand.advanced_features import get_contract_history

4. Push → Create PR

history = get_contract_history(app_id=123456)

---for tx in history['history']:

    print(f"{tx['action']}: {tx['amount']} ALGO by {tx['user']}")

## 📜 License```



MIT License — see [LICENSE](LICENSE).### **Via AlgoExplorer**



---1. Navigate to `https://testnet.algoexplorer.io/application/{app_id}`

2. View global state, transactions, and inner transactions

## 🙏 Acknowledgments

---

- **Algorand Foundation** — blockchain infrastructure

- **AlgoNode** — free RPC services (no API key needed)## 🧪 Testing

- **Pera Wallet** — client-side signing SDK

- **AlgoKit / Beaker** — smart contract framework### **Run All Tests**

- **Flask Community** — web framework & documentation

- **Google Gemini** — AI chatbot engine```bash

python -m unittest discover tests/

---```



**Built with ❤️ for transparent, decentralized campus management — wallet first.**### **Run Specific Test Suite**


```bash
python tests/test_wallet.py
```

### **Test Coverage**

| Module | Tests | Coverage |
|--------|-------|----------|
| Wallet Features | 7 tests | Payment, ASA, NFT, Contracts |
| Core Fixes | 15 tests | Auth, Elections, Groups |
| Blockchain Utils | Mocked | Hash generation, note formatting |

### **Example Test (Mocked Blockchain)**

```python
@patch('app.send_algo_payment')
def test_wallet_pay(self, mock_pay):
    mock_pay.return_value = {'success': True, 'tx_id': 'TEST_TX'}
    
    response = self.app.post('/wallet/pay', data={
        'receiver': 'TEST_ADDR',
        'amount': '1.0',
        'note': 'Test'
    })
    
    self.assertIn(b'Payment Sent!', response.data)
```

---

## 🌍 Deployment Guide

### **Local Deployment (Development)**

```bash
# Already covered in Installation section
python app.py
```

### **TestNet Deployment (Staging)**

1. **Fund Wallet**: Ensure 10+ ALGO in TestNet wallet
2. **Deploy Contracts**:
   ```bash
   python -c "from algorand.contracts.simple_bank import *; print(approval_program())" > approval.teal
   ```
3. **Run Application**:
   ```bash
   export FLASK_ENV=production
   python app.py
   ```

### **MainNet Deployment (Production)**

> ⚠️ **WARNING**: MainNet uses real ALGO with monetary value

1. **Update RPC**:
   ```python
   # algorand/connect.py
   algod_address = "https://mainnet-api.algonode.cloud"
   ```

2. **Secure Mnemonic**:
   ```bash
   export ALGO_MNEMONIC="your 25 words here"
   ```

3. **Gas Estimation**:
   - Certificate upload: ~0.001 ALGO
   - Election vote: ~0.001 ALGO
   - Smart contract deployment: ~0.1 ALGO
   - ASA creation: ~0.1 ALGO

4. **Deploy with Gunicorn**:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:8000 app:app
   ```

---

## ⛽ Gas Optimization

### **Techniques Used**

1. **0 ALGO Payments**: Use payment-to-self to minimize costs
2. **Note Field Compression**: Compact data format (`|` delimiters)
3. **Batch Transactions**: Group related operations
4. **Fee Pooling**: Smart contracts share fee budget

### **Cost Breakdown**

| Operation | Gas Cost (ALGO) | USD Equivalent* |
|-----------|-----------------|-----------------|
| Certificate Upload | 0.001 | $0.0003 |
| Election Vote | 0.001 | $0.0003 |
| ASA Creation | 0.1 | $0.03 |
| NFT Mint | 0.1 | $0.03 |
| Contract Deployment | 0.1 | $0.03 |
| Contract Interaction | 0.002 | $0.0006 |

*Assuming 1 ALGO = $0.30 USD

---

## 🔐 Security Considerations

### **Threats Mitigated**

| Attack Vector | Mitigation Strategy |
|---------------|---------------------|
| **Reentrancy** | Algorand's atomic transactions prevent reentrancy by design |
| **Integer Overflow** | PyTeal uses safe math operations |
| **Front-Running** | Algorand's 4.5s finality minimizes MEV opportunities |
| **Access Control** | Role-based permissions (Admin, Group Lead, Student) |
| **SQL Injection** | Parameterized queries via SQLite3 |
| **XSS** | Jinja2 auto-escaping enabled |
| **CSRF** | Flask session management with secret key |
| **Private Key Exposure** | Mnemonic stored server-side, never sent to client |

### **Audit Readiness Checklist**

- [x] No hardcoded secrets in repository
- [x] Input validation on all forms
- [x] Parameterized database queries
- [x] HTTPS enforced (production)
- [x] Rate limiting on blockchain calls
- [x] Error handling without stack trace exposure
- [x] Logging of all blockchain transactions
- [ ] Third-party smart contract audit (recommended for MainNet)

---

## 📊 Future Improvements

### **Phase 2: Enhanced Features**
- [ ] **Multi-Signature Wallets**: Require multiple approvals for critical actions
- [ ] **Delegated Voting**: Allow vote delegation in elections
- [ ] **IPFS Integration**: Store large files off-chain with on-chain hashes
- [ ] **Mobile App**: React Native frontend with WalletConnect

### **Phase 3: Scalability**
- [ ] **Algorand State Proofs**: Enable cross-chain verification
- [ ] **Indexer Optimization**: Custom indexer for faster queries
- [ ] **Caching Layer**: Redis for frequently accessed data
- [ ] **Load Balancing**: Horizontal scaling with Nginx

### **Phase 4: Governance**
- [ ] **DAO Structure**: Token-based governance for platform decisions
- [ ] **Proposal System**: On-chain voting for feature requests
- [ ] **Treasury Management**: Community-controlled funds

---

## 🤝 Contribution Guidelines

### **How to Contribute**

1. **Fork Repository**
   ```bash
   git clone https://github.com/Helly121/campustrust-blockchain.git
   cd campustrust-blockchain
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Follow PEP 8 style guide
   - Add tests for new features
   - Update documentation

3. **Run Tests**
   ```bash
   python -m unittest discover tests/
   ```

4. **Commit**
   ```bash
   git commit -m "feat: add XYZ feature"
   ```

   **Commit Format:**
   - `feat:` New feature
   - `fix:` Bug fix
   - `docs:` Documentation
   - `test:` Testing
   - `refactor:` Code restructuring

5. **Push & Create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

---

## 📜 License

This project is licensed under the **MIT License**.

```
MIT License

Copyright (c) 2026 CampusTrust

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```

---

## 🙏 Acknowledgments

- **Algorand Foundation** for blockchain infrastructure
- **AlgoNode** for free RPC services
- **Flask Community** for excellent documentation
- **PyTeal Team** for smart contract tooling

---

## 📞 Support

- **Documentation**: [Algorand Developer Portal](https://developer.algorand.org/)
- **Issues**: [GitHub Issues](https://github.com/Helly121/campustrust-blockchain/issues)
- **Discord**: [Algorand Discord](https://discord.gg/algorand)

---

**Built with ❤️ for transparent, decentralized campus management**