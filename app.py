import streamlit as st
import db
import auth
import coa
import assistant
import entities
from settings_page import settings_page

st.set_page_config(
    page_title="نظام المحاسبة الذكي",
    page_icon="📊",
    layout="wide"
)

db.init_db()

if "user" not in st.session_state:
    auth.login_page()
    st.stop()

user = st.session_state["user"]
permissions = st.session_state.get("permissions", [])

companies = db.get_companies()

if not companies:
    st.title("⚙️ ابدأ بإضافة شركتك")
    st.info("لازم تضيف شركة الأول، وبعدين ترفع شجرة الحسابات بتاعتها.")

    with st.form("first_company"):
        name = st.text_input("اسم الشركة")
        tax_number = st.text_input("الرقم الضريبي")
        address = st.text_area("العنوان")
        phone = st.text_input("التليفون")
        email = st.text_input("الإيميل")

        submitted = st.form_submit_button("إضافة الشركة")

        if submitted and name:
            db.add_company(name, tax_number, address, phone, email)
            st.rerun()

    st.stop()

company = st.sidebar.selectbox(
    "اختر الشركة",
    companies,
    format_func=lambda x: x["name"]
)

st.sidebar.success(f"مرحبًا {user['username']}")

menu = st.sidebar.radio(
    "القائمة",
    [
        "الرئيسية",
        "شجرة الحسابات",
        "المساعد الذكي",
        "العملاء والموردين والفواتير",
        "القيود المحاسبية",
        "الإعدادات"
    ]
)

if menu == "الرئيسية":
    st.title("📊 نظام المحاسبة الذكي")
    st.success(f"الشركة الحالية: {company['name']}")

    accounts = db.get_accounts(company["id"])
    entries = db.get_journal_entries(company["id"])
    invoices = db.get_invoices(company["id"])
    reminders = db.get_reminders(company["id"])

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("عدد الحسابات", len(accounts))
    c2.metric("عدد القيود", len(entries))
    c3.metric("عدد الفواتير", len(invoices))
    c4.metric("عدد التنبيهات", len(reminders))

elif menu == "شجرة الحسابات":
    coa.coa_page(company["id"])

elif menu == "المساعد الذكي":
    assistant.assistant_page(company, user)

elif menu == "العملاء والموردين والفواتير":
    entities.entities_page(company, permissions)

elif menu == "القيود المحاسبية":
    st.title("📘 القيود المحاسبية")

    accounts = db.get_accounts(company["id"])

    if not accounts:
        st.warning("ارفع شجرة الحسابات الأول.")
        st.stop()

    with st.form("journal_entry"):
        entry_date = st.date_input("تاريخ القيد")
        description = st.text_area("وصف القيد")

        st.subheader("تفاصيل القيد")

        lines = []

        for i in range(2):
            st.write(f"**السطر {i + 1}**")

            account = st.selectbox(
                f"الحساب {i + 1}",
                accounts,
                format_func=lambda x: f"{x['code']} - {x['name']}",
                key=f"acc_{i}"
            )

            debit = st.number_input(
                f"مدين {i + 1}",
                min_value=0.0,
                step=100.0,
                key=f"debit_{i}"
            )

            credit = st.number_input(
                f"دائن {i + 1}",
                min_value=0.0,
                step=100.0,
                key=f"credit_{i}"
            )

            memo = st.text_input(
                f"بيان {i + 1}",
                key=f"memo_{i}"
            )

            lines.append({
                "account_code": account["code"],
                "account_name": account["name"],
                "debit": debit,
                "credit": credit,
                "memo": memo
            })

        submitted = st.form_submit_button("حفظ القيد")

        if submitted:
            try:
                db.save_journal_entry(
                    company["id"],
                    str(entry_date),
                    description,
                    lines,
                    user["username"]
                )
                st.success("تم حفظ القيد بنجاح")
            except Exception as e:
                st.error(str(e))

    st.divider()
    entries = db.get_journal_entries(company["id"])

    for item in entries:
        entry = item["entry"]
        lines = item["lines"]

        with st.expander(f"{entry['entry_date']} - {entry['description']}"):
            for line in lines:
                st.write(
                    f"**{line['account_code']} - {line['account_name']}** | "
                    f"مدين: {line['debit']} | دائن: {line['credit']}"
                )

elif menu == "الإعدادات":
    settings_page(user)
