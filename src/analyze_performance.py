#!/usr/bin/env python3
"""
Analyze sailing performance based on wind direction, tacks, and points of sail.
This script processes GPX track data and analyzes speed in relation to sailing conditions.
"""

import sys
import os
import argparse
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict

# Add project root to path to allow imports from src directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.gpx_analyzer import parse_gpx, analyze_wind_direction
from src.geo_utils import calculate_bearing, angle_diff

def calculate_point_of_sail(course_bearing, wind_direction):
    """
    Calculate the point of sail based on course bearing and wind direction.
    
    Args:
        course_bearing (float): The course bearing in degrees
        wind_direction (float): The wind direction in degrees (where wind is coming FROM)
        
    Returns:
        tuple: (angle, point_of_sail_name)
    """
    # Calculate the angle between wind and course using abs((course - wind) - 180)
    wind_angle = abs((course_bearing - wind_direction) - 180)
    # Ensure the angle is between 0° and 180°
    if wind_angle > 180:
        wind_angle = 360 - wind_angle
    
    # Determine point of sail based on the angle
    if wind_angle < 35:
        point_of_sail = "Close Hauled"
    elif wind_angle < 80:
        point_of_sail = "Close Reach"
    elif wind_angle < 100:
        point_of_sail = "Beam Reach"
    elif wind_angle < 135:
        point_of_sail = "Broad Reach"
    else:  # wind_angle <= 180
        point_of_sail = "Run"
        
    return wind_angle, point_of_sail

def determine_tack(course_bearing, wind_direction):
    """
    Determine whether the boat is on port or starboard tack.
    
    Args:
        course_bearing (float): The course bearing in degrees
        wind_direction (float): The wind direction in degrees (where wind is coming FROM)
        
    Returns:
        str: 'port' or 'starboard'
    """
    # Calculate the relative angle between wind and course
    relative_angle = (wind_direction - course_bearing) % 360
    
    # If wind is coming from the port side (left), it's port tack
    # If wind is coming from the starboard side (right), it's starboard tack
    if 0 <= relative_angle < 180:
        return "port"
    else:
        return "starboard"

def analyze_track_performance(trackpoints, wind_direction, window_size=5):
    """
    Analyze track performance in relation to wind direction, tack, and point of sail.
    
    Args:
        trackpoints (list): List of TrackPoint objects
        wind_direction (float): Wind direction in degrees
        window_size (int): Window size for smoothing calculations
        
    Returns:
        pandas.DataFrame: DataFrame with performance analysis
    """
    if len(trackpoints) < 2:
        print("Not enough trackpoints for analysis")
        return None
    
    # Run wind direction analysis to get tack assignments
    # analyze_wind_direction returns (wind_direction, tack_assignments, analysis_data)
    _, tack_assignments, _ = analyze_wind_direction(trackpoints, force_wind_direction=wind_direction)
    
    # Prepare data for analysis
    data = []
    
    # Calculate speed and course for each point
    for i in range(1, len(trackpoints)):
        prev_point = trackpoints[i-1]
        curr_point = trackpoints[i]
        
        # Calculate time difference in seconds
        time_diff = (curr_point.time - prev_point.time).total_seconds()
        if time_diff <= 0:
            continue  # Skip points with invalid time differences
        
        # Calculate bearing
        bearing = calculate_bearing(prev_point.lat, prev_point.lon, curr_point.lat, curr_point.lon)
        
        # Calculate distance and speed
        calculations = trackpoint_calculations(prev_point, curr_point)
        speed_knots = calculations['speed_knots']
        
        # Get tack
        tack = tack_assignments[i] if i < len(tack_assignments) and tack_assignments[i] is not None else "unknown"
        
        # Calculate point of sail
        wind_angle, point_of_sail = calculate_point_of_sail(bearing, wind_direction)
        
        # Store data
        data.append({
            'timestamp': curr_point.time,
            'speed_knots': speed_knots,
            'course_bearing': bearing,
            'wind_direction': wind_direction,
            'wind_angle': wind_angle,
            'tack': tack,
            'point_of_sail': point_of_sail
        })
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    
    # Apply smoothing to speed and course using rolling window
    if len(df) > window_size:
        df['speed_knots_smooth'] = df['speed_knots'].rolling(window=window_size, center=True).mean()
        df['course_bearing_smooth'] = df['course_bearing'].rolling(window=window_size, center=True).mean()
    else:
        df['speed_knots_smooth'] = df['speed_knots']
        df['course_bearing_smooth'] = df['course_bearing']
    
    # Fill NaN values from smoothing
    df = df.fillna(method='bfill').fillna(method='ffill')
    
    return df

