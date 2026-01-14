"""OPC UA Security Configuration and Certificate Management.

Implements OPC UA 10101 security recommendations:
- Basic256Sha256 encryption
- Certificate-based authentication
- Username/password authentication
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from asyncua import ua
from asyncua.crypto import uacrypto
from asyncua.server.user_managers import UserManager

logger = logging.getLogger("ot_simulator.opcua_security")


@dataclass
class OPCUASecurityConfig:
    """OPC UA security configuration."""

    # Security mode
    enabled: bool = False
    security_policy: str = "Basic256Sha256"  # Basic256Sha256, NoSecurity
    security_mode: str = "SignAndEncrypt"  # Sign, SignAndEncrypt

    # Certificate paths (for server)
    server_cert_path: Optional[str] = None
    server_key_path: Optional[str] = None

    # Trusted client certificates directory
    trusted_certs_dir: Optional[str] = None

    # Username/password authentication
    enable_user_auth: bool = False
    users: dict[str, str] = None  # username: password

    def __post_init__(self):
        """Set defaults."""
        if self.users is None:
            self.users = {}


class OPCUASecurityManager:
    """Manages OPC UA server security configuration."""

    def __init__(self, config: OPCUASecurityConfig):
        """Initialize security manager.

        Args:
            config: Security configuration
        """
        self.config = config
        self.user_manager = None

        if config.enable_user_auth:
            self.user_manager = CustomUserManager(config.users)

    def get_security_policies(self) -> List[ua.SecurityPolicyType]:
        """Get list of security policies to enable.

        Returns:
            List of SecurityPolicyType enums
        """
        if not self.config.enabled:
            logger.info("Security disabled - using NoSecurity mode")
            return [ua.SecurityPolicyType.NoSecurity]

        policies = [ua.SecurityPolicyType.NoSecurity]  # Always allow NoSecurity for compatibility

        if self.config.security_policy == "Basic256Sha256":
            if self.config.security_mode == "Sign":
                policies.append(ua.SecurityPolicyType.Basic256Sha256_Sign)
                logger.info("Enabled security policy: Basic256Sha256_Sign")
            elif self.config.security_mode == "SignAndEncrypt":
                policies.append(ua.SecurityPolicyType.Basic256Sha256_SignAndEncrypt)
                logger.info("Enabled security policy: Basic256Sha256_SignAndEncrypt")
            else:
                logger.warning(f"Unknown security mode: {self.config.security_mode}, using SignAndEncrypt")
                policies.append(ua.SecurityPolicyType.Basic256Sha256_SignAndEncrypt)

        return policies

    def get_certificate_path(self) -> Optional[str]:
        """Get server certificate path.

        Returns:
            Path to certificate file or None
        """
        if not self.config.enabled or not self.config.server_cert_path:
            return None

        cert_path = Path(self.config.server_cert_path)
        if not cert_path.exists():
            logger.error(f"Server certificate not found: {cert_path}")
            return None

        logger.info(f"Using server certificate: {cert_path}")
        return str(cert_path)

    def get_private_key_path(self) -> Optional[str]:
        """Get server private key path.

        Returns:
            Path to private key file or None
        """
        if not self.config.enabled or not self.config.server_key_path:
            return None

        key_path = Path(self.config.server_key_path)
        if not key_path.exists():
            logger.error(f"Server private key not found: {key_path}")
            return None

        logger.info(f"Using server private key: {key_path}")
        return str(key_path)

    def validate_configuration(self) -> bool:
        """Validate security configuration.

        Returns:
            True if configuration is valid, False otherwise
        """
        if not self.config.enabled:
            return True

        # Check certificate files exist
        if self.config.server_cert_path:
            if not Path(self.config.server_cert_path).exists():
                logger.error(f"Server certificate not found: {self.config.server_cert_path}")
                return False
        else:
            logger.error("Security enabled but no server certificate path provided")
            return False

        if self.config.server_key_path:
            if not Path(self.config.server_key_path).exists():
                logger.error(f"Server private key not found: {self.config.server_key_path}")
                return False
        else:
            logger.error("Security enabled but no server private key path provided")
            return False

        # Check trusted certs directory
        if self.config.trusted_certs_dir:
            trusted_dir = Path(self.config.trusted_certs_dir)
            if not trusted_dir.exists():
                logger.warning(f"Trusted certs directory not found: {trusted_dir}, creating...")
                trusted_dir.mkdir(parents=True, exist_ok=True)

        logger.info("✓ Security configuration is valid")
        return True


class CustomUserManager(UserManager):
    """Custom user manager for username/password authentication."""

    def __init__(self, users: dict[str, str]):
        """Initialize user manager.

        Args:
            users: Dictionary of username: password
        """
        super().__init__()
        self.users = users
        logger.info(f"Initialized user authentication with {len(users)} users")

    def check_credentials(self, username: str, password: str) -> bool:
        """Check if username and password are valid.

        Args:
            username: Username
            password: Password

        Returns:
            True if credentials are valid, False otherwise
        """
        if username in self.users:
            if self.users[username] == password:
                logger.info(f"✓ User authenticated: {username}")
                return True
            else:
                logger.warning(f"✗ Authentication failed for user: {username} (invalid password)")
                return False
        else:
            logger.warning(f"✗ Authentication failed: unknown user {username}")
            return False


def create_security_config_from_dict(config_dict: dict) -> OPCUASecurityConfig:
    """Create security configuration from dictionary.

    Args:
        config_dict: Configuration dictionary

    Returns:
        OPCUASecurityConfig instance
    """
    return OPCUASecurityConfig(
        enabled=config_dict.get("enabled", False),
        security_policy=config_dict.get("security_policy", "Basic256Sha256"),
        security_mode=config_dict.get("security_mode", "SignAndEncrypt"),
        server_cert_path=config_dict.get("server_cert_path"),
        server_key_path=config_dict.get("server_key_path"),
        trusted_certs_dir=config_dict.get("trusted_certs_dir"),
        enable_user_auth=config_dict.get("enable_user_auth", False),
        users=config_dict.get("users", {}),
    )
