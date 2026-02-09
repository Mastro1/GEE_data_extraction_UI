# Project Design Document: GEE Data Extraction Suite (v2.0)

## 1. Project Overview

**Objective:** To create a local, Python-based desktop application for streamlined extraction of historical satellite data from Google Earth Engine (GEE).
**Platform:** A browser-based User Interface (Streamlit) backed by a custom Python library.
**Key Philosophy:** "Passive Validation." The system visualizes inputs (maps, geometries) to confirm correctness but relies on explicit file/text inputs rather than interactive drawing tools.
**State Management:** Comprehensive persistence of user settings and job history to facilitate reproducibility.

---

## 2. System Architecture & Data Persistence

The system is designed around a **Local State Architecture**. It relies on the local file system to maintain configuration and history, ensuring the user can restart the app and have it's previous work immediately available.

### **A. Global Configuration (`config/settings.toml`)**

This file acts as the persistent brain of the application. It must be human-readable and manually editable if necessary.

**Exact Schema:**

* `[gee]`
* `project_id` (string): The Google Cloud Project ID used for authentication and project name (e.g., `"my-earth-project-2024"`).

* `[paths]`
* `download_folder_local` (string): Absolute path where direct downloads (interactive mode) will be saved (e.g., `C:/Users/Name/Downloads/GEE_Local`).
* `cache_folder` (string): Path to store the job history JSONs (default: `./.cache/`).


* `[defaults]`
* `default_satellite` (string): The satellite selected on startup (e.g., `"NDVI"`).
* `default_method` (string): The default export method (e.g., `"Drive"`).



### **B. Job History & Caching (`.cache/history.json`)**

Every time the user clicks "Run Extraction", the exact parameters used are saved. This allows the "Reload Settings" feature.

**Record Schema (for each entry):**

* `timestamp` (ISO 8601 string): When the job was submitted.
* `job_id` (string): Unique UUID for the run.
* `satellite` (string): Selected source (e.g., "ERA5").
* `bands` (list[string]): Specific variables selected (e.g., `["temperature_2m", "precip"]`).
* `geometry_source` (string): Origin of geometry (e.g., "Shapefile: field_A.shp", "Point: 45.1,12.2").
* `dates` (object):
* `start_year`, `end_year` (int)
* `start_doy`, `end_doy` (int)


* `export_method` (string): "Drive" or "Local".

---

## 3. User Interface Specification (Streamlit)

The UI is divided into a **Sidebar (Control & History)** and a **Main Panel (Input & Verification)**.

### **Sidebar: Management Console**

1. **Authentication Status:**
* Visual indicator (Green Dot/Red Dot) showing if GEE is successfully initialized.
* Button: `Reconnect` (re-runs `ee.Authenticate()` if needed).


2. **Configuration:**
* Input field: `GEE Project ID` (Pre-filled from `settings.toml`).
* Input field: `Drive Folder Name` (Where files go in Google Drive).


3. **Task Monitor (Live GEE Status):**
* **Function:** Fetches the last 20 tasks via `ee.data.getTaskList()`.
* **Display:** A compact table or list.
* Columns: `Task Name`, `State` (READY, RUNNING, COMPLETED, FAILED), `Time`.


* **Refresh:** A small `Refresh` button to update the list without reloading the whole page.


4. **History / Quick Load:**
* Dropdown: "Load Previous Run".
* Content: Lists timestamps of previous jobs (e.g., "2023-10-27 14:30 - ERA5").
* **Action:** Selecting an item immediately repopulates the Main Panel inputs with those settings.



### **Main Panel: The Extraction Pipeline**

#### **Section 1: Data Source (WHAT)**

* **Satellite Selector:** Dropdown `[NDVI, ERA5, CHIRPS]`.
* **Variable Context:**
* If **NDVI**: Information text "Standard MOD13Q1 bands (NDVI, EVI) will be exported."
* If **ERA5**: Multi-select box populated with human-readable variable names.
* *Constraint:* At least one variable must be selected.


* If **CHIRPS**: Checkbox options (e.g., "Sum Daily Precipitation").

Main satellites are already described in @satellites.ts (Previously in .ts format but now we want it in JSON format)



