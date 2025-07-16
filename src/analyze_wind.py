#!/usr/bin/env python3
"""
Wind Direction Analysis Script

This script analyzes GPX files to identify wind direction based on tacking patterns.
It uses the algorithm from gpx_analyzer.py but focuses solely on wind direction calculation.
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# Import required functions from existing modules
from gpx_analyzer import parse_gpx, analyze_wind_direction, calculate_bearing, is_similar_bearing

def detect_tack_segments(trackpoints, angle_threshold=60, time_threshold=15):
    """
    Detect segments where the boat changes tack, defined as a significant course change
    (more than angle_threshold degrees) within a short time period (time_threshold seconds).
    
    Args:
        trackpoints: List of TrackPoint objects
        angle_threshold: Minimum angle change to consider as a tack change (degrees)
        time_threshold: Maximum time window for the tack change to occur (seconds)
    
    Returns:
        list: List of tack segments, each containing:
            - start_index: Index of the first trackpoint in the tack change
            - end_index: Index of the last trackpoint in the tack change
            - start_time: Timestamp of the first trackpoint
            - end_time: Timestamp of the last trackpoint
            - duration: Duration of the tack change in seconds
            - start_course: Course before the tack change
            - end_course: Course after the tack change
            - course_change: Magnitude of the course change in degrees
    """
    tack_segments = []
    
    # Need at least 3 trackpoints to detect a tack change
    if len(trackpoints) < 3:
        return tack_segments
    
    # Calculate courses between consecutive points
    courses = []
    for i in range(len(trackpoints) - 1):
        tp1 = trackpoints[i]
        tp2 = trackpoints[i + 1]
        bearing = calculate_bearing(tp1.lat, tp1.lon, tp2.lat, tp2.lon)
        courses.append(bearing)
    
    # Add a final course (duplicate of last one) to match the number of trackpoints
    courses.append(courses[-1] if courses else 0)
    
    # Detect potential tack start points (where course starts changing significantly)
    potential_tacks = []
    
    for i in range(1, len(trackpoints) - 1):
        # Calculate course change
        prev_course = courses[i-1]
        current_course = courses[i]
        
        change = abs(current_course - prev_course)
        if change > 180:  # Handle the 0/360 boundary
            change = 360 - change
        
        # If course change exceeds threshold, mark as potential tack start
        if change > angle_threshold / 2:  # Use half the threshold to catch the beginning of changes
            potential_tacks.append(i)
    
    # Process potential tacks to identify complete tack segments
    i = 0
    while i < len(potential_tacks):
        start_idx = potential_tacks[i]
        start_time = trackpoints[start_idx].time
        start_course = courses[start_idx-1]  # Course before the change
        
        # Look ahead to find the end of this tack change
        end_idx = start_idx
        max_course_change = 0
        stabilized_course = None
        
        # Look ahead until course stabilizes or time threshold is exceeded
        for j in range(start_idx + 1, len(trackpoints)):
            # Check if we've exceeded the time threshold
            current_time = trackpoints[j].time
            elapsed_seconds = (current_time - start_time).total_seconds()
            
            if elapsed_seconds > time_threshold:
                break
            
            # Calculate course change from the starting course
            current_course = courses[j]
            change = abs(current_course - start_course)
            if change > 180:  # Handle the 0/360 boundary
                change = 360 - change
            
            # Track the maximum course change
            if change > max_course_change:
                max_course_change = change
                end_idx = j
            
            # Check if course has stabilized (small change between consecutive points)
            if j > start_idx + 1:
                consecutive_change = abs(current_course - courses[j-1])
                if consecutive_change > 180:  # Handle the 0/360 boundary
                    consecutive_change = 360 - consecutive_change
                
                if consecutive_change < 5:  # Course is considered stable if change is less than 5 degrees
                    stabilized_course = current_course
                    break
        
        # If we found a significant course change and the course stabilized
        if max_course_change > angle_threshold and stabilized_course is not None:
            end_time = trackpoints[end_idx].time
            duration = (end_time - start_time).total_seconds()
            
            tack_segments.append({
                'start_index': start_idx,
                'end_index': end_idx,
                'start_time': start_time,
                'end_time': end_time,
                'duration': duration,
                'start_course': start_course,
                'end_course': stabilized_course,
                'course_change': max_course_change
            })
            
            # Skip any potential tacks that are part of this segment
            while i < len(potential_tacks) and potential_tacks[i] <= end_idx:
                i += 1
        else:
            # This potential tack didn't result in a complete tack segment
            i += 1
    
    return tack_segments

def create_segments_from_tacks(trackpoints, tack_segments):
    """
    Create segments based on tack changes:
    1. Segments from the end of one turn to the start of the next turn (straight sailing)
    2. Turn segments (the actual tack changes)
    3. Line segments connecting turns
    
    Args:
        trackpoints: List of TrackPoint objects
        tack_segments: List of tack segments detected by detect_tack_segments
    
    Returns:
        list: List of segments, each containing:
            - type: 'straight', 'turn', or 'line'
            - start_index: Index of the first trackpoint in the segment
            - end_index: Index of the last trackpoint in the segment
            - trackpoints: List of trackpoints in the segment
    """
    if not tack_segments:
        # If no tack segments detected, return a single segment with all trackpoints
        return [{
            'type': 'straight',
            'start_index': 0,
            'end_index': len(trackpoints) - 1,
            'trackpoints': trackpoints
        }]
    
    segments = []
    
    # Sort tack segments by start_index
    sorted_tacks = sorted(tack_segments, key=lambda x: x['start_index'])
    
    # Add initial straight segment if there's a gap before the first tack
    if sorted_tacks[0]['start_index'] > 0:
        segments.append({
            'type': 'straight',
            'start_index': 0,
            'end_index': sorted_tacks[0]['start_index'] - 1,
            'trackpoints': trackpoints[0:sorted_tacks[0]['start_index']]
        })
    
    # Process each tack segment
    for i, tack in enumerate(sorted_tacks):
        # Add the turn segment
        segments.append({
            'type': 'turn',
            'start_index': tack['start_index'],
            'end_index': tack['end_index'],
            'trackpoints': trackpoints[tack['start_index']:tack['end_index']+1],
            'course_change': tack['course_change'],
            'start_course': tack['start_course'],
            'end_course': tack['end_course']
        })
        
        # If there's a next tack, add a straight segment between this tack and the next
        if i < len(sorted_tacks) - 1:
            next_tack = sorted_tacks[i + 1]
            if tack['end_index'] < next_tack['start_index'] - 1:
                segments.append({
                    'type': 'straight',
                    'start_index': tack['end_index'] + 1,
                    'end_index': next_tack['start_index'] - 1,
                    'trackpoints': trackpoints[tack['end_index']+1:next_tack['start_index']]
                })
    
    # Add final straight segment if there's a gap after the last tack
    if sorted_tacks[-1]['end_index'] < len(trackpoints) - 1:
        segments.append({
            'type': 'straight',
            'start_index': sorted_tacks[-1]['end_index'] + 1,
            'end_index': len(trackpoints) - 1,
            'trackpoints': trackpoints[sorted_tacks[-1]['end_index']+1:]
        })
    
    return segments

def analyze_gpx_wind(gpx_file_path, window_size=5, plot_results=False):
    """
    Analyze a GPX file to determine wind direction and tack patterns.
    
    Args:
        gpx_file_path: Path to the GPX file
        window_size: Size of the window for smoothing course data
        plot_results: Whether to generate plots of the analysis
    
    Returns:
        Dictionary with analysis results
    """
    print(f"Analyzing GPX file: {gpx_file_path}")
    
    # Parse the GPX file
    trackpoints = parse_gpx(gpx_file_path)
    print(f"Found {len(trackpoints)} trackpoints")
    
    # Detect tack segments using the new approach
    print("Detecting tack segments...")
    tack_segments = detect_tack_segments(trackpoints, angle_threshold=60, time_threshold=15)
    print(f"Detected {len(tack_segments)} tack segments")
    
    # Create segments based on tack changes
    print("Creating segments from tack changes...")
    segments = create_segments_from_tacks(trackpoints, tack_segments)
    print(f"Created {len(segments)} segments:")
    
    # Count segment types
    turn_segments = [s for s in segments if s['type'] == 'turn']
    straight_segments = [s for s in segments if s['type'] == 'straight']
    print(f"  - {len(turn_segments)} turn segments")
    print(f"  - {len(straight_segments)} straight segments")
    
    # If we have tack segments, use them to estimate wind direction
    estimated_wind_direction = None
    port_tacks = 0
    starboard_tacks = 0
    course_groups = []
    
    if len(tack_segments) >= 2:
        # Extract courses before and after each tack
        pre_tack_courses = [segment['start_course'] for segment in tack_segments]
        post_tack_courses = [segment['end_course'] for segment in tack_segments]
        
        # Group similar courses to identify the two main tacking directions
        all_courses = pre_tack_courses + post_tack_courses
        
        # Group similar courses (within 30 degrees)
        for course in all_courses:
            added = False
            for group in course_groups:
                if is_similar_bearing(course, np.mean(group), 30):
                    group.append(course)
                    added = True
                    break
            if not added:
                course_groups.append([course])
        
        # Sort groups by size and take the two largest
        if len(course_groups) >= 2:
            course_groups.sort(key=len, reverse=True)
            main_groups = course_groups[:2]
            
            # Calculate average course for each main group
            avg_courses = []
            for group in main_groups:
                # Convert to complex numbers to handle circular averaging correctly
                complex_avg = np.mean([np.exp(1j * np.radians(c)) for c in group])
                avg_angle = np.degrees(np.angle(complex_avg)) % 360
                avg_courses.append(avg_angle)
            
            # Calculate the tacking axis (average of the two main courses)
            diff = abs(avg_courses[0] - avg_courses[1])
            if diff > 180:
                # Handle the case where the average crosses the 0/360 boundary
                if avg_courses[0] < avg_courses[1]:
                    avg_courses[0] += 360
                else:
                    avg_courses[1] += 360
            
            tacking_axis = np.mean(avg_courses) % 360
            
            # Wind direction is perpendicular to the tacking axis
            # We need to determine which of the two perpendicular directions is correct
            wind_option1 = (tacking_axis + 90) % 360
            wind_option2 = (tacking_axis - 90) % 360
            
            # For now, we'll use a simple heuristic: choose the direction that's closer to north
            # This could be improved with more sophisticated analysis
            if abs(wind_option1 - 0) < abs(wind_option2 - 0):
                estimated_wind_direction = wind_option1
            else:
                estimated_wind_direction = wind_option2
            
            # Assign tacks based on the estimated wind direction
            tack_assignments = [None] * len(trackpoints)
            
            # Calculate courses between consecutive points
            courses = []
            for i in range(len(trackpoints) - 1):
                tp1 = trackpoints[i]
                tp2 = trackpoints[i + 1]
                bearing = calculate_bearing(tp1.lat, tp1.lon, tp2.lat, tp2.lon)
                courses.append(bearing)
            courses.append(courses[-1] if courses else 0)  # Add final course
            
            # Determine tack for each point based on its course relative to wind
            for i, course in enumerate(courses):
                # Calculate relative angle to wind
                rel_angle = (course - estimated_wind_direction) % 360
                
                # Assign tack based on relative angle
                if 0 <= rel_angle < 180:
                    tack_assignments[i] = 'starboard'
                    starboard_tacks += 1
                else:
                    tack_assignments[i] = 'port'
                    port_tacks += 1
    
    # If we couldn't estimate wind direction from tack segments, fall back to the original method
    if estimated_wind_direction is None:
        print("Falling back to original wind direction analysis method...")
        estimated_wind_direction, tack_assignments, analysis_data = analyze_wind_direction(trackpoints, window_size)
        
        # Count tacks from the original method
        port_tacks = tack_assignments.count('port')
        starboard_tacks = tack_assignments.count('starboard')
        
        # Extract course groups from the original method
        course_groups = analysis_data.get('course_groups', [])
    
    # Print results
    print(f"Estimated wind direction: {estimated_wind_direction:.2f}\u00b0 (coming from)")
    print(f"Tack distribution: {port_tacks} port tacks, {starboard_tacks} starboard tacks")
    print(f"Detected {len(tack_segments)} tack segments")
    
    if len(course_groups) >= 2:
        print(f"Main tacking directions: {np.mean(course_groups[0]):.2f}\u00b0 and {np.mean(course_groups[1]):.2f}\u00b0")
    
    # Store analysis results
    results = {
        'gpx_file': gpx_file_path,
        'num_trackpoints': len(trackpoints),
        'wind_direction': estimated_wind_direction,
        'port_tacks': port_tacks,
        'starboard_tacks': starboard_tacks,
        'tack_segments': tack_segments,
        'tack_segments_count': len(tack_segments),
        'course_groups': course_groups,
        'segments': segments,
        'segments_count': len(segments),
        'turn_segments': turn_segments,
        'straight_segments': straight_segments
    }
    
    # Add analysis_data if we used the fallback method
    if estimated_wind_direction is None:
        results['analysis_data'] = analysis_data
    
    # Generate plots if requested
    if plot_results and len(trackpoints) > 0:
        plot_wind_analysis(trackpoints, courses, tack_segments=tack_segments, wind_direction=estimated_wind_direction, tack_assignments=tack_assignments, output_dir='output')
    
    return results

def plot_wind_analysis(trackpoints, courses, smoothed_courses=None, course_changes=None, tack_segments=None, wind_direction=None, tack_assignments=None, output_dir='output'):
    """Generate plots to visualize the wind direction analysis"""
    
    # Create a figure with multiple subplots
    fig, axs = plt.subplots(2, 2, figsize=(15, 10))
    
    # Plot 1: Courses over time
    axs[0, 0].plot(courses, 'b-', alpha=0.5, label='Course')
    if smoothed_courses is not None:
        axs[0, 0].plot(smoothed_courses, 'r-', label='Smoothed Course')
    axs[0, 0].set_title('Course Over Time')
    axs[0, 0].set_ylabel('Course (degrees)')
    axs[0, 0].set_xlabel('Trackpoint Index')
    axs[0, 0].legend()
    axs[0, 0].grid(True)
    
    # Plot 2: Tack segments
    if course_changes is not None:
        axs[0, 1].plot(course_changes, 'g-', label='Course Changes')
    else:
        # Calculate course changes if not provided
        calculated_changes = [0]
        for i in range(1, len(courses)):
            change = abs(courses[i] - courses[i-1])
            if change > 180:  # Handle the 0/360 boundary
                change = 360 - change
            calculated_changes.append(change)
        axs[0, 1].plot(calculated_changes, 'g-', label='Course Changes')
    
    axs[0, 1].set_title('Course Changes and Tack Segments')
    axs[0, 1].set_ylabel('Change (degrees)')
    axs[0, 1].set_xlabel('Trackpoint Index')
    axs[0, 1].grid(True)
    
    # Mark tack segments on both plots
    if tack_segments:
        for segment in tack_segments:
            start_idx = segment['start_index']
            end_idx = segment['end_index']
            # Mark the start and end of each tack segment
            axs[0, 0].axvspan(start_idx, end_idx, color='yellow', alpha=0.3)
            axs[0, 1].axvspan(start_idx, end_idx, color='yellow', alpha=0.3)
            # Add text annotation for the course change
            mid_idx = (start_idx + end_idx) // 2
            axs[0, 1].text(mid_idx, 10, f"{segment['course_change']:.0f}°", 
                         fontsize=8, ha='center', va='bottom')
    
    # Plot 3: Track colored by tack
    lats = [tp.lat for tp in trackpoints]
    lons = [tp.lon for tp in trackpoints]
    
    # Create a scatter plot with points colored by tack
    if tack_assignments:
        colors = []
        for tack in tack_assignments:
            if tack == 'port':
                colors.append('red')
            elif tack == 'starboard':
                colors.append('green')
            else:
                colors.append('gray')
    else:
        # Default color if no tack assignments
        colors = ['blue'] * len(trackpoints)
    
    axs[1, 0].scatter(lons, lats, c=colors, s=2)
    axs[1, 0].set_title('Track Colored by Tack')
    axs[1, 0].set_xlabel('Longitude')
    axs[1, 0].set_ylabel('Latitude')
    axs[1, 0].grid(True)
    
    # Add a wind direction arrow
    if wind_direction is not None:
        # Calculate the center of the track
        center_lat = np.mean(lats)
        center_lon = np.mean(lons)
        
        # Convert wind direction to radians (wind direction is where wind is coming FROM)
        wind_rad = np.radians(wind_direction)
        
        # Calculate arrow endpoint (arrow points in the direction the wind is blowing TO)
        # We need to reverse the direction since wind_direction is where wind is coming FROM
        arrow_length = 0.01  # Adjust based on your coordinate scale
        dx = arrow_length * np.sin(wind_rad + np.pi)  # Add pi to reverse direction
        dy = arrow_length * np.cos(wind_rad + np.pi)  # Add pi to reverse direction
        
        # Draw the arrow
        axs[1, 0].arrow(center_lon, center_lat, dx, dy, head_width=arrow_length/3, 
                      head_length=arrow_length/2, fc='blue', ec='blue', width=arrow_length/10)
        
        # Add a legend for the arrow
        axs[1, 0].text(center_lon + dx*1.2, center_lat + dy*1.2, 
                     f'Wind: {wind_direction:.1f}°', color='blue', fontsize=10)
    
    # Plot 4: Course distribution histogram
    axs[1, 1].hist(courses, bins=36, range=(0, 360))
    axs[1, 1].set_title('Course Distribution')
    axs[1, 1].set_xlabel('Course (degrees)')
    axs[1, 1].set_ylabel('Frequency')
    axs[1, 1].grid(True)
    
    # Add a vertical line for the wind direction
    if wind_direction is not None:
        axs[1, 1].axvline(x=wind_direction, color='blue', linestyle='-', linewidth=2)
        # Also mark the opposite direction (wind blowing to)
        axs[1, 1].axvline(x=(wind_direction + 180) % 360, color='blue', linestyle='--', linewidth=2)
    
    plt.tight_layout()
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get the base filename from the results
    base_filename = os.path.basename(trackpoints[0].filename).replace('.gpx', '') if trackpoints and hasattr(trackpoints[0], 'filename') else 'wind_analysis'
    
    # Save the figure
    output_filename = os.path.join(output_dir, f"{base_filename}_wind_analysis.png")
    plt.savefig(output_filename)
    print(f"Wind analysis plot saved to: {output_filename}")
    plt.close()

def main():
    """Main function to handle command line arguments and run analysis"""
    if len(sys.argv) < 2:
        print("Usage: python analyze_wind.py <gpx_file_path> [window_size] [--plot]")
        print("  gpx_file_path: Path to the GPX file to analyze")
        print("  window_size: Optional smoothing window size (default: 5)")
        print("  --plot: Optional flag to generate visualization plots")
        sys.exit(1)
    
    gpx_file = sys.argv[1]
    
    # Parse arguments
    window_size = 5
    plot_results = False
    
    # Check for additional arguments
    for arg in sys.argv[2:]:
        if arg == '--plot':
            plot_results = True
        elif arg.isdigit():
            window_size = int(arg)
    
    if not os.path.exists(gpx_file):
        print(f"Error: GPX file not found: {gpx_file}")
        sys.exit(1)
    
    # Run the analysis
    results = analyze_gpx_wind(gpx_file, window_size, plot_results)
    
    # Print additional detailed information
    print("\nDetailed Wind Analysis:")
    print(f"GPX File: {results['gpx_file']}")
    print(f"Number of trackpoints: {results['num_trackpoints']}")
    print(f"Wind direction: {results['wind_direction']:.2f}°")
    print(f"Port tacks: {results['port_tacks']}")
    print(f"Starboard tacks: {results['starboard_tacks']}")
    print(f"Tack ratio (port:starboard): {results['port_tacks']/max(1, results['starboard_tacks']):.2f}")
    
    # Print information about how wind direction was calculated
    print("\nWind Direction Calculation Method:")
    if len(results['tack_segments']) >= 2:
        print("Method: Based on detected tack points")
        if len(results['course_groups']) >= 2:
            group1_mean = np.mean(results['course_groups'][0])
            group2_mean = np.mean(results['course_groups'][1])
            avg_axis = (group1_mean + group2_mean) / 2
            if abs(group1_mean - group2_mean) > 180:
                # Handle the case where the average crosses the 0/360 boundary
                avg_axis = (avg_axis + 180) % 360
            print(f"Tacking axis: {avg_axis:.2f}°")
            print(f"Wind direction: {(avg_axis + 90) % 360:.2f}° or {(avg_axis - 90) % 360:.2f}°")
            print(f"Selected direction: {results['wind_direction']:.2f}°")
            print(f"Tack group 1: {len(results['course_groups'][0])} courses, mean={np.mean(results['course_groups'][0]):.2f}°")
            print(f"Tack group 2: {len(results['course_groups'][1])} courses, mean={np.mean(results['course_groups'][1]):.2f}°")
    else:
        print("Method: Fallback - using course distribution")
        print("No clear tacking pattern detected, wind direction estimated from overall course distribution.")
        
        # Print course distribution information
        courses = results['analysis_data'].get('courses', [])
        if courses:
            course_bins = np.histogram(courses, bins=36, range=(0, 360))[0]
            max_bin = np.argmax(course_bins)
            bin_size = 10  # 360/36
            peak_course = max_bin * bin_size + bin_size/2
            print(f"Most common course direction: {peak_course:.2f}°")
            print(f"Estimated wind direction (perpendicular): {(peak_course + 90) % 360:.2f}° or {(peak_course - 90) % 360:.2f}°")
    
    # Print tacking groups if available
    if len(results['course_groups']) >= 2:
        print("\nTacking Directions:")
        for i, group in enumerate(results['course_groups']):
            print(f"Group {i+1}: Mean={np.mean(group):.2f}°, Count={len(group)}")

if __name__ == "__main__":
    main()
