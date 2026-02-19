/**
 * CampusTrust Wallet Core v2.0
 * Full client-side wallet: connect, balance, history, receive QR, send payment.
 * Dependencies (loaded via CDN / webpack bundle in base.html):
 *   - window.algosdk   (CDN)
 *   - window.PeraWalletConnect  (webpack bundle)
 *   - window.QRCode    (CDN)
 */

"use strict";

/* ------------------------------------------------------------------ */
/*  GLOBALS                                                           */
/* ------------------------------------------------------------------ */
let peraWallet = null;
let connectedAccount = null;

const ALGOD_SERVER = "https://testnet-api.algonode.cloud";
const INDEXER_SERVER = "https://testnet-idx.algonode.cloud";
const ALGO_DECIMALS = 6;

/* Lightweight fetch helpers (avoid building full algod/indexer clients) */
async function algodGet(path) {
    const r = await fetch(`${ALGOD_SERVER}${path}`, { headers: { "Content-Type": "application/json" } });
    if (!r.ok) throw new Error(`Algod ${path}: ${r.status}`);
    return r.json();
}
async function indexerGet(path) {
    const r = await fetch(`${INDEXER_SERVER}${path}`, { headers: { "Content-Type": "application/json" } });
    if (!r.ok) throw new Error(`Indexer ${path}: ${r.status}`);
    return r.json();
}

/* ------------------------------------------------------------------ */
/*  INIT                                                              */
/* ------------------------------------------------------------------ */
document.addEventListener("DOMContentLoaded", () => {
    // --- Pera Wallet init ---
    if (typeof PeraWalletConnect === "undefined") {
        console.error("PeraWalletConnect library not loaded!");
        return;
    }
    try {
        const PeraClass =
            typeof PeraWalletConnect.PeraWalletConnect === "function"
                ? PeraWalletConnect.PeraWalletConnect
                : typeof PeraWalletConnect === "function"
                    ? PeraWalletConnect
                    : null;
        if (!PeraClass) throw new Error("PeraWalletConnect class not found");
        peraWallet = new PeraClass({ chainId: 416002 }); // TestNet
    } catch (e) {
        console.error("Failed to init PeraWallet:", e);
        return;
    }

    // Reconnect persisted session
    peraWallet
        .reconnectSession()
        .then((accounts) => {
            if (accounts.length) {
                connectedAccount = accounts[0];
                onWalletConnected(connectedAccount);
            }
        })
        .catch(() => { });

    // Navbar connect button
    const connectBtn = document.getElementById("connect-wallet-btn");
    if (connectBtn) connectBtn.addEventListener("click", handleConnectWallet);

    // Show wallet address in navbar account dropdown
    const navAddrEl = document.getElementById("navbar-wallet-addr");
    if (navAddrEl && connectedAccount) {
        navAddrEl.textContent = `${connectedAccount.slice(0, 8)}…${connectedAccount.slice(-6)}`;
    }
});

/* ------------------------------------------------------------------ */
/*  CONNECT / DISCONNECT                                              */
/* ------------------------------------------------------------------ */
function handleConnectWallet(e) {
    if (e) e.preventDefault();
    if (!peraWallet) return;

    peraWallet
        .connect()
        .then((accounts) => {
            peraWallet.connector?.on("disconnect", handleDisconnectWallet);
            connectedAccount = accounts[0];
            onWalletConnected(connectedAccount);
        })
        .catch((err) => {
            if (err?.data?.type !== "CONNECT_MODAL_CLOSED") {
                console.error("Connection error:", err);
            }
        });
}

function handleDisconnectWallet() {
    peraWallet.disconnect().catch(() => { });
    connectedAccount = null;
    updateNavbarButton(null);
    clearDashboardWallet();
}

/* ------------------------------------------------------------------ */
/*  ON CONNECTED – refresh everything                                 */
/* ------------------------------------------------------------------ */
async function onWalletConnected(address) {
    updateNavbarButton(address);
    // If dashboard wallet panel exists, populate it
    await refreshWalletDashboard(address);
}

