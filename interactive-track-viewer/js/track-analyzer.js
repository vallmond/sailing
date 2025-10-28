/**
 * Track Analyzer - Calculates metrics for sailing tracks
 * Handles calculations like distance, speed, wind angles, etc.
 */
class TrackAnalyzer {
    constructor() {
        this.trackData = null;
        this.windDirection = 0; // Wind direction in degrees (0-359)
    }
    
    /**
     * Set the track data to analyze
     * @param {Object} trackData - Track data from GpxParser
     */
    setTrackData(trackData) {
        this.trackData = trackData;
    }
    
    /**
     * Set the wind direction
     * @param {number} direction - Wind direction in degrees (0-359)
     */
    setWindDirection(direction) {
        this.windDirection = (direction + 360) % 360;
    }
    
    /**
     * Calculate metrics for a specific time range
     * @param {Date} startTime - Start time
     * @param {Date} endTime - End time
     * @returns {Object} - Calculated metrics
     */
    calculateMetrics(startTime, endTime) {
        if (!this.trackData || !this.trackData.points || this.trackData.points.length < 2) {
            return {
                distance: 0,
                duration: 0,
                avgSpeed: 0,
                maxSpeed: 0,
                avgWindAngle: 0,
                tacks: 0,
                windAngles: []
            };
        }
        
        // Get points in the time range
        let points = this.trackData.points;
        
        if (startTime && endTime) {
            points = points.filter(point => 
                point.time >= startTime && point.time <= endTime
            );
        }
        
        if (points.length < 2) {
            return {
                distance: 0,
                duration: 0,
                avgSpeed: 0,
                maxSpeed: 0,
                avgWindAngle: 0,
                tacks: 0,
                windAngles: []
            };
        }
        
        // Calculate total distance
        let totalDistance = 0;
        for (let i = 1; i < points.length; i++) {
            const prev = points[i - 1];
            const curr = points[i];
            
            totalDistance += this.calculateDistance(
                prev.lat, prev.lon, 
                curr.lat, curr.lon
            );
        }
        
        // Calculate duration in seconds
        const duration = (points[points.length - 1].time - points[0].time) / 1000;
        
        // Calculate average and max speed
        let totalSpeed = 0;
        let maxSpeed = 0;
        let speedCount = 0;
        
        points.forEach(point => {
            if (point.speed !== null && !isNaN(point.speed)) {
                totalSpeed += point.speed;
                maxSpeed = Math.max(maxSpeed, point.speed);
                speedCount++;
            }
        });
        
        const avgSpeed = speedCount > 0 ? totalSpeed / speedCount : 0;
        
        // Calculate wind angles and tacks
        let windAngles = [];
        let tacks = 0;
        let prevWindAngle = null;
        
        points.forEach(point => {
            if (point.course !== null && !isNaN(point.course)) {
                // Calculate angle to wind (0-180 degrees)
                const relativeAngle = Math.abs(this.normalizeAngle(point.course - this.windDirection));
                const windAngle = Math.min(relativeAngle, 360 - relativeAngle);
                
                windAngles.push(windAngle);
                
                // Count tacks (crossing through the wind)
                if (prevWindAngle !== null) {
                    // If we cross from one side of the wind to the other
                    const prevSide = this.getWindSide(prevWindAngle);
                    const currSide = this.getWindSide(windAngle);
                    
                    if (prevSide !== currSide && prevSide !== 0 && currSide !== 0) {
                        tacks++;
                    }
                }
                
                prevWindAngle = windAngle;
            }
        });
        
        // Calculate average wind angle
        const avgWindAngle = windAngles.length > 0 ? 
            windAngles.reduce((sum, angle) => sum + angle, 0) / windAngles.length : 
            0;
        
        return {
            distance: totalDistance,
            duration: duration,
            avgSpeed: avgSpeed,
            maxSpeed: maxSpeed,
            avgWindAngle: avgWindAngle,
            tacks: tacks,
            windAngles: windAngles
        };
    }
    
