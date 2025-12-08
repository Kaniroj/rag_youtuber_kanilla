from __future__ import annotations

import requests
import streamlit as st

API_URL = "http://localhost:7071/api/chat"

st.set_page_config(page_title="Kokchun RAG Chatbot", page_icon="🤖")

st.title("🤖 Kokchun RAG Chatbot")
st.write("Med denna chatbot kan du ställa frågor om innehållet i Kokchuns kurs.")

# Behåll chathistorik i session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # [{"role": "user" / "assistant", "content": str}]

# Visa chathistorik
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Användarens inmatning (chat-gränssnitt)
question = st.chat_input("Skriv din fråga här...")

if question:
    # Spara och visa användarens fråga
    st.session_state.chat_history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    # Skicka frågan till API
    try:
        response = requests.post(API_URL, json={"question": question}, timeout=60)
        response.raise_for_status()
        data = response.json()
        answer = data.get("answer", "")

        # Visa svaret
        with st.chat_message("assistant"):
            st.markdown(answer)

        st.session_state.chat_history.append(
            {"role": "assistant", "content": answer}
        )

        # Visa källor
        with st.expander("🔍 Källor som användes i svaret"):
            sources = data.get("sources", [])
            if not sources:
                st.write("Inga specifika källor rapporterades.")
            else:
                for src in sources:
                    st.write(
                        f"- **{src.get('video_id', '')}** – chunk #{src.get('chunk_index', '')}"
                    )

    except requests.RequestException as e:
        error_msg = f"❌ Fel vid anslutning till API: {e}"
        with st.chat_message("assistant"):
            st.markdown(error_msg)
        st.session_state.chat_history.append(
            {"role": "assistant", "content": error_msg}
        )
