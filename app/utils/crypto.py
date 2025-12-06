import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import hashlib
import logging

# Global variables to store encryption keys
CRYPTO_KEY = None
CRYPTO_SALT = None

logger = logging.getLogger(__name__)

class CryptoUtils:
    """Encryption utility class for handling password encryption and decryption"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CryptoUtils, cls).__new__(cls)
            cls._instance._init_crypto()
        return cls._instance
    
    def _init_crypto(self):
        """Initialize encryption keys"""
        global CRYPTO_KEY, CRYPTO_SALT
        
        if CRYPTO_KEY and CRYPTO_SALT:
            self.key = CRYPTO_KEY
            self.salt = CRYPTO_SALT
            return
        
        # Temporary values, will be replaced on login
        self.salt = b"temporary_salt_will_be_replaced"
        self.key = os.urandom(32)  # Ensure 32 bytes (256 bits)
        
        CRYPTO_KEY = self.key
        CRYPTO_SALT = self.salt
        
    def encrypt(self, plain_text: str) -> str:
        """Encrypt plaintext"""
        # Re-fetch key in case it was updated globally
        global CRYPTO_KEY
        if CRYPTO_KEY:
             self.key = CRYPTO_KEY

        if not plain_text:
            return None
            
        nonce = os.urandom(12)
        cipher = AESGCM(self.key)
        encrypted = cipher.encrypt(nonce, plain_text.encode('utf-8'), None)
        result = base64.b64encode(nonce + encrypted).decode('utf-8')
        return f"ENC:{result}"
    
    def decrypt(self, encrypted_text: str) -> str:
        """Decrypt ciphertext"""
        # Re-fetch key in case it was updated globally
        global CRYPTO_KEY
        if CRYPTO_KEY:
             self.key = CRYPTO_KEY

        if not encrypted_text:
            return None
            
        if not encrypted_text.startswith("ENC:"):
            return encrypted_text
            
        encrypted_text = encrypted_text[4:]
        
        try:
            data = base64.b64decode(encrypted_text)
            nonce = data[:12]
            ciphertext = data[12:]
            
            cipher = AESGCM(self.key)
            return cipher.decrypt(nonce, ciphertext, None).decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            return encrypted_text
    
    def is_encrypted(self, text: str) -> bool:
        """Check if text is encrypted"""
        return text and isinstance(text, str) and text.startswith("ENC:")

def set_crypto_keys(key, salt):
    """Set encryption keys globally"""
    global CRYPTO_KEY, CRYPTO_SALT
    
    if isinstance(key, str):
        key = base64.b64decode(key)
    if isinstance(salt, str):
        salt = base64.b64decode(salt)
    
    if len(key) != 32:
        raise ValueError("AES-GCM key must be 256 bits (32 bytes)")
        
    CRYPTO_KEY = key
    CRYPTO_SALT = salt
    
    # Update singleton instance if exists
    if CryptoUtils._instance:
        CryptoUtils._instance.key = key
        CryptoUtils._instance.salt = salt

def derive_key_from_credentials(username, password):
    """Derive encryption key from username and password"""
    combined = f"{username}:{password}".encode('utf-8')
    salt = hashlib.sha256(username.encode('utf-8')).digest()[:16]
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = kdf.derive(combined)
    assert len(key) == 32, "Derived key length must be 32 bytes"
    return key, salt
