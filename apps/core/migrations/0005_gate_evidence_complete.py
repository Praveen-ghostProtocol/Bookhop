"""F8 — a `gate='C'` authorisation must carry its whole evidence checklist.

QA-S0 F8: migration 0003's trigger requires a live `gate='C'`,
`scope_type='CAMPUS'`, `scope_id=NEW.id`, `revoked_at IS NULL` row and
`active = true`. It did not look at the evidence, so
`GateAuthorisation.objects.create(gate='C', scope_type='CAMPUS',
scope_id=campus.id, evidence={}, authorised_by_human='')` followed by an ORM
update opened the gate with an empty checklist, an unnamed authoriser and no
`audit_log` row.

Much smaller than the original M0 — this is an INSERT plus an UPDATE into a
table whose rows can afterwards be neither deleted nor rewritten, so a forged
authorisation is permanent evidence of the forgery — but QA's point stands:
**ADR-002 §4.1(b)'s six evidence items lived only in the command, and migration
0003 calls the trigger "the floor beneath it". The floor was lower than
§4.1(b) reads.** So the checklist moves into the database.

**What this does NOT move into the database, stated so the floor is not
overread:** whether the evidence is *true*. `campus_mou_ref = 'TODO'` still
passes, as QA-S0 B2 records and as
`test_the_database_floor_does_not_check_whether_the_evidence_is_true` asserts.
ADR-002 §4.2 already says this design makes the position auditable, not
correct. The five legal-entity facts stay in the command because they live on
another table and a row trigger cannot join to one without becoming the kind of
clever that fails on a restore.

`gate='B'` and `gate='D'` rows are unconstrained: ADR-002 §4.1(b) specifies the
checklist for Gate C, and inventing one for the others would be scaffolding for
a gate nothing opens.
"""

from django.db import migrations

#: ADR-002 §4.1(b), the six evidence keys. The command keeps its own ordered
#: copy because it prints a per-item checklist with each item's Gate number;
#: this is the set, which is all a constraint needs.
EVIDENCE_KEYS = (
    "counsel_engagement_ref",
    "takedown_sop_ref",
    "oncall_rota_ref",
    "breach_rehearsal_at",
    "campus_mou_ref",
    "notice_version_ids",
)

#: Characters that are not a name. REVIEW-S0 C1.
#:
#: Both engines' bare `trim()` / `btrim()` strip U+0020 only, so a single tab
#: passed as a named human. The first fix trimmed four characters — and four is
#: not the list: the reviewer measured that vertical tab, form feed, **NBSP
#: (what a paste from Word produces)**, figure space and ogham space all passed
#: the database floor while Python's `.strip()` blocked every one, so for five
#: of twelve forms the floor sat *above* the command it is the floor for. Worse,
#: zero-width space and BOM passed **both** layers, so the one field carrying
#: the whole "a named human signed this" rule could be satisfied by something
#: that renders as nothing in the audit row and in the go/no-go packet.
#:
#: Per-entry, with its codepoint and why it is here, so the list can be
#: extended rather than edited (`CLAUDE.md` rule 11).
INVISIBLE = (
    (0x0020, "space"),
    (0x0009, "tab"),
    (0x000A, "line feed"),
    (0x000D, "carriage return"),
    (0x000B, "vertical tab"),
    (0x000C, "form feed"),
    (0x00A0, "no-break space — what a paste from Word produces"),
    (0x1680, "ogham space mark"),
    (0x2007, "figure space"),
    (0x200B, "zero-width space — renders as an empty name"),
    (0xFEFF, "byte order mark — renders as an empty name"),
)

#: `chr()` / `char()` rather than escaped literals, so the SQL survives being
#: embedded in a Python string and so each codepoint is readable in the diff.
PG_WS = " || ".join(f"chr({cp})" for cp, _why in INVISIBLE)
SQLITE_WS = " || ".join(f"char({cp})" for cp, _why in INVISIBLE)

# ponytail: an enumerated invisible-character set, because neither engine can
# express "contains at least one visible character" — SQLite has no regex at
# all and Postgres's `[[:graph:]]` is libc- and locale-dependent, so a
# category-based test in SQL would be less predictable than this list, not more.
# **Ceiling: an invisible character not on the list passes this floor.** The
# real invariant lives one layer up, in `open_discovery._present()`, which asks
# Python's Unicode database whether any character is visible and therefore
# needs no list at all — so the command stays strictly stronger than the floor,
# which is the right relationship. Upgrade path: a CHECK calling a PL/Python
# function, which is not worth an untrusted-language extension for this.

