class TimeseriesChart {

    ds_timeseries = {
        label: 'Timeseries',
        data: [],
        borderColor: '#F44',
        borderWidth: 1.5,
        pointRadius: 0
    };

    ds_climatology = {
        label: 'Climatology (1993-2022)',
        data: [],
        borderColor: '#000',
        borderWidth: 1.5,
        borderDash: [5, 5],
        fill: {
            target: '0',
            above: 'rgba(150, 150, 255, 0.4)',
            below: 'rgba(255, 150, 150, 0.4)',
        },
        pointRadius: 0
    };

    upper_limit = {
        label: '90th Percentile',
        data: [],
        backgroundColor: 'rgba(128, 128, 128, 0.4)',
        borderColor: '#666',
        borderWidth: 1,
        borderDash: [2, 2],
        fill: {
            target: '0',
            below: 'rgba(255, 75, 75)',
        },
        pointRadius: 0
    };

    lower_limit = {
        label: '10th Percentile',
        data: [],
        backgroundColor: 'rgba(128, 128, 128, 0.4)',
        borderColor: '#666',
        borderWidth: 1,
        borderDash: [2, 2],
        fill: {
            target: '0',
            above: 'blue',
        },
        pointRadius: 0
    };

    constructor(elementId) {
        this.elementId = elementId;
        this.resizeObserver = new ResizeObserver(entries => {
            if (this.chart) {
                this.chart.resize();
            }
        });

        // Create modal once
        const modalElm = document.getElementById('chartModal');
        this.modal = new bootstrap.Modal(modalElm);
        this.selectedDate = null;
    }

    render(data) {
        console.log('Rendering chart with data:', data);
        const element = document.getElementById(this.elementId);
        if (!element) {
            console.error(`Element with id ${this.elementId} not found`);
            return;
        }

        if (this.chart) {
            this.chart.destroy();
            this.chart = null;
        }

        element.innerHTML = '<canvas style="height: 60vh !important;"></canvas>';
        const ctx = element.querySelector('canvas').getContext('2d');

        // Start observing size changes
        this.resizeObserver.observe(element);

        // Process the data first - without chart update
        this.prepareData(data);

        // Set initial selected date to end date from input
        if (!this.selectedDate) {
            const endDateStr = document.getElementById('modal-end-date').value;
            this.selectedDate = new Date(endDateStr);

            // Update both date inputs
            document.getElementById('modal-selected-date').value = endDateStr;
            document.getElementById('ts-selected-date').value = endDateStr;
        }

        // Create chart with processed data
        this.createChart(ctx, data.parameter);

        // Update the progress bar for initial date
        if (this.selectedDate) {
            this.updateSelectedDate(this.selectedDate);
        }

        this.modal.show();
    }

    prepareData(data) {
        this.statsData = data.stats;

        // Clear existing data
        this.ds_timeseries.data = [];
        this.ds_climatology.data = [];
        this.upper_limit.data = [];
        this.lower_limit.data = [];

        // Process timeseries and climatology
        data.timeseries.forEach(d => {
            const date = new Date(d.timestamp);
            const dayOfYear = Math.floor((date - new Date(date.getFullYear(), 0, 0)) / (1000 * 60 * 60 * 24));
            const climatologyData = data.climatology.find(c => c.day_of_year === dayOfYear);

            this.ds_timeseries.data.push({ x: date, y: d.value });
            if (climatologyData) {
                this.ds_climatology.data.push({ x: date, y: climatologyData.avg_value });
                this.upper_limit.data.push({ x: date, y: climatologyData.p90 });
                this.lower_limit.data.push({ x: date, y: climatologyData.p10 });
            }
        });
    }

    // Helper function to find nearest data point
    findNearestPoint(data, targetDate) {
        return data.reduce((nearest, current) => {
            const currentDiff = Math.abs(current.x.getTime() - targetDate.getTime());
            const nearestDiff = Math.abs(nearest.x.getTime() - targetDate.getTime());
            return currentDiff < nearestDiff ? current : nearest;
        }, data[0]);
    }

    date_selected_handler(e, elements, chart) {
        const canvasPosition = Chart.helpers.getRelativePosition(e, chart);
        const timestamp = chart.scales.x.getValueForPixel(canvasPosition.x);
        const date = new Date(timestamp);

        this.updateSelectedDate(date)

        // Update input field with formatted date
        const dateStr = date.toISOString().split('T')[0];

        document.getElementById('modal-selected-date').value = dateStr;

    }

    updateSelectedDate(date) {

        // Find the nearest data points
        const timeseriesPoint = this.findNearestPoint(this.ds_timeseries.data, date);
        const climatologyPoint = this.findNearestPoint(this.ds_climatology.data, date);
        const upperLimit = this.findNearestPoint(this.upper_limit.data, date);
        const lowerLimit = this.findNearestPoint(this.lower_limit.data, date);

        if (timeseriesPoint && climatologyPoint && upperLimit && lowerLimit) {
            const globalRange = this.statsData.max_difference - this.statsData.min_difference;
            const diff = timeseriesPoint.y - climatologyPoint.y;
            // Calculate position as percentage between min and max difference
            const position = ((diff - this.statsData.min_difference) / globalRange) * 100;

            // Ensure position stays within 0-100 range
            const clampedPosition = Math.min(Math.max(position, 0), 100);

            // Update progress bar
            const progressBar = document.getElementById('climatology-progress');
            progressBar.style.width = `${clampedPosition}%`;
            progressBar.setAttribute('aria-valuenow', clampedPosition);

            // Set color based on percentile position
            if (timeseriesPoint.y < lowerLimit.y) {
                progressBar.className = 'progress-bar bg-primary'; // Blue
            } else if (timeseriesPoint.y > upperLimit.y) {
                progressBar.className = 'progress-bar bg-danger';  // Red
            } else {
                progressBar.className = 'progress-bar bg-success'; // Green
            }

            // Add tooltip text
            progressBar.textContent = `${diff.toFixed(2)} ${diff >= 0 ? 'above' : 'below'} average`;
        }

        // Update selected date
        this.selectedDate = date;

        // Update vertical line
        this.chart.options.plugins.annotation.annotations.verticalLine.value = date;
        this.chart.update();

        // Update input field with formatted date
        const dateStr = date.toISOString().split('T')[0];
        document.getElementById('ts-selected-date').value = dateStr;
    }

    createChart(ctx, parameter) {
        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [
                    this.ds_timeseries,
                    this.ds_climatology,
                    this.upper_limit,
                    this.lower_limit,
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                onClick: (e, elements, chart) => this.date_selected_handler(e, elements, chart),  // Fix context binding
                plugins: {
                    title: {
                        display: true,
                        text: `${parameter} Time Series`
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    },
                    annotation: {
                        annotations: {
                            verticalLine: {
                                type: 'line',
                                scaleID: 'x',
                                borderColor: 'rgba(0, 0, 0, 0.5)',
                                borderWidth: 2,
                                value: this.selectedDate,
                                display: true
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'month'
                        },
                        title: {
                            display: true,
                            text: 'Date'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: parameter
                        }
                    }
                }
            }
        });
    }
}