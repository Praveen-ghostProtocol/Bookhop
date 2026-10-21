"""Why a test cannot run, phrased for the engine it is actually on.

ENGINE-DIVERGENCE §10.6's finding against `QA-S0.md` §7 is taken: a bare
`pytest.skip()` whose reason interpolates the live vendor into a sentence about
SQLite is honest on SQLite and **self-contradicting on PostgreSQL** — it names
the wrong engine and stops being true. Eight of QA's skips were shaped that way.

Four of them are now real tests. The four that remain are blocked by a table
that does not exist, not by the engine, and this helper is how they say so: the
reason is composed from what is actually missing on the engine in front of it.

`CLAUDE.md` rule 12's requirement is that a test which cannot run **skips with a
reason naming the engine and the slice**. That is still met — the engine is
named, and now named correctly.
"""

from django.db import connection


def unavailable(*, slice_, subject, needs_tables=(), needs_engine=None, note=""):
    """Compose a skip reason that is true on this engine.

    `needs_engine` is the engine the property requires, if any. When the suite
    is already on it, the engine is dropped from the reason instead of being
    asserted as a limit that no longer applies.
    """
    vendor = connection.vendor
    parts = []
    if needs_engine and vendor != needs_engine:
        parts.append(f"requires {needs_engine} (running on {vendor})")
    if needs_tables:
        parts.append(
            "requires " + ", ".join(f"`{t}`" for t in needs_tables)
            + f", created in {slice_}"
        )
    if not parts:
        parts.append(f"not available before {slice_}")
    reason = (
        f"NOT VERIFIABLE YET (vendor={vendor}, slice={slice_}): {subject} — "
        + "; ".join(parts) + "."
    )
    if note:
        reason += " " + note
    return reason
