"""
Sidebar module for the GEE Data Extractor.
Contains: Authentication status, Settings popup, Task monitor, History loader.
"""
import streamlit as st
import ee
from src.domain.extractors.BaseExtractor import BaseExtractor
from src.infrastructure.persistence.HistoryManager import HistoryManager


def render(settings_service):
    """Renders the sidebar components."""
    with st.sidebar:
        render_update_banner()
        st.header("🎮 Control Center")
        
        # 1. Authentication Status
        render_auth_status(settings_service)
        
        st.divider()
        
        # 2. Settings Button (opens popup)
        render_settings_popup(settings_service)
        
        st.divider()
        
        # 3. Task Monitor
        render_task_monitor()
        
        # 4. History
        render_history_loader()


def render_auth_status(settings_service):
    """Checks and displays GEE Auth status with proper initialization."""
    project_id = settings_service.get_setting("gee", "project_id", "my-project")
    
    # Use session state to track initialization status
    if 'gee_initialized' not in st.session_state:
        st.session_state.gee_initialized = False
        st.session_state.gee_error = None
    
    # Try to initialize if not already done
    if not st.session_state.gee_initialized:
        try:
            ee.Initialize(project=project_id)
            st.session_state.gee_initialized = True
            st.session_state.gee_error = None
        except ee.EEException as e:
            # Try to authenticate first
            try:
                ee.Authenticate()
                ee.Initialize(project=project_id)
                st.session_state.gee_initialized = True
                st.session_state.gee_error = None
            except Exception as auth_err:
                st.session_state.gee_initialized = False
                st.session_state.gee_error = str(auth_err)
        except Exception as e:
            st.session_state.gee_initialized = False
            st.session_state.gee_error = str(e)
    
    # Display status
    if st.session_state.gee_initialized:
        st.success(f"🟢 GEE Connected: `{project_id}`")
    else:
        st.error("🔴 GEE Disconnected")
        if st.session_state.gee_error:
            st.caption(f"Error: {st.session_state.gee_error[:50]}...")
        
        if st.button("🔄 Reconnect", use_container_width=True):
            try:
                ee.Authenticate()
                ee.Initialize(project=project_id)
                st.session_state.gee_initialized = True
                st.session_state.gee_error = None
                st.rerun()
            except Exception as auth_err:
                st.session_state.gee_error = str(auth_err)
                st.error(f"Auth failed: {auth_err}")


@st.dialog("⚙️ Settings")
def settings_dialog(settings_service):
    """Settings popup modal dialog."""
    st.markdown("### Google Earth Engine")
    
    # GEE Project ID
    current_project = settings_service.get_setting("gee", "project_id", "")
    new_project = st.text_input(
        "GEE Project ID",
        value=current_project,
        help="Your Google Cloud Project ID for GEE"
    )
    
    # Drive folder
    current_drive_folder = settings_service.get_setting("gee", "drive_folder", "GEE_Exports")
    new_drive_folder = st.text_input(
        "Google Drive Folder",
        value=current_drive_folder,
        help="Folder name in your Google Drive for exports"
    )
    
    st.markdown("### Local Paths")
    
    # Local download folder
    current_local_path = settings_service.get_setting("paths", "download_folder_local", "")
    new_local_path = st.text_input(
        "Local Download Folder",
        value=current_local_path,
        help="Where to save files for local downloads"
    )
    
    # Cache folder
    current_cache = settings_service.get_setting("paths", "cache_folder", "./.cache/")
    new_cache = st.text_input(
        "Cache Folder",
        value=current_cache,
        help="Where to store job history"
    )
    
    st.markdown("### Defaults")
    
    # Default reducer
    reducers = ['mean', 'sum', 'max', 'min', 'median']
    current_reducer = settings_service.get_setting("defaults", "default_reducer", "mean")
    new_reducer = st.selectbox(
        "Default Reducer",
        options=reducers,
        index=reducers.index(current_reducer) if current_reducer in reducers else 0
    )
    
    # Save button
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save", use_container_width=True, type="primary"):
            # Update all settings
            settings_service.update_setting("gee", "project_id", new_project)
            settings_service.update_setting("gee", "drive_folder", new_drive_folder)
            settings_service.update_setting("paths", "download_folder_local", new_local_path)
            settings_service.update_setting("paths", "cache_folder", new_cache)
            settings_service.update_setting("defaults", "default_reducer", new_reducer)
            
            # Force re-initialization if project changed
            if new_project != current_project:
                st.session_state.gee_initialized = False
            
            st.success("✅ Settings saved!")
            st.rerun()
    
    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            st.rerun()


def render_settings_popup(settings_service):
    """Settings button that opens the dialog."""
    if st.button("⚙️ Settings", use_container_width=True):
        settings_dialog(settings_service)


def render_task_monitor():
    """Displays recent GEE tasks."""
    st.subheader("📋 Tasks")
    
    if st.button("🔄 Refresh Tasks", use_container_width=True):
        try:
            tasks = BaseExtractor.monitor_tasks(limit=5)
            if tasks:
                for task in tasks:
                    state = task.get('state', 'UNKNOWN')
                    if state == 'COMPLETED':
                        icon = "🟢"
                    elif state == 'RUNNING':
                        icon = "🔵"
                    elif state == 'FAILED':
                        icon = "🔴"
                    elif state == 'READY':
                        icon = "⚪"
                    else:
                        icon = "⚪"
                    
                    desc = task.get('description', 'No Description')[:25]
                    st.text(f"{icon} {desc} [{state}]")
            else:
                st.info("No recent tasks found.")
        except Exception as e:
            st.warning(f"Could not fetch tasks: {str(e)[:50]}")


def render_history_loader():
    """Loads previous run configurations."""
    st.subheader("📜 History")
    history_manager = HistoryManager()
    history = history_manager.get_history()
    
    if not history:
        st.caption("No job history available.")
        return
    
    options = {f"{h['timestamp'][:16]} - {h['satellite'][:15]}": h for h in history}
    selected_option = st.selectbox(
        "Load Previous Run",
        options=list(options.keys()),
        label_visibility="collapsed"
    )
    
    if st.button("📥 Load Settings", use_container_width=True):
        selected_run = options[selected_option]
        st.session_state['loaded_settings'] = selected_run
        st.success("Settings loaded!")
        st.rerun()


def render_update_banner():
    """Renders an update notification banner if a newer version is available on origin/main."""
    update_info = st.session_state.get('update_info')
    if update_info is None or not update_info.update_available:
        return

    st.info(
        f"**Update available:** v{update_info.remote_version}  \n"
        f"You are on v{update_info.current_version}",
        icon="🆕",
    )
    if update_info.has_local_changes:
        st.warning(
            "Uncommitted local changes detected. Run `git stash` in your terminal before updating.",
            icon="⚠️",
        )
    if st.button("Update & Restart", type="primary", use_container_width=True, key="btn_update"):
        _do_update()
    st.divider()


def _do_update():
    """Pulls latest changes, reinstalls requirements, and restarts the app."""
    import time
    checker = st.session_state.get('update_checker')
    if not checker:
        st.error("Update service unavailable. Please restart the app manually.")
        return
    with st.spinner("Pulling latest changes..."):
        success, message = checker.perform_update()
    if success:
        st.success(message)
        time.sleep(1.5)
        checker.restart_app()
    else:
        st.error(message)
        st.session_state.pop('update_info', None)
