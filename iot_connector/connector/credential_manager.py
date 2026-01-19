"""
Credential encryption and management utilities.

Provides secure storage and retrieval of sensitive credentials used by the connector:
- Databricks OAuth2 client credentials
- Protocol endpoint passwords (OPC-UA, MQTT, Modbus)
- TLS certificates and private keys

Uses Fernet (AES-256-CBC) for symmetric encryption with key derivation from password.
"""

import os
import base64
import json
from pathlib import Path
from typing import Dict, Any, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

import logging

logger = logging.getLogger(__name__)


class CredentialManager:
    """
    Secure credential storage with Fernet encryption.

    Features:
        - AES-256-CBC encryption via Fernet
        - PBKDF2 key derivation with 480,000 iterations
        - Per-installation salt (random, stored in plaintext)
        - JSON storage format for structured credentials
        - Environment variable fallback for credentials

    Security Model:
        - Master password required for encryption/decryption
        - Salt stored alongside encrypted data (standard practice)
        - Keys derived using PBKDF2-HMAC-SHA256
        - Credentials stored in ~/.databricks_iot_connector/credentials.enc
    """

    def __init__(
        self,
        credentials_file: Optional[Path] = None,
        master_password: Optional[str] = None
    ):
        """
        Initialize credential manager.

        Args:
            credentials_file: Path to encrypted credentials file
                             (default: ~/.databricks_iot_connector/credentials.enc)
            master_password: Master password for encryption/decryption
                            (can also be set via CONNECTOR_MASTER_PASSWORD env var)
        """
        if credentials_file is None:
            credentials_file = Path.home() / ".databricks_iot_connector" / "credentials.enc"

        self.credentials_file = Path(credentials_file)
        self.credentials_file.parent.mkdir(parents=True, exist_ok=True)

        # Get master password from arg or environment
        self.master_password = master_password or os.getenv('CONNECTOR_MASTER_PASSWORD')

        if not self.master_password:
            logger.warning("No master password provided. Credential encryption disabled.")
            logger.warning("Set CONNECTOR_MASTER_PASSWORD environment variable to enable.")

        self._cipher = None
        self._salt = None

        # Load or generate salt
        self._load_or_create_salt()

    def _load_or_create_salt(self):
        """Load existing salt or generate new one."""
        salt_file = self.credentials_file.parent / "salt.txt"

        if salt_file.exists():
            # Load existing salt
            with open(salt_file, 'r') as f:
                self._salt = base64.b64decode(f.read().strip())
            logger.debug("Loaded existing salt")
        else:
            # Generate new random salt
            self._salt = os.urandom(16)
            with open(salt_file, 'w') as f:
                f.write(base64.b64encode(self._salt).decode('utf-8'))
            logger.info("Generated new salt for credential encryption")

    def _get_cipher(self) -> Optional[Fernet]:
        """Get or create Fernet cipher."""
        if self._cipher:
            return self._cipher

        if not self.master_password:
            return None

        # Derive key from master password using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._salt,
            iterations=480000,  # OWASP recommended minimum
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_password.encode('utf-8')))
        self._cipher = Fernet(key)

        return self._cipher

    def store_credentials(self, credentials: Dict[str, Any]) -> bool:
        """
        Store encrypted credentials to disk.

        Args:
            credentials: Dictionary of credentials to encrypt and store

        Returns:
            True if successful, False otherwise
        """
        cipher = self._get_cipher()
        if not cipher:
            logger.error("Cannot store credentials without master password")
            return False

        try:
            # Serialize to JSON
            json_data = json.dumps(credentials, indent=2)

            # Encrypt
            encrypted = cipher.encrypt(json_data.encode('utf-8'))

            # Write to file
            with open(self.credentials_file, 'wb') as f:
                f.write(encrypted)

            # Set restrictive permissions (owner read/write only)
            os.chmod(self.credentials_file, 0o600)

            logger.info(f"Stored encrypted credentials to {self.credentials_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to store credentials: {e}")
            return False

    def load_credentials(self) -> Optional[Dict[str, Any]]:
        """
        Load and decrypt credentials from disk.

        Returns:
            Dictionary of credentials, or None if file doesn't exist or decryption fails
        """
        if not self.credentials_file.exists():
            logger.debug("Credentials file does not exist")
            return None

        cipher = self._get_cipher()
        if not cipher:
            logger.error("Cannot load credentials without master password")
            return None

        try:
            # Read encrypted data
            with open(self.credentials_file, 'rb') as f:
                encrypted = f.read()

            # Decrypt
            decrypted = cipher.decrypt(encrypted)

            # Parse JSON
            credentials = json.loads(decrypted.decode('utf-8'))

            logger.debug("Loaded encrypted credentials")
            return credentials

        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            return None

    def get_credential(self, key: str, default: Any = None) -> Any:
        """
        Get a specific credential by key.

        Precedence:
            1. Environment variable (uppercase key with CONNECTOR_ prefix)
            2. Encrypted credentials file
            3. Default value

        Args:
            key: Credential key (e.g., 'zerobus.client_id')
            default: Default value if credential not found

        Returns:
            Credential value or default
        """
        # Check environment variable first (security best practice for containers)
        env_key = f"CONNECTOR_{key.upper().replace('.', '_')}"
        env_value = os.getenv(env_key)
        if env_value:
            return env_value

        # Check encrypted credentials
        credentials = self.load_credentials()
        if credentials:
            # Support nested keys (e.g., 'zerobus.client_id')
            parts = key.split('.')
            value = credentials
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return default
            return value

        return default

    def delete_credentials(self) -> bool:
        """
        Delete encrypted credentials file.

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.credentials_file.exists():
                self.credentials_file.unlink()
                logger.info("Deleted credentials file")
            return True
        except Exception as e:
            logger.error(f"Failed to delete credentials: {e}")
            return False

    def update_credential(self, key: str, value: Any) -> bool:
        """
        Update a single credential.

        Args:
            key: Credential key (supports nested keys with dots)
            value: New credential value

        Returns:
            True if successful, False otherwise
        """
        # Load existing credentials
        credentials = self.load_credentials() or {}

        # Update nested key
        parts = key.split('.')
        current = credentials
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value

        # Store updated credentials
        return self.store_credentials(credentials)


class CredentialInjector:
    """
    Inject credentials from secure storage into configuration dictionaries.

    Replaces placeholder values like '${credential:zerobus.client_secret}' with
    actual credentials from CredentialManager.
    """

    def __init__(self, credential_manager: CredentialManager):
        """
        Initialize credential injector.

        Args:
            credential_manager: CredentialManager instance
        """
        self.credential_manager = credential_manager

    def inject(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively inject credentials into configuration.

        Args:
            config: Configuration dictionary with placeholders

        Returns:
            Configuration with credentials injected
        """
        if isinstance(config, dict):
            return {
                k: self.inject(v)
                for k, v in config.items()
            }
        elif isinstance(config, list):
            return [self.inject(item) for item in config]
        elif isinstance(config, str) and config.startswith('${credential:') and config.endswith('}'):
            # Extract credential key
            key = config[13:-1]  # Remove '${credential:' and '}'

            # Get credential
            value = self.credential_manager.get_credential(key)

            if value is None:
                logger.warning(f"Credential not found: {key}")
                return config  # Return placeholder if not found

            return value
        else:
            return config


