import os
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

DEFAULT_LOCAL = "http://localhost:7071/api/rag/query"
DEFAULT_AZURE = "https://datatalks-ai-function.azurewebsites.net/api/rag/query"

API_URL = os.getenv("KANILLA_API_URL") or DEFAULT_AZURE
FUNCTION_KEY = os.getenv("KANILLA_FUNCTION_KEY")  # optional

st.set_page_config(page_title="Kanilla RAG", page_icon="🧠")

def post_rag(prompt: str) -> requests.Response:
    url = API_URL
    headers = {"Content-Type": "application/json"}

    # If your function auth requires a key:
    # Option A: query param ?code=...
    params = {"code": FUNCTION_KEY} if FUNCTION_KEY else None

    # Option B (alternative): header key (uncomment if you prefer)
    # if FUNCTION_KEY:
    #     headers["x-functions-key"] = FUNCTION_KEY

    return requests.post(
        url,
        json={"prompt": prompt},
        headers=headers,
        params=params,
        timeout=120,  # RAG can be slow
    )

def layout():
    st.title("🤓 Experimental Data Engineering — if it breaks, it was the data’s fault")
    st.caption(f"API: {API_URL}")

    question = st.text_input("Your question (English):")

    if st.button("Send") and question.strip():
        with st.spinner("Thinking..."):
            try:
                response = post_rag(question.strip())

                if response.status_code != 200:
                    st.error(f"API error: {response.status_code}")
                    st.code(response.text[:4000])
                    return

                # Safer JSON parsing
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
