(function () {
    const list = document.getElementById('alarmList');
    const ackedList = document.getElementById('ackedList');
    const ackedTitle = document.getElementById('ackedTitle');
    const empty = document.getElementById('alarmEmpty');
    const btnAckAll = document.getElementById('btnAckAll');
    let lastKey = '';

    function row(alarm) {
        const desc = (NE.t('desc', {}) || {})[alarm.desc] || alarm.desc;
        const levelText = alarm.level === 'error' ? NE.t('levelError') : NE.t('levelWarning');
        const action = alarm.ack ? '' :
            '<button type="button" class="ne-btn sm" data-ack="' + NE.escapeHtml(alarm.id) + '">' +
            NE.escapeHtml(NE.t('ack')) + '</button>';
        return '<div class="ne-card ne-alarm ' + NE.escapeHtml(alarm.level) + (alarm.ack ? ' acked' : '') + '">' +
            '<span class="ne-badge ' + NE.escapeHtml(alarm.level) + '">' + NE.escapeHtml(levelText) + '</span>' +
            '<span class="ne-alarm-desc">' + NE.escapeHtml(desc) + '</span>' + action +
            '<span class="ne-alarm-meta">' + NE.escapeHtml(alarm.code) + ' · ' + NE.escapeHtml(alarm.path) +
            ' · ' + NE.escapeHtml(NE.t('since')) + ' ' + NE.escapeHtml(NE.formatTime(alarm.first_seen)) + '</span></div>';
    }

    function render(data) {
        document.dispatchEvent(new CustomEvent('ne:alarms', {detail: data}));
        const key = JSON.stringify(data.alarms);
        if (key === lastKey) { return; }   // avoid redrawing (and losing focus) when nothing changed
        lastKey = key;
        const active = data.alarms.filter((a) => !a.ack);
        const acked = data.alarms.filter((a) => a.ack);
        list.innerHTML = active.map(row).join('');
        ackedList.innerHTML = acked.map(row).join('');
        ackedTitle.hidden = acked.length === 0;
        empty.hidden = active.length !== 0;
        btnAckAll.disabled = active.length === 0;
    }

    async function refresh() {
        try {
            render(await NE.api('GET', 'alarms'));
        } catch (err) {
            NE.toast(NE.t('loadFailed'), 'error');
        }
    }

    document.addEventListener('click', async (ev) => {
        const btn = ev.target.closest('[data-ack]');
        if (!btn) { return; }
        btn.disabled = true;
        try {
            render(await NE.api('POST', 'alarms/ack', {id: btn.getAttribute('data-ack')}));
        } catch (err) {
            NE.toast(NE.t('ackFailed'), 'error');
            btn.disabled = false;
        }
    });

    btnAckAll.addEventListener('click', async () => {
        btnAckAll.disabled = true;
        try {
            render(await NE.api('POST', 'alarms/ack-all'));
        } catch (err) {
            NE.toast(NE.t('ackFailed'), 'error');
            btnAckAll.disabled = false;
        }
    });

    NE.poll(refresh, 3000);
})();
