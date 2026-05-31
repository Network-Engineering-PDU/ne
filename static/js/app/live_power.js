// Poll backend for live input readings and update the UI
const LIVE_POLL_INTERVAL_MS = 2000;

function updateLiveReadings() {
    $.ajax({
        url: `/${LANG_CODE}/pdu/live_inputs/`,
        type: 'GET',
        dataType: 'json',
        success: function(resp) {
            if (!resp || resp.result !== 'ok') {
                console.error('Live power endpoint returned invalid result', resp);
                return;
            }
            // Response shape from ok_json is {"data": [...], "result": "ok"}
            let list = [];
            if (Array.isArray(resp.data)) {
                list = resp.data;
            } else if (resp.data && Array.isArray(resp.data.data)) {
                list = resp.data.data;
            }
            if (!list.length) {
                console.debug('Live power endpoint returned empty list', resp);
            }
            list.forEach(function(item) {
                const id = item.id || item.line_id;
                if ($('#live_voltage_' + id).length) $('#live_voltage_' + id).text(item.voltage != null ? item.voltage.toFixed(2) : '--');
                if ($('#live_current_' + id).length) $('#live_current_' + id).text(item.current != null ? item.current.toFixed(2) : '--');
                if ($('#live_apparent_' + id).length) $('#live_apparent_' + id).text(item.apparent_power != null ? item.apparent_power.toFixed(2) : '--');
                if ($('#live_active_' + id).length) $('#live_active_' + id).text(item.active_power != null ? item.active_power.toFixed(2) : '--');
                if ($('#live_reactive_' + id).length) $('#live_reactive_' + id).text(item.reactive_power != null ? item.reactive_power.toFixed(2) : '--');
                if ($('#live_pf_' + id).length) $('#live_pf_' + id).text(item.power_factor != null ? item.power_factor.toFixed(2) : '--');
                if ($('#live_energy_' + id).length) $('#live_energy_' + id).text(item.energy != null ? item.energy.toFixed(2) : '--');
                if ($('#live_phasevi_' + id).length) $('#live_phasevi_' + id).text(item.phase_vi != null ? item.phase_vi.toFixed(2) : '--');
                if ($('#live_freq_' + id).length) $('#live_freq_' + id).text(item.frequency != null ? item.frequency.toFixed(2) : '--');
            });
        },
        error: function(xhr, status, error) {
            console.error('Live power endpoint request failed', status, error, xhr.responseText);
        }
    });
}

$(function() {
    // start polling
    updateLiveReadings();
    setInterval(updateLiveReadings, LIVE_POLL_INTERVAL_MS);
});
