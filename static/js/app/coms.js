// COMS VARS
// Services
let checkboxComsHTTPEnable = $("#checkboxComsHTTPEnable");
let checkboxComsTELNETEnable = $("#checkboxComsTELNETEnable");
let checkboxComsSSHEnable = $("#checkboxComsSSHEnable");
let checkboxComsSNMPEnable = $("#checkboxComsSNMPEnable");
let checkboxComsModbusEnable = $("#checkboxComsModbusEnable");
// Network Setup
let checkboxComsDHCPEnable = $("#checkboxComsDHCPEnable");
let selectComsNetworkMode = $("#selectComsNetworkMode");
let spanComsConnectionTypeEthernet = $("#spanComsConnectionTypeEthernet");
let spanComsConnectionTypeWifi = $("#spanComsConnectionTypeWifi");
let containerComsEthernetConfig = $("#containerComsEthernetConfig");
let containerComsDualLanConfig = $("#containerComsDualLanConfig");
let containerComsWifiConfig = $("#containerComsWifiConfig");
let containerComsWifiStaticConfig = $("#containerComsWifiStaticConfig");
let inputComsEthernetIP = $("#inputComsEthernetIP");
let inputComsEthernetSubnetMask = $("#inputComsEthernetSubnetMask");
let inputComsEthernetGateway = $("#inputComsEthernetGateway");
let inputComsEthernetDNS = $("#inputComsEthernetDNS");
let inputComsLan1IP = $("#inputComsLan1IP");
let inputComsLan1Gateway = $("#inputComsLan1Gateway");
let inputComsLan2IP = $("#inputComsLan2IP");
let inputComsLan2Gateway = $("#inputComsLan2Gateway");
let inputComsDualLanSubnetMask = $("#inputComsDualLanSubnetMask");
let inputComsDualLanDNS = $("#inputComsDualLanDNS");
let inputComsWifiSSID = $("#inputComsWifiSSID");
let inputComsWifiPassword = $("#inputComsWifiPassword");
let inputComsWifiIP = $("#inputComsWifiIP");
let inputComsWifiSubnetMask = $("#inputComsWifiSubnetMask");
let inputComsWifiGateway = $("#inputComsWifiGateway");
let inputComsWifiDNS = $("#inputComsWifiDNS");
let networkSetupState = {
    eth_interface: '',
    loaded_ssid: ''
};
// SNMP Setup
let checkboxComsSnmpSetupBeepEnable = $("#checkboxComsSnmpSetupBeepEnable");
let checkboxComsSnmpSetupRelayEnable = $("#checkboxComsSnmpSetupRelayEnable");
let checkboxComsSnmpSetupAlarmToSmpTrapEnable = $("#checkboxComsSnmpSetupAlarmToSmpTrapEnable");
let checkboxComsSnmpSetupAlarmToEmailEnable = $("#checkboxComsSnmpSetupAlarmToEmailEnable");
let inputComsSnmpSetupWebAutoRefreshTime = $("#inputComsSnmpSetupWebAutoRefreshTime");
let inputComsSnmpSetupWebLifetime = $("#inputComsSnmpSetupWebLifetime");
let inputComsSnmpSetupSystemTime = $("#inputComsSnmpSetupSystemTime");
let inputComsSnmpSetupModbusAddress = $("#inputComsSnmpSetupModbusAddress");
// SNMP Details Settings
let modalSnmpDetailSettings = $("#modalSnmpDetailSettings");
let inputComsSnmpDetailsSettingsPort = $("#inputComsSnmpDetailsSettingsPort");
let checkboxComsSnmpDetailsSettingsAlarmToTrap = $("#checkboxComsSnmpDetailsSettingsAlarmToTrap");
// SNMP v1/v2c
let radioComsDetailsSettingsSNMPV1V2ReadCommunityPublic = $("#radioComsDetailsSettingsSNMPV1V2ReadCommunityPublic");
let radioComsDetailsSettingsSNMPV1V2ReadCommunityPrivate = $("#radioComsDetailsSettingsSNMPV1V2ReadCommunityPrivate");
let radioComsDetailsSettingsSNMPV1V2WriteCommunityPublic = $("#radioComsDetailsSettingsSNMPV1V2WriteCommunityPublic");
let radioComsDetailsSettingsSNMPV1V2WriteCommunityPrivate = $("#radioComsDetailsSettingsSNMPV1V2WriteCommunityPrivate");
// Trap Settings
let inputComsSnmpDetailsSettingsManager1Name = $("#inputComsSnmpDetailsSettingsManager1Name");
let inputComsSnmpDetailsSettingsManager1Ip = $("#inputComsSnmpDetailsSettingsManager1Ip");
let inputComsSnmpDetailsSettingsManager2Name = $("#inputComsSnmpDetailsSettingsManager2Name");
let inputComsSnmpDetailsSettingsManager2Ip = $("#inputComsSnmpDetailsSettingsManager2Ip");
let inputComsSnmpDetailsSettingsManager3Name = $("#inputComsSnmpDetailsSettingsManager3Name");
let inputComsSnmpDetailsSettingsManager3Ip = $("#inputComsSnmpDetailsSettingsManager3Ip");
let inputComsSnmpDetailsSettingsManager4Name = $("#inputComsSnmpDetailsSettingsManager4Name");
let inputComsSnmpDetailsSettingsManager4Ip = $("#inputComsSnmpDetailsSettingsManager4Ip");
let radioComsDetailsSettingsSNMPV3UsmUserReadWrite = $("#radioComsDetailsSettingsSNMPV3UsmUserReadWrite");
let radioComsDetailsSettingsSNMPV3UsmUserRead = $("#radioComsDetailsSettingsSNMPV3UsmUserRead");
// SNMP v3
let inputComsSNMPDetailsSecurityLevel = $("#inputComsSNMPDetailsSecurityLevel");
let inputComsSNMPDetailsAccessRight = $("#inputComsSNMPDetailsAccessRight");
let inputComsSNMPDetailsAutoAlgorithm = $("#inputComsSNMPDetailsAutoAlgorithm");
let inputComsSNMPDetailsAuthPassword = $("#inputComsSNMPDetailsAuthPassword");
let inputComsSNMPDetailsPrivacyAlgorithm = $("#inputComsSNMPDetailsPrivacyAlgorithm");
let inputComsSNMPDetailsPrivacyPassword = $("#inputComsSNMPDetailsPrivacyPassword");

