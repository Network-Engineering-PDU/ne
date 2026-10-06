/**
 * Live Inputs Data - polls every 2 seconds, plots Input 1-6 on all charts
 */

const CHARTS = {
    voltage: null,
    current: null,
    activePower: null,
    powerFactor: null,
};

const MAX_CHART_POINTS = 60;
const POLL_INTERVAL = 2000;
const INPUT_SERIES_COUNT = typeof INPUTS_COUNT !== 'undefined' ? INPUTS_COUNT : 6;

const CHART_CONFIGS = [
    { key: 'voltage', containerId: 'chartVoltage', field: 'voltage', unit: 'V' },
    { key: 'current', containerId: 'chartPhaseCurrent', field: 'current', unit: 'A' },
    { key: 'activePower', containerId: 'chartActivePower', field: 'active_power', unit: 'W' },
    { key: 'powerFactor', containerId: 'chartPowerFactor', field: 'power_factor', unit: '' },
];

let chartsReady = false;

if (typeof am5 !== 'undefined' && typeof am5.ready === 'function') {
    am5.ready(function () {
        try {
            initializeCharts();
            chartsReady = true;
            startLivePolling();
        } catch (error) {
            console.error('Chart init failed:', error);
            startLivePolling();
        }
    });
} else {
    document.addEventListener('DOMContentLoaded', startLivePolling);
}

function initializeCharts() {
    CHART_CONFIGS.forEach(function (config) {
        CHARTS[config.key] = createChart(config.containerId, config.unit);
    });
}

function createChart(containerId, unit) {
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

    for (let lineId = 1; lineId <= INPUT_SERIES_COUNT; lineId++) {
        const series = chart.series.push(am5xy.LineSeries.new(root, {
            name: `Input ${lineId}`,
            xAxis: xAxis,
            yAxis: yAxis,
            valueYField: 'value',
            valueXField: 'date',
            tooltip: am5.Tooltip.new(root, {
                pointerOrientation: 'horizontal',
                labelText: `[bold]{name}[/]: {valueY} ${unit}`,
            }),
        }));
        series.strokes.template.setAll({ strokeWidth: 2 });
        series.data.setAll([]);
        series.appear();
    }

    const cursor = chart.set('cursor', am5xy.XYCursor.new(root, { behavior: 'none' }));
    cursor.lineY.set('visible', false);

    const legend = chart.rightAxesContainer.children.push(
        am5.Legend.new(root, { height: am5.percent(100) })
    );

    legend.itemContainers.template.events.on('pointerout', function () {
        chart.series.each(function (chartSeries) {
            chartSeries.strokes.template.setAll({
                strokeOpacity: 1,
                strokeWidth: 2,
                stroke: chartSeries.get('fill'),
            });
        });
    });

    legend.itemContainers.template.set('width', am5.p100);
    legend.valueLabels.template.setAll({
        width: am5.p100,
        textAlign: 'right',
    });

    legend.data.setAll(chart.series.values);
    chart.appear(1000, 100);

    return chart;
}

function startLivePolling() {
    const initial = JSON.parse(document.getElementById('initialLayout').textContent);
    renderLayout(initial);
    fetchAndUpdateData();
    setInterval(fetchAndUpdateData, POLL_INTERVAL);
}

async function fetchAndUpdateData() {
    try {
        const response = await fetch(LIVE_DATA_URL, {
            credentials: 'same-origin',
            headers: { Accept: 'application/json' },
        });

        if (!response.ok) {
            console.error('Failed to fetch live data:', response.status, LIVE_DATA_URL);
            return;
        }

        const payload = await response.json();
        const layout = payload.layout || null;
        renderLayout(layout);
        if (!layout) {
            return;
        }

        // Only the inputs selected by the DIP switches are shown, summed and charted
        const active = new Set(layout.active_line_ids);
        const activeInputs = (payload.inputs || []).filter(function (input) {
            return active.has(input.line_id);
        });
        updateValues(activeInputs);
        if (chartsReady) {
            activeInputs.forEach(updateCharts);
        }
    } catch (error) {
        console.error('Error fetching live data:', error);
    }
}

