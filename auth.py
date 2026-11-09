import streamlit as st
import db
from datetime import datetime

PERMISSIONS = [
    "عرض الشركات",
    "إضافة شركة",
    "إدارة شجرة الحسابات",
    "إنشاء قيود",
    "عرض القيود",
    "إدارة العملاء والموردين",
    "إدارة الفواتير",
    "إدارة العقود",
    "إدارة التنبيهات",
    "استخدام المساعد الذكي",
    "إدارة المستخدمين والصلاحيات",
    "إعدادات النظام",
]


def login_user(username, password):
    conn = db.get_conn()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ? AND is_active = 1",
        (username,)
    ).fetchone()
    conn.close()

    if not user:
        return None

    if user["password_hash"] != db.hash_password(password):
        return None

    return dict(user)


def get_user_permissions(user):
    if user["role"] == "admin":
        return PERMISSIONS

    conn = db.get_conn()
    rows = conn.execute(
        "SELECT permission, allowed FROM permissions WHERE user_id = ?",
        (user["id"],)
    ).fetchall()
    conn.close()

    return [r["permission"] for r in rows if r["allowed"] == 1]


def has_permission(user, permission):
    return permission in get_user_permissions(user)


def create_user(username, password, full_name, role, company_id=None):
    conn = db.get_conn()
    try:
        conn.execute("""
            INSERT INTO users (username, password_hash, full_name, role, company_id, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, 1, ?)
        """, (
            username,
            db.hash_password(password),
            full_name,
            role,
            company_id,
            datetime.now().isoformat()
        ))
        conn.commit()
        return True, "تم إنشاء المستخدم بنجاح"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def save_permissions(user_id, selected_permissions):
    conn = db.get_conn()
    conn.execute("DELETE FROM permissions WHERE user_id = ?", (user_id,))

    for perm in selected_permissions:
        conn.execute("""
            INSERT INTO permissions (user_id, permission, allowed)
            VALUES (?, ?, 1)
        """, (user_id, perm))

    conn.commit()
    conn.close()


def login_page():
    st.title("🔐 تسجيل الدخول")
    st.caption("نظام المحاسبة الذكي متعدد الشركات")

    username = st.text_input("اسم المستخدم")
    password = st.text_input("كلمة السر", type="password")

    if st.button("دخول", use_container_width=True):
        user = login_user(username, password)

        if user:
            st.session_state["user"] = user
            st.session_state["permissions"] = get_user_permissions(user)
            st.rerun()
        else:
            st.error("اسم المستخدم أو كلمة السر غير صحيحة")