/* ------------------------------------------------------------------ */
/*  NAVBAR BUTTON                                                     */
/* ------------------------------------------------------------------ */
function updateNavbarButton(address) {
    const btn = document.getElementById("connect-wallet-btn");
    if (!btn) return;

    if (address) {
        btn.innerHTML = `<img src="https://explorer.perawallet.app/favicon.ico" alt="Pera" style="width:20px;height:20px;margin-right:8px"> ${address.slice(0, 6)}…${address.slice(-4)}`;
        btn.removeEventListener("click", handleConnectWallet);
        btn.addEventListener("click", handleDisconnectWallet);
        btn.classList.remove("btn-pera", "btn-success");
        btn.classList.add("btn-pera-connected");
        btn.title = "Click to disconnect";
    } else {
        btn.innerHTML = `<img src="https://explorer.perawallet.app/favicon.ico" alt="Pera" style="width:20px;height:20px;margin-right:8px"> Connect Wallet`;
        btn.removeEventListener("click", handleDisconnectWallet);
        btn.addEventListener("click", handleConnectWallet);
        btn.classList.remove("btn-pera-connected", "btn-success");
        btn.classList.add("btn-pera");
        btn.title = "Connect Pera Wallet";
    }
}

/* ------------------------------------------------------------------ */
/*  BALANCE FETCHER                                                   */
/* ------------------------------------------------------------------ */
async function fetchAccountInfo(address) {
    try {
        const data = await algodGet(`/v2/accounts/${address}`);
        const algoBalance = (data.amount || 0) / Math.pow(10, ALGO_DECIMALS);
        const minBalance = (data["min-balance"] || 100000) / Math.pow(10, ALGO_DECIMALS);
        // Parse ASA holdings
        const assets = (data.assets || []).map((a) => ({
            assetId: a["asset-id"],
            amount: a.amount,
            isFrozen: a["is-frozen"],
        }));
        return { algoBalance, minBalance, assets, raw: data };
    } catch (e) {
        console.error("fetchAccountInfo error:", e);
        return { algoBalance: 0, minBalance: 0.1, assets: [], raw: null };
    }
}

async function fetchAssetDetails(assetId) {
    try {
        const data = await algodGet(`/v2/assets/${assetId}`);
        const p = data.params || {};
        return {
            name: p.name || `ASA #${assetId}`,
            unitName: p["unit-name"] || "",
            decimals: p.decimals || 0,
            total: p.total || 0,
            url: p.url || "",
        };
    } catch {
        return { name: `ASA #${assetId}`, unitName: "", decimals: 0, total: 0, url: "" };
    }
}

/* ------------------------------------------------------------------ */
/*  TRANSACTION HISTORY (Indexer)                                     */
/* ------------------------------------------------------------------ */
async function fetchRecentTransactions(address, limit = 10) {
    try {
        const data = await indexerGet(
            `/v2/accounts/${address}/transactions?limit=${limit}`
        );
        return (data.transactions || []).map((tx) => {
            const isOutgoing = tx.sender === address;
            let otherParty = isOutgoing
                ? tx["payment-transaction"]?.receiver || tx["asset-transfer-transaction"]?.receiver || "Contract"
                : tx.sender;
            let amount = 0;
            let unit = "ALGO";
            if (tx["tx-type"] === "pay") {
                amount = (tx["payment-transaction"]?.amount || 0) / 1e6;
            } else if (tx["tx-type"] === "axfer") {
                amount = tx["asset-transfer-transaction"]?.amount || 0;
                unit = `ASA #${tx["asset-transfer-transaction"]?.["asset-id"] || "?"}`;
            } else if (tx["tx-type"] === "appl") {
                unit = "App Call";
                amount = 0;
            }
            return {
                id: tx.id,
                type: tx["tx-type"],
                isOutgoing,
                otherParty,
                amount,
                unit,
                roundTime: tx["round-time"],
                fee: (tx.fee || 0) / 1e6,
            };
        });
    } catch (e) {
        console.error("fetchRecentTransactions error:", e);
        return [];
    }
}

