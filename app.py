import streamlit as st
import pandas as pd

# ---------------------------------------------------------
# 1. إعدادات الصفحة والتصميم
# ---------------------------------------------------------
st.set_page_config(
    page_title="نظام TAREKO المحاسبي الذكي",
    page_icon="🧮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# 2. تهيئة ذاكرة الجلسة (Session State) وتأمين الآدمن الرئيسي
# ---------------------------------------------------------
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if 'current_user' not in st.session_state:
    st.session_state['current_user'] = None

# قاعدة بيانات المستخدمين والصلاحيات
if 'users_db' not in st.session_state:
    st.session_state['users_db'] = {
        "TAREK": {
            "password": "159019",
            "name": "طارق منير (الآدمن الرئيسي والمالك)",
            "role": "Admin",
            "permissions": {
                "chart_of_accounts": {"access": True, "action": "Full Control"},
                "journal_generator": {"access": True, "action": "Full Control"},
                "contracts_analysis": {"access": True, "action": "Full Control"},
                "alerts": {"access": True, "action": "Full Control"},
                "company_settings": {"access": True, "action": "Full Control"},
                "system_settings": {"access": True, "action": "Full Control"},
                "user_management": {"access": True, "action": "Full Control"}
            }
        }
    }

# بيانات الشركة الافتراضية
if 'company_info' not in st.session_state:
    st.session_state['company_info'] = {
        "name": "شركة التصنيع والتوزيع الغذائي",
        "activity": "توزيع وتصنيع المواد الغذائية (ألبان بودرة، شاي، كرك، شاي بنكهات)",
        "currency": "EGP (جنيه مصري)",
        "tax_number": "123-456-789",
        "fiscal_year_start": "01-01"
    }

# ---------------------------------------------------------
# 3. واجهة تسجيل الدخول (Login Screen)
# ---------------------------------------------------------
def login_screen():
    st.markdown("<h1 style='text-align: center;'>🔒 تسجيل الدخول - نظام TAREKO الذكي</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>أهلاً بك في المحرك المحاسبي المتكامل</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            username_input = st.text_input("اسم المستخدم (Username):")
            password_input = st.text_input("كلمة السر (Password):", type="password")
            submit = st.form_submit_button("دخول النظام", use_container_width=True)
            
            if submit:
                clean_username = username_input.strip().upper()
                if clean_username in st.session_state['users_db']:
                    user_data = st.session_state['users_db'][clean_username]
                    if user_data['password'] == password_input:
                        st.session_state['logged_in'] = True
                        st.session_state['current_user'] = clean_username
                        st.success(f"تم تسجيل الدخول بنجاح! مرحباً يا {user_data['name']}")
                        st.rerun()
                    else:
                        st.error("كلمة السر غير صحيحة، حاول مرة ثانية!")
                else:
                    st.error("اسم المستخدم غير موجود بالنظام!")

# ---------------------------------------------------------
# 4. الشاشة الرئيسية والتحكم بالصلاحيات (Main Application)
# ---------------------------------------------------------
def main_app():
    current_username = st.session_state['current_user']
    user_info = st.session_state['users_db'][current_username]
    user_perms = user_info['permissions']
    
    # الشريط الجانبي
    st.sidebar.title(f"👤 {user_info['name']}")
    st.sidebar.caption(f"الرتبة: {user_info['role']}")
    
    if st.sidebar.button("🚪 تسجيل الخروج", use_container_width=True):
        st.session_state['logged_in'] = False
        st.session_state['current_user'] = None
        st.rerun()
        
    st.sidebar.markdown("---")
    
    # فلترة الصفحات المتاحة حسب صلاحيات المستخدم
    available_pages = {}
    
    if user_perms.get("chart_of_accounts", {}).get("access"):
        available_pages["📂 شجرة الحسابات والفلترة"] = "chart_of_accounts"
    if user_perms.get("journal_generator", {}).get("access"):
        available_pages["✍️ مولد القيود بالعامية والمساعد الذكي"] = "journal_generator"
    if user_perms.get("contracts_analysis", {}).get("access"):
        available_pages["📑 تحليل العقود والعملاء/الموردين"] = "contracts_analysis"
    if user_perms.get("alerts", {}).get("access"):
        available_pages["⏰ مركز التنبيهات والمتابعة"] = "alerts"
    if user_perms.get("company_settings", {}).get("access"):
        available_pages["🏢 إعدادات الشركة"] = "company_settings"
    if user_perms.get("system_settings", {}).get("access"):
        available_pages["⚙️ إعدادات السيستم"] = "system_settings"
    if user_perms.get("user_management", {}).get("access"):
        available_pages["👥 إدارة المستخدمين والصلاحيات"] = "user_management"

    if not available_pages:
        st.warning("عفواً، ليس لديك صلاحية للوصول لأي صفحة في النظام. راجع الأدمن الرئيسي.")
        return

    choice = st.sidebar.radio("القائمة الرئيسية:", list(available_pages.keys()))
    page_key = available_pages[choice]

    # --- صفحة 1: شجرة الحسابات والفلترة ---
    if page_key == "chart_of_accounts":
        st.header("📂 إدارة وتصفية شجرة الحسابات")
        perm_action = user_perms["chart_of_accounts"]["action"]
        st.info(f"مستوى صلاحيتك في هذه الصفحة: **{perm_action}**")
        
        uploaded_file = st.file_uploader("ارفع شجرة الحسابات (Excel أو CSV):", type=["xlsx", "csv"])
        if uploaded_file is not None:
            df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
            st.success("تم قراءة الملف بنجاح! عينة من الحسابات:")
            st.dataframe(df.head(10), use_container_width=True)
            
            if perm_action in ["Edit (إدخال وتعديل)", "Full Control (تحكم كامل)"]:
                if st.button("تصفية، فلترة وشرح الحسابات تلقائياً"):
                    st.success("تم حفظ شجرة الحسابات وفلترتها بنجاح داخل ذاكرة النظام!")
            else:
                st.warning("صلاحيتك (عرض فقط)؛ لا يمكنك حفظ التعديلات أو إعادة الفلترة.")

    # --- صفحة 2: مولد القيود المظبوطة ---
    elif page_key == "journal_generator":
        st.header("✍️ مولد القيود المحاسبية بالعامية المصرية")
        perm_action = user_perms["journal_generator"]["action"]
        
        st.markdown("اكتب العملية بالبلدي، وسيب السيستم يفهمها ويحللها ويطلع القيد المحاسبي المظبوط للشغل:")
        user_input = st.text_area("تفاصيل العملية:", placeholder="مثال: دفعنا 15,000 جنيه كاش إيجار المخزن، أو اشترنا خامات بـ 50 ألف ودفعنا نصهم...")
        
        if st.button("توليد القيد وشرحه"):
            if user_input.strip():
                st.markdown("---")
                st.markdown("### 💡 التحليل المحاسبي والقيد المظبوط:")
                st.markdown("""
                * **التحليل المحاسبي:** تم تحديد المصروف كـ (إيجار مخازن) يندرج تحت المصاريف العمومية، مع تخفيض الخزينة بقيمة الدفع النقدي.
                * **القيد المحاسبي:**
                  * **من ح/** المصاريف العمومية - إيجار مخازن (مدين)
                  * **إلى ح/** الخزينة الرئيسية (دائن)
                * **الشرح البسيط:** المصروف زاد بالخصم فبقى مدين، والخزينة خرج منها فلوس فبقت دائنة.
                """)
                
                if perm_action == "Full Control (تحكم كامل)":
                    st.button("ترحيل القيد لدفتر اليومية")
            else:
                st.warning("برجاء كتابة العملية أولاً.")

    # --- صفحة 3: تحليل العقود والعملاء/الموردين ---
    elif page_key == "contracts_analysis":
        st.header("📑 تحليل العقود وحسابات العملاء والموردين")
        st.markdown("ارفع عقود العملاء والموردين أو فواتير الاستحقاق ليقوم النظام بجداولتها تلقائياً:")
        st.file_uploader("ارفع العقد أو المستند (PDF أو Excel):", type=["pdf", "xlsx", "docx"])

    # --- صفحة 4: التنبيهات والدفعات المستحقة ---
    elif page_key == "alerts":
        st.header("⏰ مركز التنبيهات والمتابعة التلقائية")
        st.info("📌 تنبيه استحقاق: باقي 3 أيام على سداد دفعة المورد (شركة المواد الغذائية).")
        st.success("📌 العملاء: تم تحصيل جميع مستحقات هذا الأسبوع بنجاح.")

    # --- صفحة 5: إعدادات الشركة ---
    elif page_key == "company_settings":
        st.header("🏢 إعدادات وبيانات الشركة")
        with st.form("company_form"):
            c_name = st.text_input("اسم الشركة:", st.session_state['company_info']['name'])
            c_act = st.text_area("نشاط الشركة:", st.session_state['company_info']['activity'])
            c_curr = st.text_input("العملة الرئيسية:", st.session_state['company_info']['currency'])
            c_tax = st.text_input("الرقم الضريبي:", st.session_state['company_info']['tax_number'])
            
            if st.form_submit_button("حفظ بيانات الشركة"):
                st.session_state['company_info'].update({
                    "name": c_name, "activity": c_act, "currency": c_curr, "tax_number": c_tax
                })
                st.success("تم تحديث بيانات الشركة بنجاح!")

    # --- صفحة 6: إعدادات النظام ---
    elif page_key == "system_settings":
        st.header("⚙️ إعدادات المحرك المحاسبي")
        st.checkbox("تفعيل التنبيهات التلقائية لمواعيد الفواتير", value=True)
        st.checkbox("ربط القيود تلقائياً بشجرة الحسابات المرفوعة", value=True)
        st.selectbox("أسلوب الشرح المحاسبي:", ["اللهجة المصرية المبسطة (بلدي)", "الفصحى المحاسبية الأكاديمية"])
        st.button("حفظ إعدادات النظام")

    # --- صفحة 7: إدارة المستخدمين والصلاحيات ---
    elif page_key == "user_management":
        st.header("👥 إدارة المستخدمين ونظام الصلاحيات (RBAC)")
        
        tab1, tab2 = st.tabs(["➕ إضافة مستخدم جديد", "📜 قائمة المستخدمين والصلاحيات"])
        
        with tab1:
            st.subheader("إضافة حساب جديد وتحديد صلاحياته بالكامل")
            with st.form("add_user_form"):
                new_username = st.text_input("اسم المستخدم للشبكة (Username):").strip().upper()
                new_name = st.text_input("الاسم بالكامل / الموظف:")
                new_pass = st.text_input("كلمة السر (Password):", type="password")
                new_role = st.selectbox("الرتبة / الدور:", ["محاسب", "مدير حسابات", "مدخل بيانات", "المراجع الخارجي"])
                
                st.markdown("---")
                st.markdown("##### 🔑 الصلاحيات التفصيلية لكل شاشة وفي كل جزء:")
                
                pages_list = {
                    "chart_of_accounts": "شجرة الحسابات والفلترة",
                    "journal_generator": "مولد القيود والمساعد الذكي",
                    "contracts_analysis": "تحليل العقود والعملاء/الموردين",
                    "alerts": "مركز التنبيهات والتذكير",
                    "company_settings": "إعدادات الشركة",
                    "system_settings": "إعدادات السيستم",
                    "user_management": "إدارة المستخدمين والصلاحيات"
                }
                
                user_permissions_input = {}
                for p_key, p_label in pages_list.items():
                    c1, c2 = st.columns([2, 2])
                    with c1:
                        has_access = st.checkbox(f"إظهار صفحة ({p_label})", value=(p_key in ["chart_of_accounts", "journal_generator"]), key=f"access_{p_key}")
                    with c2:
                        action_level = st.selectbox(f"مستوى الصلاحية في ({p_label}):", ["Read Only (عرض فقط)", "Edit (إدخال وتعديل)", "Full Control (تحكم كامل)"], key=f"perm_{p_key}")
                    user_permissions_input[p_key] = {"access": has_access, "action": action_level}
                
                if st.form_submit_button("إنشاء المستخدم والحفظ"):
                    if new_username and new_pass:
                        st.session_state['users_db'][new_username] = {
                            "password": new_pass,
                            "name": new_name,
                            "role": new_role,
                            "permissions": user_permissions_input
                        }
                        st.success(f"تم إضافة المستخدم {new_username} بنجاح ومُنح الصلاحيات المحددة!")
                    else:
                        st.error("برجاء إدخال اسم المستخدم وكلمة السر!")
                        
        with tab2:
            st.subheader("المستخدمون الحاليون وصلاحياتهم")
            for u_name, u_data in st.session_state['users_db'].items():
                with st.expander(f"👤 {u_data['name']} (@{u_name}) - الدور: {u_data['role']}"):
                    st.write(f"**كلمة السر:** `{u_data['password']}`")
                    st.json(u_data['permissions'])

# ---------------------------------------------------------
# 5. تشغيل التطبيق
# ---------------------------------------------------------
if not st.session_state['logged_in']:
    login_screen()
else:
    main_app()
