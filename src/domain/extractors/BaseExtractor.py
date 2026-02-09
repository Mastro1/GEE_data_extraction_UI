from abc import ABC, abstractmethod
import ee
from src.infrastructure.configuration.SettingsService import SettingsService
from src.application.services.GeometryService import GeometryService

class BaseExtractor(ABC):
    def __init__(self, project_id: str):
        self.project_id = project_id
        self._authenticate()
        self.settings_service = SettingsService()
        self.geometry_service = GeometryService()

    def _authenticate(self):
        """Authenticates with Earth Engine."""
        try:
            ee.Initialize(project=self.project_id)
        except Exception:
            # Trigger auth flow if initialization fails
            ee.Authenticate()
            ee.Initialize(project=self.project_id)

    def load_settings(self):
        """Refreshes settings from service."""
        # This implementation might rely on the service's state
        pass

    def check_seasonality(self, start_doy: int, end_doy: int) -> bool:
        """
        Checks if the season crosses the year boundary.
        Returns True if season crosses year (e.g. Nov to Feb), False otherwise.
        """
        return start_doy > end_doy

    @abstractmethod
    def extract(self, parameters: dict):
        """
        Main extraction method to be implemented by subclasses.
        """
        pass

    def parse_geometry(self, data, geometry_type: str) -> ee.Geometry:
        """Delegates to GeometryService."""
        return self.geometry_service.parse_geometry(data, geometry_type)

    @staticmethod
    def monitor_tasks(limit=20):
        """Returns list of recent GEE tasks."""
        try:
            return ee.data.getTaskList()[:limit]
        except Exception as e:
            print(f"Error fetching task list: {e}")
            return []
