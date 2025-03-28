import os
import sys
from dotenv import load_dotenv

class Config:
    def __init__(self):
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        self.download_dir = None
        self.db_url = None
        self.load()
        

    def load(self, filename: str = '.env'):
        env_path = os.path.join(self.root_dir, filename)
        if not self._get_env(env_path):
            raise Exception("Error loading environment file.")
        self.download_dir = self._setup_download_dir()
        self.db_url = self._get_db_url()

    def _get_env(self, filename: str = '.env'):
        try:
            if os.path.isfile(filename):
                load_dotenv(filename)
            return True
        except Exception as e:
            raise Exception(f"Error loading environment file: {e}")
            return False
    
    def _setup_download_dir(self):
        download_path = os.path.join(self.root_dir, os.getenv('DOWNLOAD_DIR', 'downloads'))
        try:
            os.makedirs(download_path, exist_ok=True)
            return download_path
        except Exception as e:
            raise Exception(f"Error setting up download directory: {e}")
            return None
    
    def _get_db_url(self):
        return os.getenv('DATABASE_URL', f"sqlite:///{self.root_dir}/bizlist.db")

class Settings():
    APP_NAME: str = 'BizList'

    class Config:
        case_sensitive = True

config = Config()
settings = Settings()