/* ------------------------------------------------------------------ */
/*  DASHBOARD WALLET PANEL (rendered in dashboard.html)               */
/* ------------------------------------------------------------------ */
async function refreshWalletDashboard(address) {
    const panel = document.getElementById("wallet-dashboard-panel");
    if (!panel || !address) return;

    // Show the panel
    panel.classList.remove("d-none");
    const placeholder = document.getElementById("wallet-connect-placeholder");
    if (placeholder) placeholder.classList.add("d-none");

    // Show address
    const addrEl = document.getElementById("wallet-address-display");
    if (addrEl) addrEl.textContent = `${address.slice(0, 8)}…${address.slice(-8)}`;

    const fullAddrEl = document.getElementById("wallet-address-full");
    if (fullAddrEl) fullAddrEl.value = address;

    // QR Code for receiving
    const qrContainer = document.getElementById("wallet-receive-qr");
    if (qrContainer && typeof QRCode !== "undefined") {
        qrContainer.innerHTML = "";
        new QRCode(qrContainer, {
            text: address,
            width: 150,
            height: 150,
            colorDark: "#1e293b",
            colorLight: "#ffffff",
        });
    }

    // Fetch balance
    const balEl = document.getElementById("wallet-algo-balance");
    const assetListEl = document.getElementById("wallet-asset-list");
    if (balEl) balEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

    const info = await fetchAccountInfo(address);
    if (balEl) balEl.textContent = info.algoBalance.toFixed(6);

    // Assets
    if (assetListEl) {
        if (info.assets.length === 0) {
            assetListEl.innerHTML = '<div class="text-muted small">No tokens held</div>';
        } else {
            assetListEl.innerHTML = "";
            // Fetch details for first 10 assets
            const toShow = info.assets.slice(0, 10);
            for (const a of toShow) {
                const details = await fetchAssetDetails(a.assetId);
                const humanAmount = a.amount / Math.pow(10, details.decimals);
                const row = document.createElement("div");
                row.className = "d-flex justify-content-between align-items-center py-1 border-bottom";
                row.innerHTML = `
                    <div>
                        <span class="fw-semibold">${details.unitName || details.name}</span>
                        <span class="text-muted small ms-1">#${a.assetId}</span>
                    </div>
                    <span class="fw-bold">${humanAmount.toLocaleString()}</span>
                `;
                assetListEl.appendChild(row);
            }
            if (info.assets.length > 10) {
                const more = document.createElement("div");
                more.className = "text-muted small mt-1";
                more.textContent = `+${info.assets.length - 10} more assets`;
                assetListEl.appendChild(more);
            }
        }
    }

    // Transaction history
    await refreshTxHistory(address);
}

async function refreshTxHistory(address) {
    const tbody = document.getElementById("wallet-tx-tbody");
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="5" class="text-center"><i class="fas fa-spinner fa-spin"></i> Loading…</td></tr>';

    const txs = await fetchRecentTransactions(address, 8);
    if (txs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No transactions yet</td></tr>';
        return;
    }

    tbody.innerHTML = "";
    for (const tx of txs) {
        const tr = document.createElement("tr");
        const date = tx.roundTime
            ? new Date(tx.roundTime * 1000).toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })
            : "Pending";
        const icon = tx.isOutgoing ? "fa-arrow-up text-danger" : "fa-arrow-down text-success";
        const sign = tx.isOutgoing ? "-" : "+";
        const otherAddr = tx.otherParty
            ? `${tx.otherParty.slice(0, 6)}…${tx.otherParty.slice(-4)}`
            : "—";
        tr.innerHTML = `
            <td><i class="fas ${icon} me-1"></i>${tx.isOutgoing ? "Sent" : "Received"}</td>
            <td class="fw-semibold">${sign}${tx.amount} ${tx.unit}</td>
            <td class="text-muted small">${otherAddr}</td>
            <td class="text-muted small">${date}</td>
            <td><a href="https://lora.algokit.io/testnet/transaction/${tx.id}" target="_blank" class="text-primary small"><i class="fas fa-external-link-alt"></i></a></td>
        `;
        tbody.appendChild(tr);
    }
}

