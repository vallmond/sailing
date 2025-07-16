import math

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points 
    on the earth (specified in decimal degrees)
    using the Haversine formula.
    
    Returns distance in meters.
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371000  # Radius of earth in meters
    return c * r

def calculate_bearing(lat1, lon1, lat2, lon2):
    """
    Calculate the bearing/direction in degrees from point 1 to point 2.
    
    Returns bearing in degrees (0-360).
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Calculate bearing
    dlon = lon2 - lon1
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    bearing = math.atan2(y, x)
    
    # Convert to degrees
    bearing_degrees = math.degrees(bearing)
    
    # Normalize to 0-360
    bearing_normalized = (bearing_degrees + 360) % 360
    
    return bearing_normalized

def angle_diff(angle1, angle2):
    """
    Calculate the difference between two angles in degrees.
    Accounts for the circular nature of angles (0-360 degrees).
    
    Args:
        angle1: First angle in degrees
        angle2: Second angle in degrees
    
    Returns:
        float: Difference between angles in degrees (-180 to 180)
    """
    # Calculate the absolute difference between angles
    diff = abs(angle2 - angle1) % 360
    
    # Adjust to get the smallest angle difference (-180 to 180)
    if diff > 180:
        diff -= 360
    
    return diff

def is_similar_bearing(bearing1, bearing2, threshold=20):
    """
    Check if two bearings are similar within a threshold.
    
    Args:
        bearing1: First bearing in degrees (0-360)
        bearing2: Second bearing in degrees (0-360)
        threshold: Maximum allowed difference in degrees (default: 20)
    
    Returns:
        bool: True if bearings are similar, False otherwise
    """
    # Calculate the absolute difference between bearings using angle_diff
    diff = abs(angle_diff(bearing1, bearing2))
    
    # Check if the difference is within the threshold
    return diff <= threshold

def calculate_speed(distance_meters, time_diff_seconds):
    """
    Calculate speed in m/s and knots based on distance and time difference.
    
    Args:
        distance_meters: Distance in meters
        time_diff_seconds: Time difference in seconds
    
    Returns:
        tuple: (speed_ms, speed_knots)
    """
    if time_diff_seconds <= 0:
        return 0, 0
    
    speed_ms = distance_meters / time_diff_seconds
    speed_knots = speed_ms * 1.94384  # Convert m/s to knots
    
    return speed_ms, speed_knots

def trackpoint_calculations(tp1, tp2):
    """
    Calculate distance, direction, and speed between two trackpoints.
    
    Args:
        tp1: First trackpoint with lat, lon, and time attributes
        tp2: Second trackpoint with lat, lon, and time attributes
    
    Returns:
        dict: Dictionary containing distance (m), direction (degrees), 
              speed (m/s), and speed (knots)
    """
    # Calculate distance
    distance = calculate_distance(tp1.lat, tp1.lon, tp2.lat, tp2.lon)
    
    # Calculate direction
    direction = calculate_bearing(tp1.lat, tp1.lon, tp2.lat, tp2.lon)
    
    # Calculate time difference in seconds
    time_diff = (tp2.time - tp1.time).total_seconds()
    
    # Calculate speed
    speed_ms, speed_knots = calculate_speed(distance, time_diff)
    
    return {
        'distance_meters': distance,
        'direction_degrees': direction,
        'speed_ms': speed_ms,
        'speed_knots': speed_knots
    }
