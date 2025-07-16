import xml.etree.ElementTree as ET
from datetime import datetime
import os
import sys
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple

# Add project root to path to allow imports from src directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.geo_utils import trackpoint_calculations, is_similar_bearing, calculate_bearing, angle_diff
import numpy as np

@dataclass
class TrackPoint:
    """Class for storing trackpoint data"""
    lat: float
    lon: float
    time: datetime
    elevation: Optional[float] = None
    
    def __str__(self):
        return f"TrackPoint(lat={self.lat}, lon={self.lon}, time={self.time.isoformat()})"

def parse_gpx(gpx_file_path):
    """
    Parse a GPX file and extract trackpoints.
    
    Args:
        gpx_file_path: Path to the GPX file
    
    Returns:
        list: List of TrackPoint objects
    """
    # Check if file exists
    if not os.path.exists(gpx_file_path):
        raise FileNotFoundError(f"GPX file not found: {gpx_file_path}")
    
    # Parse the GPX file
    tree = ET.parse(gpx_file_path)
    root = tree.getroot()
    
    # Define namespace
    ns = {'gpx': 'http://www.topografix.com/GPX/1/1'}
    
    # Extract trackpoints
    trackpoints = []
    
    # Find all trackpoints in the GPX file
    for trkpt in root.findall('.//gpx:trkpt', ns):
        lat = float(trkpt.get('lat'))
        lon = float(trkpt.get('lon'))
        
        # Get time
        time_elem = trkpt.find('gpx:time', ns)
        if time_elem is not None and time_elem.text:
            time_str = time_elem.text
            # Parse ISO format datetime
            time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        else:
            continue  # Skip trackpoints without time
        
        # Get elevation if available
        ele_elem = trkpt.find('gpx:ele', ns)
        elevation = float(ele_elem.text) if ele_elem is not None and ele_elem.text else None
        
        # Create TrackPoint object and add to list
        trackpoint = TrackPoint(lat=lat, lon=lon, time=time, elevation=elevation)
        trackpoints.append(trackpoint)
    
    return trackpoints

def detect_tack_segments(trackpoints, angle_threshold=60, time_threshold=15):
    """
    Detect tack segments in a track based on significant course changes within a time window.
    A tack segment is a series of trackpoints where a significant course change occurs.
    
    Args:
        trackpoints: List of TrackPoint objects
        angle_threshold: Minimum course change to consider as a tack (degrees)
        time_threshold: Maximum time window for a tack change (seconds)
    
    Returns:
        list: List of tack segments, each containing:
            - start_index: Index of the first trackpoint in the tack
            - end_index: Index of the last trackpoint in the tack
            - course_change: Total course change during the tack (degrees)
            - start_course: Course at the start of the tack (degrees)
            - end_course: Course at the end of the tack (degrees)
    """
    tack_segments = []
    
    # Need at least 3 trackpoints to detect tacks
    if len(trackpoints) < 3:
        return tack_segments
    
    # Calculate courses between consecutive points
    courses = []
    for i in range(len(trackpoints) - 1):
        tp1 = trackpoints[i]
        tp2 = trackpoints[i + 1]
        bearing = calculate_bearing(tp1.lat, tp1.lon, tp2.lat, tp2.lon)
        courses.append(bearing)
    
    # Detect tack segments
    i = 0
    while i < len(courses) - 1:
        # Look for the start of a significant course change (half the threshold)
        if abs(angle_diff(courses[i], courses[i+1])) > angle_threshold / 6:
            tack_start_index = i
            start_course = courses[i]
            max_course_change = 0
            current_course_change = 0
            tack_end_index = i
            
            # Find the end of the tack segment
            j = i + 1
            while j < len(courses):
                # Calculate course change from the start of the tack
                course_change = abs(angle_diff(start_course, courses[j]))
                current_course_change = max(current_course_change, course_change)
                
                # Check if we've reached the time threshold
                time_diff = (trackpoints[j+1].time - trackpoints[tack_start_index].time).total_seconds()
                if time_diff > time_threshold:
                    break
                
                # Check if the course has stabilized (small changes)
                if j > i + 1 and abs(angle_diff(courses[j-1], courses[j])) < 5:
                    # If we've had a significant course change, end the tack
                    if current_course_change >= angle_threshold:
                        tack_end_index = j
                        max_course_change = current_course_change
                        break
                
                j += 1
            
            # If we found a significant tack, record it
            if current_course_change >= angle_threshold:
                tack_segments.append({
                    'start_index': tack_start_index,
                    'end_index': tack_end_index + 1,  # +1 because courses[i] is between points i and i+1
                    'course_change': max_course_change,
                    'start_course': start_course,
                    'end_course': courses[tack_end_index]
                })
                i = tack_end_index + 1  # Skip to after this tack
                continue
        
        i += 1
    
    return tack_segments

