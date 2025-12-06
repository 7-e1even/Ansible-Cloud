import os
import yaml
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Ansible UI"
    API_V1_STR: str = "/api"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change_me_in_production_please")
    JWT_EXPIRATION_SECONDS: int = 5 * 60 * 60  # 5 hours
    
    # Admin Credentials
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin"
    
    # Database
    DB_PATH: str = "db/ansible.db"
    
    # File Uploads
    UPLOAD_FOLDER: str = "/tmp/ansible_uploads"
    
    # Logs
    LOG_DIR: str = "logs"
    
    # Tencent Cloud
    TENCENT_SECRET_ID: Optional[str] = os.getenv("TENCENT_SECRET_ID")
    TENCENT_SECRET_KEY: Optional[str] = os.getenv("TENCENT_SECRET_KEY")
    TENCENT_REGION: str = os.getenv("TENCENT_REGION", "ap-guangzhou")

    class Config:
        case_sensitive = True
        env_file = ".env"

    def load_from_yaml(self, path: str = "config.yaml"):
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                    if config_data:
                        if 'admin' in config_data:
                            self.ADMIN_USERNAME = config_data['admin'].get('username', self.ADMIN_USERNAME)
                            self.ADMIN_PASSWORD = config_data['admin'].get('password', self.ADMIN_PASSWORD)
                        if 'tencent' in config_data:
                            self.TENCENT_SECRET_ID = config_data['tencent'].get('secret_id', self.TENCENT_SECRET_ID)
                            self.TENCENT_SECRET_KEY = config_data['tencent'].get('secret_key', self.TENCENT_SECRET_KEY)
                            self.TENCENT_REGION = config_data['tencent'].get('region', self.TENCENT_REGION)
            except Exception as e:
                print(f"Warning: Failed to load config from {path}: {e}")

    def is_login_enabled(self, path: str = "config.yaml") -> bool:
        """Check if login is enabled from config file (hot reload)"""
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                    if config_data:
                        return config_data.get('enable_login', False)
            except Exception as e:
                print(f"Warning: Failed to read enable_login from {path}: {e}")
        return False

settings = Settings()
settings.load_from_yaml("config.yaml")

# Ensure directories exist
os.makedirs(os.path.dirname(settings.DB_PATH), exist_ok=True)
os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(settings.LOG_DIR, exist_ok=True)
os.makedirs("data", exist_ok=True)
