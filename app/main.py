# main.py
from app.services.logger import Logger
from app.core.config import settings
from fastapi import FastAPI

from app.routers.business import business_router

log = Logger('app-main')

# Create FastAPI app

app = FastAPI(title=settings.APP_NAME, debug=True)

@app.get("/")
def root():
    return {"message": "Welcome to the BizList API!"}

app.include_router(business_router, prefix="/businesses", tags=["businesses"])
