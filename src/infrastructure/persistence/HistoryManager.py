import json
import os
from pathlib import Path
from datetime import datetime
import uuid

class HistoryManager:
    def __init__(self, cache_folder: str = "./.cache/"):
        self.cache_folder = Path(cache_folder)
        self.history_file = self.cache_folder / "history.json"
        
        # Ensure cache directory exists
        self.cache_folder.mkdir(parents=True, exist_ok=True)
        
        self._history = self._load_history()

    def _load_history(self) -> list:
        """Loads history from JSON file."""
        if not self.history_file.exists():
            return []
        
        try:
            with open(self.history_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading history: {e}")
            return []

    def add_entry(self, entry: dict):
        """Adds a new entry to the history."""
        # Add metadata
        entry["timestamp"] = datetime.now().isoformat()
        entry["job_id"] = str(uuid.uuid4())
        
        self._history.insert(0, entry) # Prepend to keep newest first
        self._save_history()

    def get_history(self) -> list:
        """Returns the full history list."""
        return self._history

    def _save_history(self):
        """Attributes persistent storage."""
        try:
            with open(self.history_file, "w") as f:
                json.dump(self._history, f, indent=2)
        except IOError as e:
            print(f"Error saving history: {e}")
