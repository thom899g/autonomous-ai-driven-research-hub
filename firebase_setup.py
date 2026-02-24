"""
Firebase initialization and configuration for the AI Research Hub.
Handles Firestore database connection and real-time state management.
"""
import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

import firebase_admin
from firebase_admin import credentials, firestore, db
from google.cloud.firestore_v1 import Client as FirestoreClient
from google.cloud.firestore_v1.base_query import FieldFilter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FirebaseManager:
    """Manages Firebase connections and provides Firestore interface."""
    
    _instance: Optional['FirebaseManager'] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirebaseManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.db: Optional[FirestoreClient] = None
            self.realtime_db = None
            self._initialized = True
    
    def initialize(self, config_path: str = '.env') -> None:
        """
        Initialize Firebase connection using environment configuration.
        
        Args:
            config_path: Path to .env configuration file
            
        Raises:
            ValueError: If required Firebase configuration is missing
            RuntimeError: If Firebase initialization fails
        """
        try:
            # Load environment configuration
            firebase_config = self._load_firebase_config(config_path)
            
            # Create credentials dictionary
            cred_dict = {
                "type": "service_account",
                "project_id": firebase_config['FIREBASE_PROJECT_ID'],
                "private_key_id": firebase_config['FIREBASE_PRIVATE_KEY_ID'],
                "private_key": firebase_config['FIREBASE_PRIVATE_KEY'].replace('\\n', '\n'),
                "client_email": firebase_config['FIREBASE_CLIENT_EMAIL'],
                "client_id": firebase_config['FIREBASE_CLIENT_ID'],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": firebase_config['FIREBASE_CLIENT_X509_CERT_URL']
            }
            
            # Initialize Firebase app if not already initialized
            if not firebase_admin._apps:
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': f"https://{firebase_config['FIREBASE_PROJECT_ID']}.firebaseio.com"
                })
                logger.info("Firebase app initialized successfully")
            
            # Initialize Firestore and Realtime Database
            self.db = firestore.client()
            self.realtime_db = db.reference('/')
            
            # Test connection
            self._test_connection()
            logger.info("FirebaseManager initialized successfully")
            
        except KeyError as e:
            error_msg = f"Missing Firebase configuration key: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        except Exception as e:
            error_msg = f"Failed to initialize Firebase: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def _load_firebase_config(self, config_path: str) -> Dict[str, str]:
        """
        Load Firebase configuration from .env file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Dictionary of Firebase configuration values
            
        Raises:
            FileNotFoundError: If config file doesn't exist
        """
        config = {}
        try:
            with open(config_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            config[key.strip()] = value.strip().strip('"\'')
            
            # Validate required keys
            required_keys = [
                'FIREBASE_PROJECT_ID',
                'FIREBASE_PRIVATE_KEY_ID',
                'FIREBASE_PRIVATE_KEY',
                'FIREBASE_CLIENT_EMAIL',
                'FIREBASE_CLIENT_ID',
                'FIREBASE_CLIENT_X509_CERT_URL'
            ]
            
            missing_keys = [key for key in required_keys if key not in config]
            if missing_keys:
                raise KeyError(f"Missing keys: {missing_keys}")
                
            return config
            
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {config_path}")
            raise
    
    def _test_connection(self) -> None:
        """Test Firebase connection by writing and reading a test document."""
        try:
            test_ref =