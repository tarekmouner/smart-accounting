import os
import re
import sqlite3
import hashlib
from datetime import datetime
from decimal import Decimal, InvalidOperation

import pandas as pd


DB_PATH = "data/app.db"
os.makedirs("data", exist_ok=True)


def get_conn():
    conn = sqlite3.connect(
        DB_PATH,
        timeout=30,
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password):
    # متوافق مع المستخدمين الموجودين في النسخة السابقة.
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def now_text():
    return datetime.now().isoformat()


def fetch_rows(sql, params=()):
    conn = get_conn()
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def execute_write(sql, params=()):
    conn = get_conn()
    try:
        with conn:
            cursor = conn.execute(sql, params)
            return cursor.lastrowid
    finally:
        conn.close()


def init_db():
    conn = get_conn()

    try:
        with conn:
            conn.executescript("""
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
                );

                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT,
                    role TEXT DEFAULT 'user',
                    company_id INTEGER,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    permission TEXT NOT NULL,
                    allowed INTEGER DEFAULT 1,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                );

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
                );

                CREATE TABLE IF NOT EXISTS journal_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER NOT NULL,
                    entry_date TEXT NOT NULL,
                    description TEXT,
                    source TEXT,
                    created_by TEXT,
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS journal_lines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id INTEGER NOT NULL,
                    account_code TEXT NOT NULL,
                    account_name TEXT,
                    debit REAL DEFAULT 0,
                    credit REAL DEFAULT 0,
                    memo TEXT,
                    FOREIGN KEY(entry_id) REFERENCES journal_entries(id)
                );

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
                );

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
                );

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
                );

                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    due_date TEXT NOT NULL,
                    notes TEXT,
                    status TEXT DEFAULT 'مفتوح',
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER,
                    username TEXT,
                    role TEXT,
                    message TEXT,
                    created_at TEXT
                );
            """)

            user = conn.execute(
                "SELECT id FROM users WHERE username = ?",
                ("tarek",),
            ).fetchone()

            if user is None:
                conn.execute("""
                    INSERT INTO users (
                        username,
                        password_hash,
                        full_name,
                        role,
                        company_id,
                        is_active,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    "tarek",
                    hash_password("159019"),
                    "طارق - مدير النظام",
                    "admin",
                    None,
                    1,
                    now_text(),
                ))
    finally:
        conn.close()


def add_company(
    name,
    tax_number="",
    address="",
    phone="",
    email="",
    currency="EGP",
):
    name = str(name).strip()

    if not name:
        raise ValueError("لازم تكتب اسم الشركة.")

    return execute_write("""
        INSERT INTO companies (
            name, tax_number, address, phone,
            email, currency, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        name,
        tax_number,
        address,
        phone,
        email,
        currency,
        now_text(),
    ))


def get_companies():
    return fetch_rows(
        "SELECT * FROM companies ORDER BY id DESC"
    )


# ---------- استيراد شجرة الحسابات ----------

COA_ALIASES = {
    "code": [
        "code",
        "account code",
        "account_code",
        "الكود",
        "كود",
        "كود الحساب",
        "رقم الحساب",
    ],
    "name": [
        "name",
        "account name",
        "account_name",
        "اسم الحساب",
        "الحساب",
    ],
    "type": [
        "type",
        "account type",
        "account_type",
        "النوع",
        "نوع الحساب",
    ],
    "parent_code": [
        "parent_code",
        "parent code",
        "parent account code",
        "الحساب الأب",
        "كود الحساب الأب",
        "رقم الحساب الأب",
    ],
    "level": [
        "level",
        "المستوى",
        "مستوى الحساب",
    ],
    "explanation": [
        "explanation",
        "description",
        "الشرح",
        "الوصف",
        "شرح الحساب",
    ],
}


def normalize_header(value):
    text = str(value).replace("\ufeff", "").strip().lower()
    text = re.sub(r"[\u064b-\u065f\u0670]", "", text)

    for old, new in (
        ("أ", "ا"),
        ("إ", "ا"),
        ("آ", "ا"),
        ("ـ", ""),
        ("_", " "),
    ):
        text = text.replace(old, new)

    return re.sub(r"\s+", " ", text)


def clean_text(value):
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def clean_code(value):
    text = clean_text(value)

    if re.fullmatch(r"[0-9]+\.0+", text):
        return text.split(".")[0]

    return text