/* ------------------------------------------------------------------ */
/*  QUICK SEND (from dashboard)                                       */
/* ------------------------------------------------------------------ */
async function quickSendAlgo() {
    if (!connectedAccount || !peraWallet) {
        alert("Please connect your Pera Wallet first!");
        return;
    }
    const receiverInput = document.getElementById("quick-send-receiver");
    const amountInput = document.getElementById("quick-send-amount");
    const noteInput = document.getElementById("quick-send-note");
    const btn = document.getElementById("quick-send-btn");

    const receiver = receiverInput?.value.trim();
    const amount = parseFloat(amountInput?.value);
    const note = noteInput?.value.trim() || "";

    if (!receiver || receiver.length !== 58) {
        alert("Enter a valid 58-character Algorand address");
        return;
    }
    if (!amount || amount <= 0) {
        alert("Enter a valid amount");
        return;
    }

    const origText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Preparing…';

    try {
        // 1. Ask server to build unsigned txn
        const resp = await fetch("/api/prepare_payment", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ sender: connectedAccount, receiver, amount, note }),
        });
        const data = await resp.json();
        if (data.error) throw new Error(data.error);

        // 2. Decode & sign with Pera
        const txnBytes = Uint8Array.from(atob(data.unsigned_txn), (c) => c.charCodeAt(0));
        const decodedTxn = algosdk.decodeUnsignedTransaction(txnBytes);
        btn.innerHTML = '<i class="fas fa-pen-nib fa-spin me-2"></i>Sign in Pera…';
        const signedTxns = await peraWallet.signTransaction([[{ txn: decodedTxn }]]);

        // 3. Submit
        btn.innerHTML = '<i class="fas fa-broadcast-tower fa-spin me-2"></i>Submitting…';
        const submitResp = await fetch("/api/submit_transaction", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ signed_txn: arrayToBase64(signedTxns[0]) }),
        });
        const submitData = await submitResp.json();
        if (submitData.error) throw new Error(submitData.error);

        // Show success
        showToast(`✅ Sent ${amount} ALGO — Tx: ${submitData.txId.slice(0, 12)}…`, "success");

        // Reset form
        receiverInput.value = "";
        amountInput.value = "";
        noteInput.value = "";

        // Refresh dashboard data
        await refreshWalletDashboard(connectedAccount);
    } catch (err) {
        console.error("quickSendAlgo error:", err);
        showToast(`❌ ${err.message}`, "danger");
    } finally {
        btn.disabled = false;
        btn.innerHTML = origText;
    }
}

/* ------------------------------------------------------------------ */
/*  COPY & UTILITY                                                    */
/* ------------------------------------------------------------------ */
function copyWalletAddress() {
    const addr = document.getElementById("wallet-address-full")?.value;
    if (!addr) return;
    navigator.clipboard.writeText(addr).then(() => {
        showToast("Address copied!", "info");
    });
}

function arrayToBase64(uint8arr) {
    let binary = "";
    for (let i = 0; i < uint8arr.length; i++) binary += String.fromCharCode(uint8arr[i]);
    return btoa(binary);
}

