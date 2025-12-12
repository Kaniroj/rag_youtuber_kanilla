from __future__ import annotations

import os

import requests
import streamlit as st

API_BASE_URL = "https://datatalks-ai-function.azurewebsites.net"
API_URL = f"{API_BASE_URL}/api/chat"




# لیست زبان‌ها: کد، اسم نمایشی
LANGUAGES = [
    ("sv", "Svenska"),
    ("en", "English"),
    ("fa", "فارسی"),
]

st.set_page_config(page_title="Kokchun RAG Chatbot", page_icon="🤖")

# انتخاب زبان در سایدبار
if "language" not in st.session_state:
    st.session_state.language = "sv"  # پیش‌فرض: سوئدی

selected_lang = st.sidebar.selectbox(
    "Language / Språk / زبان",
    options=LANGUAGES,
    format_func=lambda x: x[1],  # فقط اسم قشنگ را نشان بده
)

# کد زبان (sv/en/fa) را در session نگه می‌داریم
st.session_state.language = selected_lang[0]
current_lang = st.session_state.language

# متن‌های UI بر اساس زبان
if current_lang == "sv":
    TITLE = "🤖 Kokchun RAG Chatbot"
    DESCRIPTION = "Med denna chatbot kan du ställa frågor om innehållet i Kokchuns kurs."
    INPUT_PLACEHOLDER = "Skriv din fråga här..."
    SOURCES_LABEL = "🔍 Källor som användes i svaret"
    NO_SOURCES = "Inga specifika källor rapporterades."
    ERROR_PREFIX = "❌ Fel vid anslutning till API:"
elif current_lang == "fa":
    TITLE = "🤖 چت‌بات Kokchun RAG"
    DESCRIPTION = "با این چت‌بات می‌تونی دربارهٔ محتوای دوره‌ی کوکچون سؤال بپرسی."
    INPUT_PLACEHOLDER = "سؤالت را اینجا بنویس..."
    SOURCES_LABEL = "🔍 منابع استفاده‌شده در پاسخ"
    NO_SOURCES = "هیچ منبع مشخصی گزارش نشد."
    ERROR_PREFIX = "❌ خطا در ارتباط با API:"
else:  # en
    TITLE = "🤖 Kokchun RAG Chatbot"
    DESCRIPTION = "With this chatbot you can ask questions about Kokchun's course content."
    INPUT_PLACEHOLDER = "Type your question here..."
    SOURCES_LABEL = "🔍 Sources used in the answer"
    NO_SOURCES = "No specific sources were reported."
    ERROR_PREFIX = "❌ Error when connecting to API:"

# عنوان و توضیح صفحه
st.title(TITLE)
st.write(DESCRIPTION)

# نگه‌داشتن تاریخچه‌ی چت در session
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # [{"role": "user" / "assistant", "content": str}]

# نمایش تاریخچه
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ورودی کاربر (چت اینترفیسی)
question = st.chat_input(INPUT_PLACEHOLDER)

if question:
    # ذخیره و نمایش سوال کاربر
    st.session_state.chat_history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    # فرستادن سوال و زبان به API
    try:
        response = requests.post(
            API_URL,
            json={
                "question": question,
                "language": current_lang,  # 👈 مهم
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        answer = data.get("answer", "")

        # نمایش پاسخ
        with st.chat_message("assistant"):
            st.markdown(answer)

        st.session_state.chat_history.append(
            {"role": "assistant", "content": answer}
        )

        # نمایش منابع
        with st.expander(SOURCES_LABEL):
            sources = data.get("sources", [])
            if not sources:
                st.write(NO_SOURCES)
            else:
                for src in sources:
                    st.write(
                        f"- **{src.get('video_id', '')}** – chunk #{src.get('chunk_index', '')}"
                    )

    except requests.RequestException as e:
        error_msg = f"{ERROR_PREFIX} {e}"
        with st.chat_message("assistant"):
            st.markdown(error_msg)
        st.session_state.chat_history.append(
            {"role": "assistant", "content": error_msg}
        )
