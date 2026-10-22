r"""The `Vary` property test's one exemption, and its declared ceiling.

`tests/a11y/test_page_cache_headers.py` holds the structural half of R-R4:
an AST walk over `web/views.py` asserting that no view reads a request
header except through `_varying_header`. It carries one exemption and one
declared ceiling, and both are claims:

> `HEADER_READERS_THAT_NEED_NO_VARY = {"_ip_ua"}` … Any further entry here
> is a claim that a header changes nothing a student sees, and must be
> defended in the same breath.

> # ponytail: AST over `web/views.py` only. Ceiling — a header read in
> # `web/context.py`, `web/forms.py` or a template tag is not seen. No such
> # read exists today.

`CLAUDE.md` rule 9 says a document's claim is not evidence, and rule 10's
corollary says *"a mark must be as narrow as the gap it marks"* — because
marking an aggregate lets a second failure hide inside the first. The
exemption is marked on a **function**, not on a **read**: a `Save-Data`
read added inside `_ip_ua` tomorrow is exempt for free, and `_ip_ua` is
called by most of the write paths in the file. This file narrows that, and
measures the ceiling instead of reading it.

Three tests, no database, no fixtures. None of them duplicates the walk in
`test_page_cache_headers.py`; each asserts something that walk takes on
trust.
"""

import ast
import pathlib

import pytest

from tests.a11y.test_page_cache_headers import (
    HEADER_READERS_THAT_NEED_NO_VARY,
    THE_RECORDER,
)

WEB = pathlib.Path(__file__).resolve().parents[2] / "web"

#: The one header the exemption's own defence covers: *"`User-Agent` is read
#: for the audit record and changes nothing in the body."* Anything else read
#: in an exempted function is outside the sentence that justifies it.
EXEMPTED_HEADERS = {"user-agent"}


def _header_literals(node):
    """Every header name read off a request inside `node`.

    Both spellings: `request.headers.get("X")` and the `HTTP_X` key into
    `request.META`. The *name* is what matters here, not the receiver — the
    receiver is the next test's question.
    """
    found = set()
    for child in ast.walk(node):
        if (
            isinstance(child, ast.Call)
            and isinstance(child.func, ast.Attribute)
            and isinstance(child.func.value, ast.Attribute)
            and child.func.value.attr == "headers"
            and child.args
            and isinstance(child.args[0], ast.Constant)
            and isinstance(child.args[0].value, str)
        ):
            found.add(child.args[0].value.lower())
        if (
            isinstance(child, ast.Constant)
            and isinstance(child.value, str)
            and child.value.startswith("HTTP_")
            and len(child.value) > 5
        ):
            found.add(child.value[5:].replace("_", "-").lower())
    return found


def _functions(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


@pytest.mark.parametrize("name", sorted(HEADER_READERS_THAT_NEED_NO_VARY))
def test_an_exempted_function_reads_only_the_header_its_exemption_defends(name):
    """The exemption is per-function; the defence is per-header.

    `_ip_ua` is exempted because `User-Agent` changes nothing in the body —
    which I checked rather than assumed: it is passed to
    `accounts.request_magic_link`, whose rate limits are keyed on the email
    and the IP and not on it. That defence does not extend to a second
    header, and the current shape of the exemption grants it anyway.

    This test is the narrowing. It fails by name on the day a header that
    *does* change a body is read inside an exempted function, which is a
    gap the structural walk cannot see because it skips the whole function.
    """
    functions = _functions(WEB / "views.py")
    assert name in functions, (
        f"{name}() is exempted from the Vary walk and no longer exists in "
        "web/views.py, so the exemption is a stale entry that silently "
        "widens the next function someone gives that name"
    )
    read = _header_literals(functions[name])
    assert read <= EXEMPTED_HEADERS, (
        f"{name}() is exempted from the `Vary` walk on the stated ground "
        f"that it reads `User-Agent` for the audit record and that nothing "
        f"in any body depends on it. It also reads {sorted(read - EXEMPTED_HEADERS)}, "
        f"which that sentence does not cover. Either route the read through "
        f"`{THE_RECORDER}` or defend the new header in the same breath — the "
        f"exemption is marked on the function and the defence is about one "
        f"header (CLAUDE.md rule 10's corollary on marks)."
    )


def test_no_header_is_read_off_a_request_under_any_other_name():
    """The walk keys on the literal name `request`. This one does not.

    `tests/a11y/test_page_cache_headers.py` matches
    `ast.Attribute(value=Name('request'), attr='headers')`. A helper written
    as `def _render(req, ...)` reading `req.headers["Save-Data"]`, or a read
    through `self.request.headers`, is invisible to it. The house style in
    `web/views.py` is `request` throughout today, which is exactly why this
    is cheap to assert now and expensive to discover later.

    Asked as a property: **any** `.headers` attribute access, whatever it
    hangs off, must be inside the recorder or an exempted function.
    """
    functions = _functions(WEB / "views.py")
    offenders = []
    for name, node in functions.items():
        if name == THE_RECORDER or name in HEADER_READERS_THAT_NEED_NO_VARY:
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.Attribute) and child.attr == "headers":
                receiver = getattr(child.value, "id", None) or ast.dump(child.value)[:40]
                offenders.append(f"{name}() line {child.lineno}: {receiver}.headers")
    assert offenders == [], (
        "a request header is read off something other than `request`, so "
        f"nothing records it and `Vary` is not patched: {offenders}"
    )


def test_the_declared_ceiling_is_real_today():
    """*"No such read exists today"* — measured, not read.

    This is the guard on the ponytail ceiling. The walk covers one module;
    the ceiling says the rest of the package reads no headers. If
    `web/context.py` starts branching on `Accept-Language` the structural
    half of R-R4 stops being a property of the package while its own comment
    still says it is one — which is rule 12's *"the document already
    describes the better state"*.

    The remedy when this fires is one line in the sibling file's
    `_sources()`, as its own comment says. It is not an entry here.
    """
    unseen = sorted(
        p for p in WEB.glob("*.py") if p.name not in ("views.py", "__init__.py")
    )
    assert unseen, "the ceiling names other modules in web/; none were found"
    offenders = []
    for path in unseen:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "headers":
                offenders.append(f"{path.name}:{node.lineno} .headers")
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and node.value.startswith("HTTP_")
            ):
                offenders.append(f"{path.name}:{node.lineno} {node.value!r}")
    assert offenders == [], (
        "the Vary walk covers web/views.py only, and its declared ceiling "
        "says no other module in the package reads a request header. One "
        f"does now, so the structural half of R-R4 has a hole: {offenders}. "
        "Widen the walk's `_sources()`; do not exempt these."
    )