#### **Section 2: Region of Interest (WHERE)**

* **Input Method Selector:** Radio button `[Point Coordinate, Shapefile Upload, GADM Admin]`.
1. **Point Coordinate:** Two text boxes (Lat, Lon).
2. **Shapefile Upload:** File uploader widget (accepts `.zip`, `.geojson`, `.kml`).
3. **GADM Admin:**
* Dropdown 1: Country (e.g., "Italy").
* Dropdown 2: Admin Level 1 (e.g., "Veneto").
* We will use [pygadm](https://pygadm.readthedocs.io/en/latest/_sources/usage.rst.txt) for this purpose.



* **Passive Map Verification:**
* **Component:** `st.map` or `folium`.
* **Behavior:** Initially empty or centered on world.
* **Trigger:** Once valid input is provided (e.g., a shapefile is uploaded), the map **automatically centers** and displays the red outline of the geometry.
* **Interaction:** User *cannot* click to draw. They can only pan/zoom to verify the input is correct.



#### **Section 3: Time Definition (WHEN)**

* **Years:** Two number inputs (Start, End).
* **Seasonality:**
* Checkbox: `Filter by Season`.
* If checked: Two sliders (0-365) for Start DOY and End DOY.
* **Visual Aid:** If Start > End, display a warning/info box: *"Note: This season crosses the New Year (e.g., Nov to Feb)."*



#### **Section 4: Execution (HOW)**

* **Method:** Toggle `[Save to Drive (Batch)]` vs `[Download Locally (Interactive)]`.
* **Button:** `RUN EXTRACTION`.
* **Feedback:**
* Show a spinner "Submitting task...".
* On success: Display a green success box with the **Task ID**.
* On failure: Display a red error box with the specific Python exception message.



---

## 4. Backend Class Design

### **Base Class: `DataExtractor**`

This abstract class enforces consistency.

* **`__init__(project_id)`**: Sets up auth.
* **`load_settings()`**: Reads `settings.toml`.
* **`parse_geometry(data, type)`**:
* Decides how to handle the input.
* If `type` == 'shapefile', it uses `geopandas` to read the file, converts to GeoJSON, then to `ee.Geometry`.


* **`check_seasonality(start_doy, end_doy)`**: Returns the boolean logic for cross-year filtering.
* **`monitor_tasks()`**: Static method that returns the list of recent GEE tasks for the sidebar.

### **Satellite Sub-Classes**

Each sub-class must have a unique `bands` dictionary mapping user-friendly names to GEE Band IDs.

* **`ERA5Extractor`**:
* Attribute `AVAILABLE_BANDS`: `{'Temperature': 'mean_2m_air_temperature', 'Rain': 'total_precipitation', ...}`
* Method `validate_bands(selected_list)`: Ensures user choices are valid.


* **`NDVIExtractor`**:
* Method `process_quality_mask()`: Applies the specific bitmasking for MODIS/Landsat to remove clouds/snow (hardcoded best practice).



---

## 5. Development Roadmap

**Phase 1: Setup & Persistence**

1. Create `config/settings.toml`.
2. Implement `src/utils/config_manager.py` to read/write settings.
3. Implement `src/utils/history_manager.py` to handle the JSON caching.

**Phase 2: The Logic Core**

1. Build the `DataExtractor` parent class.
2. Implement the **Passive Geometry Parser** (Shapefile -> ee.Geometry).
3. Implement the **Task Monitor** (API connector).

**Phase 3: The Satellite Modules**

1. Implement `NDVIExtractor` (easiest, fixed bands).
2. Implement `ERA5Extractor` (handling dynamic band selection).
3. Implement `CHIRPSExtractor`.

**Phase 4: The Interface**

1. Build the Streamlit layout.
2. Connect the **Sidebar** to the `config_manager` and `Task Monitor`.
3. Connect the **Main Panel** input widgets to the `DataExtractor`.
4. Implement the **Passive Map** (it listens to the geometry state and renders).

**Phase 5: Validation**

1. Verify History Loading: Does clicking a history item correctly reset the sliders and dropdowns?
2. Verify Passive Map: Does uploading a bad shapefile result in a clear error instead of a crashed map?