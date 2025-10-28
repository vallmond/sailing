# Interactive Sailing Track Viewer

A browser-based application for visualizing and analyzing sailing tracks from GPX files with interactive time range selection and metrics calculation.

## Features

- **Direct GPX File Processing**: Load GPX files directly in the browser without server-side processing
- **Time Range Selection**: Select specific time ranges to analyze using an interactive slider
- **Track Visualization**: View your sailing track on an interactive map with speed-based coloring
- **Metrics Calculation**: Calculate key metrics for the selected time range:
  - Distance traveled
  - Duration
  - Average and maximum speed
  - Wind angles and tack count
- **Wind Analysis**: Input wind direction and see how your track relates to the wind
- **Playback**: Animate your track with adjustable playback speed
- **Additional Objects**: Load buoys, start lines, and other markers from a JSON file

## How to Use

1. Open `index.html` in your web browser
2. Load your GPX track file using the file input
3. Optionally load a markers JSON file for buoys and other objects
4. Set the wind direction in degrees
5. Click "Load Data" to process and display your track
6. Use the time slider to select specific portions of your track
7. View calculated metrics for the selected time range
8. Use the playback controls to animate your track

## Markers JSON Format

The application accepts a JSON file with the following structure for markers:

```json
{
  "buoys": [
    {
      "name": "Buoy 1",
      "lat": 54.450,
      "lon": 18.580,
      "color": "#ff0000",
      "description": "Port rounding"
    }
  ],
  "startLine": {
    "point1": {
      "lat": 54.448,
      "lon": 18.581
    },
    "point2": {
      "lat": 54.449,
      "lon": 18.583
    }
  },
  "markers": [
    {
      "name": "Special Point",
      "lat": 54.451,
      "lon": 18.585,
      "color": "#00ff00",
      "description": "Point of interest"
    }
  ]
}
```

## Wind Analysis

The application calculates the angle between your course and the wind direction. This helps analyze your sailing performance on different points of sail. The wind rose chart shows the distribution of wind angles throughout your track.

## Requirements

- Modern web browser with JavaScript enabled
- No server-side processing required
- Works offline once loaded

## Browser Compatibility

- Chrome 60+
- Firefox 60+
- Safari 12+
- Edge 79+

## Libraries Used

- Leaflet 1.7.1 for map visualization
- jQuery 3.6.0 and jQuery UI 1.12.1 for UI controls
- D3.js v7 for data visualization (wind rose chart)
