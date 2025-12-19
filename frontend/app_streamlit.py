import streamlit as st
import requests
import os
from dotenv import load_dotenv
 
load_dotenv()
API_URL = "http://127.0.0.1:8000/rag/query"
# اگر Azure Functions:

#API_URL = f"https://kanilla-azure.azurewebsites.net/rag/query?code={os.getenv('FUNCTION_CODE')}"


def layout():
    st.title("🤓 Experimental Data Engineering — if it breaks, it was the data’s fault")
    st.write("Ask here — we’ll blame the data.")

    question = st.text_input("Your question:")

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

                st.subheader("Question")
                st.write(question)

                st.subheader("Answer")
                st.write(data.get("answer", "No answer returned"))

                sources = data.get("sources", [])
                if sources:
                    st.subheader("Sources")
                    for s in sources:
                        st.write(
                            f"- {s['source_file']} (chunk {s['chunk_index']})"
                        )

            except Exception as e:
                st.error("Request failed")
                st.exception(e)


if __name__ == "__main__":
    layout()