    /**
     * Calculate distance between two points using Haversine formula
     * @param {number} lat1 - Latitude of first point
     * @param {number} lon1 - Longitude of first point
     * @param {number} lat2 - Latitude of second point
     * @param {number} lon2 - Longitude of second point
     * @returns {number} - Distance in meters
     */
    calculateDistance(lat1, lon1, lat2, lon2) {
        const R = 6371000; // Earth radius in meters
        const φ1 = lat1 * Math.PI / 180;
        const φ2 = lat2 * Math.PI / 180;
        const Δφ = (lat2 - lat1) * Math.PI / 180;
        const Δλ = (lon2 - lon1) * Math.PI / 180;
        
        const a = Math.sin(Δφ/2) * Math.sin(Δφ/2) +
                Math.cos(φ1) * Math.cos(φ2) *
                Math.sin(Δλ/2) * Math.sin(Δλ/2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        
        return R * c;
    }
    
    /**
     * Normalize angle to 0-360 range
     * @param {number} angle - Angle in degrees
     * @returns {number} - Normalized angle (0-360)
     */
    normalizeAngle(angle) {
        return (angle + 360) % 360;
    }
    
    /**
     * Determine which side of the wind we're on
     * @param {number} windAngle - Angle to wind (0-180)
     * @returns {number} - Wind side: -1 (port), 0 (in irons), 1 (starboard)
     */
    getWindSide(windAngle) {
        if (windAngle < 45) {
            return 0; // In irons (too close to wind)
        } else if (windAngle < 90) {
            return -1; // Port tack
        } else {
            return 1; // Starboard tack
        }
    }
    
    /**
     * Get color for a speed value (for track coloring)
     * @param {number} speed - Speed in knots
     * @returns {string} - CSS color string
     */
    getSpeedColor(speed) {
        // Define color stops for speed gradient
        const colorStops = [
            { speed: 0, color: [0, 0, 255] },     // Blue (slow: 0-3 knots)
            { speed: 3, color: [0, 0, 255] },     // Blue (slow: 0-3 knots)
            { speed: 4, color: [255, 255, 0] },   // Yellow (medium: 4-5 knots)
            { speed: 5, color: [255, 255, 0] },   // Yellow (medium: 4-5 knots)
            { speed: 6, color: [0, 255, 0] },     // Green (fast: 5-6 knots)
            { speed: 6.1, color: [255, 0, 0] }    // Red (very fast: 6+ knots)
        ];
        
        // Find the color stops to interpolate between
        let lowerStop = colorStops[0];
        let upperStop = colorStops[colorStops.length - 1];
        
        for (let i = 0; i < colorStops.length - 1; i++) {
            if (speed >= colorStops[i].speed && speed <= colorStops[i + 1].speed) {
                lowerStop = colorStops[i];
                upperStop = colorStops[i + 1];
                break;
            }
        }
        
        // If speed is below minimum or above maximum, use the first or last color
        if (speed <= colorStops[0].speed) {
            return `rgb(${colorStops[0].color.join(',')})`;
        }
        
        if (speed >= colorStops[colorStops.length - 1].speed) {
            const lastColor = colorStops[colorStops.length - 1].color;
            return `rgb(${lastColor.join(',')})`;
        }
        
        // Interpolate between the two color stops
        const ratio = (speed - lowerStop.speed) / (upperStop.speed - lowerStop.speed);
        
        const r = Math.round(lowerStop.color[0] + ratio * (upperStop.color[0] - lowerStop.color[0]));
        const g = Math.round(lowerStop.color[1] + ratio * (upperStop.color[1] - lowerStop.color[1]));
        const b = Math.round(lowerStop.color[2] + ratio * (upperStop.color[2] - lowerStop.color[2]));
        
        return `rgb(${r},${g},${b})`;
    }
    
    /**
     * Format time duration as HH:MM:SS
     * @param {number} seconds - Duration in seconds
     * @returns {string} - Formatted time string
     */
    formatDuration(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        return [
            hours.toString().padStart(2, '0'),
            minutes.toString().padStart(2, '0'),
            secs.toString().padStart(2, '0')
        ].join(':');
    }
    
    /**
     * Format date as YYYY-MM-DD HH:MM:SS
     * @param {Date} date - Date object
     * @returns {string} - Formatted date string
     */
    formatDateTime(date) {
        if (!date) return '--';
        
        return date.toISOString().replace('T', ' ').substr(0, 19);
    }
}
