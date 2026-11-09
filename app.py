import streamlit as st
import pandas as pd
import sqlite3
import json
import os

# ---------------------------------------------------------
# 1. إعدادات الصفحة وتصميم الواجهة
# ---------------------------------------------------------
st.set_page_config(
    page_title="نظام TAREKO المحاسبي المتعدد للشركات",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# 2. إدارة قاعدة البيانات الدائمة (SQLite Database)
# ---------------------------------------------------------
DB_FILE = "tareko_erp.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. جدول الشركات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS companies (
            company_id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_code TEXT UNIQUE,
            company_name TEXT,
            activity TEXT,
            currency TEXT,
            tax_number TEXT,
            logo_path TEXT
        )
    ''')
    
    # 2. جدول شجرة الحسابات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chart_of_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            account_code TEXT,
            account_name TEXT,
            account_type TEXT,
            description TEXT,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY(company_id) REFERENCES companies(company_id)
        )
    ''')
    
    # 3. جدول المستخدمين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            name TEXT,
            role TEXT,
            company_id INTEGER,
            permissions TEXT,
            FOREIGN KEY(company_id) REFERENCES companies(company_id)
        )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM companies")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO companies (company_code, company_name, activity, currency, tax_number, logo_path)
            VALUES ('COMP01', 'شركة التصنيع والتوزيع الغذائي', 'توزيع وتصنيع المواد الغذائية (ألبان بودرة، شاي، كرك)', 'EGP', '123-456-789', '')
        ''')
        default_comp_id = 1
    else:
        default_comp_id = 1

    cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'TAREK'")
    if cursor.fetchone()[0] == 0:
        admin_perms = json.dumps({
            "chart_of_accounts": {"access": True, "action": "Full Control"},
            "journal_generator": {"access": True, "action": "Full Control"},
            "company_settings": {"access": True, "action": "Full Control"},
            "companies_manager": {"access": True, "action": "Full Control"},
            "user_management": {"access": True, "action": "Full Control"}
        })
        cursor.execute('''
            INSERT INTO users (username, password, name, role, company_id, permissions)
            VALUES ('TAREK', '159019', 'طارق منير (الآدمن الرئيسي)', 'Admin', ?, ?)
        ''', (default_comp_id, admin_perms))
        
    conn.commit()
    conn.close()

init_db()

# ---------------------------------------------------------
# 3. إدارة جلسة الدخول
# ---------------------------------------------------------
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'current_user' not in st.session_state:
    st.session_state['current_user'] = None
if 'active_company_id' not in st.session_state:
    st.session_state['active_company_id'] = 1

def get_user(username):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username.upper(),)).fetchone()
    conn.close()
    if user:
        user_dict = dict(user)
        user_dict['permissions'] = json.loads(user_dict['permissions'])
        return user_dict
    return None

def get_company_info(company_id):
    conn = get_db_connection()
    comp = conn.execute("SELECT * FROM companies WHERE company_id = ?", (company_id,)).fetchone()
    conn.close()
    return dict(comp) if comp else None

# ---------------------------------------------------------
# 4. شاشة تسجيل الدخول
# ---------------------------------------------------------
def login_screen():
    st.markdown("<h1 style='text-align: center;'>🔒 نظام TAREKO المحاسبي المتعدد للشركات</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>تسجيل الدخول للتحكم في كافة الشركات والكيانات</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            username_input = st.text_input("اسم المستخدم (Username):")
            password_input = st.text_input("كلمة السر (Password):", type="password")
            submit = st.form_submit_button("دخول النظام", use_container_width=True)
            
            if submit:
                clean_username = username_input.strip().upper()
                user_data = get_user(clean_username)
                if user_data:
                    if user_data['password'] == password_input:
                        st.session_state['logged_in'] = True
                        st.session_state['current_user'] = clean_username
                        st.session_state['active_company_id'] = user_data['company_id']
                        st.success(f"أهلاً بك يا {user_data['name']}!")
                        st.rerun()
                    else:
                        st.error("كلمة السر غير صحيحة!")
                else:
                    st.error("اسم المستخدم غير موجود بالنظام!")

# ---------------------------------------------------------
# 5. التطبيق الرئيسي
# ---------------------------------------------------------
def main_app():
    current_username = st.session_state['current_user']
    user_info = get_user(current_username)
    user_perms = user_info['permissions']
    
    conn = get_db_connection()
    all_companies = conn.execute("SELECT company_id, company_name FROM companies").fetchall()
    conn.close()
    
    comp_dict = {c['company_name']: c['company_id'] for c in all_companies}
    current_comp_info = get_company_info(st.session_state['active_company_id'])
    
    st.sidebar.title("🏢 إدارة الشركات")
    selected_comp_name = st.sidebar.selectbox(
        "اختر الشركة النشطة حالياً:", 
        list(comp_dict.keys()), 
        index=list(comp_dict.values()).index(st.session_state['active_company_id']) if st.session_state['active_company_id'] in comp_dict.values() else 0
    )
    
    new_comp_id = comp_dict[selected_comp_name]
    if new_comp_id != st.session_state['active_company_id']:
        st.session_state['active_company_id'] = new_comp_id
        st.rerun()

    st.sidebar.markdown(f"**الشركة الحالية:** {current_comp_info['company_name']}")
    st.sidebar.caption(f"النشاط: {current_comp_info['activity']}")
    
    st.sidebar.markdown("---")
    st.sidebar.write(f"👤 **المستخدم:** {user_info['name']}")
    if st.sidebar.button("🚪 تسجيل الخروج", use_container_width=True):
        st.session_state['logged_in'] = False
        st.session_state['current_user'] = None
        st.rerun()
        
    st.sidebar.markdown("---")
    
    available_pages = {}
    available_pages["📂 شجرة حسابات الشركة"] = "chart_of_accounts"
    available_pages["✍️ مولد القيود الذكي (شات)"] = "journal_generator"
    available_pages["🏢 إعدادات الشركة الحالية واللوجو"] = "company_settings"
    
    if user_perms.get("companies_manager", {}).get("access") or user_info['role'] == 'Admin':
        available_pages["➕ إضافة وإدارة الشركات"] = "companies_manager"
    if user_perms.get("user_management", {}).get("access") or user_info['role'] == 'Admin':
        available_pages["👥 إدارة المستخدمين والصلاحيات"] = "user_management"

    choice = st.sidebar.radio("قائمة النظام:", list(available_pages.keys()))
    page_key = available_pages[choice]

    # --- 1. صفحة شجرة الحسابات ---
    if page_key == "chart_of_accounts":
        st.header(f"📂 شجرة الحسابات الخاصة بـ: {current_comp_info['company_name']}")
        st.markdown("هنا يتم استعراض، فلترة، وشرح شجرة الحسابات التي تم رفعها وتخصيصها لهذه الشركة تحديداً.")
        
        conn = get_db_connection()
        coa_df = pd.read_sql_query(
            "SELECT account_code as 'كود الحساب', account_name as 'اسم الحساب', account_type as 'تصنيف الحساب', description as 'الشرح المحاسبي' FROM chart_of_accounts WHERE company_id = ?", 
            conn, 
            params=(st.session_state['active_company_id'],)
        )
        conn.close()
        
        if not coa_df.empty:
            st.success(f"إجمالي الحسابات المسجلة لهذه الشركة: **{len(coa_df)} حساب**")
            search_query = st.text_input("🔍 بحث داخل شجرة الحسابات (بالكود أو الاسم):")
            if search_query:
                filtered_df = coa_df[coa_df['كود الحساب'].astype(str).str.contains(search_query, case=False) | coa_df['اسم الحساب'].str.contains(search_query, case=False)]
                st.dataframe(filtered_df, use_container_width=True)
            else:
                st.dataframe(coa_df, use_container_width=True)
        else:
            st.warning("⚠️ لا توجد شجرة حسابات مسجلة لهذه الشركة حتى الآن! اذهب إلى صفحة (إعدادات الشركة الحالية واللوجو) لرفع ملف شجرة الحسابات الخاص بها.")

    # --- 2. صفحة مولد القيود التفاعلي (شات حقيقي) ---
    elif page_key == "journal_generator":
        st.header(f"✍️ المساعد المحاسبي التفاعلي - {current_comp_info['company_name']}")
        st.markdown("دردش معايا واكتب أي عملية بالعامية المصرية (مثلاً: دفعنا 5000 إيجار، أو حولنا فلوس لشركة بيلتون). **لو في حاجة مش واضحة، هسألك لحد ما أفهمها وأطلع القيد المضبوط!**")
        
        conn = get_db_connection()
        coa_df = pd.read_sql_query(
            "SELECT account_code, account_name, account_type FROM chart_of_accounts WHERE company_id = ?", 
            conn, 
            params=(st.session_state['active_company_id'],)
        )
        conn.close()
        
        if coa_df.empty:
            st.error("⚠️ تنبيه: لا توجد شجرة حسابات مسجلة لهذه الشركة! برجاء رفع شجرة الحسابات من إعدادات الشركة أولاً.")
        else:
            if 'chat_history' not in st.session_state:
                st.session_state['chat_history'] = [
                    {"role": "assistant", "content": f"أهلاً بيك يا باشمهندس طارق. أنا معاك أهو، اكتب لي العملية أو المصروف اللي حصل في {current_comp_info['company_name']}، ولو احتاجت تفاصيل هسألك لحد ما نظبط القيد!"}
                ]
            
            for message in st.session_state['chat_history']:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
            
            if user_prompt := st.chat_input("اكتب العملية المحاسبية هنا..."):
                st.session_state['chat_history'].append({"role": "user", "content": user_prompt})
                with st.chat_message("user"):
                    st.markdown(user_prompt)
                
                text_lower = user_prompt.strip().lower()
                
                with st.chat_message("assistant"):
                    with st.spinner("جاري تحليل العملية..."):
                        # فحص هل الجملة مبهمة وتحتاج سؤال استباقي (مثل أسماء شركات غامضة أو بنود غير شائعة)
                        is_vague = not any(k in text_lower for k in ["إيجار", "اجار", "كهرباء", "نور", "مياه", "مرتب", "رواتب", "مرتبات", "شراء بضاعة", "صيانة"])
                        
                        if is_vague and any(c in text_lower for c in ["شركة", "إلى", "لـ", "حوالة", "دفعنا"]):
                            clarification_msg = f"يا باشمهندس طارق، أنا قريت جملتك (`{user_prompt}`) ولقيت فيها جهة غير واضحة البند في شجرة الحسابات. **عشان مألفش من دماغي، فهمني أكتر:**\n1. هل الجهة دي (مورد بضاعة أو خامات) عليه مديونية؟\n2. ولا ده مصروف خدمي أو استشاري؟\n3. ولا سداد التزام سابق؟\nقولي طبيعتها إيه وأنا هثبتها فوراً!"
                            st.markdown(clarification_msg)
                            st.session_state['chat_history'].append({"role": "assistant", "content": clarification_msg})
                        else:
                            matched_debit = "المصاريف العمومية والتشغيلية"
                            matched_credit = "الخزينة الرئيسية"
                            
                            if "إيجار" in text_lower or "اجار" in text_lower:
                                matched_debit = "مصاريف إيجار المخازن"
                            elif "كهرباء" in text_lower or "نور" in text_lower:
                                matched_debit = "مصاريف المرافق (كهرباء ومياه)"
                            elif "مرتب" in text_lower or "رواتب" in text_lower:
                                matched_debit = "مصاريف الأجور والرواتب"
                                
                            result_reply = f"""تمام يا باشمهندس، فهمت العملية:\n\n* **القيد المحاسبي المقترح:**\n  * **من ح/** {matched_debit} (مدين)\n  * **إلى ح/** {matched_credit} (دائن)\n\n*(هل القيد ده مظبوط معاك ولا نحب نعدل حاجة؟)*"""
                            st.markdown(result_reply)
                            st.session_state['chat_history'].append({"role": "assistant", "content": result_reply})

    # --- 3. صفحة إعدادات الشركة الحالية ---
    elif page_key == "company_settings":
        st.header(f"🏢 إعدادات شركة: {current_comp_info['company_name']}")
        
        if current_comp_info.get('logo_path') and os.path.exists(current_comp_info['logo_path']):
            st.image(current_comp_info['logo_path'], width=150, caption="شعار الشركة (Logo)")
        
        with st.form("company_settings_form"):
            c_name = st.text_input("اسم الشركة:", current_comp_info['company_name'])
            c_code = st.text_input("كود أو اختصار الشركة:", current_comp_info['company_code'])
            c_act = st.text_area("نشاط الشركة:", current_comp_info['activity'])
            c_curr = st.text_input("العملة الرئيسية:", current_comp_info['currency'])
            c_tax = st.text_input("الرقم الضريبي:", current_comp_info['tax_number'])
            
            uploaded_logo = st.file_uploader("رفع أو تغيير لوجو الشركة (PNG / JPG):", type=["png", "jpg", "jpeg"])
            
            st.markdown("---")
            st.subheader("📥 رفع أو تحديث شجرة الحسابات الخاصة بهذه الشركة")
            uploaded_coa = st.file_uploader("ارفع ملف شجرة الحسابات الجديد (Excel أو CSV):", type=["xlsx", "csv"])
            
            submit_comp = st.form_submit_button("حفظ إعدادات الشركة ورفع شجرة الحسابات")
            
            if submit_comp:
                logo_path = current_comp_info.get('logo_path', '')
                if uploaded_logo is not None:
                    os.makedirs("logos", exist_ok=True)
                    logo_path = f"logos/{c_code}_logo.png"
                    with open(logo_path, "wb") as f:
                        f.write(uploaded_logo.getbuffer())
                
                conn = get_db_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE companies SET company_code=?, company_name=?, activity=?, currency=?, tax_number=?, logo_path=?
                    WHERE company_id=?
                ''', (c_code, c_name, c_act, c_curr, c_tax, logo_path, st.session_state['active_company_id']))
                
                if uploaded_coa is not None:
                    df = pd.read_excel(uploaded_coa) if uploaded_coa.name.endswith('.xlsx') else pd.read_csv(uploaded_coa)
                    cursor.execute("DELETE FROM chart_of_accounts WHERE company_id = ?", (st.session_state['active_company_id'],))
                    
                    cols = df.columns.tolist()
                    code_col = cols[0]
                    name_col = cols[1] if len(cols) > 1 else cols[0]
                    
                    for idx, row in df.iterrows():
                        code = str(row[code_col]).strip()
                        name = str(row[name_col]).strip()
                        
                        if code.startswith('1') or 'أصول' in name:
                            ac_type = 'أصول'
                            desc = 'حساب أصول وممتلكات - طبيعته مدين'
                        elif code.startswith('2') or 'خصوم' in name or 'موردين' in name:
                            ac_type = 'خصوم التزامات'
                            desc = 'حساب التزامات على الشركة - طبيعته دائن'
                        elif code.startswith('3') or 'إيراد' in name or 'مبيعات' in name:
                            ac_type = 'إيرادات'
                            desc = 'حساب إيرادات النشاط - طبيعته دائن'
                        elif code.startswith('4') or 'مصروف' in name:
                            ac_type = 'مصروفات'
                            desc = 'حساب مصروفات التشغيل - طبيعته مدين'
                        else:
                            ac_type = 'حساب عام'
                            desc = 'حساب فرعي مكمل لشجرة الحسابات'

                        cursor.execute('''
                            INSERT INTO chart_of_accounts (company_id, account_code, account_name, account_type, description)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (st.session_state['active_company_id'], code, name, ac_type, desc))
                
                conn.commit()
                conn.close()
                st.success("تم تحديث إعدادات الشركة وحفظ شجرة الحسابات واللوجو بنجاح!")
                st.rerun()

    # --- 4. صفحة إضافة وإدارة الشركات ---
    elif page_key == "companies_manager":
        st.header("➕ إضافة وتأسيس شركة جديدة بالسيستم")
        
        with st.form("new_company_form"):
            new_c_name = st.text_input("اسم الشركة الجديدة:")
            new_c_code = st.text_input("كود الشركة المختصر (مثال: COMP02):")
            new_c_act = st.text_area("نشاط الشركة:")
            new_c_curr = st.text_input("العملة الرئيسية:", "EGP")
            new_c_tax = st.text_input("الرقم الضريبي:")
            
            if st.form_submit_button("إضافة الشركة وإنشائها"):
                if new_c_name and new_c_code:
                    conn = get_db_connection()
                    try:
                        conn.execute('''
                            INSERT INTO companies (company_code, company_name, activity, currency, tax_number, logo_path)
                            VALUES (?, ?, ?, ?, ?, '')
                        ''', (new_c_code.strip().upper(), new_c_name, new_c_act, new_c_curr, new_c_tax))
                        conn.commit()
                        st.success(f"تم إنشاء الشركة ({new_c_name}) بنجاح!")
                    except Exception as e:
                        st.error(f"حدث خطأ: {e}")
                    finally:
                        conn.close()
                else:
                    st.warning("برجاء إدخال اسم الشركة والكود المختصر.")

    # --- 5. صفحة إدارة المستخدمين ---
    elif page_key == "user_management":
        st.header("👥 إدارة المستخدمين وصلاحياتهم")
        with st.form("add_user_form"):
            u_name = st.text_input("اسم المستخدم (Username):").strip().upper()
            u_fullname = st.text_input("الاسم بالكامل:")
            u_pass = st.text_input("كلمة السر:", type="password")
            
            conn = get_db_connection()
            comps_list = conn.execute("SELECT company_id, company_name FROM companies").fetchall()
            conn.close()
            comp_choices = {c['company_name']: c['company_id'] for c in comps_list}
            selected_user_comp = st.selectbox("الشركة التابع لها المستخدم:", list(comp_choices.keys()))
            u_role = st.selectbox("الدور:", ["محاسب", "مدير حسابات", "مساعد مالي"])
            
            if st.form_submit_button("حفظ المستخدم الجديد"):
                if u_name and u_pass:
                    target_comp_id = comp_choices[selected_user_comp]
                    default_perms = json.dumps({
                        "chart_of_accounts": {"access": True, "action": "Read Only"},
                        "journal_generator": {"access": True, "action": "Edit"},
                        "company_settings": {"access": False, "action": "None"}
                    })
                    conn = get_db_connection()
                    try:
                        conn.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)", 
                                     (u_name, u_pass, u_fullname, u_role, target_comp_id, default_perms))
                        conn.commit()
                        st.success(f"تم إنشاء حساب المستخدم {u_name} بنجاح!")
                    except Exception as e:
                        st.error(f"خطأ: {e}")
                    finally:
                        conn.close()

# ---------------------------------------------------------
# 6. التشغيل الأساسي
# ---------------------------------------------------------
if not st.session_state['logged_in']:
    login_screen()
else:
    main_app()
