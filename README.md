# 🌍 GEE Data Extractor UI

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=Streamlit&logoColor=white)](https://streamlit.io/)
[![Google Earth Engine](https://img.shields.io/badge/Google%20Earth%20Engine-4285F4?logo=google-earth&logoColor=white)](https://earthengine.google.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A simple but effective **Google Earth Engine (GEE) Data Extraction Suite** with a modern **Streamlit** interface. Designed for researchers, GIS specialists, and data scientists to streamline the acquisition of historical satellite datasets.

---

## 🚀 Overview

![GEE Data Extractor](assets/screenshot.png)

The **GEE Data Extractor** provides a robust pipeline for extracting complex environmental and satellite data without the need for manual coding in the GEE JavaScript code platform or with the Python API. Users can visualize their regions of interest (ROI) instantly and submit high-volume extraction jobs to either Google Drive or direct local storage.

### ✨ Key Features

- **Intuitive GUI**: A polished Streamlit dashboard for end-to-end data extraction.
- **Flexible ROI Selection**:
  - **Point Coordinates**: Select your Lat/Lon coordinates for extraction.
  - **File Upload**: Support for Shapefiles (`.shp`), GeoJSON, and KML.
  - **Administrative Boundaries**: Seamless integration with **GADM** via `pygadm` for country and province-level selection.
- **Satellites Available** (for the moment):
  - **Vegetation Indices**: MODIS NDVI & EVI (MOD13Q1).
  - **Weather & Climate**: ERA5-Land Hourly and Daily reanalysis.
  - **Precipitation**: CHIRPS Daily high-resolution rainfall data.
- **Reproducibility**: Automatic state persistence in `settings.toml` and full job history tracking in `.cache/history.json`.
- **Passive Map Verification**: Automated map and geometry rendering to confirm input accuracy before submission.

---

## 🛠️ Installation

### 1. Prerequisites
- Python 3.8 or higher.
- A **Google Earth Engine** account ([Sign up here](https://earthengine.google.com/signup/)).

### 2. Clone the Repository
```bash
git clone https://github.com/Mastro1/CropYieldData_UI.git
cd GEE_data_extractor_UI
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Authentication
Run the following command to authenticate your Google Earth Engine account:
```bash
python -c "import ee; ee.Authenticate()"
```

---

## 📖 Usage

1. **Start the Application**:
   For the best experience, use the provided helper scripts which handle environment setup automatically:
   
   - **Windows**: Simply double-click `run.bat` (it will create a virtual environment and install dependencies if they are missing).
   - **Python/Standard**: Alternatively, use the cross-platform runner:
     ```bash
     python run.py
     ```

   *Note: These scripts are optional convenience tools. You can always run the app manually using:*
   ```bash
   streamlit run src/interface/app.py
   ```
   
2. **Configure Settings**: Use the sidebar to set your GEE Project ID and default download folders.
3. **Define WHAT**: Select your satellite dataset (e.g., ERA5-Land) and the specific bands you require.
4. **Define WHERE**: Upload a geometry file or select a GADM administrative unit.
5. **Define WHEN**: Set your start/end years and optional seasonal filters.
6. **Execute**: Choose "Save to Drive" for large batch jobs or "Download Locally" for immediate samples.

---

## 🏗️ Technical Architecture

The system utilizes a **Local State Architecture** to ensure responsiveness and reliability:

- **Frontend**: Streamlit (Interface Layer)
- **Infrastructure**: Python-native GEE API wrapper.
- **Persistence**: `config/settings.toml` for user preferences.
- **History**: JSON-based event log storing previous run parameters for instant reloading.

---

## 📈 Roadmap

Future enhancements and upcoming features:

- [ ] **Expand Dataset Catalog**: Integrate additional satellite constellations (e.g., Sentinel-2, Landsat-8/9).
- [ ] **Spatial Masking**: Add support for uploading and applying custom masks (e.g., crop masks, land cover classification) during extraction.
- [ ] **Full Session Restore**: Finalize the "Reload Settings" logic to allow seamless recovery of previous work states (WIP, works for the most part).

---

## 🔍 SEO & Keywords

`Satellite Data Extraction` | `Google Earth Engine UI` | `Remote Sensing Python` | `Environmental Data Analysis` | `ERA5 Land Data` | `CHIRPS Precipitation Extraction` | `NDVI Timeseries` | `GIS Dashboard` | `Sustainable Agriculture Data`

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
*Developed with ❤️ for the Remote Sensing Community.*
