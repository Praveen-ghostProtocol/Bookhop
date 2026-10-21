# ENGINE-DIVERGENCE.md — SQLite (dev) vs PostgreSQL 16 (production)

**Owner:** backend-developer · **Version:** v1.1 · **Date:** 2026-10-21
> Header corrected by ceo-planning: it read v1.0 while the changelog below
> recorded v1.1. Flagged by code-review as R4 and worth the one line, because
> this is the document a developer is told to trust *before* trusting a green
> test run — a stale version header on it undermines the one artefact whose
> job is to say what has and has not actually been verified.
**Status:** living document. Every slice that adds a table or a constraint adds
its rows here in the same commit.
**Reads with:** ADR-001 §2.2 (the stack decision, unchanged) · ADR-002 §4 ·
ADR-003 §2.2–2.3 · `DATA-MODEL.md` · `THREAT-MODEL.md` §6.

---

## 0. Why this file exists, in one paragraph

**ADR-001 §2.2 is not amended. Production is PostgreSQL 16 and nothing in S0
changes that.** But the machine S0 was built on has **Python 3.11.9 and neither
PostgreSQL nor Docker installed**, and installing system software is the
founder's decision, not an agent's. So `bookhop/settings/base.py` selects the
engine from `BOOKHOP_DB_ENGINE` — `postgres` by default, `sqlite` in
`settings/dev.py` — and the whole test suite runs locally on SQLite.

That makes a green test run a weaker statement than it looks, and the point of
this file is to say exactly how much weaker. **Every row below is labelled
`VERIFIED HERE`, `VERIFIED HERE / ASSUMED THERE`, or `UNVERIFIED`.** Anything
labelled `UNVERIFIED` has not been executed against PostgreSQL by anybody; it
is reasoning, and reasoning is what the §9 escalation exists to replace.

**The one thing to read if you read nothing else: §5, the double-booking
guard.** A green `pytest` on this machine does **not** verify that BookHop
cannot double-book a listing in production.

---

## 1. What was actually run, and where

| | Development machine (this evidence) | Production target |
|---|---|---|
| Python | **3.11.9** (ADR-001 §2.1 says 3.12 — see §8 item 1) | 3.12 |
| Django | 5.2.8 | 5.2 LTS |
| Engine | SQLite **3.45.1** via `django.db.backends.sqlite3` | PostgreSQL 16 |
| Driver | — | `psycopg[binary]` 3.2.3 — **installed and importable here**, so `settings/prod.py` loads and `manage.py check` passes against the Postgres backend |
| Postgres server | **none** | — |

Consequences of there being no server, stated so nobody over-reads the
evidence:

- `manage.py sqlmigrate` against the Postgres backend **fails at connect**, so
  not one line of Postgres DDL for this schema has been generated, let alone
  executed. Measured: `OperationalError: connection to server at "127.0.0.1",
  port 5432 failed`.
- Every `plpgsql` body in a migration is **unexecuted text**. Its syntax has
  never been parsed by a Postgres server.
- `apps/core/migrations/0002_append_only_triggers.py` branches on
  `schema_editor.connection.vendor` and writes the same guarantee twice. The
  SQLite half is exercised by the test suite. The Postgres half is not
  exercised by anything.

`PRAGMA foreign_keys=ON` is set in `DATABASES["default"]["OPTIONS"]`, because
SQLite's default is to not enforce foreign keys at all and a development engine
must not be laxer than the one the assertions are about. **`VERIFIED HERE`.**

---

## 2. Column types

SQLite has dynamic typing: a column's declared type is a hint, not a
constraint. This is the broadest category of divergence and the easiest to
forget.

