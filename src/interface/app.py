import streamlit as st
import sys
import os
from pathlib import Path

# Add project root to path
root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))
from src.infrastructure.configuration.SettingsService import SettingsService
from src.infrastructure.update.UpdateChecker import UpdateChecker
from src.interface import sidebar, main_panel
from src.interface.map_utils import inject_drag_handle

# Page Configuration
st.set_page_config(
    page_title="GEE Data Extractor",
    page_icon="assets/favicon.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

def main():
    """Main application loop."""
    
    # Initialize Services
    settings_service = SettingsService()

    # Check for updates once per session (not on every Streamlit rerun)
    if 'update_info' not in st.session_state:
        checker = UpdateChecker()
        st.session_state['update_info'] = checker.check_for_updates()
        st.session_state['update_checker'] = checker

    # Render Interface
    sidebar.render(settings_service)
    main_panel.render(settings_service)

    # Inject drag-to-resize handles for all map iframes
    inject_drag_handle()

if __name__ == "__main__":
    main()
