import streamlit as st
import db
from datetime import date

try:
    import openai
    OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False


def build_system_prompt(company_name, accounts):
    accounts_text = "\n".join([
        f"{a['code']} | {a['name']} | {a['type'] or 'غير محدد'}"
        for a in accounts[:300]
    ])

    return f"""
أنت مساعد محاسبي مصري خبير، بتتكلم باللهجة المصرية البسيطة.

اسم الشركة: {company_name}

شجرة الحسابات المتاحة:
{accounts_text}

مهمتك:
1. افهم العملية المحاسبية اللي العميل بيقصدها.
2. لو في معلومة ناقصة أو غامضة، اسأل العميل سؤال واحد واضح في كل مرة.
3. بعد ما تفهم العملية، اشرحها ببساطة كأن العميل مش فاهم محاسبة.
4. اقترح قيد محاسبي مظبوط بصيغة:
مدين: اسم الحساب - رقم الحساب - المبلغ
دائن: اسم الحساب - رقم الحساب - المبلغ
5. استخدم فقط الحسابات الموجودة في شجرة الحسابات إن أمكن.
6. لو الحساب مش موجود، قول للعميل نضيفه في شجرة الحسابات.
7. اشرح ليه يعمل إيه خطوة بخطوة في النظام.
8. متستخدمش مصطلحات معقدة من غير شرح.
"""


def local_accounting_answer(text, accounts):
    text = text.lower()

    if any(word in text for word in ["مصروف", "مصاريف", "فاتورة مصروف", "إيجار", "رواتب"]):
        return {
            "reply": "تمام، فهمت إن فيه مصروف. بس محتاج أعرف: المصروف ده مدفوع كاش ولا على الحساب؟ وإيه اسم المورد أو الجهة اللي دفعتلها؟",
            "need_info": True
        }

    if any(word in text for word in ["بيع", "مبيعات", "فاتورة عميل", "إيراد"]):
        return {
            "reply": "تمام، دي عملية بيع. محتاج أعرف: العميل دفع كاش ولا هيدفع بعدين؟ وإيه قيمة الفاتورة والضريبة؟",
            "need_info": True
        }

    if any(word in text for word in ["شراء", "مشتريات", "مورد", "فاتورة مورد"]):
        return {
            "reply": "تمام، دي عملية شراء من مورد. محتاج أعرف: هل دفعت للمورد ولا الفاتورة هتتأخر؟ وإيه قيمة الفاتورة؟",
            "need_info": True
        }

    return {
        "reply": "اكتبلي العملية بالتفصيل، مثال: «دفت إيجار المحل 10,000 جنيه كاش» أو «بعت فاتورة لعميل بقيمة 20,000 جنيه». وهسألك على أي حاجة ناقصة وأقولك القيد المظبوط.",
        "need_info": True
    }


def ask_ai(message, company_name, accounts):
    api_key = None
    model = "gpt-4o-mini"

    try:
        api_key = st.secrets["openai"]["api_key"]
        model = st.secrets["openai"].get("model", model)
    except Exception:
        api_key = None

    if OPENAI_AVAILABLE and api_key:
        try:
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": build_system_prompt(company_name, accounts)},
                    {"role": "user", "content": message}
                ],
                temperature=0.2
            )
            return {
                "reply": response.choices[0].message.content,
                "need_info": False
            }
        except Exception as e:
            return {
                "reply": f"حصلت مشكلة في الاتصال بالذكاء الاصطناعي: {e}\n\nهحاول أساعدك بالمحرك المحلي.",
                "need_info": True
            }

    return local_accounting_answer(message, accounts)


def assistant_page(company, user):
    st.title("🤖 المساعد المحاسبي الذكي")
    st.caption("اكتب أي عملية محاسبية بالعامية، والنظام هيشرحها ويسألك على الناقص ويقترح القيد.")

    accounts = db.get_accounts(company["id"])

    if not accounts:
        st.warning("لازم ترفع شجرة الحسابات الأول من صفحة إعدادات الشركة أو شجرة الحسابات.")
        return

    if "chat" not in st.session_state:
        st.session_state["chat"] = []

    for msg in st.session_state["chat"]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_input = st.chat_input("اكتب العملية المحاسبية...")

    if user_input:
        st.session_state["chat"].append({"role": "user", "content": user_input})
        db.save_chat(company["id"], user["username"], "user", user_input)

        with st.chat_message("user"):
            st.write(user_input)

        result = ask_ai(user_input, company["name"], accounts)

        with st.chat_message("assistant"):
            st.write(result["reply"])

        st.session_state["chat"].append({"role": "assistant", "content": result["reply"]})
        db.save_chat(company["id"], user["username"], "assistant", result["reply"])
