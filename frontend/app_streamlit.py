import os
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

DEFAULT_LOCAL = "http://localhost:7071/api/rag/query"
DEFAULT_AZURE = "https://kanilla-azure.azurewebsites.net/api/rag/query"

API_URL = os.getenv("KANILLA_API_URL") or DEFAULT_LOCAL

st.set_page_config(page_title="Kanilla RAG", page_icon="🧠")


def layout():
    st.title("🤓 Experimental Data Engineering — if it breaks, it was the data’s fault")
    st.caption(f"API: {API_URL}")

    question = st.text_input("Your question (English):")

    if st.button("Send") and question.strip():
        with st.spinner("Thinking..."):
            try:
                response = requests.post(
                    API_URL,
                    json={"prompt": question},
                    timeout=60,
                )

                if response.status_code != 200:
                    st.error(f"API error: {response.status_code}")
                    st.code(response.text)
                    return

                data = response.json()

                st.subheader("Answer")
                st.write(data.get("answer", "No answer returned"))

            except Exception as e:
                st.error("Request failed")
                st.exception(e)


if __name__ == "__main__":
    layout()
