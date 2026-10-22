"""Every sentence a student is shown is in both catalogues, byte for byte.

**The defect this is written against, found by frontend while building the
verification that did not exist:** three shipped sentences sat in
`locale/en/LC_MESSAGES/django.po` as **empty or truncated** message ids —

    msgctxt "sell.isbn.checksum"
    msgid ""

    msgctxt "sell.photos.unsupported"
    msgid ""

    msgctxt "sell.photos.too_big"
    msgid "That photo is %(mb)s MB. The most BookHop takes is 8 MB — "

— while the real text lived in `web/views.py` and `web/forms.py` and was
shown to students. **The deny-list read the catalogue, found an empty string,
and reported green.** `tests/unit/test_forbidden_copy.py`'s extractor pulls
`msgid`/`msgstr` out of the `.po` files, so for those three sentences it was
scanning nothing at all — a banned word in any of them would have shipped
past a clean suite.

That is this project's defect class landing in the copy control: **a guard
whose fixture cannot produce the condition**, except here the corpus itself
was missing. A third of the sell flow's error copy was invisible to the one
check that reads copy.

**The fix is asserted here independently of the fix.** The strings are
extracted from the **source** — `pgettext_lazy` calls in `apps/**` and
`web/**`, `{% translate %}` and `{% blocktranslate %}` tags in
`templates/**` — and compared against both catalogues. Nothing here reads
the `.po` to decide what *should* be in the `.po`, which is the circularity
that let the gap exist.

Three properties, kept apart because they fail for different reasons:

1. **Present and non-empty.** Every context the code uses has a `msgid` in
   `locale/en`, and it is not the empty string.
2. **Byte-identical.** The `msgid` equals the literal the code passes —
   not merely non-empty, because `too_big` was non-empty and truncated at
   the em-dash, which is the shape an eye slides over.
3. **Both catalogues carry the same contexts**, so a Tamil string cannot
   exist for a sentence English does not have, and vice versa — and so the
   count the Tamil locale gate reasons about is the real one.
"""

import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
TEMPLATES = REPO / "templates"
LOCALE = REPO / "locale"
SOURCE_ROOTS = (REPO / "apps", REPO / "web")

#: `pgettext_lazy("context", "message")` and `pgettext(...)`, however the
#: module aliased it. The alias is matched rather than assumed: `web/forms.py`
#: imports it as `_p`, `apps/**` may not.
#: **Adjacent literals are joined**, because Python concatenates them and
#: gettext sees one string. QA's first draft read only the first fragment and
#: reported `consent.listing_publication.disclosure` as truncated — a
#: four-line literal in `web/views.py` that is correct, and whose catalogue
#: entry is correct. An extractor that cries wolf about correct copy is the
#: shape `CLAUDE.md` rule 13 names, so it is fixed rather than tolerated.
_PY_CALL = re.compile(
    r"\b(?:_p|pgettext|pgettext_lazy)\(\s*"
    r'"((?:[^"\\]|\\.)*)"\s*,\s*'
    r'((?:"(?:[^"\\]|\\.)*"\s*)+)',
    re.S,
)
_LITERAL = re.compile(r'"((?:[^"\\]|\\.)*)"')
#: `{% translate "text" context "key" %}` — Django's argument order puts the
#: message first and the context second, the opposite of the Python call.
_TAG = re.compile(
    r'{%\s*(?:translate|trans)\s+"((?:[^"\\]|\\.)*)"\s+context\s+"([^"]+)"\s*%}'
)
#: `{% blocktranslate context "key" ... %}body{% endblocktranslate %}`
_BLOCK = re.compile(
    r'{%\s*blocktranslate\s+context\s+"([^"]+)"[^%]*%}(.*?){%\s*endblocktranslate\s*%}',
    re.S,
)


def _unescape(literal):
    return literal.encode().decode("unicode_escape") if "\\" in literal else literal


#: `{context: [(plural text, where)]}` for blocktranslate blocks carrying
#: `{% plural %}`. Filled by `shipped_strings()`.
PLURALS = {}


