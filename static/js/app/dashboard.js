/* Dashboard: live overview from the PDU API. Each card loads independently so
   one failing endpoint does not blank the page. */
(function () {
    const $ = (id) => document.getElementById(id);
    const set = (id, value) => { const el = $(id); if (el) { el.textContent = value; } };

    async function alarms() {
        const data = await NE.api('GET', 'alarms');
        const active = data.alarms.filter((a) => !a.ack);
        set('dashAlarmCount', active.length);
        set('dashAlarmText', active.length ? NE.t('alarmsActive') : NE.t('noAlarms'));
        $('dashAlarmList').innerHTML = active.slice(0, 3).map((a) =>
            '<div class="ne-alarm ne-card ' + NE.escapeHtml(a.level) + '"><span class="ne-badge ' +
            NE.escapeHtml(a.level) + '">' + NE.escapeHtml(a.code) + '</span><span class="ne-alarm-desc">' +
            NE.escapeHtml(((NE.t('desc', {}) || {})[a.desc]) || a.desc) + '</span><span class="ne-alarm-meta">' + NE.escapeHtml(a.path) + '</span></div>'
        ).join('');
    }

    async function power() {
        const [sw, info] = await Promise.all([
            NE.api('GET', 'inputs/switches'), NE.api('GET', 'settings/pdu-info')]);
        const phases = {0: 1, 1: 2, 2: 3, 3: 3}[sw.sys_type] || 0;
        const branches = {0: 1, 1: 2}[sw.branch] || 0;
        const count = phases * branches;
        const readings = await Promise.all(
            Array.from({length: count}, (_, i) => NE.api('GET', 'inputs/' + i + '/data')));
        let watts = 0, energy = 0, maxCurrent = 0;
        readings.forEach((r) => {
            if (!r) { return; }
            watts += r.active_power; energy += r.energy; maxCurrent = Math.max(maxCurrent, r.current);
        });
        const rated = Number(info.rated_current) || 0;
        set('dashPower', NE.fmt(watts, 0));
        set('dashEnergy', NE.fmt(energy, 0));
        set('dashCurrent', NE.fmt(maxCurrent, 1));
        set('dashRated', rated ? NE.fmt(rated, 0) : '-');
        const pct = rated ? Math.min(100, (maxCurrent / rated) * 100) : 0;
        const bar = $('dashLoadBar');
        bar.style.width = pct + '%';
        bar.className = 'progress-bar ' + (pct > 100 ? 'bg-danger' : pct > 90 ? 'bg-warning' : 'bg-success');
    }

    async function outlets() {
        const [status, lic] = await Promise.all([
            NE.api('GET', 'outputs/switch-status'), NE.api('GET', 'settings/license')]);
        const values = Object.values(status || {});
        set('dashOutOn', values.filter(Boolean).length);
        set('dashOutTotal', values.length);
        const canControl = lic && (lic.type_id === 'B1' || lic.type_id === 'B2');
        set('dashOutLicense', canControl ? ' ' : NE.t('licenseNoControl'));
    }

    async function system() {
        const info = await NE.api('GET', 'settings/system-info');
        set('dashPn', info.product_pn); set('dashSn', info.product_sn);
        set('dashVer', info.sw_version); set('dashUptime', info.uptime);
        set('dashIp', info.ip || '-'); set('dashMac', info.lan_mac);
    }

    async function network() {
        const info = await NE.api('GET', 'network/info');
        const badge = $('dashNetBadge');
        badge.textContent = info.connected ? NE.t('connected') : NE.t('disconnected');
        badge.className = 'ne-badge ' + (info.connected ? 'ok' : 'warning');
    }

    async function refresh() {
        const results = await Promise.allSettled([alarms(), power(), outlets(), network()]);
        if (results.some((r) => r.status === 'fulfilled')) {
            set('dashUpdated', NE.t('updated') + ' ' + new Date().toLocaleTimeString());
        }
    }

    system().catch(() => {});
    NE.poll(refresh, 5000);
})();
