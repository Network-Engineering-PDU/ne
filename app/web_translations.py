"""Web interface translation file: download, checked upload and reset.

The web pages are translated with Django's catalogs
(locale/<lang>/LC_MESSAGES/django.po, compiled to .mo); their source texts
(msgid) are Spanish. Customers change them with a table: a CSV file, one row
per text, the source text as key, one column per language headed
"Name (code)", for example "Français (fr)".

An uploaded table is checked and stored in settings.WEB_TRANSLATIONS_FILE,
holding only what differs from the built-in catalogs plus the languages it
adds, so texts not changed by the customer still improve with firmware
updates. compile() turns it into .mo files in
settings.WEB_TRANSLATIONS_LOCALE, which settings.LOCALE_PATHS lists first:
Django uses those texts instead of the built-in ones. A language the table
adds gets a full catalog, English where it has no text. WebTranslationsMiddleware
reloads Django's catalogs and language list when the file changes.
"""
import csv
import io
import logging
import os
import re
import shutil
import struct
import threading

from django.conf import settings
from django.utils.translation import to_locale

logger = logging.getLogger(__name__)

MAX_LANGUAGES = 16
MAX_TEXT_LENGTH = 4000
MAX_FILE_BYTES = 2 * 1024 * 1024

CODE = re.compile(r"^[a-z]{2,3}(?:-[a-z0-9]{2,8})?$")
TITLE_CODE = re.compile(r"\(\s*([A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})?)\s*\)\s*$")
# Column titles without a code: the customer workbook's and plain names.
TITLE_ALIASES = {
    "english": "en", "inglés": "en",
    "spanish": "es", "español": "es", "espanol": "es",
    "german": "de", "deutsch": "de", "alemán": "de",
    "chinese": "zh-hans", "chinese (simplified)": "zh-hans", "中文": "zh-hans",
    "中文 (简体)": "zh-hans", "简体中文": "zh-hans",
    "arabic": "ar", "العربية": "ar",
}
KEY_TITLE = "Original text (key)"
KEY_TITLES = ("original text (key)", "original text (spanish, key)", "original text", "key", "msgid")
ID_TITLES = ("id", "text_id", "text id")
PAGE_TITLES = ("page", "página", "pagina")
NOTES_TITLE = "Must keep unchanged"

NATIVE_NAMES = {
    "es": "Español", "en": "English", "de": "Deutsch", "zh-hans": "中文 (简体)", "ar": "العربية",
}
RTL_CODES = ("ar", "fa", "ur", "ps", "ckb", "sd", "ug", "he", "iw", "yi", "dv")

# Values Django puts in a text: %(name)s in Python code, {name} in scripts.
PLACEHOLDER = re.compile(r"%\(\w+\)[sdif]|%[sdif]|\{\w*\}")

_lock = threading.RLock()
_loaded_state = None
_builtin_cache = {}


