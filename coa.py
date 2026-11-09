from io import BytesIO

import pandas as pd
import streamlit as st

import db


FIELD_LABELS = {
    "code": "كود الحساب",
    "name": "اسم الحساب",
    "type": "نوع الحساب",
    "parent_code": "كود الحساب الأب",
    "level": "المستوى",
    "explanation": "الشرح",
}


def explain_account(account):
    code = db.clean_text(account.get("code"))
    name = db.clean_text(account.get("name"))
    acc_type = db.clean_text(account.get("type"))
    parent = db.clean_text(account.get("parent_code"))
    notes = db.clean_text(account.get("explanation"))

    normalized_type = db.normalize_header(acc_type)

    explanations = {
        "اصول": (
            "نوع الحساب مسجل كأصول. "
            "الأصول بتمثل موارد أو حقوق للشركة. "
            "التفاصيل بتختلف حسب طبيعة الحساب."
        ),
        "خصوم": (
            "نوع الحساب مسجل كخصوم. "
            "الخصوم بتمثل التزامات على الشركة تجاه الغير."
        ),
        "حقوق ملكية": (
            "نوع الحساب مسجل كحقوق ملكية، "
            "وده مرتبط بحقوق الملاك في الشركة."
        ),
        "ايرادات": (
            "نوع الحساب مسجل كإيرادات. "
            "توقيت إثبات الإيراد بيتحدد حسب طبيعة العملية "
            "وتحقق شروط الاعتراف، مش مجرد استلام الفلوس."
        ),
        "مصروفات": (
            "نوع الحساب مسجل كمصروفات. "
            "لازم نعرف الفترة اللي المصروف يخصها "
            "وهل هو مصروف فعلي أو دفعة مقدمة."
        ),
        "البنك والنقد": (
            "النوع ده عادةً بيُستخدم لحسابات الخزينة "
            "والحسابات البنكية. "
            "راجِع اسم الحساب وطبيعته، خصوصًا لو حساب وسيط "
            "أو تسوية، قبل تحديد المعالجة المحاسبية."
        ),
        "بنك ونقد": (
            "النوع ده عادةً بيُستخدم لحسابات النقدية والبنوك. "
            "المعالجة الدقيقة بتعتمد على العملية وطبيعة الحساب."
        ),
        "bank and cash": (
            "النوع ده عادةً بيخص حسابات البنوك والخزينة. "
            "راجِع لو الحساب فعلي أو حساب وسيط للتسويات."
        ),
        "receivable": (
            "النوع ده عادةً بيخص مبالغ مستحقة للشركة "
            "عند العملاء أو أطراف تانية."
        ),
        "payable": (
            "النوع ده عادةً بيخص مبالغ مستحقة على الشركة "
            "للموردين أو أطراف تانية."
        ),
    }

    explanation = explanations.get(
        normalized_type,
        (
            f"النوع المسجل في الملف: {acc_type}. "
            "محتاجين نراجع طبيعة الحساب واستخدامه "
            "قبل تحديد معالجته المحاسبية."
            if acc_type
            else
            "الملف مش محدد نوع الحساب. "
            "راجع تصنيفه قبل الاعتماد على شرحه."
        ),
    )

    parts = [
        f"الحساب: {name}",
        f"الكود: {code}",
        explanation,
    ]

    if parent:
        parts.append(f"كود الحساب الأب المسجل: {parent}")

    if notes:
        parts.append(f"الوصف الموجود في الملف: {notes}")

    return "\n\n".join(parts)


def read_uploaded_file(uploaded, company_id):
    content = uploaded.getvalue()
    extension = uploaded.name.rsplit(".", 1)[-1].lower()

    if extension == "csv":
        try:
            return pd.read_csv(
                BytesIO(content),
                dtype=str,
                keep_default_na=False,
                encoding="utf-8-sig",
            )
        except UnicodeDecodeError:
            return pd.read_csv(
                BytesIO(content),
                dtype=str,
                keep_default_na=False,
                encoding="cp1256",
            )

    workbook = pd.ExcelFile(
        BytesIO(content),
        engine="openpyxl",
    )

    sheet_name = st.selectbox(
        "اختار الشيت اللي فيه شجرة الحسابات",
        options=workbook.sheet_names,
        key=f"coa_sheet_{company_id}",
    )

    return pd.read_excel(
        workbook,
        sheet_name=sheet_name,
        dtype=str,
        keep_default_na=False,
    )


