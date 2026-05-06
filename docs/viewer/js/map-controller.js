/**
 * Map Controller - Handles the Leaflet map and visualization
 * Manages track display, markers, and interactive elements
 */
class MapController {
    constructor(mapElementId) {
        this.mapElementId = mapElementId;
        this.map = null;
        this.trackLayer = null;
        this.markersLayer = null;
        this.windLayer = null;
        this.currentPositionMarker = null;
        this.trackData = null;
        this.markersData = null;
        this.windDirection = 0;
        this.colorBySpeed = true;
        
        // Track display settings
        this.trackOptions = {
            weight: 3,
            opacity: 0.8,
            lineJoin: 'round'
        };
        
        // Initialize the map
        this.initMap();
    }
    
    /**
     * Initialize the Leaflet map
     */
    initMap() {
        // Create map with default view
        this.map = L.map(this.mapElementId, {
            center: [54.45, 18.58], // Default center (Gdansk Bay)
            zoom: 13,
            maxZoom: 19
        });
        
        // Add base tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        }).addTo(this.map);
        
        // Create layers for track, markers and wind
        this.trackLayer = L.layerGroup().addTo(this.map);
        this.markersLayer = L.layerGroup().addTo(this.map);
        this.windLayer = L.layerGroup().addTo(this.map);
        
        // Add scale control
        L.control.scale({
            imperial: false,
            maxWidth: 200
        }).addTo(this.map);
    }
    
    /**
     * Set track data and display it on the map
     * @param {Object} trackData - Track data from GpxParser
     */
    setTrackData(trackData) {
        this.trackData = trackData;
        this.displayTrack();
        this.fitMapToBounds();
    }
    
    /**
     * Set markers data and display them on the map
     * @param {Object} markersData - Markers data (buoys, start line, etc.)
     */
    setMarkersData(markersData) {
        this.markersData = markersData;
        this.displayMarkers();
    }
    
    /**
     * Set wind direction and update wind indicator
     * @param {number} direction - Wind direction in degrees (0-359)
     */
    setWindDirection(direction) {
        this.windDirection = (direction + 360) % 360;
        this.displayWindDirection();
    }
    
    /**
     * Display the track on the map
     * @param {Array} filteredPoints - Optional filtered points to display
     */
    displayTrack(filteredPoints) {
        // Clear existing track
        this.trackLayer.clearLayers();
        
        if (!this.trackData || !this.trackData.points || this.trackData.points.length < 2) {
            return;
        }
        
        const points = filteredPoints || this.trackData.points;
        
        if (points.length < 2) {
            return;
        }
        
        // If coloring by speed, create segments with different colors
        if (this.colorBySpeed) {
            this.displayColoredTrack(points);
        } else {
            // Create a single polyline for the track
            const latLngs = points.map(point => [point.lat, point.lon]);
            
            L.polyline(latLngs, {
                ...this.trackOptions,
                color: '#3388ff'
            }).addTo(this.trackLayer);
        }
        
        // Add start and end markers
        this.addStartEndMarkers(points);
    }
    
    /**
     * Display track with color segments based on speed
     * @param {Array} points - Track points to display
     */
    displayColoredTrack(points) {
        const analyzer = new TrackAnalyzer();
        
        // Create segments for each pair of points
        for (let i = 1; i < points.length; i++) {
            const prev = points[i - 1];
            const curr = points[i];
            
            // Skip if no speed data
            if (curr.speed === null || isNaN(curr.speed)) continue;
            
            // Get color based on speed
            const color = analyzer.getSpeedColor(curr.speed);
            
            // Create polyline segment
            L.polyline([
                [prev.lat, prev.lon],
                [curr.lat, curr.lon]
            ], {
                ...this.trackOptions,
                color: color
            }).bindPopup(`
                <strong>Speed:</strong> ${curr.speed.toFixed(1)} knots<br>
                <strong>Course:</strong> ${curr.course ? curr.course.toFixed(0) + '°' : 'N/A'}<br>
                <strong>Time:</strong> ${curr.time ? curr.time.toLocaleTimeString() : 'N/A'}
            `).addTo(this.trackLayer);
        }
    }
    
