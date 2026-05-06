/**
 * GPX Parser - Handles loading and parsing GPX files
 * Also supports loading pre-processed JSON files
 */
class GpxParser {
    constructor() {
        this.trackPoints = [];
        this.bounds = {
            minLat: 90,
            maxLat: -90,
            minLon: 180,
            maxLon: -180
        };
        this.startTime = null;
        this.endTime = null;
    }

    /**
     * Parse a GPX file and extract track points
     * @param {File|Blob} file - The GPX file to parse
     * @returns {Promise} - Resolves with parsed track data
     */
    parseGpxFile(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            
            reader.onload = (e) => {
                const content = e.target.result;
                
                // Check if this is a JSON file (pre-processed GPX)
                if (file.name.endsWith('.json')) {
                    try {
                        const jsonData = JSON.parse(content);
                        this.processJsonData(jsonData);
                        resolve(this.getTrackData());
                    } catch (error) {
                        reject(new Error('Invalid JSON file: ' + error.message));
                    }
                    return;
                }
                
                // Process as GPX XML
                try {
                    const parser = new DOMParser();
                    const xmlDoc = parser.parseFromString(content, "text/xml");
                    
                    // Check for parsing errors
                    const parserError = xmlDoc.querySelector('parsererror');
                    if (parserError) {
                        reject(new Error('XML parsing error: ' + parserError.textContent));
                        return;
                    }
                    
                    this.processGpxXml(xmlDoc);
                    resolve(this.getTrackData());
                } catch (error) {
                    reject(new Error('Error parsing GPX: ' + error.message));
                }
            };
            
            reader.onerror = () => {
                reject(new Error('Error reading file'));
            };
            
            reader.readAsText(file);
        });
    }
    
    /**
     * Process GPX XML document
     * @param {Document} xmlDoc - The parsed XML document
     */
    processGpxXml(xmlDoc) {
        // Reset data
        this.trackPoints = [];
        this.resetBounds();
        
        // Get namespace
        const ns = xmlDoc.documentElement.namespaceURI;
        const nsResolver = ns ? 
            xmlDoc.createNSResolver(xmlDoc.documentElement) : 
            null;
        
        // XPath query for track points
        const xpath = ns ? 
            "//ns:trkpt" : 
            "//trkpt";
        
        const xpathResult = xmlDoc.evaluate(
            xpath, 
            xmlDoc, 
            nsResolver ? (prefix) => prefix === 'ns' ? ns : null : null,
            XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, 
            null
        );
        
        // Process each track point
        for (let i = 0; i < xpathResult.snapshotLength; i++) {
            const trkpt = xpathResult.snapshotItem(i);
            const lat = parseFloat(trkpt.getAttribute('lat'));
            const lon = parseFloat(trkpt.getAttribute('lon'));
            
            // Get time element
            const timeElement = trkpt.getElementsByTagName('time')[0];
            let timestamp = null;
            
            if (timeElement && timeElement.textContent) {
                timestamp = new Date(timeElement.textContent);
            }
            
            // Create point object
            const point = {
                lat: lat,
                lon: lon,
                time: timestamp,
                elevation: null,
                speed: null,
                course: null
            };
            
            // Get elevation if available
            const eleElement = trkpt.getElementsByTagName('ele')[0];
            if (eleElement && eleElement.textContent) {
                point.elevation = parseFloat(eleElement.textContent);
            }
            
            // Update bounds
            this.updateBounds(lat, lon);
            
            // Add to track points array
            this.trackPoints.push(point);
        }
        
        // Calculate derived data (speed, course, etc.)
        this.calculateDerivedData();
    }
    
    /**
     * Process pre-processed JSON data
     * @param {Object} jsonData - The parsed JSON data
     */
    processJsonData(jsonData) {
        // Reset data
        this.trackPoints = [];
        this.resetBounds();
        
        // Check if this is an array of points
        if (Array.isArray(jsonData)) {
            this.trackPoints = jsonData.map(point => {
                // Ensure time is a Date object
                if (point.time && typeof point.time === 'string') {
                    point.time = new Date(point.time);
                }
                
                // Update bounds
                this.updateBounds(point.lat, point.lon);
                
                return point;
            });
        } 
        // Or if it's an object with a points property
        else if (jsonData.points && Array.isArray(jsonData.points)) {
            this.trackPoints = jsonData.points.map(point => {
                // Ensure time is a Date object
                if (point.time && typeof point.time === 'string') {
                    point.time = new Date(point.time);
                }
                
                // Update bounds
                this.updateBounds(point.lat, point.lon);
                
                return point;
            });
        } else {
            throw new Error('Invalid JSON format');
        }
        
        // Calculate derived data if not already present
        this.calculateDerivedData();
    }
    
    /**
     * Calculate derived data like speed and course
     */
    calculateDerivedData() {
        if (this.trackPoints.length < 2) return;
        
        // Set start and end times
        this.startTime = this.trackPoints[0].time;
        this.endTime = this.trackPoints[this.trackPoints.length - 1].time;
        
        // Calculate speed and course for each point
        for (let i = 1; i < this.trackPoints.length; i++) {
            const prev = this.trackPoints[i - 1];
            const curr = this.trackPoints[i];
            
            // Skip if no timestamps
            if (!prev.time || !curr.time) continue;
            
            // Time difference in seconds
            const timeDiff = (curr.time - prev.time) / 1000;
            
            // Skip if no time difference
            if (timeDiff <= 0) continue;
            
            // Calculate distance in meters
            const distance = this.calculateDistance(
                prev.lat, prev.lon, 
                curr.lat, curr.lon
            );
            
            // Calculate speed in knots (1 m/s = 1.94384 knots)
            curr.speed = (distance / timeDiff) * 1.94384;
            
            // Calculate bearing/course
            curr.course = this.calculateBearing(
                prev.lat, prev.lon, 
                curr.lat, curr.lon
            );
        }
        
        // Set first point speed and course based on second point
        if (this.trackPoints.length > 1) {
            this.trackPoints[0].speed = this.trackPoints[1].speed;
            this.trackPoints[0].course = this.trackPoints[1].course;
        }
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
     * Calculate bearing between two points
     * @param {number} lat1 - Latitude of first point
     * @param {number} lon1 - Longitude of first point
     * @param {number} lat2 - Latitude of second point
     * @param {number} lon2 - Longitude of second point
     * @returns {number} - Bearing in degrees (0-360)
     */
    calculateBearing(lat1, lon1, lat2, lon2) {
        const φ1 = lat1 * Math.PI / 180;
        const φ2 = lat2 * Math.PI / 180;
        const λ1 = lon1 * Math.PI / 180;
        const λ2 = lon2 * Math.PI / 180;
        
        const y = Math.sin(λ2 - λ1) * Math.cos(φ2);
        const x = Math.cos(φ1) * Math.sin(φ2) -
                Math.sin(φ1) * Math.cos(φ2) * Math.cos(λ2 - λ1);
        
        let bearing = Math.atan2(y, x) * 180 / Math.PI;
        
        // Convert to 0-360 range
        bearing = (bearing + 360) % 360;
        
        return bearing;
    }
    
    /**
     * Reset bounds to initial values
     */
    resetBounds() {
        this.bounds = {
            minLat: 90,
            maxLat: -90,
            minLon: 180,
            maxLon: -180
        };
    }
    
    /**
     * Update bounds with new coordinates
     * @param {number} lat - Latitude
     * @param {number} lon - Longitude
     */
    updateBounds(lat, lon) {
        this.bounds.minLat = Math.min(this.bounds.minLat, lat);
        this.bounds.maxLat = Math.max(this.bounds.maxLat, lat);
        this.bounds.minLon = Math.min(this.bounds.minLon, lon);
        this.bounds.maxLon = Math.max(this.bounds.maxLon, lon);
    }
    
    /**
     * Get the processed track data
     * @returns {Object} - Track data object
     */
    getTrackData() {
        return {
            points: this.trackPoints,
            bounds: this.bounds,
            startTime: this.startTime,
            endTime: this.endTime
        };
    }
    
    /**
     * Filter track points by time range
     * @param {Date} startTime - Start time
     * @param {Date} endTime - End time
     * @returns {Array} - Filtered track points
     */
    getPointsInTimeRange(startTime, endTime) {
        return this.trackPoints.filter(point => 
            point.time >= startTime && point.time <= endTime
        );
    }
    
    /**
     * Convert track data to GeoJSON format
     * @returns {Object} - GeoJSON object
     */
    toGeoJSON() {
        return {
            type: "FeatureCollection",
            features: [{
                type: "Feature",
                geometry: {
                    type: "LineString",
                    coordinates: this.trackPoints.map(point => [point.lon, point.lat])
                },
                properties: {
                    name: "Track",
                    time: this.startTime ? this.startTime.toISOString() : null
                }
            }]
        };
    }
}
