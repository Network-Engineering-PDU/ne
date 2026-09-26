/* Shared helpers for the redesigned pages: PDU API access, toasts, confirm. */
const NE = (function () {
    const I18N = window.NE_I18N || {};

    function t(key, fallback) {
        return I18N[key] !== undefined ? I18N[key] : (fallback !== undefined ? fallback : key);
    }

    function escapeHtml(value) {
        return String(value === null || value === undefined ? '' : value)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    /* Calls the PDU API through the authenticated proxy (/pdu/<path>).
       Resolves with the parsed JSON (or null); rejects with an Error whose
       .status is the HTTP status. */
    async function api(method, path, body) {
        const options = {
            method: method,
            headers: {'X-Requested-With': 'XMLHttpRequest'},
            credentials: 'same-origin',
        };
        if (body !== undefined) {
            options.headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(body);
        }
        let response;
        try {
            response = await fetch('/pdu/' + path, options);
        } catch (err) {
            const e = new Error(t('apiUnreachable', 'PDU API unreachable'));
            e.status = 0;
            throw e;
        }
        if (response.status === 401) {
            window.location.href = '/login/';
            throw new Error('Unauthorized');
        }
        const text = await response.text();
        let data = null;
        try { data = text ? JSON.parse(text) : null; } catch (err) { data = null; }
        if (!response.ok) {
            const detail = data && (data.detail || data.message);
            const e = new Error(typeof detail === 'string' ? detail : 'HTTP ' + response.status);
            e.status = response.status;
            throw e;
        }
        return data;
    }

    function toast(message, kind) {
        let box = document.getElementById('neToasts');
        if (!box) {
            box = document.createElement('div');
            box.id = 'neToasts';
            box.className = 'ne-toasts';
            box.setAttribute('role', 'status');
            box.setAttribute('aria-live', 'polite');
            document.body.appendChild(box);
        }
        const el = document.createElement('div');
        el.className = 'ne-toast ' + (kind || '');
        el.textContent = message;
        box.appendChild(el);
        setTimeout(() => el.remove(), kind === 'error' ? 6000 : 3000);
    }

    /* Promise based confirmation dialog. */
    function confirmDialog(title, message, options) {
        options = options || {};
        return new Promise((resolve) => {
            const dialog = document.createElement('dialog');
            dialog.className = 'ne-dialog';
            dialog.innerHTML =
                '<h2>' + escapeHtml(title) + '</h2><p class="ne-muted mb-0">' + escapeHtml(message) + '</p>' +
                '<div class="ne-actions"><button type="button" class="ne-btn" data-r="0">' +
                escapeHtml(t('cancel', 'Cancel')) + '</button><button type="button" class="ne-btn ' +
                (options.danger ? 'danger' : 'primary') + '" data-r="1">' +
                escapeHtml(options.confirmLabel || t('confirm', 'Confirm')) + '</button></div>';
            document.body.appendChild(dialog);
            const done = (value) => { dialog.close(); dialog.remove(); resolve(value); };
            dialog.addEventListener('click', (ev) => {
                const r = ev.target.getAttribute && ev.target.getAttribute('data-r');
                if (r !== null && r !== undefined) { done(r === '1'); }
            });
            dialog.addEventListener('cancel', (ev) => { ev.preventDefault(); done(false); });
            dialog.showModal();
        });
    }

    function poll(fn, intervalMs) {
        let stopped = false;
        let timer = null;
        async function tick() {
            if (stopped) { return; }
            if (!document.hidden) {
                try { await fn(); } catch (err) { /* handled by fn */ }
            }
            timer = setTimeout(tick, intervalMs);
        }
        tick();
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && !stopped) { clearTimeout(timer); tick(); }
        });
        return () => { stopped = true; clearTimeout(timer); };
    }

    function fmt(value, digits) {
        const n = Number(value);
        return Number.isFinite(n) ? n.toFixed(digits === undefined ? 1 : digits) : '-';
    }

    function formatTime(epochSeconds) {
        if (!epochSeconds) { return ''; }
        return new Date(epochSeconds * 1000).toLocaleString();
    }

    return {t, api, toast, confirm: confirmDialog, poll, fmt, escapeHtml, formatTime};
})();

/* Shell: mobile drawer, alarm badge and PDU API status. Runs on every page
   that has the app shell. */
document.addEventListener('DOMContentLoaded', function () {
    const shell = document.querySelector('.ne-shell');
    if (!shell) { return; }

    const toggle = document.getElementById('neMenuToggle');
    const scrim = document.getElementById('neScrim');
    const setOpen = (open) => {
        shell.classList.toggle('open', open);
        if (toggle) { toggle.setAttribute('aria-expanded', open ? 'true' : 'false'); }
    };
    if (toggle) { toggle.addEventListener('click', () => setOpen(!shell.classList.contains('open'))); }
    if (scrim) { scrim.addEventListener('click', () => setOpen(false)); }
    document.addEventListener('keydown', (ev) => { if (ev.key === 'Escape') { setOpen(false); } });

    const badges = document.querySelectorAll('[data-alarm-count]');
    const apiBar = document.getElementById('neApiBar');
    const showCount = (unacked) => {
        badges.forEach((el) => { el.textContent = unacked > 99 ? '99+' : unacked; el.hidden = unacked === 0; });
    };
    // Pages that change alarms (acknowledge) announce it so the badge updates at once
    document.addEventListener('ne:alarms', (ev) => showCount(ev.detail.unacked));
    NE.poll(async function () {
        try {
            const data = await NE.api('GET', 'alarms');
            showCount(data ? data.unacked : 0);
            if (apiBar) { apiBar.classList.remove('show'); }
        } catch (err) {
            if (apiBar) { apiBar.classList.add('show'); }
        }
    }, 5000);
});