| # | Contract (`DATA-MODEL.md`) | Postgres | SQLite here (measured) | Divergence that matters | Label |
|---|---|---|---|---|---|
| 2.1 | `campuses.email_domains text[] NOT NULL DEFAULT '{}'` | would be `text[]` | `TEXT` holding a JSON array (`models.JSONField`) | **This is a deviation from a FROZEN contract on both engines, not just locally.** `ArrayField` is `django.contrib.postgres`-only and cannot be expressed on SQLite, and a per-engine field choice would produce two different migrations for one schema. The only operation v1 performs is membership, which is identical. **Escalated to cto — §9 item 1.** | `VERIFIED HERE` (column exists as `TEXT`), **deviation**, Postgres shape `UNVERIFIED` |
| 2.2 | `gate_authorisations.evidence jsonb`, `jobs.payload jsonb`, `idempotency_keys.response_body jsonb` | `jsonb`: semantic equality, key order normalised, GIN-indexable | `TEXT`: byte-string equality, no operators | The gate trigger compares `evidence` for change. On Postgres, re-saving the same object with reordered keys is **not** a change; on SQLite it **is**. Nothing in v1 re-saves evidence, so this is latent, not live. S7's analytics must not index into these on SQLite — `supports_json_field_contains = False` (measured). | `VERIFIED HERE / ASSUMED THERE` |
| 2.3 | `uuid` (`audit_log.actor_pseudonym`, and every `*_pseudonym` from S1) | native `uuid`, format validated by the engine, 16 bytes | `char(32)` (measured) | On Postgres a malformed uuid is rejected by the database; on SQLite any 32-char string is accepted. Pseudonyms are generated in Python, so the risk is a bad migration or a direct SQL insert, not application code. Also affects `ORDER BY` on uuid columns. | `VERIFIED HERE / ASSUMED THERE` |
| 2.4 | `inet` (`audit_log.ip`; S1 `email_login_tokens.requested_ip`, `consents.ip`) | `inet`: validates and normalises, supports subnet operators | `char(39)` (measured) | Postgres will reject a non-address string at insert; SQLite will store it. Rate-limiting or abuse queries that use subnet containment can only be written on Postgres. | `VERIFIED HERE / ASSUMED THERE` |
| 2.5 | `timestamptz`, `USE_TZ=True`, stored UTC (`DATA-MODEL.md` §0) | `timestamp with time zone`, microsecond precision | declared `datetime`, stored as ISO-8601 **text with no offset**; Django attaches UTC on read (measured) | Ordering and equality work because the text is fixed-width ISO. But **SQL-level** date arithmetic (`now() - interval '90 days'`, `date_trunc`) is Postgres-only — see §6. All S0 timestamps are computed in Python, so no S0 code depends on it. | `VERIFIED HERE / ASSUMED THERE` |
| 2.6 | `DEFAULT now()` on `created_at`/`occurred_at` etc. | a real server-side default | **no DB-side default**: every timestamp comes from Python `timezone.now()` | Deliberate, and it is *not* an engine divergence — the behaviour is identical on both — but it **is** a deviation from the DDL in `DATA-MODEL.md`. Consequence: a row inserted by raw SQL without the column would fail rather than default. Nothing does that. | **deviation, identical on both engines** |
| 2.7 | `integer` / `smallint` with ranges | int4/int2 range enforced; out-of-range is an error | **no range check**: `99999` stored in a `smallint` column (measured) | `jobs.attempts smallint` overflowing is an error on Postgres and silent on SQLite. Low impact; `max_attempts` is 5. | `VERIFIED HERE / ASSUMED THERE` |
| 2.8 | `integer` money, **no float money ever** (ADR-003 §2.1) | a float inserted into `integer` is rejected or rounded by the engine | **a float stays a float**: `300.75` inserted into an `integer NOT NULL` column came back as `typeof = 'real'`, value `300.75`. A string `'12abc'` came back as `typeof = 'text'` (measured) | **This one is worth reading twice.** The "integer paise, never float money" rule is enforced by the *Postgres* type system, by the Python service layer, and by ADR-003's CHECK — but **not** by the local engine. A float-money bug in S2 would pass the local suite. Mitigation in S2: the service layer must coerce and validate, and the CHECK bound (`>= 0 AND <= 10000000`) is enforced on both. | `VERIFIED HERE` (SQLite does **not** enforce it) / Postgres behaviour `UNVERIFIED` |
| 2.9 | `citext` (`users.email`, S1) | `citext` extension: case-insensitive uniqueness in the engine | would need `COLLATE NOCASE` or a lowercased column | **S1 blocker, flagged now.** `UNIQUE(email)` must be case-insensitive or `Student@x.edu` and `student@x.edu` become two accounts. On SQLite the plain unique index is case-**sensitive**: `'a' < 'B'` evaluated to false, i.e. BINARY collation (measured). S1 must either normalise the address in the service layer (works on both, recommended) or accept that the property is Postgres-only. | `UNVERIFIED` — not in S0 |
| 2.10 | `bigint GENERATED BY DEFAULT AS IDENTITY` (`DATA-MODEL.md` §0) | a sequence; values are never reused | `INTEGER PRIMARY KEY` = rowid alias (measured); **max rowid can be reused after the highest row is deleted** | Matters only for a table whose rows are deleted and whose ids are referenced elsewhere. `audit_log` cannot be deleted from, so the hash chain is unaffected. Noted for S1's purge work. | `VERIFIED HERE / ASSUMED THERE` |
| 2.11 | `boolean` | native `boolean` | integer `0`/`1` | Only bites raw SQL written as `WHERE flag = 'true'`. All S0 access is through the ORM. The CHECK probe in `tests/unit/test_seed_separation.py` uses `1`/`0` for that reason. | `VERIFIED HERE / ASSUMED THERE` |

---

## 3. Constraints and triggers

