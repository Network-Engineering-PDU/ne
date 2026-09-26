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