def detect_coa_columns(columns):
    lookup = {}

    for target, aliases in COA_ALIASES.items():
        for alias in aliases:
            lookup[normalize_header(alias)] = target

    return {
        column: lookup.get(normalize_header(column))
        for column in columns
    }


def prepare_coa(df):
    if df is None or df.empty:
        raise ValueError("الملف أو الشيت المختار فاضي.")

    frame = df.copy()
    detected = detect_coa_columns(frame.columns)
    rename_map = {
        original: target
        for original, target in detected.items()
        if target is not None
    }

    frame = frame.rename(columns=rename_map)

    recognized = [
        column
        for column in frame.columns
        if column in COA_ALIASES
    ]

    if len(recognized) != len(set(recognized)):
        raise ValueError(
            "فيه أكتر من عمود اتعرف بنفس المعنى. "
            "مثلًا عمود باسم الكود وعمود تاني باسم code. "
            "خلي عمود واحد فقط لكل حقل."
        )

    missing = {"code", "name"} - set(frame.columns)

    if missing:
        raise ValueError(
            "لازم الملف يحتوي على عمود الكود وعمود اسم الحساب. "
            "ممكن تسميهم: الكود واسم الحساب، أو code وname."
        )

    records = []
    seen_codes = set()

    for row_number, (_, row) in enumerate(
        frame.iterrows(),
        start=2,
    ):
        code = clean_code(row.get("code"))
        name = clean_text(row.get("name"))

        if not code and not name:
            continue

        if not code or not name:
            raise ValueError(
                f"الصف رقم {row_number}: كود الحساب أو اسمه ناقص."
            )

        if code in seen_codes:
            raise ValueError(
                f"كود الحساب {code} متكرر في الملف. "
                "راجع التكرار، ولو الملف فيه أكتر من شركة "
                "افصل حسابات كل شركة في ملف أو شيت مستقل."
            )

        seen_codes.add(code)

        raw_level = clean_text(row.get("level", ""))

        try:
            level_value = Decimal(raw_level or "1")

            if (
                not level_value.is_finite()
                or level_value < 1
                or level_value != level_value.to_integral_value()
            ):
                raise ValueError

            level = int(level_value)
        except (InvalidOperation, ValueError, OverflowError):
            raise ValueError(
                f"الصف رقم {row_number}: "
                "مستوى الحساب لازم يكون رقم صحيح أكبر من صفر."
            )

        parent_code = clean_code(row.get("parent_code", ""))

        if parent_code == code:
            raise ValueError(
                f"الحساب {code} مش ممكن يكون هو الحساب الأب لنفسه."
            )

        records.append({
            "code": code,
            "name": name,
            "type": clean_text(row.get("type", "")),
            "parent_code": parent_code,
            "level": level,
            "explanation": clean_text(
                row.get("explanation", "")
            ),
        })

    if not records:
        raise ValueError("مفيش حسابات صالحة للحفظ في الملف.")

    return pd.DataFrame(records)


def save_coa(company_id, df):
    prepared = prepare_coa(df)
    conn = get_conn()

    try:
        with conn:
            company = conn.execute(
                "SELECT id FROM companies WHERE id = ?",
                (company_id,),
            ).fetchone()

            if company is None:
                raise ValueError("الشركة المختارة مش موجودة.")

            existing_codes = {
                row["code"]
                for row in conn.execute(
                    "SELECT code FROM accounts WHERE company_id = ?",
                    (company_id,),
                ).fetchall()
            }

            added = 0
            updated = 0

            for row in prepared.to_dict("records"):
                if row["code"] in existing_codes:
                    updated += 1
                else:
                    added += 1

                conn.execute("""
                    INSERT INTO accounts (
                        company_id,
                        code,
                        name,
                        type,
                        parent_code,
                        level,
                        explanation,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)

                    ON CONFLICT(company_id, code)
                    DO UPDATE SET
                        name = excluded.name,
                        type = excluded.type,
                        parent_code = excluded.parent_code,
                        level = excluded.level,
                        explanation = excluded.explanation
                """, (
                    company_id,
                    row["code"],
                    row["name"],
                    row["type"],
                    row["parent_code"],
                    row["level"],
                    row["explanation"],
                    now_text(),
                ))

        return {
            "total": len(prepared),
            "added": added,
            "updated": updated,
        }
    finally:
        conn.close()


