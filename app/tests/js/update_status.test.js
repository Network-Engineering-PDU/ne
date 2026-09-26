const assert = require('assert');
const {summarize} = require('../../../static/js/app/update_status.js');

const cases = [
  // [description, status, expected key, expected active]
  ['nothing going on', {ota_status: 'idle', update_phase: 'idle'}, 'idle', false],
  ['empty / missing', undefined, 'idle', false],
  ['upload being staged', {ota_status: 'idle', update_phase: 'staging', active_update_source: 'web'}, 'staging', true],
  ['upload waiting for confirmation', {ota_status: 'idle', update_phase: 'pending_confirm', is_pending: true}, 'pendingConfirm', true],
  ['pending flag only', {ota_status: 'idle', update_phase: 'idle', is_pending: true}, 'pendingConfirm', true],
  ['installer running for an upload', {ota_status: 'idle', update_phase: 'installing', active_update_source: 'web', update_busy: true}, 'installing', true],
  ['USB installer busy without a session phase', {ota_status: 'idle', update_phase: 'idle', update_busy: true}, 'installing', true],
  ['OTA downloading (installer phase is staging too)', {ota_status: 'downloading', download_progress: 42, update_phase: 'staging'}, 'downloading', true],
  ['OTA downloading, no session', {ota_status: 'downloading', download_progress: 42, update_phase: 'idle'}, 'downloading', true],
  ['OTA verifying', {ota_status: 'verifying'}, 'verifying', true],
  ['OTA installing', {ota_status: 'installing', update_phase: 'installing'}, 'installing', true],
  ['reboot needed', {ota_status: 'pending_reboot'}, 'pendingReboot', true],
  ['checking', {ota_status: 'checking'}, 'checking', true],
  ['failed', {ota_status: 'failed', last_error: 'bad signature'}, 'failed', false],
];
for (const [name, status, key, active] of cases) {
  const s = summarize(status);
  assert.strictEqual(s.key, key, name + ': key ' + s.key);
  assert.strictEqual(s.active, active, name + ': active');
}

// Progress is only reported for a download and is clamped to 0-100.
assert.strictEqual(summarize({ota_status: 'downloading', download_progress: 42}).progress, 42);
assert.strictEqual(summarize({ota_status: 'downloading', download_progress: 250}).progress, 100);
assert.strictEqual(summarize({ota_status: 'downloading', download_progress: -3}).progress, 0);
assert.strictEqual(summarize({ota_status: 'downloading', download_progress: 'x'}).progress, 0);
assert.strictEqual(summarize({ota_status: 'idle'}).progress, null);

// The error text and update source are passed through for the message.
assert.strictEqual(summarize({ota_status: 'failed', last_error: 'bad signature'}).params.error, 'bad signature');
assert.strictEqual(summarize({update_phase: 'installing', active_update_source: 'usb'}).params.source, 'usb');

// The regression: during an upload or install the old code showed "idle".
for (const st of [{ota_status: 'idle', update_phase: 'staging'}, {ota_status: 'idle', update_phase: 'installing'}]) {
  assert.notStrictEqual(summarize(st).key, 'idle');
}
console.log('ok', cases.length, 'cases');