class TranslationFileError(ValueError):
    """The upload can't be used at all. code names the problem for the UI."""

    def __init__(self, code, detail=""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _custom_file():
    return settings.WEB_TRANSLATIONS_FILE


def _custom_locale():
    return settings.WEB_TRANSLATIONS_LOCALE


def _builtin_locale():
    return os.path.join(settings.BASE_DIR, "locale")


def builtin_languages():
    """[(code, name)] of the firmware's languages, in settings order."""
    return [(code, NATIVE_NAMES.get(code, code)) for code in settings.BUILTIN_LANGUAGE_CODES]


def is_rtl(code):
    return code.split("-")[0] in RTL_CODES


# ---- Catalogs -----------------------------------------------------------------

_ESCAPES = {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}


def _unquote(text):
    """The text of a quoted .po string (without its quotes)."""
    return re.sub(r"\\(.)", lambda m: _ESCAPES.get(m.group(1), m.group(1)), text)


def _po_entries(path):
    """[(msgid, msgstr, references)] of a .po file, header and fuzzy
    entries left out."""
    entries = []
    msgid = msgstr = None
    section = None
    refs = []
    fuzzy = False

    def flush():
        if msgid and not fuzzy:
            entries.append((msgid, msgstr or "", refs))

    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            if line.startswith("#:"):
                if section == "msgstr":
                    flush()
                    msgid = msgstr = section = None
                    refs, fuzzy = [], False
                refs = refs + line[2:].split()
            elif line.startswith("#,"):
                if section == "msgstr":
                    flush()
                    msgid = msgstr = section = None
                    refs, fuzzy = [], False
                fuzzy = "fuzzy" in line
            elif line.startswith("#"):
                continue
            elif line.startswith("msgid "):
                if section == "msgstr":
                    # An entry without comments follows the previous one
                    flush()
                    refs, fuzzy = [], False
                msgid, msgstr, section = _unquote(line[6:].strip()[1:-1]), None, "msgid"
            elif line.startswith("msgstr "):
                msgstr, section = _unquote(line[7:].strip()[1:-1]), "msgstr"
            elif line.startswith('"'):
                part = _unquote(line[1:-1])
                if section == "msgid":
                    msgid += part
                elif section == "msgstr":
                    msgstr += part
        if section == "msgstr":
            flush()
    return entries


def _po_header(path):
    """The header (msgstr of msgid "") of a .po file."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    match = re.search(r'^msgid ""\s*\nmsgstr ((?:"[^\n]*"\s*\n)+)', text, re.M)
    if not match:
        return ""
    return "".join(_unquote(part) for part in re.findall(r'"(.*)"', match.group(1)))


def _po_path(code):
    return os.path.join(_builtin_locale(), to_locale(code), "LC_MESSAGES", "django.po")


def builtin():
    """The firmware's texts: {"order": [msgid], "pages": {msgid: page},
    "texts": {code: {msgid: text}}, "headers": {code: header}}. Spanish
    texts default to the source text, which is Spanish."""
    paths = {code: _po_path(code) for code, _ in builtin_languages()}
    stamp = tuple((p, os.path.getmtime(p)) for p in paths.values() if os.path.exists(p))
    if _builtin_cache.get("stamp") == stamp:
        return _builtin_cache["data"]
    order, pages, texts, headers = [], {}, {}, {}
    for code, path in paths.items():
        texts[code] = {}
        if not os.path.exists(path):
            continue
        headers[code] = _po_header(path)
        for msgid, msgstr, refs in _po_entries(path):
            if msgid not in pages:
                order.append(msgid)
                pages[msgid] = _page(refs)
            if msgstr:
                texts[code][msgid] = msgstr
    for msgid in order:
        texts.setdefault("es", {}).setdefault(msgid, msgid)
    data = {"order": order, "pages": pages, "texts": texts, "headers": headers}
    _builtin_cache.update(stamp=stamp, data=data)
    return data


def _page(refs):
    names = []
    for ref in refs:
        name = os.path.splitext(os.path.basename(ref.split(":")[0]))[0]
        if name and name not in names:
            names.append(name)
    return ", ".join(names)


# ---- Checks -------------------------------------------------------------------

def text_problem(source, text):
    """Why a translation of source can't be used: (code, detail), or None."""
    if len(text) > MAX_TEXT_LENGTH:
        return ("too_long", str(MAX_TEXT_LENGTH))
    if any(c != "\n" and (ord(c) < 0x20 or 0x7F <= ord(c) < 0xA0) for c in text):
        return ("control_chars", "")
    expected = sorted(PLACEHOLDER.findall(source))
    if sorted(PLACEHOLDER.findall(text)) != expected:
        return ("placeholders", " ".join(dict.fromkeys(expected)))
    # A text Python fills in (% placeholders) can't have other '%' signs
    if "%" in "".join(expected) and text.count("%") != source.count("%"):
        return ("placeholders", " ".join(dict.fromkeys(expected)))
    return None


def must_keep(source):
    found = list(dict.fromkeys(PLACEHOLDER.findall(source)))
    notes = []
    if found:
        notes.append("Placeholders: " + "  ".join(found))
    if "\n" in source:
        notes.append("Line breaks: keep them (Alt+Enter in Excel)")
    return "\n".join(notes)


# ---- Tables -------------------------------------------------------------------

def _decode(data):
    if len(data) > MAX_FILE_BYTES:
        raise TranslationFileError("too_large", str(MAX_FILE_BYTES))
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as ex:
        raise TranslationFileError("not_utf8") from ex
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _separator(text):
    header, quoted = [], False
    for char in text:
        if char == '"':
            quoted = not quoted
        elif char == "\n" and not quoted:
            break
        elif not quoted:
            header.append(char)
    counts = {sep: header.count(sep) for sep in (",", ";", "\t")}
    if counts[";"] > counts[","] and counts[";"] >= counts["\t"]:
        return ";"
    return "\t" if counts["\t"] > counts[","] else ","


def _column_title(title):
    title = title.strip()
    match = TITLE_CODE.search(title)
    if match:
        code = match.group(1).lower()
        name = title[:match.start()].strip()
        return (code, name) if CODE.match(code) else None
    alias = TITLE_ALIASES.get(title.lower())
    return (alias, NATIVE_NAMES[alias]) if alias else None


def parse_table(data):
    text = _decode(data)
    rows = list(csv.reader(io.StringIO(text, newline=""), delimiter=_separator(text)))
    if not rows:
        raise TranslationFileError("empty")
    table = {"languages": [], "columns": {}, "key": None, "id": None, "rows": [], "ignored": []}
    for index, title in enumerate(rows[0]):
        lowered = title.strip().lower()
        if lowered in KEY_TITLES and table["key"] is None:
            table["key"] = index
            continue
        if lowered in ID_TITLES and table["id"] is None:
            table["id"] = index
            continue
        if lowered in PAGE_TITLES:
            continue
        language = _column_title(title)
        if language is None or language[0] in table["columns"]:
            if title.strip() and title.strip() != NOTES_TITLE:
                table["ignored"].append(title.strip())
            continue
        table["columns"][language[0]] = index
        table["languages"].append(language)
    if table["key"] is None:
        raise TranslationFileError("no_key")
    for number, cells in enumerate(rows[1:], start=2):
        if any(cell.strip() for cell in cells):
            table["rows"].append((number, cells))
    return table


def _cell(cells, index):
    return cells[index] if index is not None and index < len(cells) else ""


def _read_custom(path=None):
    try:
        with open(path or _custom_file(), "rb") as f:
            return parse_table(f.read())
    except (OSError, TranslationFileError):
        return None


def _custom_texts(table):
    """{code: {msgid: text}} of a stored table."""
    texts = {code: {} for code, _ in table["languages"]}
    for _, cells in table["rows"]:
        key = _cell(cells, table["key"])
        for code, index in table["columns"].items():
            value = _cell(cells, index)
            if key and value:
                texts[code].setdefault(key, value)
    return texts


def languages(path=None):
    """[(code, name)] the web interface offers: built-in, then the file's."""
    result = builtin_languages()
    custom = _read_custom(path)
    for code, name in (custom["languages"] if custom else []):
        if code not in dict(result) and len(result) < MAX_LANGUAGES:
            result.append((code, name or code))
    return result


def info(path=None):
    path = path or _custom_file()
    try:
        modified = int(os.stat(path).st_mtime)
    except OSError:
        modified = None
    return {
        "custom": modified is not None,
        "modified": modified,
        "languages": [{"code": code, "name": name} for code, name in languages(path)],
    }


