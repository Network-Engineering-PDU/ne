/* Turns the PDU's update status into one summary line.
 *
 * The API reports two independent things:
 *  - ota_status / download_progress: the online (OTA) channel
 *  - update_phase / update_busy / active_update_source: the installer session
 *    used by uploads from this UI and by USB updates (idle, staging,
 *    pending_confirm, installing)
 * Looking at only ota_status shows "idle" during an upload or an install.
 */
(function (root) {
    const OTA_ACTIVE = ['checking', 'downloading', 'verifying', 'installing', 'pending_reboot'];

    /* Returns {key, kind, progress, active, params}. `key` selects the text,
       `kind` is a badge colour (ok | warning | error | info | ''), `progress` is
       0-100 or null, `active` is true while something is running (poll faster). */
    function summarize(st) {
        st = st || {};
        const ota = st.ota_status || 'idle';
        const phase = st.update_phase || 'idle';
        const source = st.active_update_source || '';
        const percent = Math.max(0, Math.min(100, Number(st.download_progress) || 0));

        if (ota === 'failed' && phase === 'idle') {
            return {key: 'failed', kind: 'error', progress: null, active: false, params: {error: st.last_error || ''}};
        }
        // An online download also reports the installer phase as 'staging'; show the download
        if (ota === 'downloading') {
            return {key: 'downloading', kind: 'info', progress: percent, active: true, params: {percent: percent}};
        }
        if (phase === 'staging') {
            return {key: 'staging', kind: 'info', progress: null, active: true, params: {source: source}};
        }
        if (phase === 'installing' || ota === 'installing' || (st.update_busy && phase !== 'pending_confirm')) {
            return {key: 'installing', kind: 'warning', progress: null, active: true, params: {source: source}};
        }
        if (ota === 'verifying') {
            return {key: 'verifying', kind: 'info', progress: null, active: true, params: {}};
        }
        if (ota === 'pending_reboot') {
            return {key: 'pendingReboot', kind: 'warning', progress: null, active: true, params: {}};
        }
        if (phase === 'pending_confirm' || ota === 'pending_confirm' || st.is_pending) {
            return {key: 'pendingConfirm', kind: 'warning', progress: null, active: true, params: {source: source}};
        }
        if (ota === 'checking') {
            return {key: 'checking', kind: 'info', progress: null, active: true, params: {}};
        }
        if (ota === 'failed') {
            return {key: 'failed', kind: 'error', progress: null, active: false, params: {error: st.last_error || ''}};
        }
        return {key: 'idle', kind: '', progress: null, active: false, params: {}};
    }

    const api = {summarize: summarize, OTA_ACTIVE: OTA_ACTIVE};
    if (typeof module !== 'undefined' && module.exports) { module.exports = api; }
    root.UpdateStatus = api;
})(typeof window !== 'undefined' ? window : globalThis);
