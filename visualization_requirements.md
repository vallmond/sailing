# Regatta Track Visualization Requirements

This document outlines the comprehensive requirements and implementation details for the GPX track visualization system used in the regatta analysis project.

## 1. Core Visualization Requirements

### 1.1 Track Segmentation
- **Bearing-based Segmentation**: Track is divided into segments based on significant bearing changes
- **Configurable Threshold**: Bearing threshold (default 40°) determines when a new segment starts
- **Segment Filtering**: Ability to display specific segment ranges for detailed analysis

### 1.2 Interactive Map Features
- **Base Map**: OpenStreetMap as the base layer
- **Zoom and Pan**: Standard map navigation controls
- **Bounds Fitting**: Automatically fit the map to show the entire track
- **Segment Popups**: Click on any segment to view detailed information
- **Responsive Design**: Works on both desktop and mobile browsers

### 1.3 Track Information Display
- **Info Box**: Shows overall track statistics (distance, duration, speeds)
- **Legend**: Explains color coding and provides segment statistics
- **Wind Information**: When available, shows wind direction and tack distribution

## 2. Segment Visualization

### 2.1 Speed-Based Coloring
The primary coloring schema uses paired colors for each speed category:

| Speed Category | Color Pair | Description |
|----------------|------------|---------------|
| Slow | Green/Yellow | rgb(80,200,80) and rgb(220,220,60) - Used when maneuvering or in light wind (<3 knots) |
| Medium | Blue/Purple | rgb(60,80,220) and rgb(180,60,220) - Normal cruising speed in moderate wind (3-6 knots) |
| Fast | Red/Orange | rgb(220,60,60) and rgb(240,140,40) - High performance in strong wind conditions (>6 knots) |

These are alternated with a light/dark contrast pattern to distinguish adjacent segments.

### 2.2 Segment Trend Visualization

#### 2.2.1 Overall Segment Trends
- **Trendline Display**: Each segment has a straight line connecting its start and end points
- **Direction Indication**: Shows the overall direction of travel in the segment
- **Bearing Calculation**: Overall bearing is calculated and displayed in the popup

#### 2.2.2 First and Last 10 Seconds Trends
- **First 10s Trendline**: Blue solid line showing direction during first 10 seconds
- **Last 10s Trendline**: Red solid line showing direction during last 10 seconds
- **Direction Change**: Calculate and display the direction change within the segment
- **Bearing Information**: Show both first and last 10s bearings in the segment popup

### 2.3 Segment Popup Information
- **Basic Info**: Segment number, distance, duration, speed
- **Direction Info**: Overall bearing, bearing change from previous segment
- **Time Info**: Start and end times of the segment
- **Speed Category**: Text and color indication of speed category
- **Direction Change**: Direction change within segment (first 10s to last 10s)

## 3. Wind Analysis Visualization

### 3.1 Wind Direction Estimation
- **Algorithm**: Analyze tacking patterns to estimate wind direction
- **Wind Arrow**: Visual indicator showing the direction wind is coming from
- **Wind Direction**: Numerical display of wind direction in degrees

### 3.2 Tack Indication
When wind direction is estimated, segments are also categorized by tack:

| Tack | Description |
|------|-------------|
| Port | Wind coming from the left side of the boat (wind on port side) |
| Starboard | Wind coming from the right side of the boat (wind on starboard side) |
| Mixed | Segments that contain both port and starboard tacks |

### 3.3 Wind-Related Information
- **Relative Wind Angle**: Angle between segment direction and wind direction
- **Tack Distribution**: Count of segments by tack (port, starboard, mixed)
- **Dominant Tack**: Most common tack for each segment

## 4. Legend and Information Elements

### 4.1 Track Information Box
- **Distance**: Total track distance in kilometers
- **Duration**: Total duration in minutes
- **Average Speed**: Overall average speed in knots
- **Min/Max Speed**: Minimum and maximum speeds in knots

### 4.2 Speed Categories Legend
- **Color Coding**: Visual explanation of speed-based colors
- **Speed Ranges**: Text description of speed thresholds

### 4.3 Segment Statistics
- **Count by Speed**: Number of segments in each speed category
- **Total Count**: Total number of segments in the visualization

### 4.4 Tack Distribution (when wind available)
- **Port Tack Count**: Number of segments on port tack
- **Starboard Tack Count**: Number of segments on starboard tack
- **Mixed Tack Count**: Number of segments with mixed tacks

### 4.5 Wind Direction Indicator (when available)
- **Arrow**: Visual indicator of wind direction
- **Direction Value**: Wind direction in degrees

## 5. Implementation Notes

### 5.1 Technologies Used
- **Mapping**: Leaflet.js for interactive map display
- **Base Map**: OpenStreetMap tiles
- **Data Processing**: Python for GPX parsing and analysis
- **Output Format**: Self-contained HTML file with embedded JavaScript

### 5.2 Additional Visualization Methods

#### 5.2.1 Single-Color Alternative
An alternative visualization approach uses single colors instead of paired colors:

| Speed Range | Color | RGB Value | Description |
|-------------|-------|-----------|-------------|
| < 3 knots | Blue | rgb(50,50,200) | Slow speed |
| 3-6 knots | Green | rgb(50,180,50) | Medium speed |
| > 6 knots | Red | rgb(200,50,50) | Fast speed |

## 6. Future Enhancement Possibilities

### 6.1 Additional Visualization Options
- **Wind Angle Coloring**: Color segments based on their angle to the wind (upwind, reaching, downwind)
- **Efficiency Coloring**: Color based on speed relative to theoretical maximum for that wind angle
- **VMG Coloring**: Color based on Velocity Made Good toward a waypoint or upwind/downwind
- **Acceleration/Deceleration**: Color based on speed changes within segments

### 6.2 Advanced Analysis Features
- **Tacking Efficiency**: Calculate and visualize efficiency of tacking maneuvers
- **Start Line Analysis**: Special visualization for race start sequences
- **Mark Rounding**: Detection and analysis of mark roundings in races
- **Layline Visualization**: Show optimal approach angles to marks based on wind
- **Polar Diagram Integration**: Compare actual performance to theoretical boat speed
