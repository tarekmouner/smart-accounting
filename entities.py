import streamlit as st
import db
from datetime import date


def entities_page(company, permissions):
    tab1, tab2, tab3, tab4 = st.tabs([
        "العملاء والموردين",
        "الفواتير",
        "العقود",
        "التنبيهات"
    ])

    with tab1:
        st.title("👥 العملاء والموردين")

        party_type = st.selectbox("النوع", ["عميل", "مورد"])

        with st.form("add_party"):
            name = st.text_input("الاسم")
            phone = st.text_input("التليفون")
            email = st.text_input("الإيميل")
            tax_number = st.text_input("الرقم الضريبي")
            address = st.text_input("العنوان")
            notes = st.text_area("ملاحظات")

            submitted = st.form_submit_button("حفظ")

            if submitted:
                if not name:
                    st.error("لازم تكتب الاسم")
                else:
                    db.add_party(
                        company["id"], party_type, name, phone, email,
                        tax_number, address, notes
                    )
                    st.success("تم الحفظ")

        st.divider()
        parties = db.get_parties(company["id"])
        st.dataframe(parties, use_container_width=True)

    with tab2:
        st.title("🧾 الفواتير")

        parties = db.get_parties(company["id"])

        if not parties:
            st.warning("أضف عميل أو مورد الأول.")
        else:
            with st.form("add_invoice"):
                invoice_type = st.selectbox("نوع الفاتورة", ["بيع", "شراء"])
                party = st.selectbox(
                    "العميل أو المورد",
                    parties,
                    format_func=lambda x: f"{x['name']} - {x['party_type']}"
                )
                invoice_number = st.text_input("رقم الفاتورة")
                invoice_date = st.date_input("تاريخ الفاتورة", date.today())
                due_date = st.date_input("تاريخ الاستحقاق", date.today())
                amount = st.number_input("قيمة الفاتورة", min_value=0.0, step=100.0)
                paid_amount = st.number_input("المدفوع", min_value=0.0, step=100.0)
                notes = st.text_area("ملاحظات")

                submitted = st.form_submit_button("حفظ الفاتورة")

                if submitted:
                    db.add_invoice(
                        company["id"], invoice_type, party["id"], invoice_number,
                        str(invoice_date), str(due_date), amount, paid_amount, notes
                    )
                    st.success("تم حفظ الفاتورة")

        st.divider()
        invoices = db.get_invoices(company["id"])
        st.dataframe(invoices, use_container_width=True)

    with tab3:
        st.title("📄 العقود")

        parties = db.get_parties(company["id"])

        if not parties:
            st.warning("أضف عميل أو مورد الأول.")
        else:
            with st.form("add_contract"):
                party = st.selectbox(
                    "الطرف",
                    parties,
                    format_func=lambda x: f"{x['name']} - {x['party_type']}"
                )
                title = st.text_input("عنوان العقد")
                contract_date = st.date_input("تاريخ العقد", date.today())
                start_date = st.date_input("تاريخ البداية", date.today())
                end_date = st.date_input("تاريخ النهاية", date.today())
                amount = st.number_input("قيمة العقد", min_value=0.0, step=1000.0)
                payment_terms = st.text_area("شروط الدفع")
                notes = st.text_area("ملاحظات")

                submitted = st.form_submit_button("حفظ العقد")

                if submitted:
                    db.add_contract(
                        company["id"], party["id"], title, str(contract_date),
                        str(start_date), str(end_date), amount, payment_terms, notes
                    )
                    st.success("تم حفظ العقد")

        st.divider()
        contracts = db.get_contracts(company["id"])
        st.dataframe(contracts, use_container_width=True)

    with tab4:
        st.title("🔔 التنبيهات")

        with st.form("add_reminder"):
            title = st.text_input("عنوان التنبيه")
            due_date = st.date_input("تاريخ التنبيه", date.today())
            notes = st.text_area("ملاحظات")

            submitted = st.form_submit_button("حفظ التنبيه")

            if submitted:
                db.add_reminder(company["id"], title, str(due_date), notes)
                st.success("تم حفظ التنبيه")

        st.divider()
        reminders = db.get_reminders(company["id"])
        st.dataframe(reminders, use_container_width=True)
