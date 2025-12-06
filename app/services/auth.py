import jwt
import time
import datetime
from typing import Optional, Dict, Any
from app.core.config import settings
from app.utils.crypto import derive_key_from_credentials, set_crypto_keys
import logging

logger = logging.getLogger(__name__)

class AuthService:
    def create_token(self, user_id: str) -> str:
        payload = {
            'user_id': user_id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=settings.JWT_EXPIRATION_SECONDS)
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def authenticate_user(self, username, password) -> bool:
        if not settings.ADMIN_USERNAME or not settings.ADMIN_PASSWORD:
            logger.error("Admin credentials not set")
            return False
            
        if username == settings.ADMIN_USERNAME and password == settings.ADMIN_PASSWORD:
            # Initialize crypto keys on successful login
            try:
                key, salt = derive_key_from_credentials(username, password)
                set_crypto_keys(key, salt)
                logger.info(f"Crypto keys derived successfully for user {username}")
                return True
            except Exception as e:
                logger.error(f"Failed to derive crypto keys: {str(e)}")
                return False
        return False

auth_service = AuthService()
