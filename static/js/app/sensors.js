let modalSensorsNew = $("#modalSensorsNew");
let bleScanPollTimer = null;
let bleDiscoveredDevices = [];

const SENSORS_SCAN_API = "/api/sensors-scan";

let SENSORS = {

    name: 'Sensors',

    update_sensor_name: function (elem, sensor_id) {
        let originalText = elem.html();
        $.ajax({
            url: `/${LANG_CODE}/sensors/${sensor_id}/update_name`,
            type: 'POST',
            data: {
                'name': $('#inputSensorName_'+sensor_id).val(),
            },
            dataType: 'json',
            beforeSend: function (){
                elem.attr('disabled', true).html(SPINNER_SM_DARK);
            },
            success: function() {
                elem.attr('disabled', false).html(originalText);
            },
            error: function (response) {
                elem.attr('disabled', false).html(originalText);
                alert('Error: ' + JSON.stringify(response));
            }
        });
    },

    stop_ble_scan: function () {
        if (bleScanPollTimer) {
            clearInterval(bleScanPollTimer);
            bleScanPollTimer = null;
        }
        $.post(`${SENSORS_SCAN_API}/stop/`);
    },

    render_discovered_list: function () {
        if (!bleDiscoveredDevices.length) {
            modalSensorsNew.find('.modal-body').html(
                '<p class="text-center text-muted">No MST01 or BeaconX Pro devices found yet.</p>'
            );
            return;
        }

        let html = '<p class="bold text-center">Select sensors to add</p><div class="list-group">';
        bleDiscoveredDevices.forEach(function (dev, idx) {
            html += `
                <label class="list-group-item">
                    <input class="form-check-input me-2 ble-sensor-pick" type="checkbox" value="${dev.mac}" checked>
                    <strong>${dev.kind}</strong> — ${dev.mac}
                    <span class="text-muted"> (${dev.rssi} dBm)</span>
                </label>`;
        });
        html += '</div>';
        html += `
            <div class="d-flex gap-2 pt-3">
                <button type="button" class="btn btn-primary w-50" id="btnBleAddSelected">Add selected</button>
                <button type="button" class="btn btn-outline-primary w-50" id="btnBleAddAll">Add all</button>
            </div>`;
        modalSensorsNew.find('.modal-body').html(html);

        $('#btnBleAddSelected').on('click', function () {
            SENSORS.confirm_ble_sensors(false);
        });
        $('#btnBleAddAll').on('click', function () {
            SENSORS.confirm_ble_sensors(true);
        });
    },

    poll_discovered: function () {
        $.getJSON(`${SENSORS_SCAN_API}/discovered/`, function (data) {
            bleDiscoveredDevices = data.devices || [];
            SENSORS.render_discovered_list();
        });
    },

    confirm_ble_sensors: function (addAll) {
        let payload = addAll ? { all: true } : {
            macs: $('.ble-sensor-pick:checked').map(function () {
                return $(this).val();
            }).get()
        };
        if (!addAll && (!payload.macs || !payload.macs.length)) {
            alert('Select at least one sensor.');
            return;
        }
        $.ajax({
            url: `${SENSORS_SCAN_API}/confirm/`,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(payload),
            success: function () {
                SENSORS.stop_ble_scan();
                modalSensorsNew.modal('hide');
                window.location.href = SENSORS_URL;
            },
            error: function (response) {
                alert('Error: ' + JSON.stringify(response));
            }
        });
    },

    add_new_sensor: function () {
        bleDiscoveredDevices = [];
        modalSensorsNew.find('.modal-body').html(
            '<div class="d-flex justify-content-center">' + SPINNER + '</div>' +
            '<div class="row pt-3"><div class="col text-center">' +
            '<p class="bold">Scanning Minew MST01 / BeaconX Pro…</p>' +
            '<p class="text-muted fst-italic">Power on the sensor and keep it nearby</p>' +
            '</div></div>'
        );

        modalSensorsNew.modal({
            backdrop: "static",
            width: "420px"
        }).modal("show");

        $.post(`${SENSORS_SCAN_API}/start/`)
            .done(function () {
                SENSORS.poll_discovered();
                bleScanPollTimer = setInterval(SENSORS.poll_discovered, 5000);
                setTimeout(function () {
                    SENSORS.poll_discovered();
                }, 60000);
            })
            .fail(function (xhr) {
                alert('Could not start BLE scan. Check BlueZ/Bluetooth service on the PDU. ' + xhr.responseText);
            });
    }
};


$(function () {
    modalSensorsNew.on("hidden.bs.modal", function () {
        SENSORS.stop_ble_scan();
    });
});
