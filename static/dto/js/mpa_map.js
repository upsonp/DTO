class MPAMap {
    static #DEFAULT_ENDPOINTS = {
        parameters: '/api/mpa/{id}/parameters/',
        timeseries: '/api/mpa/{id}/timeseries/{parameter}/',
        latestDate: '/api/mpa/latest-date/',
        mpaZones: '/api/mpa-zones/geojson/'
    };

    constructor(mapId, options = {}) {
        this.endpoints = { ...MPAMap.#DEFAULT_ENDPOINTS, ...options.endpoints };
        this.selected_mpa = null;
        this.updateTimeout = null;
        this.initializeMap(mapId, options);
        this.initializeControls();
        this.initializeDateInputs();
        this.initializeModalDateListeners();
        this.chartObservers = [];
    }

    initializeMap(mapId, options) {
        this.map = L.map(mapId, {
            zoomControl: false,
            ...options
        }).setView([43.75, -63.0], 7);

        // Add base layers
        this.oceanLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Tiles © <a href="https://services.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer">ArcGIS</a>'
        }).addTo(this.map);

        this.satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Tiles © <a href="https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer">ArcGIS</a>'
        });

        // Add controls
        L.control.scale({ position: 'bottomright' }).addTo(this.map);
        L.control.zoom({ position: 'bottomright' }).addTo(this.map);
        L.control.layers({
            "Ocean": this.oceanLayer,
            "Satellite": this.satelliteLayer
        }).addTo(this.map);
    }

    initializeControls() {
        this.parameterSelect = document.getElementById('parameterSelect');
        this.loadButton = document.getElementById('loadDataBtn');

        this.parameterSelect.addEventListener('change', (e) => {
            this.loadButton.disabled = !e.target.value;
        });

        this.loadButton.addEventListener('click', () => this.loadTimeseriesData());
    }

    async initializeDateInputs() {
        try {
            const response = await fetch(this.endpoints.latestDate);
            const data = await response.json();
            document.getElementById('ts-start-date').value = data.start_date;
            document.getElementById('ts-end-date').value = data.end_date;
        } catch (error) {
            console.error('Error fetching date range:', error);
            // Fallback dates
            const endDate = new Date();
            const startDate = new Date();
            startDate.setFullYear(endDate.getFullYear() - 10);
            document.getElementById('ts-start-date').value = startDate.toISOString().split('T')[0];
            document.getElementById('ts-end-date').value = endDate.toISOString().split('T')[0];
        }
    }

    // Add this to your initialization method (e.g., constructor)
    initializeModalDateListeners() {
        const modalStartDate = document.getElementById('modal-start-date');
        const modalEndDate = document.getElementById('modal-end-date');
        const modalSelectedDate = document.getElementById('modal-selected-date');

        const debouncedUpdate = () => {
            clearTimeout(this.updateTimeout);
            this.updateTimeout = setTimeout(() => {
                // Update accordion dates
                document.getElementById('ts-start-date').value = modalStartDate.value;
                document.getElementById('ts-end-date').value = modalEndDate.value;
                document.getElementById('ts-selected-date').value = modalSelectedDate.value;

                // Load data and notify all charts
                this.loadTimeseriesData();
            }, 500);
        };

        modalStartDate.addEventListener('change', debouncedUpdate);
        modalEndDate.addEventListener('change', debouncedUpdate);
        modalSelectedDate.addEventListener('change', () => {
            // Update selected date in all charts
            const date = new Date(modalSelectedDate.value);
            this.chartObservers.forEach(chart => {
                chart.updateSelectedDate(date);
            });
        });
    }

    // Add this method to handle MPA feature interactions
    onEachFeature(feature, layer) {
        layer.on('click', (e) => {
            if (this.selected_mpa) {
                this.selected_mpa.setStyle(this.mpaStyle);
            }
            layer.setStyle(this.highlightStyle);
            this.selected_mpa = layer;
            this.selected_mpa.feature = feature;  // Store feature for later use

            // Show content
            document.getElementById('noMpaSelected').style.display = 'none';
            document.getElementById('timeseriesContent').style.display = 'block';

            // Store current parameter selection
            const parameterSelect = document.getElementById('parameterSelect');
            const currentParameter = parameterSelect.value;

            // Show loading state
            parameterSelect.disabled = true;

            // Use endpoint constant with parameter substitution
            const parametersUrl = this.endpoints.parameters.replace('{id}', feature.id);
            fetch(parametersUrl)
                .then(response => response.json())
                .then(data => {
                    // Clear existing options except the placeholder
                    parameterSelect.innerHTML = '<option value="">Choose parameter...</option>';

                    // Add new options
                    data.parameters.forEach(param => {
                        const option = document.createElement('option');
                        option.value = param.value;
                        option.textContent = param.label;
                        parameterSelect.appendChild(option);
                    });

                    // Restore previous selection if it exists in new options
                    if (currentParameter && data.parameters.some(p => p.value === currentParameter)) {
                        parameterSelect.value = currentParameter;
                        this.loadButton.disabled = false;
                    } else {
                        this.loadButton.disabled = true;
                    }

                    parameterSelect.disabled = false;
                })
                .catch(error => {
                    console.error('Error fetching parameters:', error);
                    parameterSelect.disabled = false;
                });
        });

        // Add tooltip
        layer.bindTooltip((layer) => {
            const props = feature.properties;
            return `<strong>${props.mpa_name}</strong><br>
                    Area: ${props.area_km2.toFixed(2)} km²`;
        }, {
            permanent: false,
            direction: 'auto',
            className: 'mpa-tooltip'
        });
    }

    async loadMPAZones() {
        const loadingElement = document.getElementById('map-loading');
        loadingElement.style.display = 'block';

        try {
            const response = await fetch(this.endpoints.mpaZones);
            const data = await response.json();
            data.features.sort((a, b) => b.properties.area_km2 - a.properties.area_km2);

            L.geoJSON(data, {
                style: this.mpaStyle,
                onEachFeature: (feature, layer) => this.onEachFeature(feature, layer)
            }).addTo(this.map);
        } catch (error) {
            console.error('Error:', error);
        } finally {
            loadingElement.style.display = 'none';
        }
    }

    async loadTimeseriesData() {
        if (!this.selected_mpa) return;

        const parameter = this.parameterSelect.value;
        if (!parameter) return;

        const startDate = document.getElementById('ts-start-date').value;
        const endDate = document.getElementById('ts-end-date').value;
        const selectedDate = document.getElementById('ts-selected-date').value;

        document.getElementById('modal-start-date').value = startDate;
        document.getElementById('modal-end-date').value = endDate;
        document.getElementById('modal-selected-date').value = selectedDate;

        const mpa_id = this.selected_mpa.feature.id;

        // Clear previous chart and use correct element ID
        const chartElement = document.getElementById('modalTimeseriesChart');
        chartElement.innerHTML = '';
        this.loadButton.disabled = true;

        try {
            const url = this.endpoints.timeseries
                .replace('{id}', mpa_id)
                .replace('{parameter}', parameter) +
                `?start_date=${startDate}&end_date=${endDate}`;

            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            // Instead of directly rendering to timeseriesChart
            this.notifyChartObservers(data);
        } catch (error) {
            console.error('Error fetching timeseries:', error);
            chartElement.innerHTML = '<div class="alert alert-danger">Error loading chart data</div>';
        } finally {
            this.loadButton.disabled = false;
        }
    }

    // Add method to register charts
    addChartObserver(chart) {
        this.chartObservers.push(chart);
    }

    // Add method to notify all charts
    notifyChartObservers(data) {
        this.chartObservers.forEach(chart => {
            chart.render(data);
        });
    }

    mpaStyle = {
        fillColor: '#ff4d4d',
        fillOpacity: 0.3,
        color: '#ffffff',
        weight: 2,
        opacity: 1
    };

    highlightStyle = {
        fillColor: '#ff4d4d',
        fillOpacity: 0.6,
        color: '#ffff00',
        weight: 3,
        opacity: 1
    };
}