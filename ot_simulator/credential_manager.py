"""Secure credential management for Zero-Bus configurations.

Encrypts sensitive credentials (OAuth secrets) before saving to disk.
Uses Fernet symmetric encryption with a machine-specific key.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet

logger = logging.getLogger("ot_simulator.credentials")


class CredentialManager:
    """Manages encrypted storage of OAuth credentials."""

    def __init__(self, config_dir: Path | None = None):
        """Initialize credential manager.

        Args:
            config_dir: Directory to store encrypted configs (default: ot_simulator/zerobus_configs)
        """
        if config_dir is None:
            config_dir = Path("ot_simulator") / "zerobus_configs"

        self.config_dir = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Generate or load encryption key (machine-specific)
        self.key_file = self.config_dir / ".encryption_key"
        self.cipher = self._get_or_create_cipher()

    def _get_or_create_cipher(self) -> Fernet:
        """Get or create encryption cipher with persistent key."""
        if self.key_file.exists():
            # Load existing key
            with open(self.key_file, "rb") as f:
                key = f.read()
            logger.info("Loaded existing encryption key")
        else:
            # Generate new key
            key = Fernet.generate_key()
            with open(self.key_file, "wb") as f:
                f.write(key)
            # Secure the key file (owner read/write only)
            self.key_file.chmod(0o600)
            logger.info("Generated new encryption key")

        return Fernet(key)

    def encrypt_credential(self, credential: str) -> str:
        """Encrypt a credential string.

        Args:
            credential: Plain text credential

        Returns:
            Base64-encoded encrypted credential
        """
        if not credential:
            return ""

        encrypted = self.cipher.encrypt(credential.encode())
        return base64.b64encode(encrypted).decode()

    def decrypt_credential(self, encrypted_credential: str) -> str:
        """Decrypt a credential string.

        Args:
            encrypted_credential: Base64-encoded encrypted credential

        Returns:
            Plain text credential
        """
        if not encrypted_credential:
            return ""

        try:
            encrypted = base64.b64decode(encrypted_credential.encode())
            decrypted = self.cipher.decrypt(encrypted)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt credential: {e}")
            return ""

    def save_config(self, protocol: str, config: dict[str, Any]) -> Path:
        """Save Zero-Bus configuration with encrypted credentials.

        Args:
            protocol: Protocol name (opcua, mqtt, modbus)
            config: Configuration dictionary with auth.client_id and auth.client_secret

        Returns:
            Path to saved config file
        """
        # Make a copy to avoid modifying the original
        config_copy = json.loads(json.dumps(config))

        # Encrypt the client secret if present
        if "auth" in config_copy:
            if "client_secret" in config_copy["auth"]:
                plain_secret = config_copy["auth"]["client_secret"]
                config_copy["auth"]["client_secret_encrypted"] = self.encrypt_credential(plain_secret)
                # Remove plain text secret
                del config_copy["auth"]["client_secret"]
                config_copy["auth"]["_encrypted"] = True

            if "client_id" in config_copy["auth"]:
                # Client ID doesn't need encryption (not sensitive)
                pass

        # Save to JSON file (YAML not needed, JSON is cleaner for this)
        config_file = self.config_dir / f"{protocol}_zerobus.json"
        with open(config_file, "w") as f:
            json.dump(config_copy, f, indent=2)

        # Secure the config file
        config_file.chmod(0o600)

        logger.info(f"Saved encrypted config for {protocol} to {config_file}")
        return config_file

    def load_config(self, protocol: str) -> dict[str, Any] | None:
        """Load and decrypt Zero-Bus configuration.

        Args:
            protocol: Protocol name (opcua, mqtt, modbus)

        Returns:
            Decrypted configuration dictionary or None if not found
        """
        config_file = self.config_dir / f"{protocol}_zerobus.json"

        if not config_file.exists():
            logger.debug(f"No saved config found for {protocol}")
            return None

        try:
            with open(config_file, "r") as f:
                config = json.load(f)

            # Decrypt the client secret if present
            if "auth" in config and config["auth"].get("_encrypted"):
                if "client_secret_encrypted" in config["auth"]:
                    encrypted_secret = config["auth"]["client_secret_encrypted"]
                    config["auth"]["client_secret"] = self.decrypt_credential(encrypted_secret)
                    # Remove encrypted version from returned config
                    del config["auth"]["client_secret_encrypted"]
                del config["auth"]["_encrypted"]

            logger.info(f"Loaded config for {protocol}")
            return config

        except Exception as e:
            logger.error(f"Failed to load config for {protocol}: {e}")
            return None

    def delete_config(self, protocol: str) -> bool:
        """Delete saved configuration.

        Args:
            protocol: Protocol name (opcua, mqtt, modbus)

        Returns:
            True if deleted, False if not found
        """
        config_file = self.config_dir / f"{protocol}_zerobus.json"

        if config_file.exists():
            config_file.unlink()
            logger.info(f"Deleted config for {protocol}")
            return True

        return False

    def list_configs(self) -> list[str]:
        """List all saved protocol configurations.

        Returns:
            List of protocol names with saved configs
        """
        configs = []
        for config_file in self.config_dir.glob("*_zerobus.json"):
            protocol = config_file.stem.replace("_zerobus", "")
            configs.append(protocol)

        return configs
