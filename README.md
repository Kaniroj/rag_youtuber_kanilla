# rag_youtuber_kanilla


RAG Youtuber – AI-chattbot för data engineering-innehåll

Detta projekt är en Retrieval Augmented Generation (RAG)-chattbot byggd för en YouTuber inom data engineering.
Användare kan ställa frågor om videoinnehåll och få svar som är förankrade i de faktiska transkripten från videorna.

Syftet är att göra långa tekniska videor sökbara, interaktiva och mer lättillgängliga.


Idé

YouTube-videor innehåller mycket värdefull kunskap, men
– informationen är svår att söka i
– tittare vill ofta ställa följdfrågor

Detta projekt omvandlar transkript till en vektorbaserad kunskapsdatabas och gör innehållet tillgängligt via en chattbot.

Arkitektur (översikt)

Videotranskript embed-das och lagras i LanceDB

Användarens fråga embed-das

Relevanta textstycken hämtas via vektorsökning

Ett LLM genererar svar baserat på hämtad kontext (RAG)

Resultatet exponeras via ett serverlöst FastAPI-API

Teknikstack:
Python 3.11
FastAPI + PydanticAI
LanceDB (vektordatabas)
Azure Functions (serverless backend)
HTML / JavaScript-frontend

Projektstruktur

src/
├── api.py – FastAPI-app och endpoints
├── rag_engine.py – RAG-logik
├── history_store.py – Sessionsbaserat minne
├── video_mvp.py – YouTube-beskrivning och taggar
├── schemas.py
└── config.py

function_app.py – Azure Functions ASGI-proxy

Genomförda uppgifter

Obligatoriska (G):
– Datainläsning till vektordatabas
– RAG-pipeline med PydanticAI
– FastAPI-backend
– Serverless deployment med Azure Functions

MVP-utökningar (VG):
– Sessionsbaserat chattminne
– Endpoint för chathistorik
– Chatt-UI med full konversationsvy
– Endpoints för
• Generering av YouTube-beskrivningar
• Generering av YouTube-taggar (20–40 nyckelord)

🔌 API-endpoints

GET /
GET /api/health
POST /api/chat
GET /api/history/{session_id}
DELETE /api/history/{session_id}
GET /api/videos/{video_id}/description
GET /api/videos/{video_id}/tags

Köra projektet lokalt

pip install -r requirements.txt
func start

Öppna i webbläsare:
http://localhost:7071

🎥 Demo-video

En demo-video (5–10 minuter) visar:
– RAG-chatt i praktiken
– Sessionsminne
– API-endpoints
– Genomgång av kodstruktur

Länk till video: (lägg till här)

Avslutande kommentar

Projektet visar hur AI engineering och data engineering kan kombineras för att förvandla statiskt utbildningsinnehåll till en interaktiv lärplattform.
Det är byggt som ett proof-of-concept med tydliga MVP-funktioner och en ren, utbyggbar arkitektur.