| # | Property | Postgres | SQLite here (measured) | Label |
|---|---|---|---|---|
| 3.1 | **`CHECK (col IN (...))` for every enum** (`DATA-MODEL.md` §0) | enforced | enforced; `supports_table_check_constraints = True` | `VERIFIED HERE / ASSUMED THERE` |
| 3.2 | **`CHECK (seller_is_seed = buyer_is_seed)`** — seed and real never transact (ADR-002 §4.1(c)) | enforced | the *mechanism* is enforced on INSERT **and** UPDATE: `tests/unit/test_seed_separation.py::test_check_constraint_mechanism_is_enforced_on_this_engine` builds a two-column CHECK of this exact shape and both violations raise | mechanism `VERIFIED HERE`; **the real constraint does not exist yet — `transfers` is an S4 table.** Until S4 nothing in this repository prevents a seed/real transfer, because nothing creates transfers |
| 3.3 | **Partial unique index** — the double-booking guard | see §5 | see §5 | see §5 |
| 3.4 | `UNIQUE` treats NULLs as distinct (`idempotency_keys UNIQUE(user_id, key)` with a NULL user) | NULLs distinct unless `NULLS NOT DISTINCT` is asked for, which we do not | NULLs distinct | identical by the SQL standard; `VERIFIED HERE / ASSUMED THERE`. **This identical behaviour was itself the defect** QA-S0 B3 found: an anonymous POST never deduped, so a replay claimed a second row instead of replaying the first, and API-CONTRACT §5.1/§5.6 have four anonymous POSTs. Closed in migration 0004 by a second, partial unique index on `key` alone WHERE `user_id IS NULL`, which puts anonymous keys in one global namespace — sound because the key is a client UUIDv4. Rejected alternatives and why are in `services.idempotent()`'s docstring. **Then QA-S0 F10 found the fix incomplete, and the gap was a disclosure rather than a hole in a guard:** a global namespace is safe only if the key is unguessable, and nothing checked the format, so `Idempotency-Key: 1` was legal — and on a matching body the second anonymous caller received the first's stored `response_body`, measured as `{"grievance_ref": "GRV-000123"}` reaching a stranger on the endpoint a distressed non-user reaches us through. Two changes: an anonymous key **must parse as a UUID** (else `400 VALIDATION_FAILED`), which makes API-CONTRACT §4.1's own argument true instead of assumed; and **an anonymous replay returns the status, never the stored body**, so no path exists on which one anonymous caller receives another's response. An authenticated replay is unchanged. `VERIFIED HERE` |
| 3.5 | **`audit_log` is append-only** (`DATA-MODEL.md` §8) — UPDATE and DELETE blocked | `BEFORE UPDATE OR DELETE` row trigger raising `RAISE EXCEPTION` | `BEFORE UPDATE` and `BEFORE DELETE` triggers raising `RAISE(ABORT, ...)`; six assertions in `tests/unit/test_audit_append_only.py` cover single-row update, single-row delete and whole-table delete | SQLite half `VERIFIED HERE`; **Postgres plpgsql half `UNVERIFIED` — the function body has never been parsed by a server** |
| 3.6 | **`audit_log` cannot be emptied by `TRUNCATE`** | row triggers **do not fire on TRUNCATE**, so migration 0002 adds a separate `BEFORE TRUNCATE … FOR EACH STATEMENT` trigger. Without it the §3.5 guarantee has a hole on Postgres that does not exist on SQLite. **Migration 0003 redefines it with one declared escape** — see §7.1, which v1.0 of this document got backwards | SQLite **has no `TRUNCATE` statement** at all — measured: `OperationalError: near "TRUNCATE": syntax error` — so there is nothing to block and nothing to test | the hole was found by writing this document; the fix is `UNVERIFIED` and **is the single most important thing for a Postgres box to confirm** |
| 3.6a | **Triggers survive `session_replication_role = 'replica'`** | migration 0003 adds `ALTER TABLE … ENABLE ALWAYS TRIGGER` to all five guards. THREAT-MODEL §4 B5/B6 already accepts direct SQL as out of scope, so this is not a new exposure, but the replication-role route is one line to close and it matters for logical replication and for a restore | no equivalent and none needed | `UNVERIFIED` (REVIEW-S0 N7) |
| 3.6b | **`campuses.discovery_enabled_at` has a write guard** — M0, the finding that blocked integration | `BEFORE INSERT OR UPDATE` row trigger (migration 0003): an INSERT must leave the column NULL; setting it to NULL is always permitted; setting it to a timestamp requires a live `gate = 'C'`, `scope_type = 'CAMPUS'`, `scope_id = NEW.id`, `revoked_at IS NULL` authorisation **and** `active = true` | the same rule as two `WHEN`-guarded triggers, one for INSERT and one for UPDATE. A subquery in a trigger `WHEN` clause works here — **measured**, because SQLite forbids subqueries in CHECK constraints and it was not safe to assume triggers behave the same. 11 assertions in `tests/unit/test_gate.py` | SQLite half `VERIFIED HERE`; Postgres plpgsql half `UNVERIFIED` |
| 3.6c | **A `gate='C'` authorisation must carry its whole evidence checklist** (QA-S0 F8) | `BEFORE INSERT OR UPDATE` plpgsql trigger looping the six ADR-002 §4.1(b) evidence keys, with `jsonb_typeof` separating a blank string from an empty array | two `WHEN`-guarded triggers using SQLite's JSON1 (`json_extract`, `json_type`, `json_array_length`), which Django's JSONField already relies on here. **Measured and fixed while writing it:** both engines' bare `trim()`/`btrim()` strip spaces only, so a single tab passed as a named human — both bodies now pass an explicit whitespace set. 13 assertions | SQLite half `VERIFIED HERE`; Postgres plpgsql half `UNVERIFIED`. **The floor it raises is bounded and the bound is asserted**: it checks that every box is filled, never that any box is true (`campus_mou_ref = 'TODO'` still opens the gate — QA-S0 B2, ADR-002 §4.2) |
| 3.7 | **`gate_authorisations` permits no UPDATE except `revoked_at`/`revoked_reason`**, and no DELETE (`DATA-MODEL.md` §1) | row trigger comparing each immutable column with `IS DISTINCT FROM`, plus a `BEFORE TRUNCATE` statement trigger | `WHEN ... IS NOT ...` trigger plus a DELETE trigger; two assertions in `tests/unit/test_gate.py` (delete refused, `evidence` rewrite refused) | SQLite half `VERIFIED HERE`; Postgres half `UNVERIFIED` |
| 3.8 | **The exception *class* a trigger raises** | `RAISE EXCEPTION` is SQLSTATE `P0001` → `psycopg.errors.RaiseException` → `django.db.utils.InternalError` | `RAISE(ABORT, ...)` → `django.db.utils.IntegrityError` (measured) | **`VERIFIED HERE` for SQLite, `UNVERIFIED` for Postgres, and this one will bite someone.** A service that catches `IntegrityError` to convert a trigger failure into a 4xx will pass locally and **swallow nothing on Postgres**. Every test in this repository catches `django.db.DatabaseError`, the common parent, on purpose. S2's price-immutability handler and S4's `accept_offer` must do the same or branch explicitly |
| 3.8a | **The local engine does not type its columns** (§2.8) — so P14's one permitted money column was free to be a float | `integer` rejects or rounds a float; `real`/`numeric` are distinct declared types | nothing enforces a declared type, and a name-based control reads none: QA-S0 F1 attack 7 declared `listings.asking_price_paise` as `real` in raw DDL and the whole guard passed it | **closed, and engine-neutrally**: `tests/unit/test_forbidden_schema.py` now forbids **every** float or decimal column anywhere (except `handover_points`' public-landmark coordinates), reading types through Django model meta *and* `connection.introspection.get_field_type()`, and **failing closed** when a declared type cannot be classified — because `numeric` and `double precision` are exactly the shapes it hunts. Verified against `real` and `numeric` raw-DDL attacks: both caught. `VERIFIED HERE` |
| 3.9 | **`listings_price_immutable`** (ADR-003 §2.2) — P14 | plpgsql `BEFORE UPDATE` trigger, given verbatim in ADR-003 | **no SQLite equivalent is written, because `listings` is an S2 table.** What is verified today is that this engine aborts an UPDATE from a `BEFORE UPDATE` trigger at all: `tests/unit/test_price_immutable.py::test_trigger_mechanism_raises_on_this_engine` builds the probe and the UPDATE raises with the `P14` marker in the message | mechanism `VERIFIED HERE`; **the real trigger does not exist and the property is NOT satisfied yet.** `tests/unit/test_price_immutable.py`'s two real assertions are **skipped**, with `listings is created in S2` as the reason, exactly as `TASKS.md` §2 S0 instructs. **S2 must write a second, SQLite trigger body or P14 becomes locally unverifiable** |
| 3.10 | Deferrable constraints | supported | `supports_deferrable_unique_constraints = False` (measured) | not used anywhere; no impact |
| 3.11 | Covering / GIN / GiST indexes | supported | `supports_covering_indexes = False`; B-tree only | S2's `GIN (title_norm gin_trgm_ops)` and S3's search cannot be created locally — see §6 |
| 3.12 | DDL inside a transaction | supported | `can_rollback_ddl = True` (measured) | identical; migrations roll back on both |

---

## 4. Concurrency, locking and isolation — the category where local green means least

| # | Property | Postgres | SQLite here | Label |
|---|---|---|---|---|
| 4.1 | Write concurrency | MVCC; many concurrent writers; row-level locks | **one writer for the whole database**. Concurrent writers serialise or get `OperationalError: database is locked` | structural. **Every concurrency assertion in this repository passes locally for a reason that does not exist in production.** `UNVERIFIED THERE` |
| 4.2 | Isolation level | `READ COMMITTED` by default | effectively serialised writes | a read-modify-write race that Postgres permits **cannot be reproduced locally**. The `expected_version` optimistic lock (API-CONTRACT §4.2) is therefore untestable here in its failure mode: its `UPDATE ... WHERE version = ?` returning zero rows can be *simulated* by changing the version first, but not *raced*. `UNVERIFIED THERE` |
| 4.3 | `SELECT ... FOR UPDATE SKIP LOCKED` for job claiming (ADR-001 §2.4) | the ADR's mechanism | **Django reports `has_select_for_update = False` and `has_select_for_update_skip_locked = False`, and silently omits the locking clause instead of raising** (measured: the query runs and returns rows) | A silent no-op is worse than an error, because the code would look correct locally while locking nothing. `apps/core/jobs.py` therefore claims with a conditional `UPDATE ... WHERE id = ? AND locked_at IS NULL` and checks the row count. Same property, expressible on both engines, visible in the query log. **This is a deviation from ADR-001 §2.4's stated mechanism — §9 item 2.** Claim-skipping is `VERIFIED HERE` single-threaded (`tests/unit/test_jobs.py::test_a_job_locked_by_a_live_worker_is_skipped`); multi-worker claiming is `UNVERIFIED` on both |
| 4.3a | **Lock release when a worker dies** — the half of §4.3 that v1.0 of this document missed (REVIEW-S0 M4) | `SKIP LOCKED` holds its lock inside the transaction, so the lock **is released when the connection dies** | a `locked_at` column is released by nothing. Measured before the fix: a job locked 30 days earlier by `dead-worker` was not run, not retried and not failed across three successive `run_due_jobs()` calls — which delivers the job **zero** times, permanently and silently, against the at-least-once guarantee in ADR-001 §2.4 and API-CONTRACT §4.4, in exactly the case that guarantee exists for. From S1 that job is `retention.purge`, a DPDP r.8(3) obligation that would stop running with no error | **fixed**: `settings.JOB_LOCK_TIMEOUT` (15 min) makes a stale lock claimable, in both the candidate query and the compare-and-swap. Reclaim-and-run, the timeout boundary, and no-resurrection-of-completed-or-failed are all `VERIFIED HERE`. The §4.3 deviation is acceptable only **with** this: a `locked_by` column without expiry is strictly weaker than the mechanism it replaced |
| 4.4 | Savepoints (used by `record_audit`'s retry and `idempotent()`) | supported | supported; `VERIFIED HERE` — an inner `IntegrityError` rolls back to the savepoint and the outer transaction stays usable | `VERIFIED HERE / ASSUMED THERE` |
| 4.5 | `audit_log.prev_hash UNIQUE` keeping the hash chain linear under concurrent appenders | the intended mechanism: the loser of a race fails the unique insert and retries against the new head | the uniqueness is enforced (`VERIFIED HERE`), but the race it exists for **cannot happen locally** because there is one writer | mechanism `VERIFIED HERE`; the concurrency property it buys is `UNVERIFIED` |
| 4.6 | Advisory locks | available | none | not used; ADR-001 §2.2 and API-CONTRACT §4.3 both forbid application-level locking |

---

## 5. The double-booking guard — the property that matters most, stated precisely

`DATA-MODEL.md` §5 and `API-CONTRACT.md` §4.3 make one claim:

```sql
CREATE UNIQUE INDEX one_active_transfer_per_listing
  ON transfers (listing_id)
  WHERE state IN ('ACCEPTED','SCHEDULED','AWAITING_CONFIRMATION','DISPUTED');
```

> "A concurrent second accept violates the index and the service returns
> `409 LISTING_ALREADY_RESERVED`. No application-level locking, no advisory
> locks, no race."

### 5.1 What is verified on this machine, and on which engine

Everything in this subsection was run on **SQLite 3.45.1**, in
`tests/unit/test_partial_unique_index_engine.py`:

| Assertion | Result |
|---|---|
| the engine supports partial indexes at all (`supports_partial_indexes`) | **True** |
| a partial unique index with an `IN (...)` predicate rejects a **second INSERT** of an active row for the same `listing_id` | rejected |
| it rejects an **UPDATE** that moves a second row *into* an active state — the path `accept_offer` actually takes (`OFFERED → ACCEPTED`) | rejected |
| each of the four active states collides individually (parametrised) | all four rejected |
| many `OFFERED` / `DECLINED` / `CANCELLED` rows per listing remain legal | legal |
| a transfer leaving the active set frees the listing for a new active transfer (the relist path) | succeeds |
| Django's `UniqueConstraint(condition=...)` renders a `CREATE UNIQUE INDEX ... WHERE ...` on this backend rather than dropping the condition | `WHERE` present |
| a Django `condition=` index **really reaches this database**: `jobs_due_idx` in the live schema reads `CREATE INDEX "jobs_due_idx" ON "jobs" ("run_after") WHERE ("completed_at" IS NULL AND "failed_at" IS NULL)` | confirmed |

So: **the index shape is correct, Django emits it faithfully, and the
predicate semantics are right — on SQLite.**

### 5.2 What is NOT verified, anywhere

1. **None of the above has been run on PostgreSQL.** There is no Postgres
   server on this machine. The Postgres behaviour of a partial unique index is
   well-established, and I expect it to match — but **that is an expectation,
   not a test result, and this document will not launder it into one.**
2. **The constraint does not exist.** `transfers` is an S4 table. There is no
   `transfers` table, no `one_active_transfer_per_listing` index and no
   `accept_offer`. §5.1 verifies the *engine capability the guard will rest
   on*, deliberately named
   `tests/unit/test_partial_unique_index_engine.py` rather than
   `test_double_booking.py` so nobody mistakes one for the other.
3. **The concurrency claim is the part SQLite cannot test even in principle.**
   `tests/api/test_double_booking.py` (S4, `THREAT-MODEL.md` §6) fires N
   concurrent accepts and asserts exactly one 2xx and N−1 `409`s. On SQLite
   there is one database writer, so the N−1 losers would be serialised by the
   **database-level write lock**, not by the index. Worse, a concurrent SQLite
   writer typically fails with `OperationalError: database is locked`, not with
   an integrity error — so a run on SQLite could show "exactly one success"
   while never once exercising the unique-violation path the service converts
   into `409 LISTING_ALREADY_RESERVED`. **A green `test_double_booking.py` on
   SQLite would be close to meaningless, and arguably worse than no test,
   because it would read as evidence.**
4. **The exception class differs** (§3.8). On Postgres a unique-index violation
   is `IntegrityError` (SQLSTATE `23505`) — the same class SQLite gives — so
   `accept_offer`'s `except IntegrityError → 409` is expected to be correct on
   both. This is the one place where the class does *not* diverge; the
   divergence in §3.8 is about `RAISE EXCEPTION` in a **plpgsql trigger**, not
   about index violations. Keep the two apart.

### 5.3 The instruction that follows from this

**`tests/api/test_double_booking.py` must refuse to run on SQLite.** When S4
writes it, it should `pytest.skip` with "requires PostgreSQL: the concurrency
this asserts cannot occur on SQLite (ENGINE-DIVERGENCE.md §5.2)" rather than
pass. A skipped test tells the truth; a green one does not. The same applies to
any future test whose subject is a race.

**Preventing double-booking is the single most important correctness property
in BookHop, and as of the end of S0 it is implemented nowhere and verified
nowhere. That is correct for S0 — it is S4's work — but it must not be read as
anything else.**

---

## 6. SQL and extensions later slices need, which SQLite cannot provide at all

Recorded now so no slice discovers it mid-build. All `UNVERIFIED` locally by
definition: they cannot run here.

| Slice | Needs | SQLite | Consequence |
|---|---|---|---|
| S1 | `citext` for `users.email` | absent | normalise in the service layer (see §2.9) |
| S1 | `gen_random_uuid()` as a column DEFAULT (`users.person_pseudonym`) | absent | generate in Python (`default=uuid.uuid4`), which works on both; the DB-side default in `DATA-MODEL.md` §2 will not exist on SQLite |
| S2 | `pg_trgm` + `GIN (title_norm gin_trgm_ops)` | absent | the trigram index cannot be created locally. The migration must branch, and **title search relevance is untestable on this machine**; exact ISBN-13 lookup is testable |
| S3 | trigram similarity ranking (`API-CONTRACT.md` §5.3) | absent | S3's ranking tests are Postgres-only. The gate and pagination tests are not |
| S7 | `percentile_cont(...) WITHIN GROUP`, `date_trunc`, `interval`, `::numeric`, `NULLIF` — i.e. **all of `DATA-MODEL.md` §9's queries** | absent or different | **`apps/analytics/sql/**` cannot run on SQLite at all.** Every metric view, the §9.2 repeat-transfer query, the §9.3 match rate and the §9.4 support-minutes queries are Postgres-only. S7 cannot be verified on this machine in any form |
| ADR-002 §6 step 2 | row-level security | absent | post-v1 |
| ADR-002 §6 step 4 | declarative range partitioning | absent | post-v1 |

**This is the strongest single argument for getting a local Postgres before
S7, and a reasonable one for getting it before S2.**

---

## 7. Test-harness divergences

| # | Thing | Note |
|---|---|---|
| 7.1 | `TransactionTestCase` / pytest-django's `transactional_db` | **Corrected 2026-10-21 (REVIEW-S0 M5). v1.0 of this row said the opposite and would have sent a future developer the wrong way.** Django flushes with `DELETE` on SQLite, which the append-only trigger correctly refuses, so those fixtures are unusable with `audit_log` rows locally — that part was right. The claim that "on Postgres, flush uses TRUNCATE, which row triggers do not see, so the same test would tear down cleanly there" **contradicted §3.6 in the same commit**: §3.6's whole purpose is that TRUNCATE no longer passes. Django 5.2's `postgresql.DatabaseOperations.sql_flush` emits `TRUNCATE "t1", "t2", …;` (read from the installed source), so with 0002 applied, **every `transactional_db` teardown on Postgres raises `audit_log is append-only`** — and §5.3 requires `tests/api/test_double_booking.py` to be transactional *and* to run on Postgres, so the collision lands exactly on the most important correctness property in the system. At that moment the tempting fix is deleting the guard §3.6 calls the most important unverified thing S0 shipped. **Resolution, chosen before a Postgres box exists rather than discovered on one:** migration 0003 redefines both TRUNCATE guards to return without raising when `current_setting('bookhop.allow_flush', true) = 'yes'`. `current_setting(..., true)` yields NULL when unset, so the default is to raise. UPDATE and DELETE get no escape — only the whole-table flush, which is what the harness needs and what an attacker does not. **The session fixture that does this is `tests/conftest.py::allow_test_flush`**, session-scoped and `autouse`, a no-op on SQLite. **Corrected again, 2026-10-21 (QA-S0 F9): v1.1 called the fixture mandatory and did not write it** — `bookhop.allow_flush` appeared in exactly one file in the repository, the migration — so the first Postgres run would have failed in teardown after all. It exists now. **And the second correction, which is a claim withdrawn rather than a bug fixed:** an earlier report of mine said a test asserts this GUC cannot be set under production settings. **No such test exists and none could.** A custom GUC is settable by any role in any session and `current_setting` reads whatever that session set; Django settings have no say in it. So the escape is gated by nobody, and the honest control is not a setting production forbids but **THREAT-MODEL §4 B5/B6's accepted scope: direct SQL is out of scope, addressed by privilege separation and `personal_data_access_log`, not by this trigger.** What the guard does buy is real and narrower than it read: it stops Django's own `sql_flush` and an accidental `TRUNCATE`. It does not stop a determined session, and §3.6 should be read with that bound. `UNVERIFIED` — no Postgres server here. Use `django_db` (transaction rollback) wherever a race is not the subject; the rule is in the docstring of `tests/unit/test_audit_append_only.py`. |
| 7.2 | `connection.schema_editor()` | SQLite's schema editor refuses to start inside a transaction, and pytest-django runs every test in one. `test_django_uniqueconstraint_condition_compiles_to_a_partial_index` therefore instantiates the editor without entering it and only renders SQL. On Postgres the context manager would work normally. |
| 7.3 | `LIKE` case sensitivity | Measured: on SQLite `'Algebra' LIKE '%alge%'` is **true** — `LIKE` is case-insensitive for ASCII by default. On Postgres `LIKE` is case-sensitive and `ILIKE` is not. **So Django's `__contains` behaves like `__icontains` locally.** A search test that passes here can fail in production. Relevant from S2. |
| 7.4 | Text collation / `ORDER BY` | Measured: `'a' < 'B'` is **false** on SQLite (BINARY). Postgres uses the database's collation, typically making it true. Any ordered list rendered to a user, and any cursor pagination keyed on a text column (`API-CONTRACT.md` §2.3), can order differently on the two engines. v1's cursors sort on `published_at`/`id`, so this is latent. |
| 7.5 | The `engine` fixture | `tests/conftest.py` exposes `connection.vendor`, and the tests whose meaning depends on the engine print or assert it, so a CI log says which engine an assertion ran on. |

---

## 8. Deviations from the frozen contracts introduced by S0, in one list

Not divergences between engines — places where the code does not match a
frozen document. Each is here rather than silently in a commit.

1. **Python 3.11.9, not 3.12** (ADR-001 §2.1). The machine has only 3.11.9.
   Django 5.2 supports 3.10–3.13, so nothing is lost; the production box should
   still be 3.12. **Low risk, stated for completeness.**
2. **`campuses.email_domains` is a jsonb/TEXT list, not `text[]`**
   (`DATA-MODEL.md` §1). §2.1. Needs a cto decision.
3. **Job claiming is a conditional UPDATE, not `SELECT ... FOR UPDATE SKIP
   LOCKED`** (ADR-001 §2.4). §4.3. Same guarantee, different SQL.
4. **No DB-side `DEFAULT now()`** on timestamp columns (`DATA-MODEL.md` §0).
   §2.6. Identical behaviour on both engines.
5. **`/readyz`'s third check is "no job overdue by more than 5 minutes", not
   "last job run < 5 min ago"** (`API-CONTRACT.md` §5.8). There is no scheduler
   on this machine to produce a heartbeat, so the literal check would report
   not-ready forever. Noted in the code with its upgrade path (S8).
6. ~~**`bookhop/urls.py` wraps `include("web.urls")` in a
   `try/except ModuleNotFoundError`**~~ — **withdrawn.** REVIEW-S0 N4 is right
   that the declared ceiling (a genuine `ImportError` inside `web.urls`
   swallowed as "not there yet" — a silent outage of the entire student-facing
   surface) was avoidable for the same two lines. It is now
   `importlib.util.find_spec("web") is not None`, which asks the one question
   that matters and lets a real import error propagate. **Nothing is left to
   delete later**, so `bookhop/urls.py` is not touched again (TASKS §1). A
   deletion that depends on someone remembering is the same bet the original
   comment apologised for.
6a. **`idempotency_keys` carries a second unique index** that `DATA-MODEL.md`
   §5 does not specify: partial, on `key` alone, WHERE `user_id IS NULL`
   (§3.4). It is an **addition that makes the stated semantics true** for
   anonymous callers rather than a relaxation, so it is recorded rather than
   escalated — but cto should fold it into §5 so the contract and the code stop
   disagreeing, and should settle the API-CONTRACT §4.1 question QA-S0 B3
   actually raises: whether anonymous POSTs carry a key at all.

6b. **The W1 whitelist's non-monetary name list matches bare names as well as
   suffixes**, and adds one word, `status`. ADR-003 §2.3 W1 states the list as
   suffixes only (`_count`, `_seconds`, …), and as literally written it rejects
   `jobs.attempts`, `listing_photos.width`/`height`/`bytes`,
   `support_work_log.seconds`, `search_result_opens.position` and
   `idempotency_keys.response_status` — six columns `DATA-MODEL.md` mandates,
   which would have reproduced M2 in a new place. None of those names can hold
   a consideration, so this is a wording clarification rather than a widening of
   the money allowance; it is escalated as §9 item 6 and the alternative
   (`DECLARED_NON_MONETARY`, an exact `(table, column)` allowlist) is present
   and empty so the narrower route stays available.

7. **`seed_demo` does not create the staff user or the `is_seed` students**
   that `TASKS.md` §2 S0 lists, because `users` is an S1 table. The command
   prints that it did not. Consequently **`TASKS.md` S0's "done when
   `seed_demo` produces a browsable-by-staff dataset" is not met and cannot be
   met before S1/S2** — there are no users and no listings to browse.

---

## 9. Escalations

1. **To cto — `campuses.email_domains`.** `DATA-MODEL.md` §1 specifies
   `text[]`. Implemented as a JSON list so one migration serves both engines
   (§2.1). Either amend the contract, or accept a per-engine field and two
   migration paths, or require a local Postgres. **My recommendation: amend the
   contract to `jsonb`.** The only operation is membership, the data is a short
   list of domains, and `jsonb` is the type that exists on both engines.
2. **To cto — ADR-001 §2.4's job-claiming mechanism.** `SELECT ... FOR UPDATE
   SKIP LOCKED` is silently a no-op on SQLite, so I used a compare-and-swap
   UPDATE (§4.3). The at-least-once and single-claim properties are unchanged.
   Asking for a one-line amendment rather than carrying an undocumented
   divergence.
3. **To cto / founder — a local PostgreSQL 16 is needed, and the trigger is
   earlier than it looks.** Nothing is blocked today. But:
   - **before S2**, because P14's price-immutability trigger (ADR-003 §2.2) is
     plpgsql and §3.9 is the whole of its verification today;
   - **before S4**, because §5 is the double-booking guard and a SQLite run of
     `test_double_booking.py` is not evidence;
   - **before S7**, because none of `DATA-MODEL.md` §9's SQL can execute on
     SQLite (§6).
   Cost is Rs 0 — Postgres 16 runs natively on Windows without Docker — so this
   is an installation decision, not a spend decision. **Until it happens, the
   Postgres halves of both append-only triggers (§3.5, §3.6, §3.7) are
   unexecuted text, and that is the largest unverified thing S0 shipped.**
4. **To test-qa.** Two instructions that come out of this document:
   (a) any test whose subject is a race must skip on SQLite rather than pass
   (§5.3); (b) catch `django.db.DatabaseError`, not `IntegrityError`, when
   asserting that a trigger fired, because the class differs by engine (§3.8).
5. **To code-review.** The checks this document makes mechanical: a new
   migration that contains vendor-branching SQL must add its row to §3; a new
   column type from §2 must add its row; and a test asserting a concurrency
   property must say which engine it ran on.
6. **To cto — ADR-003 §2.3 W1's non-monetary name list.** See §8 item 6b. It
   rejects six columns `DATA-MODEL.md` mandates as written. Asking for the
   suffix-or-bare reading plus `status` to be stated in the ADR, so the guard
   and the schema stop needing a developer's judgement to reconcile.
7. **To cto — ADR-003 §5.3's residual exposure, which should be written into the
   ADR rather than left in a test docstring.** The whitelist closes every
   *named* and every *typed* escape that QA-S0 F1 demonstrated: 20 of its 22
   attack shapes are caught, including `transfers.cash_handed_over`,
   `transfer_settlements.cash_total`, `settlements.amount_minor`,
   `receipts.total_inr` and `asking_price_paise` declared `real` or `numeric`.
   **Two are not closable by any schema or source control and should be stated
   as accepted residual exposure, not as covered:**
   - a `jsonb`/text document can hold `{"paid": 30000}` (`jobs.payload`, and
     from S3 `notifications.payload`);
   - a free-text column can hold "Paid Rs 300" (`transfers.handover_note`);
   - and a third, from QA's attack 8: a Python `@property settled_price`
     changes zero columns and is invisible to every assertion here.
   The honest compensating controls are the product ones the PRD already has —
   EX-18's "no in-app 'how much did you pay?' field, anywhere, in any optional
   form" — plus `tests/unit/test_forbidden_response.py`, which ADR-003 §2.3 and
   THREAT-MODEL §6 both name and **which still has no owning slice**
   (REVIEW-S0 N2). A named control with no owner is never written; it is also
   the compensating control for the jsonb limb, so the two escalations are the
   same escalation.
9. **To cto — `MONEY_TOKEN_SHAPE_EXEMPTIONS`, and it is an allowance, so it is
   escalated rather than claimed as obvious.** W1b's 22 tokens are all enforced
   now, which is a tightening and needs no escalation. But two of them collide
   with names three frozen contracts mandate, and the collisions are not
   hypothetical:
   - **`due`** appears in every SLA clock in the schema —
     `listings.purge_due_at`, `transfers.purge_due_at`,
     `reports.acknowledge_due_at` / `act_due_at` / `disposal_due_at`,
     `data_subject_requests.due_at`, `disputes.sla_due_at`,
     `legal_notices.act_due_at`, `grievances.disposal_due_at` and more: about
     fifteen columns, from S1 onward.
   - **`sum`** is inside `consume_magic_link`, which **API-CONTRACT §3 freezes**
     and which W1c's source grep reads.
   Enforcing the bare tokens would turn the P14 guard red on contract-mandated
   names with the tempting fix being an edit to a founder-escalating file under
   schedule pressure — **REVIEW-S0 M2 recreated, which is the counterfactual cto
   used to ratify `status`.** So three shapes are exempted — `due_at`,
   `overdue`, `consume` — each answered against the ADR's own discriminating
   question (a deadline, a backlog state and a verb; none can denote a
   consideration), and
   `test_the_token_shape_exemptions_cannot_swallow_a_known_attack` proves
   `amount_due`, `due_paise`, `due_inr`, `total_due`, `sum_paise` and `cash_sum`
   all still fail. **Where the name was ours, it was renamed rather than
   exempted:** `run_due_jobs` is now `run_pending_jobs`. Asking for the three
   shapes to be stated in ADR-003 §2.3 W1b, or refused with a direction.
10. **To test-qa — twelve of your tests now fail because the defect they
   characterise is fixed, and none needs a change on my side.** Eight in
   `test_gate_journey.py` create an incomplete `gate='C'` authorisation, which
   migration 0005 now refuses at the INSERT (F8) — they want
   `pytest.raises(DatabaseError)`, or a complete row where the point is the
   command's printed checklist. Three in `test_idempotency_contract.py` use a
   short anonymous key or expect a replayed body (F10). One,
   `test_migration_guards.py::test_no_test_in_the_repository_sets_the_flush_escape`,
   asserts that nothing sets `bookhop.allow_flush` — `tests/conftest.py` now
   does (F9), which is what §7.1 asked for.
12. **To cto — `DATA-MODEL.md` §5 needs one line for migration 0004's partial
   index**, which is the amendment I owe you a prompt for rather than an edit.
   §5 specifies `idempotency_keys` with `UNIQUE (user_id, key)`. The shipped
   schema also has a **partial unique index on `key` alone WHERE
   `user_id IS NULL`**, because that is what closes QA-S0 B3: NULLs are
   distinct on both engines, so an anonymous POST never deduped. It is an
   addition that makes §5's stated semantics true rather than a relaxation, and
   it is now load-bearing for F10's disclosure fix too. **The §4.1 question
   underneath it is still cto's:** whether anonymous POSTs carry an
   `Idempotency-Key` at all, and if they do, that it must be a UUID — which the
   code now enforces and the contract still only argues.
13. **To cto — one filename in `TASKS.md`.** S1's first commit names W1c's
   source grep `tests/unit/test_no_money_shaped_source.py`. It shipped in S0 as
   `tests/unit/test_forbidden_source.py`, and **test-qa's
   `tests/contract/test_p14.py` already imports that module path in three
   places and those tests are green.** I did not rename it: turning three of
   QA's passing tests red to match a filename is the wrong direction for a
   one-line correction. Either name is fine; the contract and the repository
   should agree on one.
14. **To cto — ADR-002 §4.1(b), two sentences, both now true and neither
   written.** The reviewer's C2 asks for the first and C1 for the second.
   (a) **A gate C authorisation is written complete or not at all.** Migration
   0005 refuses an incomplete INSERT, so the workflow §4.1(b) describes — a
   stored row whose checklist the command reports on item by item — cannot
   happen; the only reachable incomplete state is "no row". The per-item
   checklist is a pre-flight affordance, and an operator assembling evidence
   over days holds it outside the database until it is complete. I agree with
   the invariant and not with leaving it undocumented.
   (b) **`authorised_by_human` is checked for presence, not for truth.** It must
   now contain at least one visible character — twelve blank forms are refused
   by the database and the Unicode-category test above it refuses the ones the
   database's enumerated list does not know — but `'TODO'` is still a name as
   far as the system is concerned, and the go/no-go packet should say so.
11. **To test-qa — one thing to keep in mind when you re-measure.** The
   command's per-evidence-item branch is now unreachable from the database,
   because an incomplete authorisation cannot be saved. That is the control
   working, not the checklist becoming pointless: it is what tells an operator
   *which* item to go and get, with its Gate number. It is tested directly, on
   an unsaved row, via `checklist(campus, auth=...)`.
8. **To test-qa — two of your tests now fail because the defect they
   characterise is fixed, and one errors for the right reason.**
   `test_the_same_key_on_a_different_endpoint_is_still_the_same_key` (M3),
   `test_finding_an_anonymous_request_gets_no_idempotency_at_all` (B3),
   `test_demonstration_a_dob_column_passes_the_shipped_control` (F2a),
   `test_p14_is_not_guaranteed_by_naming` (F1 — it measures QA's own
   transcription of the deny-list, not the shipped control; the shipped control
   now catches four of the shapes it lists) and
   `test_finding_an_inactive_campus_can_still_have_an_open_gate` (B1) all
   assert the old behaviour. And
   `test_the_gate_column_cannot_be_opened_outside_the_authorised_command` now
   **raises** `DatabaseError` on the ORM update rather than silently not
   persisting, so it errors instead of passing: the guard fails loud, which is
   the correct behaviour, and the test wants
   `pytest.raises(DatabaseError)` around the update. Its final assertion —
   that the column is still NULL and no audit row was written — holds.

---

## Amendment log

| Date | Change | By |
|---|---|---|
| 2026-10-21 | v1.0 — written during S0, from measurements on SQLite 3.45.1 / Django 5.2.8 / Python 3.11.9, with no PostgreSQL server available | backend-developer |
| 2026-10-21 | **v1.3 — closing pass, REVIEW-S0 C1.** A trim-based blank check is a whitespace deny-list, and four characters was not the list: vertical tab, form feed, **NBSP (a paste from Word)**, figure space and ogham space passed the database floor while the command above it blocked them, and **zero-width space and BOM passed both layers** — so the one field carrying "a named human signed this" could be satisfied by something that renders as nothing in the go/no-go packet. Migration 0005's set is now eleven codepoints, each with its reason, and **the invariant itself** — at least one visible character, asked of Python's Unicode database per character and therefore needing no list — is in `open_discovery.has_visible_character`, which also catches five invisibles the SQL list does not know. The asymmetry and its ceiling are declared in the migration: neither engine can express the test (SQLite has no regex, Postgres's `[[:graph:]]` is locale-dependent), so the floor enumerates and the layer above generalises. Also: `tests/unit/test_forbidden_response.py` written (P14 at the contract boundary — the compensating control for the jsonb and free-text limbs, named by ADR-003 §2.3 and ownerless for two review rounds). Escalations 12–14 added | backend-developer |
| 2026-10-21 | **v1.2 — second S0 rework, after QA-S0 v2.0.** §7.1 **corrected a second time**: v1.1 called the flush fixture mandatory and did not write it, and a claim of mine that a test asserts the GUC cannot be set under production settings is **withdrawn — no such test exists and none could**; the honest control is THREAT-MODEL §4 B5/B6's accepted scope, and `tests/conftest.py::allow_test_flush` now exists. New row §3.6c (the gate evidence checklist moves into the database, F8); §3.4 extended again (the anonymous key format and the replayed body, F10 — a demonstrated disclosure). P14's lists move to `apps/core/p14.py` (W1d) with W1c's source grep in `tests/unit/test_forbidden_source.py`; all 22 W1b tokens enforced over **every** column in **any** type, and the exemption scoped to two columns instead of the `listings` table (F6/F7). Escalations 9–11 added | backend-developer |
| 2026-10-21 | **v1.1 — S0 rework after REVIEW-S0 and QA-S0.** §7.1 **corrected**: it asserted the opposite of the truth and contradicted §3.6 (M5); the TRUNCATE guards gain one declared session escape so a Postgres test harness and the append-only guarantee can coexist. New rows: §3.6a (`ENABLE ALWAYS`), §3.6b (the gate column's write guard, M0), §3.8a (float money is now checked by type, not named), §4.3a (job lock expiry, M4), and §3.4 extended (anonymous idempotency, QA-S0 B3). Deviation 6 **withdrawn** (`find_spec` replaces the `try/except`); deviations 6a and 6b added. Escalations 6–8 added | backend-developer |
