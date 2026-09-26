/* Bluetooth and NTP cards of the Coms page (the touchscreen's Networks menu). */
(function () {
    const $ = (id) => document.getElementById(id);
    const busy = {bt: false};

    // ---- Bluetooth -----------------------------------------------------------
    let btState = null;
    let lastKey = '';

    function deviceRow(d) {
        const status = d.connected ? NE.t('btDeviceConnected') : d.paired ? NE.t('btDevicePaired') : NE.t('btDeviceAvailable');
        const primary = !d.paired ? ['pair', NE.t('btPair')] : d.connected ? ['disconnect', NE.t('btDisconnect')] : ['connect', NE.t('btConnect')];
        const remove = d.paired ? '<button type="button" class="ne-btn sm" data-bt="remove" data-mac="' + NE.escapeHtml(d.mac) + '">' + NE.escapeHtml(NE.t('btRemove')) + '</button>' : '';
        return '<div class="ne-card" style="padding:12px"><div class="ne-outlet-head"><h3>' + NE.escapeHtml(d.name || d.mac) +
            '</h3><span class="ne-badge ' + (d.connected ? 'ok' : '') + '">' + NE.escapeHtml(status) + '</span></div>' +
            '<div class="ne-muted" style="font-size:.82rem">' + NE.escapeHtml(d.mac) + (d.rssi !== null && d.rssi !== undefined ? ' · ' + NE.escapeHtml(d.rssi) + ' dBm' : '') + '</div>' +
            '<div class="ne-actions mt-2"><button type="button" class="ne-btn sm primary" data-bt="' + primary[0] + '" data-mac="' +
            NE.escapeHtml(d.mac) + '">' + NE.escapeHtml(primary[1]) + '</button>' + remove + '</div></div>';
    }

    function renderBt(st) {
        btState = st;
        // Do not fight the user while a toggle request is in flight
        if (!busy.bt) {
            $('btPowered').checked = !!st.powered;
            $('btDiscoverable').checked = !!st.discoverable; $('btPairable').checked = !!st.pairable;
        }
        $('btDiscoverable').disabled = !st.powered; $('btPairable').disabled = !st.powered; $('btScan').disabled = !st.powered;
        $('btScan').textContent = st.discovering ? NE.t('btScanStop') : NE.t('btScanStart');
        $('btPairing').hidden = !st.pairing_request;
        if (st.pairing_request) {
            $('btPairingName').textContent = st.pairing_name || ''; $('btPairingMac').textContent = st.pairing_mac || '';
            $('btPairingKey').textContent = st.pairing_passkey || '';
        }
        const key = JSON.stringify(st.devices);
        if (key !== lastKey) {
            lastKey = key;
            $('btDevices').innerHTML = st.devices.map(deviceRow).join('');
        }
        $('btEmpty').hidden = st.devices.length !== 0;
    }

    async function loadBt() {
        try { renderBt(await NE.api('GET', 'settings/bluetooth')); }
        catch (err) { if ($('btDevices').children.length === 0) { NE.toast(NE.t('btLoadFailed'), 'error'); } }
    }

    async function btCall(method, path, body) {
        try {
            await NE.api(method, path, body);
        } catch (err) {
            NE.toast(NE.t('btActionFailed'), 'error');
        }
        await loadBt();
    }

    ['btPowered', 'btDiscoverable', 'btPairable'].forEach((id) => {
        $(id).addEventListener('change', async () => {
            busy.bt = true;
            await btCall('PUT', 'settings/bluetooth', {
                powered: $('btPowered').checked, discoverable: $('btDiscoverable').checked, pairable: $('btPairable').checked,
            });
            busy.bt = false;
            renderBt(btState);
        });
    });

    $('btScan').addEventListener('click', () => {
        const stop = btState && btState.discovering;
        btCall('POST', 'settings/bluetooth/scan/' + (stop ? 'stop' : 'start'));
    });

    document.addEventListener('click', (ev) => {
        const device = ev.target.closest('[data-bt]');
        if (device) {
            device.disabled = true;
            btCall('POST', 'settings/bluetooth/devices/' + device.getAttribute('data-mac') + '/' + device.getAttribute('data-bt'));
            return;
        }
        const pair = ev.target.closest('[data-pair]');
        if (pair) { btCall('POST', 'settings/bluetooth/pairing/' + pair.getAttribute('data-pair')); }
    });

    // ---- NTP -----------------------------------------------------------------
    function fillNtp(st, keepForm) {
        if (!keepForm) {
            $('ntpEnabled').checked = !!st.enabled; $('ntpServer').value = st.server || ''; $('ntpOffset').value = String(st.time_offset);
        }
        const badge = $('ntpSync');
        badge.textContent = !st.enabled ? NE.t('ntpOff') : st.synchronized ? NE.t('ntpSynced') : NE.t('ntpNotSynced');
        badge.className = 'ne-badge ' + (!st.enabled ? '' : st.synchronized ? 'ok' : 'warning');
    }

    (function buildOffsets() {
        let html = '';
        for (let h = -12; h <= 12; h++) { html += '<option value="' + h + '">UTC' + (h >= 0 ? '+' : '') + h + '</option>'; }
        $('ntpOffset').innerHTML = html;
    })();

    async function loadNtp(keepForm) {
        try { fillNtp(await NE.api('GET', 'settings/ntp'), keepForm); } catch (err) { /* status stays as is */ }
    }

    $('formNtp').addEventListener('submit', async (ev) => {
        ev.preventDefault();
        const server = $('ntpServer').value.trim();
        if ($('ntpEnabled').checked && !server) { NE.toast(NE.t('ntpServerRequired'), 'error'); $('ntpServer').focus(); return; }
        try {
            const st = await NE.api('PUT', 'settings/ntp', {
                enabled: $('ntpEnabled').checked, server: server || '0.openembedded.pool.ntp.org',
                time_offset: Number($('ntpOffset').value),
            });
            fillNtp(st, false); NE.toast(NE.t('saved'), 'ok');
        } catch (err) {
            NE.toast(NE.t('saveFailed') + (err.message ? ': ' + err.message : ''), 'error');
        }
    });

    loadNtp(false);
    NE.poll(() => { loadNtp(true); return loadBt(); }, 3000);
})();

