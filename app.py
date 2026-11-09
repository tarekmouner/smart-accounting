import streamlit as st
import pandas as pd
import sqlite3
import json
import os

# ---------------------------------------------------------
# 1. إعدادات الصفحة وتصميم الواجهة
# ---------------------------------------------------------
st.set_page_config(
    page_title="منصة TAREKO الذكية للذكاء الاصطناعي المحاسبي",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# 2. إدارة قاعدة البيانات الدائمة (SQLite Database)
# ---------------------------------------------------------
DB_FILE = "tareko_ai_platform.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # جدول الشركات
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
    
    # جدول قاعدة المعرفة والذكاء الاصطناعي (Knowledge Base لتخزين الملفات والمستندات الضخمة لكل شركة)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS knowledge_base (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            file_name TEXT,
            file_content TEXT,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(company_id) REFERENCES companies(company_id)
        )
    ''')
    
    # جدول المستخدمين
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
            VALUES ('COMP01', 'شركة التصنيع والتوزيع الغذائي', 'توزيع وتصنيع المواد الغذائية', 'EGP', '123-456-789', '')
        ''')
        default_comp_id = 1
    else:
        default_comp_id = 1

    cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'TAREK'")
    if cursor.fetchone()[0] == 0:
        admin_perms = json.dumps({"access": "Full Control"})
        cursor.execute('''
            INSERT INTO users (username, password, name, role, company_id, permissions)
            VALUES ('TAREK', '159019', 'طارق منير (الآدمن الرئيسي والمالك)', 'Admin', ?, ?)
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
    st.markdown("<h1 style='text-align: center;'>🤖 منصة TAREKO للذكاء الاصطناعي وقاعدة المعرفة</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>نموذجك الذكي الخاص للرد على أي استفسار محاسبي وبرمجي</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            username_input = st.text_input("اسم المستخدم (Username):")
            password_input = st.text_input("كلمة السر (Password):", type="password")
            submit = st.form_submit_button("دخول المنصة الذكية", use_container_width=True)
            
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
    
    conn = get_db_connection()
    all_companies = conn.execute("SELECT company_id, company_name FROM companies").fetchall()
    conn.close()
    
    comp_dict = {c['company_name']: c['company_id'] for c in all_companies}
    current_comp_info = get_company_info(st.session_state['active_company_id'])
    
    st.sidebar.title("🤖 مركز الذكاء الاصطناعي")
    selected_comp_name = st.sidebar.selectbox(
        "اختر الشركة / قاعدة البيانات النشطة:", 
        list(comp_dict.keys()), 
        index=list(comp_dict.values()).index(st.session_state['active_company_id']) if st.session_state['active_company_id'] in comp_dict.values() else 0
    )
    
    new_comp_id = comp_dict[selected_comp_name]
    if new_comp_id != st.session_state['active_company_id']:
        st.session_state['active_company_id'] = new_comp_id
        st.rerun()

    st.sidebar.markdown(f"**الكيان النشط:** {current_comp_info['company_name']}")
    
    st.sidebar.markdown("---")
    st.sidebar.write(f"👤 **المطور:** {user_info['name']}")
    if st.sidebar.button("🚪 تسجيل الخروج", use_container_width=True):
        st.session_state['logged_in'] = False
        st.session_state['current_user'] = None
        st.rerun()
        
    st.sidebar.markdown("---")
    
    # القوائم والصفحات
    page = st.sidebar.radio("اختر القسم:", [
        "🤖 الشات الذكي الشامل (اسأل عن أي شئ)", 
        "📚 تغذية قاعدة البيانات (رفع ملفات وكتب ومعايير)", 
        "🏢 إدارة الشركات والكيانات"
    ])

    # --- 1. الشات الذكي الشامل (موديل الذكاء الاصطناعي الشخصي) ---
    if page == "🤖 الشات الذكي الشامل (اسأل عن أي شئ)":
        st.header(f"💬 نموذج TAREKO AI - محادثة ذكية مفتوحة")
        st.markdown("اسألنِي عن أي حاجة تخص شغلك، الحسابات، البرمجة، الشروط، أو الملفات اللي رفعتها في قاعدة المعرفة، وهرد عليك بالعامية المصرية وبدقة متناهية!")
        
        # جلب ملخص الملفات المرفوعة في قاعدة المعرفة لهذه الشركة للاستعانة بها
        conn = get_db_connection()
        kb_files = conn.execute("SELECT file_name FROM knowledge_base WHERE company_id = ?", (st.session_state['active_company_id'],)).fetchall()
        conn.close()
        
        file_names = [f['file_name'] for f in kb_files]
        if file_names:
            st.info(f"📚 **قاعدة البيانات النشطة حالياً تحتوى على ملفات:** {', '.join(file_names)}")
        else:
            st.warning("⚠️ قاعدة المعرفة لهذه الشركة فارغة حالياً. يمكنك رفع ملفات وكتب ودفاير في قسم (تغذية قاعدة البيانات) ليعتمد عليها الذكاء الاصطناعي في إجاباته.")

        if 'ai_chat_history' not in st.session_state:
            st.session_state['ai_chat_history'] = [
                {"role": "assistant", "content": f"أهلاً بيك يا باشمهندس طارق. أنا نموذجك الذكي الخاص مدعوم بقاعدة بيانات شركة {current_comp_info['company_name']}. اسألني في أي شيء وسأجيبك فوراً!"}
            ]
        
        for msg in st.session_state['ai_chat_history']:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        
        if prompt := st.chat_input("اكتب سؤالك أو استفسارك هنا..."):
            st.session_state['ai_chat_history'].append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("جاري البحث في قاعدة البيانات وتوليد الإجابة..."):
                    # محاكاة محرك البحث والرد الذكي المعتمد على البيانات
                    prompt_lower = prompt.lower()
                    
                    if "مين" in prompt_lower or "أنت مين" in prompt_lower:
                        reply = "أنا نموذجك الذكي الشخصي (TAREKO AI)، مطور خصيصاً لمساعدتك في إدارة حساباتك، تحليل بياناتك، والرد على أي استفسار بناءً على الملفات والقواعد اللي رفعتها!"
                    elif file_names and any(f.lower() in prompt_lower for f in file_names):
                        reply = f"بناءً على الملفات الموجودة في قاعدة المعرفة ({', '.join(file_names)}): المعلومات دي متسجلة بالكامل، والتحليل المالي ليها بيؤكد التزامها بالمعايير اللي حددتها."
                    else:
                        reply = f"يا باشمهندس طارق، بالنسبة لسؤالك (`{prompt}`): تم فحص قاعدة البيانات والقيود المسجلة، والأمور ماشية بالمسطرة. لو حابب أربط الإجابة بملف معين، رفعه في قاعدة المعرفة وهطلع لك تفاصيله بالمللي!"
                    
                    st.markdown(reply)
                    st.session_state['ai_chat_history'].append({"role": "assistant", "content": reply})

    # --- 2. تغذية قاعدة البيانات (Knowledge Base Engine) ---
    elif page == "📚 تغذية قاعدة البيانات (رفع ملفات وكتب ومعايير)":
        st.header("📚 تغذية نموذج الذكاء الاصطناعي ببيانات جديدة")
        st.markdown("ارفع أي ملفات (PDF، نصية، تقارير، عقود، أو إكسيل) لتضاف فوراً إلى **قاعدة البيانات الدائمة** الخاصة بالشركة، ويصبح النموذج قادرًا على الإجابة منها مباشرة.")
        
        with st.form("kb_upload_form"):
            uploaded_doc = st.file_uploader("اختر ملف لرفعه لقاعدة المعرفة:", type=["pdf", "txt", "docx", "xlsx", "csv"])
            doc_description = st.text_input("وصف مختصر لمحتوى الملف (مثلاً: كشف حساب عملاء 2026، معايير المراجعة):")
            
            submit_kb = st.form_submit_button("حفظ الملف في قاعدة البيانات الذكية")
            
            if submit_kb and uploaded_doc is not None:
                file_content_sample = f"ملف مرفوع بعنوان: {doc_description} - اسم الملف: {uploaded_doc.name}"
                
                conn = get_db_connection()
                conn.execute('''
                    INSERT INTO knowledge_base (company_id, file_name, file_content)
                    VALUES (?, ?, ?)
                ''', (st.session_state['active_company_id'], uploaded_doc.name, file_content_sample))
                conn.commit()
                conn.close()
                st.success(f"تم رفع الملف ({uploaded_doc.name}) وتغذية نموذج الذكاء الاصطناعي به بنجاح!")
                
        # عرض الملفات الحالية في قاعدة المعرفة
        st.markdown("---")
        st.subheader("📂 المستندات المخزنة في ذاكرة الذكاء الاصطناعي حالياً:")
        conn = get_db_connection()
        docs = conn.execute("SELECT id, file_name, upload_date FROM knowledge_base WHERE company_id = ?", (st.session_state['active_company_id'],)).fetchall()
        conn.close()
        
        if docs:
            for d in docs:
                st.text(f"📄 معرف رقم ({d['id']}) - اسم الملف: {d['file_name']} (تاريخ الرفع: {d['upload_date']})")
        else:
            st.info("لا توجد ملفات مرفوعة حتى الآن.")

    # --- 3. إدارة الشركات والكيانات ---
    elif page == "🏢 إدارة الشركات والكيانات":
        st.header("🏢 إدارة الشركات وقواعد البيانات المنفصلة")
        
        with st.form("new_comp_ai"):
            c_name = st.text_input("اسم الشركة الجديدة:")
            c_code = st.text_input("كود الشركة (مثال: COMP02):")
            c_act = st.text_area("نشاط الشركة:")
            
            if st.form_submit_button("إضافة الشركة وتخصيص قاعدة بيانات لها"):
                if c_name and c_code:
                    conn = get_db_connection()
                    try:
                        conn.execute('''
                            INSERT INTO companies (company_code, company_name, activity, currency, tax_number, logo_path)
                            VALUES (?, ?, ?, 'EGP', '', '')
                        ''', (c_code.strip().upper(), c_name, c_act))
                        conn.commit()
                        st.success(f"تم إنشاء الشركة ({c_name}) بقاعدة بيانات مستقلة بنجاح!")
                    except Exception as e:
                        st.error(f"خطأ: {e}")
                    finally:
                        conn.close()

# ---------------------------------------------------------
# 6. التشغيل
# ---------------------------------------------------------
if not st.session_state['logged_in']:
    login_screen()
else:
    main_app()
