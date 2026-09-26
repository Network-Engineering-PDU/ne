/* Outlets: live data and on/off control, gated by the PDU license the same way
   the touchscreen does (A1 none, A2 data, B1 control, B2 both). */
(function () {
    const grid = document.getElementById('outletGrid');
    const empty = document.getElementById('outletEmpty');
    const bulk = document.getElementById('outletBulk');
    const licenseBox = document.getElementById('outletLicense');
    const licenseText = document.getElementById('outletLicenseText');
    const csvUrls = NE.t('csvUrls', {});

    let outlets = [];          // [{index, name, socket}]
    let canControl = false;
    let canRead = false;
    let licenseKnown = false;
    const busy = new Set();    // outlet indexes with a pending request
    const state = {};          // index -> bool
    let data = {};             // index -> live data

    function metric(label, value, unit) {
        return '<div><span>' + NE.escapeHtml(label) + '</span><b>' + NE.escapeHtml(value) + '</b>' +
            '<span>' + NE.escapeHtml(unit) + '</span></div>';
    }

    function card(o) {
        const on = !!state[o.index];
        const d = data[o.index];
        const csv = csvUrls[o.index + 1];
        let body = '';
        if (canRead && d) {
            body = '<div class="ne-metrics">' +
                metric(NE.t('voltage'), NE.fmt(d.voltage, 1), 'V') +
                metric(NE.t('current'), NE.fmt(d.current, 2), 'A') +
                metric(NE.t('activePower'), NE.fmt(d.active_power, 1), 'W') + '</div>' +
                '<details><summary class="ne-muted">' + NE.escapeHtml(NE.t('details')) + '</summary>' +
                '<dl class="ne-kv mt-2">' +
                '<dt>' + NE.escapeHtml(NE.t('reactivePower')) + '</dt><dd>' + NE.fmt(d.reactive_power, 1) + ' VAr</dd>' +
                '<dt>' + NE.escapeHtml(NE.t('apparentPower')) + '</dt><dd>' + NE.fmt(d.apparent_power, 1) + ' VA</dd>' +
                '<dt>' + NE.escapeHtml(NE.t('powerFactor')) + '</dt><dd>' + NE.fmt(d.power_factor, 2) + '</dd>' +
                '<dt>' + NE.escapeHtml(NE.t('frequency')) + '</dt><dd>' + NE.fmt(d.frequency, 2) + ' Hz</dd>' +
                '<dt>' + NE.escapeHtml(NE.t('phase')) + '</dt><dd>' + NE.fmt(d.phase, 1) + '°</dd>' +
                '<dt>' + NE.escapeHtml(NE.t('energy')) + '</dt><dd>' + NE.fmt(d.energy, 1) + ' Wh</dd>' +
                '<dt>' + NE.escapeHtml(NE.t('socket')) + '</dt><dd>' + NE.escapeHtml(d.conn) + '</dd>' +
                '<dt>' + NE.escapeHtml(NE.t('fuse')) + '</dt><dd>' +
                NE.escapeHtml((NE.t('fuseNames', []) || [])[d.fuse] || '-') + '</dd></dl>' +
                (csv ? '<a class="ne-btn sm mt-2" href="' + NE.escapeHtml(csv) + '"><svg class="ne-icon"><use href="#i-download"/></svg>CSV</a>' : '') +
                '</details>';
        }
        const toggle = canControl ?
            '<label class="ne-switch" aria-label="' + NE.escapeHtml(o.name) + '"><input type="checkbox" data-outlet="' +
            o.index + '"' + (on ? ' checked' : '') + (busy.has(o.index) ? ' disabled' : '') + '><span></span></label>' :
            '<span class="ne-badge ' + (on ? 'ok' : '') + '">' + NE.escapeHtml(on ? NE.t('on') : NE.t('off')) + '</span>';
        return '<article class="ne-card ne-outlet' + (on ? '' : ' off') + '"><div class="ne-outlet-head"><h3>' +
            NE.escapeHtml(o.name) + '</h3>' + (canControl ? '<span class="ne-badge ' + (on ? 'ok' : '') + '">' +
            NE.escapeHtml(on ? NE.t('on') : NE.t('off')) + '</span>' : '') + toggle + '</div>' + body + '</article>';
    }

    function render() {
        // Keep an open <details> and focus stable across refreshes
        const openIdx = Array.from(grid.querySelectorAll('article')).map((a, i) => a.querySelector('details[open]') ? i : -1).filter((i) => i >= 0);
        const focused = document.activeElement && document.activeElement.getAttribute &&
            document.activeElement.getAttribute('data-outlet');
        grid.innerHTML = outlets.map(card).join('');
        grid.querySelectorAll('article').forEach((a, i) => {
            if (openIdx.includes(i)) { const dt = a.querySelector('details'); if (dt) { dt.open = true; } }
        });
        if (focused !== null && focused !== undefined) {
            const el = grid.querySelector('[data-outlet="' + focused + '"]');
            if (el) { el.focus(); }
        }
        empty.hidden = outlets.length !== 0 || !licenseKnown;
        bulk.hidden = !(canControl && outlets.length);
    }

    function applyLicense(type) {
        canControl = type === 'B1' || type === 'B2';
        canRead = type === 'A2' || type === 'B2';
        licenseKnown = true;
        const message = type === 'A2' ? NE.t('licenseDataOnly') :
            type === 'B1' ? NE.t('licenseControlOnly') : (canControl ? '' : NE.t('licenseNone'));
        licenseText.textContent = message;
        licenseBox.hidden = !message;
    }

    async function loadList() {
        const list = await NE.api('GET', 'outputs');
        outlets = list.map((o) => ({index: o.line_id - 1, name: o.name, socket: o.socket_type}));
    }

    async function refresh() {
        try {
            const lic = await NE.api('GET', 'settings/license');
            applyLicense(lic.type_id);
            if (!outlets.length) { await loadList(); }
            const status = await NE.api('GET', 'outputs/switch-status');
            Object.keys(status || {}).forEach((k) => { if (!busy.has(Number(k))) { state[k] = status[k]; } });
            data = canRead ? await NE.api('GET', 'outputs/data') : {};
            render();
        } catch (err) {
            NE.toast(NE.t('loadFailed'), 'error');
        }
    }

    async function setOutlet(index, value) {
        await NE.api('PUT', 'outputs/' + index + '/switch-status', {switch_status: value});
    }

    grid.addEventListener('change', async (ev) => {
        const input = ev.target.closest('[data-outlet]');
        if (!input) { return; }
        const index = Number(input.getAttribute('data-outlet'));
        const value = input.checked;
        const outlet = outlets.find((o) => o.index === index);
        input.checked = !value;   // only change once confirmed and applied
        const ok = await NE.confirm(outlet.name, (value ? NE.t('enableOne') : NE.t('disableOne')) + ' ' + outlet.name + '?',
            {confirmLabel: value ? NE.t('enableOne') : NE.t('disableOne')});
        if (!ok) { return; }
        busy.add(index);
        render();
        try {
            await setOutlet(index, value);
            state[index] = value;
        } catch (err) {
            NE.toast(NE.t('updateFailed') + ': ' + err.message, 'error');
        } finally {
            busy.delete(index);
            render();
        }
    });

    async function setAll(value) {
        const ok = await NE.confirm(NE.t('confirm'), value ? NE.t('enableAllQ') : NE.t('disableAllQ'),
            {confirmLabel: value ? NE.t('enableOne') : NE.t('disableOne'), danger: !value});
        if (!ok) { return; }
        outlets.forEach((o) => busy.add(o.index));
        render();
        const results = await Promise.allSettled(outlets.map((o) => setOutlet(o.index, value)));
        results.forEach((r, i) => { if (r.status === 'fulfilled') { state[outlets[i].index] = value; } });
        outlets.forEach((o) => busy.delete(o.index));
        render();
        if (results.some((r) => r.status === 'rejected')) { NE.toast(NE.t('updateSomeFailed'), 'error'); }
    }

    document.getElementById('btnEnableAll').addEventListener('click', () => setAll(true));
    document.getElementById('btnDisableAll').addEventListener('click', () => setAll(false));

    NE.poll(refresh, 3000);
})();
