/**
 * Live Inputs Data - Real-time polling and display
 * Polls every 2 seconds and updates tables and charts dynamically
 */

// Store for chart instances and data
const CHARTS = {
    voltage: null,
    current: null,
    activePower: null,
    powerFactor: null,
};

// Store for chart data series (keep last 60 data points for smooth scrolling)
const CHART_DATA = {
    voltage: [],
    current: [],
    activePower: [],
    powerFactor: [],
};

const MAX_CHART_POINTS = 60;

// Poll interval: 2000ms (2 seconds)
const POLL_INTERVAL = 2000;

// Store input mapping for easier access
let inputsMap = {};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing live inputs...');
    
    // Initialize charts
    initializeCharts();
    
    // Start polling
    startLivePolling();
});

/**
 * Initialize AmCharts for live updates
 */
function initializeCharts() {
    console.log('Initializing charts...');
    
    // Chart configuration factory
    function createChart(containerId, dataKey, unit) {
        let root = am5.Root.new(containerId);
        root.setThemes([am5themes_Animated.new(root)]);
        
        let chart = root.container.children.push(am5xy.XYChart.new(root, {
            panX: true,
            panY: true,
            wheelX: "panX",
            wheelY: "zoomX",
            maxTooltipDistance: 10,
            pinchZoomX: true,
        }));
        
        // X-axis (time)
        let xAxis = chart.xAxes.push(am5xy.DateAxis.new(root, {
            maxDeviation: 0.2,
            baseInterval: { timeUnit: "second", count: 10 },
            renderer: am5xy.AxisRendererX.new(root, {}),
            tooltip: am5.Tooltip.new(root, {}),
        }));
        
        // Y-axis (values)
        let yAxis = chart.yAxes.push(am5xy.ValueAxis.new(root, {
            renderer: am5xy.AxisRendererY.new(root, {}),
        }));
        
        // Add series for each input
        for (let inputId = 1; inputId <= INPUTS_COUNT; inputId++) {
            let series = chart.series.push(am5xy.LineSeries.new(root, {
                name: `Input ${inputId}`,
                xAxis: xAxis,
                yAxis: yAxis,
                valueYField: "value",
                valueXField: "date",
                tooltip: am5.Tooltip.new(root, {
                    pointerOrientation: "horizontal",
                    labelText: "[bold]{name}[/] {value}",
                }),
            }));
            
            series.strokes.template.setAll({
                strokeWidth: 2,
            });
            
            // Store empty data
            series.data.setAll([]);
        }
        
        // Animate on load
        chart.appear(1000, 100);
        
        return { root, chart };
    }
    
    // Create all charts
    const chartConfigs = [
        { id: 'chartVoltage', key: 'voltage', unit: 'V' },
        { id: 'chartPhaseCurrent', key: 'current', unit: 'A' },
        { id: 'chartActivePower', key: 'activePower', unit: 'W' },
        { id: 'chartPowerFactor', key: 'powerFactor', unit: '' },
    ];
    
    chartConfigs.forEach(config => {
        const chartObj = createChart(config.id, config.key, config.unit);
        CHARTS[config.key] = chartObj.chart;
    });
}

/**
 * Start polling for live data every 2 seconds
 */
function startLivePolling() {
    console.log('Starting live polling...');
    
    // Fetch immediately on start
    fetchAndUpdateData();
    
    // Then poll every 2 seconds
    setInterval(fetchAndUpdateData, POLL_INTERVAL);
}

/**
 * Fetch live data from API and update UI
 */
async function fetchAndUpdateData() {
    try {
        const response = await fetch(LIVE_DATA_URL);
        if (!response.ok) {
            console.error('Failed to fetch live data:', response.status);
            return;
        }
        
        const data = await response.json();
        if (data.result === 'OK' && data.data && data.data.inputs) {
            const inputs = data.data.inputs;
            
            // Update each input tab
            inputs.forEach(input => {
                updateInputTable(input);
                updateCharts(input);
            });
        }
    } catch (error) {
        console.error('Error fetching live data:', error);
    }
}

/**
 * Update input table with new values
 */
function updateInputTable(input) {
    const tabPane = document.querySelector(`#tab_${input.id}`);
    if (!tabPane) return;
    
    // Format number with 2 decimals and commas
    const formatNumber = (value) => {
        if (value === null || value === undefined) return '--';
        return parseFloat(value).toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    };
    
    // Update all fields in the table
    const fields = [
        { name: 'voltage', value: input.voltage },
        { name: 'current', value: input.current },
        { name: 'apparent_power', value: input.apparent_power },
        { name: 'active_power', value: input.active_power },
        { name: 'reactive_power', value: input.reactive_power },
        { name: 'power_factor', value: input.power_factor },
        { name: 'energy', value: input.energy },
        { name: 'phase_vi', value: input.phase_vi },
        { name: 'frequency', value: input.frequency },
    ];
    
    fields.forEach(field => {
        const cell = tabPane.querySelector(`[data-field="${field.name}"]`);
        if (cell) {
            cell.textContent = formatNumber(field.value);
            // Add a subtle flash effect on update
            cell.style.backgroundColor = '#c8e6c9';
            setTimeout(() => {
                cell.style.transition = 'background-color 0.5s ease';
                cell.style.backgroundColor = 'transparent';
            }, 50);
        }
    });
}

/**
 * Update charts with new data point
 */
function updateCharts(input) {
    const timestamp = input.timestamp || new Date().getTime();
    
    // Add data to each chart's data array
    const dataPoint = {
        date: new Date(timestamp),
        value: input,
    };
    
    // Update voltage chart
    addDataPointToChart('voltage', input.id, timestamp, input.voltage);
    
    // Update current chart
    addDataPointToChart('current', input.id, timestamp, input.current);
    
    // Update active power chart
    addDataPointToChart('activePower', input.id, timestamp, input.active_power);
    
    // Update power factor chart
    addDataPointToChart('powerFactor', input.id, timestamp, input.power_factor);
}

/**
 * Add a single data point to a chart
 */
function addDataPointToChart(chartKey, inputId, timestamp, value) {
    const chart = CHARTS[chartKey];
    if (!chart) return;
    
    // Find the correct series for this input (series are added in order 1, 2, 3...)
    const series = chart.series.getIndex(inputId - 1);
    if (!series) return;
    
    // Create data point
    const dataPoint = {
        date: new Date(timestamp),
        value: parseFloat(value) || 0,
    };
    
    // Add to series data
    let currentData = series.data.values || [];
    currentData.push(dataPoint);
    
    // Keep only last MAX_CHART_POINTS
    if (currentData.length > MAX_CHART_POINTS) {
        currentData = currentData.slice(-MAX_CHART_POINTS);
    }
    
    // Update series with new data
    series.data.setAll(currentData);
}

/**
 * Format number with 2 decimals and locale-specific formatting
 */
function formatNumber(value) {
    if (value === null || value === undefined) return '--';
    return parseFloat(value).toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}
