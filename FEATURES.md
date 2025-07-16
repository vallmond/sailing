# Regatta Project Features

This document provides an overview of the key features and functionality in the Regatta sailing track visualization project.

## Core Features

### Track Analysis
- **GPX Parsing**: Parse GPX files containing sailing tracks with timestamps, coordinates, and speed data
- **Segment Detection**: Automatically detect segments based on bearing changes and speed patterns
- **Speed Analysis**: Calculate speed metrics for each segment including average, max, and min speeds
- **Wind Direction Analysis**: Estimate wind direction from tacking patterns or accept manual input
- **Tack Detection**: Identify tacking maneuvers and classify segments by tack (port/starboard)
- **Point of Sail Classification**: Categorize segments based on their angle to the wind

### Visualization
- **Interactive Map**: Display the sailing track on an interactive Leaflet.js map
- **Speed-Based Coloring**: Color-code track segments based on speed categories (slow/medium/fast)
- **Segment Popups**: Show detailed metrics when clicking on a track segment
- **Wind Direction Indicator**: Display wind direction with a compass-oriented arrow
- **Buoy Visualization**: Show course markers (buoys, lines, polygons) on the map
- **Statistics Panel**: Display overall track statistics and segment distribution

## Usage

### Basic Usage
```bash
python -m src.generate_track_html [gpx_file] [bearing_threshold] [start_segment] [end_segment] [output_file] [buoys_file] [wind_direction]
```

### Parameters
- **gpx_file**: Path to the GPX file to analyze
- **bearing_threshold**: Minimum bearing change to detect a new segment (default: 60°)
- **start_segment**: First segment to include (optional)
- **end_segment**: Last segment to include (optional)
- **output_file**: Custom output HTML file path (optional)
- **buoys_file**: JSON file containing buoy coordinates (optional)
- **wind_direction**: Force a specific wind direction in degrees (optional)

### Example
```bash
python -m src.generate_track_html data/2025-06-28-11_13.gpx 60 None None None data/sample_buoys.json 270
```

## Data Formats

### GPX Files
Standard GPX format with trackpoints containing:
- Latitude and longitude
- Timestamp
- Speed (optional)

### Buoy JSON Format
```json
[
  {
    "name": "Buoy 1",
    "lat": 54.123,
    "lon": 18.456,
    "type": "marker"
  },
  {
    "name": "Line 1",
    "points": [
      {"lat": 54.123, "lon": 18.456},
      {"lat": 54.124, "lon": 18.457}
    ],
    "type": "line"
  }
]
```

## Future Development Ideas
- User interface for adjusting parameters
- Multiple track comparison
- Performance analytics dashboard
- Weather data integration
- Race timing and handicap calculations
