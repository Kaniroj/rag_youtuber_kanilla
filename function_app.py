import azure.functions as func
from azure.functions import AsgiMiddleware

# FastAPI app شما
from knowledge_base.api import app as fastapi_app


# Azure Function App
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.route(
    route="{*path}",
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
)
async def fastapi_proxy(
    req: func.HttpRequest,
    context: func.Context,
) -> func.HttpResponse:
    """
    Proxy all HTTP requests to the FastAPI application.
    """
    return await AsgiMiddleware(fastapi_app).handle_async(req, context)


@app.route(route="kanilla_azure", auth_level=func.AuthLevel.FUNCTION)
def kanilla_azure(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')

    if name:
        return func.HttpResponse(f"Hello, {name}. This HTTP triggered function executed successfully.")
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )