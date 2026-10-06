# Network Engineering 

## Init App and Run the server
To run the initial configurations, migrations and run server, execute the following command:
```
python manage.py ne_init
```
This will make all the initial config to be used by the web application.

## Web UI structure

Pages share one shell (`templates/base.html`: sidebar, alarm badge, PDU
connection banner) and one stylesheet, `static/css/app.css` (design tokens,
`.ne-*` components, light/dark). The older `styles.css` is only kept for markup
that has not been migrated yet (Inputs, Sensors, Users and the Coms network
form).

The redesigned pages (Dashboard, Alarms, Outlets, Settings and the Bluetooth /
NTP cards on Coms) are rendered by the browser from the PDU API:

- `static/js/app/ne.js` is the shared helper: `NE.api()`, toasts, confirmation
  dialogs and polling.
- The browser never talks to the PDU API directly. `/pdu/<path>` (see
  `app/pdu_proxy.py`) requires a logged-in session, forwards only the method +
  path pairs listed in `ALLOWED`, and needs the `X-Requested-With:
  XMLHttpRequest` header on writes because CSRF middleware is disabled in this
  project. To use a new PDU endpoint from a page, add it to `ALLOWED` and cover
  it in `app/tests/test_pdu_proxy.py`.
- Alarms are evaluated by the PDU API (`GET /alarms`); the touchscreen and this
  UI show the same list. Display settings (rotation, inactivity time, location
  fields, skip login) are edited through `GET/PUT /display-config`.
- Strings use Spanish message ids with English in `locale/en`. Recompile
  `django.mo` after editing the `.po` (no `msgfmt` needed: `polib` works).

Tests: `python manage.py test app`.

## Languages

Supported: Spanish (`es`, default), English, German (`de`), Chinese Simplified
(`zh-hans`) and Arabic (`ar`, right-to-left). Each language is one text file:
`locale/<lang>/LC_MESSAGES/django.po` (`zh_Hans` and `ar` folders for the last two).

To change a translation, edit the `msgstr` line in that file, then compile:
```
python -c "import polib; p=polib.pofile('locale/de/LC_MESSAGES/django.po'); p.save_as_mofile('locale/de/LC_MESSAGES/django.mo')"
```
(`msgfmt`/`compilemessages` from gettext works too.) Keep placeholders such as
`{field}`, `%(total)s` and `%(reason)s` unchanged; `python manage.py test app.tests.test_i18n`
fails if a placeholder is lost.

The German, Chinese and Arabic files are machine-drafted and need review by a
native speaker before release.

To add a new string, wrap it in `{% translate '...' %}` (or `_()` in Python) using
the Spanish text as the key, then add the English and other languages to the `.po` files.
