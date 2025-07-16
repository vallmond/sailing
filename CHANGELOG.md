# Regatta Project Changelog

This document tracks significant changes and features added to the Regatta sailing track visualization project.

## 2025-06-29

### Added
- **Performance Analysis Script**: Created a new script (`analyze_performance.py`) to analyze vessel speed in relation to wind direction, tacks, and points of sail
  - Provides detailed statistics on performance across different sailing conditions
  - Outputs data as CSV for further analysis and visualization
  - Shows speed distribution by wind angle in 10° bins

### Added
- **Point of Sail Classification**: Added automatic classification of sailing segments based on relative wind angle
  - Close Hauled: < 35° from the wind
  - Close Reach: 35° to 80° from the wind
  - Beam Reach: 80° to 100° from the wind
  - Broad Reach: 100° to 135° from the wind
  - Run: 135° to 180° from the wind
  - Turning: For all turn segments
- **Wind Direction Icon Improvements**: Fixed wind direction icon to show North at the top with compass labels (N, E, S, W)
- **Points of Sail Statistics**: Added statistics in the legend showing distribution of points of sail across the track

### Fixed
- Corrected wind direction icon orientation in popups
- Fixed point of sail calculation using formula: `abs((course - wind) - 180)`

## 2025-06-28

### Added
- **Wind Direction Parameter**: Added ability to specify wind direction as a command-line parameter
  - When provided, automatic wind direction estimation is bypassed
  - Example: `python -m src.generate_track_html data/2025-06-28-11_13.gpx 60 None None None data/sample_buoys.json 270`
- **Buoy Visualization**: Added support for visualizing buoys, lines, and polygons from JSON files
  - Buoys appear as markers on the map with popups
  - Added to legend with appropriate styling

### Fixed
- Fixed Leaflet.js polyline distance calculation
- Improved legend display logic

## Earlier Changes

### Core Features
- GPX track parsing and visualization
- Segment detection and analysis
- Speed-based coloring of track segments
- Interactive map with segment metrics
- Tack detection and visualization
- Wind direction estimation algorithm
