# main.py
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router

# Configure logging
log_folder = os.getenv("LOG_FOLDER", "logs")
log_folder = os.path.abspath(log_folder)
log_file = os.path.join(log_folder, os.getenv("LOG_FILE", "bizlist.log"))
log_format = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
os.makedirs(log_folder, exist_ok=True)

log_level_str = os.getenv("LOG_LEVEL", "DEBUG")
log_level = getattr(logging, log_level_str.upper(), logging.DEBUG)

logger = logging.getLogger(__name__)
logger.setLevel(log_level)
lh = logging.FileHandler(log_file, mode="w")
lh.setFormatter(logging.Formatter(log_format))
logger.addHandler(lh)

app = FastAPI()

# CORS middleware
origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)