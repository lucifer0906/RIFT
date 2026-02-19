"""
CampusTrust – Wallet Authentication Utilities
===============================================
Sign-In With Algorand (SIWA) helpers.
All authentication is wallet-based — no passwords.
"""

import os
import time
import base64
from functools import wraps
from flask import session, redirect, url_for, jsonify, request


def wallet_required(f):
    """Decorator: redirect to wallet login page if user is not authenticated."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('wallet_login'))
        return f(*args, **kwargs)
    return decorated_function


def wallet_required_api(f):
    """Decorator: return 401 JSON if user is not authenticated (for API routes)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required. Connect your wallet.'}), 401
        return f(*args, **kwargs)
    return decorated_function