def shipped_strings():
    """`{context: (text, where)}` for every student-facing string in the code.

    **The source of truth is the source.** A context appearing twice with the
    same text is fine — `sell.h1` is on two templates — and is deduplicated;
    appearing twice with *different* text is a finding in its own right,
    asserted below, because the catalogue can only hold one of them.
    """
    found = {}
    clashes = []

    def record(context, text, where):
        text = _unescape(text)
        if context in found and found[context][0] != text:
            clashes.append((context, found[context], (text, where)))
        found.setdefault(context, (text, where))

    for root in SOURCE_ROOTS:
        for path in sorted(root.rglob("*.py")):
            if "/migrations/" in path.as_posix() or "__pycache__" in path.as_posix():
                continue
            source = path.read_text(encoding="utf-8")
            for context, literals in _PY_CALL.findall(source):
                record(
                    context,
                    "".join(_LITERAL.findall(literals)),
                    path.relative_to(REPO).as_posix(),
                )

    for path in sorted(TEMPLATES.rglob("*.html")):
        source = path.read_text(encoding="utf-8")
        where = path.relative_to(REPO).as_posix()
        for message, context in _TAG.findall(source):
            record(context, message, where)
        for context, body in _BLOCK.findall(source):
            # `{{ email }}` in a blocktranslate body is `%(email)s` in the
            # catalogue — Django's own rewrite, not a mismatch. Normalised
            # here so the comparison is about the sentence and not about
            # which side of the template engine it was read from.
            text = re.sub(r"\{\{\s*([\w.]+)\s*\}\}", lambda m: f"%({m.group(1)})s", body)
            # `{% plural %}` splits a blocktranslate into `msgid` and
            # `msgid_plural`. The singular is what `msgid` holds; the plural
            # is a second entry and is checked by the plural sweep below.
            singular = re.split(r"\{%\s*plural\s*%\}", text)[0]
            record(context, " ".join(singular.split()), where)
            parts = re.split(r"\{%\s*plural\s*%\}", text)
            if len(parts) > 1:
                PLURALS.setdefault(context, []).append(
                    (" ".join(parts[1].split()), where)
                )

    return found, clashes


def catalogue(locale):
    """`{msgctxt: msgid}` from a `.po`, read as text.

    Deliberately not `polib` or Django's own loader: the question is what is
    **written in the file**, including an empty `msgid`, and a loader that
    falls back to the context or skips empties would hide exactly the defect
    this file exists for.
    """
    path = LOCALE / locale / "LC_MESSAGES" / "django.po"
    if not path.exists():
        return None
    entries = {}
    context = None
    for block in path.read_text(encoding="utf-8").split("\n\n"):
        context = None
        msgid_parts = []
        in_msgid = False
        for line in block.splitlines():
            if line.startswith("msgctxt "):
                context = line[len("msgctxt "):].strip().strip('"')
            elif line.startswith("msgid "):
                in_msgid = True
                msgid_parts.append(line[len("msgid "):].strip().strip('"'))
            elif line.startswith("msgstr"):
                in_msgid = False
            elif in_msgid and line.startswith('"'):
                msgid_parts.append(line.strip().strip('"'))
        if context is not None:
            entries[context] = _unescape("".join(msgid_parts))
    return entries


# --------------------------------------------------------------------------


def test_the_extractor_found_a_real_corpus():
    """**Rule 10's fourth disguise, first.** If the regexes stopped matching,
    every assertion below would pass over an empty set and this file would be
    the same kind of green the deny-list was."""
    found, _clashes = shipped_strings()
    assert len(found) >= 150, (
        f"the extractor found {len(found)} student-facing strings. S2 ships "
        "well over two hundred; this is the regexes having stopped matching, "
        "not the copy having shrunk."
    )
    assert any(where.endswith(".py") for _text, where in found.values()), (
        "no Python `pgettext` call was extracted, so the half of the copy "
        "that lives in views and forms — which is where all three empty "
        "msgids were — is unmeasured"
    )
    assert any(where.endswith(".html") for _text, where in found.values()), (
        "no template string was extracted"
    )


def test_no_context_carries_two_different_sentences():
    """A context is the catalogue's key, so two texts under one context means
    one of them can never be translated. Checked before the comparison, so a
    mismatch below is never really a clash here."""
    _found, clashes = shipped_strings()
    assert clashes == [], (
        "these contexts are used with more than one English text, so the "
        f"catalogue can only carry one of them: {clashes}"
    )


def test_every_shipped_sentence_is_in_the_english_catalogue_byte_for_byte():
    """**The regression for the three empty ids, derived from the source.**

    Present, non-empty, and equal. The third clause is the one that catches
    `sell.photos.too_big`, which was present and non-empty and stopped at
    the em-dash — and a non-empty check would have called it covered.
    """
    found, _clashes = shipped_strings()
    entries = catalogue("en")
    assert entries, "locale/en/LC_MESSAGES/django.po is missing"

    missing, empty, mismatched = [], [], []
    for context, (text, where) in sorted(found.items()):
        if context not in entries:
            missing.append(f"{context} ({where})")
        elif entries[context] == "":
            empty.append(f"{context} ({where}): {text!r}")
        elif entries[context] != text:
            mismatched.append(
                f"{context} ({where}):\n     code: {text!r}\n  catalogue: "
                f"{entries[context]!r}"
            )

    assert empty == [], (
        "these shipped sentences are EMPTY in the English catalogue, so the "
        "banned-vocabulary scan reads nothing for them and a warranting word "
        "in any of them would pass a green suite:\n" + "\n".join(empty)
    )
    assert mismatched == [], (
        "these catalogue entries are not the sentence the code passes. A "
        "truncated entry is the dangerous shape: it is non-empty, so a "
        "presence check calls it covered, and the part that is missing is "
        "the part nobody scanned:\n" + "\n\n".join(mismatched)
    )
    assert missing == [], (
        "these shipped sentences have no catalogue entry at all, so they are "
        "outside the deny-list's corpus entirely:\n" + "\n".join(missing)
    )


