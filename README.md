# BookHop — repository

A marketplace for physical used books in India. Pilot: verified adults at
2–3 Chennai campuses, local handovers.

`company/` is the company brain and `company/architecture/` holds the frozen
contracts. **Read them before changing code**; `TASKS.md` §1 is the authoritative
file-ownership map and no agent edits a file it does not own.

## Run it

```
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
copy .env.example .env
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py seed_demo
.venv\Scripts\python.exe -m pytest
```

### The database you are actually running against

Production is **PostgreSQL 16** (ADR-001 §2.2). The development machine this
was built on has neither Postgres nor Docker, so `bookhop/settings/dev.py`
defaults to **SQLite**, selected by `BOOKHOP_DB_ENGINE`.

> **Read `company/architecture/ENGINE-DIVERGENCE.md` before you trust a green
> test run.** It lists every place the two engines differ for this schema and
> says, per item, whether the property is verified locally or only assumed.
> Some of them matter: the double-booking guard is one.

`bookhop/settings/prod.py` refuses to start on anything but Postgres.

## Management commands

| Command | What it does |
|---|---|
| `migrate` | schema; every change is a migration, no exceptions |
| `seed_demo` | one city, one campus with the discovery gate **closed** |
| `open_discovery --campus <slug> [--by <name>]` | opens discovery, **only** with a complete `gate_authorisations` row (ADR-002 §4.1(b)); prints the checklist and exits non-zero on the first missing item. The column also has a **database write guard**, so this is the only path that can open a gate at all — not merely the intended one |
| `close_discovery --campus <slug> --reason <text> [--by <name>]` | closes it and revokes the authorisation. Closing is always permitted, by design |
| `run_jobs` | claims and runs due jobs, then exits (a systemd timer runs it every minute from S8) |
| `verify_audit_chain` | recomputes the `audit_log` hash chain |

## Layout

```
bookhop/           settings, root urlconf, wsgi            (backend-developer)
apps/core/         tenancy, discovery gate, audit, jobs,
                   feature flags, idempotency              (backend-developer)
apps/accounts/     S0: frozen signature stubs only         (backend-developer)
tests/unit/        unit + the CI guard tests               (backend-developer)
tests/api/         API/service-level tests                 (backend-developer)
web/ templates/
static/ locale/    HTML routes, templates, CSS, EN+TA      (frontend-developer)
tests/e2e/ a11y/   written independently of the code       (test-qa)
deploy/ ops/       dormant until S8                        (platform-sre)
```

## The guard tests, and what they are for

These fail the build on purpose. Do not relax one; a diff to
`tests/unit/test_forbidden_schema.py` is a founder escalation (ADR-003 §5.2).

| Test | Property |
|---|---|
| `test_forbidden_schema.py` | ADR-003 §2.3 as amended — a **whitelist**, over lists imported from `apps/core/p14.py` (never retyped): every numeric column is `listings.asking_price_paise` or carries a ratified non-monetary name; **no column anywhere, in any type, contains a money token** except the two the ADR names; **no float or decimal column exists anywhere**, checked as the union of both introspection routes so a model cannot vouch for a `real` column; the four transaction tables have frozen column lists; the deny-list sits behind all of it for its error message. No DOB is permitted in any table, in any state |
| `test_forbidden_source.py` | ADR-003 §2.3 W1c — no model field, `@property`, serialiser key or response key in `apps/**` is money-shaped. A `@property settled_price` changes zero columns, so this is the only control for that residual |
| `test_forbidden_response.py` | ADR-003 §2.3 at the contract boundary — no response contains a money-shaped key at any depth, and no key is named `price`, `amount`, `total` or `value`. A price absent from storage but present in a response is still a record, and this is the compensating control for P14's jsonb and free-text limbs |
| `test_gate.py` | a campus is closed by default and **the column has a database write guard**, so neither an ORM `update()` nor a `save()` nor an INSERT can open a gate without a live, **complete** Gate C authorisation; an incomplete authorisation cannot even be written; `open_discovery`'s checklist names the missing item; the authorisation row is append-only |
| `test_audit_append_only.py` | `audit_log` cannot be updated or deleted, and a tampered chain is detected |
| `test_scoping.py` | every tenant-scoped model has `campus_id`/`city_id` NOT NULL and a leading index |
| `test_price_immutable.py` | the `listings_price_immutable` trigger — **skipped until S2**, with the engine mechanism verified today |
| `test_seed_separation.py` | seed and real accounts never transact — **skipped until S4**, with the CHECK mechanism verified today |
| `test_partial_unique_index_engine.py` | the engine behaviour the double-booking guard rests on |