PG_FORWARD = """
CREATE OR REPLACE FUNCTION gate_authorisations_evidence_complete() RETURNS trigger AS $fn$
DECLARE
  k  text;
  ws constant text := {ws};
BEGIN
  IF NEW.gate <> 'C' THEN
    RETURN NEW;
  END IF;

  IF coalesce(btrim(NEW.authorised_by_human, ws), '') = '' THEN
    RAISE EXCEPTION
      'ADR-002 4.1(b): a gate C authorisation needs a named human in authorised_by_human. No agent writes this row.';
  END IF;

  FOREACH k IN ARRAY ARRAY[{keys}] LOOP
    IF NEW.evidence -> k IS NULL
       OR (jsonb_typeof(NEW.evidence -> k) = 'array'
           AND jsonb_array_length(NEW.evidence -> k) = 0)
       OR (jsonb_typeof(NEW.evidence -> k) NOT IN ('array', 'object')
           AND coalesce(btrim(NEW.evidence ->> k, ws), '') = '') THEN
      RAISE EXCEPTION
        'ADR-002 4.1(b): a gate C authorisation needs every evidence item; missing or blank: %', k;
    END IF;
  END LOOP;

  RETURN NEW;
END $fn$ LANGUAGE plpgsql;

CREATE TRIGGER gate_authorisations_evidence_complete
  BEFORE INSERT OR UPDATE ON gate_authorisations
  FOR EACH ROW EXECUTE FUNCTION gate_authorisations_evidence_complete();
ALTER TABLE gate_authorisations ENABLE ALWAYS TRIGGER gate_authorisations_evidence_complete;
""".format(ws=PG_WS, keys=", ".join(f"'{k}'" for k in EVIDENCE_KEYS))

PG_REVERSE = """
DROP TRIGGER IF EXISTS gate_authorisations_evidence_complete ON gate_authorisations;
DROP FUNCTION IF EXISTS gate_authorisations_evidence_complete();
"""

MESSAGE = (
    "ADR-002 4.1(b): a gate C authorisation needs a named human and every "
    "evidence item, non-blank. No agent writes this row."
)


def _sqlite_condition():
    """True when a gate C row is incomplete.

    `json_extract` / `json_type` are SQLite's JSON1, compiled in by default and
    already relied on by Django's JSONField on this backend. The blank-vs-absent
    and empty-array distinctions mirror the Postgres body above.
    """
    parts = [f"coalesce(trim(NEW.authorised_by_human, {SQLITE_WS}), '') = ''"]
    for key in EVIDENCE_KEYS:
        extract = f"json_extract(NEW.evidence, '$.{key}')"
        parts.append(
            f"({extract} IS NULL"
            f" OR (json_type(NEW.evidence, '$.{key}') = 'text'"
            f"     AND coalesce(trim({extract}, {SQLITE_WS}), '') = '')"
            f" OR (json_type(NEW.evidence, '$.{key}') = 'array'"
            f"     AND json_array_length(NEW.evidence, '$.{key}') = 0))"
        )
    return "\n      OR ".join(parts)


SQLITE_FORWARD = [
    f"""
    CREATE TRIGGER gate_authorisations_evidence_complete_insert
    BEFORE INSERT ON gate_authorisations
    WHEN NEW.gate = 'C' AND ({_sqlite_condition()})
    BEGIN
      SELECT RAISE(ABORT, '{MESSAGE}');
    END;
    """,
    f"""
    CREATE TRIGGER gate_authorisations_evidence_complete_update
    BEFORE UPDATE ON gate_authorisations
    WHEN NEW.gate = 'C' AND ({_sqlite_condition()})
    BEGIN
      SELECT RAISE(ABORT, '{MESSAGE}');
    END;
    """,
]

SQLITE_REVERSE = [
    "DROP TRIGGER IF EXISTS gate_authorisations_evidence_complete_insert;",
    "DROP TRIGGER IF EXISTS gate_authorisations_evidence_complete_update;",
]


def _run(statements_pg, statements_sqlite):
    def apply(apps, schema_editor):
        vendor = schema_editor.connection.vendor
        if vendor == "postgresql":
            # params=None: see the note in 0002. `missing or blank: %', k`
            # needs a literal `%` to reach plpgsql.
            schema_editor.execute(statements_pg, None)
        elif vendor == "sqlite":
            for statement in statements_sqlite:
                schema_editor.execute(statement, None)
        else:
            raise RuntimeError(
                f"the gate evidence guard is not written for {vendor!r}; ADR-001 §2.2 "
                "permits postgresql (production) and sqlite (local dev) only"
            )

    return apply


class Migration(migrations.Migration):
    dependencies = [("core", "0004_anonymous_idempotency_key")]

    operations = [
        migrations.RunPython(_run(PG_FORWARD, SQLITE_FORWARD), _run(PG_REVERSE, SQLITE_REVERSE)),
    ]
