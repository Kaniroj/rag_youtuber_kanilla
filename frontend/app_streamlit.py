import os
import requests
import streamlit as st
from dotenv import load_dotenv

# Load environment variables from .env (if present)
load_dotenv()

# Toggle: set True to use local Functions host, False to use Azure
#lockal
#USE_LOCAL = True
USE_LOCAL = False
# Default endpoints (match your Swagger: POST /rag/query)
DEFAULT_LOCAL = "http://localhost:7071/rag/query"
DEFAULT_AZURE = "https://datatalks-ai-function.azurewebsites.net/rag/query"

# Choose base URL:
# 1) Start from defaults (local vs azure)
# 2) Allow override via .env: KANILLA_API_URL
API_URL = DEFAULT_LOCAL if USE_LOCAL else DEFAULT_AZURE
API_URL = os.getenv("KANILLA_API_URL", API_URL)

# Optional: Azure Functions key (Host key 'default')
FUNCTION_KEY = os.getenv("KANILLA_FUNCTION_KEY")

st.set_page_config(page_title="datatalks-rg", page_icon="🧠")


def post_rag(prompt: str) -> requests.Response:
    headers = {"Content-Type": "application/json"}

    # If auth_level=FUNCTION in Azure, you need the key:
    # it can be passed as query param ?code=...
    params = {"code": FUNCTION_KEY} if FUNCTION_KEY else None

    return requests.post(
        API_URL,
        json={"prompt": prompt},  # matches OpenAPI schema: Prompt(prompt: str)
        headers=headers,
        params=params,
        timeout=120,
    )


def layout():
    st.title("🤓 Experimental Data Engineering — if it breaks, it was the data’s fault")

    # Debug info so you always know what you're calling
    st.caption(f"API: {API_URL}")
    #st.caption(f"Has key: {bool(FUNCTION_KEY)} | USE_LOCAL: {USE_LOCAL}")

    question = st.text_input("Your question (English):")

    if st.button("Send") and question.strip():
        with st.spinner("Thinking..."):
            try:
                response = post_rag(question.strip())

                if response.status_code != 200:
                    st.error(f"API error: {response.status_code}")
                    st.code(response.text[:4000])
                    return

                try:
                    data = response.json()
                except ValueError:
                    st.error("API returned non-JSON response")
                    st.code(response.text[:4000])
                    return

                st.subheader("Answer")
                st.write(data.get("answer") or data.get("result") or "No answer returned")

            except requests.Timeout:
                st.error("Request timed out (try again or increase timeout).")
            except Exception as e:
                st.error("Request failed")
                st.exception(e)


if __name__ == "__main__":
    layout()