const VALUE_FIELDS = [
    'voltage', 'current', 'apparent_power', 'active_power',
    'reactive_power', 'power_factor', 'phase_vi', 'frequency', 'energy',
];
let renderedLayoutKey = null;

function escapeText(value) {
    return String(value).replace(/[&<>"']/g, function (c) {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
}

// Builds the power info and one card per branch, with a column per phase
function renderLayout(layout) {
    const unavailable = document.getElementById('inputsUnavailable');
    const cards = document.getElementById('branchCards');
    const key = JSON.stringify(layout);
    if (key === renderedLayoutKey) {
        return;
    }
    renderedLayoutKey = key;

    if (!layout) {
        cards.innerHTML = '';
        unavailable.hidden = false;
        ['infoBranch', 'infoType', 'infoCurrent'].forEach(function (id) {
            document.getElementById(id).textContent = '-';
        });
        return;
    }
    unavailable.hidden = true;
    document.getElementById('infoBranch').textContent = layout.branch_label;
    document.getElementById('infoType').textContent = layout.type_label;
    document.getElementById('infoCurrent').textContent = layout.current_type_label || '-';

    const csvUrls = JSON.parse(document.getElementById('inputCsvUrls').textContent);
    cards.innerHTML = layout.branches.map(function (branch) {
        const head = branch.phases.map(function (phase) {
            return `<th class="text-end">${escapeText(phase.label)}</th>`;
        }).join('');
        const rows = VALUE_FIELDS.map(function (field) {
            const cells = branch.phases.map(function (phase) {
                return `<td class="text-end" data-line="${phase.line_id}" data-field="${field}">--</td>`;
            }).join('');
            return `<tr><td class="bold">${escapeText(INPUT_LABELS[field])}</td>${cells}</tr>`;
        }).join('');
        const links = branch.phases.map(function (phase) {
            const url = csvUrls[phase.line_id];
            return url ? `<td class="text-end"><a href="${escapeText(url)}" class="btn btn-primary2 btn-sm">CSV</a></td>` : '<td></td>';
        }).join('');
        return `<div class="borderGreen p-4 mb-3">
            <h3 class="textGreen little2">${escapeText(branch.name)}</h3>
            <div class="table-responsive">
              <table class="table table-borderless align-middle">
                <thead><tr><th></th>${head}</tr></thead>
                <tbody>${rows}<tr><td></td>${links}</tr></tbody>
              </table>
            </div>
          </div>`;
    }).join('');
}

function updateValues(activeInputs) {
    let totalPower = 0;
    let totalEnergy = 0;
    activeInputs.forEach(function (input) {
        VALUE_FIELDS.forEach(function (field) {
            let value = input[field];
            if (field === 'energy' && value !== null && value !== undefined) {
                value = Math.abs(parseFloat(value));
            }
            document.querySelectorAll(`[data-line="${input.line_id}"][data-field="${field}"]`).forEach(function (cell) {
                cell.textContent = formatNumber(value);
            });
        });
        totalPower += parseFloat(input.active_power) || 0;
        totalEnergy += Math.abs(parseFloat(input.energy) || 0);
    });
    document.getElementById('totalPower').textContent = formatNumber(totalPower);
    document.getElementById('totalEnergy').textContent = formatNumber(totalEnergy);
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

function updateCharts(input) {
    const timestamp = input.timestamp || Date.now();
    addDataPointToChart('voltage', input.line_id, timestamp, input.voltage);
    addDataPointToChart('current', input.line_id, timestamp, input.current);
    addDataPointToChart('activePower', input.line_id, timestamp, input.active_power);
    addDataPointToChart('powerFactor', input.line_id, timestamp, input.power_factor);
}

function addDataPointToChart(chartKey, lineId, timestamp, value) {
    const chart = CHARTS[chartKey];
    if (!chart || !lineId || lineId < 1 || lineId > INPUT_SERIES_COUNT) {
        return;
    }

    const series = chart.series.getIndex(lineId - 1);
    if (!series) {
        return;
    }

    const dataPoint = {
        date: timestamp,
        value: value === null || value === undefined ? 0 : parseFloat(value) || 0,
    };

    series.data.push(dataPoint);

    while (series.data.length > MAX_CHART_POINTS) {
        series.data.removeIndex(0);
    }
}
