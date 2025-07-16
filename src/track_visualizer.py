#!/usr/bin/env python3
"""
Simple GPX track visualization using Python's turtle module.
This script reads a GPX file, segments it based on bearing changes,
and displays the track with different colors for each segment.
"""

import sys
import os
import random
import turtle

# Add project root to path to allow imports from src directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.gpx_analyzer import parse_gpx, detect_segments, analyze_segments

def visualize_track(gpx_file, bearing_threshold=20):
    """
    Visualize a GPX track using turtle graphics.
    Each segment will be drawn in a different color.
    """
    # Parse GPX file
    print(f"Parsing GPX file: {gpx_file}")
    trackpoints = parse_gpx(gpx_file)
    print(f"Found {len(trackpoints)} trackpoints")
    
    # Detect segments
    print(f"Detecting segments (bearing threshold: {bearing_threshold}°)...")
    segments = detect_segments(trackpoints, bearing_threshold)
    print(f"Found {len(segments)} segments")
    
    # Set up the turtle screen
    screen = turtle.Screen()
    screen.title("GPX Track Visualization")
    screen.setup(800, 600)
    screen.bgcolor("white")
    
    # Find min/max coordinates to scale the visualization
    min_lat = min(tp.lat for tp in trackpoints)
    max_lat = max(tp.lat for tp in trackpoints)
    min_lon = min(tp.lon for tp in trackpoints)
    max_lon = max(tp.lon for tp in trackpoints)
    
    # Calculate scaling factors
    width = screen.window_width() * 0.8
    height = screen.window_height() * 0.8
    
    lon_range = max_lon - min_lon
    lat_range = max_lat - min_lat
    
    x_scale = width / lon_range if lon_range > 0 else 1
    y_scale = height / lat_range if lat_range > 0 else 1
    
    # Use the smaller scale to maintain aspect ratio
    scale = min(x_scale, y_scale)
    
    # Calculate center offsets
    center_lon = (min_lon + max_lon) / 2
    center_lat = (min_lat + max_lat) / 2
    
    # Create a turtle for drawing
    t = turtle.Turtle()
    t.speed(0)  # Fastest speed
    t.penup()
    t.hideturtle()
    
    # Draw each segment with a different color
    colors = ["red", "blue", "green", "purple", "orange", "cyan", "magenta", "brown", "pink"]
    
    for i, segment in enumerate(segments):
        if not segment:  # Skip empty segments
            continue
        
        # Choose a color for this segment
        t.pencolor(colors[i % len(colors)])
        t.pensize(2)
        
        # Move to the first point of the segment
        first_point = segment[0]
        x = (first_point.lon - center_lon) * scale
        y = (first_point.lat - center_lat) * scale
        t.goto(x, y)
        t.pendown()
        
        # Draw the segment
        for point in segment[1:]:
            x = (point.lon - center_lon) * scale
            y = (point.lat - center_lat) * scale
            t.goto(x, y)
        
        t.penup()
    
    # Add a legend
    legend_t = turtle.Turtle()
    legend_t.penup()
    legend_t.hideturtle()
    legend_t.goto(-screen.window_width()/2 + 10, screen.window_height()/2 - 30)
    legend_t.write(f"GPX Track: {gpx_file}", font=("Arial", 10, "normal"))
    legend_t.goto(-screen.window_width()/2 + 10, screen.window_height()/2 - 50)
    legend_t.write(f"Segments: {len(segments)}", font=("Arial", 10, "normal"))
    legend_t.goto(-screen.window_width()/2 + 10, screen.window_height()/2 - 70)
    legend_t.write(f"Bearing threshold: {bearing_threshold}°", font=("Arial", 10, "normal"))
    
    print("Track visualization complete. Close the window to exit.")
    screen.mainloop()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python track_visualizer.py <gpx_file> [bearing_threshold]")
        sys.exit(1)
    
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
    
    visualize_track(gpx_file_path, bearing_threshold)