def test_the_tamil_catalogue_carries_the_same_contexts_as_the_english_one():
    """Both catalogues, as the fix claims. A context in one and not the other
    is a string that cannot be reviewed, counted or gated.

    This is **not** a check that the Tamil text is right — nobody has read
    it, `locale/ta/REVIEWED.toml` is deliberately empty, and
    `tests/a11y/test_s2_pages.py` asserts the locale stays closed. It is a
    check that the two files describe the same product, because the Tamil
    locale gate counts blocking-class msgids and a missing one is a string
    the gate cannot know about.
    """
    english = catalogue("en")
    tamil = catalogue("ta")
    assert tamil, "locale/ta/LC_MESSAGES/django.po is missing"

    only_en = sorted(set(english) - set(tamil))
    only_ta = sorted(set(tamil) - set(english))
    assert only_en == [], (
        "these contexts exist in English and not in Tamil, so the locale "
        "gate cannot count them and a native reviewer would never be shown "
        f"them: {only_en}"
    )
    assert only_ta == [], (
        "these contexts exist in Tamil and not in English, so there is "
        f"Tamil copy for a sentence the product does not ship: {only_ta}"
    )


def test_the_deny_list_actually_reads_what_the_code_ships():
    """**The control's reach, which is what the three empty ids broke.**

    `tests/unit/test_forbidden_copy.py` scans `templates/**` and
    `locale/en/**`. It does **not** read `.py` files, by design — the first
    draft that did reported a CSS class as banned copy. So every sentence
    written in `web/views.py` or `web/forms.py` reaches the deny-list
    **only through its catalogue entry**, and that is precisely why an empty
    `msgid` took three sentences out of scope silently.

    Asserted here as the standing property: every Python-authored string is
    in the file the deny-list reads, and the scan is therefore over the whole
    corpus rather than most of it.
    """
    from tests.unit.test_forbidden_copy import scanned_files, translatable_strings

    found, _clashes = shipped_strings()
    python_authored = {
        text for text, where in found.values() if where.endswith(".py")
    }
    assert python_authored, "no Python-authored copy was extracted"

    scanned = set()
    for _name, source in scanned_files():
        scanned.update(translatable_strings(source))

    unscanned = sorted(text for text in python_authored if text not in scanned)
    assert unscanned == [], (
        "these sentences are written in Python and never reach the "
        "banned-vocabulary scan, because the scan reads templates and the "
        "English catalogue and these are in neither. A banned word in any "
        "of them ships past a green suite — which is exactly what the three "
        f"empty msgids did:\n" + "\n".join(repr(t) for t in unscanned)
    )


def test_the_plural_half_of_every_blocktranslate_is_in_the_catalogue_too():
    """**The same gap, one grammatical form over.**

    `{% plural %}` makes a block two catalogue entries: `msgid` and
    `msgid_plural`. The singular is compared above. The plural is a separate
    string, shown to a student whenever the count is not one — which for
    *"The seller attached N photos"* is three times out of four — and an
    empty or truncated `msgid_plural` would take it out of the deny-list's
    corpus in exactly the way the three empty `msgid`s did.

    Read from the raw file rather than through the `msgctxt` map, because
    `msgid_plural` lives on its own line and the map above deliberately only
    collects `msgid`.
    """
    found, _clashes = shipped_strings()
    assert found and PLURALS, (
        "no blocktranslate with a `{% plural %}` was extracted, so this test "
        "is measuring nothing"
    )
    raw = (LOCALE / "en" / "LC_MESSAGES" / "django.po").read_text(encoding="utf-8")
    plural_ids = {
        _unescape(m) for m in re.findall(r'^msgid_plural\s+"(.*)"', raw, re.M)
    }

    missing = []
    for context, entries in sorted(PLURALS.items()):
        for text, where in entries:
            if text not in plural_ids:
                missing.append(f"{context} ({where}): {text!r}")
    assert missing == [], (
        "these plural forms are shipped and have no `msgid_plural` in the "
        "English catalogue, so the banned-vocabulary scan never reads "
        "them:\n" + "\n".join(missing)
    )
