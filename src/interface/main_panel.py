"""
Main Panel module for the GEE Data Extractor.
Contains the primary extraction pipeline UI with 4 sections:
1. Data Source (WHAT) - Satellite and variable selection
2. Region of Interest (WHERE) - Point/Shapefile/GADM selection
3. Time Definition (WHEN) - Year and DOY selection
4. Execution (HOW) - Run extraction
"""
import streamlit as st
import ee
import json
import folium
from streamlit_folium import st_folium
from pathlib import Path
import tempfile
import os
from datetime import datetime

from src.infrastructure.configuration.SettingsService import SettingsService
from src.application.services.GeometryService import GeometryService
from src.infrastructure.persistence.HistoryManager import HistoryManager


def load_satellites():
    """Load satellite configurations from JSON."""
    # Try config folder first, then root
    config_path = Path("config/satellites.json")
    if not config_path.exists():
        config_path = Path("satellites.json")
    
    if config_path.exists():
        with open(config_path, 'r') as f:
            data = json.load(f)
            return data.get('satellites', [])
    return []


def update_default_filename():
    """Update the custom filename in session state based on current selections."""
    # Get current satellite ID
    # Note: satellite_selector key in session state holds the name
    sat_name = st.session_state.get('satellite_selector')
    satellites = load_satellites()
    selected_satellite = next((s for s in satellites if s['name'] == sat_name), None)
    sat_id = selected_satellite['id'] if selected_satellite else "GEE"
    
    # Get current years (prefer form values if in middle of submission, else session state)
    start = st.session_state.get('form_start_year') or st.session_state.get('start_year', 2020)
    end = st.session_state.get('form_end_year') or st.session_state.get('end_year', datetime.now().year)
    
    st.session_state.custom_filename = f"{sat_id}_{start}_{end}_timeseries"


def render(settings_service: SettingsService):
    """Renders the main panel with extraction pipeline."""
    st.title("🛰️ GEE Data Extractor")
    
    # Load satellites configuration
    satellites = load_satellites()
    
    # Check for loaded settings from history
    loaded_settings = st.session_state.get('loaded_settings', {})
    
    # Initialize session state for points if not exists
    if 'selected_points' not in st.session_state:
        st.session_state.selected_points = []
    
    # Section 1: Data Source (WHAT)
    render_data_source_section(satellites, loaded_settings)
    
    st.divider()
    
    # Section 2: Region of Interest (WHERE)
    render_roi_section(loaded_settings)
    
    st.divider()
    
    # Section 3: Time Definition (WHEN)
    render_time_section(loaded_settings)
    
    st.divider()
    
    # Section 4: Execution (HOW)
    render_execution_section(settings_service, satellites)


