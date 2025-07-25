# Regatta Track Analysis

A Python toolkit for analyzing GPX tracks from sailing regattas.

> **Note:** This project was created with assistance from Windsurf and Claude 3.7 Sonnet.

## Features

- Parse GPX files into trackpoint objects
- Calculate distance between points (using Haversine formula)
- Calculate bearing/direction in degrees
- Calculate speed in m/s and knots
- Automatic track segmentation based on bearing/direction changes
- Detailed metrics for each segment (distance, duration, speed, bearing)
- Interactive web-based visualization of tracks and segments

## Usage

### Analyzing a GPX file

```bash
python3 src/gpx_analyzer.py your_track.gpx [bearing_threshold]
```

The optional `bearing_threshold` parameter (default: 20°) controls how sensitive the segmentation is to direction changes. A lower value creates more segments.

### Visualizing a GPX track

```bash
python3 src/generate_track_html.py your_track.gpx [bearing_threshold] [start_segment] [end_segment] [output_file] [buoys_file] [wind_direction]
```

The optional `bearing_threshold` parameter (default: 20°) controls how sensitive the segmentation is to direction changes. A lower value creates more segments.

The optional `start_segment` and `end_segment` parameters allow you to specify a range of segments to visualize. These should be zero-based indices.

The optional `output_file` parameter allows you to specify the output file name. If not specified, the default is `track_visualization.html`.

The optional `buoys_file` parameter allows you to specify a JSON file containing buoy coordinates. The file should be in the format `[{"lat": lat, "lon": lon, "name": name}, ...]`.

The optional `wind_direction` parameter allows you to specify the wind direction in degrees (where wind is coming FROM).

This creates an HTML file in the `docs` directory with an interactive map visualization. The HTML file will automatically open in your default browser.


### Using the geo_utils library in your own code

```python
from geo_utils import calculate_distance, calculate_bearing, calculate_speed

# Calculate distance between two points
distance = calculate_distance(lat1, lon1, lat2, lon2)  # Returns distance in meters

# Calculate bearing/direction
bearing = calculate_bearing(lat1, lon1, lat2, lon2)  # Returns bearing in degrees (0-360)

# Calculate speed
speed_ms, speed_knots = calculate_speed(distance_meters, time_diff_seconds)

# Check if two bearings are similar (handles 0/360 degree wrapping)
are_similar = is_similar_bearing(bearing1, bearing2, threshold=20)
```

## Project Structure

- `/src/` - Python source code
  - `geo_utils.py` - Core library with calculation functions
  - `gpx_analyzer.py` - Main script for parsing and analyzing GPX files
  - `generate_track_html.py` - Script to generate interactive HTML visualizations
  - `track_visualizer.py` - Alternative visualization using Python's turtle module (requires tkinter)
- `/data/` - GPX track files
- `/output/` - Generated HTML visualizations
- `*.md` - Documentation files

## Visualization Features

- Interactive map with OpenStreetMap background
- Color-coded track segments based on direction
- Popup information for each segment showing:
  - Distance
  - Duration
  - Direction/bearing
  - Average speed
- Adjustable segmentation sensitivity via bearing threshold