    /**
     * Add start and end markers to the track
     * @param {Array} points - Track points
     */
    addStartEndMarkers(points) {
        if (points.length < 2) return;
        
        const startPoint = points[0];
        const endPoint = points[points.length - 1];
        
        // Start marker (green)
        L.circleMarker([startPoint.lat, startPoint.lon], {
            radius: 6,
            color: '#00aa00',
            fillColor: '#00ff00',
            fillOpacity: 0.7,
            weight: 2
        }).bindPopup(`
            <strong>Start</strong><br>
            <strong>Time:</strong> ${startPoint.time ? startPoint.time.toLocaleString() : 'N/A'}
        `).addTo(this.trackLayer);
        
        // End marker (red)
        L.circleMarker([endPoint.lat, endPoint.lon], {
            radius: 6,
            color: '#aa0000',
            fillColor: '#ff0000',
            fillOpacity: 0.7,
            weight: 2
        }).bindPopup(`
            <strong>End</strong><br>
            <strong>Time:</strong> ${endPoint.time ? endPoint.time.toLocaleString() : 'N/A'}
        `).addTo(this.trackLayer);
    }
    
    /**
     * Display markers (buoys, start line, etc.) on the map
     */
    displayMarkers() {
        // Clear existing markers
        this.markersLayer.clearLayers();
        
        if (!this.markersData) return;
        
        // Process buoys
        if (this.markersData.buoys && Array.isArray(this.markersData.buoys)) {
            this.markersData.buoys.forEach(buoy => {
                if (!buoy.lat || !buoy.lon) return;
                
                // Create buoy marker
                const marker = L.circleMarker([buoy.lat, buoy.lon], {
                    radius: 5,
                    color: buoy.color || '#000',
                    fillColor: buoy.color || '#ff0',
                    fillOpacity: 0.7,
                    weight: 2
                });
                
                // Add popup with buoy info
                let popupContent = `<strong>${buoy.name || 'Buoy'}</strong>`;
                if (buoy.description) {
                    popupContent += `<br>${buoy.description}`;
                }
                
                marker.bindPopup(popupContent);
                marker.addTo(this.markersLayer);
            });
        }
        
        // Process start line if available
        if (this.markersData.startLine && 
            this.markersData.startLine.point1 && 
            this.markersData.startLine.point2) {
            
            const p1 = this.markersData.startLine.point1;
            const p2 = this.markersData.startLine.point2;
            
            // Create start line
            if (p1.lat && p1.lon && p2.lat && p2.lon) {
                L.polyline([
                    [p1.lat, p1.lon],
                    [p2.lat, p2.lon]
                ], {
                    color: '#ff0000',
                    weight: 3,
                    dashArray: '5, 5',
                    opacity: 0.8
                }).bindPopup('Start Line').addTo(this.markersLayer);
                
                // Add markers for start line ends
                L.circleMarker([p1.lat, p1.lon], {
                    radius: 4,
                    color: '#000',
                    fillColor: '#ff0000',
                    fillOpacity: 0.7
                }).bindPopup('Start Line - Pin End').addTo(this.markersLayer);
                
                L.circleMarker([p2.lat, p2.lon], {
                    radius: 4,
                    color: '#000',
                    fillColor: '#ff0000',
                    fillOpacity: 0.7
                }).bindPopup('Start Line - Committee Boat').addTo(this.markersLayer);
            }
        }
        
        // Process other custom markers
        if (this.markersData.markers && Array.isArray(this.markersData.markers)) {
            this.markersData.markers.forEach(marker => {
                if (!marker.lat || !marker.lon) return;
                
                // Create marker
                const icon = L.divIcon({
                    html: `<div class="custom-marker" style="background-color: ${marker.color || '#3388ff'}"></div>`,
                    className: 'custom-marker-container',
                    iconSize: [12, 12]
                });
                
                L.marker([marker.lat, marker.lon], {
                    icon: icon
                }).bindPopup(`
                    <strong>${marker.name || 'Marker'}</strong>
                    ${marker.description ? '<br>' + marker.description : ''}
                `).addTo(this.markersLayer);
            });
        }
    }
    
