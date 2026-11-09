import os
import sqlite3
import hashlib
import pandas as pd
from datetime import datetime, date

DB_PATH = "data/app.db"
os.makedirs("data", exist_ok=True)


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        tax_number TEXT,
        address TEXT,
        phone TEXT,
        email TEXT,
        currency TEXT DEFAULT 'EGP',
        logo_path TEXT,
        created_at TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT,
        role TEXT DEFAULT 'user',
        company_id INTEGER,
        is_active INTEGER DEFAULT 1,
        created_at TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS permissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        permission TEXT NOT NULL,
        allowed INTEGER DEFAULT 1,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        code TEXT NOT NULL,
        name TEXT NOT NULL,
        type TEXT,
        parent_code TEXT,
        level INTEGER DEFAULT 1,
        explanation TEXT,
        created_at TEXT,
        UNIQUE(company_id, code)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS journal_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        entry_date TEXT NOT NULL,
        description TEXT,
        source TEXT,
        created_by TEXT,
        created_at TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS journal_lines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_id INTEGER NOT NULL,
        account_code TEXT NOT NULL,
        account_name TEXT,
        debit REAL DEFAULT 0,
        credit REAL DEFAULT 0,
        memo TEXT,
        FOREIGN KEY(entry_id) REFERENCES journal_entries(id)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS parties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        party_type TEXT NOT NULL,
        name TEXT NOT NULL,
        phone TEXT,
        email TEXT,
        tax_number TEXT,
        address TEXT,
        notes TEXT,
        created_at TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        invoice_type TEXT NOT NULL,
        party_id INTEGER NOT NULL,
        invoice_number TEXT,
        invoice_date TEXT,
        due_date TEXT,
        amount REAL DEFAULT 0,
        paid_amount REAL DEFAULT 0,
        status TEXT DEFAULT 'غير مدفوعة',
        notes TEXT,
        created_at TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS contracts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        party_id INTEGER NOT NULL,
        title TEXT,
        contract_date TEXT,
        start_date TEXT,
        end_date TEXT,
        amount REAL DEFAULT 0,
        payment_terms TEXT,
        notes TEXT,
        created_at TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        due_date TEXT NOT NULL,
        notes TEXT,
        status TEXT DEFAULT 'مفتوح',
        created_at TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER,
        username TEXT,
        role TEXT,
        message TEXT,
        created_at TEXT
    )
    """)

    # المستخدم الأساسي
    c.execute("SELECT COUNT(*) FROM users WHERE username = 'tarek'")
    if c.fetchone()[0] == 0:
        c.execute("""
            INSERT INTO users (username, password_hash, full_name, role, company_id, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            "tarek",
            hash_password("159019"),
            "طارق - مدير النظام",
            "admin",
            None,
            1,
            datetime.now().isoformat()
        ))

    conn.commit()
    conn.close()


def add_company(name, tax_number="", address="", phone="", email="", currency="EGP"):
    conn = get_conn()
    conn.execute("""
        INSERT INTO companies (name, tax_number, address, phone, email, currency, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, tax_number, address, phone, email, currency, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_companies():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM companies ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_coa(company_id, df):
    """
    df لازم يكون فيه الأعمدة:
    code, name
    واختياري: type, parent_code, level, explanation
    """
    required = {"code", "name"}
    df.columns = [str(c).strip().lower() for c in df.columns]

    if not required.issubset(set(df.columns)):
        raise ValueError("ملف الإكسل لازم يحتوي على عمودين على الأقل: code و name")

    conn = get_conn()
    conn.execute("DELETE FROM accounts WHERE company_id = ?", (company_id,))

    for _, row in df.iterrows():
        code = str(row.get("code", "")).strip()
        name = str(row.get("name", "")).strip()

        if not code or not name:
            continue

        conn.execute("""
            INSERT OR REPLACE INTO accounts
            (company_id, code, name, type, parent_code, level, explanation, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            company_id,
            code,
            name,
            str(row.get("type", "") or ""),
            str(row.get("parent_code", "") or ""),
            int(row.get("level", 1) or 1),
            str(row.get("explanation", "") or ""),
            datetime.now().isoformat()
        ))

    conn.commit()
    conn.close()


