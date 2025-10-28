/**
 * Interactive Sailing Track Viewer
 * Main application script that ties everything together
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize components
    const gpxParser = new GpxParser();
    const trackAnalyzer = new TrackAnalyzer();
    const mapController = new MapController('map');
    
    // DOM elements
    const gpxFileInput = document.getElementById('gpx-file');
    const markersFileInput = document.getElementById('markers-file');
    const windDirectionInput = document.getElementById('wind-direction');
    const loadDataButton = document.getElementById('load-data');
    
    const timeSlider = document.getElementById('time-slider-range');
    const startTimeLabel = document.getElementById('start-time');
    const endTimeLabel = document.getElementById('end-time');
    const playPauseButton = document.getElementById('play-pause');
    const playbackSpeedInput = document.getElementById('playback-speed');
    
    const distanceValue = document.getElementById('distance-value');
    const durationValue = document.getElementById('duration-value');
    const avgSpeedValue = document.getElementById('avg-speed-value');
    const maxSpeedValue = document.getElementById('max-speed-value');
    const avgWindAngleValue = document.getElementById('avg-wind-angle-value');
    const tackCountValue = document.getElementById('tack-count-value');
    const windRoseChart = document.getElementById('wind-rose-chart');
    
    const showTrackCheckbox = document.getElementById('show-track');
    const showMarkersCheckbox = document.getElementById('show-markers');
    const showWindCheckbox = document.getElementById('show-wind');
    const colorBySpeedCheckbox = document.getElementById('color-by-speed');
    
    // Track data
    let trackData = null;
    let markersData = null;
    let selectedStartTime = null;
    let selectedEndTime = null;
    let isPlaying = false;
    let playbackTimer = null;
    let currentPlaybackIndex = 0;
    
    // Initialize UI components
    initializeUI();
    
    // Initialize tooltips
    initializeTooltips();
    
    /**
     * Initialize UI components and event listeners
     */
    function initializeUI() {
        // Load data button
        loadDataButton.addEventListener('click', loadData);
        
        // Display options
        showTrackCheckbox.addEventListener('change', updateDisplayOptions);
        showMarkersCheckbox.addEventListener('change', updateDisplayOptions);
        showWindCheckbox.addEventListener('change', updateDisplayOptions);
        colorBySpeedCheckbox.addEventListener('change', updateDisplayOptions);
        
        // Play/pause button
        playPauseButton.addEventListener('click', togglePlayback);
        
        // Disable time controls initially
        disableTimeControls(true);
    }
    
    /**
     * Load data from files
     */
    async function loadData() {
        try {
            // Show loading state
            loadDataButton.textContent = 'Loading...';
            loadDataButton.disabled = true;
            
            // Load GPX file
            if (gpxFileInput.files.length === 0) {
                alert('Please select a GPX or JSON track file');
                resetLoadingState();
                return;
            }
            
            // Parse GPX file
            trackData = await gpxParser.parseGpxFile(gpxFileInput.files[0]);
            
            // Set track data to analyzer and map controller
            trackAnalyzer.setTrackData(trackData);
            mapController.setTrackData(trackData);
            
            // Load markers file if provided
            if (markersFileInput.files.length > 0) {
                const reader = new FileReader();
                
                reader.onload = function(e) {
                    try {
                        markersData = JSON.parse(e.target.result);
                        mapController.setMarkersData(markersData);
                    } catch (error) {
                        console.error('Error parsing markers file:', error);
                        alert('Error parsing markers file: ' + error.message);
                    }
                };
                
                reader.onerror = function() {
                    console.error('Error reading markers file');
                    alert('Error reading markers file');
                };
                
                reader.readAsText(markersFileInput.files[0]);
            }
            
            // Set wind direction
            const windDirection = parseInt(windDirectionInput.value) || 0;
            trackAnalyzer.setWindDirection(windDirection);
            mapController.setWindDirection(windDirection);
            
            // Initialize time slider
            initializeTimeSlider();
            
            // Calculate and display metrics
            updateMetrics();
            
            // Enable time controls
            disableTimeControls(false);
            
            // Reset loading state
            resetLoadingState();
        } catch (error) {
            console.error('Error loading data:', error);
            alert('Error loading data: ' + error.message);
            resetLoadingState();
        }
    }
    
    /**
     * Reset loading button state
     */
    function resetLoadingState() {
        loadDataButton.textContent = 'Load Data';
        loadDataButton.disabled = false;
    }
    
    /**
     * Initialize time slider with track time range
     */
    function initializeTimeSlider() {
        if (!trackData || !trackData.startTime || !trackData.endTime) {
            return;
        }
        
        // Get time range
        const startTime = trackData.startTime;
        const endTime = trackData.endTime;
        
        // Set initial selected times
        selectedStartTime = startTime;
        selectedEndTime = endTime;
        
        // Update time labels
        updateTimeLabels();
        
        // Initialize jQuery UI slider
        $(timeSlider).slider({
            range: true,
            min: startTime.getTime(),
            max: endTime.getTime(),
            values: [startTime.getTime(), endTime.getTime()],
            step: 1000, // 1 second steps
            slide: function(event, ui) {
                // Update selected times
                selectedStartTime = new Date(ui.values[0]);
                selectedEndTime = new Date(ui.values[1]);
                
                // Update time labels
                updateTimeLabels();
                
                // Update track display and metrics
                updateTrackDisplay();
                updateMetrics();
            }
        });
    }
    
    /**
     * Update time labels with selected time range
     */
    function updateTimeLabels() {
        if (!selectedStartTime || !selectedEndTime) {
            startTimeLabel.textContent = 'Start: --:--:--';
            endTimeLabel.textContent = 'End: --:--:--';
            return;
        }
        
        startTimeLabel.textContent = 'Start: ' + selectedStartTime.toLocaleTimeString();
        endTimeLabel.textContent = 'End: ' + selectedEndTime.toLocaleTimeString();
    }
    
    /**
     * Update track display based on selected time range
     */
    function updateTrackDisplay() {
        if (!trackData || !trackData.points) {
            return;
        }
        
        // Filter points by selected time range
        const filteredPoints = trackData.points.filter(point => 
            point.time >= selectedStartTime && point.time <= selectedEndTime
        );
        
        // Update track display
        mapController.displayTrack(filteredPoints);
    }
    
    /**
     * Update metrics based on selected time range
     */
    function updateMetrics() {
        if (!trackData || !trackData.points) {
            return;
        }
        
        // Calculate metrics for selected time range
        const metrics = trackAnalyzer.calculateMetrics(selectedStartTime, selectedEndTime);
        
        // Update metrics display
        distanceValue.textContent = (metrics.distance / 1000).toFixed(2) + ' km';
        durationValue.textContent = formatDuration(metrics.duration);
        avgSpeedValue.textContent = metrics.avgSpeed.toFixed(1) + ' knots';
        maxSpeedValue.textContent = metrics.maxSpeed.toFixed(1) + ' knots';
        avgWindAngleValue.textContent = metrics.avgWindAngle.toFixed(0) + '°';
        tackCountValue.textContent = metrics.tacks;
        
        // Update wind rose chart
        updateWindRoseChart(metrics.windAngles);
    }
    
    /**
     * Update wind rose chart with wind angles
     * @param {Array} windAngles - Array of wind angles
     */
    function updateWindRoseChart(windAngles) {
        // Clear existing chart
        windRoseChart.innerHTML = '';
        
        if (!windAngles || windAngles.length === 0) {
            return;
        }
        
        // Create wind rose using D3.js
        const width = windRoseChart.clientWidth;
        const height = windRoseChart.clientHeight;
        const radius = Math.min(width, height) / 2 - 10;
        
        // Group wind angles into bins (0-30, 30-60, 60-90, 90-120, 120-150, 150-180)
        const bins = [0, 0, 0, 0, 0, 0];
        
        windAngles.forEach(angle => {
            const binIndex = Math.min(Math.floor(angle / 30), 5);
            bins[binIndex]++;
        });
        
        // Normalize bins
        const maxBin = Math.max(...bins);
        const normalizedBins = bins.map(bin => bin / maxBin);
        
        // Create SVG
        const svg = d3.select(windRoseChart)
            .append('svg')
            .attr('width', width)
            .attr('height', height)
            .append('g')
            .attr('transform', `translate(${width/2}, ${height/2})`);
        
        // Create scale
        const angleScale = d3.scaleLinear()
            .domain([0, 180])
            .range([0, Math.PI]);
        
        // Create arc generator
        const arc = d3.arc()
            .innerRadius(0)
            .outerRadius((d, i) => normalizedBins[i] * radius)
            .startAngle((d, i) => angleScale(i * 30))
            .endAngle((d, i) => angleScale((i + 1) * 30));
        
        // Draw arcs
        svg.selectAll('path')
            .data(normalizedBins)
            .enter()
            .append('path')
            .attr('d', arc)
            .attr('fill', (d, i) => d3.interpolateBlues(0.3 + d * 0.7))
            .attr('stroke', '#fff')
            .attr('stroke-width', 1);
        
        // Add axis lines
        for (let i = 0; i <= 6; i++) {
            const angle = i * 30;
            const radians = angleScale(angle);
            const x = Math.sin(radians) * radius;
            const y = -Math.cos(radians) * radius;
            
            svg.append('line')
                .attr('x1', 0)
                .attr('y1', 0)
                .attr('x2', x)
                .attr('y2', y)
                .attr('stroke', '#ccc')
                .attr('stroke-width', 1)
                .attr('stroke-dasharray', '2,2');
            
            svg.append('text')
                .attr('x', Math.sin(radians) * (radius + 10))
                .attr('y', -Math.cos(radians) * (radius + 10))
                .attr('text-anchor', 'middle')
                .attr('dominant-baseline', 'middle')
                .attr('font-size', '10px')
                .text(angle + '°');
        }
    }
    
    /**
     * Toggle playback of track
     */
    function togglePlayback() {
        if (isPlaying) {
            stopPlayback();
        } else {
            startPlayback();
        }
    }
    
    /**
     * Start playback animation
     */
    function startPlayback() {
        if (!trackData || !trackData.points || trackData.points.length === 0) {
            return;
        }
        
        // Set playing state
        isPlaying = true;
        playPauseButton.querySelector('i').classList.remove('play-icon');
        playPauseButton.querySelector('i').classList.add('pause-icon');
        
        // Get filtered points
        const filteredPoints = trackData.points.filter(point => 
            point.time >= selectedStartTime && point.time <= selectedEndTime
        );
        
        if (filteredPoints.length === 0) {
            stopPlayback();
            return;
        }
        
        // Start from beginning
        currentPlaybackIndex = 0;
        
        // Get playback speed (1-10)
        const playbackSpeed = parseInt(playbackSpeedInput.value) || 5;
        
        // Start playback timer
        playbackTimer = setInterval(() => {
            // Update current position
            mapController.updateCurrentPosition(filteredPoints[currentPlaybackIndex]);
            
            // Increment index
            currentPlaybackIndex++;
            
            // Stop if reached end
            if (currentPlaybackIndex >= filteredPoints.length) {
                stopPlayback();
            }
        }, 1000 / playbackSpeed);
    }
    
    /**
     * Stop playback animation
     */
    function stopPlayback() {
        // Clear timer
        if (playbackTimer) {
            clearInterval(playbackTimer);
            playbackTimer = null;
        }
        
        // Reset playing state
        isPlaying = false;
        playPauseButton.querySelector('i').classList.add('play-icon');
        playPauseButton.querySelector('i').classList.remove('pause-icon');
    }
    
    /**
     * Update display options based on checkboxes
     */
    function updateDisplayOptions() {
        mapController.toggleTrack(showTrackCheckbox.checked);
        mapController.toggleMarkers(showMarkersCheckbox.checked);
        mapController.toggleWind(showWindCheckbox.checked);
        mapController.setColorBySpeed(colorBySpeedCheckbox.checked);
    }
    
    /**
     * Enable or disable time controls
     * @param {boolean} disabled - Whether controls should be disabled
     */
    function disableTimeControls(disabled) {
        // Disable slider
        $(timeSlider).slider(disabled ? 'disable' : 'enable');
        
        // Disable playback controls
        playPauseButton.disabled = disabled;
        playbackSpeedInput.disabled = disabled;
    }
    
    /**
     * Format time duration as HH:MM:SS
     * @param {number} seconds - Duration in seconds
     * @returns {string} - Formatted time string
     */
    function formatDuration(seconds) {
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
     * Initialize tooltips for info icons
     */
    function initializeTooltips() {
        // Setup tooltips for each info icon
        setupTooltip('gpx-info', 'gpx-tooltip');
        setupTooltip('markers-info', 'markers-tooltip');
        setupTooltip('wind-info', 'wind-tooltip');
        
        // Close tooltips when clicking elsewhere
        document.addEventListener('click', function() {
            document.querySelectorAll('.tooltip').forEach(tooltip => {
                tooltip.classList.remove('visible');
            });
        });
    }
    
    /**
     * Setup tooltip functionality for an info icon
     * @param {string} infoId - ID of the info icon element
     * @param {string} tooltipId - ID of the tooltip element
     */
    function setupTooltip(infoId, tooltipId) {
        const infoIcon = document.getElementById(infoId);
        const tooltip = document.getElementById(tooltipId);
        
        if (infoIcon && tooltip) {
            // Toggle tooltip visibility on click
            infoIcon.addEventListener('click', function(e) {
                e.stopPropagation();
                
                // Close all other tooltips first
                document.querySelectorAll('.tooltip').forEach(t => {
                    if (t.id !== tooltipId) {
                        t.classList.remove('visible');
                    }
                });
                
                // Toggle this tooltip
                tooltip.classList.toggle('visible');
            });
            
            // Prevent tooltip from closing when clicking inside it
            tooltip.addEventListener('click', function(e) {
                e.stopPropagation();
            });
        }
    }
});
