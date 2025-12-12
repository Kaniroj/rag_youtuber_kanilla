import azure.functions as func
from src.api import app as fastapi_app

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)



@app.route(route="{*route}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def fastapi_proxy(
    req: func.HttpRequest, context: func.Context
) -> func.HttpResponse:
    return await func.AsgiMiddleware(fastapi_app).handle_async(req, context)