def get_accounts(company_id):
    return fetch_rows("""
        SELECT *
        FROM accounts
        WHERE company_id = ?
        ORDER BY code
    """, (company_id,))


def search_accounts(company_id, keyword):
    keyword = f"%{str(keyword).strip()}%"

    return fetch_rows("""
        SELECT *
        FROM accounts
        WHERE company_id = ?
          AND (
              code LIKE ?
              OR name LIKE ?
              OR explanation LIKE ?
          )
        ORDER BY code
    """, (company_id, keyword, keyword, keyword))


# ---------- القيود ----------

def parse_amount(value):
    try:
        amount = Decimal(str(value or 0))

        if not amount.is_finite() or amount < 0:
            raise ValueError

        if amount != amount.quantize(Decimal("0.01")):
            raise ValueError

        return amount
    except (InvalidOperation, ValueError):
        raise ValueError(
            "المبلغ لازم يكون رقم موجب أو صفر، "
            "وبحد أقصى رقمين بعد العلامة العشرية."
        )


def save_journal_entry(
    company_id,
    entry_date,
    description,
    lines,
    username,
    source="يدوي",
):
    clean_lines = []

    for line in lines:
        debit = parse_amount(line.get("debit", 0))
        credit = parse_amount(line.get("credit", 0))

        if debit == 0 and credit == 0:
            continue

        if debit > 0 and credit > 0:
            raise ValueError(
                "سطر القيد الواحد لازم يكون مدين أو دائن، مش الاتنين."
            )

        code = clean_code(line.get("account_code"))

        if not code:
            raise ValueError("لازم تختار حساب لكل سطر.")

        clean_lines.append({
            "code": code,
            "debit": debit,
            "credit": credit,
            "memo": clean_text(line.get("memo", "")),
        })

    if len(clean_lines) < 2:
        raise ValueError("القيد لازم يحتوي على سطرين فعليين على الأقل.")

    total_debit = sum(
        (line["debit"] for line in clean_lines),
        Decimal("0"),
    )
    total_credit = sum(
        (line["credit"] for line in clean_lines),
        Decimal("0"),
    )

    if total_debit != total_credit:
        raise ValueError(
            f"القيد غير متوازن: المدين {total_debit} "
            f"والدائن {total_credit}."
        )

    conn = get_conn()

    try:
        with conn:
            for line in clean_lines:
                account = conn.execute("""
                    SELECT name FROM accounts
                    WHERE company_id = ? AND code = ?
                """, (company_id, line["code"])).fetchone()

                if account is None:
                    raise ValueError(
                        f"الحساب {line['code']} مش موجود في شجرة الشركة."
                    )

                line["name"] = account["name"]

            cursor = conn.execute("""
                INSERT INTO journal_entries (
                    company_id, entry_date, description,
                    source, created_by, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                company_id,
                entry_date,
                description,
                source,
                username,
                now_text(),
            ))

            entry_id = cursor.lastrowid

            for line in clean_lines:
                conn.execute("""
                    INSERT INTO journal_lines (
                        entry_id, account_code, account_name,
                        debit, credit, memo
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    entry_id,
                    line["code"],
                    line["name"],
                    float(line["debit"]),
                    float(line["credit"]),
                    line["memo"],
                ))

        return entry_id
    finally:
        conn.close()


def get_journal_entries(company_id):
    conn = get_conn()

    try:
        entries = conn.execute("""
            SELECT * FROM journal_entries
            WHERE company_id = ?
            ORDER BY entry_date DESC, id DESC
        """, (company_id,)).fetchall()

        result = []

        for entry in entries:
            lines = conn.execute("""
                SELECT * FROM journal_lines
                WHERE entry_id = ?
                ORDER BY id
            """, (entry["id"],)).fetchall()

            result.append({
                "entry": dict(entry),
                "lines": [dict(line) for line in lines],
            })

        return result
    finally:
        conn.close()


# ---------- العملاء والموردين ----------