def create_segments_from_tacks(trackpoints, tack_segments):
    """
    Create segments based on tack changes:
    1. Segments from the end of one turn to the start of the next turn (straight sailing)
    2. Turn segments (the actual tack changes)
    
    Args:
        trackpoints: List of TrackPoint objects
        tack_segments: List of tack segments detected by detect_tack_segments
    
    Returns:
        tuple: (segments, segment_types) where segments is a list of trackpoint lists,
               and segment_types is a list of corresponding segment types ('turn' or 'straight')
    """
    if not tack_segments:
        # If no tack segments detected, return a single segment with all trackpoints
        return [trackpoints], ['straight']
    
    segments = []
    segment_types = []
    
    # Sort tack segments by start_index
    sorted_tacks = sorted(tack_segments, key=lambda x: x['start_index'])
    
    # Add initial straight segment if there's a gap before the first tack
    if sorted_tacks[0]['start_index'] > 0:
        # Include the first point of the first tack to ensure connection
        initial_segment = trackpoints[0:sorted_tacks[0]['start_index'] + 1]
        segments.append(initial_segment)
        segment_types.append('straight')
    
    # Process each tack segment
    for i, tack in enumerate(sorted_tacks):
        # Add the turn segment
        turn_segment = trackpoints[tack['start_index']:tack['end_index'] + 1]
        segments.append(turn_segment)
        segment_types.append('turn')
        
        # If there's a next tack, add a straight segment between this tack and the next
        if i < len(sorted_tacks) - 1:
            next_tack = sorted_tacks[i + 1]
            if tack['end_index'] < next_tack['start_index'] - 1:
                # Include the last point of the current tack and first point of the next tack
                # to ensure segments are connected
                straight_segment = trackpoints[tack['end_index']:next_tack['start_index'] + 1]
                segments.append(straight_segment)
                segment_types.append('straight')
    
    # Add final straight segment if there's a gap after the last tack
    if sorted_tacks[-1]['end_index'] < len(trackpoints) - 1:
        # Start from the last point of the last tack to ensure connection
        final_segment = trackpoints[sorted_tacks[-1]['end_index']:]
        segments.append(final_segment)
        segment_types.append('straight')
    
    return segments, segment_types

def detect_segments(trackpoints, bearing_threshold=20):
    """
    Detect segments in a track based on tack changes and straight sailing.
    
    Args:
        trackpoints: List of TrackPoint objects
        bearing_threshold: Threshold for bearing change to detect segments
    
    Returns:
        tuple: (segments, segment_types) where segments is a list of trackpoint lists,
               and segment_types is a list of corresponding segment types ('turn' or 'straight')
    """
    # First try to detect tack segments
    tack_segments = detect_tack_segments(trackpoints, angle_threshold=60, time_threshold=45)
    
    # If tack segments were found, create segments from them
    if tack_segments:
        print(f"Detected {len(tack_segments)} tack segments")
        print("Creating segments from tack changes...")
        return create_segments_from_tacks(trackpoints, tack_segments)
    
    # Fall back to original bearing-based segmentation if no tacks detected
    print("No tack segments detected, falling back to bearing-based segmentation")
    
    # Need at least 2 trackpoints to detect segments
    if len(trackpoints) < 2:
        return [trackpoints], ['straight']
    
    segments = []
    current_segment = [trackpoints[0]]
    
    # Group trackpoints with similar bearing into segments
    for i in range(len(trackpoints) - 1):
        tp1 = trackpoints[i]
        tp2 = trackpoints[i + 1]
        
        # Calculate bearing between consecutive points
        bearing = calculate_bearing(tp1.lat, tp1.lon, tp2.lat, tp2.lon)
        
        # If this is the first point, set the segment bearing
        if len(current_segment) == 1:
            segment_bearing = bearing
        
        # Check if the bearing is similar to the segment bearing
        bearing_diff = abs(angle_diff(bearing, segment_bearing))
        
        # Debug output for large bearing changes
        if bearing_diff > 30:
            print(f"Bearing change: {angle_diff(bearing, segment_bearing):.1f}° at point {i+1}")
        
        if bearing_diff <= bearing_threshold:
            # Add the point to the current segment
            current_segment.append(tp2)
        else:
            # Start a new segment
            print(f"Creating new segment due to bearing change of {angle_diff(bearing, segment_bearing):.1f}°")
            segments.append(current_segment)
            current_segment = [tp2]
            segment_bearing = bearing
    
    # Add the last segment if it's not empty
    if current_segment:
        segments.append(current_segment)
    
    # All segments from bearing-based segmentation are considered 'straight'
    segment_types = ['straight'] * len(segments)
    
    return segments, segment_types

