import requests
from dotenv import load_dotenv
import os
 
load_dotenv()
url = f"https://kanilla-azure.azurewebsites.net/rag/query?code={os.getenv('FUNCTION_CODE')}"
 
response = requests.post(url= url, json= {"prompt": "advanced SQL"})
print(response)