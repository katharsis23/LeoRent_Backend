import firebase_admin
from firebase_admin import credentials
from src.leorent_backend.config.firebase import FIREBASE_CONFIG
from loguru import logger


def get_firebase_app():
    """Get or initialize Firebase app"""
    try:
        if not firebase_admin._apps:
            if not FIREBASE_CONFIG.type_:
                logger.warning(
                    "Firebase config not provided, skipping initialization"
                )
                return None

            cred_dict = FIREBASE_CONFIG.credentials_dict
            cred = credentials.Certificate(cred_dict)
            return firebase_admin.initialize_app(cred)
        return firebase_admin._apps[0]
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        return None


firebase_app = get_firebase_app()