def add_party(
    company_id,
    party_type,
    name,
    phone="",
    email="",
    tax_number="",
    address="",
    notes="",
):
    if not str(name).strip():
        raise ValueError("لازم تكتب اسم العميل أو المورد.")

    return execute_write("""
        INSERT INTO parties (
            company_id, party_type, name, phone,
            email, tax_number, address, notes, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        company_id,
        party_type,
        str(name).strip(),
        phone,
        email,
        tax_number,
        address,
        notes,
        now_text(),
    ))


def get_parties(company_id, party_type=None):
    if party_type:
        return fetch_rows("""
            SELECT * FROM parties
            WHERE company_id = ? AND party_type = ?
            ORDER BY name
        """, (company_id, party_type))

    return fetch_rows("""
        SELECT * FROM parties
        WHERE company_id = ?
        ORDER BY name
    """, (company_id,))


def validate_party_company(company_id, party_id):
    rows = fetch_rows("""
        SELECT id FROM parties
        WHERE id = ? AND company_id = ?
    """, (party_id, company_id))

    if not rows:
        raise ValueError(
            "العميل أو المورد مش تابع للشركة المختارة."
        )


# ---------- الفواتير ----------

def add_invoice(
    company_id,
    invoice_type,
    party_id,
    invoice_number,
    invoice_date,
    due_date,
    amount,
    paid_amount=0,
    notes="",
):
    validate_party_company(company_id, party_id)

    amount = parse_amount(amount)
    paid_amount = parse_amount(paid_amount)

    if amount <= 0:
        raise ValueError("قيمة الفاتورة لازم تكون أكبر من صفر.")

    if paid_amount > amount:
        raise ValueError(
            "المدفوع أكبر من قيمة الفاتورة. "
            "راجع المبلغ أو سجل الدفعة الزائدة بشكل منفصل."
        )

    if paid_amount == amount:
        status = "مدفوعة"
    elif paid_amount > 0:
        status = "مدفوعة جزئيًا"
    else:
        status = "غير مدفوعة"

    return execute_write("""
        INSERT INTO invoices (
            company_id, invoice_type, party_id,
            invoice_number, invoice_date, due_date,
            amount, paid_amount, status, notes, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        company_id,
        invoice_type,
        party_id,
        invoice_number,
        invoice_date,
        due_date,
        float(amount),
        float(paid_amount),
        status,
        notes,
        now_text(),
    ))


def get_invoices(company_id):
    return fetch_rows("""
        SELECT i.*, p.name AS party_name
        FROM invoices i
        LEFT JOIN parties p
          ON i.party_id = p.id
         AND i.company_id = p.company_id
        WHERE i.company_id = ?
        ORDER BY i.due_date ASC
    """, (company_id,))


# ---------- العقود ----------

def add_contract(
    company_id,
    party_id,
    title,
    contract_date,
    start_date,
    end_date,
    amount,
    payment_terms="",
    notes="",
):
    validate_party_company(company_id, party_id)
    amount = parse_amount(amount)

    return execute_write("""
        INSERT INTO contracts (
            company_id, party_id, title,
            contract_date, start_date, end_date,
            amount, payment_terms, notes, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        company_id,
        party_id,
        title,
        contract_date,
        start_date,
        end_date,
        float(amount),
        payment_terms,
        notes,
        now_text(),
    ))


def get_contracts(company_id):
    return fetch_rows("""
        SELECT c.*, p.name AS party_name
        FROM contracts c
        LEFT JOIN parties p
          ON c.party_id = p.id
         AND c.company_id = p.company_id
        WHERE c.company_id = ?
        ORDER BY c.end_date ASC
    """, (company_id,))


# ---------- التنبيهات ----------

def add_reminder(company_id, title, due_date, notes=""):
    if not str(title).strip():
        raise ValueError("لازم تكتب عنوان التنبيه.")

    return execute_write("""
        INSERT INTO reminders (
            company_id, title, due_date,
            notes, status, created_at
        )
        VALUES (?, ?, ?, ?, 'مفتوح', ?)
    """, (
        company_id,
        title,
        due_date,
        notes,
        now_text(),
    ))


def get_reminders(company_id):
    return fetch_rows("""
        SELECT * FROM reminders
        WHERE company_id = ?
        ORDER BY due_date ASC
    """, (company_id,))


# ---------- المحادثات ----------

def save_chat(company_id, username, role, message):
    return execute_write("""
        INSERT INTO chat_messages (
            company_id, username, role,
            message, created_at
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        company_id,
        username,
        role,
        message,
        now_text(),
    ))


init_db()
