"""
Configuration Loader for Databricks IoT Connector

Loads configuration from YAML files and GUI state (JSON).
Supports environment variable expansion and validation.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import yaml

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Loads and validates connector configuration from YAML and JSON state files."""

    def __init__(self, config_path: str = "config"):
        """
        Initialize config loader.

        Args:
            config_path: Path to config file OR directory containing config files
        """
        config_path = Path(config_path)

        # Check if it's a file or directory
        if config_path.is_file() or (not config_path.exists() and config_path.suffix in ['.yaml', '.yml']):
            # It's a file path
            self.yaml_config_path = config_path
            self.config_dir = config_path.parent
            self.state_config_path = self.config_dir / "connector_state.json"
        else:
            # It's a directory
            self.config_dir = config_path
            self.yaml_config_path = self.config_dir / "connector.yaml"
            self.state_config_path = self.config_dir / "connector_state.json"

        self._config: Optional[Dict[str, Any]] = None

    def load(self) -> Dict[str, Any]:
        """
        Load configuration from YAML and JSON state files.

        Priority: connector_state.json (GUI) > connector.yaml > defaults

        Returns:
            Merged configuration dictionary
        """
        config = {}

        # Load YAML config if exists
        if self.yaml_config_path.exists():
            logger.info(f"Loading YAML config from {self.yaml_config_path}")
            with open(self.yaml_config_path, 'r') as f:
                yaml_config = yaml.safe_load(f)
                if yaml_config:
                    config = self._expand_env_vars(yaml_config)

        # Load JSON state (GUI config) if exists - overwrites YAML
        if self.state_config_path.exists():
            logger.info(f"Loading GUI state from {self.state_config_path}")
            with open(self.state_config_path, 'r') as f:
                state_config = json.load(f)
                if state_config:
                    config = self._merge_configs(config, state_config)

        # Validate configuration
        self._validate_config(config)

        self._config = config
        return config

    def save_state(self, config: Dict[str, Any]):
        """
        Save configuration to JSON state file (for GUI).

        Args:
            config: Configuration dictionary to save
        """
        self.config_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Saving GUI state to {self.state_config_path}")
        with open(self.state_config_path, 'w') as f:
            json.dump(config, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key (dot notation supported).

        Args:
            key: Configuration key (e.g., 'zerobus.workspace_host')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        if self._config is None:
            self.load()

        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    @property
    def config(self) -> Dict[str, Any]:
        """Get the full configuration dictionary."""
        if self._config is None:
            self.load()
        return self._config

    def _expand_env_vars(self, config: Any) -> Any:
        """
        Recursively expand environment variables in config.

        Supports ${VAR_NAME} format.

        Args:
            config: Configuration value (dict, list, str)

        Returns:
            Config with environment variables expanded
        """
        if isinstance(config, dict):
            return {k: self._expand_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._expand_env_vars(v) for v in config]
        elif isinstance(config, str):
            # Expand ${VAR_NAME} or $VAR_NAME
            import re
            def replace_var(match):
                var_name = match.group(1)
                return os.environ.get(var_name, match.group(0))

            # Match ${VAR} or $VAR
            pattern = r'\$\{([A-Z_][A-Z0-9_]*)\}|\$([A-Z_][A-Z0-9_]*)'
            return re.sub(pattern, lambda m: os.environ.get(m.group(1) or m.group(2), m.group(0)), config)
        else:
            return config

    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two configuration dictionaries.

        Args:
            base: Base configuration
            override: Override configuration (takes precedence)

        Returns:
            Merged configuration
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    def _validate_config(self, config: Dict[str, Any]):
        """
        Validate configuration has required fields.

        Args:
            config: Configuration to validate

        Raises:
            ValueError: If required fields are missing
        """
        if not config:
            raise ValueError("Configuration is empty")

        # Validate ZeroBus config
        if 'zerobus' not in config:
            raise ValueError("Missing 'zerobus' section in configuration")

        zerobus = config['zerobus']
        required_zerobus_fields = ['workspace_host', 'zerobus_endpoint', 'auth', 'target']
        for field in required_zerobus_fields:
            if field not in zerobus:
                raise ValueError(f"Missing required field 'zerobus.{field}'")

        # Validate auth
        auth = zerobus['auth']
        if 'client_id' not in auth or 'client_secret' not in auth:
            raise ValueError("Missing OAuth credentials in 'zerobus.auth'")

        # Validate target
        target = zerobus['target']
        required_target_fields = ['catalog', 'schema', 'table']
        for field in required_target_fields:
            if field not in target:
                raise ValueError(f"Missing required field 'zerobus.target.{field}'")

        # Validate sources
        if 'sources' in config:
            if not isinstance(config['sources'], list):
                raise ValueError("'sources' must be a list")

            for i, source in enumerate(config['sources']):
                if 'protocol' not in source:
                    raise ValueError(f"Source {i} missing 'protocol' field")
                if 'endpoint' not in source:
                    raise ValueError(f"Source {i} missing 'endpoint' field")

                protocol = source['protocol']
                if protocol not in ['opcua', 'mqtt', 'modbus']:
                    raise ValueError(f"Source {i} has invalid protocol '{protocol}'")

        logger.info("Configuration validation passed")
