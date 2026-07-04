// SETTINGS VARS
// System Info
let spanSettingsSystemInfoProductName = $("#spanSettingsSystemInfoProductName");
let spanSettingsSystemInfoProductPn = $("#spanSettingsSystemInfoProductPn");
let spanSettingsSystemInfoProductSn = $("#spanSettingsSystemInfoProductSn");
let spanSettingsSystemInfoLanMac = $("#spanSettingsSystemInfoLanMac");
let spanSettingsSystemInfoSwVersion = $("#spanSettingsSystemInfoSwVersion");
// Snmp nms
let inputSettingsSnmpNmsSystemName = $("#inputSettingsSnmpNmsSystemName");
let inputSettingsSnmpNmsSystemContact = $("#inputSettingsSnmpNmsSystemContact");
let inputSettingsSnmpNmsSystemLocation = $("#inputSettingsSnmpNmsSystemLocation");
// PDU Info
let spanSettingsPduInfoOutletCount = $("#spanSettingsPduInfoOutletCount");
let spanSettingsPduInfoRatedCurrent = $("#spanSettingsPduInfoRatedCurrent");
let spanSettingsPduInfoController = $("#spanSettingsPduInfoController");
let spanSettingsPduInfoType = $("#spanSettingsPduInfoType");
// OTA
let spanSettingsOtaInstalledVersion = $("#spanSettingsOtaInstalledVersion");
let spanSettingsOtaAvailableVersion = $("#spanSettingsOtaAvailableVersion");
let spanSettingsOtaLastCheck = $("#spanSettingsOtaLastCheck");
let spanSettingsOtaStatus = $("#spanSettingsOtaStatus");
// System Reboot
let modalSettingsRestartOrRestoreFactory = $("#modalSettingsRestartOrRestoreFactory");