def generate_master_password() -> str:
    """
    Generate a secure random master password.

    Returns:
        Base64-encoded 32-byte random password
    """
    return base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8')


# CLI helper for credential management
if __name__ == '__main__':
    import sys
    import getpass

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python credential_manager.py store <key> <value>  - Store a credential")
        print("  python credential_manager.py get <key>            - Get a credential")
        print("  python credential_manager.py delete               - Delete all credentials")
        print("  python credential_manager.py generate-password    - Generate master password")
        sys.exit(1)

    command = sys.argv[1]

    if command == 'generate-password':
        password = generate_master_password()
        print(f"Generated master password: {password}")
        print("\nSet this as environment variable:")
        print(f"export CONNECTOR_MASTER_PASSWORD='{password}'")
        sys.exit(0)

    # Get master password
    master_password = os.getenv('CONNECTOR_MASTER_PASSWORD')
    if not master_password:
        master_password = getpass.getpass("Enter master password: ")

    manager = CredentialManager(master_password=master_password)

    if command == 'store':
        if len(sys.argv) != 4:
            print("Usage: python credential_manager.py store <key> <value>")
            sys.exit(1)

        key = sys.argv[2]
        value = sys.argv[3]

        if manager.update_credential(key, value):
            print(f"✓ Stored credential: {key}")
        else:
            print(f"✗ Failed to store credential: {key}")
            sys.exit(1)

    elif command == 'get':
        if len(sys.argv) != 3:
            print("Usage: python credential_manager.py get <key>")
            sys.exit(1)

        key = sys.argv[2]
        value = manager.get_credential(key)

        if value is not None:
            print(f"{key} = {value}")
        else:
            print(f"Credential not found: {key}")
            sys.exit(1)

    elif command == 'delete':
        confirm = input("Delete all encrypted credentials? (yes/no): ")
        if confirm.lower() == 'yes':
            if manager.delete_credentials():
                print("✓ Deleted all credentials")
            else:
                print("✗ Failed to delete credentials")
                sys.exit(1)
        else:
            print("Cancelled")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