def export_csv(path=None):
    """The table in use as UTF-8 CSV with a byte order mark (Excel)."""
    base = builtin()
    custom = _read_custom(path)
    langs = builtin_languages()
    for code, name in (custom["languages"] if custom else []):
        if code not in dict(langs) and len(langs) < MAX_LANGUAGES:
            langs.append((code, name or code))
    changes = _custom_texts(custom) if custom else {}

    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\r\n")
    writer.writerow(["ID", "Page", KEY_TITLE] + [f"{name} ({code})" for code, name in langs] + [NOTES_TITLE])
    for number, msgid in enumerate(base["order"], start=1):
        texts = [changes.get(code, {}).get(msgid) or base["texts"].get(code, {}).get(msgid, "")
                 for code, _ in langs]
        writer.writerow([f"W{number:03d}", base["pages"][msgid], msgid] + texts + [must_keep(msgid)])
    return "﻿" + out.getvalue()


def import_csv(data):
    """Checks an uploaded table. Returns (csv_text, report): csv_text holds
    the accepted texts that differ from the built-in ones (None if nothing
    does). Raises TranslationFileError if the table can't be used."""
    base = builtin()
    upload = parse_table(data)
    ids = {msgid: f"W{n:03d}" for n, msgid in enumerate(base["order"], start=1)}
    by_stripped = {msgid.strip(): msgid for msgid in base["order"]}

    builtin_codes = [code for code, _ in builtin_languages()]
    langs = builtin_languages()
    for code, name in upload["languages"]:
        if code in builtin_codes:
            continue
        if len(langs) >= MAX_LANGUAGES:
            raise TranslationFileError("too_many_languages", str(MAX_LANGUAGES))
        if not name or len(name) > 63 or "\n" in name:
            name = code
        langs.append((code, name))
    new_codes = [code for code, _ in langs if code not in builtin_codes]
    uploaded_codes = [code for code, _ in langs if code in upload["columns"]]

    report = {"languages": uploaded_codes, "new_languages": new_codes, "checked": 0,
              "accepted": 0, "changed": 0, "rejected": [], "ignored_columns": upload["ignored"]}
    changes = {}               # msgid -> {code: text}
    for number, cells in upload["rows"]:
        key = _cell(cells, upload["key"])
        msgid = key if key in base["pages"] else by_stripped.get(key.strip())
        if msgid is None:
            if any(_cell(cells, upload["columns"][c]) for c in uploaded_codes):
                report["rejected"].append({"row": number, "id": _cell(cells, upload["id"]).strip(),
                                           "language": "", "reason": "unknown_text",
                                           "detail": key[:80]})
            continue
        for code in uploaded_codes:
            text = _cell(cells, upload["columns"][code])
            if not text:
                continue
            report["checked"] += 1
            problem = text_problem(msgid, text)
            if problem:
                report["rejected"].append({"row": number, "id": ids[msgid], "language": code,
                                           "reason": problem[0], "detail": problem[1]})
                continue
            report["accepted"] += 1
            if text != base["texts"].get(code, {}).get(msgid, ""):
                changes.setdefault(msgid, {})[code] = text
    report["changed"] = sum(len(texts) for texts in changes.values())

    stored = [lang for lang in langs
              if lang[0] in new_codes or any(lang[0] in t for t in changes.values())]
    if not stored:
        return None, report
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["ID", "Page", KEY_TITLE] + [f"{name} ({code})" for code, name in stored])
    for msgid in base["order"]:
        if msgid in changes:
            writer.writerow([ids[msgid], base["pages"][msgid], msgid] +
                            [changes[msgid].get(code, "") for code, _ in stored])
    return out.getvalue(), report


# ---- Applying -----------------------------------------------------------------

