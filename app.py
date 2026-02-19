from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
import os
import sqlite3
import hashlib
import datetime
import time
from werkzeug.utils import secure_filename
from utils.hash_utils import get_file_hash
from algorand.store_hash import store_on_chain
from utils.blockchain_utils import (
    record_attendance_on_chain,
    record_feedback_on_chain,
    record_group_task_on_chain,
    record_group_milestone_on_chain,
    store_certificate_hash,
    verify_certificate_on_chain,
    delete_certificate_on_chain
)
import base64
from algosdk import encoding as algo_encoding
from algosdk.transaction import PaymentTxn
from algorand.connect import get_client, get_suggested_params
from algorand.advanced_features import (
    build_payment_txn, build_asa_create_txn, build_nft_mint_txn,
    build_deploy_contract_txn, build_bank_deposit_txns, build_bank_withdraw_txn,
    get_contract_history, compile_program,
    submit_signed_transaction, submit_signed_group,
    build_lockbox_deploy_txn,
)
from utils.rewards import ensure_campus_token, distribute_reward, generate_student_wallet, opt_in_asset, TOKEN_UNIT
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

try:
    from contracts.campus_bank import app as bank_beaker_app
    from contracts.campus_dao import app as dao_beaker_app
except Exception:
    bank_beaker_app = None
    dao_beaker_app = None
    print("Warning: Could not import Beaker contracts. Make sure beaker-pyteal is installed.")

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'super-secret-key-change-in-production')
UPLOAD_FOLDER = 'uploads/certificates'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db_connection():
    db_path = os.path.join(app.root_path, 'database', 'campus.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        password_hash TEXT DEFAULT '',
        role TEXT DEFAULT 'student',
        wallet_address TEXT UNIQUE,
        wallet_mnemonic TEXT,
        face_descriptor TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Simple migration for existing DB
    try:
        c.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE users ADD COLUMN face_descriptor TEXT")
    except sqlite3.OperationalError:
        pass # Column likely exists
    
    c.execute('''CREATE TABLE IF NOT EXISTS certificates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        filename TEXT,
        cert_hash TEXT UNIQUE,
        tx_id TEXT,
        asset_id INTEGER,
        upload_date TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS elections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        description TEXT,
        created_by INTEGER,
        created_date TEXT,
        status TEXT DEFAULT 'active'
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        election_id INTEGER,
        name TEXT,
        FOREIGN KEY(election_id) REFERENCES elections(id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        election_id INTEGER,
        user_id INTEGER,
        candidate_id INTEGER,
        tx_id TEXT,
        vote_date TEXT,
        UNIQUE(election_id, user_id)
    )''')

    # Attendance Tracking Tables
    c.execute('''CREATE TABLE IF NOT EXISTS attendance_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_by INTEGER NOT NULL,
        course_code TEXT,
        session_date DATE,
        session_time TIME,
        status TEXT DEFAULT 'active',
        created_at TEXT,
        FOREIGN KEY(created_by) REFERENCES users(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS attendance_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        marked_by INTEGER,
        status TEXT DEFAULT 'absent',
        check_in_time TEXT,
        marked_at TEXT,
        tx_id TEXT,
        FOREIGN KEY(session_id) REFERENCES attendance_sessions(id),
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(marked_by) REFERENCES users(id),
        UNIQUE(session_id, user_id)
    )''')

    # Feedback Collection Tables
    c.execute('''CREATE TABLE IF NOT EXISTS feedback_forms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_by INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        form_type TEXT DEFAULT 'feedback',
        is_active INTEGER DEFAULT 1,
        allow_anonymous INTEGER DEFAULT 1,
        created_date TEXT,
        closed_date TEXT,
        FOREIGN KEY(created_by) REFERENCES users(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS feedback_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        form_id INTEGER NOT NULL,
        question_text TEXT NOT NULL,
        question_type TEXT DEFAULT 'text',
        required INTEGER DEFAULT 0,
        question_order INTEGER,
        FOREIGN KEY(form_id) REFERENCES feedback_forms(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS feedback_responses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        form_id INTEGER NOT NULL,
        user_id INTEGER,
        question_id INTEGER NOT NULL,
        response_text TEXT,
        is_anonymous INTEGER DEFAULT 0,
        response_date TEXT,
        tx_id TEXT,
        FOREIGN KEY(form_id) REFERENCES feedback_forms(id),
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(question_id) REFERENCES feedback_questions(id)
    )''')

    # Group Coordination Tables
    c.execute('''CREATE TABLE IF NOT EXISTS groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        creation_type TEXT DEFAULT 'admin_created',
        created_by INTEGER NOT NULL,
        created_date TEXT,
        status TEXT DEFAULT 'active',
        category TEXT,
        FOREIGN KEY(created_by) REFERENCES users(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS group_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        role TEXT DEFAULT 'member',
        status TEXT DEFAULT 'accepted',
        joined_date TEXT,
        FOREIGN KEY(group_id) REFERENCES groups(id),
        FOREIGN KEY(user_id) REFERENCES users(id),
        UNIQUE(group_id, user_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS group_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        assigned_to INTEGER,
        due_date TEXT,
        status TEXT DEFAULT 'pending',
        created_date TEXT,
        completed_date TEXT,
        tx_id TEXT,
        FOREIGN KEY(group_id) REFERENCES groups(id),
        FOREIGN KEY(assigned_to) REFERENCES users(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS group_milestones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        target_date TEXT,
        completed_date TEXT,
        proof_url TEXT,
        tx_id TEXT,
        FOREIGN KEY(group_id) REFERENCES groups(id)
    )''')

    # Transaction Logs Table
    c.execute('''CREATE TABLE IF NOT EXISTS transaction_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        details TEXT,
        tx_id TEXT,
        timestamp TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')

    # DAO Proposals Table
    c.execute('''CREATE TABLE IF NOT EXISTS group_proposals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        amount_algo REAL DEFAULT 0,
        recipient_address TEXT,
        status TEXT DEFAULT 'pending',
        yes_votes INTEGER DEFAULT 0,
        no_votes INTEGER DEFAULT 0,
        tx_id TEXT,
        created_date TEXT,
        FOREIGN KEY(group_id) REFERENCES groups(id)
    )''')

    # Proposal Votes Table
    c.execute('''CREATE TABLE IF NOT EXISTS proposal_votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proposal_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        choice TEXT NOT NULL,
        FOREIGN KEY(proposal_id) REFERENCES group_proposals(id),
        FOREIGN KEY(user_id) REFERENCES users(id),
        UNIQUE(proposal_id, user_id)
    )''')

    # ── Lockbox / Time-Locked Savings Goals ──
    c.execute('''CREATE TABLE IF NOT EXISTS lockbox_goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        group_id INTEGER,
        name TEXT NOT NULL,
        target_amount INTEGER DEFAULT 0,
        deposited_amount INTEGER DEFAULT 0,
        unlock_time INTEGER NOT NULL,
        app_id INTEGER,
        status TEXT DEFAULT 'locked',
        tx_id TEXT,
        created_date TEXT,
        released_date TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(group_id) REFERENCES groups(id)
    )''')

    # ── Privacy-Aware Receipts ──
    c.execute('''CREATE TABLE IF NOT EXISTS privacy_receipts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        json_data TEXT,
        data_hash TEXT NOT NULL,
        tx_id TEXT,
        created_date TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')

    # Migrations for columns added after initial schema
    try:
        c.execute("ALTER TABLE attendance_sessions ADD COLUMN end_time TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        c.execute("ALTER TABLE feedback_responses ADD COLUMN comments TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        c.execute("ALTER TABLE groups ADD COLUMN dao_app_id INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        c.execute("ALTER TABLE groups ADD COLUMN treasury_address TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Create default admin (wallet-based: admin wallet can be set via ADMIN_WALLET env var)
    admin_wallet = os.environ.get('ADMIN_WALLET', 'ADMIN_PLACEHOLDER')
    c.execute("INSERT OR IGNORE INTO users (student_id, name, password_hash, role, wallet_address) VALUES (?, 'Administrator', '', 'admin', ?)",
              (admin_wallet, admin_wallet))
    
    conn.commit()
    conn.close()

create_tables()

# ── Nonce store for wallet auth challenges ──
# In-memory store: {address: {"nonce": str, "timestamp": float, "unsigned_txn": str}}
_auth_challenges = {}
AUTH_NONCE_EXPIRY = 300  # 5 minutes

def log_transaction(user_id, action, details, tx_id=None):
    try:
        timestamp = datetime.datetime.now().isoformat()
        
        # 1. DB Logging
        conn = get_db_connection()
        conn.execute('''INSERT INTO transaction_logs 
                       (user_id, action, details, tx_id, timestamp)
                       VALUES (?, ?, ?, ?, ?)''',
                    (user_id, action, details, tx_id, timestamp))
        conn.commit()
        conn.close()
        
        # 2. File Logging
        log_entry = f"[{timestamp}] User: {user_id} | Action: {action} | Details: {details} | TX: {tx_id or 'N/A'}\n"
        # Use absolute path or relative to CWD
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'transaction_logs.txt')
        with open(log_path, 'a') as f:
            f.write(log_entry)
            
    except Exception as e:
        print(f"Logging failed: {e}")

def get_current_user():
    if 'user_id' not in session:
        return None
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    conn.close()
    return user

def wallet_required(f):
    """Decorator: redirect to wallet login if not authenticated."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return redirect(url_for('wallet_login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator: require admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return redirect(url_for('wallet_login'))
        if user['role'] != 'admin':
            flash('Admin access required.')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def utility_processor():
    from utils.rewards import TOKEN_UNIT
    return dict(TOKEN_UNIT=TOKEN_UNIT)

# ══════════════════════════════════════════════════════════════════════
#  WALLET-ONLY AUTHENTICATION (Sign-In With Algorand)
# ══════════════════════════════════════════════════════════════════════

@app.route('/login')
@app.route('/wallet-login')
def wallet_login():
    """Wallet login page — connect Pera Wallet to authenticate."""
    if get_current_user():
        return redirect(url_for('dashboard'))
    return render_template('wallet_login.html')

@app.route('/api/auth/challenge', methods=['POST'])
def auth_challenge():
    """Generate a challenge: unsigned zero-ALGO self-payment with random nonce as note.
    The user signs this tx with Pera to prove wallet ownership — no on-chain cost."""
    data = request.json or {}
    address = data.get('address', '').strip()

    if not address or len(address) != 58:
        return jsonify({'error': 'Valid 58-character Algorand address required'}), 400

    # Validate address checksum
    try:
        algo_encoding.decode_address(address)
    except Exception:
        return jsonify({'error': 'Invalid Algorand address checksum'}), 400

    # Generate random nonce
    nonce = base64.b64encode(os.urandom(32)).decode()
    message = f"CampaFi Login\nDomain: {request.host}\nWallet: {address}\nNonce: {nonce}"

    try:
        # Build unsigned zero-ALGO self-payment with challenge as note
        client = get_client()
        params = get_suggested_params()
        txn = PaymentTxn(
            sender=address,
            sp=params,
            receiver=address,
            amt=0,
            note=message.encode()
        )
        # Encode to base64 msgpack (msgpack_encode already returns base64 string)
        unsigned_b64 = algo_encoding.msgpack_encode(txn)

        # Store challenge server-side (keyed by address)
        _auth_challenges[address] = {
            'nonce': nonce,
            'message': message,
            'timestamp': time.time(),
            'unsigned_txn': unsigned_b64,
        }

        return jsonify({
            'nonce': nonce,
            'message': message,
            'unsigned_txn': unsigned_b64,
        })

    except Exception as e:
        print(f"Auth challenge error: {e}")
        return jsonify({'error': f'Failed to build challenge: {str(e)}'}), 500

@app.route('/api/auth/verify', methods=['POST'])
def auth_verify():
    """Verify the signed challenge transaction. If valid, create session.
    Auto-creates user on first login."""
    data = request.json or {}
    address = data.get('address', '').strip()
    signed_txn_b64 = data.get('signed_txn', '').strip()

    if not address or not signed_txn_b64:
        return jsonify({'error': 'Address and signed_txn required'}), 400

    # Check challenge exists and hasn't expired
    challenge = _auth_challenges.get(address)
    if not challenge:
        return jsonify({'error': 'No pending challenge. Request a new one.'}), 400

    if time.time() - challenge['timestamp'] > AUTH_NONCE_EXPIRY:
        _auth_challenges.pop(address, None)
        return jsonify({'error': 'Challenge expired. Request a new one.'}), 400

    try:
        # Decode the signed transaction (msgpack_decode expects base64 string)
        signed_txn = algo_encoding.msgpack_decode(signed_txn_b64)

        # Verify the transaction was signed by the claimed address
        # The signed transaction object contains the sender and the signature
        txn_obj = signed_txn.transaction if hasattr(signed_txn, 'transaction') else signed_txn.dictify()

        # Extract sender from the signed transaction
        if hasattr(signed_txn, 'transaction'):
            sender = signed_txn.transaction.sender
        else:
            sender = address  # fallback

        # Verify sender matches claimed address
        if sender != address:
            return jsonify({'error': 'Transaction sender does not match claimed address'}), 401

        # Verify the note contains our challenge
        if hasattr(signed_txn, 'transaction'):
            note = signed_txn.transaction.note
        else:
            note = None

        if note:
            note_str = note.decode('utf-8') if isinstance(note, bytes) else note
            if challenge['nonce'] not in note_str:
                return jsonify({'error': 'Challenge nonce mismatch'}), 401
        else:
            return jsonify({'error': 'Transaction missing challenge note'}), 401

        # Clear the challenge (one-time use)
        _auth_challenges.pop(address, None)

        # Find or create user
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE wallet_address = ?', (address,)).fetchone()

        if not user:
            # First-time login: auto-create user
            # Use truncated address as student_id and display name
            short_addr = f"{address[:6]}...{address[-4:]}"
            conn.execute(
                'INSERT INTO users (student_id, name, password_hash, role, wallet_address) VALUES (?, ?, ?, ?, ?)',
                (address, short_addr, '', 'student', address)
            )
            conn.commit()
            user = conn.execute('SELECT * FROM users WHERE wallet_address = ?', (address,)).fetchone()
            log_transaction(user['id'], 'WALLET_REGISTER', f'First login via wallet: {short_addr}')

        conn.close()

        # Set session
        session['user_id'] = user['id']
        session['wallet_address'] = address

        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'name': user['name'],
                'role': user['role'],
                'wallet_address': address,
            }
        })

    except Exception as e:
        print(f"Auth verify error: {e}")
        return jsonify({'error': f'Verification failed: {str(e)}'}), 400

@app.route('/api/auth/status', methods=['GET'])
def auth_status():
    """Check current auth status."""
    user = get_current_user()
    if user:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': user['id'],
                'name': user['name'],
                'role': user['role'],
                'wallet_address': user['wallet_address'],
            }
        })
    return jsonify({'authenticated': False})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('wallet_login'))

# Legacy routes — redirect to wallet login
@app.route('/register', methods=['GET'])
def register():
    return redirect(url_for('wallet_login'))

@app.route('/setup_face', methods=['GET', 'POST'])
def setup_face():
    user = get_current_user()
    if not user:
        return redirect(url_for('wallet_login'))
        
    if request.method == 'POST':
        data = request.json
        descriptor = data.get('descriptor') # List of floats
        
        if not descriptor or len(descriptor) != 128:
            return jsonify({'error': 'Invalid face descriptor'}), 400
            
        import json
        descriptor_json = json.dumps(descriptor)
        
        conn = get_db_connection()
        conn.execute('UPDATE users SET face_descriptor = ? WHERE id = ?', (descriptor_json, user['id']))
        conn.commit()
        conn.close()
        
        # Log action
        log_transaction(user['id'], 'FACE_SETUP', 'Registered Face ID')
        
        return jsonify({'success': True})
        
    return render_template('setup_face.html', user=user)

@app.route('/')
@app.route('/dashboard')
def dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for('wallet_login'))
    
    conn = get_db_connection()
    certs = conn.execute('SELECT * FROM certificates WHERE user_id = ? ORDER BY upload_date DESC',
                         (user['id'],)).fetchall()
    elections = conn.execute('SELECT * FROM elections ORDER BY created_date DESC').fetchall()
    
    # Fetch pending invites
    invites = conn.execute('''SELECT g.* 
                              FROM groups g 
                              JOIN group_members gm ON g.id = gm.group_id 
                              WHERE gm.user_id = ? AND gm.status = 'invited' ''',
                           (user['id'],)).fetchall()
    
    # Calculate Attendance Analytics
    attendance_stats = []
    attendance_summary = None
    if user['role'] == 'student':
        # Get all distinct courses from sessions
        courses = conn.execute('SELECT DISTINCT course_code FROM attendance_sessions WHERE course_code IS NOT NULL').fetchall()
        
        for course in courses:
            code = course['course_code']
            # Total sessions
            total_sessions = conn.execute('SELECT COUNT(*) FROM attendance_sessions WHERE course_code = ?', (code,)).fetchone()[0]
            
            # Attended sessions
            attended = conn.execute('''
                SELECT COUNT(*) FROM attendance_records ar
                JOIN attendance_sessions s ON ar.session_id = s.id
                WHERE s.course_code = ? AND ar.user_id = ? AND ar.status = 'present'
            ''', (code, user['id'])).fetchone()[0]
            
            pct = (attended / total_sessions * 100) if total_sessions > 0 else 0
            attendance_stats.append({
                'code': code,
                'total': total_sessions,
                'attended': attended,
                'pct': round(pct, 1)
            })
            
        # Calculate Total Attendance Summary
        total_all_sessions = sum(s['total'] for s in attendance_stats)
        total_all_attended = sum(s['attended'] for s in attendance_stats)
        overall_pct = round((total_all_attended / total_all_sessions * 100), 1) if total_all_sessions > 0 else 0
        
        attendance_summary = {
            'total_conducted': total_all_sessions,
            'total_attended': total_all_attended,
            'overall_pct': overall_pct
        }
            
    conn.close()
    
    return render_template('dashboard.html', 
                           user=user, 
                           certs=certs, 
                           elections=elections, 
                           invites=invites, 
                           attendance_stats=attendance_stats,
                           attendance_summary=attendance_summary if user['role'] == 'student' else None,
                           TOKEN_UNIT=TOKEN_UNIT)

@app.route('/upload_certificate', methods=['GET', 'POST'])
def upload_certificate():
    user = get_current_user()
    if not user:
        return redirect(url_for('wallet_login'))
    
    if request.method == 'POST':
        if 'certificate' not in request.files:
            flash('No file selected')
            return redirect(request.url)
        
        file = request.files['certificate']
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        # Calculate hash first (before stream is consumed by save)
        cert_hash = get_file_hash(file)
        
        # Save file
        file.save(filepath)
        
        # Logic change: Check on-chain existence first
        conn = get_db_connection()
        on_chain_data = verify_certificate_on_chain(cert_hash)
        
        # Determine Target Student ID
        target_student_id = user['student_id'] # Default to current user
        if user['role'] == 'admin':
            custom_id = request.form.get('student_id')
            if custom_id:
                target_student_id = custom_id.strip()

        if on_chain_data['verified']:
            # Certificate exists on blockchain. Check ownership.
            metadata = on_chain_data.get('metadata', '')
            # Expected format: StudentID|Name|Date
            try:
                owner_id = metadata.split('|')[0]
                if str(owner_id) != str(target_student_id):
                    flash(f'Ownership Mismatch! This certificate is registered to Student ID: {owner_id}')
                    conn.close()
                    return redirect(request.url)
                else:
                    # Ownership matches. Allow re-upload/db-sync.
                    flash('Certificate verified on blockchain! Syncing to database...')
            except IndexError:
                # Legacy format or error
                pass
                
        existing = conn.execute('SELECT * FROM certificates WHERE cert_hash = ?', (cert_hash,)).fetchone()
        if existing:
            flash('This certificate hash already exists in the database.')
            conn.close()
            return redirect(url_for('dashboard'))
        
        txid = None
        if not on_chain_data['verified']:
            try:
                # 1. Store Hash (New Box Storage Logic)
                # Create metadata: StudentID|Name|Date
                metadata = f"{target_student_id}|{user['name']}|{datetime.datetime.now().isoformat()}"
                # Hex to bytes
                cert_hash_bytes = bytes.fromhex(cert_hash)
                
                txid = store_certificate_hash(cert_hash_bytes, metadata)
                
                if not txid:
                    raise Exception("Failed to store certificate hash on-chain")
                
                # 2. Mint NFT (New Feature)
                should_mint = request.form.get('mint_nft') == 'on'
                asset_id = None
                
                if should_mint:
                    # NFT minting now goes through Pera Wallet signing flow.
                    # We store a placeholder; the user can mint from Wallet page.
                    flash("Certificate stored on-chain! To mint an NFT, use the Wallet → Mint NFT tab.", "info")

            except Exception as e:
                flash(f'Algorand transaction failed: {e}')
                conn.close()
                return redirect(url_for('dashboard'))
        else:
            # It was already on chain, we just syncing DB
            txid = "EXISTING_ON_CHAIN"

        upload_date = datetime.datetime.now().isoformat()
        # Use target_student_id for the record if possible, but the DB schema links to user_id (PK).
        # Complex: If Admin uploads for Student X, we need Student X's user_id.
        # For now, if Admin uploads, it's linked to Admin's INT account, but Metadata has Real Student ID.
        # Ideally we look up the user by student_id to get their DB ID.
        
        db_user_id = user['id']
        if user['role'] == 'admin' and target_student_id != user['student_id']:
            target_user = conn.execute('SELECT id FROM users WHERE student_id = ?', (target_student_id,)).fetchone()
            if target_user:
                db_user_id = target_user['id']
            else:
                 flash(f"Warning: Student ID {target_student_id} not found in database. Certificate linked to Admin.")

        conn.execute('INSERT INTO certificates (user_id, filename, cert_hash, tx_id, asset_id, upload_date) VALUES (?, ?, ?, ?, ?, ?)',
                     (db_user_id, filename, cert_hash, txid, asset_id, upload_date))
        conn.commit()
        conn.close()
        
        
        msg = f'Certificate uploaded! TxID: {txid}'
        if asset_id:
            msg += f' | NFT Minted (ID: {asset_id})'
        
        # Log transaction
        log_transaction(user['id'], 'CERTIFICATE_UPLOAD', f"Uploaded {filename}", txid)
        
        flash(msg)
        return redirect(url_for('dashboard'))
    
    return render_template('upload_cert.html', user=user)

@app.route('/delete_certificate/<int:cert_id>', methods=['POST'])
def delete_certificate(cert_id):
    if 'user_id' not in session:
        return redirect(url_for('wallet_login'))
        
    conn = get_db_connection()
    cert = conn.execute('SELECT * FROM certificates WHERE id = ?', (cert_id,)).fetchone()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if not cert:
        flash('Certificate not found.')
        conn.close()
        return redirect(url_for('dashboard'))
        
    # Permission check: Owner or Admin
    if str(cert['user_id']) != str(session['user_id']) and user['role'] != 'admin':
        flash('Unauthorized to delete this certificate.')
        conn.close()
        return redirect(url_for('dashboard'))
        
    try:
        # 1. Delete from Blockchain
        cert_hash_bytes = bytes.fromhex(cert['cert_hash'])
        
        # Check if exists first
        verify_result = verify_certificate_on_chain(cert['cert_hash'])
        
        if verify_result and verify_result.get('verified'):
            txid = delete_certificate_on_chain(cert_hash_bytes)
            if txid:
                flash(f'Certificate deleted from blockchain. TxID: {txid}')
            else:
                flash('Warning: Blockchain deletion failed, but removing from database.')
        else:
            flash('Certificate not found on blockchain (likely never synced). internal record deleted.')

        # 2. Delete from DB
        conn.execute('DELETE FROM certificates WHERE id = ?', (cert_id,))
        conn.commit()
            
    except Exception as e:
        flash(f'Error during deletion: {e}')
    finally:
        conn.close()
        
    return redirect(url_for('dashboard'))
    


@app.route('/verify', methods=['GET', 'POST'])
def verify():
    result = None
    if request.method == 'POST':
        if 'certificate' not in request.files:
            flash('No file selected')
            return redirect(request.url)
        
        file = request.files['certificate']
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)
        
        cert_hash = get_file_hash(file)
        
        conn = get_db_connection()
        cert = conn.execute('''SELECT c.*, u.name, u.student_id 
                               FROM certificates c 
                               JOIN users u ON c.user_id = u.id 
                               WHERE c.cert_hash = ?''', (cert_hash,)).fetchone()
        conn.close()
        
        # Verify on-chain independently
        cert_hash_bytes = bytes.fromhex(cert_hash)
        chain_result = verify_certificate_on_chain(cert_hash_bytes)
        
        if cert:
            result = {
                'valid': True,
                'student_name': cert['name'],
                'student_id': cert['student_id'],
                'filename': cert['filename'],
                'tx_id': cert['tx_id'],
                'hash': cert_hash,
                'on_chain_status': chain_result
            }
        else:
            # Even if not in DB, check chain
            if chain_result['verified']:
                result = {
                    'valid': True,
                    'student_name': 'Unknown (On-Chain Only)',
                    'student_id': 'N/A',
                    'filename': 'Unknown',
                    'tx_id': 'Look up via Explorer',
                    'hash': cert_hash,
                    'on_chain_status': chain_result
                }
            else:
                result = {'valid': False, 'hash': cert_hash, 'message': 'Verification Failed: Fraudulent or Unauthorized Certificate.'}
    
    return render_template('verify_cert.html', result=result)

@app.route('/create_election', methods=['GET', 'POST'])
def create_election():
    user = get_current_user()
    if not user or user['role'] != 'admin':
        flash('Admin only')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        candidates_text = request.form['candidates']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO elections (title, description, created_by, created_date) VALUES (?, ?, ?, ?)',
                       (title, description, user['id'], datetime.datetime.now().isoformat()))
        election_id = cursor.lastrowid
        
        for name in candidates_text.strip().splitlines():
            if name.strip():
                cursor.execute('INSERT INTO candidates (election_id, name) VALUES (?, ?)',
                               (election_id, name.strip()))
        
        conn.commit()
        conn.close()
        
        # Log transaction
        log_transaction(user['id'], 'ELECTION_CREATE', f"Created election: {title}")
        
        flash('Election created!')
        return redirect(url_for('dashboard'))
    
    return render_template('create_election.html')

@app.route('/election/<int:eid>', methods=['GET', 'POST'])
def election_detail(eid):
    user = get_current_user()
    if not user:
        return redirect(url_for('wallet_login'))
    
    conn = get_db_connection()
    election = conn.execute('SELECT * FROM elections WHERE id = ?', (eid,)).fetchone()
    if not election:
        flash('Election not found')
        return redirect(url_for('dashboard'))
    
    candidates = conn.execute('SELECT * FROM candidates WHERE election_id = ?', (eid,)).fetchall()
    has_voted = conn.execute('SELECT * FROM votes WHERE election_id = ? AND user_id = ?',
                             (eid, user['id'])).fetchone()
    
    if request.method == 'POST' and election['status'] == 'active' and not has_voted:
        # Prevent Admin from voting
        if user['role'] == 'admin':
            flash('Admins are not allowed to vote.')
            return redirect(request.url)
            
        candidate_id = request.form['candidate']
        vote_date = datetime.datetime.now().isoformat()
        
        note = f"VOTE|election:{eid}|candidate:{candidate_id}"
        try:
            txid = store_on_chain(note)
        except Exception:
            flash('Vote recording on blockchain failed')
            conn.close()
            return redirect(request.url)
        
        conn.execute('INSERT INTO votes (election_id, user_id, candidate_id, tx_id, vote_date) VALUES (?, ?, ?, ?, ?)',
                     (eid, user['id'], candidate_id, txid, vote_date))
        conn.commit()
        flash('Vote recorded!')
        return redirect(request.url)
    
    # Results
    results = conn.execute('''SELECT c.name, COUNT(v.id) as votes 
                              FROM candidates c 
                              LEFT JOIN votes v ON c.id = v.candidate_id 
                              WHERE c.election_id = ? 
                              GROUP BY c.id''', (eid,)).fetchall()
    
    # Fetch vote ledger for blockchain verification
    vote_records = conn.execute('''
        SELECT v.tx_id, v.vote_date, c.name as candidate_name
        FROM votes v
        JOIN candidates c ON v.candidate_id = c.id
        WHERE v.election_id = ?
        ORDER BY v.vote_date DESC
    ''', (eid,)).fetchall()
    
    conn.close()
    return render_template('election.html', election=election, candidates=candidates,
                           has_voted=has_voted, results=results, user=user, vote_records=vote_records)

@app.route('/end_election/<int:eid>')
def end_election(eid):
    user = get_current_user()
    if not user or user['role'] != 'admin':
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    conn.execute('UPDATE elections SET status = "ended" WHERE id = ?', (eid,))
    conn.commit()
    conn.close()
    flash('Election ended')
    return redirect(url_for('election_detail', eid=eid))

@app.route('/delete_election/<int:eid>')
def delete_election(eid):
    user = get_current_user()
    if not user or user['role'] != 'admin':
        flash('Admin only')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    election = conn.execute('SELECT * FROM elections WHERE id = ?', (eid,)).fetchone()
    
    if not election:
        flash('Election not found')
        conn.close()
        return redirect(url_for('dashboard'))
        
    if election['status'] != 'ended':
        flash('Cannot delete active election. End it first.')
        conn.close()
        return redirect(url_for('election_detail', eid=eid))

    # Delete related data
    conn.execute('DELETE FROM votes WHERE election_id = ?', (eid,))
    conn.execute('DELETE FROM candidates WHERE election_id = ?', (eid,))
    conn.execute('DELETE FROM elections WHERE id = ?', (eid,))
    
    conn.commit()
    conn.close()
    flash('Election deleted successfully')
    return redirect(url_for('dashboard'))

# ========================= ATTENDANCE TRACKING ROUTES =========================

@app.route('/attendance/create', methods=['GET', 'POST'])
def create_attendance_session():
    user = get_current_user()
    if not user or user['role'] not in ['admin', 'instructor']:
        flash('Admin or Instructor only')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        course_code = request.form['course_code']
        session_date = request.form['session_date']
        session_time = request.form['session_time']
        duration = int(request.form.get('duration', 60)) # Default 60 mins

        # Calculate end time
        start_datetime = datetime.datetime.strptime(f"{session_date} {session_time}", "%Y-%m-%d %H:%M")
        end_datetime = start_datetime + datetime.timedelta(minutes=duration)
        end_time_iso = end_datetime.isoformat()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO attendance_sessions
                         (created_by, course_code, session_date, session_time, end_time, created_at)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (user['id'], course_code, session_date, session_time, end_time_iso, datetime.datetime.now().isoformat()))
        conn.commit()
        session_id = cursor.lastrowid
        conn.close()

        # Log transaction
        log_transaction(user['id'], 'ATTENDANCE_SESSION_CREATE', f"Created session for {course_code} at {session_time}")

        flash(f'Attendance session created for {course_code} with {duration} min duration')
        return redirect(url_for('attendance_session', session_id=session_id))

    return render_template('attendance_create.html')

@app.route('/attendance/delete/<int:session_id>', methods=['POST'])
def delete_attendance_session(session_id):
    user = get_current_user()
    if not user or user['role'] not in ['admin', 'instructor']:
        flash('Unauthorized')
        return redirect(url_for('attendance_list'))

    conn = get_db_connection()
    # verify ownership or admin
    session_info = conn.execute('SELECT * FROM attendance_sessions WHERE id = ?', (session_id,)).fetchone()
    if not session_info:
        flash('Session not found')
        conn.close()
        return redirect(url_for('attendance_list'))
        
    if user['role'] != 'admin' and session_info['created_by'] != user['id']:
        flash('You can only delete sessions you created')
        conn.close()
        return redirect(url_for('attendance_list'))

    # Delete records and session
    conn.execute('DELETE FROM attendance_records WHERE session_id = ?', (session_id,))
    conn.execute('DELETE FROM attendance_sessions WHERE id = ?', (session_id,))
    conn.commit()
    conn.close()
    
    log_transaction(user['id'], 'ATTENDANCE_SESSION_DELETE', f"Deleted session {session_id}")
    flash('Attendance session deleted')
    return redirect(url_for('attendance_list'))

@app.route('/attendance/<int:session_id>', methods=['GET', 'POST'])
def attendance_session(session_id):
    user = get_current_user()
    if not user:
        return redirect(url_for('wallet_login'))

    conn = get_db_connection()
    session_info = conn.execute('SELECT * FROM attendance_sessions WHERE id = ?', (session_id,)).fetchone()

    if not session_info:
        flash('Session not found')
        return redirect(url_for('dashboard'))

    # Check if user has already marked attendance
    existing_record = conn.execute('SELECT * FROM attendance_records WHERE session_id = ? AND user_id = ?',
                                 (session_id, user['id'])).fetchone()
    
    # Check deadline
    now = datetime.datetime.now().isoformat()
    is_expired = False
    if session_info['end_time'] and now > session_info['end_time']:
        is_expired = True

    if request.method == 'POST' and not existing_record:
        if is_expired:
            flash('Check-in time has expired for this session.')
            return redirect(request.url)
            
        # Student self check-in
        check_in_time = datetime.datetime.now().isoformat()
        
        # Face Recognition Handling
        face_descriptor_str = request.form.get('face_descriptor')
        
        # STRICT MODE: Require face descriptor
        if not face_descriptor_str:
            flash('Strict Attendance Mode: Face verification required.')
            return redirect(request.url)
            
        import json
        import math
        
        try:
            live_descriptor = json.loads(face_descriptor_str)
            
            # Retrieve user's registered descriptor
            if not user['face_descriptor']:
                flash('You have not set up Face ID. Please go to your profile/dashboard to set it up.')
                conn.close()
                return redirect(url_for('dashboard'))
                
            stored_descriptor = json.loads(user['face_descriptor'])
            
            # Euclidean Distance Calculation
            distance = math.sqrt(sum([(a - b) ** 2 for a, b in zip(live_descriptor, stored_descriptor)]))
            
            # Threshold (0.6 is standard for dlib/face_recognition, strict can be 0.5)
            if distance > 0.5:
                flash(f'Identity Verification Failed! Face does not match registered student (Distance: {distance:.2f})')
                conn.close()
                return redirect(request.url)
                
        except Exception as e:
            flash(f'Face processing error: {e}')
            conn.close()
            return redirect(request.url)
            
        # If passed, simulate hash for chain (since we have verified identity)
        face_hash = hashlib.sha256(face_descriptor_str.encode()).hexdigest()

        try:
            # txid = record_attendance_on_chain(session_id, user['id'], 'present', user['id'], face_hash)
            # Optimization: Run blockchain recording in background thread
            import threading
            
            def record_async(sid, uid, stat, marked_by, f_hash):
                try:
                    # Create new connection for thread
                    with app.app_context():
                        tx = record_attendance_on_chain(sid, uid, stat, marked_by, f_hash)
                        # Update DB with actual TXID
                        c = get_db_connection()
                        c.execute('UPDATE attendance_records SET tx_id = ? WHERE session_id = ? AND user_id = ?',
                                (tx, sid, uid))
                        c.commit()
                        c.close()
                        
                        # Log success
                        log_transaction(uid, 'ATTENDANCE_CHECKIN', f"Async check-in success for session {sid}", tx)
                        
                        # REWARD: Send Campus Tokens (also async now)
                        try:
                            token_id = ensure_campus_token()
                            if token_id:
                                distribute_reward(uid, 5, "Attendance Reward")
                        except:
                            pass
                except Exception as e:
                    print(f"Async recording failed: {e}")

            # Initial DB Record with Pending TX
            conn.execute('''INSERT INTO attendance_records
                           (session_id, user_id, marked_by, status, check_in_time, marked_at, tx_id)
                           VALUES (?, ?, ?, ?, ?, ?, ?)''',
                       (session_id, user['id'], user['id'], 'present', check_in_time, check_in_time, 'Verified & Pending'))
            conn.commit()
            
            # Start background thread
            thread = threading.Thread(target=record_async, args=(session_id, user['id'], 'present', user['id'], face_hash))
            thread.start()
            
            flash('Identity Verified! Check-in successful.')
            return redirect(request.url)

        except Exception as e:
            flash(f'Failed to record attendance: {e}')
            conn.close()
            return redirect(request.url)

    # Get all students and their attendance status
    all_students = conn.execute('SELECT * FROM users WHERE role = "student" ORDER BY name').fetchall()
    attendance_records = conn.execute('SELECT * FROM attendance_records WHERE session_id = ?',
                                    (session_id,)).fetchall()

    attendance_dict = {rec['user_id']: rec for rec in attendance_records}

    # Check if current user is the instructor who created this session
    is_instructor = session_info['created_by'] == user['id'] or user['role'] == 'admin'

    conn.close()
    
    # Format times for display (AM/PM)
    display_info = dict(session_info)
    try:
        if session_info['end_time']:
            dt = datetime.datetime.fromisoformat(session_info['end_time'])
            display_info['end_time_display'] = dt.strftime("%I:%M %p")
        
        # Session time is likely HH:MM
        st = datetime.datetime.strptime(session_info['session_time'], "%H:%M")
        display_info['session_time_display'] = st.strftime("%I:%M %p")
    except:
        # Fallback
        display_info['end_time_display'] = session_info['end_time'][11:16] if session_info['end_time'] else ''
        display_info['session_time_display'] = session_info['session_time']

    return render_template('attendance_session.html',
                         session_info=display_info,
                         students=all_students,
                         attendance_dict=attendance_dict,
                         existing_record=existing_record,
                         is_instructor=is_instructor,
                         user=user,
                         now=now)

@app.route('/attendance/<int:session_id>/<int:user_id>', methods=['PUT'])
def mark_attendance(session_id, user_id):
    user = get_current_user()
    if not user or user['role'] not in ['admin', 'instructor']:
        return jsonify({'error': 'Unauthorized'}), 403

    status = request.json.get('status', 'absent')
    marked_time = datetime.datetime.now().isoformat()

    conn = get_db_connection()

    # Check if record exists
    existing = conn.execute('SELECT * FROM attendance_records WHERE session_id = ? AND user_id = ?',
                           (session_id, user_id)).fetchone()

    try:
        txid = record_attendance_on_chain(session_id, user_id, status, user['id'])
    except Exception as e:
        return jsonify({'error': 'Blockchain recording failed'}), 500

    if existing:
        conn.execute('UPDATE attendance_records SET status = ?, marked_by = ?, marked_at = ?, tx_id = ? WHERE session_id = ? AND user_id = ?',
                    (status, user['id'], marked_time, txid, session_id, user_id))
    else:
        conn.execute('''INSERT INTO attendance_records
                       (session_id, user_id, marked_by, status, marked_at, tx_id)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                   (session_id, user_id, user['id'], status, marked_time, txid))

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'tx_id': txid})

@app.route('/attendance/list')
def attendance_list():
    user = get_current_user()
    if not user:
        return redirect(url_for('wallet_login'))

    conn = get_db_connection()

    if user['role'] in ['admin', 'instructor']:
        # Show all sessions created by this user or all sessions for admin
        if user['role'] == 'admin':
            sessions = conn.execute('SELECT * FROM attendance_sessions ORDER BY session_date DESC, session_time DESC').fetchall()
        else:
            sessions = conn.execute('SELECT * FROM attendance_sessions WHERE created_by = ? ORDER BY session_date DESC, session_time DESC',
                                  (user['id'],)).fetchall()
    else:
        # Students see only active sessions
        sessions = conn.execute('SELECT * FROM attendance_sessions WHERE status = "active" ORDER BY session_date DESC').fetchall()

    conn.close()
    return render_template('attendance_list.html', sessions=sessions, user=user)

@app.route('/attendance/report/<course_code>')
def attendance_report(course_code):
    user = get_current_user()
    if not user or user['role'] not in ['admin', 'instructor']:
        flash('Instructor only')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()

    # Get all sessions for this course
    sessions = conn.execute('''SELECT * FROM attendance_sessions
                              WHERE course_code = ? ORDER BY session_date DESC, session_time DESC''',
                           (course_code,)).fetchall()

    # Get attendance summary
    summary = conn.execute('''SELECT u.id, u.name, u.student_id,
                             SUM(CASE WHEN ar.status = "present" THEN 1 ELSE 0 END) as present_count,
                             COUNT(ar.id) as total_sessions
                             FROM users u
                             LEFT JOIN attendance_records ar ON u.id = ar.user_id
                             LEFT JOIN attendance_sessions s ON ar.session_id = s.id
                             WHERE u.role = "student" AND s.course_code = ?
                             GROUP BY u.id
                             ORDER BY u.name''',
                            (course_code,)).fetchall()

    conn.close()

    return render_template('attendance_report.html',
                         course_code=course_code,
                         sessions=sessions,
                         summary=summary,
                         user=user)

# ========================= FEEDBACK COLLECTION ROUTES =========================

@app.route('/feedback/create', methods=['GET', 'POST'])
def create_feedback():
    user = get_current_user()
    if not user or user['role'] != 'admin':
        flash('Admin only')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        allow_anonymous = 1 if request.form.get('allow_anonymous') else 0

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO feedback_forms
                         (created_by, title, description, allow_anonymous, created_date, is_active)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (user['id'], title, description, allow_anonymous, datetime.datetime.now().isoformat(), 1))
        form_id = cursor.lastrowid

        # Add questions
        question_texts = request.form.getlist('questions')
        question_types = request.form.getlist('question_types')
        question_reqd = request.form.getlist('question_required')

        for i, q_text in enumerate(question_texts):
            if q_text.strip():
                required = 1 if (i < len(question_reqd) and question_reqd[i]) else 0
                q_type = question_types[i] if i < len(question_types) else 'text'
                cursor.execute('''INSERT INTO feedback_questions
                                 (form_id, question_text, question_type, required, question_order)
                                 VALUES (?, ?, ?, ?, ?)''',
                              (form_id, q_text.strip(), q_type, required, i))

        conn.commit()
        conn.close()

        # Log transaction
        log_transaction(user['id'], 'FEEDBACK_FORM_CREATE', f"Created feedback form: {title}")

        flash('Feedback form created!')
        return redirect(url_for('feedback_form', form_id=form_id))

    return render_template('feedback_create.html')

@app.route('/feedback/<int:form_id>', methods=['GET', 'POST'])
def feedback_form(form_id):
    user = get_current_user()

    conn = get_db_connection()
    form_info = conn.execute('SELECT * FROM feedback_forms WHERE id = ?', (form_id,)).fetchone()

    if not form_info or not form_info['is_active']:
        flash('Form not found or is closed')
        return redirect(url_for('dashboard'))

    # Admin cannot submit feedback, redirect to results
    if user and user['role'] == 'admin':
        return redirect(url_for('feedback_results', form_id=form_id))

    questions = conn.execute('SELECT * FROM feedback_questions WHERE form_id = ? ORDER BY question_order',
                            (form_id,)).fetchall()

    if request.method == 'POST' and user:
        is_anonymous = request.form.get('is_anonymous') == 'on'
        response_date = datetime.datetime.now().isoformat()

        for q in questions:
            response_text = request.form.get(f'question_{q["id"]}')

            if response_text is not None:
                response_hash = hashlib.sha256(response_text.encode()).hexdigest() if response_text else ''

                try:
                    if is_anonymous:
                        # Anonymous: not stored on blockchain for privacy
                        txid = None
                    else:
                        # Verified: store on blockchain
                        txid = record_feedback_on_chain(form_id, user['id'], q['id'], response_hash)
                        
                        # REWARD: Send Campus Tokens (10 for verified feedback)
                        ensure_campus_token()
                        distribute_reward(user['id'], 10, "Feedback Reward")
                except Exception as e:
                    flash('Failed to record feedback on blockchain')
                    conn.close()
                    return redirect(request.url)

                # Get optional comment for this question
                comment_key = f"question_{q['id']}_comment"
                comment = request.form.get(comment_key, '')

                conn.execute('''INSERT INTO feedback_responses 
                              (form_id, user_id, question_id, response_text, tx_id, is_anonymous, comments, response_date)
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                           (form_id, 
                            user['id'] if not is_anonymous else None, 
                            q['id'], 
                            response_text, 
                            txid if not is_anonymous else None,
                            1 if is_anonymous else 0,
                            comment,
                            response_date))

        conn.commit()
        
        # Log transaction (only if verified)
        if not is_anonymous:
             # Just logging the last txid if multiple questions, or generic log
             # Ideally we log per response but that's too much. Let's log the form submission.
             # We use the txid from the last question if available, or just note it's on chain
             last_tx = txid if 'txid' in locals() else None
             log_transaction(user['id'], 'FEEDBACK_SUBMIT', f"Submitted feedback for form {form_id}", last_tx)
             
        flash('Feedback submitted!')
        return redirect(url_for('dashboard'))

    # Check if user has already responded
    response = None
    if user:
        response = conn.execute('SELECT * FROM feedback_responses WHERE form_id = ? AND user_id = ?',
                               (form_id, user['id'])).fetchone()
    
    conn.close()

    return render_template('feedback_form.html',
                         form=form_info,
                         questions=questions,
                         response=response,
                         user=user,
                         form_id=form_id)

@app.route('/feedback/<int:form_id>/results')
def feedback_results(form_id):
    user = get_current_user()
    if not user:
        return redirect(url_for('wallet_login'))

    conn = get_db_connection()
    form_info = conn.execute('SELECT * FROM feedback_forms WHERE id = ?', (form_id,)).fetchone()

    if not form_info:
        flash('Form not found')
        return redirect(url_for('dashboard'))

    # Check authorization
    if user['role'] != 'admin':
        flash('Unauthorized')
        return redirect(url_for('dashboard'))

    questions = conn.execute('SELECT * FROM feedback_questions WHERE form_id = ? ORDER BY question_order',
                            (form_id,)).fetchall()

    results = {}
    for q in questions:
        # Get individual responses with tx_id and comments
        responses = conn.execute('''SELECT response_text, is_anonymous, tx_id, comments
                                   FROM feedback_responses
                                   WHERE question_id = ?
                                   ORDER BY id DESC''',
                               (q['id'],)).fetchall()
        
        # Group by text to show counts, but keep individual details if needed
        # For this view, listing individual responses with TX ID is better than grouping
        # if we want to show verification.
        # However, the previous view was grouped.
        # Let's change the view to list responses with their verification status.
        
        results[q['id']] = {
            'question': q['question_text'],
            'type': q['question_type'],
            'responses': responses
        }
        
        # Calculate Sentiment for Ratings
        if q['question_type'] == 'rating' and responses:
            total_score = 0
            count = 0
            for r in responses:
                if r['response_text'] and r['response_text'].isdigit():
                    total_score += int(r['response_text'])
                    count += 1
            
            if count > 0:
                avg = total_score / count
                results[q['id']]['average'] = round(avg, 1)
                
                if avg >= 3.5:
                    results[q['id']]['sentiment'] = 'Positive'
                    results[q['id']]['sentiment_color'] = 'success'
                elif avg >= 2.5:
                    results[q['id']]['sentiment'] = 'Neutral'
                    results[q['id']]['sentiment_color'] = 'warning'
                else:
                    results[q['id']]['sentiment'] = 'Negative'
                    results[q['id']]['sentiment_color'] = 'danger'

    response_count = conn.execute('SELECT COUNT(DISTINCT user_id) FROM feedback_responses WHERE form_id = ? AND user_id IS NOT NULL',
                                 (form_id,)).fetchone()[0]
    anon_response_count = conn.execute('SELECT COUNT(DISTINCT id) FROM feedback_responses WHERE form_id = ? AND is_anonymous = 1',
                                      (form_id,)).fetchone()[0]

    conn.close()

    return render_template('feedback_results.html',
                         form=form_info,
                         questions=questions,
                         results=results,
                         response_count=response_count,
                         anon_response_count=anon_response_count,
                         user=user)

@app.route('/feedback/list')
def feedback_list():
    user = get_current_user()
    if not user:
        return redirect(url_for('wallet_login'))

    conn = get_db_connection()
    
    # Get active forms
    forms = conn.execute('SELECT * FROM feedback_forms WHERE is_active = 1 ORDER BY created_date DESC').fetchall()
    
    # Get user's responses
    responded_forms = set()
    rows = conn.execute('SELECT DISTINCT form_id FROM feedback_responses WHERE user_id = ?', (user['id'],)).fetchall()
    for row in rows:
        responded_forms.add(row['form_id'])
    
    conn.close()
    
    return render_template('feedback_list.html', forms=forms, responded_forms=responded_forms, user=user)

@app.route('/feedback/<int:form_id>/close', methods=['PUT'])
def close_feedback(form_id):
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db_connection()
    form_info = conn.execute('SELECT * FROM feedback_forms WHERE id = ?', (form_id,)).fetchone()

    if not form_info or (user['id'] != form_info['created_by'] and user['role'] != 'admin'):
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 403

    conn.execute('UPDATE feedback_forms SET is_active = 0, closed_date = ? WHERE id = ?',
                (datetime.datetime.now().isoformat(), form_id))
    conn.commit()
    conn.close()

    return jsonify({'success': True})

# ========================= GROUP COORDINATION ROUTES =========================

@app.route('/groups/admin/create', methods=['GET', 'POST'])
def admin_create_group():
    user = get_current_user()
    if not user or user['role'] != 'admin':
        flash('Admin only')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        category = request.form['category']
        selected_members = request.form.getlist('members')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO groups
                         (name, description, creation_type, created_by, created_date, category)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (name, description, 'admin_created', user['id'], datetime.datetime.now().isoformat(), category))
        group_id = cursor.lastrowid

        # Add members
        for member_id in selected_members:
            try:
                cursor.execute('''INSERT INTO group_members
                                 (group_id, user_id, role, joined_date)
                                 VALUES (?, ?, ?, ?)''',
                              (group_id, int(member_id), 'member', datetime.datetime.now().isoformat()))
            except:
                pass

        # Add group creator as lead
        cursor.execute('''INSERT INTO group_members
                         (group_id, user_id, role, joined_date)
                         VALUES (?, ?, ?, ?)''',
                      (group_id, user['id'], 'lead', datetime.datetime.now().isoformat()))

        conn.commit()
        conn.close()
        
        # Log transaction
        log_transaction(user['id'], 'GROUP_CREATE_ADMIN', f"Created group {name} ({category})")

        flash('Group created!')
        return redirect(url_for('group_detail', group_id=group_id))

    conn = get_db_connection()
    students = conn.execute('SELECT * FROM users WHERE role = "student" ORDER BY name').fetchall()
    conn.close()

    return render_template('group_admin_create.html', students=students)

@app.route('/groups/create', methods=['GET', 'POST'])
def create_group():
    user = get_current_user()
    if not user:
        return redirect(url_for('wallet_login'))

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        category = request.form.get('category', 'Project')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO groups
                         (name, description, creation_type, created_by, created_date, category, status)
                         VALUES (?, ?, ?, ?, ?, ?, ?)''',
                      (name, description, 'student_created', user['id'], datetime.datetime.now().isoformat(), category, 'active'))
        group_id = cursor.lastrowid

        # Add creator as lead
        cursor.execute('''INSERT INTO group_members
                         (group_id, user_id, role, joined_date)
                         VALUES (?, ?, ?, ?)''',
                      (group_id, user['id'], 'lead', datetime.datetime.now().isoformat()))

        conn.commit()
        conn.close()
        
        # Log transaction
        log_transaction(user['id'], 'GROUP_CREATE_STUDENT', f"Created group {name} ({category})")

        flash('Group created!')
        return redirect(url_for('group_detail', group_id=group_id))

    return render_template('group_create.html')

@app.route('/groups/discover')
def discover_groups():
    user = get_current_user()
    if not user:
        return redirect(url_for('wallet_login'))

    conn = get_db_connection()
    
    query = request.args.get('q', '').strip()

    if query:
        # Search for groups
        groups = conn.execute('''SELECT g.*, COUNT(gm.user_id) as member_count
                                FROM groups g
                                LEFT JOIN group_members gm ON g.id = gm.group_id
                                WHERE g.creation_type = "student_created" 
                                AND g.status = "active"
                                AND (g.name LIKE ? OR g.description LIKE ?)
                                GROUP BY g.id
                                ORDER BY g.created_date DESC''', 
                                (f'%{query}%', f'%{query}%')).fetchall()
    else:
        # Get all student-created groups
        groups = conn.execute('''SELECT g.*, COUNT(gm.user_id) as member_count
                                FROM groups g
                                LEFT JOIN group_members gm ON g.id = gm.group_id
                                WHERE g.creation_type = "student_created" AND g.status = "active"
                                GROUP BY g.id
                                ORDER BY g.created_date DESC''').fetchall()

    # Get user's groups
    user_groups = conn.execute('''SELECT DISTINCT g.id FROM groups g
                                 JOIN group_members gm ON g.id = gm.group_id
                                 WHERE gm.user_id = ?''', (user['id'],)).fetchall()
    user_group_ids = {g['id'] for g in user_groups}

    conn.close()

    return render_template('group_discover.html', groups=groups, user_group_ids=user_group_ids, user=user, query=query)

@app.route('/groups/<int:group_id>/join', methods=['POST'])
def join_group(group_id):
    user = get_current_user()
    if not user:
        return redirect(url_for('wallet_login'))

    conn = get_db_connection()

    # Check if already member
    existing = conn.execute('SELECT * FROM group_members WHERE group_id = ? AND user_id = ?',
                           (group_id, user['id'])).fetchone()

    if not existing:
        conn.execute('''INSERT INTO group_members
                       (group_id, user_id, role, joined_date)
                       VALUES (?, ?, ?, ?)''',
                   (group_id, user['id'], 'member', datetime.datetime.now().isoformat()))
        conn.commit()
        flash('Joined group!')

    conn.close()
    return redirect(url_for('group_detail', group_id=group_id))

@app.route('/groups/<int:group_id>/leave', methods=['POST'])
def leave_group(group_id):
    user = get_current_user()
    if not user:
        return redirect(url_for('wallet_login'))

    conn = get_db_connection()
    conn.execute('DELETE FROM group_members WHERE group_id = ? AND user_id = ?', (group_id, user['id']))
    conn.commit()
    conn.close()

    flash('Left group')
    return redirect(url_for('dashboard'))

@app.route('/groups/<int:group_id>')
def group_detail(group_id):
    user = get_current_user()
    if not user:
        return redirect(url_for('wallet_login'))

    conn = get_db_connection()
    group = conn.execute('SELECT * FROM groups WHERE id = ?', (group_id,)).fetchone()

    if not group:
        flash('Group not found')
        return redirect(url_for('dashboard'))



    # Get members
    members = conn.execute('''SELECT u.id, u.name, u.student_id, gm.role, gm.status
                             FROM group_members gm
                             JOIN users u ON gm.user_id = u.id
                             WHERE gm.group_id = ? ORDER BY gm.role DESC, u.name''',
                          (group_id,)).fetchall()

    # Get tasks
    tasks = conn.execute('''SELECT t.*, u.name as assignee_name 
                           FROM group_tasks t 
                           LEFT JOIN users u ON t.assigned_to = u.id 
                           WHERE t.group_id = ? 
                           ORDER BY t.due_date''',
                        (group_id,)).fetchall()

    # Get milestones
    milestones = conn.execute('SELECT * FROM group_milestones WHERE group_id = ? ORDER BY target_date',
                             (group_id,)).fetchall()

    # Check if user is member
    is_member = conn.execute('SELECT * FROM group_members WHERE group_id = ? AND user_id = ?',
                            (group_id, user['id'])).fetchone() is not None

    # Check if user is lead
    is_lead = conn.execute('SELECT * FROM group_members WHERE group_id = ? AND user_id = ? AND role = "lead"',
                          (group_id, user['id'])).fetchone() is not None

    # Get DAO Data
    proposals = conn.execute('SELECT * FROM group_proposals WHERE group_id = ? ORDER BY id DESC', (group_id,)).fetchall()
    
    # Get Treasury Balance if exists
    treasury_balance = 0.0
    try:
        client = get_client()
        if group['treasury_address']:
            account_info = client.account_info(group['treasury_address'])
            treasury_balance = account_info.get('amount', 0) / 1_000_000
        elif not group['dao_app_id'] or group['dao_app_id'] == 0:
            # Legacy groups without DAO – show 0 balance
            treasury_balance = 0.0
    except Exception as e:
        print(f"Error fetching treasury balance: {e}")
        treasury_balance = 0.0

    conn.close()

    return render_template('group_detail.html',
                         group=group,
                         members=members,
                         tasks=tasks,
                         milestones=milestones,
                         proposals=proposals,
                         treasury_balance=treasury_balance,
                         is_member=is_member,
                         is_lead=is_lead,
                         user=user)

# --- DAO Routes ---

@app.route('/groups/<int:group_id>/dao/deploy', methods=['POST'])
def deploy_dao(group_id):
    user = get_current_user()
    if not user: return redirect(url_for('wallet_login'))
    
    # Only lead or admin can deploy
    conn = get_db_connection()
    is_lead = conn.execute('SELECT * FROM group_members WHERE group_id = ? AND user_id = ? AND role = "lead"',
                          (group_id, user['id'])).fetchone()
    
    if not is_lead and user['role'] != 'admin':
        flash('Only Group Lead can initialize the DAO.')
        return redirect(url_for('group_detail', group_id=group_id))
        
    try:
        # DAO deployment now happens via AlgoKit CLI or Pera Wallet signing.
        # Here we just record a placeholder – the lead must deploy via CLI.
        flash('DAO deployment now uses AlgoKit. Run: python -m contracts.deploy --deploy --contract campus_dao', 'info')
            
    except Exception as e:
        flash(f'Error: {str(e)}')
    
    conn.close()
    return redirect(url_for('group_detail', group_id=group_id))

@app.route('/groups/<int:group_id>/dao/propose', methods=['POST'])
def create_proposal(group_id):
    user = get_current_user()
    conn = get_db_connection()
    
    title = request.form['title']
    desc = request.form['description']
    amount = float(request.form['amount'])
    recipient = request.form['recipient']
    
    conn.execute('INSERT INTO group_proposals (group_id, title, description, amount_algo, recipient_address, status, created_date) VALUES (?, ?, ?, ?, ?, ?, ?)',
                 (group_id, title, desc, amount, recipient, 'pending', datetime.datetime.now()))
    conn.commit()
    conn.close()
    
    flash('Proposal created!')
    return redirect(url_for('group_detail', group_id=group_id))

@app.route('/groups/<int:group_id>/dao/vote/<int:proposal_id>', methods=['POST'])
def vote_proposal(group_id, proposal_id):
    user = get_current_user()
    choice = request.form['choice'] # 'yes' or 'no'
    
    conn = get_db_connection()
    try:
        # Check if already voted
        # (Assuming distinct constraint in DB)
        conn.execute('INSERT INTO proposal_votes (proposal_id, user_id, choice) VALUES (?, ?, ?)',
                    (proposal_id, user['id'], choice))
        
        # Update Counts
        if choice == 'yes':
            conn.execute('UPDATE group_proposals SET yes_votes = yes_votes + 1 WHERE id = ?', (proposal_id,))
        else:
            conn.execute('UPDATE group_proposals SET no_votes = no_votes + 1 WHERE id = ?', (proposal_id,))
            
        conn.commit()
        flash('Vote cast successfully!')
    except sqlite3.IntegrityError:
        flash('You have already voted on this proposal.')
    except Exception as e:
        flash(f'Error: {e}')
        
    conn.close()
    return redirect(url_for('group_detail', group_id=group_id))

@app.route('/groups/<int:group_id>/dao/approve/<int:proposal_id>', methods=['POST'])
def approve_proposal(group_id, proposal_id):
    user = get_current_user()
    conn = get_db_connection()
    # Check permissions (Lead or Admin) - simplified check for now, can be robustified
    group = conn.execute('SELECT * FROM groups WHERE id = ?', (group_id,)).fetchone()
    if user['role'] != 'admin':
         flash('Unauthorized')
         conn.close()
         return redirect(url_for('group_detail', group_id=group_id))

    conn.execute("UPDATE group_proposals SET status = 'approved' WHERE id = ?", (proposal_id,))
    conn.commit()
    conn.close()
    flash('Proposal approved!')
    return redirect(url_for('group_detail', group_id=group_id))

@app.route('/groups/<int:group_id>/dao/reject/<int:proposal_id>', methods=['POST'])
def reject_proposal(group_id, proposal_id):
    user = get_current_user()
    conn = get_db_connection()
    # Check permissions
    group = conn.execute('SELECT * FROM groups WHERE id = ?', (group_id,)).fetchone()
    if user['role'] != 'admin':
         flash('Unauthorized')
         conn.close()
         return redirect(url_for('group_detail', group_id=group_id))

    conn.execute("UPDATE group_proposals SET status = 'rejected' WHERE id = ?", (proposal_id,))
    conn.commit()
    conn.close()
    flash('Proposal rejected!')
    return redirect(url_for('group_detail', group_id=group_id))

@app.route('/groups/<int:group_id>/dao/execute/<int:proposal_id>', methods=['POST'])
def execute_proposal(group_id, proposal_id):
    user = get_current_user()
    if not user or user['role'] != 'admin':
        flash('Only Admin can execute treasury proposals.')
        return redirect(url_for('group_detail', group_id=group_id))
    
    conn = get_db_connection()
    group = conn.execute('SELECT * FROM groups WHERE id = ?', (group_id,)).fetchone()
    prop = conn.execute('SELECT * FROM group_proposals WHERE id = ?', (proposal_id,)).fetchone()
    
    if prop['status'] == 'approved' or prop['yes_votes'] > prop['no_votes']:
        # Proposal execution now requires Pera Wallet signing.
        # Mark proposal as 'pending_execution' – admin must sign via wallet.
        conn.execute("UPDATE group_proposals SET status = 'pending_execution' WHERE id = ?",
                     (proposal_id,))
        conn.commit()
        flash('Proposal approved! Please execute it from the Wallet page using Pera Wallet.', 'info')
            
    else:
        flash('Proposal does not have enough votes.')

    conn.close()
    return redirect(url_for('group_detail', group_id=group_id))

@app.route('/groups/<int:group_id>/delete', methods=['POST'])
def delete_group(group_id):
    user = get_current_user()
    if not user:
        return redirect(url_for('wallet_login'))

    conn = get_db_connection()
    
    # Check if user is lead or admin
    is_lead = conn.execute('SELECT * FROM group_members WHERE group_id = ? AND user_id = ? AND role = "lead"',
                          (group_id, user['id'])).fetchone() is not None
    
    if not is_lead and user['role'] != 'admin':
        conn.close()
        flash('Only group leads can delete groups')
        return redirect(url_for('group_detail', group_id=group_id))

    # Delete everything related to group
    conn.execute('DELETE FROM group_tasks WHERE group_id = ?', (group_id,))
    conn.execute('DELETE FROM group_milestones WHERE group_id = ?', (group_id,))
    conn.execute('DELETE FROM group_members WHERE group_id = ?', (group_id,))
    conn.execute('DELETE FROM groups WHERE id = ?', (group_id,))
    
    conn.commit()
    conn.close()
    
    flash('Group deleted successfully')
    return redirect(url_for('dashboard'))

@app.route('/groups/<int:group_id>/invite', methods=['POST'])
def invite_member(group_id):
    user = get_current_user()
    if not user:
        return redirect(url_for('wallet_login'))

    conn = get_db_connection()
    
    # Check if user is lead or admin
    is_lead = conn.execute('SELECT * FROM group_members WHERE group_id = ? AND user_id = ? AND role = "lead"',
                          (group_id, user['id'])).fetchone() is not None
    
    if not is_lead and user['role'] != 'admin':
        conn.close()
        flash('Only group leads can invite members')
        return redirect(url_for('group_detail', group_id=group_id))

    student_id = request.form.get('student_id')
    
    # Find user
    target_user = conn.execute('SELECT * FROM users WHERE student_id = ?', (student_id,)).fetchone()
    
    if not target_user:
        conn.close()
        flash('Student ID not found')
        return redirect(url_for('group_detail', group_id=group_id))

    # Check if already member (accepted or invited)
    existing = conn.execute('SELECT * FROM group_members WHERE group_id = ? AND user_id = ?',
                           (group_id, target_user['id'])).fetchone()
    
    if existing:
        conn.close()
        if existing['status'] == 'invited':
            flash('User has already been invited')
        else:
            flash('User is already a member')
        return redirect(url_for('group_detail', group_id=group_id))

    # Add member with 'invited' status
    conn.execute('''INSERT INTO group_members
                   (group_id, user_id, role, joined_date, status)
                   VALUES (?, ?, ?, ?, ?)''',
               (group_id, target_user['id'], 'member', datetime.datetime.now().isoformat(), 'invited'))
    conn.commit()
    conn.close()
    
    flash(f'Invitation sent to {target_user["name"]}')
    return redirect(url_for('group_detail', group_id=group_id))

@app.route('/groups/<int:group_id>/accept_invite', methods=['POST'])
def accept_invite(group_id):
    user = get_current_user()
    if not user:
        return redirect(url_for('wallet_login'))

    conn = get_db_connection()
    conn.execute('UPDATE group_members SET status = "accepted" WHERE group_id = ? AND user_id = ?',
                (group_id, user['id']))
    conn.commit()
    conn.close()
    
    flash('Incorporated into group!')
    return redirect(url_for('group_detail', group_id=group_id))

@app.route('/groups/<int:group_id>/decline_invite', methods=['POST'])
def decline_invite(group_id):
    user = get_current_user()
    if not user:
        return redirect(url_for('wallet_login'))

    conn = get_db_connection()
    conn.execute('DELETE FROM group_members WHERE group_id = ? AND user_id = ?',
                (group_id, user['id']))
    conn.commit()
    conn.close()
    
    flash('Invitation declined')
    return redirect(url_for('dashboard'))

@app.route('/groups/<int:group_id>/task', methods=['POST'])
def create_task(group_id):
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db_connection()

    # Check if user is group lead or admin (Restrict creation)
    is_lead = conn.execute('SELECT * FROM group_members WHERE group_id = ? AND user_id = ? AND role = "lead"',
                          (group_id, user['id'])).fetchone() is not None

    if not is_lead and user['role'] != 'admin':
        conn.close()
        return jsonify({'error': 'Not authorized'}), 403

    title = request.form.get('title')
    description = request.form.get('description')
    assigned_to = request.form.get('assigned_to')
    due_date = request.form.get('due_date')

    cursor = conn.cursor()
    cursor.execute('''INSERT INTO group_tasks
                     (group_id, title, description, assigned_to, due_date, created_date)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (group_id, title, description, assigned_to or None, due_date, datetime.datetime.now().isoformat()))
    task_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'task_id': task_id})

@app.route('/groups/<int:group_id>/task/<int:task_id>/complete', methods=['POST'])
def complete_task(group_id, task_id):
    user = get_current_user()
    if not user:
        return redirect(url_for('wallet_login'))

    conn = get_db_connection()
    task = conn.execute('SELECT * FROM group_tasks WHERE id = ? AND group_id = ?', (task_id, group_id)).fetchone()

    if not task:
        conn.close()
        flash('Task not found')
        return redirect(url_for('group_detail', group_id=group_id))

    # Check if authorized (assignee, lead, or admin)
    is_lead = conn.execute('SELECT * FROM group_members WHERE group_id = ? AND user_id = ? AND role = "lead"',
                          (group_id, user['id'])).fetchone() is not None

    if task['assigned_to'] != user['id'] and not is_lead and user['role'] != 'admin':
        conn.close()
        flash('Not authorized to complete this task')
        return redirect(url_for('group_detail', group_id=group_id))

    completed_date = datetime.datetime.now().isoformat()
    try:
        txid = record_group_task_on_chain(group_id, task_id, user['id'])
    except Exception as e:
        conn.close()
        flash('Blockchain recording failed')
        return redirect(url_for('group_detail', group_id=group_id))

    conn.execute('''UPDATE group_tasks
                   SET status = "completed", completed_date = ?, tx_id = ?
                   WHERE id = ?''',
               (completed_date, txid, task_id))

    conn.commit()
    conn.close()
    
    flash('Task marked as completed!')
    return redirect(url_for('group_detail', group_id=group_id))

@app.route('/groups/<int:group_id>/task/<int:task_id>', methods=['PUT'])
def update_task(group_id, task_id):
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    new_status = request.json.get('status')

    conn = get_db_connection()
    task = conn.execute('SELECT * FROM group_tasks WHERE id = ? AND group_id = ?', (task_id, group_id)).fetchone()

    if not task:
        conn.close()
        return jsonify({'error': 'Task not found'}), 404

    # Check if authorized (assignee, lead, or admin)
    is_lead = conn.execute('SELECT * FROM group_members WHERE group_id = ? AND user_id = ? AND role = "lead"',
                          (group_id, user['id'])).fetchone() is not None

    if task['assigned_to'] != user['id'] and not is_lead and user['role'] != 'admin':
        conn.close()
        return jsonify({'error': 'Not authorized'}), 403

    completed_date = None
    if new_status == 'completed':
        completed_date = datetime.datetime.now().isoformat()
        try:
            txid = record_group_task_on_chain(group_id, task_id, user['id'])
        except Exception as e:
            conn.close()
            return jsonify({'error': 'Blockchain recording failed'}), 500
    else:
        txid = None

    conn.execute('''UPDATE group_tasks
                   SET status = ?, completed_date = ?, tx_id = ?
                   WHERE id = ?''',
               (new_status, completed_date, txid, task_id))

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'tx_id': txid})

@app.route('/groups/<int:group_id>/task/<int:task_id>', methods=['DELETE'])
def delete_task(group_id, task_id):
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db_connection()

    # Check if user is group lead
    is_lead = conn.execute('SELECT * FROM group_members WHERE group_id = ? AND user_id = ? AND role = "lead"',
                          (group_id, user['id'])).fetchone() is not None

    if not is_lead and user['role'] != 'admin':
        conn.close()
        return jsonify({'error': 'Not authorized'}), 403

    conn.execute('DELETE FROM group_tasks WHERE id = ? AND group_id = ?', (task_id, group_id))
    conn.commit()
    conn.close()

    return jsonify({'success': True})

@app.route('/groups/<int:group_id>/milestone', methods=['POST'])
def create_milestone(group_id):
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db_connection()

    # Check if user is group lead
    is_lead = conn.execute('SELECT * FROM group_members WHERE group_id = ? AND user_id = ? AND role = "lead"',
                          (group_id, user['id'])).fetchone() is not None

    if not is_lead and user['role'] != 'admin':
        conn.close()
        return jsonify({'error': 'Not authorized'}), 403

    title = request.form.get('title')
    description = request.form.get('description')
    target_date = request.form.get('target_date')

    cursor = conn.cursor()
    cursor.execute('''INSERT INTO group_milestones
                     (group_id, title, description, target_date)
                     VALUES (?, ?, ?, ?)''',
                  (group_id, title, description, target_date))
    milestone_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'milestone_id': milestone_id})

@app.route('/groups/<int:group_id>/milestones/<int:milestone_id>/complete', methods=['POST'])
def complete_milestone(group_id, milestone_id):
    user = get_current_user()
    conn = get_db_connection()

    # Check permissions
    group = conn.execute('SELECT * FROM groups WHERE id = ?', (group_id,)).fetchone()
    if not group:
         conn.close()
         return "Group not found", 404

    is_lead = conn.execute('SELECT * FROM group_members WHERE group_id = ? AND user_id = ? AND role = "lead"',
                          (group_id, user['id'])).fetchone() is not None

    if not is_lead and user['role'] != 'admin':
        conn.close()
        flash('Unauthorized: Only Group Lead can complete milestones.')
        return redirect(url_for('group_detail', group_id=group_id))

    # Proof URL (Optional for now)
    proof_url = request.form.get('proof_url', '')
    
    # Record completion
    # In a real app, we might want to record on chain here too
    # For now, just update DB
    
    completed_time = datetime.datetime.now().isoformat()
    
    conn.execute('UPDATE group_milestones SET completed_date = ?, proof_url = ? WHERE id = ?',
               (completed_time, proof_url, milestone_id))
    conn.commit()
    conn.close()
    
    flash('Milestone marked as complete!')
    return redirect(url_for('group_detail', group_id=group_id))

@app.route('/logs')
def public_logs():
    user = get_current_user()
    if not user:
        return redirect(url_for('wallet_login'))
        
    conn = get_db_connection()
    # Join with users to get names
    logs = conn.execute('''
        SELECT t.*, u.name as user_name 
        FROM transaction_logs t 
        LEFT JOIN users u ON t.user_id = u.id 
        ORDER BY t.timestamp DESC''').fetchall()
    conn.close()
    
    return render_template('public_logs.html', logs=logs)

@app.route('/download_logs')
def download_logs():
    user = get_current_user()
    if not user:
        return redirect(url_for('wallet_login'))
        
    conn = get_db_connection()
    logs = conn.execute('''
        SELECT t.timestamp, u.name, t.action, t.details, t.tx_id
        FROM transaction_logs t 
        LEFT JOIN users u ON t.user_id = u.id 
        ORDER BY t.timestamp DESC''').fetchall()
    conn.close()
    
    import io
    import csv
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Timestamp', 'User', 'Action', 'Details', 'Transaction ID'])
    
    # Data
    for log in logs:
        writer.writerow([
            log['timestamp'], 
            log['name'] if log['name'] else 'Unknown', 
            log['action'], 
            log['details'], 
            log['tx_id']
        ])
        
    from flask import Response as FlaskResponse
    return FlaskResponse(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=campafi_logs.csv"}
    )

@app.route('/wallet')
def wallet_features():
    return render_template('wallet_features.html', TOKEN_UNIT=TOKEN_UNIT)

@app.route('/wallet/pay', methods=['POST'])
def wallet_pay():
    # Legacy form POST – redirect to wallet page (actual payment goes through API + Pera)
    flash('Please use the "Connect Wallet" button and the on-page form to send payments via Pera Wallet.', 'info')
    return redirect(url_for('wallet_features'))

@app.route('/wallet/create_asset', methods=['POST'])
def wallet_create_asset():
    flash('Please use the "Connect Wallet" button and the on-page form to create assets via Pera Wallet.', 'info')
    return redirect(url_for('wallet_features'))

@app.route('/wallet/mint_nft', methods=['POST'])
def wallet_mint_nft():
    flash('Please use the "Connect Wallet" button and the on-page form to mint NFTs via Pera Wallet.', 'info')
    return redirect(url_for('wallet_features'))

@app.route('/wallet/contract/deploy', methods=['POST'])
def wallet_contract_deploy():
    flash('Contract deployment now uses the AlgoKit CLI.  Run: python -m contracts.deploy --deploy', 'info')
    return redirect(url_for('wallet_features'))

@app.route('/wallet/contract/interact', methods=['POST'])
def wallet_contract_interact():
    flash('Smart contract interaction now goes through Pera Wallet signing.', 'info')
    return redirect(url_for('wallet_features'))

@app.route('/wallet/contract/history', methods=['POST'])
def wallet_contract_history():
    app_id = int(request.form.get('app_id'))
    result = get_contract_history(app_id)
    
    if result['success']:
        return render_template('wallet_features.html', contract_history=result['history'], app_id=app_id, TOKEN_UNIT=TOKEN_UNIT)
    else:
        flash(f'Failed to fetch history: {result.get("error")}', 'danger')
        return redirect(url_for('wallet_features'))

@app.route('/api/prepare_payment', methods=['POST'])
def prepare_payment():
    data = request.json
    sender = data.get('sender')
    receiver = data.get('receiver')
    amount = data.get('amount')
    note = data.get('note', '')

    if not all([sender, receiver, amount]):
        return jsonify({'error': 'Missing sender, receiver or amount'}), 400

    try:
        result = build_payment_txn(sender, receiver, float(amount), note)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

try:
    from google import genai
except ImportError:
    genai = None
    print("Warning: google-generativeai not installed. Chatbot will be disabled.")

# Configure Gemini Client
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY not found in environment variables.")

@app.route('/api/chat', methods=['POST'])
def chat_api():
    data = request.json
    message = data.get('message', '').strip()
    user = get_current_user() # Might be None
    
    conn = get_db_connection()
    response_text = ""
    
    # DEBUG LOGGING
    print(f"Chat request received: {message}")
    print(f"API Key present: {bool(GEMINI_API_KEY)}")
    
    # 1. GATHER CONTEXT (Internal Data)
    context_data = ""
    
    # User Info
    if user:
        # Attendance - DETAILED BREAKDOWN
        try:
            # Join sessions with records to get per-course stats
            # We need all sessions, and match with user's records
            # This query gets all sessions and counts user's presence
            course_stats = conn.execute('''
                SELECT 
                    s.course_code,
                    COUNT(s.id) as total_sessions,
                    SUM(CASE WHEN r.status = 'present' THEN 1 ELSE 0 END) as attended
                FROM attendance_sessions s
                LEFT JOIN attendance_records r ON s.id = r.session_id AND r.user_id = ?
                GROUP BY s.course_code
            ''', (user['id'],)).fetchall()
            
            if course_stats:
                context_data += f"User: {user['name']} (Role: {user['role']}).\nVerified Attendance Data:\n"
                for stat in course_stats:
                    code = stat['course_code']
                    attended = stat['attended'] if stat['attended'] else 0
                    total = stat['total_sessions']
                    pct = (attended / total * 100) if total > 0 else 0
                    context_data += f"- {code}: {attended}/{total} classes attended ({pct:.1f}%)\n"
            else:
                 context_data += f"User: {user['name']} (Role: {user['role']}). No attendance sessions recorded yet.\n"

        except Exception as e:
            print(f"Attendance Query Error: {e}")
            context_data += f"User: {user['name']}. Attendance data currently unavailable.\n"
        
        # User's Groups
        try:
            groups = conn.execute('''
                SELECT g.name FROM groups g JOIN group_members gm ON g.id = gm.group_id WHERE gm.user_id = ?
            ''', (user['id'],)).fetchall()
            group_names = [g['name'] for g in groups]
            context_data += f"Member of Groups: {', '.join(group_names)}.\n"
        except:
             pass
    else:
        context_data += "User is currently NOT logged in. Ask them to login for personal stats.\n"
        
    # DAO Info (General)
    try:
        dao_group = conn.execute('SELECT * FROM groups WHERE treasury_address IS NOT NULL LIMIT 1').fetchone()
        if dao_group:
             context_data += f"Main DAO: {dao_group['name']} (Treasury Active).\n"
    except:
        pass

    # 2. INTELLIGENT SYSTEM PROMPT (Optimized)
    system_instruction = f"""
    You are CampusBot for CampaFi.
    
    Source Data:
    {context_data}
    
    Directives:
    - Precise attendance counts.
    - Blockchain expert.
    - No hallucinations.
    """
    
    try:
        if GEMINI_API_KEY and genai:
            client = genai.Client(api_key=GEMINI_API_KEY)
            
            models_to_try = [
                'gemini-2.0-flash-lite',
                'gemini-1.5-flash',
                'gemini-2.0-flash',
            ]
            
            response = None
            last_error = None
            
            # Implementation of Retries with Exponential Backoff
            max_retries = 3
            
            for model_name in models_to_try:
                for attempt in range(max_retries):
                    try:
                        print(f"Attempting {model_name} (Attempt {attempt+1})")
                        response = client.models.generate_content(
                            model=model_name,
                            contents=f"{system_instruction}\n\nUSER QUESTION: {message}"
                        )
                        if response:
                            break
                    except Exception as e:
                        last_error = e
                        error_str = str(e).upper()
                        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                            wait_time = (attempt + 1) * 2 # 2s, 4s, 6s...
                            print(f"Rate limited. Waiting {wait_time}s...")
                            time.sleep(wait_time)
                        else:
                            # If it's not a rate limit, don't retry this model
                            print(f"Non-retryable error with {model_name}: {e}")
                            break
                
                if response:
                    print(f"Success with {model_name}")
                    break
            
            if response:
                response_text = response.text
            else:
                if "429" in str(last_error) or "RESOURCE_EXHAUSTED" in str(last_error):
                     response_text = "I'm receiving too many requests. I tried to wait, but the limit is still active. Please try again in 1 minute."
                else:
                     response_text = "I'm having trouble connecting to my AI brain. Please try again later."

        else:
            if not genai:
                response_text = "Chatbot is offline (AI library not installed)."
            else:
                response_text = "Chatbot is offline (API Key missing)."
            
    except Exception as e:
        import traceback
        print(f"Gemini Global Error: {e}")
        traceback.print_exc()
        response_text = "An unexpected error occurred."
        
    conn.close()
    return jsonify({'response': response_text})


@app.route('/api/prepare_asset_creation', methods=['POST'])
def prepare_asset_creation():
    data = request.json
    sender = data.get('sender')
    asset_name = data.get('asset_name')
    unit_name = data.get('unit_name')
    total = data.get('total')
    decimals = data.get('decimals')
    url = data.get('url')

    if not all([sender, asset_name, unit_name, total, decimals]):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        result = build_asa_create_txn(sender, unit_name, asset_name, int(total), int(decimals), url)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/prepare_nft_minting', methods=['POST'])
def prepare_nft_minting():
    data = request.json
    sender = data.get('sender')
    asset_name = data.get('asset_name')
    unit_name = data.get('unit_name')
    ipfs_url = data.get('ipfs_url')

    if not all([sender, asset_name, unit_name, ipfs_url]):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        result = build_nft_mint_txn(sender, unit_name, asset_name, ipfs_url)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/prepare_bank_deposit', methods=['POST'])
def prepare_bank_deposit():
    """Build grouped unsigned deposit txns for Pera signing."""
    data = request.json
    sender = data.get('sender')
    app_id = data.get('app_id')
    amount = data.get('amount')

    if not all([sender, app_id, amount]):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        result = build_bank_deposit_txns(sender, int(app_id), float(amount))
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/prepare_bank_withdraw', methods=['POST'])
def prepare_bank_withdraw():
    """Build unsigned withdraw txn for Pera signing."""
    data = request.json
    sender = data.get('sender')
    app_id = data.get('app_id')
    amount = data.get('amount')

    if not all([sender, app_id, amount]):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        result = build_bank_withdraw_txn(sender, int(app_id), float(amount))
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/submit_transaction', methods=['POST'])
def submit_transaction():
    """Submit a Pera-signed transaction (base64) to the Algorand network."""
    data = request.json
    signed_txn_b64 = data.get('signed_txn')
    signed_txns_b64 = data.get('signed_txns')  # for grouped txns

    if not signed_txn_b64 and not signed_txns_b64:
        return jsonify({'error': 'Missing signed transaction(s)'}), 400

    try:
        if signed_txns_b64:
            # Grouped transaction submission
            result = submit_signed_group(signed_txns_b64)
        else:
            result = submit_signed_transaction(signed_txn_b64)

        if result.get('success'):
            resp = {'txId': result['tx_id']}
            if 'asset_id' in result:
                resp['assetId'] = result['asset_id']
            if 'app_id' in result:
                resp['appId'] = result['app_id']
            return jsonify(resp)
        else:
            return jsonify({'error': result.get('error', 'Unknown error')}), 500

    except Exception as e:
        print(f"Submission Error: {e}")
        return jsonify({'error': str(e)}), 500

# ── CampusCoin ASA endpoints ──────────────────────────────────────
CAMPUS_COIN_ID = os.environ.get('CAMPUS_COIN_ID')  # set after first deploy

@app.route('/api/prepare_campus_coin_deploy', methods=['POST'])
def prepare_campus_coin_deploy():
    """Build unsigned ASA-create txn for CampusCoin (admin only)."""
    data = request.json
    sender = data.get('sender')
    if not sender:
        return jsonify({'error': 'Missing sender address'}), 400
    try:
        from contracts.campus_coin import build_campus_coin_create_txn
        result = build_campus_coin_create_txn(sender)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/campus_coin_info', methods=['GET'])
def campus_coin_info():
    """Return CampusCoin ASA details (public)."""
    if not CAMPUS_COIN_ID:
        return jsonify({'configured': False, 'message': 'CampusCoin not deployed yet'})
    try:
        from contracts.campus_coin import verify_campus_coin
        info = verify_campus_coin(int(CAMPUS_COIN_ID))
        info['configured'] = True
        return jsonify(info)
    except Exception as e:
        return jsonify({'configured': False, 'error': str(e)})

# ══════════════════════════════════════════════════════════════════════
#  LOCKBOX / TIME-LOCKED SAVINGS
# ══════════════════════════════════════════════════════════════════════

@app.route('/lockbox')
@wallet_required
def lockbox():
    """Lockbox savings goals page."""
    user = get_current_user()
    conn = get_db_connection()
    
    # Fetch all goals visible to this user (own goals + group goals they belong to)
    goals_raw = conn.execute('''
        SELECT lg.*, g.name as group_name
        FROM lockbox_goals lg
        LEFT JOIN groups g ON lg.group_id = g.id
        WHERE lg.user_id = ?
           OR lg.group_id IN (
               SELECT group_id FROM group_members WHERE user_id = ? AND status = 'accepted'
           )
        ORDER BY lg.created_date DESC
    ''', (user['id'], user['id'])).fetchall()
    
    # Fetch user's groups for the create form
    user_groups = conn.execute('''
        SELECT g.id, g.name FROM groups g
        JOIN group_members gm ON g.id = gm.group_id
        WHERE gm.user_id = ? AND gm.status = 'accepted'
    ''', (user['id'],)).fetchall()
    conn.close()
    
    import time as _time
    now_ts = int(_time.time())
    goals = []
    for g in goals_raw:
        goal = dict(g)
        goal['target_algo'] = goal['target_amount'] / 1_000_000 if goal['target_amount'] else 0
        goal['deposited_algo'] = goal['deposited_amount'] / 1_000_000 if goal['deposited_amount'] else 0
        goal['is_unlockable'] = now_ts >= goal['unlock_time']
        goal['is_creator'] = (goal['user_id'] == user['id'])
        # Format unlock date
        try:
            from datetime import datetime as _dt
            goal['unlock_date_str'] = _dt.fromtimestamp(goal['unlock_time']).strftime('%b %d, %Y %H:%M')
        except:
            goal['unlock_date_str'] = str(goal['unlock_time'])
        goals.append(goal)
    
    return render_template('lockbox.html', user=user, goals=goals, user_groups=user_groups)


@app.route('/api/lockbox/create', methods=['POST'])
@wallet_required
def lockbox_create():
    """Create a new lockbox goal and optionally build deploy txn."""
    user = get_current_user()
    data = request.json or {}
    
    name = data.get('name', '').strip()
    target_algo = float(data.get('target_algo', 0))
    unlock_timestamp = int(data.get('unlock_timestamp', 0))
    group_id = data.get('group_id') or None
    sender = data.get('sender', '').strip()
    
    if not name or target_algo <= 0 or unlock_timestamp <= 0:
        return jsonify({'error': 'Name, target amount, and unlock date required'}), 400
    
    target_microalgo = int(target_algo * 1_000_000)
    
    conn = get_db_connection()
    cursor = conn.execute(
        '''INSERT INTO lockbox_goals (user_id, group_id, name, target_amount, unlock_time, created_date)
           VALUES (?, ?, ?, ?, ?, ?)''',
        (user['id'], group_id, name, target_microalgo, unlock_timestamp,
         datetime.datetime.now().isoformat())
    )
    goal_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    log_transaction(user['id'], 'LOCKBOX_CREATE', f'Created lockbox goal: {name} (target: {target_algo} ALGO)')
    
    # Build deploy txn if sender provided
    result = {'goal_id': goal_id}
    if sender:
        try:
            txn_data = build_lockbox_deploy_txn(sender, name, target_microalgo, unlock_timestamp)
            result['txn_b64'] = txn_data['txn_b64']
        except Exception as e:
            result['deploy_note'] = f'Contract deploy skipped: {str(e)}. Goal saved off-chain.'
    
    return jsonify(result)


@app.route('/api/lockbox/confirm_deploy', methods=['POST'])
@wallet_required
def lockbox_confirm_deploy():
    """Submit signed deploy txn and update goal with app_id."""
    data = request.json or {}
    goal_id = data.get('goal_id')
    signed_b64 = data.get('signed_txn', '')
    
    if not goal_id or not signed_b64:
        return jsonify({'error': 'Missing goal_id or signed_txn'}), 400
    
    try:
        result = submit_signed_transaction(signed_b64)
        if result.get('success'):
            app_id = result.get('app_id')
            tx_id = result.get('tx_id')
            conn = get_db_connection()
            conn.execute('UPDATE lockbox_goals SET app_id = ?, tx_id = ? WHERE id = ?',
                        (app_id, tx_id, goal_id))
            conn.commit()
            conn.close()
            
            user = get_current_user()
            log_transaction(user['id'], 'LOCKBOX_DEPLOY', f'Deployed lockbox contract: App ID {app_id}', tx_id)
            
            return jsonify({'app_id': app_id, 'tx_id': tx_id})
        else:
            return jsonify({'error': result.get('error', 'Deploy failed')}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/lockbox/deposit', methods=['POST'])
@wallet_required
def lockbox_deposit():
    """Build unsigned deposit txns for a lockbox goal."""
    data = request.json or {}
    sender = data.get('sender', '')
    goal_id = data.get('goal_id')
    app_id = data.get('app_id', 0)
    amount_algo = float(data.get('amount_algo', 0))
    
    if not sender or not goal_id or amount_algo <= 0:
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        if app_id and int(app_id) > 0:
            # Use on-chain deposit (grouped txns)
            result = build_bank_deposit_txns(sender, int(app_id), amount_algo)
            return jsonify(result)
        else:
            # Off-chain only — build a simple self-payment with note
            result = build_payment_txn(sender, sender, amount_algo, 
                                       f'CampaFi Lockbox Deposit: Goal #{goal_id}')
            return jsonify({'txns_b64': [result['txn_b64']]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/lockbox/confirm_deposit', methods=['POST'])
@wallet_required
def lockbox_confirm_deposit():
    """Submit signed deposit and update goal balance."""
    data = request.json or {}
    goal_id = data.get('goal_id')
    signed_txns = data.get('signed_txns', [])
    amount_algo = float(data.get('amount_algo', 0))
    
    if not goal_id or not signed_txns:
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        if len(signed_txns) > 1:
            result = submit_signed_group(signed_txns)
        else:
            result = submit_signed_transaction(signed_txns[0])
        
        if result.get('success'):
            amount_micro = int(amount_algo * 1_000_000)
            conn = get_db_connection()
            conn.execute('UPDATE lockbox_goals SET deposited_amount = deposited_amount + ? WHERE id = ?',
                        (amount_micro, goal_id))
            conn.commit()
            conn.close()
            
            user = get_current_user()
            log_transaction(user['id'], 'LOCKBOX_DEPOSIT', 
                          f'Deposited {amount_algo} ALGO to lockbox #{goal_id}', result.get('tx_id'))
            
            return jsonify({'tx_id': result['tx_id']})
        else:
            return jsonify({'error': result.get('error', 'Deposit failed')}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/lockbox/withdraw', methods=['POST'])
@wallet_required
def lockbox_withdraw():
    """Build unsigned withdraw txn (time-lock enforced on-chain)."""
    data = request.json or {}
    sender = data.get('sender', '')
    goal_id = data.get('goal_id')
    app_id = data.get('app_id', 0)
    amount_algo = float(data.get('amount_algo', 0))
    
    if not sender or not goal_id:
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Verify unlock time has passed
    conn = get_db_connection()
    goal = conn.execute('SELECT * FROM lockbox_goals WHERE id = ?', (goal_id,)).fetchone()
    conn.close()
    
    if not goal:
        return jsonify({'error': 'Goal not found'}), 404
    
    import time as _time
    if _time.time() < goal['unlock_time']:
        return jsonify({'error': 'Funds are still locked! Unlock time has not been reached.'}), 403
    
    try:
        if app_id and int(app_id) > 0:
            result = build_bank_withdraw_txn(sender, int(app_id), amount_algo)
        else:
            result = build_payment_txn(sender, sender, 0, 
                                       f'CampaFi Lockbox Withdraw: Goal #{goal_id}')
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/lockbox/force_release', methods=['POST'])
@wallet_required
def lockbox_force_release():
    """Build unsigned force-release txn (bypasses time lock)."""
    data = request.json or {}
    sender = data.get('sender', '')
    goal_id = data.get('goal_id')
    app_id = data.get('app_id', 0)
    amount_algo = float(data.get('amount_algo', 0))
    
    user = get_current_user()
    conn = get_db_connection()
    goal = conn.execute('SELECT * FROM lockbox_goals WHERE id = ?', (goal_id,)).fetchone()
    conn.close()
    
    if not goal or goal['user_id'] != user['id']:
        return jsonify({'error': 'Only the goal creator can force-release'}), 403
    
    try:
        if app_id and int(app_id) > 0:
            result = build_bank_withdraw_txn(sender, int(app_id), amount_algo)
        else:
            result = build_payment_txn(sender, sender, 0,
                                       f'CampaFi Lockbox FORCE RELEASE: Goal #{goal_id}')
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/lockbox/confirm_withdraw', methods=['POST'])
@wallet_required
def lockbox_confirm_withdraw():
    """Submit signed withdraw/release txn and update goal status."""
    data = request.json or {}
    goal_id = data.get('goal_id')
    signed_b64 = data.get('signed_txn', '')
    force = data.get('force', False)
    
    if not goal_id or not signed_b64:
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        result = submit_signed_transaction(signed_b64)
        if result.get('success'):
            conn = get_db_connection()
            conn.execute('''UPDATE lockbox_goals SET status = 'released', released_date = ? WHERE id = ?''',
                        (datetime.datetime.now().isoformat(), goal_id))
            conn.commit()
            conn.close()
            
            user = get_current_user()
            action = 'LOCKBOX_FORCE_RELEASE' if force else 'LOCKBOX_WITHDRAW'
            log_transaction(user['id'], action, 
                          f'Released lockbox #{goal_id}', result.get('tx_id'))
            
            return jsonify({'tx_id': result['tx_id']})
        else:
            return jsonify({'error': result.get('error', 'Withdraw failed')}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════════════
#  PRIVACY-AWARE RECEIPTS (Hash Anchoring + Off-Chain Data)
# ══════════════════════════════════════════════════════════════════════

@app.route('/receipts')
@wallet_required
def receipts():
    """Privacy receipts page."""
    user = get_current_user()
    conn = get_db_connection()
    receipts = conn.execute(
        'SELECT * FROM privacy_receipts WHERE user_id = ? ORDER BY created_date DESC',
        (user['id'],)
    ).fetchall()
    conn.close()
    return render_template('receipts.html', user=user, receipts=receipts)


@app.route('/receipts/verify')
def receipts_verify_page():
    """Public verification page (accessible via QR/link)."""
    hash_param = request.args.get('hash', '')
    receipt_id = request.args.get('id', '')
    
    receipt = None
    if receipt_id:
        conn = get_db_connection()
        receipt = conn.execute('SELECT * FROM privacy_receipts WHERE id = ?', (receipt_id,)).fetchone()
        conn.close()
        if receipt:
            hash_param = receipt['data_hash']
    
    return render_template('receipts.html', 
                         user=get_current_user() or {'name': 'Guest', 'role': 'guest'},
                         receipts=[],
                         verify_hash=hash_param)


@app.route('/api/receipts/create', methods=['POST'])
@wallet_required
def receipts_create():
    """Create a privacy receipt and optionally build an anchor txn."""
    user = get_current_user()
    data = request.json or {}
    
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    json_data = data.get('json_data', '').strip()
    data_hash = data.get('data_hash', '').strip()
    anchor = data.get('anchor_on_chain', False)
    sender = data.get('sender', '').strip()
    
    if not title or not json_data or not data_hash:
        return jsonify({'error': 'Title, JSON data, and hash required'}), 400
    
    # Verify hash matches
    computed = hashlib.sha256(json_data.encode()).hexdigest()
    if computed != data_hash:
        return jsonify({'error': 'Hash mismatch — computed hash does not match provided hash'}), 400
    
    conn = get_db_connection()
    cursor = conn.execute(
        '''INSERT INTO privacy_receipts (user_id, title, description, json_data, data_hash, created_date)
           VALUES (?, ?, ?, ?, ?, ?)''',
        (user['id'], title, description, json_data, data_hash,
         datetime.datetime.now().isoformat())
    )
    receipt_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    log_transaction(user['id'], 'RECEIPT_CREATE', f'Created receipt: {title} (hash: {data_hash[:16]}...)')
    
    result = {'receipt_id': receipt_id, 'data_hash': data_hash}
    
    # Build anchor txn (zero-ALGO self-payment with hash in note)
    if anchor and sender:
        try:
            note = f'CampaFi Receipt Anchor|{data_hash}|{title}'
            txn_data = build_payment_txn(sender, sender, 0, note)
            result['txn_b64'] = txn_data['txn_b64']
        except Exception as e:
            result['anchor_note'] = f'On-chain anchor skipped: {str(e)}'
    
    return jsonify(result)


@app.route('/api/receipts/anchor', methods=['POST'])
@wallet_required
def receipts_anchor():
    """Submit signed anchor txn and update receipt with tx_id."""
    data = request.json or {}
    receipt_id = data.get('receipt_id')
    signed_b64 = data.get('signed_txn', '')
    
    if not receipt_id or not signed_b64:
        return jsonify({'error': 'Missing receipt_id or signed_txn'}), 400
    
    try:
        result = submit_signed_transaction(signed_b64)
        if result.get('success'):
            tx_id = result['tx_id']
            conn = get_db_connection()
            conn.execute('UPDATE privacy_receipts SET tx_id = ? WHERE id = ?',
                        (tx_id, receipt_id))
            conn.commit()
            conn.close()
            
            user = get_current_user()
            log_transaction(user['id'], 'RECEIPT_ANCHOR', 
                          f'Anchored receipt #{receipt_id} on-chain', tx_id)
            
            return jsonify({'tx_id': tx_id})
        else:
            return jsonify({'error': result.get('error', 'Anchor failed')}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/receipts/verify', methods=['POST'])
def receipts_verify():
    """Verify a receipt hash against stored records and on-chain data."""
    data = request.json or {}
    data_hash = data.get('data_hash', '').strip()
    json_data = data.get('json_data', '').strip()
    
    if not data_hash and json_data:
        data_hash = hashlib.sha256(json_data.encode()).hexdigest()
    
    if not data_hash:
        return jsonify({'verified': False, 'message': 'No hash provided'}), 400
    
    conn = get_db_connection()
    receipt = conn.execute(
        'SELECT * FROM privacy_receipts WHERE data_hash = ?', (data_hash,)
    ).fetchone()
    conn.close()
    
    if receipt:
        result = {
            'verified': True,
            'title': receipt['title'],
            'tx_id': receipt['tx_id'],
            'created_date': receipt['created_date'],
            'on_chain': bool(receipt['tx_id']),
        }
        
        # If anchored on-chain, we can also verify via indexer
        if receipt['tx_id']:
            try:
                from algorand.connect import get_indexer
                idx = get_indexer()
                txn_info = idx.search_transactions(txid=receipt['tx_id'])
                txns = txn_info.get('transactions', [])
                if txns:
                    note = txns[0].get('note', '')
                    if note:
                        import base64 as _b64
                        decoded_note = _b64.b64decode(note).decode('utf-8', errors='ignore')
                        if data_hash in decoded_note:
                            result['chain_verified'] = True
            except Exception:
                pass  # Indexer lookup is best-effort
        
        return jsonify(result)
    else:
        return jsonify({
            'verified': False,
            'message': 'Hash not found in any stored receipt'
        })


# ══════════════════════════════════════════════════════════════════════
#  REAL-TIME CHAIN EVENT VISUALISER
# ══════════════════════════════════════════════════════════════════════

@app.route('/chain-events')
@wallet_required
def chain_events():
    """Chain event visualiser page."""
    user = get_current_user()
    return render_template('chain_events.html', user=user)


@app.route('/api/chain_events', methods=['GET'])
def api_chain_events():
    """Fetch recent chain events via the Algorand Indexer.
    Supports filtering by type and pagination via after_round."""
    from algorand.connect import get_indexer
    
    after_round = request.args.get('after_round', 0, type=int)
    event_type = request.args.get('type', '')  # pay, axfer, appl, acfg
    limit = request.args.get('limit', 20, type=int)
    limit = min(limit, 50)  # Cap at 50
    
    try:
        idx = get_indexer()
        
        # Build indexer query
        # We search recent transactions across the network
        # For a campus app, you'd filter by known app IDs / ASA IDs
        kwargs = {'limit': limit}
        
        if after_round > 0:
            kwargs['min_round'] = after_round + 1
        
        if event_type == 'pay':
            kwargs['txn_type'] = 'pay'
        elif event_type == 'axfer':
            kwargs['txn_type'] = 'axfer'
        elif event_type == 'appl':
            kwargs['txn_type'] = 'appl'
        elif event_type == 'acfg':
            kwargs['txn_type'] = 'acfg'
        
        # Get campus-relevant app IDs from DB for focused queries
        campus_note_prefix = 'CampaFi'
        kwargs['note_prefix'] = base64.b64encode(campus_note_prefix.encode()).decode()
        
        try:
            response = idx.search_transactions(**kwargs)
        except Exception:
            # Fallback: broader query without note filter
            kwargs.pop('note_prefix', None)
            response = idx.search_transactions(**kwargs)
        
        txns = response.get('transactions', [])
        events = []
        last_round = after_round
        
        for txn in txns:
            tx_type = txn.get('tx-type', 'unknown')
            confirmed_round = txn.get('confirmed-round', 0)
            if confirmed_round > last_round:
                last_round = confirmed_round
            
            # Parse timestamp
            round_time = txn.get('round-time', 0)
            time_str = ''
            if round_time:
                try:
                    from datetime import datetime as _dt
                    time_str = _dt.fromtimestamp(round_time).strftime('%H:%M:%S')
                except:
                    time_str = str(round_time)
            
            # Decode note
            note_str = ''
            if txn.get('note'):
                try:
                    note_str = base64.b64decode(txn['note']).decode('utf-8', errors='ignore')
                except:
                    pass
            
            event = {
                'tx_id': txn.get('id', ''),
                'type': tx_type,
                'sender': txn.get('sender', ''),
                'round': confirmed_round,
                'time': time_str,
                'note': note_str,
            }
            
            # Type-specific fields
            if tx_type == 'pay':
                pay = txn.get('payment-transaction', {})
                event['receiver'] = pay.get('receiver', '')
                event['amount'] = pay.get('amount', 0) / 1_000_000
            elif tx_type == 'axfer':
                axfer = txn.get('asset-transfer-transaction', {})
                event['receiver'] = axfer.get('receiver', '')
                event['asset_id'] = axfer.get('asset-id', 0)
                event['asset_amount'] = axfer.get('amount', 0)
                event['asset_name'] = ''  # Would need extra lookup
            elif tx_type == 'appl':
                appl = txn.get('application-transaction', {})
                event['app_id'] = appl.get('application-id', 0)
                event['receiver'] = ''  # App calls don't have a receiver per se
            elif tx_type == 'acfg':
                acfg = txn.get('asset-config-transaction', {})
                event['asset_id'] = acfg.get('asset-id', 0)
                event['receiver'] = ''  # Config txns
            
            events.append(event)
        
        return jsonify({
            'events': events,
            'last_round': last_round,
            'count': len(events)
        })
    
    except Exception as e:
        return jsonify({'events': [], 'error': str(e), 'last_round': after_round})


if __name__ == '__main__':
    app.run(debug=True)