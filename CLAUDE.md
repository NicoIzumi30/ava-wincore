# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Ava Wincore** is a comprehensive outlet analysis system that analyzes retail outlet locations based on surrounding facilities and Indomaret competitor presence. The system integrates Google Spreadsheet data with interactive multi-province maps and business intelligence reporting.

### Core Features
- Analyzes 9 categories of surrounding facilities (residential, education, public areas, culinary, business centers, groceries, convenience stores, industrial, hospital/clinic)
- Multi-province interactive maps (Jakarta, West Java, Central Java, South Sumatra, North Sumatra, East Java-Bali-Kalimantan, Southeast Sulawesi)
- Indomaret competitor analysis and integration
- Automated rating system (1-5 stars based on facility count)
- Excel and JSON export with visual indicators
- Web dashboard with province navigation
- Automated daily updates via cron jobs

## Development Commands

### Main Application
```bash
# Run main analysis (interactive)
python main.py

# Run analysis with help
python main.py --help

# Start web server for dashboard
python web_server.py
# Access at: http://localhost:8080

# Run standalone kecamatan analysis
python kecamatan_analysis.py

# Run automated update
python auto_update.py
```

### Testing and Status
```bash
# Check application status
./check_status.sh

# Restart services
./restart.sh

# Check dependencies
python -c "import pandas, folium, gspread, geopy; print('Dependencies OK')"
```

### Docker Deployment
```bash
# Build Docker image
docker build -t outlet-analisis .

# Run container
docker run -d -p 8080:8080 --name outlet-analisis outlet-analisis

# Access container
docker exec -it outlet-analisis /bin/bash
```

## Architecture Overview

### Core Components
- **main.py**: Primary entry point with interactive workflow
- **config.py**: Central configuration with province bounds, API settings, clustering configuration
- **data_loader.py**: Google Sheets integration and data loading
- **facility_analyzer.py**: Core analysis engine using Overpass API
- **map_generator.py**: Multi-province map generation with Folium
- **indomaret_handler.py**: Competitor analysis and integration
- **web_server.py**: Flask web server for dashboard access

### Data Flow
1. **Load data** from Google Spreadsheet (credentials.json required)
2. **Analyze facilities** around each outlet using Overpass API
3. **Integrate Indomaret data** for competitor analysis
4. **Generate maps** per province + full map with clustering
5. **Export results** to Excel with checkmarks and JSON
6. **Serve via web** dashboard with province navigation

### Key Configuration
- **Google Sheets**: ID `1qbyTP6ec2vrwtfW1q5WAR5Iz0D8sZ28OEmF785xpm8s`, sheet `INPUT AVA MOBILE`
- **Analysis radius**: Default 100m, expandable to 200m
- **Province support**: 7 configured provinces with specific bounds and zoom levels
- **Clustering**: Auto-adaptive based on dataset size (50-1000+ outlets)
- **APIs**: Multiple Overpass API endpoints for redundancy

### Required Files
- **credentials.json**: Google Sheets API service account credentials
- **indomaret_data.json**: Optional competitor data in format: `[{"Store": "name", "Latitude": lat, "Longitude": lon, "Kecamatan": "district"}]`

### Output Structure
```
output/
├── analisis_outlet.xlsx          # Excel with checkmarks and summary
├── hasil_analisis_outlet.json    # Raw analysis data
├── peta_outlet_full.html         # Full multi-province map
├── peta_outlet_[province].html   # Individual province maps
├── maps_index.html               # Visual map navigator
├── index.html                    # Main dashboard
└── indomaret_competition_report.json  # Competitor analysis
```

## Development Guidelines

### Adding New Provinces
1. Add province configuration to `PROVINCE_BOUNDS` in config.py
2. Include bounds, center coordinates, zoom level, and filename
3. Update province detection logic in `multi_province_utils.py`

### Modifying Analysis Categories
- Edit facility categories in `facility_analyzer.py`
- Update Overpass API queries for new facility types
- Adjust rating calculation logic

### Performance Optimization
- Use clustering settings in config.py for large datasets
- Leverage API caching via `api_ava_wincore.pkl`
- Implement batch processing for multiple outlets
- Configure appropriate thread counts in `MAX_WORKERS`

### API Integration
- Primary data source: Google Sheets API
- Facility data: Overpass API (OpenStreetMap)
- Fallback endpoints configured for reliability
- Cache system reduces redundant API calls

## Common Issues

### Setup Issues
- Ensure `credentials.json` has proper Google Sheets API permissions
- Verify spreadsheet ID and sheet name in config.py
- Check virtual environment activation for dependencies

### Performance Issues
- Large datasets: Enable aggressive clustering mode
- API timeouts: Increase `API_TIMEOUT` in config.py
- Memory usage: Reduce `BATCH_SIZE` or `MAX_WORKERS`

### Map Generation Issues
- Browser compatibility: Use modern browsers for HTML maps
- Large datasets: Consider performance clustering mode
- Missing provinces: Check province name mapping in config

## Monitoring and Logs

- **outlet_analysis.log**: Main application logs
- **web_server.log**: Web server access and error logs
- **cron.log**: Automated update logs
- **outlet_analysis_progress.json**: Resume capability for interrupted analysis