def print_performance_summary(df):
    """
    Print a summary of performance metrics grouped by point of sail and tack.
    
    Args:
        df (pandas.DataFrame): DataFrame with performance data
    """
    print("\n===== OVERALL PERFORMANCE SUMMARY =====")
    print(f"Total data points: {len(df)}")
    print(f"Average speed: {df['speed_knots'].mean():.2f} knots")
    print(f"Maximum speed: {df['speed_knots'].max():.2f} knots")
    
    print("\n===== PERFORMANCE BY POINT OF SAIL =====")
    pos_stats = df.groupby('point_of_sail')['speed_knots'].agg(['count', 'mean', 'max', 'std']).reset_index()
    for _, row in pos_stats.iterrows():
        print(f"{row['point_of_sail']}: {row['count']} points, Avg: {row['mean']:.2f} knots, Max: {row['max']:.2f} knots, StdDev: {row['std']:.2f}")
    
    print("\n===== PERFORMANCE BY TACK =====")
    tack_stats = df.groupby('tack')['speed_knots'].agg(['count', 'mean', 'max', 'std']).reset_index()
    for _, row in tack_stats.iterrows():
        print(f"{row['tack']}: {row['count']} points, Avg: {row['mean']:.2f} knots, Max: {row['max']:.2f} knots, StdDev: {row['std']:.2f}")
    
    print("\n===== PERFORMANCE BY POINT OF SAIL AND TACK =====")
    combined_stats = df.groupby(['point_of_sail', 'tack'])['speed_knots'].agg(['count', 'mean', 'max', 'std']).reset_index()
    for _, row in combined_stats.iterrows():
        print(f"{row['point_of_sail']} on {row['tack']} tack: {row['count']} points, Avg: {row['mean']:.2f} knots, Max: {row['max']:.2f} knots, StdDev: {row['std']:.2f}")
    
    print("\n===== SPEED BY WIND ANGLE (10° BINS) =====")
    # Create 10-degree bins for wind angle
    df['wind_angle_bin'] = (df['wind_angle'] // 10) * 10
    angle_stats = df.groupby('wind_angle_bin')['speed_knots'].agg(['count', 'mean', 'max']).reset_index()
    for _, row in angle_stats.iterrows():
        print(f"{int(row['wind_angle_bin'])}° to {int(row['wind_angle_bin'])+10}°: {row['count']} points, Avg: {row['mean']:.2f} knots, Max: {row['max']:.2f} knots")

def main():
    """Main function to parse arguments and run analysis"""
    parser = argparse.ArgumentParser(description='Analyze sailing performance based on wind direction')
    parser.add_argument('gpx_file', help='Path to GPX file')
    parser.add_argument('wind_direction', type=float, help='Wind direction in degrees (where wind is coming FROM)')
    parser.add_argument('--window', type=int, default=5, help='Window size for smoothing calculations')
    parser.add_argument('--output', help='Optional CSV output file path')
    
    args = parser.parse_args()
    
    print(f"Parsing GPX file: {args.gpx_file}")
    trackpoints = parse_gpx(args.gpx_file)
    print(f"Found {len(trackpoints)} trackpoints")
    
    print(f"Analyzing performance with wind direction: {args.wind_direction}°")
    performance_df = analyze_track_performance(trackpoints, args.wind_direction, args.window)
    
    if performance_df is not None:
        print_performance_summary(performance_df)
        
        if args.output:
            performance_df.to_csv(args.output, index=False)
            print(f"\nDetailed performance data saved to: {args.output}")

if __name__ == "__main__":
    # Import trackpoint_calculations here to avoid circular imports
    from src.geo_utils import trackpoint_calculations
    main()