    /**
     * Display wind direction indicator on the map
     */
    displayWindDirection() {
        // Clear existing wind indicator
        this.windLayer.clearLayers();
        
        if (!this.map) return;
        
        // Create wind arrow in the top-right corner
        const windArrow = L.control({position: 'topright'});
        
        windArrow.onAdd = (map) => {
            const div = L.DomUtil.create('div', 'wind-arrow');
            div.innerHTML = `
                <div class="wind-arrow-container">
                    <div class="wind-arrow-icon" style="transform: rotate(${this.windDirection}deg)">
                        ↑
                    </div>
                    <div class="wind-arrow-label">${this.windDirection}°</div>
                </div>
            `;
            return div;
        };
        
        windArrow.addTo(this.map);
        
        // Add wind direction to the map center for reference
        const bounds = this.map.getBounds();
        const center = bounds.getCenter();
        
        // Calculate arrow endpoints
        const arrowLength = 0.01; // Adjust based on zoom level
        const radians = (this.windDirection - 180) * Math.PI / 180; // Wind direction is where it's coming FROM
        
        const endLat = center.lat + arrowLength * Math.cos(radians);
        const endLng = center.lng + arrowLength * Math.sin(radians);
        
        // Create arrow
        const arrow = L.polyline([
            [center.lat, center.lng],
            [endLat, endLng]
        ], {
            color: '#0066cc',
            weight: 3,
            opacity: 0.8
        }).addTo(this.windLayer);
        
        // Add arrowhead
        const arrowHead = L.polygon([
            [endLat, endLng],
            [
                endLat - arrowLength * 0.2 * Math.cos(radians - Math.PI * 0.2),
                endLng - arrowLength * 0.2 * Math.sin(radians - Math.PI * 0.2)
            ],
            [
                endLat - arrowLength * 0.2 * Math.cos(radians + Math.PI * 0.2),
                endLng - arrowLength * 0.2 * Math.sin(radians + Math.PI * 0.2)
            ]
        ], {
            color: '#0066cc',
            fillColor: '#0066cc',
            fillOpacity: 0.8,
            weight: 1
        }).bindPopup(`Wind Direction: ${this.windDirection}°`).addTo(this.windLayer);
    }
    
    /**
     * Update current position marker on the map
     * @param {Object} point - Track point
     */
    updateCurrentPosition(point) {
        if (!point || !point.lat || !point.lon) return;
        
        // Remove existing marker
        if (this.currentPositionMarker) {
            this.map.removeLayer(this.currentPositionMarker);
        }
        
        // Create new marker
        this.currentPositionMarker = L.circleMarker([point.lat, point.lon], {
            radius: 8,
            color: '#fff',
            fillColor: '#3388ff',
            fillOpacity: 1,
            weight: 2
        }).bindPopup(`
            <strong>Current Position</strong><br>
            <strong>Time:</strong> ${point.time ? point.time.toLocaleTimeString() : 'N/A'}<br>
            <strong>Speed:</strong> ${point.speed ? point.speed.toFixed(1) + ' knots' : 'N/A'}<br>
            <strong>Course:</strong> ${point.course ? point.course.toFixed(0) + '°' : 'N/A'}
        `).addTo(this.map);
    }
    
    /**
     * Fit map view to track bounds
     */
    fitMapToBounds() {
        if (!this.trackData || !this.trackData.bounds) return;
        
        const bounds = L.latLngBounds(
            [this.trackData.bounds.minLat, this.trackData.bounds.minLon],
            [this.trackData.bounds.maxLat, this.trackData.bounds.maxLon]
        );
        
        // Add padding
        this.map.fitBounds(bounds, {
            padding: [50, 50],
            maxZoom: 16
        });
    }
    
    /**
     * Toggle track visibility
     * @param {boolean} visible - Whether track should be visible
     */
    toggleTrack(visible) {
        if (visible) {
            this.trackLayer.addTo(this.map);
        } else {
            this.map.removeLayer(this.trackLayer);
        }
    }
    
    /**
     * Toggle markers visibility
     * @param {boolean} visible - Whether markers should be visible
     */
    toggleMarkers(visible) {
        if (visible) {
            this.markersLayer.addTo(this.map);
        } else {
            this.map.removeLayer(this.markersLayer);
        }
    }
    
    /**
     * Toggle wind direction indicator visibility
     * @param {boolean} visible - Whether wind indicator should be visible
     */
    toggleWind(visible) {
        if (visible) {
            this.windLayer.addTo(this.map);
        } else {
            this.map.removeLayer(this.windLayer);
        }
    }
    
    /**
     * Toggle track coloring by speed
     * @param {boolean} colorBySpeed - Whether to color track by speed
     */
    setColorBySpeed(colorBySpeed) {
        this.colorBySpeed = colorBySpeed;
        this.displayTrack();
    }
}
