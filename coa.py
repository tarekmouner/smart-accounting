import streamlit as st
import pandas as pd
import db


def explain_account(account):
    name = account["name"]
    code = account["code"]
    acc_type = account["type"] or "غير محدد"

    explanations = {
        "أصول": f"الحساب {name} رقم {code} هو حساب أصول، ويعني حاجة للشركة ليها قيمة اقتصادية، زي النقدية أو المخزون أو المدينين.",
        "خصوم": f"الحساب {name} رقم {code} هو حساب خصوم، ويعني التزام أو دين على الشركة، زي الموردين أو القروض.",
        "حقوق ملكية": f"الحساب {name} رقم {code} يمثل حقوق الملكية، ويعني حصة الملاك في الشركة بعد خصم الالتزامات.",
        "إيرادات": f"الحساب {name} رقم {code} هو إيراد، ويعني فلوس دخلة للشركة من نشاطها، زي مبيعات أو خدمات.",
        "مصروفات": f"الحساب {name} رقم {code} هو مصروف، ويعني تكلفة بتخرج من الشركة عشان تشغيل النشاط، زي إيجار أو رواتب."
    }

    base = explanations.get(acc_type, f"الحساب {name} رقم {code} تم تصنيفه كـ {acc_type}.")

    if account["parent_code"]:
        base += f" وهو تابع للحساب الأب رقم {account['parent_code']}."

    if account["explanation"]:
        base += f" ملاحظة النظام: {account['explanation']}"

    return base


def coa_page(company_id):
    st.title("🌳 شجرة الحسابات")
    st.info("ارفع ملف Excel فيه شجرة الحسابات، والنظام هيحفظها للشركة المختارة ويشرح لك كل حساب.")

    uploaded = st.file_uploader(
        "ارفع ملف شجرة الحسابات Excel",
        type=["xlsx", "xls", "csv"]
    )

    if uploaded:
        try:
            if uploaded.name.endswith(".csv"):
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded)

            st.subheader("معاينة الملف")
            st.dataframe(df.head(30), use_container_width=True)

            st.write("الأعمدة الموجودة:")
            st.write(", ".join(df.columns))

            if st.button("حفظ شجرة الحسابات لهذه الشركة", type="primary"):
                try:
                    db.save_coa(company_id, df)
                    st.success("تم حفظ شجرة الحسابات بنجاح")
                except Exception as e:
                    st.error(f"خطأ: {e}")

        except Exception as e:
            st.error(f"مشكلة في قراءة الملف: {e}")

    st.divider()
    st.subheader("البحث والشرح")

    accounts = db.get_accounts(company_id)

    if not accounts:
        st.warning("لسه مفيش شجرة حسابات محفوظة لهذه الشركة.")
        return

    keyword = st.text_input("ابحث باسم الحساب أو رقمه")

    if keyword:
        accounts = db.search_accounts(company_id, keyword)

    for acc in accounts:
        with st.expander(f"{acc['code']} - {acc['name']}"):
            st.write(f"**النوع:** {acc['type'] or 'غير محدد'}")
            st.write(f"**الحساب الأب:** {acc['parent_code'] or 'لا يوجد'}")
            st.write(f"**المستوى:** {acc['level']}")
            st.success(explain_account(acc))
