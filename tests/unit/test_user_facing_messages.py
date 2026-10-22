"""No internal document reference reaches a student — REVIEW-S1 R9.

API-CONTRACT §2.2: `message` is *"already localised"* and L3 renders it as a
page. So it is **copy**, and copy that reads *"DATA-MODEL §2 allows
['SETTINGS_TOGGLE', 'SIGNUP_FORM', 'STAFF_RECORDED']"* tells a student nothing
they can act on while telling them something about our filing system.

Six of these shipped, and **the seventh arrived in the same pass that was
fixing the other six** — the enum validator added for rule 18 cited DATA-MODEL
in its message. That is the whole argument for a guard rather than a cleanup:
the next one will be added by someone correcting something else.

**The citation is not deleted, it is moved.** `ServiceError(message, **context)`
puts developer detail in `context`, which `error_payload` logs and never
renders. `tests/unit/test_consent.py` asserts the detail is still there, so
this guard cannot be satisfied by throwing the diagnosis away.

The scan is an AST walk over the raise sites rather than a grep, because a
grep over source cannot tell a message from the docstring above it — and every
docstring in these modules cites contracts, correctly.
"""

import ast
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
APPS = REPO / "apps"

#: What must not appear in a rendered message. Per-entry so a false positive
#: narrows one marker rather than deleting the list (`CLAUDE.md` rule 11).
DOCUMENT_MARKERS = {
    "§": "a section sign is only ever a contract citation",
    "DATA-MODEL": "the schema document",
    "API-CONTRACT": "the API document",
    "THREAT-MODEL": "the threat model",
    "COMPLIANCE.md": "the compliance file",
    "CLAUDE.md": "the project instructions",
    "TASKS.md": "the build order",
    "ADR-00": "an architecture decision record",
    "manage.py": "an operator command a student cannot run",
}

#: Exceptions that never reach a student. `NotImplementedError` and
#: `RuntimeError` are raised **at** a developer — a missing template, an unset
#: salt, an unimplemented stub — and are not `ServiceError`, so they are never
#: rendered through §2.2's shape.
DEVELOPER_EXCEPTIONS = {
    "NotImplementedError", "RuntimeError", "ValueError", "TypeError",
    "TemplateDoesNotExist", "CommandError", "AssertionError",
}


def rendered_messages():
    """`(file, line, exception, message)` for every raise that reaches §2.2.

    The **first positional argument only**: that is what `ServiceError.__init__`
    passes to `str(exc)` and what `error_payload` renders. Keyword arguments —
    `detail`, `field_errors`, `purpose_key` — are context and are not rendered.
    """
    found = []
    for path in sorted(APPS.rglob("*.py")):
        if "/migrations/" in path.relative_to(REPO).as_posix():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Raise) or not isinstance(node.exc, ast.Call):
                continue
            name = getattr(node.exc.func, "id", "") or getattr(node.exc.func, "attr", "")
            if name in DEVELOPER_EXCEPTIONS or not node.exc.args:
                continue
            arg = node.exc.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                text = arg.value
            elif isinstance(arg, ast.JoinedStr):
                text = "".join(v.value for v in arg.values if isinstance(v, ast.Constant))
            else:
                continue
            found.append((path.relative_to(REPO).as_posix(), node.lineno, name, text))
    return found


def test_the_scan_finds_the_raise_sites_it_claims_to():
    """`CLAUDE.md` rule 12. A walk that matched nothing would pass everything."""
    messages = rendered_messages()
    assert len(messages) >= 15, (
        f"only {len(messages)} rendered messages found in apps/**; the AST walk "
        "has stopped seeing raise sites"
    )
    assert any("services.py" in f for f, _l, _n, _t in messages)


def test_no_rendered_message_cites_an_internal_document():
    """The rule. Six of these shipped and a seventh arrived while they were
    being fixed."""
    offenders = []
    for file, line, name, text in rendered_messages():
        for marker, why in DOCUMENT_MARKERS.items():
            if marker in text:
                offenders.append(f"{file}:{line} {name}({marker!r} — {why}): {text[:70]}")
    assert offenders == [], (
        "API-CONTRACT §2.2's `message` is rendered to a student as a page. "
        "These cite an internal document in it. Move the citation to a keyword "
        "argument — `detail=...` — which is logged and never rendered, and "
        "leave the student a sentence they can act on:\n" + "\n".join(offenders)
    )


def test_the_detail_keyword_is_not_rendered():
    """The other half: moving a citation into `detail` is only a fix if
    `detail` genuinely stays out of the response."""
    from apps.core.api import error_payload
    from apps.core.errors import ValidationFailed

    exc = ValidationFailed("Plain sentence.", detail="DATA-MODEL §2 says so")
    body = error_payload(exc)["error"]
    assert body["message"] == "Plain sentence."
    assert "DATA-MODEL" not in str(body)
    assert exc.context["detail"] == "DATA-MODEL §2 says so", (
        "the citation was deleted rather than moved; the diagnosis has to "
        "survive somewhere a developer reads"
    )


@pytest.mark.parametrize(
    "message,should_flag",
    [
        ("DATA-MODEL §2 allows ['A', 'B'].", True),
        ("See API-CONTRACT §4.1.", True),
        ("Run `manage.py migrate`.", True),
        ("That is not a consent mechanism we can record.", False),
        ("BookHop is for students aged 18 and over.", False),
        ("Check your email for a sign-in link.", False),
    ],
)
def test_the_marker_set_catches_a_citation_and_leaves_copy_alone(message, should_flag):
    """The detector's own detector, with real strings from both sides —
    including the three the product actually ships."""
    flagged = any(marker in message for marker in DOCUMENT_MARKERS)
    assert flagged is should_flag, message
