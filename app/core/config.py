import os
from dotenv import load_dotenv

class Config:
    def __init__(self):
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        self.download_dir = None
        self.db_url = None
        self.settings = dict()
        self.load()
        

    def load(self, filename: str = '.env'):
        env_path = os.path.join(self.root_dir, filename)
        if not self._get_env(env_path):
            raise Exception("Error loading environment file.")
        self.download_dir = self._setup_download_dir()
        self.db_url = self._get_db_url()

    def _get_env(self, filename: str = '.env'):
        """Load environment variables from a .env file."""
        if not os.path.isfile(filename):
            raise FileNotFoundError(f"Environment file {filename} not found.")

        # Parse each line in the environment file and set the environment variables
        try:
            with open(filename) as f:
                for line in f:
                    if line.startswith('#') or not line.strip():
                        continue
                    key, value = line.strip().split('=', 1)
                    self.settings.update({key: value.strip('"').strip("'")})
                    os.environ[key] = value.strip('"').strip("'")
            return True
                    
        except Exception as e:
            raise Exception(f"Error parsing environment file: {e}")
    
    def _setup_download_dir(self):
        download_path = os.path.join(self.root_dir, os.getenv('DOWNLOAD_DIR', 'downloads'))
        try:
            os.makedirs(download_path, exist_ok=True)
            return download_path
        except Exception as e:
            raise Exception(f"Error setting up download directory: {e}")
    
    def _get_db_url(self):
        return os.getenv('DATABASE_URL', f"sqlite:///{self.root_dir}/bizlist.db")

config = Config()