function showToast(message, type = "info") {
    const container = document.getElementById("toast-container") || createToastContainer();
    const toast = document.createElement("div");
    toast.className = `alert alert-${type} alert-dismissible fade show shadow-sm mb-2`;
    toast.setAttribute("role", "alert");
    toast.innerHTML = `${message}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 6000);
}

function createToastContainer() {
    const c = document.createElement("div");
    c.id = "toast-container";
    c.style.cssText = "position:fixed;top:80px;right:20px;z-index:9999;width:360px;";
    document.body.appendChild(c);
    return c;
}

function clearDashboardWallet() {
    const panel = document.getElementById("wallet-dashboard-panel");
    if (panel) panel.classList.add("d-none");
    const placeholder = document.getElementById("wallet-connect-placeholder");
    if (placeholder) placeholder.classList.remove("d-none");
}

/* ------------------------------------------------------------------ */
/*  WALLET-ONLY AUTHENTICATION (Sign-In With Algorand)                */
/* ------------------------------------------------------------------ */

/**
 * Full wallet login flow:
 * 1. Connect Pera Wallet
 * 2. Request challenge from server (unsigned zero-ALGO self-pay with nonce)
 * 3. Sign challenge tx with Pera
 * 4. Send signed tx to server for verification
 * 5. Server creates session → redirect to dashboard
 */
async function walletLogin() {
    const statusEl = document.getElementById("wallet-login-status");
    const btnEl = document.getElementById("wallet-login-btn");

    function setStatus(msg, type = "info") {
        if (statusEl) {
            statusEl.className = `alert alert-${type} mt-3`;
            statusEl.innerHTML = msg;
            statusEl.classList.remove("d-none");
        }
    }

    if (btnEl) {
        btnEl.disabled = true;
        btnEl.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Connecting Wallet…';
    }

    try {
        // 1. Connect Pera Wallet
        if (!peraWallet) {
            throw new Error("Pera Wallet SDK not loaded. Please refresh the page.");
        }

        let accounts;
        try {
            accounts = await peraWallet.connect();
        } catch (err) {
            if (err?.data?.type === "CONNECT_MODAL_CLOSED") {
                throw new Error("Wallet connection cancelled.");
            }
            throw err;
        }

        const address = accounts[0];
        if (!address) throw new Error("No account selected.");

        setStatus(`<i class="fas fa-wallet me-2"></i>Connected: ${address.slice(0, 6)}…${address.slice(-4)}. Requesting challenge…`, "info");
        if (btnEl) btnEl.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Requesting Challenge…';

        // 2. Get challenge from server
        const challengeResp = await fetch("/api/auth/challenge", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ address }),
        });
        const challengeData = await challengeResp.json();
        if (challengeData.error) throw new Error(challengeData.error);

        setStatus(`<i class="fas fa-pen-nib me-2"></i>Please sign the login message in Pera Wallet…`, "warning");
        if (btnEl) btnEl.innerHTML = '<i class="fas fa-pen-nib fa-spin me-2"></i>Sign in Pera…';

        // 3. Decode unsigned tx and sign with Pera
        const txnBytes = Uint8Array.from(atob(challengeData.unsigned_txn), (c) => c.charCodeAt(0));
        const decodedTxn = algosdk.decodeUnsignedTransaction(txnBytes);

        const signedTxns = await peraWallet.signTransaction([[{ txn: decodedTxn }]]);

        const signedB64 = arrayToBase64(signedTxns[0]);

        setStatus(`<i class="fas fa-shield-alt me-2"></i>Verifying signature…`, "info");
        if (btnEl) btnEl.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Verifying…';

        // 4. Send signed tx to server for verification
        const verifyResp = await fetch("/api/auth/verify", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ address, signed_txn: signedB64 }),
        });
        const verifyData = await verifyResp.json();

        if (verifyData.success) {
            setStatus(`<i class="fas fa-check-circle me-2"></i>Login successful! Redirecting…`, "success");
            // Store the connected account
            connectedAccount = address;
            // Redirect to dashboard
            setTimeout(() => {
                window.location.href = "/dashboard";
            }, 800);
        } else {
            throw new Error(verifyData.error || "Verification failed");
        }

    } catch (err) {
        console.error("walletLogin error:", err);
        const msg = err.message || "Login failed. Please try again.";
        setStatus(`<i class="fas fa-exclamation-triangle me-2"></i>${msg}`, "danger");
        if (btnEl) {
            btnEl.disabled = false;
            btnEl.innerHTML = '<img src="https://explorer.perawallet.app/favicon.ico" alt="Pera" style="width:24px;height:24px;margin-right:10px"> Login with Pera Wallet';
        }
    }
}

/**
 * Wallet logout: disconnect Pera + clear server session
 */
async function walletLogout() {
    try {
        if (peraWallet) await peraWallet.disconnect().catch(() => {});
    } catch (_) {}
    connectedAccount = null;
    window.location.href = "/logout";
}
