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
    check_new_sensor: function () {
        $.ajax({
            url: `/${LANG_CODE}/check_new_sensor`,
            type: 'GET',
            data: {},
            dataType: 'json',
            success: function(response) {
                if (response.result === 'ok'){
                    setTimeout(function (){
                        modalSensorsNew.modal('hide');
                    }, 1000);

                    setTimeout(function (){
                        window.location.href = SENSORS_URL;
                    }, 1700);
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

    add_new_sensor: function (){
        // body
        modalSensorsNew.find('.modal-body').html(
            '<div class="d-flex justify-content-center">' + SPINNER + '</div>' +
                  '<div class="row pt-3">' +
                        '<div class="col text-center">' +
                            `<p class="bold">Scanning a new TycheTools sensor...</p>` +
                            '<p class="text-muted fst-italic">Please, power on the device to add it to de network</p>' +
                        '</div>' +
                 '</div>'
        )

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
                    // Hacer polling a backend verificando si hay algun sensor nuevo
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