// Hosts
let modalComsHost = $("#modalComsHost");
let btnComsHost = $("#btnComsHost");


let COMS = {

    name: 'Coms',
    url: `/${LANG_CODE}/coms/`,
    url_hosts: `/${LANG_CODE}/hosts/`,

    translated_network_message: function (key, field) {
        let message = COMS_I18N[key] || "";
        return field ? message.replace("{field}", field) : message;
    },

    wait_for_web_ui: function (elem, originalText, attempt, targetIP) {
        attempt = attempt || 0;
        if (targetIP && targetIP !== window.location.hostname) {
            let port = window.location.port ? `:${window.location.port}` : '';
            let targetUrl = `${window.location.protocol}//${targetIP}${port}/${LANG_CODE}/coms/`;
            setTimeout(function () {
                window.location.assign(targetUrl);
            }, 4000);
            return;
        }
        $.ajax({
            url: `${COMS.url}?_=${Date.now()}`,
            type: 'GET',
            cache: false,
            timeout: 3000,
            success: function () {
                window.location.reload();
            },
            error: function () {
                if (attempt < 40) {
                    setTimeout(function () {
                        COMS.wait_for_web_ui(elem, originalText, attempt + 1, targetIP);
                    }, 1500);
                    return;
                }

                if (elem !== undefined) {
                    elem.attr('disabled', false).html(originalText);
                }
                alert(COMS.translated_network_message('networkUnreachable'));
            }
        });
    },

    // Mpdbus Add
    get_modbus_addr: function () {
        /*
        response example:
            {
                "addr": 1
            }
        */
        // Modbus
        $.ajax({
            url: COMS.url,
            type: 'POST',
            data: {
                'endpoint': 'settings/modbus',
                'method': 'GET'
            },
            dataType: 'json',
            success: function(response) {
                if (response.result === 'ok'){
                    if (response.addr !== undefined && response.addr !== ''){
                        inputComsSnmpSetupModbusAddress.val(response.addr);
                    }else{
                        inputComsSnmpSetupModbusAddress.val('');
                    }
                }else{
                    alert('Warning: ' + response.message);
                }
            },
            error: function (response) {
                alert('Error: ' + response.message);
            }
        });
    },

    // Services
    get_services: function () {
        /*
        response example:
            {
                "ssh": True,
                "snmp": False,
                "modbus": True,
            }
        */
        $.ajax({
            url: COMS.url,
            type: 'POST',
            data: {
                'endpoint': 'network/services',
                'method': 'GET'
            },
            dataType: 'json',
            success: function(response) {
                if (response.result === 'ok'){
                    checkboxComsSSHEnable.prop('checked', response.ssh);
                    checkboxComsSNMPEnable.prop('checked', response.snmp);
                    checkboxComsModbusEnable.prop('checked', response.modbus);
                }else{
                    alert('Warning: ' + response.message);
                }
            },
            error: function (response) {
                alert('Error: ' + response.message);
            }
        });
    },

    update_service: function (elem, service) {
        let endpoint = '';
        let modbus_addr = '';
        let modbus_addr_int = 0;
        // SSH
        if (service === 'ssh'){
            if (checkboxComsSSHEnable.is(':checked')){
                endpoint = 'start-ssh';
            }else{
                endpoint = 'stop-ssh';
            }
        // SNMP
        }else if (service === 'snmp'){
            if (checkboxComsSNMPEnable.is(':checked')){
                endpoint = 'start-snmp';
            }else{
                endpoint = 'stop-snmp';
            }
        // MODBUS
        }else if (service === 'modbus') {
            if (checkboxComsModbusEnable.is(':checked')){
                endpoint = 'start-modbus';
            }else{
                endpoint = 'stop-modbus';
            }
        // ADDR Modbus
        }else {
            endpoint = 'modbus';
            modbus_addr = inputComsSnmpSetupModbusAddress.val();
            modbus_addr_int = parseInt(modbus_addr);

            if (!modbus_addr || modbus_addr === '' || !Number.isInteger(modbus_addr_int) || modbus_addr_int < 0 || modbus_addr_int > 255){
                alert("Modbus address must be an integer between 0 and 255.");
                inputComsSnmpSetupModbusAddress.val('');
                return false;
            }
        }

        $.ajax({
            url: COMS.url,
            type: 'POST',
            data: {
                'endpoint': `settings/${endpoint}`,
                'method': 'POST',
                'modbus_addr': modbus_addr_int
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
    },

    // Network Setup
    update_network_setup_form: function () {
        let mode = parseInt(selectComsNetworkMode.val(), 10);
        let dhcp = checkboxComsDHCPEnable.is(':checked');
        let hasEthernet = mode === 0 || mode === 2 || mode === 3;
        let hasWifi = mode === 1 || mode === 3;

        containerComsEthernetConfig.toggleClass(
            'd-none', !hasEthernet || mode === 2 || dhcp);
        containerComsDualLanConfig.toggleClass('d-none', mode !== 2 || dhcp);
        containerComsWifiConfig.toggleClass('d-none', !hasWifi);
        containerComsWifiStaticConfig.toggleClass('d-none', dhcp);
    },

    network_value: function (field) {
        return $.trim(field.val() || '');
    },

    is_valid_ipv4: function (value) {
        let parts = value.split('.');
        if (parts.length !== 4) {
            return false;
        }
        return parts.every(function (part) {
            return /^\d{1,3}$/.test(part) &&
                parseInt(part, 10) >= 0 && parseInt(part, 10) <= 255;
        });
    },

    validate_network_field: function (field, label, required) {
        let value = COMS.network_value(field);
        field.removeClass('borderRed');
        if ((required && !value) || (value && !COMS.is_valid_ipv4(value))) {
            field.addClass('borderRed');
            alert(COMS.translated_network_message("invalidIpv4", label));
            return false;
        }
        return true;
    },

    validate_dns_field: function (field, label) {
        let value = COMS.network_value(field);
        field.removeClass('borderRed');
        if (!value) {
            return true;
        }
        let valid = value.split(',').every(function (server) {
            return COMS.is_valid_ipv4($.trim(server));
        });
        if (!valid) {
            field.addClass('borderRed');
            alert(COMS.translated_network_message("invalidDns", label));
        }
        return valid;
    },

    validate_network_setup: function () {
        let mode = parseInt(selectComsNetworkMode.val(), 10);
        let dhcp = checkboxComsDHCPEnable.is(':checked');
        let usesWifi = mode === 1 || mode === 3;

        if (usesWifi && !COMS.network_value(inputComsWifiSSID)) {
            inputComsWifiSSID.addClass('borderRed');
            alert(COMS.translated_network_message('wifiSsidRequired'));
            return false;
        }
        inputComsWifiSSID.removeClass('borderRed');

        if (usesWifi &&
            COMS.network_value(inputComsWifiSSID) !== networkSetupState.loaded_ssid &&
            !COMS.network_value(inputComsWifiPassword)) {
            inputComsWifiPassword.addClass('borderRed');
            alert(COMS.translated_network_message('wifiPasswordRequired'));
            return false;
        }
        inputComsWifiPassword.removeClass('borderRed');

        if (dhcp) {
            return true;
        }

        if (mode === 0 || mode === 3) {
            if (!COMS.validate_network_field(inputComsEthernetIP, COMS_I18N.ethernetIp, true) ||
                !COMS.validate_network_field(inputComsEthernetSubnetMask, COMS_I18N.ethernetSubnetMask, true) ||
                !COMS.validate_network_field(inputComsEthernetGateway, COMS_I18N.ethernetGateway, false) ||
                !COMS.validate_dns_field(inputComsEthernetDNS, COMS_I18N.ethernetDns)) {
                return false;
            }
        }

        if (mode === 2) {
            if (!COMS.validate_network_field(inputComsLan1IP, COMS_I18N.lan1Ip, true) ||
                !COMS.validate_network_field(inputComsLan1Gateway, COMS_I18N.lan1Gateway, true) ||
                !COMS.validate_network_field(inputComsLan2IP, COMS_I18N.lan2Ip, true) ||
                !COMS.validate_network_field(inputComsLan2Gateway, COMS_I18N.lan2Gateway, true) ||
                !COMS.validate_network_field(inputComsDualLanSubnetMask, COMS_I18N.lanSubnetMask, true) ||
                !COMS.validate_dns_field(inputComsDualLanDNS, COMS_I18N.lanDns)) {
                return false;
            }
            if (COMS.network_value(inputComsLan1IP) === COMS.network_value(inputComsLan2IP)) {
                alert(COMS.translated_network_message('lanAddressesDifferent'));
                return false;
            }
        }

        if (usesWifi) {
            if (!COMS.validate_network_field(inputComsWifiIP, COMS_I18N.wifiIp, true) ||
                !COMS.validate_network_field(inputComsWifiSubnetMask, COMS_I18N.wifiSubnetMask, true) ||
                !COMS.validate_network_field(inputComsWifiGateway, COMS_I18N.wifiGateway, false) ||
                !COMS.validate_dns_field(inputComsWifiDNS, COMS_I18N.wifiDns)) {
                return false;
            }
            if (mode === 3 &&
                COMS.network_value(inputComsEthernetIP) === COMS.network_value(inputComsWifiIP)) {
                alert(COMS.translated_network_message('ethernetWifiAddressesDifferent'));
                return false;
            }
        }
        return true;
    },

    get_network_setup: function (elem) {
        let originalText = '';
        if (elem !== undefined){
            originalText = elem.html();
        }
        $.ajax({
            url: COMS.url,
            type: 'POST',
            data: {
                'endpoint': 'network/interfaces',
                'method': 'GET',
            },
            dataType: 'json',
            success: function(response) {
                if (response.result === 'ok'){
                    if (elem !== undefined){
                        elem.attr('disabled', false).html(originalText);
                    }
                    spanComsConnectionTypeEthernet.html(response.ethernet_mac);
                    spanComsConnectionTypeWifi.html(response.wifi_mac);
                    let params = response.params || {};
                    let mode = parseInt(response.nw_mode, 10);
                    if (![0, 1, 2, 3].includes(mode)) {
                        mode = response.type === 4 || response.type === 5 ? 1 : 0;
                    }

                    networkSetupState.eth_interface = response.eth_interface ||
                        params.eth_interface || '';
                    networkSetupState.loaded_ssid = params.ssid || '';
                    selectComsNetworkMode.val(String(mode));
                    checkboxComsDHCPEnable.prop('checked', Boolean(response.dhcp));

                    inputComsEthernetIP.val(response.lan1_ip || params.ip || '192.168.1.100');
                    inputComsEthernetSubnetMask.val(params.subnet_mask || '255.255.255.0');
                    inputComsEthernetGateway.val(response.lan1_gateway || params.gateway_ip || '192.168.1.1');
                    inputComsEthernetDNS.val(params.dns || '8.8.8.8');

                    inputComsLan1IP.val(response.lan1_ip || params.ip || '192.168.1.100');
                    inputComsLan1Gateway.val(response.lan1_gateway || params.gateway_ip || '192.168.1.1');
                    inputComsLan2IP.val(response.lan2_ip || '192.168.1.200');
                    inputComsLan2Gateway.val(response.lan2_gateway || '192.168.1.1');
                    inputComsDualLanSubnetMask.val(params.subnet_mask || '255.255.255.0');
                    inputComsDualLanDNS.val(params.dns || '8.8.8.8');

                    inputComsWifiSSID.val(params.ssid || '');
                    inputComsWifiPassword.val('');
                    inputComsWifiIP.val(response.wifi_ip || (mode === 1 ? params.ip : '') || '192.168.1.150');
                    inputComsWifiSubnetMask.val(response.wifi_subnet_mask ||
                        (mode === 1 ? params.subnet_mask : '') || '255.255.255.0');
                    inputComsWifiGateway.val(response.wifi_gateway ||
                        (mode === 1 ? params.gateway_ip : '') || '192.168.1.1');
                    inputComsWifiDNS.val(response.wifi_dns ||
                        (mode === 1 ? params.dns : '') || '8.8.8.8');
                    COMS.update_network_setup_form();
                }else{
                    alert('Warning: ' + response.message);
                }
            },
            error: function (response) {
                if (elem !== undefined){
                    elem.attr('disabled', false).html(originalText);
                }
                alert('Error: ' + response.message);
            }
        });
    },

    update_network_setup: function (elem) {
        let originalText = '';
        if (elem !== undefined){
            originalText = elem.html();
        }
        if (!COMS.validate_network_setup()) {
            return false;
        }

        let mode = parseInt(selectComsNetworkMode.val(), 10);
        let dhcp = checkboxComsDHCPEnable.is(':checked');
        let wifiOnly = mode === 1;
        let dualLan = mode === 2;
        let ethernetIP = dualLan ? COMS.network_value(inputComsLan1IP) :
            COMS.network_value(inputComsEthernetIP);
        let ethernetMask = dualLan ? COMS.network_value(inputComsDualLanSubnetMask) :
            COMS.network_value(inputComsEthernetSubnetMask);
        let ethernetGateway = dualLan ?
            (networkSetupState.eth_interface === 'eth0' ?
                COMS.network_value(inputComsLan2Gateway) :
                COMS.network_value(inputComsLan1Gateway)) :
            COMS.network_value(inputComsEthernetGateway);
        let ethernetDNS = dualLan ? COMS.network_value(inputComsDualLanDNS) :
            COMS.network_value(inputComsEthernetDNS);
        let wifiIP = COMS.network_value(inputComsWifiIP);
        let wifiMask = COMS.network_value(inputComsWifiSubnetMask);
        let wifiGateway = COMS.network_value(inputComsWifiGateway);
        let wifiDNS = COMS.network_value(inputComsWifiDNS);

        let payload = {
            "type": wifiOnly ? (dhcp ? 4 : 5) : (dhcp ? 2 : 3),
            "dhcp": dhcp,
            "nw_mode": mode,
            "eth_interface": networkSetupState.eth_interface,
            "lan1_ip": COMS.network_value(inputComsLan1IP) || ethernetIP,
            "lan1_gateway": COMS.network_value(inputComsLan1Gateway) || ethernetGateway,
            "lan2_ip": COMS.network_value(inputComsLan2IP),
            "lan2_gateway": COMS.network_value(inputComsLan2Gateway),
            "wifi_ip": wifiIP,
            "wifi_subnet_mask": wifiMask,
            "wifi_gateway": wifiGateway,
            "wifi_dns": wifiDNS,
            "params": {
                "ip": wifiOnly ? wifiIP : ethernetIP,
                "subnet_mask": wifiOnly ? wifiMask : ethernetMask,
                "gateway_ip": wifiOnly ? wifiGateway : ethernetGateway,
                "dns": wifiOnly ? wifiDNS : ethernetDNS,
                "ssid": COMS.network_value(inputComsWifiSSID),
                "password": COMS.network_value(inputComsWifiPassword),
                "eth_interface": networkSetupState.eth_interface
            }
        };
        let targetIP = '';
        if (!dhcp) {
            targetIP = wifiOnly ? wifiIP : ethernetIP;
        }
        $.ajax({
            url: COMS.url,
            type: 'POST',
            data: {
                'endpoint': 'network/interfaces',
                'method': 'PUT',
                'payload': JSON.stringify(payload)
            },
            dataType: 'json',
            beforeSend: function (){
                if (elem !== undefined){
                    elem.attr('disabled', true).html(SPINNER_SM_DARK);
                }
            },
            success: function(response) {
                if (response.result === 'ok'){
                    console.log(response.message);
                    networkSetupState.loaded_ssid = COMS.network_value(inputComsWifiSSID);
                    setTimeout(function() {
                        COMS.wait_for_web_ui(elem, originalText, 0, targetIP);
                    }, 1500);
                }else{
                    if (elem !== undefined){
                        elem.attr('disabled', false).html(originalText);
                    }
                    alert('Warning: ' + response.message);
                }
            },
            error: function (response) {
                COMS.wait_for_web_ui(elem, originalText, 0, targetIP);
            }
        });
    },

    // SNMP Setup
    get_snmp_setup: function (elem) {
        let originalText = '';
        if (elem !== undefined){
            originalText = elem.html();
        }
        /*
        response example:
            {
                "beep": True,
                "relay": False,
                "trap_alarm": True,
                "email_alarm": True,
                "refresh_period": 60,
                "life_time": 240,
                "datetime": "2022-12-25 12:24:25"
                "modbus_address": 125
            }
        */
        $.ajax({
            url: COMS.url,
            type: 'POST',
            data: {
                'endpoint': 'network/snmp/settings',
                'method': 'GET',
            },
            dataType: 'json',
            success: function(response) {
                if (response.result === 'ok'){
                    if (elem !== undefined){
                        elem.attr('disabled', false).html(originalText);
                    }
                    // checkboxComsSnmpSetupBeepEnable.attr('checked', response.beep);
                    checkboxComsSnmpSetupRelayEnable.attr('checked', response.relay);
                    checkboxComsSnmpSetupAlarmToSmpTrapEnable.attr('checked', response.trap_alarm);
                    checkboxComsSnmpSetupAlarmToEmailEnable.attr('checked', response.email_alarm);
                    inputComsSnmpSetupWebAutoRefreshTime.val(response.refresh_period);
                    inputComsSnmpSetupWebLifetime.val(response.life_time);
                    inputComsSnmpSetupSystemTime.val(response.datetime);
                    inputComsSnmpSetupModbusAddress.val(response.modbus_address);
                }else{
                    alert('Warning: ' + response.message);
                }
            },
            error: function (response) {
                if (elem !== undefined){
                    elem.attr('disabled', false).html(originalText);
                }
                alert('Error: ' + response.message);
            }
        });
    },

    update_snmp_setup: function (elem) {
        let originalText = elem.html();
        /*
        body example:
            {
                "beep": True,
                "relay": False,
                "trap_alarm": True,
                "email_alarm": True,
                "refresh_period": 60,
                "life_time": 240,
                "datetime": "2022-12-25 12:24:25"
                "modbus_address": 125
            }
        */
        let payload = {
            "beep": checkboxComsSnmpSetupBeepEnable.is(':checked'),
            "relay": checkboxComsSnmpSetupRelayEnable.is(':checked'),
            "trap_alarm": checkboxComsSnmpSetupAlarmToSmpTrapEnable.is(':checked'),
            "email_alarm": checkboxComsSnmpSetupAlarmToEmailEnable.is(':checked'),
            "refresh_period": inputComsSnmpSetupWebAutoRefreshTime.val(),
            "life_time": inputComsSnmpSetupWebLifetime.val(),
            "datetime": inputComsSnmpSetupSystemTime.val(),
            "modbus_address": inputComsSnmpSetupModbusAddress.val(),
        }
        $.ajax({
            url: COMS.url,
            type: 'POST',
            data: {
                'endpoint': 'network/snmp/settings',
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
                if (elem !== undefined){
                    elem.attr('disabled', false).html(originalText);
                }
                alert('Error: ' + response.message);
            }
        });
    },

    get_snmp_details_settings: function (){
        /*
        response example:
            {
                "port": 161,
                "trap": {
                    "read_community": "Public",
                    "write_community": "Private",
                },
                "snmp_v1_v2c": {
                    "usm_user": "rw",
                    "security_level": "auth/priv",
                    "access_right": "rw",
                    "auth_algorithm": "HMAC-SHA",
                    "auth_pwd": "123",
                    "privacy_algorithm": "HMAC-SHA",
                    "privacy_pwd": "123",
                },
            }
        */
        $.ajax({
            url: COMS.url,
            type: 'POST',
            data: {
                'endpoint': 'network/snmp/detailed-settings',
                'method': 'GET',
            },
            dataType: 'json',
            success: function(response) {
                if (response.result === 'ok'){
                    // populate fields
                    inputComsSnmpDetailsSettingsPort.val(response.port);
                    // trap obj
                    let trap = response.trap;
                    if (trap){
                        checkboxComsSnmpDetailsSettingsAlarmToTrap.attr('checked', trap.alarm);
                        inputComsSnmpDetailsSettingsManager1Name.val(trap.manager_1_name);
                        inputComsSnmpDetailsSettingsManager1Ip.val(trap.manager_1_ip);
                        inputComsSnmpDetailsSettingsManager2Name.val(trap.manager_2_name);
                        inputComsSnmpDetailsSettingsManager2Ip.val(trap.manager_2_ip);
                        inputComsSnmpDetailsSettingsManager3Name.val(trap.manager_3_name);
                        inputComsSnmpDetailsSettingsManager3Ip.val(trap.manager_3_ip);
                        inputComsSnmpDetailsSettingsManager4Name.val(trap.manager_4_name);
                        inputComsSnmpDetailsSettingsManager4Ip.val(trap.manager_4_ip);
                    }
                    // snmp_v1_v2c obj
                    let snmp_v1_v2c = response.snmp_v1_v2c;
                    if (snmp_v1_v2c){
                        radioComsDetailsSettingsSNMPV1V2ReadCommunityPublic.attr('checked', snmp_v1_v2c.read_community === 'Public');
                        radioComsDetailsSettingsSNMPV1V2ReadCommunityPrivate.attr('checked', snmp_v1_v2c.read_community === 'Private');
                        radioComsDetailsSettingsSNMPV1V2WriteCommunityPublic.attr('checked', snmp_v1_v2c.write_community === 'Public');
                        radioComsDetailsSettingsSNMPV1V2WriteCommunityPrivate.attr('checked', snmp_v1_v2c.write_community === 'Private');
                    }
                    // snmp_v3 obj
                    let snmp_v3 = response.snmp_v3;
                    if (snmp_v3){
                        radioComsDetailsSettingsSNMPV3UsmUserReadWrite.attr('checked', snmp_v3.usm_user === 'rw');
                        radioComsDetailsSettingsSNMPV3UsmUserRead.attr('checked', snmp_v3.usm_user === 'r');
                        inputComsSNMPDetailsSecurityLevel.val(snmp_v3.security_level);
                        inputComsSNMPDetailsAccessRight.val(snmp_v3.access_right);
                        inputComsSNMPDetailsAutoAlgorithm.val(snmp_v3.auth_algorithm);
                        inputComsSNMPDetailsAuthPassword.val(snmp_v3.auth_pwd);
                        inputComsSNMPDetailsPrivacyAlgorithm.val(snmp_v3.privacy_algorithm);
                        inputComsSNMPDetailsPrivacyPassword.val(snmp_v3.privacy_pwd);
                    }

                    // show modal
                    modalSnmpDetailSettings.modal('show');
                }else{
                    alert('Warning: ' + response.message);
                }
            },
            error: function (response) {
                if (elem !== undefined){
                    elem.attr('disabled', false).html(originalText);
                }
                alert('Error: ' + response.message);
            }
        });
    },

    update_snmp_details_settings: function (elem) {
        let originalText = elem.html();
        /*
        body example:
            {
                "port": 161,
                "trap": {
                    "alarm": True,
                    "manager_1_name": "Trap manager",
                    "manager_1_ip": "192.168.0.12",
                    "manager_2_name": "Trap manager",
                    "manager_2_ip": "192.168.0.13",
                    "manager_3_name": null,
                    "manager_3_ip": null,
                    "manager_4_name": null,
                    "manager_4_ip": null,
                },
                "snmp_v1_v2c": {
                    "read_community": "Public",
                    "write_community": "Private",
                },
                "snmp_v3": {
                    "usm_user": "rw",
                    "security_level": "auth/priv",
                    "access_right": "rw",
                    "auth_algorithm": "HMAC-SHA",
                    "auth_pwd": "123",
                    "privacy_algorithm": "HMAC-SHA",
                    "privacy_pwd": "123",
                },
            }
        */
        let read_community = "Public";
        let write_community = "Public";
        if (radioComsDetailsSettingsSNMPV1V2ReadCommunityPrivate.is(':checked')){
            read_community = "Private";
        }
        if (radioComsDetailsSettingsSNMPV1V2WriteCommunityPrivate.is(':checked')){
            write_community = "Private";
        }

        let usm_user = "rw";
        if (radioComsDetailsSettingsSNMPV3UsmUserRead.is(':checked')){
            usm_user = "r";
        }

        let payload = {
            "port": inputComsSnmpDetailsSettingsPort.val(),
            "trap": {
                "alarm": checkboxComsSnmpDetailsSettingsAlarmToTrap.is(':checked'),
                "manager_1_name": inputComsSnmpDetailsSettingsManager1Name.val(),
                "manager_1_ip": inputComsSnmpDetailsSettingsManager1Ip.val(),
                "manager_2_name": inputComsSnmpDetailsSettingsManager2Name.val(),
                "manager_2_ip": inputComsSnmpDetailsSettingsManager2Ip.val(),
                "manager_3_name": inputComsSnmpDetailsSettingsManager3Name.val(),
                "manager_3_ip": inputComsSnmpDetailsSettingsManager3Ip.val(),
                "manager_4_name": inputComsSnmpDetailsSettingsManager4Name.val(),
                "manager_4_ip": inputComsSnmpDetailsSettingsManager4Ip.val(),
            },
            "snmp_v1_v2c": {
                "read_community": read_community,
                "write_community": write_community,
            },
            "snmp_v3": {
                "usm_user": usm_user,
                "security_level": inputComsSNMPDetailsSecurityLevel.val(),
                "access_right": inputComsSNMPDetailsAccessRight.val(),
                "auth_algorithm": inputComsSNMPDetailsAutoAlgorithm.val(),
                "auth_pwd": inputComsSNMPDetailsAuthPassword.val(),
                "privacy_algorithm": inputComsSNMPDetailsPrivacyAlgorithm.val(),
                "privacy_pwd": inputComsSNMPDetailsPrivacyPassword.val(),
            },
        }
        $.ajax({
            url: COMS.url,
            type: 'POST',
            data: {
                'endpoint': 'network/snmp/detailed-settings',
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
                        modalSnmpDetailSettings.modal('hide');
                        alert('SNMP Details Settings Updated!');
                    }, 1500);
                }else{
                    alert('Warning: ' + response.message);
                }
            },
            error: function (response) {
                if (elem !== undefined){
                    elem.attr('disabled', false).html(originalText);
                }
                alert('Error: ' + response.message);
            }
        });
    },

    // Hosts
    show_modal_for_hosts: function (elem, action){
        let trParent = elem.parent().parent();
        let btnText = '';
        let host_id = 0;
        let valueForNameField = '';
        let valueForIpField = '';
        if (action === 'add'){
            btnText = 'Add Host';
        }else if (action === 'edit'){
            btnText = 'Edit Host';
            host_id = parseInt(trParent.attr('host_id'));
            valueForNameField = trParent.attr('host_name');
            valueForIpField = trParent.attr('host_ip');
        }else{
            btnText = 'Delete Host';
            host_id = parseInt(trParent.attr('host_id'));
            valueForNameField = trParent.attr('host_name');
            valueForIpField = trParent.attr('host_ip');
        }
        // body
        let htmlForBody = ''
        if (action !== 'delete'){
            htmlForBody =
                `<p class="bold textGreen">${btnText}</p>
                 <div class="row">
                    <div class="col">
                        <P>Name</P>
                        <div class="input-group mb-3">
                            <input id="inputComsHostName" type="text" class="form-control" value="${valueForNameField}" />
                        </div>
                    </div>
                    <div class="col">
                        <p>IP</p>
                        <div class="input-group mb-3">
                            <input id="inputComsHostIp" type="text" class="form-control" value="${valueForIpField}" />
                        </div>
                    </div>
                 </div>`;
        }else{
            htmlForBody =
                `<div class="iconWarn"></div>
                <p class="bold text-center">
                    ARE YOU SURE YOU WANT TO DELETE THIS HOST ?
                </p>
                <p>(This action can not be undone).</p>
                <div class="d-flex justify-content-start bd-highlight">
                    <div class="p-2 bd-highlight">
                        <span class="fw-bold">Name:</span> ${valueForNameField}
                    </div>
                </div>
                <div class="d-flex justify-content-start bd-highlight">
                    <div class="p-2 bd-highlight">
                        <span class="fw-bold">URL:</span> ${valueForIpField}
                    </div>
                </div>`
        }
        // modal body dynamic content
        modalComsHost.find('.modal-body').html(htmlForBody);
        // submit button
        btnComsHost.attr('action', action).attr('host_id', host_id).html(btnText);
        // show modal
        modalComsHost.modal({
            "backdrop":"static",
            "width": "400px"
        }).modal("show");
    },

    submit_host: function (elem){
        let originalText = elem.html();
        let action = elem.attr('action');
        let host_id = elem.attr('host_id');
        let inputComsHostName = $('#inputComsHostName');
        let inputComsHostIp = $('#inputComsHostIp');
        let host_name = inputComsHostName.val();
        let host_ip = inputComsHostIp.val();

        // validations
        if (action !== 'delete'){
            if (!host_name || host_name === '' || host_name === undefined){
                inputComsHostName.addClass('borderRed');
                return false;
            }else{
                inputComsHostName.removeClass('borderRed');
            }
            if (!host_ip || host_ip === '' || host_ip === undefined){
                inputComsHostIp.addClass('borderRed');
                return false;
            }else{
                inputComsHostIp.removeClass('borderRed');
            }
        }
        $.ajax({
            url: COMS.url_hosts,
            type: 'POST',
            data: {
                'action': action,
                'id': host_id,
                'name': host_name,
                'ip': host_ip
            },
            dataType: 'json',
            beforeSend: function (){
                elem.attr('disabled', true).html(SPINNER_SM_DARK);
            },
            success: function(response) {
                elem.attr('disabled', false).html(originalText);
                if (response.result === 'ok'){
                    modalComsHost.modal('hide');
                    setTimeout(function (){
                        location.reload();
                    }, 500);
                }
                alert(response.message);
            },
            error: function (response) {
                elem.attr('disabled', false).html(originalText);
                alert('Error: ' + JSON.stringify(response));
            }
        });
    }
};


$(function() {

    // COMS
    // Modbus
    COMS.get_modbus_addr();
    // Services
    COMS.get_services();
    // Network Setup
    COMS.update_network_setup_form();
    COMS.get_network_setup();
    // SNMP Setup
    // COMS.get_snmp_setup();

});
