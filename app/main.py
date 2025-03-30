# main.py
from app.services.logger import Logger
from app.core.config import config
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.routers.business import business_router
from app.routers.serpapi import serpapi_router
from app.routers.owens import owenscorning

log = Logger('app-main')

# Create FastAPI app

app = FastAPI(title=config.settings['APP_NAME'], debug=True)

@app.get("/")
def root():
    return {"message": "Welcome to the BizList API!"}

app.include_router(business_router, prefix="/businesses", tags=["businesses"])
app.include_router(serpapi_router, prefix="/serpapi", tags=["serpapi"])
app.include_router(owenscorning, prefix="/scrape/owenscorning", tags=["scraper", "owenscorning"])

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def catch_all(request: Request, path: str):
    """Catch-all route for any other paths not defined in the routers."""
    log.info(f"PATH NOT FOUND - Path: {path} - Method: {request.method}")
    return JSONResponse(
        status_code=404,
        content={
            "error": "404 - Not Found",
            "message": f"The requested path '{path}' was not found on the server.",
            "method": request.method
        }
    )
