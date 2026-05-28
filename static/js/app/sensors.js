let modalSensorsNew = $("#modalSensorsNew");

let SENSORS = {

    name: 'Sensors',

    // Update Sensor Name
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

    // Modal for New Sensor (execute start-scan in gw and then make polling to db to see if there is a new sensor)
    render_new_sensor_list: function(sensors) {
        if (!sensors || sensors.length === 0) {
            modalSensorsNew.find('.modal-body').html(
                '<div class="text-center">' +
                    '<p class="bold">No BLE devices found yet.</p>' +
                    '<p class="text-muted fst-italic">Keep the devices powered on and within range.</p>' +
                '</div>'
            );
            return;
        }

        let html = '<div class="table-responsive"><table class="table table-striped">';
        html += '<thead><tr><th>MAC</th><th>Nombre</th><th></th></tr></thead><tbody>';
        sensors.forEach(function(sensor) {
            html += '<tr>' +
                `<td class="text-center">${sensor.mac_address}</td>` +
                `<td class="text-center">${sensor.name || '-'}</td>` +
                '<td class="text-center">' +
                    `<button class="btn btn-sm btn-success" onclick="SENSORS.accept_new_sensor(${sensor.id})">` +
                        'Agregar' +
                    '</button>' +
                '</td>' +
            '</tr>';
        });
        html += '</tbody></table></div>';
        html += '<div class="text-center"><small class="text-muted">Seleccione un dispositivo para agregar como sensor.</small></div>';
        modalSensorsNew.find('.modal-body').html(html);
    },

    render_scan_spinner: function() {
        modalSensorsNew.find('.modal-body').html(
            '<div class="d-flex justify-content-center">' + SPINNER + '</div>' +
                  '<div class="row pt-3">' +
                        '<div class="col text-center">' +
                            `<p class="bold">Scanning for BLE devices...</p>` +
                            '<p class="text-muted fst-italic">Please power on the devices and keep them close.</p>' +
                        '</div>' +
                 '</div>'
        );
    },

    check_new_sensor: function () {
        $.ajax({
            url: `/${LANG_CODE}/check_new_sensor`,
            type: 'GET',
            data: {},
            dataType: 'json',
            success: function(response) {
                if (response.result === 'ok' && response.data && response.data.sensors && response.data.sensors.length > 0){
                    SENSORS.render_new_sensor_list(response.data.sensors);
                }
                else{
                    setTimeout(function (){
                        SENSORS.check_new_sensor();
                    },5000);
                }
            },
            error: function (response) {
                alert('Error: ' + JSON.stringify(response));
            }
        });
    },

    accept_new_sensor: function(sensor_id) {
        $.ajax({
            url: `/${LANG_CODE}/sensors/${sensor_id}/accept_new`,
            type: 'POST',
            data: {},
            dataType: 'json',
            success: function(response) {
                if (response.result === 'ok'){
                    modalSensorsNew.modal('hide');
                    setTimeout(function (){
                        window.location.href = SENSORS_URL;
                    }, 500);
                } else {
                    alert('Warning: ' + response.message);
                }
            },
            error: function (response) {
                alert('Error: ' + JSON.stringify(response));
            }
        });
    },

    add_new_sensor: function (){
        SENSORS.render_scan_spinner();

        // Start Scanning (Gateway)
        $.ajax({
            url: `/${LANG_CODE}/settings/`,
            type: 'POST',
            data: {
                'endpoint': 'settings/start-scan',
            },
            dataType: 'json',
            success: function(response) {
                if (response.result === 'ok'){
                    console.log(response.message);
                    setTimeout(function (){
                        SENSORS.check_new_sensor();
                    }, 1500);
                }else{
                    alert('Warning: ' + response.message);
                }
            },
            error: function (response) {
                alert('Error: ' + response.message);
            }
        });

        // show
        modalSensorsNew.modal({
            "backdrop":"static",
            "width": "320px"
        }).modal("show");

    }

};


$(function() {

    // when close the modal, execute stop-scan in gateway
    modalSensorsNew.on("hidden.bs.modal", function () {
        $.ajax({
            url: `/${LANG_CODE}/settings/`,
            type: 'POST',
            data: {
                'endpoint': 'settings/stop-scan'
            },
            dataType: 'json',
            success: function(response) {
                if (response.result === 'ok'){
                    console.log(response.message);
                }else{
                    alert('Warning: ' + response.message);
                }
            },
            error: function (response) {
                alert('Error: ' + response.message);
            }
        });
    });

});

