"""
Centralized configuration management system
"""
import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class ConfigValidationResult:
    """Configuration validation result"""
    is_valid: bool
    errors: list
    warnings: list

class ConfigManager:
    """Centralized configuration management"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.configs = {}
        self.environment = os.getenv("HOT_DURHAM_ENV", "development")
        
    def load_config(self, config_name: str, config_type: str = "json") -> Dict[str, Any]:
        """Load configuration file"""
        config_file = self.config_dir / f"{config_name}.{config_type}"
        
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        if config_type == "json":
            with open(config_file, 'r') as f:
                config = json.load(f)
        elif config_type == "yaml" or config_type == "yml":
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
        else:
            raise ValueError(f"Unsupported config type: {config_type}")
        
        # Apply environment-specific overrides
        env_config = self._load_environment_config(config_name)
        if env_config:
            config.update(env_config)
        
        self.configs[config_name] = config
        return config
    
    def _load_environment_config(self, config_name: str) -> Optional[Dict[str, Any]]:
        """Load environment-specific configuration overrides from JSON or YAML file"""
        env_dir = self.config_dir / "environments"
        env_file_json = env_dir / f"{self.environment}.json"
        env_file_yaml = env_dir / f"{self.environment}.yaml"
        env_file_yml = env_dir / f"{self.environment}.yml"

        if env_file_json.exists():
            with open(env_file_json, 'r') as f:
                return json.load(f)
        elif env_file_yaml.exists():
            with open(env_file_yaml, 'r') as f:
                return yaml.safe_load(f)
        elif env_file_yml.exists():
            with open(env_file_yml, 'r') as f:
                return yaml.safe_load(f)
        else:
            return None
    
    def get_config(self, config_name: str, key: str = None, default: Any = None) -> Any:
        """Get configuration value"""
        if config_name not in self.configs:
            try:
                self.load_config(config_name)
            except FileNotFoundError:
                if default is not None:
                    return default
                raise
        
        config = self.configs[config_name]
        
        if key is None:
            return config
        
        # Support nested keys with dot notation
        keys = key.split('.')
        value = config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def validate_config(self, config_name: str) -> ConfigValidationResult:
        """Validate configuration"""
        errors = []
        warnings = []
        
        try:
            config = self.get_config(config_name)
        except Exception as e:
            errors.append(f"Failed to load config: {e}")
            return ConfigValidationResult(False, errors, warnings)
        
        # Common validations
        if config_name == "api_credentials":
            required_keys = ["tsi_credentials", "wu_api_key", "google_credentials"]
            for key in required_keys:
                if key not in config:
                    errors.append(f"Missing required key: {key}")
        
        elif config_name == "test_sensors":
            if "TEST_SENSOR_IDS" not in config:
                errors.append("Missing TEST_SENSOR_IDS")
            elif not isinstance(config["TEST_SENSOR_IDS"], list):
                errors.append("TEST_SENSOR_IDS must be a list")
        
        elif config_name == "database":
            if "db_path" not in config:
                warnings.append("No db_path specified, using default")
        
        return ConfigValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def save_config(self, config_name: str, config: Dict[str, Any], 
                   config_type: str = "json"):
        """Save configuration to file"""
        config_file = self.config_dir / f"{config_name}.{config_type}"
        
        if config_type == "json":
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
        elif config_type == "yaml" or config_type == "yml":
            with open(config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
        else:
            raise ValueError(f"Unsupported config type: {config_type}")
        
        self.configs[config_name] = config
    
    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get all loaded configurations"""
        return self.configs.copy()
    
    def reload_config(self, config_name: str):
        """Reload configuration from file"""
        if config_name in self.configs:
            del self.configs[config_name]
        return self.load_config(config_name)
