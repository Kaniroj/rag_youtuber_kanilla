import logging

import azure.functions as func
from azure.functions import AsgiMiddleware

# Import FastAPI app (måste funka i Azure, annars indexeras 0 functions)
from knowledge_base.api import app as fastapi_app


# ------------------------------------------------------------
# Azure Function App (Python v2 programming model)
# ------------------------------------------------------------
# Default auth: FUNCTION (kräver function key)
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# Skapa middleware en gång (inte per request)
asgi = AsgiMiddleware(fastapi_app)


# ------------------------------------------------------------
# Proxy ALLT under /api/* till FastAPI
# ------------------------------------------------------------
# OBS: Azure Functions lägger redan på prefixet "/api/" i URL:en,
# därför ska route INTE börja med "api/" här.
#
# Extern URL:  /api/rag/query  -> route="{*path}" får path="rag/query"
@app.route(
    route="{*path}",
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    auth_level=func.AuthLevel.FUNCTION,
)
async def fastapi_proxy(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    return await asgi.handle_async(req, context)


# ------------------------------------------------------------
# Enkel test-endpoint (bra för att testa att indexing funkar)
# ------------------------------------------------------------
@app.route(route="kokchun-azure", methods=["GET", "POST"], auth_level=func.AuthLevel.FUNCTION)
def kokchun_azure(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("kokchun-azure called")

    name = req.params.get("name")
    if not name:
        try:
            body = req.get_json()
            name = (body or {}).get("name")
        except ValueError:
            name = None

    if name:
        return func.HttpResponse(f"Hello, {name}.", status_code=200)

    return func.HttpResponse(
        "OK. Pass ?name=... or JSON {'name': '...'}",
        status_code=200,
    )


# ------------------------------------------------------------
# (Valfritt) Public health check utan key
# ------------------------------------------------------------
# @app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
# def health(req: func.HttpRequest) -> func.HttpResponse:
#     return func.HttpResponse("ok", status_code=200)