def import_section(company_id):
    st.subheader("رفع شجرة الحسابات")

    st.info(
        "الملف لازم يحتوي على كود الحساب واسم الحساب. "
        "ممكن أسماء الأعمدة تكون عربي أو إنجليزي. "
        "ارفع حسابات الشركة المختارة فقط."
    )

    uploaded = st.file_uploader(
        "اختار ملف Excel أو CSV",
        type=["xlsx", "csv"],
        key=f"coa_upload_{company_id}",
    )

    if uploaded is None:
        st.caption(
            "ملفات Excel القديمة بصيغة .xls مش مدعومة "
            "في النسخة دي؛ احفظها بصيغة .xlsx الأول."
        )
        return

    try:
        df = read_uploaded_file(uploaded, company_id)
    except Exception:
        st.error(
            "تعذر قراءة الملف. اتأكد إن صيغته فعلًا "
            "XLSX أو CSV وإنه مش محمي بكلمة مرور."
        )
        return

    st.write("معاينة أول 30 صف من الملف:")
    st.dataframe(
        df.head(30),
        use_container_width=True,
    )

    st.write("مطابقة الأعمدة:")

    detected = db.detect_coa_columns(df.columns)

    mapping_rows = [
        {
            "العمود في الملف": str(original),
            "الحقل في النظام": (
                FIELD_LABELS[target]
                if target
                else "مش هيتخزن في النسخة الحالية"
            ),
        }
        for original, target in detected.items()
    ]

    st.dataframe(
        pd.DataFrame(mapping_rows),
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        "الأعمدة الإضافية زي عملة الحساب والسماح بالتسوية "
        "واسم الشركة مش هتتخزن في جدول الحسابات الحالي. "
        "اسم الشركة الموجود في الملف مش بيغيّر الشركة المختارة."
    )

    try:
        prepared = db.prepare_coa(df)
    except ValueError as error:
        st.error(str(error))
        return

    st.success(
        f"الملف جاهز: {len(prepared)} حساب صالح للحفظ."
    )

    with st.expander("راجع البيانات اللي هتتحفظ"):
        st.dataframe(
            prepared.rename(columns=FIELD_LABELS),
            use_container_width=True,
            hide_index=True,
        )

    existing = {
        account["code"]
        for account in db.get_accounts(company_id)
    }

    incoming = set(prepared["code"])
    added_count = len(incoming - existing)
    updated_count = len(incoming & existing)

    st.write(
        f"هيتم إضافة {added_count} حساب جديد، "
        f"وتحديث {updated_count} حساب موجود."
    )

    st.warning(
        "التحديث بيستخدم كود الحساب للمطابقة داخل الشركة. "
        "بيستبدل الاسم والنوع والأب والمستوى والشرح للحسابات "
        "الموجودة في الملف، حتى لو بعض الحقول فاضية. "
        "الحسابات القديمة غير الموجودة في الملف مش هتتمسح."
    )

    confirmed = st.checkbox(
        "راجعت البيانات، والملف يخص الشركة المختارة، وموافق على الحفظ.",
        key=f"coa_confirm_{company_id}",
    )

    if st.button(
        "حفظ شجرة الحسابات لهذه الشركة",
        type="primary",
        disabled=not confirmed,
        key=f"coa_save_{company_id}",
    ):
        try:
            result = db.save_coa(company_id, prepared)
        except ValueError as error:
            st.error(str(error))
        except Exception:
            st.error(
                "حصل خطأ أثناء الحفظ. "
                "راجع سجلات التطبيق لمعرفة التفاصيل."
            )
        else:
            st.success(
                f"تم الحفظ: إضافة {result['added']} حساب "
                f"وتحديث {result['updated']} حساب."
            )


def saved_accounts_section(company_id):
    st.subheader("شجرة الحسابات المحفوظة")

    accounts = db.get_accounts(company_id)

    if not accounts:
        st.warning(
            "لسه مفيش شجرة حسابات محفوظة للشركة المختارة."
        )
        return

    all_df = pd.DataFrame(accounts)

    c1, c2 = st.columns(2)

    c1.metric("عدد الحسابات", len(accounts))
    c2.metric(
        "عدد الأنواع المسجلة",
        len({
            account["type"]
            for account in accounts
            if account["type"]
        }),
    )

    export_columns = [
        "code",
        "name",
        "type",
        "parent_code",
        "level",
        "explanation",
    ]

    csv_data = (
        all_df[export_columns]
        .to_csv(index=False)
        .encode("utf-8-sig")
    )

    st.download_button(
        "تنزيل نسخة CSV من الشجرة المحفوظة",
        data=csv_data,
        file_name=f"company_{company_id}_accounts.csv",
        mime="text/csv",
        key=f"coa_download_{company_id}",
    )

    keyword = st.text_input(
        "ابحث بكود الحساب أو اسمه",
        key=f"coa_search_{company_id}",
    ).strip()

    types = sorted({
        db.clean_text(account.get("type"))
        for account in accounts
        if db.clean_text(account.get("type"))
    })

    selected_type = st.selectbox(
        "فلترة حسب نوع الحساب",
        options=["كل الأنواع"] + types,
        key=f"coa_type_{company_id}",
    )

    filtered = accounts

    if keyword:
        search_value = keyword.casefold()

        filtered = [
            account
            for account in filtered
            if (
                search_value in account["code"].casefold()
                or search_value in account["name"].casefold()
            )
        ]

    if selected_type != "كل الأنواع":
        filtered = [
            account
            for account in filtered
            if account["type"] == selected_type
        ]

    st.write(f"عدد الحسابات بعد الفلترة: {len(filtered)}")

    if not filtered:
        st.info("مفيش حسابات مطابقة للبحث.")
        return

    display_df = pd.DataFrame(filtered)

    st.dataframe(
        display_df[export_columns].rename(
            columns=FIELD_LABELS
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("شرح حساب")

    by_code = {
        account["code"]: account
        for account in filtered
    }

    selected_code = st.selectbox(
        "اختار الحساب اللي عايز تفهمه",
        options=list(by_code),
        format_func=lambda code: (
            f"{code} - {by_code[code]['name']}"
        ),
        key=f"coa_explain_{company_id}",
    )

    selected_account = by_code[selected_code]

    st.info(explain_account(selected_account))

    st.caption(
        "الشرح هنا مبسط وقائم على النوع المسجل في الملف، "
        "مش تحليل ذكاء اصطناعي أو اعتماد لقيد محاسبي."
    )


def coa_page(company_id):
    st.title("شجرة الحسابات")

    import_section(company_id)

    st.divider()

    saved_accounts_section(company_id)
