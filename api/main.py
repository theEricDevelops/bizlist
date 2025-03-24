# main.py
import os
from api.logger import Logger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router

# Configure logging
log_folder = os.getenv("LOG_FOLDER", "logs")
log_folder = os.path.abspath(log_folder)
log_file = os.path.join(log_folder, os.getenv("LOG_FILE", "bizlist.log"))

os.makedirs(log_folder, exist_ok=True)

log_level = os.getenv("LOG_LEVEL", "DEBUG")

# Create logger
log = Logger(__name__, log_file, log_level, console_log=True)

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