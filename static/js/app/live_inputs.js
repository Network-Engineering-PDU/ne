/**
 * Live Inputs Data - polls the backend every 2 seconds (same rate as PDU display)
 */

const CHARTS = {
    voltage: null,
    current: null,
    activePower: null,
    powerFactor: null,
};

const MAX_CHART_POINTS = 60;
const POLL_INTERVAL = 2000;

document.addEventListener('DOMContentLoaded', function () {
    initializeCharts();
    startLivePolling();
});

function initializeCharts() {
    function createChart(containerId) {
        const root = am5.Root.new(containerId);
        root.setThemes([am5themes_Animated.new(root)]);

        const chart = root.container.children.push(am5xy.XYChart.new(root, {
            panX: true,
            panY: true,
            wheelX: 'panX',
            wheelY: 'zoomX',
            maxTooltipDistance: 10,
            pinchZoomX: true,
        }));

        const xAxis = chart.xAxes.push(am5xy.DateAxis.new(root, {
            maxDeviation: 0.2,
            baseInterval: { timeUnit: 'second', count: 10 },
            renderer: am5xy.AxisRendererX.new(root, {}),
            tooltip: am5.Tooltip.new(root, {}),
        }));

        const yAxis = chart.yAxes.push(am5xy.ValueAxis.new(root, {
            renderer: am5xy.AxisRendererY.new(root, {}),
        }));

        for (let lineId = 1; lineId <= INPUTS_COUNT; lineId++) {
            const series = chart.series.push(am5xy.LineSeries.new(root, {
                name: `Input ${lineId}`,
                xAxis: xAxis,
                yAxis: yAxis,
                valueYField: 'value',
                valueXField: 'date',
                tooltip: am5.Tooltip.new(root, {
                    pointerOrientation: 'horizontal',
                    labelText: '[bold]{name}[/] {valueY}',
                }),
            }));
            series.strokes.template.setAll({ strokeWidth: 2 });
            series.data.setAll([]);
        }

        chart.appear(1000, 100);
        return chart;
    }

    CHARTS.voltage = createChart('chartVoltage');
    CHARTS.current = createChart('chartPhaseCurrent');
    CHARTS.activePower = createChart('chartActivePower');
    CHARTS.powerFactor = createChart('chartPowerFactor');
}

function startLivePolling() {
    fetchAndUpdateData();
    setInterval(fetchAndUpdateData, POLL_INTERVAL);
}

async function fetchAndUpdateData() {
    try {
        const response = await fetch(LIVE_DATA_URL);
        if (!response.ok) {
            console.error('Failed to fetch live data:', response.status);
            return;
        }

        const payload = await response.json();
        const inputs = payload.inputs || payload.data?.inputs || [];
        const result = (payload.result || '').toLowerCase();

        if (inputs.length && (result === 'ok' || result === 'success')) {
            inputs.forEach(updateInputTable);
            inputs.forEach(updateCharts);
        }
    } catch (error) {
        console.error('Error fetching live data:', error);
    }
}

function formatNumber(value) {
    if (value === null || value === undefined || value === '') {
        return '--';
    }
    const parsed = parseFloat(value);
    if (Number.isNaN(parsed)) {
        return '--';
    }
    return parsed.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
}

function updateInputTable(input) {
    const tabPane = document.querySelector(`#tab_${input.id}`);
    if (!tabPane) {
        return;
    }

    const fields = [
        'voltage',
        'current',
        'apparent_power',
        'active_power',
        'reactive_power',
        'power_factor',
        'energy',
        'phase_vi',
        'frequency',
    ];

    fields.forEach(function (fieldName) {
        const cell = tabPane.querySelector(`[data-field="${fieldName}"]`);
        if (cell) {
            cell.textContent = formatNumber(input[fieldName]);
        }
    });
}

function updateCharts(input) {
    const timestamp = input.timestamp || Date.now();
    addDataPointToChart('voltage', input.line_id, timestamp, input.voltage);
    addDataPointToChart('current', input.line_id, timestamp, input.current);
    addDataPointToChart('activePower', input.line_id, timestamp, input.active_power);
    addDataPointToChart('powerFactor', input.line_id, timestamp, input.power_factor);
}

function addDataPointToChart(chartKey, lineId, timestamp, value) {
    const chart = CHARTS[chartKey];
    if (!chart || !lineId) {
        return;
    }

    const series = chart.series.getIndex(lineId - 1);
    if (!series) {
        return;
    }

    const dataPoint = {
        date: timestamp,
        value: parseFloat(value) || 0,
    };

    let currentData = series.data.values || [];
    currentData.push(dataPoint);

    if (currentData.length > MAX_CHART_POINTS) {
        currentData = currentData.slice(-MAX_CHART_POINTS);
    }

    series.data.setAll(currentData);
}