def analyze_wind_direction(trackpoints, window_size=5, min_turn_duration=10, exclude_edges=True, force_wind_direction=None):
    """
    Analyze track to estimate wind direction based on tacking patterns.
    Filters out short turns and optionally excludes first and last turns for more accurate estimation.
    
    Args:
        trackpoints: List of TrackPoint objects
        window_size: Size of the window for smoothing course data
        min_turn_duration: Minimum duration in seconds for a turn to be considered valid
        exclude_edges: Whether to exclude the first and last turns from wind direction calculation
        force_wind_direction: If provided, use this wind direction instead of calculating it
    
    Returns:
        tuple: (estimated_wind_direction, tack_assignments, analysis_data)
            - estimated_wind_direction: Wind direction in degrees (0-360)
            - tack_assignments: List of tack assignments ('port', 'starboard', or None) for each trackpoint
            - analysis_data: Dictionary with additional analysis information
    """
    # Need at least window_size+1 trackpoints to analyze
    if len(trackpoints) < window_size + 1:
        return None, [None] * len(trackpoints), {}
        
    # Initialize variables
    estimated_wind_direction = force_wind_direction  # Use forced direction if provided
    tack_assignments = [None] * len(trackpoints)
    
    # Initialize analysis data dictionary
    analysis_data = {}
    
    # 1. Compute the course between each pair of points
    courses = []
    for i in range(len(trackpoints) - 1):
        tp1 = trackpoints[i]
        tp2 = trackpoints[i + 1]
        bearing = calculate_bearing(tp1.lat, tp1.lon, tp2.lat, tp2.lon)
        courses.append(bearing)
    
    # Add a final course (duplicate of last one) to match the number of trackpoints
    courses.append(courses[-1] if courses else 0)
    
    # 2. Smooth the course data using a moving average
    smoothed_courses = []
    
    # For the first points where we don't have a full window
    for i in range(window_size // 2):
        # For the very beginning, just use the first course
        smoothed_courses.append(courses[0])
    
    # Apply moving average for the middle points
    for i in range(window_size // 2, len(courses) - window_size // 2):
        window = courses[i - window_size // 2:i + window_size // 2 + 1]
        # Convert to complex numbers to handle circular averaging correctly
        complex_avg = np.mean([np.exp(1j * np.radians(c)) for c in window])
        avg_angle = np.degrees(np.angle(complex_avg)) % 360
        smoothed_courses.append(avg_angle)
    
    # For the last points where we don't have a full window
    for i in range(len(courses) - window_size // 2, len(courses)):
        # For the very end, just use the last course
        smoothed_courses.append(courses[-1])
    
    # 3. Detect tacking pattern and calculate wind direction if not forced
    potential_tack_points = []
    valid_tack_points = []
    tack_points = []
    tack_durations = []
    
    # Calculate course changes between consecutive smoothed courses
    course_changes = []
    for i in range(1, len(smoothed_courses)):
        change = abs(angle_diff(smoothed_courses[i], smoothed_courses[i-1]))
        course_changes.append(change)
    
    # Add a zero at the beginning to match the number of trackpoints
    course_changes.insert(0, 0)
    
    # Only perform tack detection and wind direction estimation if we don't have a forced wind direction
    if force_wind_direction is None:
        # Identify significant course changes (potential tacks)
        tack_threshold = 60  # Minimum angle change to consider as a tack
        potential_tack_points = [i for i, change in enumerate(course_changes) if change > tack_threshold]
        
        # Filter out short turns by checking their duration
        for i, tack_idx in enumerate(potential_tack_points):
            # Skip if this is the last potential tack point
            if i == len(potential_tack_points) - 1:
                continue
                
            # Calculate the duration of this turn
            next_tack_idx = potential_tack_points[i + 1]
            if next_tack_idx < len(trackpoints) and tack_idx < len(trackpoints):
                if trackpoints[next_tack_idx].time and trackpoints[tack_idx].time:  # Make sure time data is available
                    turn_duration = (trackpoints[next_tack_idx].time - trackpoints[tack_idx].time).total_seconds()
                    tack_durations.append(turn_duration)
                    
                    # Only include turns that are long enough
                    if turn_duration >= min_turn_duration:
                        valid_tack_points.append(tack_idx)
        
        # Exclude first and last turns if requested and if we have enough turns
        tack_points = valid_tack_points
        if exclude_edges and len(valid_tack_points) >= 4:  # Need at least 4 to exclude 2
            tack_points = valid_tack_points[1:-1]  # Exclude first and last
        
        # 4. Estimate wind direction if we have enough tack points
        if len(tack_points) >= 2:  # We need at least two tacks to estimate
            # Extract courses at tack points
            tack_courses = [smoothed_courses[i] for i in tack_points]
            
            # Group similar courses (within 30 degrees) to identify the two main tacking directions
            course_groups = []
            for course in tack_courses:
                added = False
                for group in course_groups:
                    if is_similar_bearing(course, np.mean(group), 30):
                        group.append(course)
                        added = True
                        break
                if not added:
                    course_groups.append([course])
            
            # If we have at least 2 distinct course groups, we can estimate wind direction
            if len(course_groups) >= 2:
                # Sort groups by size and take the two largest
                course_groups.sort(key=len, reverse=True)
                main_groups = course_groups[:2]
                
                # Calculate average course for each main group
                avg_courses = []
                for group in main_groups:
                    # Convert to complex numbers to handle circular averaging correctly
                    complex_avg = np.mean([np.exp(1j * np.radians(c)) for c in group])
                    avg_angle = np.degrees(np.angle(complex_avg)) % 360
                    avg_courses.append(avg_angle)
                
                # Calculate the average tacking axis (bisector of the two main courses)
                # We need to handle the case where the courses are across the 0/360 boundary
                diff = abs(angle_diff(avg_courses[0], avg_courses[1]))
                if diff > 180:
                    # If the difference is more than 180, we need to adjust one of the angles
                    if avg_courses[0] < avg_courses[1]:
                        avg_courses[0] += 360
                    else:
                        avg_courses[1] += 360
                
                tacking_axis = np.mean(avg_courses) % 360
                
                # Wind direction is opposite to the tacking axis
                estimated_wind_direction = (tacking_axis + 180) % 360
                
                # Add more analysis data
                analysis_data.update({
                    'course_groups': course_groups,
                    'main_groups': main_groups,
                    'avg_courses': avg_courses,
                    'tacking_axis': tacking_axis,
                    'estimation_method': 'tacking_pattern'
                })
            else:
                # If we don't have distinct course groups, use the dominant heading
                dominant_course = np.median(smoothed_courses) % 360
                estimated_wind_direction = (dominant_course + 180) % 360
                analysis_data['estimation_method'] = 'dominant_course'
        else:
            # If we don't have enough tack points, use the median course as a fallback
            if smoothed_courses:
                dominant_course = np.median(smoothed_courses) % 360
                estimated_wind_direction = (dominant_course + 180) % 360
                analysis_data['estimation_method'] = 'fallback_median'
                analysis_data['dominant_course'] = dominant_course
    else:
        # If we're using a forced wind direction, mark it in the analysis data
        analysis_data['estimation_method'] = 'forced'
        analysis_data['forced_wind_direction'] = force_wind_direction
    
    # 5. Determine tack for each point (this happens regardless of whether wind direction was forced or calculated)
    
    # 5. Determine tack for each point
    if estimated_wind_direction is not None:
        for i, course in enumerate(smoothed_courses):
            relative_angle = (estimated_wind_direction - course + 360) % 360
            if relative_angle < 180:
                tack_assignments[i] = 'port'  # Wind on the left
            else:
                tack_assignments[i] = 'starboard'  # Wind on the right
    
    # Update analysis data for visualization or further processing
    analysis_data.update({
        'courses': courses,
        'smoothed_courses': smoothed_courses,
        'course_changes': course_changes,
        'potential_tack_points': potential_tack_points,
        'used_tack_points': tack_points if tack_points else [],
        'tack_durations': []
    })
    
    # If we're using a forced wind direction, mark it in the analysis data
    if force_wind_direction is not None:
        analysis_data['estimation_method'] = 'forced'
        analysis_data['forced_wind_direction'] = force_wind_direction
    
    return estimated_wind_direction, tack_assignments, analysis_data

def analyze_track(trackpoints):
    """
    Analyze a track by calculating metrics between consecutive trackpoints.
    
    Args:
        trackpoints: List of TrackPoint objects
    
    Returns:
        list: List of dictionaries with calculations between points
    """
    # Need at least 2 trackpoints to analyze
    if len(trackpoints) < 2:
        return []
    
    # Calculate metrics between consecutive trackpoints
    metrics = []
    for i in range(len(trackpoints) - 1):
        tp1 = trackpoints[i]
        tp2 = trackpoints[i + 1]
        
        # Calculate distance, direction, and speed
        point_metrics = trackpoint_calculations(tp1, tp2)
        
        # Add trackpoint indices for reference
        point_metrics['point_index'] = i
        point_metrics['start_point'] = tp1
        point_metrics['end_point'] = tp2
        
        metrics.append(point_metrics)
    
    return metrics

def analyze_segments(segments, segment_types=None):
    """
    Analyze segments by calculating metrics for each segment.
    
    Args:
        segments: List of segments, each containing a list of trackpoints
        segment_types: Optional list of segment types ('turn' or 'straight') for each segment
    
    Returns:
        list: List of dictionaries with segment metrics
    """
    segment_metrics = []
    
    # If segment_types is not provided, assume all segments are 'straight'
    if segment_types is None:
        segment_types = ['straight'] * len(segments)
    
    for i, segment in enumerate(segments):
        # Need at least 2 trackpoints in a segment for analysis
        if len(segment) < 2:
            continue
        
        # Calculate metrics for the segment
        first_point = segment[0]
        last_point = segment[-1]
        
        # Calculate overall bearing for the segment (start to end)
        overall_bearing = calculate_bearing(
            first_point.lat, first_point.lon,
            last_point.lat, last_point.lon
        )
        
        # Calculate total distance and time for the segment
        total_distance = 0
        total_time = (last_point.time - first_point.time).total_seconds()
        
        # Calculate point-to-point metrics within the segment
        point_metrics = []
        for j in range(len(segment) - 1):
            tp1 = segment[j]
            tp2 = segment[j + 1]
            metrics = trackpoint_calculations(tp1, tp2)
            total_distance += metrics['distance_meters']
            point_metrics.append(metrics)
        
        # Calculate average speed for the segment
        avg_speed_ms = total_distance / total_time if total_time > 0 else 0
        avg_speed_knots = avg_speed_ms * 1.94384
        
        segment_metrics.append({
            'segment_index': i,
            'segment_type': segment_types[i] if i < len(segment_types) else 'straight',
            'num_points': len(segment),
            'start_time': first_point.time,
            'end_time': last_point.time,
            'duration_seconds': total_time,
            'total_distance_meters': total_distance,
            'overall_bearing': overall_bearing,
            'avg_speed_ms': avg_speed_ms,
            'avg_speed_knots': avg_speed_knots,
            'points': segment,
            'point_metrics': point_metrics
        })
    
    return segment_metrics

def main():
    """Main function to process a GPX file"""
    import sys
    
    # Check if file path is provided
    if len(sys.argv) < 2:
        print("Usage: python gpx_analyzer.py <gpx_file_path> [bearing_threshold]")
        return
    
    # Get the project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Handle input file path - check if it's a relative path or just a filename
    gpx_file_path = sys.argv[1]
    if not os.path.isabs(gpx_file_path):
        # If not an absolute path, assume it's in the data directory
        if not os.path.exists(gpx_file_path):
            gpx_file_path = os.path.join(project_root, 'data', gpx_file_path)
    
    # Check if the file exists
    if not os.path.exists(gpx_file_path):
        print(f"Error: GPX file not found: {gpx_file_path}")
        sys.exit(1)
    
    # Get bearing threshold from command line or use default
    bearing_threshold = 20
    if len(sys.argv) > 2:
        try:
            bearing_threshold = float(sys.argv[2])
        except ValueError:
            print(f"Warning: Invalid bearing threshold '{sys.argv[2]}', using default: {bearing_threshold}°")
    
    try:
        # Parse GPX file
        print(f"Parsing GPX file: {gpx_file_path}")
        trackpoints = parse_gpx(gpx_file_path)
        print(f"Found {len(trackpoints)} trackpoints")
        
        # First, analyze the track to estimate wind direction
        print("\nAnalyzing track to estimate wind direction...")
        wind_direction, tack_assignments, wind_analysis = analyze_wind_direction(trackpoints)
        
        if wind_direction is not None:
            print(f"Estimated wind direction: {wind_direction:.2f}° (coming from)")
            # Count tacks
            port_tacks = tack_assignments.count('port')
            starboard_tacks = tack_assignments.count('starboard')
            print(f"Tack distribution: {port_tacks} port tacks, {starboard_tacks} starboard tacks")
        else:
            print("Could not estimate wind direction from the track data")
        
        # Detect tack segments first
        print("\nDetecting tack segments...")
        tack_segments = detect_tack_segments(trackpoints, angle_threshold=60, time_threshold=15)
        print(f"Detected {len(tack_segments)} tack segments")
        
        # Then detect segments based on tack changes
        print(f"\nCreating segments from tack changes...")
        segments = create_segments_from_tacks(trackpoints, tack_segments)
        
        # Count segment types
        turn_segments = [s for i, s in enumerate(segments) if i < len(tack_segments) and i % 2 == 1]
        straight_segments = [s for i, s in enumerate(segments) if i >= len(tack_segments) or i % 2 == 0]
        print(f"Created {len(segments)} segments:")
        print(f"  - {len(turn_segments)} turn segments")
        print(f"  - {len(straight_segments)} straight segments")
        
        # Analyze segments
        segment_metrics = analyze_segments(segments, tack_segments, trackpoints)
        
        # Add wind direction and tack information to each segment
        if wind_direction is not None:
            for i, segment in enumerate(segment_metrics):
                # Get the indices of the first and last points in this segment
                first_idx = trackpoints.index(segment['points'][0])
                last_idx = trackpoints.index(segment['points'][-1])
                
                # Count tacks in this segment
                segment_tacks = tack_assignments[first_idx:last_idx+1]
                port_count = segment_tacks.count('port')
                starboard_count = segment_tacks.count('starboard')
                
                # Determine dominant tack for the segment
                if port_count > starboard_count:
                    dominant_tack = 'port'
                elif starboard_count > port_count:
                    dominant_tack = 'starboard'
                else:
                    dominant_tack = 'mixed'
                
                # Calculate relative angle to wind
                relative_wind_angle = (wind_direction - segment['overall_bearing'] + 360) % 360
                if relative_wind_angle > 180:
                    relative_wind_angle = 360 - relative_wind_angle
                
                # Add wind information to segment metrics
                segment_metrics[i]['wind_direction'] = wind_direction
                segment_metrics[i]['dominant_tack'] = dominant_tack
                segment_metrics[i]['relative_wind_angle'] = relative_wind_angle
        
        # Display segment results
        print("\nSegment Analysis:")
        print("----------------")
        
        total_distance = 0
        total_duration = 0
        
        for i, segment in enumerate(segment_metrics):
            total_distance += segment['total_distance_meters']
            total_duration += segment['duration_seconds']
            
            # Print segment information
            print(f"Segment {i+1} of {len(segment_metrics)}:")
            print(f"  Type: {segment['segment_type']}")
            print(f"  Points: {segment['num_points']}")
            print(f"  Start: {segment['start_time'].isoformat()}")
            print(f"  End: {segment['end_time'].isoformat()}")
            print(f"  Duration: {segment['duration_seconds']:.1f} seconds")
            print(f"  Distance: {segment['total_distance_meters']:.2f} m")
            print(f"  Direction: {segment['overall_bearing']:.2f}°")
            print(f"  Avg Speed: {segment['avg_speed_knots']:.2f} knots ({segment['avg_speed_ms']:.2f} m/s)")
            
            # Print wind information if available
            if wind_direction is not None and 'dominant_tack' in segment:
                print(f"  Wind: {segment['wind_direction']:.2f}° (relative angle: {segment['relative_wind_angle']:.2f}°)")
                print(f"  Dominant Tack: {segment['dominant_tack']}")
            
            print()
        
        # Print summary
        print("\nSummary:")
        print(f"Total segments: {len(segment_metrics)}")
        print(f"Total distance: {total_distance/1000:.2f} km")
        print(f"Total duration: {total_duration/60:.1f} minutes")
        print(f"Average speed: {(total_distance/1000) / (total_duration/3600):.2f} km/h")
        if wind_direction is not None:
            print(f"Estimated wind direction: {wind_direction:.2f}°")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
