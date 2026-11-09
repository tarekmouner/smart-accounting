import streamlit as st
import db
import auth


def settings_page(user):
    st.title("⚙️ إعدادات النظام والشركة")

    tab1, tab2, tab3 = st.tabs([
        "الشركات",
        "المستخدمين والصلاحيات",
        "إعدادات النظام"
    ])

    with tab1:
        st.subheader("إضافة شركة جديدة")

        with st.form("add_company"):
            name = st.text_input("اسم الشركة")
            tax_number = st.text_input("الرقم الضريبي")
            address = st.text_area("العنوان")
            phone = st.text_input("التليفون")
            email = st.text_input("الإيميل")
            currency = st.selectbox("العملة", ["EGP", "USD", "EUR", "SAR", "AED"])

            submitted = st.form_submit_button("إضافة الشركة")

            if submitted:
                if not name:
                    st.error("لازم تكتب اسم الشركة")
                else:
                    db.add_company(name, tax_number, address, phone, email, currency)
                    st.success("تم إضافة الشركة")

        st.divider()
        companies = db.get_companies()
        st.dataframe(companies, use_container_width=True)

    with tab2:
        st.subheader("إضافة مستخدم")

        companies = db.get_companies()

        if companies:
            with st.form("add_user"):
                username = st.text_input("اسم المستخدم")
                password = st.text_input("كلمة السر", type="password")
                full_name = st.text_input("الاسم بالكامل")
                role = st.selectbox("الصلاحية", ["user", "admin"])

                company = st.selectbox(
                    "الشركة",
                    companies,
                    format_func=lambda x: x["name"]
                )

                submitted = st.form_submit_button("إنشاء المستخدم")

                if submitted:
                    ok, msg = auth.create_user(
                        username,
                        password,
                        full_name,
                        role,
                        company["id"]
                    )

                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
        else:
            st.warning("أضف شركة الأول قبل ما تضيف مستخدمين.")

        st.divider()
        st.subheader("صلاحيات المستخدمين")

        conn = db.get_conn()
        users = conn.execute("SELECT * FROM users").fetchall()
        conn.close()

        if users:
            selected_user = st.selectbox(
                "اختر المستخدم",
                users,
                format_func=lambda x: x["username"]
            )

            selected_permissions = st.multiselect(
                "الصلاحيات المسموح بها",
                auth.PERMISSIONS,
                default=auth.get_user_permissions(dict(selected_user))
            )

            if st.button("حفظ الصلاحيات"):
                auth.save_permissions(selected_user["id"], selected_permissions)
                st.success("تم حفظ الصلاحيات")

    with tab3:
        st.subheader("معلومات النظام")

        st.write("قاعدة البيانات الحالية: SQLite محلية")

        st.warning("""
        على Streamlit Community Cloud، ملف قاعدة البيانات ممكن يضيع عند إعادة النشر.
        علشان البيانات تبقى دايمة، نربط النظام لاحقًا بـ Supabase أو PostgreSQL سحابي.
        """)

        st.info("""
        المستخدم الأساسي:
        اسم المستخدم: tarek
        كلمة السر: 159019
        """)