/* SNMP and Modbus cards. SNMP uses the same endpoint as the touchscreen
   (network/snmp/display-settings); passwords are write-only. */
(function () {
    const $ = (id) => document.getElementById(id);
    const RE_COMMUNITY = /^[A-Za-z0-9_.-]{1,64}$/;
    const RE_USER = /^[A-Za-z0-9_.-]{1,32}$/;
    const RE_PASSWORD = /^[A-Za-z0-9_.@#%+=:-]{8,64}$/;
    const RE_HOST_LABEL = /^[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?$/;
    const managers = () => Array.from(document.querySelectorAll('#formSnmp [data-mgr]'));
    let loaded = null;   // last configuration from the PDU

    function validTarget(value) {
        if (!value) { return true; }
        const parts = value.replace(/\.$/, '').split('.');
        if (parts.length === 4 && parts.every((p) => /^\d{1,3}$/.test(p))) { return parts.every((p) => Number(p) <= 255); }
        return !parts.every((p) => /^\d+$/.test(p)) && parts.every((p) => RE_HOST_LABEL.test(p));
    }

    function syncVisibility() {
        const v3 = $('snmpVersion').value === 'V3';
        const level = $('snmpV3Level').value;
        $('rowCommunity').hidden = v3;
        $('blockV3').hidden = !v3;
        $('rowAuth').hidden = level === 'noAuthNoPriv';
        $('rowPriv').hidden = level !== 'authPriv';
        $('snmpPwdHint').hidden = level === 'noAuthNoPriv';
        const keep = !!(loaded && loaded.v3_configured && $('snmpV3User').value.trim() === loaded.v3_user);
        ['snmpV3AuthPwd', 'snmpV3PrivPwd'].forEach((id) => { $(id).placeholder = keep ? NE.t('snmpPwdKeep') : ''; });
    }

    function fill(cfg) {
        loaded = cfg;
        $('snmpEnabled').checked = !!cfg.enabled;
        $('snmpVersion').value = cfg.version;
        $('snmpCommunity').value = cfg.community || '';
        $('snmpSet').checked = !!cfg.set_enabled;
        $('snmpTraps').checked = !!cfg.traps_enabled;
        managers().forEach((el, i) => { el.value = cfg['manager_' + (i + 1)] || ''; });
        $('snmpV3User').value = cfg.v3_user || '';
        $('snmpV3Level').value = cfg.v3_security_level;
        $('snmpV3AuthAlg').value = cfg.v3_auth_algorithm;
        $('snmpV3PrivAlg').value = cfg.v3_privacy_algorithm;
        $('snmpV3AuthPwd').value = ''; $('snmpV3PrivPwd').value = '';
        syncVisibility();
    }

    async function loadSnmp() {
        try { fill(await NE.api('GET', 'network/snmp/display-settings')); }
        catch (err) { NE.toast(NE.t('loadFailed', 'Could not load SNMP') + (err.message ? ': ' + err.message : ''), 'error'); }
    }

    ['snmpVersion', 'snmpV3Level'].forEach((id) => $(id).addEventListener('change', syncVisibility));
    $('snmpV3User').addEventListener('input', syncVisibility);

    function invalid(id, messageKey) { NE.toast(NE.t(messageKey), 'error'); $(id).focus(); return false; }

    function collect() {
        const version = $('snmpVersion').value;
        const community = $('snmpCommunity').value.trim() || (loaded && loaded.community) || '';
        if (version !== 'V3' && !RE_COMMUNITY.test(community)) { return invalid('snmpCommunity', 'snmpCommunityInvalid'); }
        for (const el of managers()) {
            if (!validTarget(el.value.trim())) { return invalid(el.id, 'snmpMgrInvalid'); }
        }
        const body = {
            enabled: $('snmpEnabled').checked, version: version, set_enabled: $('snmpSet').checked,
            community: RE_COMMUNITY.test(community) ? community : (loaded && RE_COMMUNITY.test(loaded.community) ? loaded.community : 'public'), traps_enabled: $('snmpTraps').checked,
            v3_security_level: $('snmpV3Level').value, v3_auth_algorithm: $('snmpV3AuthAlg').value,
            v3_privacy_algorithm: $('snmpV3PrivAlg').value,
        };
        managers().forEach((el, i) => { body['manager_' + (i + 1)] = el.value.trim() || null; });
        if (version === 'V3') {
            const user = $('snmpV3User').value.trim();
            if (!RE_USER.test(user)) { return invalid('snmpV3User', 'snmpUserInvalid'); }
            body.v3_user = user;
            const sameUser = !!(loaded && loaded.v3_configured && loaded.v3_user === user);
            const level = body.v3_security_level;
            const auth = $('snmpV3AuthPwd').value; const priv = $('snmpV3PrivPwd').value;
            if (level !== 'noAuthNoPriv') {
                if (auth || !sameUser) { if (!RE_PASSWORD.test(auth)) { return invalid('snmpV3AuthPwd', 'snmpPwdInvalid'); } body.v3_auth_password = auth; }
            }
            if (level === 'authPriv') {
                if (priv || !sameUser) { if (!RE_PASSWORD.test(priv)) { return invalid('snmpV3PrivPwd', 'snmpPwdInvalid'); } body.v3_privacy_password = priv; }
            }
        }
        return body;
    }

    $('formSnmp').addEventListener('submit', async (ev) => {
        ev.preventDefault();
        const body = collect();
        if (!body) { return; }
        const button = $('snmpSave');
        button.disabled = true;
        try {
            fill(await NE.api('PUT', 'network/snmp/display-settings', body));
            NE.toast(NE.t('saved'), 'ok');
        } catch (err) {
            NE.toast(err.status === 500 ? NE.t('snmpApplyFailed') : NE.t('saveFailed') + (err.message ? ': ' + err.message : ''), 'error');
            if (err.status === 500) { loadSnmp(); }
        } finally {
            button.disabled = false;
        }
    });

    // ---- Modbus --------------------------------------------------------------
    async function loadModbus() {
        try {
            const [addr, services] = await Promise.all([NE.api('GET', 'settings/modbus'), NE.api('GET', 'network/services')]);
            if (document.activeElement !== $('modbusAddr')) { $('modbusAddr').value = addr.addr; }
            $('modbusEnabled').checked = !!services.modbus;
        } catch (err) { /* keep the current values */ }
    }

    $('modbusEnabled').addEventListener('change', async () => {
        const enable = $('modbusEnabled').checked;
        try { await NE.api('POST', 'settings/' + (enable ? 'start' : 'stop') + '-modbus'); }
        catch (err) { NE.toast(NE.t('modbusFailed'), 'error'); }
        await loadModbus();
    });

    $('formModbus').addEventListener('submit', async (ev) => {
        ev.preventDefault();
        const text = $('modbusAddr').value.trim();
        const addr = Number(text);
        if (text === '' || !Number.isInteger(addr) || addr < 0 || addr > 255) { NE.toast(NE.t('modbusAddrInvalid'), 'error'); $('modbusAddr').focus(); return; }
        try { await NE.api('PUT', 'settings/modbus', {addr: addr}); NE.toast(NE.t('saved'), 'ok'); }
        catch (err) { NE.toast(NE.t('saveFailed') + (err.message ? ': ' + err.message : ''), 'error'); }
        await loadModbus();
    });

    loadSnmp();
    loadModbus();
})();
