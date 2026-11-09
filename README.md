# نظام المحاسبة الذكي

نظام محاسبي متعدد الشركات مبني بـ Streamlit و Python و SQLite.

## المستخدم الأساسي

اسم المستخدم: tarek  
كلمة السر: 159019

## التشغيل محليًا

1. نزّل Python من الموقع الرسمي.
2. افتح CMD أو Terminal داخل فولدر المشروع.
3. نفذ الأوامر دي:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## رفع المشروع على GitHub

1. اعمل حساب على GitHub.
2. اعمل repository جديد.
3. ارفع كل ملفات المشروع.
4. مترفعش ملف `.streamlit/secrets.toml` الحقيقي.

## النشر على Streamlit

1. ادخل على https://share.streamlit.io
2. سجل الدخول بـ GitHub.
3. اضغط Create app.
4. اختر repository المشروع.
5. اختر الملف: `app.py`
6. اضغط Deploy.

Streamlit Community Cloud بيسمح بنشر التطبيقات مباشرة من مستودع GitHub. [4][5]

## إضافة مفتاح الذكاء الاصطناعي

من إعدادات التطبيق في Streamlit Cloud:

```toml
[openai]
api_key = "مفتاحك"
model = "gpt-4o-mini"
```

الـ Secrets لازم تتحفظ في إعدادات التطبيق أو ملف `.streamlit/secrets.toml` المحلي، ومينفعش يترفع على GitHub. [1][12]
