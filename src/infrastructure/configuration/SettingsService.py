import toml
import os
from pathlib import Path

class SettingsService:
    def __init__(self, config_path: str = "config/settings.toml"):
        self.config_path = Path(config_path)
        self._settings = self._load_settings()

    def _load_settings(self) -> dict:
        """Loads settings from the TOML file. Creates default if not exists."""
        if not self.config_path.exists():
            import shutil
            example_path = self.config_path.with_name('settings.example.toml')
            if example_path.exists():
                shutil.copy(example_path, self.config_path)
            else:
                return {}
        
        try:
            return toml.load(self.config_path)
        except Exception as e:
            print(f"Error loading settings: {e}")
            return {}

    def get_setting(self, section: str, key: str, default=None):
        """Retrieves a specific setting value."""
        return self._settings.get(section, {}).get(key, default)

    def get_all_settings(self) -> dict:
        """Returns the complete settings dictionary."""
        return self._settings

    def update_setting(self, section: str, key: str, value):
        """Updates a setting and writes to file."""
        if section not in self._settings:
            self._settings[section] = {}
        
        self._settings[section][key] = value
        self._save_settings()

    def _save_settings(self):
        """Writes the current settings back to the TOML file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            toml.dump(self._settings, f)
