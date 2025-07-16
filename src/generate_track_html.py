import sys
import os
import json
from datetime import datetime
# Update imports to use the new directory structure
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.gpx_analyzer import parse_gpx, detect_segments, analyze_segments, analyze_wind_direction, detect_tack_segments, create_segments_from_tacks
from src.geo_utils import calculate_bearing, angle_diff

def load_buoys(buoys_file):
    """
    Load buoy coordinates from a JSON file.
    
    Args:
        buoys_file (str): Path to the JSON file containing buoy coordinates
        
    Returns:
        list: List of buoy coordinates as dicts with 'lat', 'lon', and 'name' keys
    """
    if not os.path.exists(buoys_file):
        print(f"Warning: Buoys file {buoys_file} not found.")
        return []
    
    try:
        with open(buoys_file, 'r') as f:
            buoys = json.load(f)
        print(f"Loaded {len(buoys)} buoys from {buoys_file}")
        return buoys
    except Exception as e:
        print(f"Error loading buoys file: {e}")
        return []

def generate_html_visualization(gpx_file, bearing_threshold=60, start_segment=None, end_segment=None, output_file=None, buoys=None, wind_direction=None):
    """
    Generate an HTML visualization of the GPX track with segments colored by speed.
    Now includes wind direction visualization and buoy markers.
    
    Args:
        gpx_file (str): Path to the GPX file
        bearing_threshold (float): Threshold for bearing change to detect segments
        start_segment (int, optional): Index of the first segment to visualize
        end_segment (int, optional): Index of the last segment to visualize
        output_file (str, optional): Path to save the HTML output
        buoys (list, optional): List of buoy coordinates as dicts with 'lat', 'lon', and optional 'name'
                               Example: [{'lat': 54.402008, 'lon': 18.758700, 'name': 'Buoy 1'}]
        wind_direction (float, optional): Wind direction in degrees (0-360, coming from). If not provided,
                                        will be estimated from the track data.
    """
    # Parse GPX file
    print(f"Parsing GPX file: {gpx_file}")
    trackpoints = parse_gpx(gpx_file)
    print(f"Found {len(trackpoints)} trackpoints")
    
    # Analyze wind direction with improved filtering
    print("Analyzing track to estimate wind direction...")
    
    # Handle wind direction - use provided value or estimate from track
    if wind_direction is not None:
        print(f"Using provided wind direction: {wind_direction:.2f}° (coming from)")
        # Get tack assignments based on the provided wind direction
        _, tack_assignments, wind_analysis = analyze_wind_direction(
            trackpoints, 
            min_turn_duration=10,  # Minimum 10 seconds for a turn to be considered
            exclude_edges=True,    # Exclude first and last turns
            force_wind_direction=wind_direction
        )
    else:
        # First analyze without filtering to get original wind direction
        original_wind_direction, _, original_wind_analysis = analyze_wind_direction(
            trackpoints, 
            min_turn_duration=0,    # No minimum duration
            exclude_edges=False     # Include all turns
        )
        
        # Then analyze with filtering to get the final wind direction
        print("Analyzing track to estimate wind direction...")
        wind_direction, tack_assignments, wind_analysis = analyze_wind_direction(
            trackpoints, 
            min_turn_duration=10,  # Minimum 10 seconds for a turn to be considered
            exclude_edges=True     # Exclude first and last turns
        )
        
        if wind_direction is not None:
            print(f"Estimated wind direction: {wind_direction:.2f}° (coming from)")
            
            # Count tacks
            port_tacks = tack_assignments.count('port')
            starboard_tacks = tack_assignments.count('starboard')
            print(f"Tack distribution: {port_tacks} port tacks, {starboard_tacks} starboard tacks")
        else:
            print("Could not estimate wind direction from track data.")
        
        # Print information about filtered tack points
        if 'potential_tack_points' in wind_analysis and 'used_tack_points' in wind_analysis:
            print(f"Detected {len(wind_analysis['potential_tack_points'])} potential tack points")
            if 'valid_tack_points' in wind_analysis:
                print(f"After filtering short turns: {len(wind_analysis['valid_tack_points'])} valid tack points")
            print(f"After excluding first/last turns: {len(wind_analysis['used_tack_points'])} tack points used for wind estimation")
            print(f"Wind estimation method: {wind_analysis.get('estimation_method', 'unknown')}")
            
            if 'course_groups' in wind_analysis:
                print(f"\nFiltered course groups: {len(wind_analysis['course_groups'])}")
                for i, group in enumerate(wind_analysis['course_groups']):
                    print(f"  Group {i+1}: {len(group)} points, avg course: {np.mean(group):.2f}°")
                    
            if 'avg_courses' in wind_analysis:
                print(f"\nMain tacking directions: {wind_analysis['avg_courses']}")
                print(f"Tacking axis: {wind_analysis.get('tacking_axis', 'unknown')}°")
        else:
            print("Could not estimate wind direction from the track data")
    
    # Detect segments using the tack-based approach
    print("Detecting tack segments...")
    segments, segment_types = detect_segments(trackpoints, bearing_threshold=bearing_threshold)
    
    # Count segment types
    turn_segments = [segments[i] for i, segment_type in enumerate(segment_types) if segment_type == 'turn']
    straight_segments = [segments[i] for i, segment_type in enumerate(segment_types) if segment_type == 'straight']
    print(f"Created {len(segments)} segments:")
    print(f"  - {len(turn_segments)} turn segments")
    print(f"  - {len(straight_segments)} straight segments")
    
    # Apply segment filtering if specified
    segment_offset = 0
    if start_segment is not None:
        if start_segment >= len(segments):
            print(f"Error: Start segment {start_segment} is out of range (max: {len(segments)-1})")
            return
        segment_offset = start_segment
        segments = segments[start_segment:]
        print(f"Starting from segment {start_segment}")
    
    if end_segment is not None:
        if end_segment >= len(segments) + segment_offset:
            print(f"Error: End segment {end_segment} is out of range (max: {len(segments) + segment_offset - 1})")
            return
        segments = segments[:end_segment - segment_offset + 1]
        print(f"Ending at segment {end_segment}")
    
    print(f"Visualizing {len(segments)} segments")
    
    # Analyze segments
    segment_metrics = analyze_segments(segments, segment_types)
    
    # Add wind direction and tack information to each segment
    if wind_direction is not None:
        for i, segment in enumerate(segment_metrics):
            # Count tacks in this segment
            segment_points = segments[i]
            tack_counts = {'port': 0, 'starboard': 0}
            
            for j, point in enumerate(segment_points):
                point_idx = trackpoints.index(point)
                if point_idx < len(tack_assignments) and tack_assignments[point_idx] is not None:
                    tack = tack_assignments[point_idx]
                    tack_counts[tack] = tack_counts.get(tack, 0) + 1
            
            # Determine dominant tack
            dominant_tack = 'mixed'
            if tack_counts['port'] > 0 and tack_counts['starboard'] == 0:
                dominant_tack = 'port'
            elif tack_counts['starboard'] > 0 and tack_counts['port'] == 0:
                dominant_tack = 'starboard'
            
            # Calculate the angle between wind direction and course bearing for point of sail
            course_bearing = segment['overall_bearing']
            
            # Calculate the point of sail angle using the formula: abs((course - wind) - 180)
            # This gives the angle from the wind direction
            # We need to handle the case where the angle is greater than 180°
            wind_angle_diff = abs((course_bearing - wind_direction) - 180)
            # Ensure the angle is between 0° and 180°
            wind_angle = wind_angle_diff if wind_angle_diff <= 180 else 360 - wind_angle_diff
            
            # Debug output
            if i < 5:  # Only print for first few segments to avoid flooding output
                print(f"Segment {i}: Wind {wind_direction}\u00b0, Course {course_bearing}\u00b0, Angle {wind_angle}\u00b0")
            
            # Determine point of sail based on true wind angle
            point_of_sail = 'Unknown'
            if segment_types[i] == 'turn':
                point_of_sail = 'Turning'
            elif wind_angle < 35:
                point_of_sail = 'Close Hauled'
            elif wind_angle < 80:
                point_of_sail = 'Close Reach'
            elif wind_angle < 100:
                point_of_sail = 'Beam Reach'
            elif wind_angle < 135:
                point_of_sail = 'Broad Reach'
            elif wind_angle <= 180:
                point_of_sail = 'Run'
            
            # Add wind information to segment metrics
            segment_metrics[i]['wind_direction'] = wind_direction
            segment_metrics[i]['dominant_tack'] = dominant_tack
            segment_metrics[i]['relative_wind_angle'] = wind_angle
            segment_metrics[i]['point_of_sail'] = point_of_sail
    
    # Prepare track data for visualization
    segments_data = []
    for i, segment in enumerate(segment_metrics):
        # Create a simplified representation of the segment for the visualization
        segment_data = {
            'index': i + segment_offset,
            'points': [{'lat': p.lat, 'lon': p.lon, 'time': p.time.isoformat() if p.time else None} for p in segment['points']],
            'segment_type': segment.get('segment_type', 'straight'),  # Add segment type information
            'metrics': {
                'distance_km': segment['total_distance_meters'] / 1000,  # Convert meters to km
                'duration_minutes': segment['duration_seconds'] / 60,  # Convert seconds to minutes
                'speed_knots': segment['avg_speed_knots'],
                'overall_bearing': segment['overall_bearing'],
                'bearing_change': 0,  # Will be calculated below if not first segment
                'start_time': segment['start_time'].isoformat() if segment['start_time'] else None,
                'end_time': segment['end_time'].isoformat() if segment['end_time'] else None,
                'first_10s_bearing': segment.get('first_10s_bearing', segment['overall_bearing']),
                'last_10s_bearing': segment.get('last_10s_bearing', segment['overall_bearing']),
                'direction_change': segment.get('direction_change', 0),
                'segment_type': segment.get('segment_type', 'straight')  # Add segment type to metrics as well
            }
        }
        
        # Calculate bearing change from previous segment if not the first segment
        if i > 0:
            prev_segment = segment_metrics[i-1]
            bearing_change = angle_diff(segment['overall_bearing'], prev_segment['overall_bearing'])
            segment_data['metrics']['bearing_change'] = bearing_change
        
        # Add speed category
        speed = segment['avg_speed_knots']
        if speed < 4:
            segment_data['metrics']['speed_category'] = 'slow'
        elif speed < 6:
            segment_data['metrics']['speed_category'] = 'medium'
        else:
            segment_data['metrics']['speed_category'] = 'fast'
        
        # Add wind information if available
        if wind_direction is not None and 'wind_direction' in segment:
            segment_data['metrics']['wind_direction'] = segment['wind_direction']
            segment_data['metrics']['dominant_tack'] = segment['dominant_tack']
            segment_data['metrics']['relative_wind_angle'] = segment['relative_wind_angle']
            segment_data['metrics']['point_of_sail'] = segment['point_of_sail']
        
        segments_data.append(segment_data)
    
    # Create the complete track data dictionary with wind analysis information
    track_data = {
        'points': [
            {
                'lat': tp.lat,
                'lon': tp.lon,
                'time': tp.time.isoformat() if tp.time else None,
                'speed': tp.speed_knots if hasattr(tp, 'speed_knots') else None,
                'tack': tack_assignments[i] if tack_assignments and i < len(tack_assignments) else None
            } for i, tp in enumerate(trackpoints)
        ],
        'segments': segments_data,
        'wind_direction': wind_direction if wind_direction is not None else None,
        'buoys': buoys if buoys else [],
        'wind_analysis': {
            'potential_tack_points': wind_analysis.get('potential_tack_points', []),
            'valid_tack_points': wind_analysis.get('valid_tack_points', []),
            'used_tack_points': wind_analysis.get('used_tack_points', []),
            'estimation_method': wind_analysis.get('estimation_method', 'unknown')
        } if wind_analysis else {}
    }
    
    # Calculate overall track metrics
    total_distance = sum(segment['total_distance_meters'] for segment in segment_metrics) / 1000  # Convert to km
    total_duration = sum(segment['duration_seconds'] for segment in segment_metrics) / 60  # Convert to minutes
    avg_speed = sum(segment['avg_speed_knots'] for segment in segment_metrics) / len(segment_metrics) if segment_metrics else 0
    min_speed = min(segment['avg_speed_knots'] for segment in segment_metrics) if segment_metrics else 0
    max_speed = max(segment['avg_speed_knots'] for segment in segment_metrics) if segment_metrics else 0
    
    # Determine output file name if not specified
    if output_file is None:
        base_name = os.path.splitext(os.path.basename(gpx_file))[0]
        output_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output', f"{base_name}_visualization.html")
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Create the HTML content in parts to avoid f-string issues
    html_parts = []
    
    # HTML header
    html_parts.append("""<!DOCTYPE html>
<html>
<head>
    <title>GPX Track Visualization</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
    <style>
        body { margin: 0; padding: 0; }
        #map { position: absolute; top: 0; bottom: 0; width: 100%; }
        .info { padding: 6px 8px; font: 14px/16px Arial, Helvetica, sans-serif; background: white; background: rgba(255,255,255,0.8); box-shadow: 0 0 15px rgba(0,0,0,0.2); border-radius: 5px; }
        .info h4 { margin: 0 0 5px; color: #777; }
        .legend { text-align: left; line-height: 18px; color: #555; }
        .legend i { width: 18px; height: 18px; float: left; margin-right: 8px; opacity: 0.7; }
        .segment-info { margin-bottom: 5px; }
        .segment-info-label { font-weight: bold; }
        hr { border: 0; height: 1px; background: #ccc; margin: 10px 0; }
    </style>
</head>
<body>
    <div id="map"></div>
""")
    
    # Convert track data to JSON for JavaScript
    track_data_json = json.dumps(track_data)
    
    # Start script tag
    html_parts.append("""<script>
    // Track data from Python
    const trackData = """)
    
    # Add the JSON data
    html_parts.append(track_data_json)
    
    # Add track metrics
    html_parts.append(f"""; 
    
    // Track metrics
    const trackMetrics = {{
        totalDistance: {total_distance:.2f},
        totalDuration: {total_duration:.2f},
        avgSpeed: {avg_speed:.2f},
        minSpeed: {min_speed:.2f},
        maxSpeed: {max_speed:.2f}
    }};
    
    // Initialize the map
    const map = L.map('map');
    
    // Add OpenStreetMap tile layer
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }}).addTo(map);
    
    // Function to get color based on segment type, speed category and segment index
    function getSegmentColor(segment) {{
        const isEven = segment.index % 2 === 0;
        const speed = segment.metrics.speed_knots;
        const segmentType = segment.segment_type;
        
        // If it's a turn segment, use a different color scheme
        if (segmentType === 'turn') {{
            // Turn segments: Red/Orange regardless of speed
            return isEven ? 'rgb(255,0,0)' : 'rgb(255,100,0)';
        }} else {{
            // Straight segments: Use speed-based coloring
            if (speed < 3) {{
                // Slow: Green/Yellow
                return isEven ? 'rgb(80,200,80)' : 'rgb(220,220,60)';
            }} else if (speed < 6) {{
                // Medium: Blue/Purple
                return isEven ? 'rgb(60,80,220)' : 'rgb(180,60,220)';
            }} else {{
                // Fast: Red/Orange
                return isEven ? 'rgb(220,60,60)' : 'rgb(240,140,40)';
            }}
        }}
    }}
    
    // Create a polyline for each segment
    const bounds = L.latLngBounds();
    """)
    
    # Add JavaScript for creating polylines and trend lines
    html_parts.append("""    
    // First, display the track segments
    trackData.segments.forEach((segment, index) => {
        const points = segment.points;
        const metrics = segment.metrics;
        
        // Skip if no points
        if (points.length === 0) return;
        
        // Create an array of [lat, lng] for the polyline
        const latlngs = points.map(p => [p.lat, p.lon]);
        
        // Extend the map bounds
        latlngs.forEach(latlng => bounds.extend(latlng));
        
        // Get color based on segment type, speed and segment index
        const color = getSegmentColor(segment);
        
        // Create the polyline for the segment
        const polyline = L.polyline(latlngs, {
            color: color,
            weight: 5,
            opacity: 0.8,
            smoothFactor: 1
        }).addTo(map);
        
        // Create trend lines - only for straight segments with enough points
        if (points.length >= 2 && segment.segment_type === 'straight' && points.length >= 5) {
            // Overall segment trend line (black dashed)
            const startPoint = [points[0].lat, points[0].lon];
            const endPoint = [points[points.length - 1].lat, points[points.length - 1].lon];
            L.polyline([startPoint, endPoint], {
                color: 'black',
                weight: 2,
                opacity: 0.7,
                dashArray: '5, 5'
            }).addTo(map);
            
            // First 10 seconds trend line (blue solid)
            if (points.length > 10) {
                const first10sPoints = points.slice(0, Math.min(10, Math.floor(points.length / 3))).map(p => [p.lat, p.lon]);
                const first10sStart = first10sPoints[0];
                const first10sEnd = first10sPoints[first10sPoints.length - 1];
                L.polyline([first10sStart, first10sEnd], {
                    color: 'blue',
                    weight: 2,
                    opacity: 0.7
                }).addTo(map);
            }
            
            // Last 10 seconds trend line (red solid)
            if (points.length > 10) {
                const last10sPoints = points.slice(-Math.min(10, Math.floor(points.length / 3))).map(p => [p.lat, p.lon]);
                const last10sStart = last10sPoints[0];
                const last10sEnd = last10sPoints[last10sPoints.length - 1];
                L.polyline([last10sStart, last10sEnd], {
                    color: 'red',
                    weight: 2,
                    opacity: 0.7
                }).addTo(map);
            }
        }
        
        // Create popup with segment information
        let popupContent = `
            <div class="segment-info">
                <div><span class="segment-info-label">Segment:</span> ${segment.index}</div>
                <div><span class="segment-info-label">Type:</span> <strong>${segment.segment_type}</strong></div>
                <div><span class="segment-info-label">Distance:</span> ${metrics.distance_km.toFixed(2)} km</div>
                <div><span class="segment-info-label">Duration:</span> ${metrics.duration_minutes.toFixed(2)} min</div>
                <div><span class="segment-info-label">Avg Speed:</span> ${metrics.speed_knots.toFixed(2)} knots</div>
                <div><span class="segment-info-label">Speed Category:</span> <span style="color:${color}">${metrics.speed_category}</span></div>
                <div><span class="segment-info-label">Overall Bearing:</span> ${metrics.overall_bearing.toFixed(1)}\u00b0</div>
                <div><span class="segment-info-label">Bearing Change:</span> ${metrics.bearing_change.toFixed(1)}\u00b0</div>
                <div><span class="segment-info-label">Start Time:</span> ${new Date(metrics.start_time).toLocaleString()}</div>
                <div><span class="segment-info-label">End Time:</span> ${new Date(metrics.end_time).toLocaleString()}</div>
        `;
        
        // Add wind direction and tack info if available
        if (metrics.wind_direction !== undefined) {
            // Create a wind direction arrow
            const arrowSize = 40;
            const arrowDirection = metrics.wind_direction;
            
            popupContent += `
                <hr>
                <div><span class="segment-info-label">Wind Direction:</span> ${metrics.wind_direction.toFixed(1)}\u00b0
                    <div style="display: inline-block; margin-left: 10px;">
                        <svg width="${arrowSize}" height="${arrowSize}" viewBox="0 0 ${arrowSize} ${arrowSize}">
                            <circle cx="${arrowSize/2}" cy="${arrowSize/2}" r="${arrowSize/2-2}" stroke="#999" stroke-width="1" fill="#f0f0f0" />
                            <!-- Draw the North indicator at the top of the circle -->
                            <text x="${arrowSize/2}" y="8" text-anchor="middle" font-size="8" font-weight="bold" fill="#666">N</text>
                            <!-- Draw the East indicator -->
                            <text x="${arrowSize-4}" y="${arrowSize/2+3}" text-anchor="middle" font-size="8" fill="#666">E</text>
                            <!-- Draw the South indicator -->
                            <text x="${arrowSize/2}" y="${arrowSize-2}" text-anchor="middle" font-size="8" fill="#666">S</text>
                            <!-- Draw the West indicator -->
                            <text x="4" y="${arrowSize/2+3}" text-anchor="middle" font-size="8" fill="#666">W</text>
                            <!-- Draw the wind direction arrow with North at the top (0 degrees) -->
                            <line 
                                x1="${arrowSize/2}" 
                                y1="${arrowSize/2}" 
                                x2="${arrowSize/2 + Math.sin(arrowDirection * Math.PI / 180) * (arrowSize/2-5)}" 
                                y2="${arrowSize/2 - Math.cos(arrowDirection * Math.PI / 180) * (arrowSize/2-5)}" 
                                stroke="blue" 
                                stroke-width="2" 
                            />
                            <polygon 
                                points="
                                    ${arrowSize/2 + Math.sin(arrowDirection * Math.PI / 180) * (arrowSize/2-5)},
                                    ${arrowSize/2 - Math.cos(arrowDirection * Math.PI / 180) * (arrowSize/2-5)},
                                    ${arrowSize/2 + Math.sin((arrowDirection-15) * Math.PI / 180) * (arrowSize/2-12)},
                                    ${arrowSize/2 - Math.cos((arrowDirection-15) * Math.PI / 180) * (arrowSize/2-12)},
                                    ${arrowSize/2 + Math.sin((arrowDirection+15) * Math.PI / 180) * (arrowSize/2-12)},
                                    ${arrowSize/2 - Math.cos((arrowDirection+15) * Math.PI / 180) * (arrowSize/2-12)}
                                "
                                fill="blue"
                            />
                        </svg>
                    </div>
                </div>
                <div><span class="segment-info-label">Relative Wind Angle:</span> ${metrics.relative_wind_angle ? metrics.relative_wind_angle.toFixed(1) + '\u00b0' : 'N/A'}</div>
                <div><span class="segment-info-label">Point of Sail:</span> <strong>${metrics.point_of_sail || 'N/A'}</strong></div>
                <div><span class="segment-info-label">Dominant Tack:</span> ${metrics.dominant_tack || 'N/A'}</div>
            `;
        }
        
        popupContent += '</div>';
        polyline.bindPopup(popupContent);
    });
    
    // Fit the map to the track bounds
    map.fitBounds(bounds);
    
    // If we have wind analysis data, display the tack points used for wind direction estimation
    if (trackData.wind_analysis) {
        // Create markers for potential tack points (small gray circles)
        if (trackData.wind_analysis.potential_tack_points) {
            trackData.wind_analysis.potential_tack_points.forEach(idx => {
                if (idx < trackData.points.length) {
                    const point = trackData.points[idx];
                    L.circleMarker([point.lat, point.lon], {
                        radius: 3,
                        color: 'gray',
                        fillColor: 'gray',
                        fillOpacity: 0.5
                    }).addTo(map).bindPopup(`Potential tack point at ${point.time}`);
                }
            });
        }
        
        // Create markers for valid tack points (medium yellow circles)
        if (trackData.wind_analysis.valid_tack_points) {
            trackData.wind_analysis.valid_tack_points.forEach(idx => {
                if (idx < trackData.points.length) {
                    const point = trackData.points[idx];
                    L.circleMarker([point.lat, point.lon], {
                        radius: 4,
                        color: 'yellow',
                        fillColor: 'yellow',
                        fillOpacity: 0.7
                    }).addTo(map).bindPopup(`Valid tack point at ${point.time}`);
                }
            });
        }
        
        // Create markers for used tack points (larger green circles)
        if (trackData.wind_analysis.used_tack_points) {
            trackData.wind_analysis.used_tack_points.forEach(idx => {
                if (idx < trackData.points.length) {
                    const point = trackData.points[idx];
                    L.circleMarker([point.lat, point.lon], {
                        radius: 5,
                        color: 'green',
                        fillColor: 'green',
                        fillOpacity: 0.8
                    }).addTo(map).bindPopup(`Tack point used for wind estimation at ${point.time}`);
                }
            });
        }
    }
    
    // Display buoys and course markers if available
    if (trackData.buoys && trackData.buoys.length > 0) {
        // Create a buoy icon
        const buoyIcon = L.divIcon({
            html: `<div style="
                width: 20px; 
                height: 20px; 
                background-color: red; 
                border: 2px solid white; 
                border-radius: 50%; 
                box-shadow: 0 0 5px rgba(0,0,0,0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: bold;
                font-size: 12px;
            ">B</div>`,
            className: '',
            iconSize: [20, 20],
            iconAnchor: [10, 10]
        });
        
        // Process each course marker based on its type
        trackData.buoys.forEach((marker, index) => {
            const markerName = marker.name || `Marker ${index + 1}`;
            
            // Handle different marker types
            if (!marker.type || marker.type === 'marker') {
                // Single point marker (buoy)
                L.marker([marker.lat, marker.lon], {icon: buoyIcon})
                    .addTo(map)
                    .bindPopup(`<b>${markerName}</b><br>Lat: ${marker.lat.toFixed(6)}<br>Lon: ${marker.lon.toFixed(6)}`);
            } 
            else if (marker.type === 'line' && marker.points && marker.points.length >= 2) {
                // Line with multiple points (like start/finish line)
                const lineColor = marker.color || '#FF0000';
                const lineWidth = marker.width || 3;
                const linePoints = marker.points.map(p => [p.lat, p.lon]);
                
                const line = L.polyline(linePoints, {
                    color: lineColor,
                    weight: lineWidth,
                    opacity: 0.8
                }).addTo(map);
                
                // Calculate line distance
                let lineDistance = 0;
                for (let i = 0; i < linePoints.length - 1; i++) {
                    const p1 = L.latLng(linePoints[i]);
                    const p2 = L.latLng(linePoints[i + 1]);
                    lineDistance += p1.distanceTo(p2);
                }
                
                // Add popup with line information
                line.bindPopup(`<b>${markerName}</b><br>Length: ${(lineDistance / 1000).toFixed(3)} km`);
                
                // Add small markers at line endpoints if needed
                if (marker.showEndpoints !== false) {
                    const endpointIcon = L.divIcon({
                        html: `<div style="width: 8px; height: 8px; background-color: ${lineColor}; border: 1px solid white; border-radius: 50%;"></div>`,
                        className: '',
                        iconSize: [8, 8],
                        iconAnchor: [4, 4]
                    });
                    
                    // Add markers at start and end points
                    L.marker(linePoints[0], {icon: endpointIcon}).addTo(map);
                    L.marker(linePoints[linePoints.length - 1], {icon: endpointIcon}).addTo(map);
                }
            }
            else if (marker.type === 'polygon' && marker.points && marker.points.length >= 3) {
                // Polygon (like course boundary)
                const polygonColor = marker.color || '#0000FF';
                const polygonWidth = marker.width || 2;
                const polygonPoints = marker.points.map(p => [p.lat, p.lon]);
                
                // Create polygon with optional fill
                const polygon = L.polygon(polygonPoints, {
                    color: polygonColor,
                    weight: polygonWidth,
                    opacity: 0.8,
                    fillColor: marker.fillColor || polygonColor,
                    fillOpacity: marker.fill ? (marker.fillOpacity || 0.1) : 0
                }).addTo(map);
                
                // Add popup with polygon information
                polygon.bindPopup(`<b>${markerName}</b>`);
            }
        });
    }
    
    // Add track info control
    const info = L.control();
    
    info.onAdd = function(map) {
        const div = L.DomUtil.create('div', 'info');
        div.innerHTML = '<h4>Track Information</h4>' +
            `<div><b>Distance:</b> ${trackMetrics.totalDistance.toFixed(2)} km</div>` +
            `<div><b>Duration:</b> ${trackMetrics.totalDuration.toFixed(2)} min</div>` +
            `<div><b>Avg Speed:</b> ${trackMetrics.avgSpeed.toFixed(2)} knots</div>` +
            `<div><b>Min Speed:</b> ${trackMetrics.minSpeed.toFixed(2)} knots</div>` +
            `<div><b>Max Speed:</b> ${trackMetrics.maxSpeed.toFixed(2)} knots</div>`;
        return div;
    };
    
    info.addTo(map);
    
    // Add legend control
    const legend = L.control({position: 'bottomright'});
    
    legend.onAdd = function(map) {
        const div = L.DomUtil.create('div', 'info legend');
        
        // Add segment type legend
        div.innerHTML = '<h4>Segment Types</h4>';
        
        // Add legend for segment types
        div.innerHTML += '<div><i style="background:rgb(255,0,0)"></i> Turn (even)</div>';
        div.innerHTML += '<div><i style="background:rgb(255,100,0)"></i> Turn (odd)</div>';
        
        // Add speed category legend
        div.innerHTML += '<hr><h4>Speed Categories (Straight Segments)</h4>';
        
        // Add legend for speed categories with paired colors
        div.innerHTML += '<div><i style="background:rgb(80,200,80)"></i> Slow (even) < 4 knots</div>';
        div.innerHTML += '<div><i style="background:rgb(220,220,60)"></i> Slow (odd) < 4 knots</div>';
        div.innerHTML += '<div><i style="background:rgb(60,80,220)"></i> Medium (even) 4-6 knots</div>';
        div.innerHTML += '<div><i style="background:rgb(180,60,220)"></i> Medium (odd) 4-6 knots</div>';
        div.innerHTML += '<div><i style="background:rgb(220,60,60)"></i> Fast (even) > 6 knots</div>';
        div.innerHTML += '<div><i style="background:rgb(240,140,40)"></i> Fast (odd) > 6 knots</div>';
        
        // Add trend line legend
        div.innerHTML += '<hr><h4>Trend Lines</h4>';
        div.innerHTML += '<div><i style="background:black; height:2px; margin-top:8px; opacity:0.7"></i> Overall segment</div>';
        div.innerHTML += '<div><i style="background:blue; height:2px; margin-top:8px; opacity:0.7"></i> First 10 seconds</div>';
        div.innerHTML += '<div><i style="background:red; height:2px; margin-top:8px; opacity:0.7"></i> Last 10 seconds</div>';
        
        // Add tack points legend
        div.innerHTML += '<hr><h4>Tack Points</h4>';
        div.innerHTML += '<div><i style="background:gray; width:6px; height:6px; border-radius:50%; display:inline-block"></i> Potential Tack</div>';
        div.innerHTML += '<div><i style="background:yellow; width:8px; height:8px; border-radius:50%; display:inline-block"></i> Valid Tack (>10s)</div>';
        div.innerHTML += '<div><i style="background:green; width:10px; height:10px; border-radius:50%; display:inline-block"></i> Used for Wind Direction</div>';
        
        // Add course markers legend if present
        if (trackData.buoys && trackData.buoys.length > 0) {
            div.innerHTML += '<hr><h4>Course Markers</h4>';
            
            // Check for marker types present in the data
            const hasMarkers = trackData.buoys.some(b => !b.type || b.type === 'marker');
            const hasLines = trackData.buoys.some(b => b.type === 'line');
            const hasPolygons = trackData.buoys.some(b => b.type === 'polygon');
            
            // Add legend items for each type present
            if (hasMarkers) {
                div.innerHTML += '<div><i style="background:red; width:10px; height:10px; border-radius:50%; border:1px solid white; display:inline-block; color:white; text-align:center; font-weight:bold; font-size:8px;">B</i> Buoy</div>';
            }
            
            if (hasLines) {
                div.innerHTML += '<div><i style="background:red; width:15px; height:3px; display:inline-block;"></i> Line</div>';
            }
            
            if (hasPolygons) {
                div.innerHTML += '<div><i style="background:rgba(0,0,255,0.1); border:2px solid blue; width:15px; height:10px; display:inline-block;"></i> Area</div>';
            }
        }
        
        // Add segment count info
        div.innerHTML += '<hr><h4>Segment Stats</h4>';
        
        // Count segments by type
        const typeCounts = {
            turn: trackData.segments.filter(s => s.segment_type === 'turn').length,
            straight: trackData.segments.filter(s => s.segment_type === 'straight').length
        };
        
        div.innerHTML += '<div><b>By Type:</b></div>';
        div.innerHTML += '<div>Turn: ' + typeCounts.turn + '</div>';
        div.innerHTML += '<div>Straight: ' + typeCounts.straight + '</div>';
        
        // Count segments by speed category
        const speedCounts = {
            slow: trackData.segments.filter(s => s.metrics.speed_category === 'slow').length,
            medium: trackData.segments.filter(s => s.metrics.speed_category === 'medium').length,
            fast: trackData.segments.filter(s => s.metrics.speed_category === 'fast').length
        };
        
        div.innerHTML += '<div><b>By Speed:</b></div>';
        div.innerHTML += '<div>Slow: ' + speedCounts.slow + '</div>';
        div.innerHTML += '<div>Medium: ' + speedCounts.medium + '</div>';
        div.innerHTML += '<div>Fast: ' + speedCounts.fast + '</div>';
        div.innerHTML += '<b>Total: ' + trackData.length + '</b>';
        
        // Add tack distribution if wind direction is available
        if (trackData.length > 0 && trackData[0].metrics.wind_direction !== undefined) {
            const tackCounts = {
                port: trackData.filter(s => s.metrics.dominant_tack === 'port').length,
                starboard: trackData.filter(s => s.metrics.dominant_tack === 'starboard').length,
                mixed: trackData.filter(s => s.metrics.dominant_tack === 'mixed').length
            };
            
            div.innerHTML += '<hr><h4>Tack Distribution</h4>';
            div.innerHTML += '<div>Port: ' + tackCounts.port + '</div>';
            div.innerHTML += '<div>Starboard: ' + tackCounts.starboard + '</div>';
            if (tackCounts.mixed > 0) {
                div.innerHTML += '<div>Mixed: ' + tackCounts.mixed + '</div>';
            }
            
            // Add point of sail distribution
            const pointOfSailCounts = {
                'Turning': trackData.filter(s => s.metrics.point_of_sail === 'Turning').length,
                'Close Hauled': trackData.filter(s => s.metrics.point_of_sail === 'Close Hauled').length,
                'Close Reach': trackData.filter(s => s.metrics.point_of_sail === 'Close Reach').length,
                'Beam Reach': trackData.filter(s => s.metrics.point_of_sail === 'Beam Reach').length,
                'Broad Reach': trackData.filter(s => s.metrics.point_of_sail === 'Broad Reach').length,
                'Run': trackData.filter(s => s.metrics.point_of_sail === 'Run').length,
                'Unknown': trackData.filter(s => s.metrics.point_of_sail === 'Unknown').length
            };
            
            div.innerHTML += '<hr><h4>Points of Sail</h4>';
            for (const [sail, count] of Object.entries(pointOfSailCounts)) {
                if (count > 0) {
                    div.innerHTML += `<div>${sail}: ${count}</div>`;
                }
            }
        }
        
        return div;
    };
    
    legend.addTo(map);
</script>
</body>
</html>""")
    
    # Combine all HTML parts
    html_content = ''.join(html_parts)
    
    # Write HTML file
    with open(output_file, 'w') as f:
        f.write(html_content)
    
    print(f"HTML visualization saved to: {output_file}")
    return output_file


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_track_html.py <gpx_file> [bearing_threshold] [start_segment] [end_segment] [output_file] [buoys_file] [wind_direction]")
        sys.exit(1)
    
    # Get the project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Handle input file path - check if it's a relative path or just a filename
    gpx_file = sys.argv[1]
    if not os.path.isabs(gpx_file):
        # If not an absolute path, assume it's in the data directory
        if not os.path.exists(gpx_file):
            gpx_file = os.path.join(project_root, 'data', gpx_file)
    
    # Check if the file exists
    if not os.path.exists(gpx_file):
        print(f"Error: GPX file not found: {gpx_file}")
        sys.exit(1)
    
    bearing_threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 60
    
    # Handle start_segment parameter
    start_segment = None
    if len(sys.argv) > 3 and sys.argv[3] != "None":
        start_segment = int(sys.argv[3])
    
    # Handle end_segment parameter
    end_segment = None
    if len(sys.argv) > 4 and sys.argv[4] != "None":
        end_segment = int(sys.argv[4])
    
    # Handle output file path
    output_file = None
    if len(sys.argv) > 5 and sys.argv[5] != "None":
        output_file = sys.argv[5]
        if not os.path.isabs(output_file):
            # If not an absolute path, put it in the output directory
            output_file = os.path.join(project_root, 'output', output_file)
    
    buoys_file = None
    if len(sys.argv) > 6 and sys.argv[6] != "None":
        buoys_file = sys.argv[6]
    buoys = load_buoys(buoys_file) if buoys_file else []
    
    # Handle wind direction parameter
    wind_direction = None
    if len(sys.argv) > 7 and sys.argv[7] != "None":
        try:
            wind_direction = float(sys.argv[7])
            print(f"Using provided wind direction: {wind_direction}°")
        except ValueError:
            print(f"Warning: Invalid wind direction '{sys.argv[7]}', will estimate from track data")
    
    generate_html_visualization(gpx_file, bearing_threshold, start_segment, end_segment, output_file, buoys, wind_direction)

if __name__ == "__main__":
    main()
