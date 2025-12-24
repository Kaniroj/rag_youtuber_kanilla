import logging

import azure.functions as func
from azure.functions import AsgiMiddleware

# Import FastAPI app (måste funka i Azure, annars indexeras 0 functions)
from knowledge_base.api import app as fastapi_app

# ------------------------------------------------------------
# Azure Function App (Python v2 programming model)
# ------------------------------------------------------------
# Default auth: FUNCTION (kräver function key) – kan override per route
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# Skapa middleware en gång (inte per request)
asgi = AsgiMiddleware(fastapi_app)

# ------------------------------------------------------------
# Proxy ALLT till FastAPI
# ------------------------------------------------------------
# Viktigt:
# - Prefixet (/api eller inte) styrs av host.json -> extensions.http.routePrefix
# - Din route här ska bara vara "{*path}" och FastAPI bestämmer resten (t.ex. /rag/query)
@app.route(
    route="{*path}",
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    auth_level=func.AuthLevel.FUNCTION,
)
async def fastapi_proxy(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    return await asgi.handle_async(req, context)

# ------------------------------------------------------------
# Enkel test-endpoint (bra för att testa att indexing + auth funkar)
# ------------------------------------------------------------
@app.route(route="datatalks-rg", methods=["GET", "POST"], auth_level=func.AuthLevel.FUNCTION)
def datatalks_rg(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("datatalks-rg called")

    name = req.params.get("name")
    if not name:
        try:
            body = req.get_json()
            name = (body or {}).get("name")
        except ValueError:
            name = None

    if name:
        return func.HttpResponse(f"Hello, {name}.", status_code=200)

    return func.HttpResponse("OK. Pass ?name=... or JSON {'name': '...'}", status_code=200)

# ------------------------------------------------------------
# Public health check utan key (perfekt för att debugga URL/prefix)
# ------------------------------------------------------------
@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse("ok", status_code=200)