let SETTINGS = {

    name: 'Settings',
    url: `/${LANG_CODE}/settings/`,

    // System Info
    get_system_info: function () {
        /*
        response example:
            {
                "product_name": "NET-POWER",
                "product_pn": "PDU2000-16-1PH-8-0-S1",
                "product_sn": "50FF99DFFF00",
                "lan_mac": "50-FF-99-DF-FF-00",
                "sw_version": "AXX-1.3.0"
            }
        */
        $.ajax({
            url: SETTINGS.url,
            type: 'POST',
            data: {
                'endpoint': 'settings/system-info',
                'method': 'GET'
            },
            dataType: 'json',
            beforeSend: function (xhr) {
                spanSettingsSystemInfoProductName.html(SPINNER);
                spanSettingsSystemInfoProductPn.html(SPINNER);
                spanSettingsSystemInfoProductSn.html(SPINNER);
                spanSettingsSystemInfoLanMac.html(SPINNER);
                spanSettingsSystemInfoSwVersion.html(SPINNER);
            },
            success: function(response) {
                if (response.result === 'ok'){
                    setTimeout(function() {
                        spanSettingsSystemInfoProductName.html(response.product_name);
                        spanSettingsSystemInfoProductPn.html(response.product_pn);
                        spanSettingsSystemInfoProductSn.html(response.product_sn);
                        spanSettingsSystemInfoLanMac.html(response.lan_mac);
                        spanSettingsSystemInfoSwVersion.html(response.sw_version);
                    }, 1200);
                }else{
                    alert('Warning: ' + response.message);
                }
            },
            error: function (response) {
                alert('Error: ' + response.message);
            }
        });
    },

    // System Info - SNMP NMS
    get_snmp_nms: function (elem) {
        let originalText = '';
        if (elem !== undefined){
            originalText = elem.html();
        }
        /*
        response example:
            {
                "system_name": "NET-POWER",
                "system_contact": "info@telefonica.es",
                "system_location": "Madrid Data Center Room 1",
            }
        */
        $.ajax({
            url: SETTINGS.url,
            type: 'POST',
            data: {
                'endpoint': 'settings/snmp-nms',
                'method': 'GET'
            },
            dataType: 'json',
            beforeSend: function (xhr) {
                if (elem !== undefined){
                    elem.attr('disabled', true).html(SPINNER_SM_DARK);
                }
                inputSettingsSnmpNmsSystemName.val('');
                inputSettingsSnmpNmsSystemContact.val('');
                inputSettingsSnmpNmsSystemLocation.val('');
            },
            success: function(response) {
                if (response.result === 'ok'){
                    setTimeout(function() {
                        if (elem !== undefined){
                            elem.attr('disabled', false).html(originalText);
                        }
                        inputSettingsSnmpNmsSystemName.val(response.system_name);
                        inputSettingsSnmpNmsSystemContact.val(response.system_contact);
                        inputSettingsSnmpNmsSystemLocation.val(response.system_location);
                    }, 1000);
                }else{
                    alert('Warning: ' + response.message);
                }
            },
            error: function (response) {
                alert('Error: ' + response.message);
            }
        });
    },

    update_snmp_nms: function (elem) {
        let originalText = elem.html();
        /*
        body example:
            {
                "system_name": "NET-POWER",
                "system_contact": "info@telefonica.es",
                "system_location": "Madrid Data Center Room 1",
            }
        */
        let payload = {
            "system_name": inputSettingsSnmpNmsSystemName.val(),
            "system_contact": inputSettingsSnmpNmsSystemContact.val(),
            "system_location": inputSettingsSnmpNmsSystemLocation.val()
        }
        $.ajax({
            url: SETTINGS.url,
            type: 'POST',
            data: {
                'endpoint': 'settings/snmp-nms',
                'method': 'PUT',
                'payload': JSON.stringify(payload)
            },
            dataType: 'json',
            beforeSend: function (){
                elem.attr('disabled', true).html(SPINNER_SM_DARK);
            },
            success: function(response) {
                if (response.result === 'ok'){
                    console.log(response.message);
                    setTimeout(function() {
                        elem.attr('disabled', false).html(originalText);
                    }, 1500);
                }else{
                    alert('Warning: ' + response.message);
                }
            },
            error: function (response) {
                elem.attr('disabled', false).html(originalText);
                alert('Error: ' + response.message);
            }
        });
    },

    // Upload SoftwareUpdate or HttpCert
    upload_file: function (elem, endpoint){
        let originalText = elem.html();
        let formData = new FormData();
        let file = $('#inputFile_' + endpoint)[0].files[0]
        formData.append('file', file);
        formData.append('method','POST');
        formData.append('endpoint',`settings/${endpoint}`);

        let err_msg = '';
        if (
            (endpoint === 'swupdate' && !isValidExtension(file.name, ['bin'])) ||
            (endpoint === 'ca-key' && !isValidExtension(file.name, ['key'])) ||
            (endpoint === 'ca-cert' && !isValidExtension(file.name, ['crt']))
        ){
            if (LANG_CODE === 'en'){
                err_msg = 'Incorrect File Extension'
            }else{
                err_msg = 'Extensión de Fichero Incorrecta'
            }
            alert(err_msg);
        }
        else{
            $.ajax({
                url: SETTINGS.url,
                type: 'POST',
                data: formData,
                dataType: 'json',
                contentType: false,  // tell jQuery not to set contentType
                processData: false,  // tell jQuery not to process the data
                beforeSend: function (xhr) {
                    if (elem !== undefined){
                        elem.attr('disabled', true).html(SPINNER_SM_DARK);
                    }
                },
                success: function(response) {
                    if (response.result === 'ok'){
                        console.log(response.message);
                        setTimeout(function() {
                            elem.attr('disabled', false).html(originalText);
                        }, 1000);
                    }else{
                        if (elem !== undefined){
                            elem.attr('disabled', false).html(originalText);
                        }
                        alert(response.message);
                    }
                },
                error: function (response) {
                    if (elem !== undefined){
                        elem.attr('disabled', false).html(originalText);
                    }
                    alert(response.message);
                }
            });
        }
    },

    // PDU Info
    get_pdu_info: function () {
        /*
        response example:
            {
                "outlet_count": 8,
                "rated_current": 32.5,
                "controller": "ARM9 PN-4",
                "type": "PDU&AC"
            }
        */
        $.ajax({
            url: SETTINGS.url,
            type: 'POST',
            data: {
                'endpoint': 'settings/pdu-info',
                'method': 'GET'
            },
            dataType: 'json',
            beforeSend: function (xhr) {
                spanSettingsPduInfoOutletCount.html(SPINNER);
                spanSettingsPduInfoRatedCurrent.html(SPINNER);
                spanSettingsPduInfoController.html(SPINNER);
                spanSettingsPduInfoType.html(SPINNER);
            },
            success: function(response) {
                if (response.result === 'ok'){
                    setTimeout(function() {
                        let newRatedCurrent = String(response.rated_current);
                        if (SETTINGS.current_pdu_rated_current !== newRatedCurrent) {
                            SETTINGS.current_pdu_rated_current = newRatedCurrent;
                            spanSettingsPduInfoOutletCount.html(response.outlet_count);
                            spanSettingsPduInfoRatedCurrent.html(response.rated_current + ' A');
                            spanSettingsPduInfoController.html(response.controller);
                            spanSettingsPduInfoType.html(response.type);
                        }
                    }, 2000);
                }else{
                    alert('Warning: ' + response.message);
                }
            },
            error: function (response) {
                alert('Error: ' + response.message);
            }
        });
    },

    current_pdu_rated_current: null,
    ota_status_poll_timer: null,
    ota_status_polling: false,

    render_ota_status: function (response) {
        spanSettingsOtaInstalledVersion.html(response.installed_version || '-');
        spanSettingsOtaAvailableVersion.html(response.available_version || '-');
        spanSettingsOtaLastCheck.html(response.last_check_time || '-');
        let status = response.ota_status || response.status || 'idle';
        if (status === 'downloading' && response.download_progress !== undefined) {
            status += ' (' + response.download_progress + '%)';
        }
        if (response.update_phase && response.update_phase !== 'idle' && response.update_phase !== status) {
            status += ' / ' + response.update_phase;
        }
        if (response.last_error) {
            status += ' (' + response.last_error + ')';
        }
        spanSettingsOtaStatus.html(status);
    },

    get_ota_status: function (refresh, showSpinner) {
        if (showSpinner === undefined) {
            showSpinner = true;
        }
        if (SETTINGS.ota_status_polling && !showSpinner) {
            return;
        }
        SETTINGS.ota_status_polling = true;
        $.ajax({
            url: SETTINGS.url,
            type: 'POST',
            data: {
                'endpoint': 'settings/update-status',
                'method': 'GET',
                'refresh': refresh ? '1' : '0',
            },
            dataType: 'json',
            timeout: 30000,
            complete: function () {
                SETTINGS.ota_status_polling = false;
            },
            beforeSend: function () {
                if (showSpinner) {
                    spanSettingsOtaInstalledVersion.html(SPINNER);
                    spanSettingsOtaAvailableVersion.html(SPINNER);
                    spanSettingsOtaLastCheck.html(SPINNER);
                    spanSettingsOtaStatus.html(SPINNER);
                }
            },
            success: function(response) {
                if (response.result === 'ok') {
                    SETTINGS.render_ota_status(response);
                } else {
                    SETTINGS.render_ota_status({});
                    if (response.message) {
                        console.warn('OTA status:', response.message);
                    }
                }
            },
            error: function () {
                spanSettingsOtaInstalledVersion.html('-');
                spanSettingsOtaAvailableVersion.html('-');
                spanSettingsOtaLastCheck.html('-');
                spanSettingsOtaStatus.html('error');
            }
        });
    },

    start_ota_status_polling: function () {
        if (SETTINGS.ota_status_poll_timer !== null) {
            clearInterval(SETTINGS.ota_status_poll_timer);
        }
        SETTINGS.ota_status_poll_timer = setInterval(function () {
            SETTINGS.get_ota_status(false, false);
        }, 2000);
    },

    check_ota_now: function (elem) {
        let originalText = elem.html();
        $.ajax({
            url: SETTINGS.url,
            type: 'POST',
            data: {
                'endpoint': 'settings/ota-check-now',
            },
            dataType: 'json',
            timeout: 30000,
            beforeSend: function () {
                elem.attr('disabled', true).html(SPINNER_SM_DARK);
                spanSettingsOtaInstalledVersion.html(SPINNER);
                spanSettingsOtaAvailableVersion.html(SPINNER);
                spanSettingsOtaLastCheck.html(SPINNER);
                spanSettingsOtaStatus.html(SPINNER);
            },
            success: function(response) {
                elem.attr('disabled', false).html(originalText);
                if (response.result === 'ok') {
                    SETTINGS.render_ota_status(response);
                    SETTINGS.get_ota_status(false, false);
                } else {
                    alert(response.message || 'OTA check failed');
                }
            },
            error: function (xhr, textStatus, errorThrown) {
                elem.attr('disabled', false).html(originalText);
                let message = 'OTA check failed';
                try {
                    let json = JSON.parse(xhr.responseText || '{}');
                    if (json.message) {
                        message = json.message;
                    }
                } catch (e) {
                    if (errorThrown) {
                        message = errorThrown;
                    }
                }
                alert(message);
                SETTINGS.get_ota_status(false);
            }
        });
    },

    // Tools System Reboot or Factory Reset
    system_reboot_or_factory_reset: function (elem) {
        let originalText = elem.html();
        let endpoint = elem.attr('endpoint');
        let alertMessage = 'Restarting PDU...';
        if (endpoint === 'factory-reset'){
            alertMessage = 'Factory reset...';
        }
        $.ajax({
            url: SETTINGS.url,
            type: 'POST',
            data: {
                'endpoint': `settings/${endpoint}`,
            },
            dataType: 'json',
            beforeSend: function (){
                elem.attr('disabled', true).html(SPINNER_SM_DARK);
            },
            success: function(response) {
                if (response.result === 'ok'){
                    console.log(response.message);
                    setTimeout(function() {
                        modalSettingsRestartOrRestoreFactory.modal('hide');
                    }, 1500);
                    setTimeout(function() {
                        alert(`${alertMessage} Device will restart in a few seconds`);
                    }, 1700);
                }else{
                    alert('Warning: ' + response.message);
                }
            },
            error: function (response) {
                elem.attr('disabled', false).html(originalText);
                alert('Error: ' + response.message);
            }
        });
    },

    // Utils (open modal with dynamic actions)
    show_modal_for_system_reboot_or_factory_reset: function (elem, endpoint){
        let warning_text = elem.html();
        // body
        modalSettingsRestartOrRestoreFactory.find('.modal-body').html(
            '<div class="d-flex justify-content-center">' +
            '<div class="iconWarn"></div>' +
            '</div>' +
            '<div class="row pt-3">' +
            '<div class="col text-center">' +
            `<p class="bold">ARE YOU SURE YOU WANT TO ${warning_text} ?</p>` +
            '<p class="text-muted fst-italic">Warning: This action can not be undone</p>' +
            '</div>' +
            '</div>'
        )
        // footer
        modalSettingsRestartOrRestoreFactory.find('.modal-footer').html(
            '<a onclick="SETTINGS.system_reboot_or_factory_reset($(this));" class="btn btnRed" endpoint="'+endpoint+'">' +
            '<span class="iconRestart"></span> ' + warning_text +
            '</a>'
        )
        // show
        modalSettingsRestartOrRestoreFactory.modal('show');
    }
};


$(function() {

    // SETTINGS
    // System Info
    SETTINGS.get_system_info();
    // Snmp nms
    SETTINGS.get_snmp_nms();
    // PDU Info
    SETTINGS.get_pdu_info();
    // OTA
    SETTINGS.get_ota_status(false);
    SETTINGS.start_ota_status_polling();

});