def render_data_source_section(satellites: list, loaded_settings: dict):
    """Section 1: Data Source - Satellite and variable selection."""
    st.header("1️⃣ Data Source")
    
    if not satellites:
        st.error("No satellite configurations found. Please check satellites.json")
        return
    
    # Build satellite options
    satellite_options = {sat['name']: sat for sat in satellites}
    satellite_names = list(satellite_options.keys())
    
    # Default selection from loaded settings or settings
    default_idx = 0
    if loaded_settings.get('satellite'):
        for i, name in enumerate(satellite_names):
            if satellite_options[name]['id'] == loaded_settings.get('satellite'):
                default_idx = i
                break
    
    # Satellite selector
    selected_sat_name = st.selectbox(
        "Select Satellite/Dataset",
        options=satellite_names,
        index=default_idx,
        key="satellite_selector",
        on_change=update_default_filename
    )
    
    selected_satellite = satellite_options[selected_sat_name]
    
    # Display satellite info in expander
    with st.expander("ℹ️ Dataset Information", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**ID:** `{selected_satellite['id']}`")
            st.markdown(f"**GEE Collection:** `{selected_satellite['ee_collection_name']}`")
            st.markdown(f"**Start Date:** {selected_satellite.get('startDate', 'N/A')}")
        with col2:
            st.markdown(f"**Pixel Size:** {selected_satellite.get('pixelSize', 'N/A')}m")
            if selected_satellite.get('website'):
                st.markdown(f"[📖 Documentation]({selected_satellite['website']})")
        st.markdown(f"**Description:** {selected_satellite.get('description', 'No description available')}")
    
    # Variable/Band selection
    bands = selected_satellite.get('bands', [])
    if bands:
        st.subheader("Select Variables/Bands")
        
        # Store band selections with reducers
        if 'band_selections' not in st.session_state:
            st.session_state.band_selections = {}
        
        band_names = [b['name'] for b in bands]
        
        # Default bands from loaded settings
        default_bands = loaded_settings.get('bands', [])
        default_selections = [b for b in band_names if b in default_bands] or band_names[:1]
        
        selected_bands = st.multiselect(
            "Select bands to extract",
            options=band_names,
            default=default_selections if any(b in band_names for b in default_selections) else [],
            key="band_multiselect"
        )
        
        # For each selected band, show reducer option
        if selected_bands:
            st.markdown("**Reducer per Variable:**")
            reducers = ['mean', 'sum', 'max', 'min', 'median', 'first']
            
            for band_name in selected_bands:
                col1, col2 = st.columns([2, 1])
                with col1:
                    # Find band info
                    band_info = next((b for b in bands if b['name'] == band_name), {})
                    units = band_info.get('units', '')
                    desc = band_info.get('description', '')
                    st.caption(f"**{band_name}** ({units}) - {desc[:50]}...")
                with col2:
                    reducer = st.selectbox(
                        f"Reducer",
                        options=reducers,
                        index=0,
                        key=f"reducer_{band_name}",
                        label_visibility="collapsed"
                    )
                    st.session_state.band_selections[band_name] = reducer
        
        st.session_state.selected_satellite = selected_satellite
        st.session_state.selected_bands = selected_bands
    else:
        st.warning("No bands available for this dataset")


def render_roi_section(loaded_settings: dict):
    """Section 2: Region of Interest - Geometry selection."""
    st.header("2️⃣ Region of Interest")
    
    # Input method selector
    roi_method = st.radio(
        "Select input method",
        options=["📍 Point Coordinates", "📁 Shapefile Upload", "🗺️ GADM Admin"],
        horizontal=True,
        key="roi_method"
    )
    
    geometry_service = GeometryService()
    
    if "📍 Point" in roi_method:
        render_point_input(loaded_settings)
    elif "📁 Shapefile" in roi_method:
        render_shapefile_input()
    elif "🗺️ GADM" in roi_method:
        render_gadm_input()
    
    # Display map for verification
    render_verification_map()


def render_point_input(loaded_settings: dict):
    """Point coordinate input with multiple points support."""
    st.subheader("Point Selection")
    
    # Manual entry
    st.markdown("**Add point manually or upload CSV:**")
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        lat = st.number_input("Latitude", value=0.0, min_value=-90.0, max_value=90.0, step=0.01, key="lat_input")
    with col2:
        lon = st.number_input("Longitude", value=0.0, min_value=-180.0, max_value=180.0, step=0.01, key="lon_input")
    with col3:
        st.write("")  # Spacer
        st.write("")
        if st.button("➕ Add", key="add_point_btn"):
            if lat != 0.0 or lon != 0.0:
                point = {'lat': lat, 'lon': lon}
                if point not in st.session_state.selected_points:
                    st.session_state.selected_points.append(point)
                    st.success(f"Added point ({lat}, {lon})")
                    st.rerun()

    # CSV Upload
    with st.expander("📂 Upload points from CSV"):
        csv_file = st.file_uploader("Upload CSV file", type=['csv'], key="point_csv_uploader", help="CSV must contain 'lat' and 'lon' columns (or 'latitude'/'longitude')")
        if csv_file:
            try:
                import pandas as pd
                df = pd.read_csv(csv_file)
                
                # Detect columns
                lat_cols = [c for c in df.columns if c.lower() in ['lat', 'latitude', 'y', 'lat_dec']]
                lon_cols = [c for c in df.columns if c.lower() in ['lon', 'longitude', 'x', 'lon_dec', 'lng']]
                
                if not lat_cols or not lon_cols:
                    st.error("❌ Could not find latitude/longitude columns. Please ensure they are named 'lat' and 'lon'.")
                else:
                    lat_col = lat_cols[0]
                    lon_col = lon_cols[0]
                    
                    new_points = []
                    for _, row in df.iterrows():
                        p = {'lat': round(float(row[lat_col]), 6), 'lon': round(float(row[lon_col]), 6)}
                        if p not in st.session_state.selected_points and p not in new_points:
                            new_points.append(p)
                    
                    if new_points:
                        st.session_state.selected_points.extend(new_points)
                        st.success(f"✅ Added {len(new_points)} points from CSV!")
                        st.rerun()
                    else:
                        st.info("No new unique points found in CSV.")
            except Exception as e:
                st.error(f"Error reading CSV: {e}")

    
    # Interactive map for clicking
    st.markdown("**Or click on map to add points:**")
    
    # Create folium map
    center = [0, 0]
    if st.session_state.selected_points:
        center = [st.session_state.selected_points[-1]['lat'], 
                  st.session_state.selected_points[-1]['lon']]
    
    m = folium.Map(location=center, zoom_start=3)
    
    # Add existing points to map
    for i, pt in enumerate(st.session_state.selected_points):
        folium.Marker(
            [pt['lat'], pt['lon']],
            popup=f"Point {i+1}: ({pt['lat']:.4f}, {pt['lon']:.4f})",
            icon=folium.Icon(color='red', icon='info-sign')
        ).add_to(m)
    
    # Display map with click capture
    map_data = st_folium(m, height=300, width=None, key="point_map")
    
    # Handle map click
    if map_data and map_data.get('last_clicked'):
        clicked = map_data['last_clicked']
        new_point = {'lat': round(clicked['lat'], 6), 'lon': round(clicked['lng'], 6)}
        if new_point not in st.session_state.selected_points:
            st.session_state.selected_points.append(new_point)
            st.rerun()
    
    # Display selected points with delete option
    if st.session_state.selected_points:
        st.markdown("**Selected Points:**")
        for i, pt in enumerate(st.session_state.selected_points):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.text(f"Point {i+1}: ({pt['lat']}, {pt['lon']})")
            with col2:
                if st.button("🗑️", key=f"del_pt_{i}"):
                    st.session_state.selected_points.pop(i)
                    st.rerun()
        
        if st.button("Clear All Points"):
            st.session_state.selected_points = []
            st.rerun()


def render_shapefile_input():
    """Shapefile/GeoJSON upload."""
    st.subheader("Shapefile Upload")
    
    uploaded_file = st.file_uploader(
        "Upload shapefile (.zip), GeoJSON (.geojson), or KML (.kml)",
        type=['zip', 'geojson', 'json', 'kml'],
        key="shapefile_uploader"
    )
    
    if uploaded_file:
        # Save to temp file
        suffix = Path(uploaded_file.name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getvalue())
            st.session_state.uploaded_shapefile = tmp.name
        st.success(f"Uploaded: {uploaded_file.name}")


def render_gadm_input():
    """GADM administrative boundary selection with map visualization."""
    st.subheader("GADM Administrative Boundaries")
    
    # Import pygadm
    try:
        import pygadm
    except ImportError:
        st.error("pygadm is not installed. Run: pip install pygadm")
        return
    
    # Country selection
    country = st.text_input(
        "Country Name", 
        placeholder="e.g., Italy, South Africa, Zambia", 
        key="gadm_country",
        help="Enter the country name to load its boundaries"
    )
    
    # Admin level for content
    admin_level = st.selectbox(
        "Administrative Level",
        options=[0, 1, 2],
        format_func=lambda x: f"Level {x} ({'Country' if x == 0 else 'State/Province' if x == 1 else 'District'})",
        key="gadm_level"
    )
    
    # Load button
    if country:
        col1, col2 = st.columns([1, 1])
        with col1:
            load_clicked = st.button("🔍 Load Boundary", use_container_width=True)
        
        if load_clicked or st.session_state.get('gadm_gdf') is not None:
            with st.spinner(f"Loading {country} boundaries..."):
                try:
                    # Load GADM data
                    if load_clicked or st.session_state.get('gadm_country_loaded') != country:
                        if admin_level > 0:
                            # Get subdivisions
                            gdf = pygadm.Items(name=country, content_level=admin_level)
                        else:
                            # Just the country
                            gdf = pygadm.Items(name=country)
                        
                        # Store in session state
                        st.session_state.gadm_gdf = gdf
                        st.session_state.gadm_country_loaded = country
                        st.session_state.gadm_level_loaded = admin_level
                    else:
                        gdf = st.session_state.gadm_gdf
                    
                    # Show info
                    st.success(f"✅ Loaded {len(gdf)} region(s) for {country}")
                    
                    # If we have subdivisions, let user select specific ones
                    if admin_level > 0 and len(gdf) > 1:
                        # Get name column (usually NAME_1, NAME_2, etc.)
                        name_col = f"NAME_{admin_level}"
                        if name_col in gdf.columns:
                            region_names = gdf[name_col].tolist()
                            
                            selected_regions = st.multiselect(
                                f"Select specific regions (optional)",
                                options=region_names,
                                default=[],
                                key="gadm_regions",
                                help="Leave empty to use entire country"
                            )
                            
                            if selected_regions:
                                gdf = gdf[gdf[name_col].isin(selected_regions)]
                                st.info(f"Selected {len(gdf)} region(s)")
                    
                    # Display map
                    st.markdown("**Boundary Preview:**")
                    
                    try:
                        # Get centroid for map center
                        centroid = gdf.geometry.unary_union.centroid
                        center = [centroid.y, centroid.x]
                        
                        # Create folium map
                        m = folium.Map(location=center, zoom_start=5)
                        
                        # WORKAROUND for pygadm pandas compatibility bug:
                        # Use gdf.geometry.__geo_interface__ instead of gdf.__geo_interface__
                        # This avoids triggering the buggy Items.__init__ on subsetting
                        folium.GeoJson(
                            gdf.geometry.__geo_interface__,
                            style_function=lambda x: {
                                'fillColor': '#3388ff',
                                'color': '#3388ff',
                                'weight': 2,
                                'fillOpacity': 0.3
                            }
                        ).add_to(m)
                        
                        # Fit bounds
                        bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
                        m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
                        
                        # Display map
                        st_folium(m, height=350, width=None, key="gadm_map")
                        
                    except Exception as map_error:
                        st.warning(f"Map preview unavailable: {str(map_error)[:100]}")
                    
                    # Store selection in session state
                    st.session_state.gadm_selection = {
                        'name': country,
                        'admin_level': admin_level,
                        'gdf': gdf  # Store the GeoDataFrame for extraction
                    }
                    
                except ValueError as e:
                    st.error(f"❌ Could not find '{country}'. Check spelling.")
                    st.caption(f"Error: {str(e)[:200]}")
                except Exception as e:
                    st.error(f"❌ Error loading boundary: {str(e)}")
    else:
        st.caption("Enter a country name above to load its boundaries")


def render_verification_map():
    """Passive verification map showing selected geometries."""
    # This is shown in the point input for now
    pass


def render_time_section(loaded_settings: dict):
    """Section 3: Time Definition with form to reduce reruns."""
    st.header("3️⃣ Time Definition")
    
    # Check for invalid date ranges in session state
    current_start = st.session_state.get('start_year', 2020)
    current_end = st.session_state.get('end_year', datetime.now().year)
    
    if current_end < current_start:
        st.error(f"⚠️ **Invalid Date Range**: End Year ({current_end}) is before Start Year ({current_start}).")

    with st.form("time_definition_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            start_year = st.number_input(
                "Start Year",
                min_value=1980,
                max_value=datetime.now().year,
                value=loaded_settings.get('dates', {}).get('start_year', 2020),
                key="form_start_year"
            )
        
        with col2:
            end_year = st.number_input(
                "End Year",
                min_value=1980,
                max_value=datetime.now().year,
                value=loaded_settings.get('dates', {}).get('end_year', datetime.now().year),
                key="form_end_year"
            )
        
        # Seasonality filter
        use_season = st.checkbox("🌾 Filter by Season (Day of Year)", 
                                 value=loaded_settings.get('dates', {}).get('use_season', False),
                                 key="form_use_season")
        
        start_doy = 1
        end_doy = 365
        
        if use_season:
            col1, col2 = st.columns(2)
            with col1:
                start_doy = st.slider(
                    "Start DOY",
                    min_value=1,
                    max_value=365,
                    value=loaded_settings.get('dates', {}).get('start_doy', 1),
                    key="form_start_doy"
                )
            with col2:
                end_doy = st.slider(
                    "End DOY",
                    min_value=1,
                    max_value=365,
                    value=loaded_settings.get('dates', {}).get('end_doy', 365),
                    key="form_end_doy"
                )
            
            if start_doy > end_doy:
                st.info("💡 **Cross-Year Season**: This period will handle date ranges spanning across consecutive years.")

        # Form submit button
        submitted = st.form_submit_button("✅ Apply Date Settings", use_container_width=True)
        
        if submitted:
            # Update session state with form values
            st.session_state.start_year = start_year
            st.session_state.end_year = end_year
            st.session_state.use_season = use_season
            st.session_state.start_doy = start_doy
            st.session_state.end_doy = end_doy
            
            # Also update date_config for the extraction service
            st.session_state.date_config = {
                'start_year': start_year,
                'end_year': end_year,
                'start_doy': start_doy,
                'end_doy': end_doy,
                'use_season': use_season
            }
            
            # Update the custom filename based on new dates
            update_default_filename()
            
            st.success("Dates and Filename updated!")
            st.rerun()

    # If no date_config yet, initialize it from session state or defaults
    if 'date_config' not in st.session_state:
        st.session_state.date_config = {
            'start_year': st.session_state.get('start_year', 2020),
            'end_year': st.session_state.get('end_year', datetime.now().year),
            'start_doy': st.session_state.get('start_doy', 1),
            'end_doy': st.session_state.get('end_doy', 365),
            'use_season': st.session_state.get('use_season', False)
        }


def render_execution_section(settings_service: SettingsService, satellites: list):
    """Section 4: Execution - Run extraction."""
    st.header("4️⃣ Execution")
    
    # Export method
    export_method = st.radio(
        "Export Method",
        options=["☁️ Save to Google Drive (Batch)", "💾 Download Locally (Interactive)"],
        horizontal=True,
        key="export_method"
    )
    
    # Drive folder configuration
    if "Drive" in export_method:
        drive_folder = settings_service.get_setting("gee", "drive_folder", "GEE_Exports")
        drive_folder = st.text_input("Drive Folder Name", value=drive_folder, key="drive_folder")
    
    # Filename / Task Name
    selected_satellite = st.session_state.get('selected_satellite')
    date_config = st.session_state.get('date_config', {})
    
    # Generate default suggestion
    sat_id = selected_satellite['id'] if selected_satellite else "GEE"
    year_str = f"{date_config.get('start_year', '')}_{date_config.get('end_year', '')}" if date_config else "extraction"
    default_filename = f"{sat_id}_{year_str}_timeseries"
    
    custom_filename = st.text_input(
        "File Name / Task Name", 
        value=default_filename, 
        help="The name used for the GEE task and the output file",
        key="custom_filename"
    )
    
    st.divider()
    
    # Run button
    if st.button("🚀 RUN EXTRACTION", type="primary", use_container_width=True):
        run_extraction(settings_service, export_method)


def run_extraction(settings_service: SettingsService, export_method: str):
    """Execute the GEE extraction - outputs CSV with time-series data."""
    with st.spinner("Submitting task to Google Earth Engine..."):
        try:
            # Validate inputs
            selected_satellite = st.session_state.get('selected_satellite')
            selected_bands = st.session_state.get('selected_bands', [])
            selected_points = st.session_state.get('selected_points', [])
            date_config = st.session_state.get('date_config', {})
            band_selections = st.session_state.get('band_selections', {})
            
            if not selected_satellite:
                st.error("Please select a satellite/dataset")
                return
            
            if not selected_bands:
                st.error("Please select at least one band")
                return
            
            if not selected_points and not st.session_state.get('uploaded_shapefile') and not st.session_state.get('gadm_selection'):
                st.error("Please define a region of interest (point, shapefile, or GADM)")
                return
            
            # Initialize GEE if needed
            project_id = settings_service.get_setting("gee", "project_id")
            try:
                ee.Initialize(project=project_id)
            except:
                st.error("Failed to initialize GEE. Please check authentication.")
                return
            
            # Build geometry and feature collection
            geometry, features = build_geometry_and_features()
            if geometry is None:
                st.error("Failed to build geometry from inputs")
                return
            
            # Build image collection
            collection_id = selected_satellite['ee_collection_name']
            collection = ee.ImageCollection(collection_id)
            
            # Apply date filters
            start_date = f"{date_config['start_year']}-01-01"
            end_date = f"{date_config['end_year']}-12-31"
            collection = collection.filterDate(start_date, end_date)
            
            # Apply DOY filter if not full year
            if date_config.get('start_doy', 1) != 1 or date_config.get('end_doy', 365) != 365:
                start_doy = date_config['start_doy']
                end_doy = date_config['end_doy']
                
                if start_doy <= end_doy:
                    # Normal season
                    collection = collection.filter(ee.Filter.dayOfYear(start_doy, end_doy))
                else:
                    # Cross-year season
                    collection = collection.filter(
                        ee.Filter.Or(
                            ee.Filter.dayOfYear(start_doy, 365),
                            ee.Filter.dayOfYear(1, end_doy)
                        )
                    )
            
            # Filter by bounds
            collection = collection.filterBounds(geometry)
            
            # Select only needed bands
            collection = collection.select(selected_bands)
            
            # Build the reducer based on band selections
            # We'll use the same reducer for all bands (most common case)
            # or combine multiple reducers
            reducer_name = list(band_selections.values())[0] if band_selections else 'mean'
            
            if reducer_name == 'mean':
                reducer = ee.Reducer.mean()
            elif reducer_name == 'sum':
                reducer = ee.Reducer.sum()
            elif reducer_name == 'max':
                reducer = ee.Reducer.max()
            elif reducer_name == 'min':
                reducer = ee.Reducer.min()
            elif reducer_name == 'median':
                reducer = ee.Reducer.median()
            elif reducer_name == 'first':
                reducer = ee.Reducer.first()
            else:
                reducer = ee.Reducer.mean()
            
            # Function to extract data for each image
            def extract_values(image):
                """Extract values at each point/region for an image."""
                # Add date properties
                date = ee.Date(image.get('system:time_start'))
                
                # Reduce regions - extract values at each feature
                reduced = image.reduceRegions(
                    collection=features,
                    reducer=reducer,
                    scale=selected_satellite.get('pixelSize', 1000)
                )
                
                # Add date info to each feature
                def add_date(feature):
                    return feature.set({
                        'date': date.format('YYYY-MM-dd'),
                        'year': date.get('year'),
                        'month': date.get('month'),
                        'day': date.get('day'),
                        'doy': date.getRelative('day', 'year').add(1),
                        'system_time': image.get('system:time_start')
                    })
                
                return reduced.map(add_date)
            
            # Map over collection to extract values
            extracted = collection.map(extract_values).flatten()
            
            # Export task name (use custom filename if provided)
            task_name = st.session_state.get('custom_filename', f"{selected_satellite['id']}_{date_config['start_year']}_{date_config['end_year']}_timeseries")
            
            if "Drive" in export_method:
                drive_folder = st.session_state.get('drive_folder', 'GEE_Exports')
                
                # Export as CSV to Drive
                task = ee.batch.Export.table.toDrive(
                    collection=extracted,
                    description=task_name,
                    folder=drive_folder,
                    fileNamePrefix=task_name,
                    fileFormat='CSV'
                )
                task.start()
                
                # Get task ID
                task_id = task.status()['id']
                
                st.success(f"✅ Task submitted successfully!")
                st.info(f"**Task ID:** `{task_id}`")
                st.info(f"**Output:** CSV file in Google Drive folder `{drive_folder}`")
                st.markdown(f"📊 [View in GEE Console](https://code.earthengine.google.com/tasks)")
                
                # Save to history
                history_manager = HistoryManager()
                history_manager.add_entry({
                    'satellite': selected_satellite['id'],
                    'bands': selected_bands,
                    'reducers': band_selections,
                    'geometry_source': 'Points' if selected_points else 'Shapefile/GADM',
                    'num_points': len(selected_points) if selected_points else 0,
                    'dates': date_config,
                    'export_method': 'Drive',
                    'output_format': 'CSV',
                    'task_id': task_id
                })
                
            else:
                # Local download - get as CSV directly
                # Note: This may fail for very large datasets
                st.info("Fetching data... This may take a moment for large datasets.")
                
                try:
                    # Get the data directly (limited to ~5000 features)
                    data = extracted.getInfo()
                    
                    if data and 'features' in data:
                        # Convert to pandas dataframe
                        import pandas as pd
                        
                        rows = []
                        for feature in data['features']:
                            props = feature.get('properties', {})
                            rows.append(props)
                        
                        df = pd.DataFrame(rows)
                        
                        # Provide download button
                        csv_data = df.to_csv(index=False)
                        st.success("✅ Data extracted successfully!")
                        st.download_button(
                            label="📥 Download CSV",
                            data=csv_data,
                            file_name=f"{task_name}.csv",
                            mime="text/csv"
                        )
                        
                        # Show preview
                        st.subheader("Data Preview")
                        st.dataframe(df.head(20))
                    else:
                        st.warning("No data returned. Try adjusting filters or using Drive export for large datasets.")
                        
                except Exception as fetch_error:
                    st.error(f"Local fetch failed (dataset may be too large): {fetch_error}")
                    st.info("💡 Tip: Use 'Save to Google Drive' for larger datasets")
        
        except Exception as e:
            st.error(f"❌ Extraction failed: {str(e)}")
            import traceback
            st.code(traceback.format_exc())


def build_geometry_and_features():
    """Build ee.Geometry and ee.FeatureCollection from session state inputs."""
    geometry_service = GeometryService()
    
    # Check for points
    points = st.session_state.get('selected_points', [])
    if points:
        # Create features with point IDs
        features = []
        for i, p in enumerate(points):
            point = ee.Geometry.Point([p['lon'], p['lat']])
            feature = ee.Feature(point, {
                'point_id': i + 1,
                'latitude': p['lat'],
                'longitude': p['lon']
            })
            features.append(feature)
        
        feature_collection = ee.FeatureCollection(features)
        
        if len(points) == 1:
            geometry = ee.Geometry.Point([points[0]['lon'], points[0]['lat']])
        else:
            coords = [[p['lon'], p['lat']] for p in points]
            geometry = ee.Geometry.MultiPoint(coords)
        
        return geometry, feature_collection
    
    # Check for shapefile
    shapefile_path = st.session_state.get('uploaded_shapefile')
    if shapefile_path:
        geometry = geometry_service.parse_geometry(shapefile_path, 'shapefile')
        # Create a FeatureCollection from the geometry
        feature_collection = ee.FeatureCollection([ee.Feature(geometry, {'source': 'shapefile'})])
        return geometry, feature_collection
    
    # Check for GADM
    gadm_selection = st.session_state.get('gadm_selection')
    if gadm_selection and 'gdf' in gadm_selection:
        # Use the cached GeoDataFrame
        gdf = gadm_selection['gdf']
        
        # WORKAROUND for pygadm pandas compatibility bug:
        # Cannot use gdf.__geo_interface__ or subset the gdf
        # Instead, access geometry series directly and build EE features manually
        
        # Simplify geometries to avoid GEE payload limits
        simplified_geoms = gdf.geometry.simplify(tolerance=0.01)
        
        # Build EE features from each geometry
        ee_features = []
        for i, geom in enumerate(simplified_geoms):
            # Convert shapely geometry to GeoJSON dict
            geom_dict = geom.__geo_interface__
            
            # Create EE geometry from GeoJSON
            ee_geom = ee.Geometry(geom_dict)
            
            # Create feature with basic properties
            ee_feature = ee.Feature(ee_geom, {
                'source': 'gadm',
                'feature_id': i + 1,
                'country': gadm_selection.get('name', ''),
                'admin_level': gadm_selection.get('admin_level', 0)
            })
            ee_features.append(ee_feature)
        
        # Create FeatureCollection
        feature_collection = ee.FeatureCollection(ee_features)
        
        # Get geometry as union of all features
        geometry = feature_collection.geometry()
        
        return geometry, feature_collection
    elif gadm_selection:
        # Fallback to GeometryService if no gdf in selection
        geometry = geometry_service.parse_geometry(gadm_selection, 'gadm')
        feature_collection = ee.FeatureCollection([ee.Feature(geometry, {
            'source': 'gadm',
            'country': gadm_selection.get('name', ''),
            'admin_level': gadm_selection.get('admin_level', 0)
        })])
        return geometry, feature_collection
    
    return None, None

