import logging
print("FUNCTION_APP LOADED (print)")
logging.warning("FUNCTION_APP LOADED (logging)")

import azure.functions as func
from azure.functions import AsgiMiddleware

# Import FastAPI app (must work in Azure; if it fails, functions may not be indexed)
try:
    from knowledge_base.api import app as fastapi_app
except Exception as e:
    logging.exception("FAILED importing FastAPI app: %s", e)
    raise

# Azure Function App (Python v2 programming model)
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# Create middleware once
asgi = AsgiMiddleware(fastapi_app)

# Proxy everything to FastAPI
@app.route(
    route="{*path}",
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    auth_level=func.AuthLevel.FUNCTION,
)
async def fastapi_proxy(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    return await asgi.handle_async(req, context)

# Simple test endpoint
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

# Public health check without key
@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse("ok", status_code=200)

# Ultra-minimal endpoint to test indexing (no FastAPI involved)
@app.route(route="ping", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def ping(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse("pong", status_code=200)