def get_accounts(company_id):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM accounts
        WHERE company_id = ?
        ORDER BY code
    """, (company_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_accounts(company_id, keyword):
    keyword = f"%{keyword.strip()}%"
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM accounts
        WHERE company_id = ?
        AND (code LIKE ? OR name LIKE ? OR explanation LIKE ?)
        ORDER BY code
    """, (company_id, keyword, keyword, keyword)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_journal_entry(company_id, entry_date, description, lines, username, source="يدوي"):
    total_debit = sum(float(x.get("debit", 0) or 0) for x in lines)
    total_credit = sum(float(x.get("credit", 0) or 0) for x in lines)

    if abs(total_debit - total_credit) > 0.01:
        raise ValueError("القيد غير متوازن: إجمالي مدين لا يساوي إجمالي دائن")

    conn = get_conn()
    cur = conn.execute("""
        INSERT INTO journal_entries
        (company_id, entry_date, description, source, created_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (company_id, entry_date, description, source, username, datetime.now().isoformat()))

    entry_id = cur.lastrowid

    for line in lines:
        conn.execute("""
            INSERT INTO journal_lines
            (entry_id, account_code, account_name, debit, credit, memo)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            entry_id,
            line.get("account_code", ""),
            line.get("account_name", ""),
            float(line.get("debit", 0) or 0),
            float(line.get("credit", 0) or 0),
            line.get("memo", "")
        ))

    conn.commit()
    conn.close()
    return entry_id


def get_journal_entries(company_id):
    conn = get_conn()
    entries = conn.execute("""
        SELECT * FROM journal_entries
        WHERE company_id = ?
        ORDER BY entry_date DESC, id DESC
    """, (company_id,)).fetchall()

    result = []
    for e in entries:
        lines = conn.execute("""
            SELECT * FROM journal_lines WHERE entry_id = ?
        """, (e["id"],)).fetchall()
        result.append({
            "entry": dict(e),
            "lines": [dict(l) for l in lines]
        })

    conn.close()
    return result


def add_party(company_id, party_type, name, phone="", email="", tax_number="", address="", notes=""):
    conn = get_conn()
    conn.execute("""
        INSERT INTO parties
        (company_id, party_type, name, phone, email, tax_number, address, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (company_id, party_type, name, phone, email, tax_number, address, notes, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_parties(company_id, party_type=None):
    conn = get_conn()
    if party_type:
        rows = conn.execute("""
            SELECT * FROM parties
            WHERE company_id = ? AND party_type = ?
            ORDER BY name
        """, (company_id, party_type)).fetchall()
    else:
        rows = conn.execute("""
            SELECT * FROM parties
            WHERE company_id = ?
            ORDER BY name
        """, (company_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_invoice(company_id, invoice_type, party_id, invoice_number, invoice_date, due_date, amount, paid_amount=0, notes=""):
    status = "مدفوعة" if float(paid_amount) >= float(amount) and float(amount) > 0 else "غير مدفوعة"

    conn = get_conn()
    conn.execute("""
        INSERT INTO invoices
        (company_id, invoice_type, party_id, invoice_number, invoice_date, due_date, amount, paid_amount, status, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (company_id, invoice_type, party_id, invoice_number, invoice_date, due_date, amount, paid_amount, status, notes, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_invoices(company_id):
    conn = get_conn()
    rows = conn.execute("""
        SELECT i.*, p.name AS party_name
        FROM invoices i
        LEFT JOIN parties p ON i.party_id = p.id
        WHERE i.company_id = ?
        ORDER BY i.due_date ASC
    """, (company_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_contract(company_id, party_id, title, contract_date, start_date, end_date, amount, payment_terms="", notes=""):
    conn = get_conn()
    conn.execute("""
        INSERT INTO contracts
        (company_id, party_id, title, contract_date, start_date, end_date, amount, payment_terms, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (company_id, party_id, title, contract_date, start_date, end_date, amount, payment_terms, notes, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_contracts(company_id):
    conn = get_conn()
    rows = conn.execute("""
        SELECT c.*, p.name AS party_name
        FROM contracts c
        LEFT JOIN parties p ON c.party_id = p.id
        WHERE c.company_id = ?
        ORDER BY c.end_date ASC
    """, (company_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_reminder(company_id, title, due_date, notes=""):
    conn = get_conn()
    conn.execute("""
        INSERT INTO reminders (company_id, title, due_date, notes, status, created_at)
        VALUES (?, ?, ?, ?, 'مفتوح', ?)
    """, (company_id, title, due_date, notes, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_reminders(company_id):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM reminders
        WHERE company_id = ?
        ORDER BY due_date ASC
    """, (company_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_chat(company_id, username, role, message):
    conn = get_conn()
    conn.execute("""
        INSERT INTO chat_messages (company_id, username, role, message, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (company_id, username, role, message, datetime.now().isoformat()))
    conn.commit()
    conn.close()


init_db()
