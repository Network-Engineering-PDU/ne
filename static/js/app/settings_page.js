/* Settings page: PDU info + rated current, touchscreen settings and
   translations, software update, certificates and maintenance. Reads and writes the PDU API through
   the proxy; file uploads, reboot and factory reset go through this page's own
   Django endpoint (they need server side file handling). */
(function () {
    const $ = (id) => document.getElementById(id);
    const setText = (id, value) => { $(id).textContent = (value === undefined || value === null || value === '') ? '-' : value; };
    const RATED = [10, 15, 16, 20, 30, 32];   // same choices as the touchscreen
    let displayConfig = null;

    async function guarded(action, failMessage) {
        try {
            return await action();
        } catch (err) {
            NE.toast(failMessage + (err.message ? ': ' + err.message : ''), 'error');
            return undefined;
        }
    }

    // ---- PDU info ----------------------------------------------------------
    async function loadPdu() {
        const [sys, pdu] = await Promise.all([NE.api('GET', 'settings/system-info'), NE.api('GET', 'settings/pdu-info')]);
        setText('pduPn', sys.product_pn); setText('pduSn', sys.product_sn); setText('pduVer', sys.sw_version);
        setText('pduMac', sys.lan_mac); setText('pduIp', sys.ip); setText('pduUptime', sys.uptime);
        setText('pduOutlets', pdu.outlet_count); setText('pduController', pdu.controller); setText('pduType', pdu.type);
        const select = $('ratedCurrent');
        const values = RATED.includes(pdu.rated_current) ? RATED : RATED.concat([pdu.rated_current]).sort((a, b) => a - b);
        select.innerHTML = values.map((v) => '<option value="' + v + '">' + v + ' A</option>').join('');
        select.value = String(pdu.rated_current);
    }

    $('formRated').addEventListener('submit', async (ev) => {
        ev.preventDefault();
        const done = await guarded(async () => {
            await NE.api('PUT', 'settings/pdu-info', {rated_current: Number($('ratedCurrent').value)});
            return true;
        }, NE.t('saveFailed'));
        if (done) { NE.toast(NE.t('saved'), 'ok'); }
    });

    // ---- Display ------------------------------------------------------------
    const textInputs = () => Array.from(document.querySelectorAll('#formDisplay [data-key]'));

    function fillDisplay(cfg) {
        displayConfig = cfg;
        $('dispRotation').value = String(cfg.rotation === 3 ? 3 : 2);
        $('dispInactivity').value = cfg.inactivity_time;
        $('dispSkipLogin').checked = !!cfg.skip_login;
        textInputs().forEach((el) => { el.value = cfg[el.getAttribute('data-key')] || ''; });
    }

    async function loadDisplay() { fillDisplay(await NE.api('GET', 'display-config')); }

    $('formDisplay').addEventListener('submit', async (ev) => {
        ev.preventDefault();
        const minutes = Number($('dispInactivity').value);
        if (!Number.isInteger(minutes) || minutes < 1 || minutes > 300) {
            NE.toast(NE.t('invalidRange') + ' (1 – 300)', 'error');
            $('dispInactivity').focus();
            return;
        }
        const rotation = Number($('dispRotation').value);
        if (displayConfig && rotation !== displayConfig.rotation && !(await NE.confirm(NE.t('rotationRestart').split('.')[0], NE.t('rotationRestart')))) {
            return;
        }
        const body = Object.assign({}, displayConfig, {
            rotation: rotation, inactivity_time: minutes, skip_login: $('dispSkipLogin').checked,
        });
        textInputs().forEach((el) => { body[el.getAttribute('data-key')] = el.value.trim(); });
        const saved = await guarded(() => NE.api('PUT', 'display-config', body), NE.t('saveFailed'));
        if (saved) { fillDisplay(saved); NE.toast(NE.t('saved'), 'ok'); }
    });

    // ---- Translation files: touchscreen and web interface ---------------------
    /* One card per translation file (templates/partials/translations_card.html).
       p prefixes its element ids and its messages (falling back to the tr_
       ones); files is {file, info}: the table's URL (GET download, POST the CSV
       as the body, DELETE to reset) and its status URL. With reload, the page
       reloads after a change to show the new texts, keeping the report. */
    function translationSection(p, files, reload) {
        const el = (id) => $(p + id);
        const msg = (key, fallback) => NE.t(p + '_' + key, NE.t('tr_' + key, fallback));
        const storedReport = p + 'Report';
        let names = {};

        async function request(method, url, body) {
            const options = {method: method, credentials: 'same-origin', headers: {'X-Requested-With': 'XMLHttpRequest'}};
            if (body) { options.body = body; options.headers['Content-Type'] = 'text/csv'; }
            let response;
            try { response = await fetch(url, options); } catch (err) { throw new Error(NE.t('apiUnreachable', 'PDU API unreachable')); }
            if (response.status === 401) { window.location.href = '/login/'; throw new Error('Unauthorized'); }
            const data = await response.json().catch(() => null);
            if (!response.ok || !data) {
                const e = new Error(data && data.code ? msg('err_' + data.code, data.detail) : ((data && (data.message || data.detail)) || 'HTTP ' + response.status));
                throw e;
            }
            return data;
        }

        function fill(info) {
            names = {};
            info.languages.forEach((l) => { names[l.code] = l.name; });
            setText(p + 'State', info.custom ? NE.t('tr_custom') + ' · ' + NE.formatTime(info.modified) : NE.t('tr_original'));
            setText(p + 'Langs', info.languages.map((l) => l.name).join(', '));
            el('Reset').disabled = !info.custom;
        }

        function reasonText(r) {
            let text = msg(r.reason, r.reason);
            if (r.reason === 'placeholders' && r.detail) { text += ' ' + NE.t('tr_mustContain') + ': ' + r.detail; }
            else if (r.reason !== 'colour_marks' && r.reason !== 'too_long' && r.detail) { text += ': ' + r.detail; }
            return text;
        }

        function showReport(report) {
            const lines = [NE.t('tr_summary').replace('{accepted}', report.accepted)
                .replace('{changed}', report.changed).replace('{rejected}', report.rejected.length)];
            if (report.new_languages.length) {
                lines.push(NE.t('tr_newLangs') + ': ' + report.new_languages.map((c) => names[c] || c).join(', '));
            }
            if (report.ignored_columns.length) { lines.push(NE.t('tr_ignored') + ': ' + report.ignored_columns.join(', ')); }
            const summary = el('Summary');
            summary.textContent = lines.join(' ');
            summary.className = 'ne-alert' + (report.rejected.length ? ' warning' : '');
            const esc = NE.escapeHtml;
            el('Rejected').innerHTML = report.rejected.map((r) => '<tr><td>' + esc(r.row) + '</td><td>' + esc(r.id) +
                '</td><td>' + esc(names[r.language] || r.language) + '</td><td style="white-space:normal">' +
                esc(reasonText(r)) + '</td></tr>').join('');
            el('RejectedWrap').hidden = report.rejected.length === 0;
            el('Report').hidden = false;
        }

        // A reload shows the new texts: the report waits in the session.
        function reloadWith(report) {
            try { sessionStorage.setItem(storedReport, JSON.stringify(report)); } catch (err) { /* shown nowhere */ }
            window.location.reload();
        }

        el('Form').addEventListener('submit', async (ev) => {
            ev.preventDefault();
            const input = el('File');
            const file = input.files && input.files[0];
            if (!file) { NE.toast(NE.t('fileRequired'), 'error'); return; }
            if (!/\.csv$/i.test(file.name)) { NE.toast(NE.t('wrongExt') + ' .csv', 'error'); return; }
            const button = el('Form').querySelector('button[type="submit"]');
            button.disabled = true;
            let data;
            try {
                data = await request('POST', files.file, file);
            } catch (err) {
                NE.toast(NE.t('uploadFailed') + ': ' + err.message, 'error');
                return;
            } finally {
                button.disabled = false;
            }
            input.value = '';
            if (reload) { reloadWith(data.report); return; }
            fill(data);
            showReport(data.report);
            NE.toast(NE.t('saved'), 'ok');
        });

        el('Reset').addEventListener('click', async () => {
            if (!(await NE.confirm(NE.t('tr_resetTitle'), msg('resetQ'), {danger: true, confirmLabel: NE.t('tr_resetTitle')}))) { return; }
            const info = await guarded(() => request('DELETE', files.file), NE.t('saveFailed'));
            if (!info) { return; }
            if (reload) { reloadWith(null); return; }
            fill(info);
            el('Report').hidden = true;
            NE.toast(msg('restarting'), 'ok');
        });

        return async function load() {
            fill(await request('GET', files.info));
            let report = null;
            try {
                report = JSON.parse(sessionStorage.getItem(storedReport));
                sessionStorage.removeItem(storedReport);
            } catch (err) { report = null; }
            if (report) { showReport(report); NE.toast(NE.t('saved'), 'ok'); }
        };
    }

    const loadTranslations = translationSection('tr',
        {file: '/pdu/display-translations', info: '/pdu/display-translations/info'}, false);
    const loadWebTranslations = translationSection('wtr',
        {file: '/web-translations/', info: '/web-translations/info'}, true);

    // ---- Software update ----------------------------------------------------
    const BADGE_KIND = {ok: 'ok', info: 'info', warning: 'warning', error: 'error'};
    let updateActive = false;      // an update is running: poll faster, lock the controls
    let wasActive = false;

    function describe(summary) {
        let text = NE.t('upd_' + summary.key);
        if (summary.key === 'downloading') { text += ' ' + summary.params.percent + '%'; }
        if (summary.params.source && ['staging', 'installing', 'pendingConfirm'].includes(summary.key)) {
            text += ' (' + NE.t('src_' + summary.params.source, summary.params.source) + ')';
        }
        if (summary.key === 'failed' && summary.params.error) { text += ': ' + summary.params.error; }
        return text;
    }

    function setUpdateBusy(active) {
        updateActive = active;
        $('btnOtaCheck').disabled = active;
        const upload = $('formUpload').querySelector('button[type="submit"]');
        upload.disabled = active;
        upload.title = active ? NE.t('updateBusy') : '';
    }

    function renderSummary(st) {
        const summary = UpdateStatus.summarize(st);
        const badge = $('otaStatus');
        badge.textContent = describe(summary);
        badge.className = 'ne-badge ' + (BADGE_KIND[summary.kind] || '');
        $('otaDetail').textContent = '';
        $('otaProgressWrap').hidden = summary.progress === null;
        if (summary.progress !== null) { $('otaProgress').style.width = summary.progress + '%'; }
        $('otaPending').hidden = summary.key !== 'pendingConfirm';
        setUpdateBusy(summary.active);
        wasActive = summary.active;
    }

    function fillUpdate(st) {
        setText('otaInstalled', st.installed_version); setText('otaAvailable', st.available_version);
        setText('otaLast', st.last_check_time);
        renderSummary(st);
        if (document.activeElement && document.activeElement.closest('#formUpdate')) { return; }   // do not overwrite edits
        $('otaEnabled').checked = !!st.ota_enabled; $('otaAuto').checked = !!st.auto_update;
        $('otaInterval').value = st.check_interval_hours; $('otaServer').value = st.update_server || '';
    }

    async function loadUpdate() {
        try {
            fillUpdate(await NE.api('GET', 'settings/update-status'));
        } catch (err) {
            // Mid update the PDU restarts its services (or reboots): say so instead of keeping an old status
            if (wasActive) {
                const badge = $('otaStatus');
                badge.textContent = NE.t('upd_restarting'); badge.className = 'ne-badge warning';
            }
            throw err;
        }
    }

    // Poll every 2 s while an update is running, otherwise every 15 s.
    (function pollUpdate() {
        const next = () => setTimeout(pollUpdate, updateActive || wasActive ? 2000 : 15000);
        if (document.hidden) { next(); return; }
        loadUpdate().then(next, next);
    })();

    $('btnOtaCheck').addEventListener('click', async () => {
        const btn = $('btnOtaCheck');
        btn.disabled = true; $('otaStatus').textContent = NE.t('checking'); $('otaStatus').className = 'ne-badge info';
        const st = await guarded(() => NE.api('POST', 'settings/ota-check-now'), NE.t('loadFailed'));
        btn.disabled = false;
        if (st) { fillUpdate(st); } else { loadUpdate().catch(() => {}); }
    });

    $('formUpdate').addEventListener('submit', async (ev) => {
        ev.preventDefault();
        const hours = Number($('otaInterval').value);
        if (!Number.isInteger(hours) || hours < 1 || hours > 8760) {
            NE.toast(NE.t('invalidRange') + ' (1 – 8760)', 'error'); $('otaInterval').focus(); return;
        }
        const ok = await guarded(async () => {
            await NE.api('PUT', 'settings/update-settings', {
                auto_update: $('otaAuto').checked, ota_enabled: $('otaEnabled').checked,
                check_interval_hours: hours, update_server: $('otaServer').value.trim(),
            });
            return true;
        }, NE.t('saveFailed'));
        if (ok) { NE.toast(NE.t('saved'), 'ok'); loadUpdate().catch(() => {}); }
    });

    // ---- Uploads, reboot, factory reset (Django endpoint) -------------------
    async function postToSettings(fields, file) {
        const form = new FormData();
        Object.keys(fields).forEach((k) => form.append(k, fields[k]));
        if (file) { form.append('file', file); }
        let response;
        try {
            response = await fetch(SETTINGS_URL, {method: 'POST', body: form, credentials: 'same-origin',
                headers: {'X-Requested-With': 'XMLHttpRequest'}});
        } catch (err) { return {result: 'bad', message: NE.t('apiUnreachable')}; }
        try { return await response.json(); } catch (err) { return {result: 'bad', message: 'HTTP ' + response.status}; }
    }

    async function upload(form, input) {
        const file = input.files && input.files[0];
        if (!file) { NE.toast(NE.t('fileRequired'), 'error'); return; }
        const ext = form.getAttribute('data-ext');
        if (ext && !file.name.endsWith(ext)) { NE.toast(NE.t('wrongExt') + ' ' + ext, 'error'); return; }
        const button = form.querySelector('button[type="submit"]');
        button.disabled = true;
        const res = await postToSettings({endpoint: form.getAttribute('data-endpoint')}, file);
        button.disabled = false;
        if (res.result === 'ok') { NE.toast(res.message || NE.t('saved'), 'ok'); input.value = ''; loadUpdate().catch(() => {}); }
        else { NE.toast(res.message || NE.t('uploadFailed'), 'error'); }
    }

    document.querySelectorAll('form[data-upload]').forEach((form) => {
        form.addEventListener('submit', (ev) => { ev.preventDefault(); upload(form, form.querySelector('input[type="file"]')); });
    });
    $('formUpload').addEventListener('submit', (ev) => { ev.preventDefault(); upload($('formUpload'), $('fileUpdate')); });

    async function maintenance(endpoint, title, question, danger) {
        if (!(await NE.confirm(title, question, {danger: danger, confirmLabel: title}))) { return; }
        const res = await postToSettings({endpoint: endpoint});
        if (res.result === 'ok') { NE.toast(NE.t('requestSent'), 'ok'); }
        else { NE.toast(res.message || NE.t('saveFailed'), 'error'); }
    }
    $('btnReboot').addEventListener('click', () => maintenance('settings/system-reboot', NE.t('rebootTitle'), NE.t('rebootQ'), false));
    $('btnFactory').addEventListener('click', () => maintenance('settings/factory-reset', NE.t('factoryTitle'), NE.t('factoryQ'), true));

    // ---- Init ---------------------------------------------------------------
    [loadPdu, loadDisplay, loadTranslations, loadWebTranslations].forEach((loader) => {
        loader().catch((err) => NE.toast(NE.t('loadFailed') + (err.message ? ': ' + err.message : ''), 'error'));
    });
})();