def _write_mo(path, catalog, header):
    """Writes a GNU .mo file (see CPython's Tools/i18n/msgfmt.py)."""
    entries = sorted([("", header)] + list(catalog.items()))
    ids = strs = b""
    offsets = []
    for msgid, msgstr in entries:
        key, value = msgid.encode("utf-8"), msgstr.encode("utf-8")
        offsets.append((len(ids), len(key), len(strs), len(value)))
        ids += key + b"\0"
        strs += value + b"\0"
    keystart = 7 * 4 + 16 * len(entries)
    valuestart = keystart + len(ids)
    koffsets, voffsets = [], []
    for o1, l1, o2, l2 in offsets:
        koffsets += [l1, o1 + keystart]
        voffsets += [l2, o2 + valuestart]
    output = struct.pack("Iiiiiii", 0x950412de, 0, len(entries), 7 * 4,
                         7 * 4 + len(entries) * 8, 0, 0)
    output += struct.pack(f"{len(koffsets)}i", *koffsets)
    output += struct.pack(f"{len(voffsets)}i", *voffsets)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(output + ids + strs)


def compile_catalogs(path=None, locale_dir=None):
    """Writes the .mo files of the custom table, removing old ones."""
    locale_dir = locale_dir or _custom_locale()
    custom = _read_custom(path)
    staging = locale_dir + ".new"
    shutil.rmtree(staging, ignore_errors=True)
    if custom:
        base = builtin()
        texts = _custom_texts(custom)
        default_header = "Content-Type: text/plain; charset=UTF-8\nPlural-Forms: nplurals=2; plural=(n != 1);\n"
        for code, _ in custom["languages"]:
            if code in base["texts"]:
                catalog = dict(texts.get(code, {}))
                header = base["headers"].get(code, default_header)
            else:
                # A new language: English where it has no text yet
                catalog = dict(base["texts"].get("en", {}))
                catalog.update(texts.get(code, {}))
                header = default_header
            if catalog:
                _write_mo(os.path.join(staging, to_locale(code), "LC_MESSAGES", "django.mo"),
                          catalog, header)
    shutil.rmtree(locale_dir, ignore_errors=True)
    if os.path.isdir(staging):
        os.rename(staging, locale_dir)


def apply(path=None):
    """Makes Django use the current table: language list, right-to-left
    languages and catalogs."""
    from django.utils.translation import trans_real

    langs = languages(path)
    names = dict(settings.BUILTIN_LANGUAGES)
    settings.LANGUAGES = tuple((code, names.get(code, name)) for code, name in langs)
    settings.RTL_LANGUAGES = tuple(code for code, _ in langs if is_rtl(code))
    trans_real._translations = {}
    trans_real._default = None
    trans_real.check_for_language.cache_clear()
    trans_real.get_languages.cache_clear()
    trans_real.get_supported_language_variant.cache_clear()


def native_name(code):
    """The language's name as it writes it (the file's for added ones)."""
    return NATIVE_NAMES.get(code) or str(dict(settings.LANGUAGES).get(code, code))


def _file_state(path):
    try:
        st = os.stat(path)
        return (st.st_ino, st.st_size, st.st_mtime_ns)
    except OSError:
        return None


def refresh(force=False):
    """Compiles and applies the table if it changed since the last time (or
    always with force). Never raises: the site keeps its texts on errors."""
    global _loaded_state
    path = _custom_file()
    state = _file_state(path)
    if not force and state == _loaded_state:
        return
    with _lock:
        if not force and state == _loaded_state:
            return
        try:
            compile_catalogs(path)
            apply(path)
            _loaded_state = state
        except Exception:      # pylint: disable=broad-except
            logger.exception("Could not apply the web translation file")
            _loaded_state = state


def save(text):
    """Replaces the custom table in one step (None removes it) and applies it."""
    path = _custom_file()
    with _lock:
        if text is None:
            try:
                os.unlink(path)
            except FileNotFoundError:
                pass
        else:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            temporary = path + ".tmp"
            with open(temporary, "w", encoding="utf-8", newline="") as f:
                f.write(text)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporary, path)
        refresh(force=True)


class WebTranslationsMiddleware:
    """Picks up a changed translation file before the language is chosen
    (place it before LocaleMiddleware)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        refresh()
        return self.get_response(request)
