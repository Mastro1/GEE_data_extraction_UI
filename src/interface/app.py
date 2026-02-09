import streamlit as st
import sys
import os
from pathlib import Path

# Add project root to path
root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))
from src.infrastructure.configuration.SettingsService import SettingsService
from src.interface import sidebar, main_panel

# Page Configuration
st.set_page_config(
    page_title="GEE Data Extractor",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

def main():
    """Main application loop."""
    
    # Initialize Services
    settings_service = SettingsService()
    
    # Load CSS (Optional - for custom styling if needed later)
    # with open("assets/style.css") as f:
    #     st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    # Render Interface
    sidebar.render(settings_service)
    main_panel.render(settings_service)

if __name__ == "__main__":
    main()
