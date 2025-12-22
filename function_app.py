import logging

import azure.functions as func
from azure.functions import AsgiMiddleware

# FastAPI app شما
from knowledge_base.api import app as fastapi_app


# -----------------------------
# Azure Function App
# -----------------------------
# پیش‌فرض را امن‌تر می‌گذاریم: FUNCTION
# (یعنی همه‌ی routeها به کلید Function نیاز دارند مگر اینکه جداگانه Anonymous تعریف شوند)
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# Middleware را یک‌بار می‌سازیم تا هر درخواست دوباره instantiate نشود
asgi = AsgiMiddleware(fastapi_app)


# -----------------------------
# FastAPI proxy (بهتر: روی یک prefix)
# -----------------------------
# برای جلوگیری از تداخل با routeهای دیگر، catch-all را روی api/ می‌گذاریم
@app.route(
    route="api/{*path}",
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    auth_level=func.AuthLevel.FUNCTION,  # صریح و واضح
)
async def fastapi_proxy(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    """
    Proxy all HTTP requests under /api/* to the FastAPI application.
    """
    return await asgi.handle_async(req, context)


# -----------------------------
# A simple test endpoint
# -----------------------------
@app.route(route="kanilla_azure", auth_level=func.AuthLevel.FUNCTION, methods=["GET", "POST"])
def kanilla_azure(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Python HTTP trigger function processed a request.")

    name = req.params.get("name")
    if not name:
        try:
            req_body = req.get_json()
            name = (req_body or {}).get("name")
        except ValueError:
            name = None

    if name:
        return func.HttpResponse(
            f"Hello, {name}. This HTTP triggered function executed successfully.",
            status_code=200,
        )

    return func.HttpResponse(
        "This HTTP triggered function executed successfully. "
        "Pass a name in the query string or in the request body for a personalized response.",
        status_code=200,
    )


# -----------------------------
# Optional: a public health check
# -----------------------------
# اگر واقعاً لازم داری یک endpoint عمومی داشته باشی (برای health probe)، این را باز کن:
#
# @app.route(route="health", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
# def health(req: func.HttpRequest) -> func.HttpResponse:
#     return func.HttpResponse("ok", status_code=200)
