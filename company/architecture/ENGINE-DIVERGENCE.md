# ENGINE-DIVERGENCE.md — SQLite (dev) vs PostgreSQL 16 (production)

**Owner:** backend-developer · **Version:** v1.5 · **Date:** 2026-10-22

> **v1.4: a PostgreSQL 16.15 server now exists and every `UNVERIFIED` label
> below has been executed against it.** Read §10 first — it is the result of
> that run, including the three things this document got wrong and the two
> defects the run found in shipped S0 code. Rows elsewhere still carry their
> pre-run labels where §10 does not supersede them; where §10 contradicts a
> row, **§10 is the measurement and the row is the expectation.**
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
changes that.** But the machine S0 was built on had **Python 3.11.9 and neither
PostgreSQL nor Docker installed** (**PostgreSQL 16.15 was installed on
2026-10-21, with the founder's approval — see §10; this section describes the
conditions S0 was written under, which is why the labels below exist**), and installing system software is the
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

- ~~`manage.py sqlmigrate` against the Postgres backend **fails at connect**~~ —
  **superseded v1.4.** A server exists. And `sqlmigrate` was never the route:
  these are `RunPython` operations, so it prints *"THIS OPERATION CANNOT BE
  WRITTEN AS SQL"* on both engines regardless of connectivity (measured for
  0002, 0003, 0005). The installed DDL is read from the catalog instead —
  `pg_get_functiondef`, `pg_trigger.tgenabled` — which is better evidence,
  because it is what the server kept rather than what we sent. §10.6.
- ~~Every `plpgsql` body in a migration is **unexecuted text**.~~ **Superseded
  v1.4:** all five bodies are created, and every refusal branch inside them has
  been executed with its message text asserted — which is the stronger claim,
  because `check_function_bodies` only ever checked their syntax. §10.4 item 1.
- `apps/core/migrations/0002_append_only_triggers.py` branches on
  `schema_editor.connection.vendor` and writes the same guarantee twice. The
  SQLite half is exercised by the test suite. ~~The Postgres half is not
  exercised by anything.~~ **Superseded v1.4** — and the Postgres half did not
  parse at all on first contact: §10.1.

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
| 2.8 | `integer` money, **no float money ever** (ADR-003 §2.1) | **CORRECTED v1.4 (§10.2):** measured — a float into `integer` is **silently ROUNDED**, not rejected (`300.75` → `301`, `pg_typeof = integer`). A non-numeric string *is* rejected (22P02). So the engine guarantees no float is ever *stored* and reports nothing; detection is the service layer's, not the database's — §9 item 16 | **a float stays a float**: `300.75` inserted into an `integer NOT NULL` column came back as `typeof = 'real'`, value `300.75`. A string `'12abc'` came back as `typeof = 'text'` (measured) | **This one is worth reading twice.** The "integer paise, never float money" rule is enforced by the *Postgres* type system, by the Python service layer, and by ADR-003's CHECK — but **not** by the local engine. A float-money bug in S2 would pass the local suite. Mitigation in S2: the service layer must coerce and validate, and the CHECK bound (`>= 0 AND <= 10000000`) is enforced on both. | `VERIFIED HERE` (SQLite does **not** enforce it) / Postgres behaviour `UNVERIFIED` |
| 2.9 | `citext` (`users.email`, S1) | `citext` extension: case-insensitive uniqueness in the engine | would need `COLLATE NOCASE` or a lowercased column | **S1 blocker, flagged now.** `UNIQUE(email)` must be case-insensitive or `Student@x.edu` and `student@x.edu` become two accounts. On SQLite the plain unique index is case-**sensitive**: `'a' < 'B'` evaluated to false, i.e. BINARY collation (measured). S1 must either normalise the address in the service layer (works on both, recommended) or accept that the property is Postgres-only. | `UNVERIFIED` — not in S0 |
| 2.10 | `bigint GENERATED BY DEFAULT AS IDENTITY` (`DATA-MODEL.md` §0) | a sequence; values are never reused | `INTEGER PRIMARY KEY` = rowid alias (measured); **max rowid can be reused after the highest row is deleted** | Matters only for a table whose rows are deleted and whose ids are referenced elsewhere. `audit_log` cannot be deleted from, so the hash chain is unaffected. Noted for S1's purge work. | `VERIFIED HERE / ASSUMED THERE` |
| 2.11 | `boolean` | native `boolean` | integer `0`/`1` | **CORRECTED v1.4 (§10.2) — this row was wrong, and it had written the wrong reason down as deliberate.** `1`/`0` in the CHECK probe did not make it portable; it made it **not reach the constraint at all** on PostgreSQL: `DatatypeMismatch: column "seller_is_seed" is of type boolean but expression is of type integer`, raised before the CHECK is evaluated. The probe passed on SQLite comparing two integers in a column SQLite was not typing. Now `true`/`false`, understood by both engines, exercising a boolean column as a boolean. The underlying divergence (raw SQL written `WHERE flag = 'true'`) still stands. | `VERIFIED ON BOTH` (v1.4) |

---

## 3. Constraints and triggers

| # | Property | Postgres | SQLite here (measured) | Label |
|---|---|---|---|---|
| 3.1 | **`CHECK (col IN (...))` for every enum** (`DATA-MODEL.md` §0) | enforced | enforced; `supports_table_check_constraints = True` | `VERIFIED HERE / ASSUMED THERE` |
| 3.2 | **`CHECK (seller_is_seed = buyer_is_seed)`** — seed and real never transact (ADR-002 §4.1(c)) | enforced | the *mechanism* is enforced on INSERT **and** UPDATE: `tests/unit/test_seed_separation.py::test_check_constraint_mechanism_is_enforced_on_this_engine` builds a two-column CHECK of this exact shape and both violations raise | mechanism `VERIFIED HERE`; **the real constraint does not exist yet — `transfers` is an S4 table.** Until S4 nothing in this repository prevents a seed/real transfer, because nothing creates transfers |
| 3.3 | **Partial unique index** — the double-booking guard | see §5 | see §5 | see §5 |
| 3.4 | `UNIQUE` treats NULLs as distinct (`idempotency_keys UNIQUE(user_id, key)` with a NULL user) | NULLs distinct unless `NULLS NOT DISTINCT` is asked for, which we do not | NULLs distinct | identical by the SQL standard; `VERIFIED HERE / ASSUMED THERE`. **This identical behaviour was itself the defect** QA-S0 B3 found: an anonymous POST never deduped, so a replay claimed a second row instead of replaying the first, and API-CONTRACT §5.1/§5.6 have four anonymous POSTs. Closed in migration 0004 by a second, partial unique index on `key` alone WHERE `user_id IS NULL`, which puts anonymous keys in one global namespace — sound because the key is a client UUIDv4. Rejected alternatives and why are in `services.idempotent()`'s docstring. **Then QA-S0 F10 found the fix incomplete, and the gap was a disclosure rather than a hole in a guard:** a global namespace is safe only if the key is unguessable, and nothing checked the format, so `Idempotency-Key: 1` was legal — and on a matching body the second anonymous caller received the first's stored `response_body`, measured as `{"grievance_ref": "GRV-000123"}` reaching a stranger on the endpoint a distressed non-user reaches us through. Two changes: an anonymous key **must parse as a UUID** (else `400 VALIDATION_FAILED`), which makes API-CONTRACT §4.1's own argument true instead of assumed; and **an anonymous replay returns the status, never the stored body**, so no path exists on which one anonymous caller receives another's response. An authenticated replay is unchanged. `VERIFIED HERE` |
| 3.5 | **`audit_log` is append-only** (`DATA-MODEL.md` §8) — UPDATE and DELETE blocked | `BEFORE UPDATE OR DELETE` row trigger raising `RAISE EXCEPTION` | `BEFORE UPDATE` and `BEFORE DELETE` triggers raising `RAISE(ABORT, ...)`; six assertions in `tests/unit/test_audit_append_only.py` cover single-row update, single-row delete and whole-table delete | **VERIFIED ON BOTH v1.4** (§10.4) — the Postgres body now executes and its message text is asserted (`UPDATE`/`DELETE` interpolated from `TG_OP`), on both engines |
| 3.6 | **`audit_log` cannot be emptied by `TRUNCATE`** | row triggers **do not fire on TRUNCATE**, so migration 0002 adds a separate `BEFORE TRUNCATE … FOR EACH STATEMENT` trigger. Without it the §3.5 guarantee has a hole on Postgres that does not exist on SQLite. **Migration 0003 redefines it with one declared escape** — see §7.1, which v1.0 of this document got backwards | SQLite **has no `TRUNCATE` statement** at all — measured: `OperationalError: near "TRUNCATE": syntax error` — so there is nothing to block and nothing to test | **VERIFIED ON BOTH v1.4** (§10.4) — the hole was found by writing this document and **the fix is now measured**: `TRUNCATE audit_log` with the escape unset raises P0001 `audit_log is append-only: TRUNCATE is not permitted`, `TRUNCATE gate_authorisations` names its own table, and the inverse holds under the escape. §10.4 items 2 and 7 |
| 3.6a | **Triggers survive `session_replication_role = 'replica'`** | migration 0003 adds `ALTER TABLE … ENABLE ALWAYS TRIGGER` to all five guards. THREAT-MODEL §4 B5/B6 already accepts direct SQL as out of scope, so this is not a new exposure, but the replication-role route is one line to close and it matters for logical replication and for a restore | no equivalent and none needed | **VERIFIED ON BOTH v1.4** (§10.4) — all six triggers `tgenabled='A'`, all still refuse under `session_replication_role='replica'`, **with a negative control** showing a plain-enabled trigger is bypassed. Finding: role `bookhop` cannot set the role at all (42501) — the exposure is a restore or a replication worker, so `INFRA.md` §3.3 owns it (REVIEW-S0 N7) |
| 3.6b | **`campuses.discovery_enabled_at` has a write guard** — M0, the finding that blocked integration | `BEFORE INSERT OR UPDATE` row trigger (migration 0003): an INSERT must leave the column NULL; setting it to NULL is always permitted; setting it to a timestamp requires a live `gate = 'C'`, `scope_type = 'CAMPUS'`, `scope_id = NEW.id`, `revoked_at IS NULL` authorisation **and** `active = true` | the same rule as two `WHEN`-guarded triggers, one for INSERT and one for UPDATE. A subquery in a trigger `WHEN` clause works here — **measured**, because SQLite forbids subqueries in CHECK constraints and it was not safe to assume triggers behave the same. 11 assertions in `tests/unit/test_gate.py` | **VERIFIED ON BOTH v1.4** (§10.4) — every refusal and every permitted counterpart executed, including the inactive-campus refusal (QA-S0 B1) |
| 3.6c | **A `gate='C'` authorisation must carry its whole evidence checklist** (QA-S0 F8) | `BEFORE INSERT OR UPDATE` plpgsql trigger looping the six ADR-002 §4.1(b) evidence keys, with `jsonb_typeof` separating a blank string from an empty array | two `WHEN`-guarded triggers using SQLite's JSON1 (`json_extract`, `json_type`, `json_array_length`), which Django's JSONField already relies on here. **Measured and fixed while writing it:** both engines' bare `trim()`/`btrim()` strip spaces only, so a single tab passed as a named human — both bodies now pass an explicit whitespace set. 13 assertions | **VERIFIED ON BOTH v1.4** (§10.4) — all six keys refused by name, the empty-array branch fires specifically, `evidence` confirmed `jsonb` not `json`, all eleven invisible codepoints refused individually, `server_encoding = UTF8` with each codepoint round-tripped, and **the declared ceiling asserted as a ceiling** (U+2060 passes). The NULL path is refused by the *trigger*, not by `NOT NULL` — the CHECK-satisfied-by-NULL trap is real and avoided. §10.4 items 4-6. **The floor it raises is bounded and the bound is asserted**: it checks that every box is filled, never that any box is true (`campus_mou_ref = 'TODO'` still opens the gate — QA-S0 B2, ADR-002 §4.2) |
| 3.7 | **`gate_authorisations` permits no UPDATE except `revoked_at`/`revoked_reason`**, and no DELETE (`DATA-MODEL.md` §1) | row trigger comparing each immutable column with `IS DISTINCT FROM`, plus a `BEFORE TRUNCATE` statement trigger | `WHEN ... IS NOT ...` trigger plus a DELETE trigger; two assertions in `tests/unit/test_gate.py` (delete refused, `evidence` rewrite refused) | **VERIFIED ON BOTH v1.4** (§10.4) — DELETE refused, `evidence` rewrite refused, and `revoked_at`/`revoked_reason`-only UPDATE **succeeds** — the permitted counterpart, so the guard is not simply refusing everything |
| 3.8 | **The exception *class* a trigger raises** | **CORRECTED v1.4 (§10.2):** SQLSTATE `P0001` → `psycopg.errors.RaiseException` → **`django.db.utils.ProgrammingError`**, measured. Not `InternalError` — that was psycopg **2**'s mapping; in psycopg 3 `RaiseException` subclasses `ProgrammingError`. **The hazard this row warned about was real and the class it named was wrong**, so the mitigation in the next column is the only reason it cost nothing | `RAISE(ABORT, ...)` → `django.db.utils.IntegrityError` (measured) | **`VERIFIED HERE` for SQLite, `UNVERIFIED` for Postgres, and this one will bite someone.** A service that catches `IntegrityError` to convert a trigger failure into a 4xx will pass locally and **swallow nothing on Postgres**. Every test in this repository catches `django.db.DatabaseError`, the common parent, on purpose. S2's price-immutability handler and S4's `accept_offer` must do the same or branch explicitly |
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
| 4.5 | `audit_log.prev_hash UNIQUE` keeping the hash chain linear under concurrent appenders | the intended mechanism: the loser of a race fails the unique insert and retries against the new head | the uniqueness is enforced (`VERIFIED HERE`), but the race it exists for **cannot happen locally** because there is one writer | **VERIFIED ON POSTGRES v1.4, and it found a defect** (§10.3(a)): the race occurs, and the 4-attempt budget **dropped an audit row** at 12 concurrent appenders while reporting a broken chain. Budget now 12 with jittered backoff; 12/24/40 appenders all land and the chain verifies. The mechanism was right; its tuning had never met a second writer |
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
| 7.1 | `TransactionTestCase` / pytest-django's `transactional_db` | **Corrected 2026-10-21 (REVIEW-S0 M5). v1.0 of this row said the opposite and would have sent a future developer the wrong way.** Django flushes with `DELETE` on SQLite, which the append-only trigger correctly refuses, so those fixtures are unusable with `audit_log` rows locally — that part was right. The claim that "on Postgres, flush uses TRUNCATE, which row triggers do not see, so the same test would tear down cleanly there" **contradicted §3.6 in the same commit**: §3.6's whole purpose is that TRUNCATE no longer passes. Django 5.2's `postgresql.DatabaseOperations.sql_flush` emits `TRUNCATE "t1", "t2", …;` (read from the installed source), so with 0002 applied, **every `transactional_db` teardown on Postgres raises `audit_log is append-only`** — and §5.3 requires `tests/api/test_double_booking.py` to be transactional *and* to run on Postgres, so the collision lands exactly on the most important correctness property in the system. At that moment the tempting fix is deleting the guard §3.6 calls the most important unverified thing S0 shipped. **Resolution, chosen before a Postgres box exists rather than discovered on one:** migration 0003 redefines both TRUNCATE guards to return without raising when `current_setting('bookhop.allow_flush', true) = 'yes'`. `current_setting(..., true)` yields NULL when unset, so the default is to raise. UPDATE and DELETE get no escape — only the whole-table flush, which is what the harness needs and what an attacker does not. **The session fixture that does this is `tests/conftest.py::allow_test_flush`**, session-scoped and `autouse`, a no-op on SQLite. **Corrected again, 2026-10-21 (QA-S0 F9): v1.1 called the fixture mandatory and did not write it** — `bookhop.allow_flush` appeared in exactly one file in the repository, the migration — so the first Postgres run would have failed in teardown after all. It exists now. **And the second correction, which is a claim withdrawn rather than a bug fixed:** an earlier report of mine said a test asserts this GUC cannot be set under production settings. **No such test exists and none could.** A custom GUC is settable by any role in any session and `current_setting` reads whatever that session set; Django settings have no say in it. So the escape is gated by nobody, and the honest control is not a setting production forbids but **THREAT-MODEL §4 B5/B6's accepted scope: direct SQL is out of scope, addressed by privilege separation and `personal_data_access_log`, not by this trigger.** What the guard does buy is real and narrower than it read: it stops Django's own `sql_flush` and an accidental `TRUNCATE`. It does not stop a determined session, and §3.6 should be read with that bound. **VERIFIED v1.4, after a third correction — and this one was a bug, not a wording slip.** The fixture existed and still did not work: a session GUC lives on a *connection*, not on a pytest session, so a session-scoped `SET` bound it to whichever connection existed at setup and **any close reopened one without it**. Measured: one threaded test calling `connections.close_all()` was enough, and the next transactional test died in teardown on `TRUNCATE "cities", "jobs", …`. That is precisely the S4 collision F9 was written to prevent, and S4's `test_double_booking.py` triggers both halves. Now declared on Django's `connection_created` signal, so every connection gets it as it opens (§10.3(b)). The escape and its deny-by-default are measured in §10.4 item 7, and a `transactional_db` teardown is now exercised by `tests/unit/test_transactional_teardown.py` — **there was no such test before, so the whole suite said nothing about this.** Use `django_db` (transaction rollback) wherever a race is not the subject; the rule is in the docstring of `tests/unit/test_audit_append_only.py`. |
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
3. ~~**To cto / founder — a local PostgreSQL 16 is needed.**~~ **CLOSED
   2026-10-21: PostgreSQL 16.15 installed and approved by the founder, and §10
   is the result of the first run against it.** The original escalation, kept
   because the three dates it named are the reason it was granted:
   - **before S2**, because P14's price-immutability trigger (ADR-003 §2.2) is
     plpgsql and §3.9 is the whole of its verification today;
   - **before S4**, because §5 is the double-booking guard and a SQLite run of
     `test_double_booking.py` is not evidence;
   - **before S7**, because none of `DATA-MODEL.md` §9's SQL can execute on
     SQLite (§6).
   Cost is Rs 0 — Postgres 16 runs natively on Windows without Docker — so this
   is an installation decision, not a spend decision. ~~**Until it happens, the
   Postgres halves of both append-only triggers (§3.5, §3.6, §3.7) are
   unexecuted text, and that is the largest unverified thing S0 shipped.**~~
   **They are executed now, and the run was worth it before S2 rather than
   after: the migrations did not even apply (§10.1), and two defects in shipped
   code were found that no SQLite run could have reached (§10.3).**
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

15. **To cto — `audit_log.prev_hash UNIQUE` serialises every audit append, and
   that is a `DATA-MODEL.md` §8 property, not a constant I can tune.** §10.3(a)
   raised the retry budget from 4 to 12 with backoff, which stops a loser being
   dropped and stops it being reported as a tamper. It does not change the
   shape: a single linear chain means **every mutation in the system competes
   for one row**, and the loser's cost is a retry. At the pilot's write rate
   (2–3 campuses) the limit is far above load, which is why I fixed the budget
   and did not touch the design. Two upgrade paths, both yours: a **per-scope
   chain** so appends to different campuses do not compete, or **periodic
   checkpoint anchoring** instead of a per-row chain. Asking for a decision
   before S4, because S4 is the first slice with concurrent mutations on one
   object, not before S7.
16. **To cto — ADR-003 §2.1 should say which layer enforces integer paise.**
   §10.2 measured that PostgreSQL enforces it by **silently rounding** a float
   into an `integer` column (`300.75 → 301`), not by raising. So the sentence
   "the PostgreSQL type system enforces it" is true about *storage* and false
   about *detection*, and the only layer that can report a float-money bug is
   the service-layer coercion §2.8 already mandates for S2. One clause, so S2
   does not read the ADR as meaning the database will catch it.
17. **To test-qa — §7's nine assertions still need writing, and two of them
   should stay in your tree.** §10.6: the "skip → run" items have no body, so
   nothing converted. I executed §1 directly instead (§10.4). Two specifically
   belong to you rather than to me and I have deliberately not written them:
   `test_truncate_cannot_empty_the_audit_log` (the refusal needs the escape
   unset, naming it is the only way to unset it, and your own
   `test_the_flush_escape_is_declared_by_the_harness_and_nothing_else`
   inventories every file that names it — your tree is exempt by path, mine is
   not, and `CLAUDE.md` rule 13 says rename ours before widening yours), and
   `test_the_postgres_guards_actually_fire`. Also: **eight of your 25
   body-less skips now print a reason naming SQLite while running on
   PostgreSQL**, which is a skip that no longer tells the truth. And one
   observation on that inventory guard, offered rather than asked: its
   docstring says the question is "whether anything *sets* it" while the test
   is a flat substring match on the bare name in any file, including a comment
   or a docstring — `CLAUDE.md` rule 11's shape, where the next collision is
   resolved by editing the allowlist. A per-entry match rule (does this file
   *execute* a `SET`?) would survive a legitimate third reader.

---

## 10. The first PostgreSQL run — 2026-10-21, PostgreSQL 16.15

**What ran:** `POSTGRES-FIRST-RUN.md` §1 items 1–9, executed directly against
the server, plus the whole test suite on both engines. **95 direct assertions,
0 failures**, each asserting the SQLSTATE *and* the exception message text, not
just that the operation was refused — because
`check_function_bodies` validates plpgsql **syntax** at `CREATE FUNCTION` while
plpgsql resolves identifiers and operators at the **first execution of each
branch**, so a guard can be created cleanly and fail the first time anyone does
the forbidden thing, and the worst shape of that failure still *blocks* the
operation. Suite: **571 passed / 60 skipped on PostgreSQL, 573 passed / 58
skipped on SQLite**, three consecutive runs each, no flakes.

### 10.1 The blocker, and why the fix is not the obvious one

`migrate` from empty died on `core.0002` with
`psycopg.ProgrammingError: incomplete placeholder: '%'`. Four `%` characters in
plpgsql `RAISE` format strings (0002 ×2, 0003, 0005) are parsed by psycopg as
parameter placeholders before PostgreSQL sees them, because
`postgresql.DatabaseSchemaEditor.execute` merges params client-side **unless
params is None**.

**Fixed by passing `params=None`, not by doubling the `%`.** Doubling also
works — measured: `compose_sql("… %% …", ())` yields `… % …` — but it puts two
escaping layers under one message, and **getting it wrong is silent**: a
mis-doubled specifier leaves a literal `%` or `%%` in the message while the
guard still refuses the operation, so the refusal is indistinguishable and only
the text is broken. `params=None` removes the layer instead of escaping for it,
and is Django's own documented escape hatch for exactly this.

**The message text is now asserted, on both engines**
(`tests/unit/test_audit_append_only.py::test_the_append_only_message_names_the_operation_it_refused`):
`TG_OP` and `TG_TABLE_NAME` interpolate correctly, and no `%` survives into any
message. Measured text, read from the server:
`audit_log is append-only (DATA-MODEL.md section 8): UPDATE is not permitted`,
`… DELETE is not permitted`,
`audit_log is append-only: TRUNCATE is not permitted…`,
`gate_authorisations is append-only: TRUNCATE…` (its own table name),
`…missing or blank: counsel_engagement_ref` (and each of the other five keys).

### 10.2 Three predictions in this document that were WRONG

| # | This document said | Measured | Why it matters |
|---|---|---|---|
| **§3.8** | `RAISE EXCEPTION` → P0001 → `psycopg.errors.RaiseException` → **`django.db.utils.InternalError`** | **`django.db.utils.ProgrammingError`.** In psycopg **3**, `RaiseException` subclasses `ProgrammingError`; it subclassed `InternalError` in psycopg 2, which is where the prediction came from | **The hazard was real and the named class was wrong, so §3.8's own mitigation is what saved us.** Every test in the repository catches `django.db.DatabaseError`, the common parent, on purpose — so nothing broke. Had any caller been written to catch `InternalError` *on the strength of this row*, it would have swallowed nothing on PostgreSQL. **The instruction stands and is now the only correct one: catch `DatabaseError`.** `UniqueViolation` → `IntegrityError` is unchanged (23505), so §5.2 item 4 holds and `apps/core/services.py`'s two `except IntegrityError` handlers — the `prev_hash` retry and `idempotent()` — are both correct: both are unique-index paths, neither is a trigger. **No caller needed fixing** |
| **§2.11** | boolean divergence "only bites raw SQL written as `WHERE flag = 'true'`. The CHECK probe in `tests/unit/test_seed_separation.py` uses `1`/`0` **for that reason**" | `INSERT INTO _seed_probe VALUES (1, 1, 1)` raises `DatatypeMismatch: column "seller_is_seed" is of type boolean but expression is of type integer` — **before the CHECK is ever evaluated** | **A test that was passing for the wrong reason, and this document had written the wrong reason down as deliberate.** On SQLite it compared two integers in a column SQLite was not typing; on PostgreSQL it never reached the constraint. The only suite failure of the run. Fixed to `true`/`false`, understood by both engines, and it now exercises a boolean column *as a boolean* |
| **§2.8** | a float into an `integer` column is "rejected or rounded by the engine" | **Rounded, silently**: `300.75` into `integer` returns `301`, `pg_typeof = integer`. A non-numeric string *is* rejected (22P02) | **The direction matters for S2.** ADR-003 §2.1's "integer paise, never float money" is true in that no float is ever *stored* — but PostgreSQL enforces it by **silent rounding, not by an error**. So a float-money bug loses sub-paise precision with no signal on either engine, and §2.8's mandated service-layer coercion is the only layer that can report it. Not a relaxation of the rule; a correction to which layer enforces it |

### 10.3 Two defects in shipped S0 code, both invisible to SQLite

**(a) `record_audit`'s retry budget dropped audit rows.** The loop retried the
`prev_hash UNIQUE` race **4 times with no backoff**. Measured, 12 appenders on
12 real connections: one lost four straight races and **its audit row was
dropped** — and because `record_audit` is called inside the mutation's
transaction, that mutation fails. The attempts-to-win distribution's tail grows
with contention (a winner needed 5 attempts at 8 appenders, 7 at 24), so 4 was
already below the observed need at modest concurrency. **This race cannot occur
on SQLite — one database writer — which is exactly §4.1's warning cashing in.**
Fixed: budget 12, jittered backoff to decorrelate the herd (without it every
loser re-reads the same head and spends the budget on self-inflicted
collisions). Re-measured at 12, 24 and 40 appenders: all land, chain verifies.

The second half was a **diagnostic** defect of the shape `CLAUDE.md` rule 9
names. Exhausting the budget raised **`AuditChainBroken`** — a class whose name
asserts tampering, during an incident that establishes only write contention
and in which the chain is provably intact. A load spike would have sent an
operator hunting a tamper. Now `AuditAppendContention`, deliberately **not** a
subclass, so an alert on the broken-chain class does not fire on contention.
Regression test: `tests/unit/test_audit_chain_race.py`.

**(b) `tests/conftest.py::allow_test_flush` bound a per-connection setting to a
pytest session.** The escape is a session **GUC**: it lives on a *database
connection*. A session-scoped fixture that `SET` it once bound it to whichever
connection existed at session setup, and **any close reopened a connection
without it**. Measured: one test that used threads and called
`connections.close_all()` was enough, and the *next* transactional test died in
teardown on `TRUNCATE "cities", "jobs", …` with `audit_log is append-only`.

**That is the failure QA-S0 F9 and §7.1 exist to prevent, and it would have
landed on S4's `test_double_booking.py`** — which needs `transactional_db`
*and* several real connections to race at all, i.e. it triggers both halves.
Fixed by moving the declaration onto Django's `connection_created` signal, so
every connection gets it the moment it opens. A per-connection setting belongs
on a per-connection hook.

### 10.4 Items that PASSED, with what makes each non-vacuous

| Item | Result | The control that stops it passing vacuously |
|---|---|---|
| **0** · `migrate` from empty | **PASS** after 10.1. Five plpgsql bodies parse, six triggers and six `ENABLE ALWAYS` statements accepted | the failure was loud and total |
| **1** · every refusal path, message asserted | **PASS**, 68 assertions. Each guard's forbidden operation refused with SQLSTATE **P0001** and the stated text; each paired with its permitted counterpart (`UPDATE` of only `revoked_at`/`revoked_reason` succeeds; opening *with* a live authorisation succeeds; closing always succeeds; `gate='B'` is unconstrained) | a non-P0001 SQLSTATE is treated as a FAIL even though the operation was refused — that is the whole point of item 1 |
| **2** · `TG_OP` ordering on the statement-level TRUNCATE triggers | **PASS**. The intended message appears, **not** `record "new" is not assigned yet` | asserted as a string, so a future reorder of those two blocks turns it red instead of holding by accident |
| **3** · `ENABLE ALWAYS` under `session_replication_role='replica'` | **PASS**. All six triggers `tgenabled='A'`; all guards still refuse under `replica` | **negative control**: downgrading one trigger to plain-enabled and retrying shows the UPDATE **does** get through, so the assertions measure `ENABLE ALWAYS` and not something else. **Finding: role `bookhop` cannot `SET session_replication_role` at all (42501)** — the bypass is unreachable by the application role, so this had to run as `postgres`. The exposure is a restore or a replication apply worker, which is what `INFRA.md` §3.3 should assert |
| **4** · `chr()` and the database encoding | **PASS**. `server_encoding = UTF8`; all eleven codepoints round-trip (`ascii(chr(n)) = n`); the built set is exactly 11 characters | the round-trip is per codepoint, so a non-UTF8 database silently substituting one character fails on that character |
| **5** · `btrim` behaves as `btrim` | **PASS**, all four. Set semantics (`btrim('ab','ba') = ''`), ends-only (an interior ZWSP is untouched and the name **passes** — correct, it has visible characters), and **the NULL path is refused by the TRIGGER, not by `NOT NULL`**: the BEFORE trigger fires first and its `coalesce(btrim(NULL, ws), '')` catches it. **The CHECK-constraint trap is real and avoided** — bare `btrim(NULL, ws) IS NULL` measured, and a CHECK is *satisfied* by NULL, so the trigger form is load-bearing rather than incidental | all eleven invisible forms asserted individually, and **the declared ceiling asserted as a ceiling**: U+2060 WORD JOINER is not in the eleven and **passes** the database floor, exactly as the migration declares. The ceiling has not moved, and `open_discovery.has_visible_character` is still what generalises above it |
| **6** · `NEW.evidence -> k` against the real column type | **PASS**. `evidence` is **`jsonb`**, not `json`; the `jsonb_array_length` branch fires specifically on an empty `notice_version_ids`; an object-typed value is accepted by the `jsonb_typeof` branch | the empty-array refusal names *that key*, so the array branch is distinguished from the generic missing-key branch |
| **7** · the escape defaults to deny | **PASS**, five cases. Unset → refused; `'no'` → refused; **`'YES'` (wrong case) → refused**; `'yes'` → `TRUNCATE` **succeeds**; and Django's own multi-table `sql_flush` shape succeeds | the inverse is asserted, so the escape is proved to be an escape rather than dead code — and §10.3(b) is the proof that the *fixture* now reaches it |
| **8** · `idempotency_anon` under genuine concurrency | **PASS**. 12 threads, 12 real connections, barrier-released: exactly one winner for the anonymous partial index **and** for the authenticated composite index; exactly one row; no loser escaped as a raw database error. API-CONTRACT §4.1's *"the insert of the key row is the lock"* is verified under real contention for the first time | **negative control** for the Django trap: without a nested `atomic()` the transaction **is** poisoned (`TransactionManagementError`), and with `services.idempotent`'s own `atomic()` savepoint the loser's outer transaction survives — so the 409 is renderable. **This cannot happen on SQLite**, where the loser gets a lock error. `accept_offer` in S4 must keep that savepoint |
| **9** · forward and reverse from empty | **PASS**. Reverse 0005 → 0001 leaves **zero** triggers and **zero** functions; re-apply restores all six, all `A`. Triggers are dropped before their functions | the catalog is read after the reverse, not inferred from the migration exiting 0 |
| **§4.5** · the audit hash chain under concurrent appenders | **PASS after §10.3(a)** at 12, 24 and 40 appenders; `verify_audit_chain` confirms every row present and linear | the test asserts the **row count** as well as chain validity, because a lost row with no exception is worse than a raised one — nothing would signal it |

### 10.5 §2 and §7 predictions that were RIGHT, and were invisible to the suite

All four predicted behaviour changes are real at the engine level — and
**three of them produced no test failure, because nothing in S0 exercises
them.** That is not coverage; it is absence of subject matter.

| Row | Measured on PostgreSQL | Live from |
|---|---|---|
| §2.3 `uuid` | a malformed `actor_pseudonym` is rejected, 22P02 | S1 (`*_pseudonym`) |
| §2.4 `inet` | `'not-an-ip'` into `audit_log.ip` is rejected, 22P02 | S1 (`requested_ip`, `consents.ip`) |
| §2.7 `smallint` | `jobs.attempts` **is** `smallint`; `99999` is rejected, 22003 | now, latent |
| §7.3 `LIKE` | **case-SENSITIVE**: `__contains="likeprobe"` matches 0 rows where SQLite matched 1. `__icontains` matches | **S2** — `__contains` behaved like `__icontains` locally |
| §7.4 collation | `'a' < 'B'` is **True** here, **False** on SQLite | latent; bites any user-visible ordering or text-keyed cursor |
| §2.1, §2.6 | `campuses.email_domains` is `jsonb`; **zero** columns carry a `now()` default | deviations §8 items 2 and 4 confirmed identical on PostgreSQL; both still need cto |

### 10.6 A finding against `QA-S0.md` §7 itself

**§7's "*(skip → run)*" conversion cannot happen, for any of its items.** Those
tests have **no body**: each is a single unconditional `pytest.skip()` whose
reason is an f-string interpolating the live vendor into text describing SQLite.
**25 tests in the repository are shaped this way**; 8 name SQLite as the reason
and now print, on PostgreSQL, *"NOT VERIFIABLE ON THIS ENGINE
(vendor=postgresql …) because SQLite has no TRUNCATE statement"* — a skip
reason that names the wrong engine and no longer tells the truth. They are
honest placeholders on SQLite and self-contradicting on PostgreSQL.

This is `CLAUDE.md` rule 12 in a new shape, and it is why §1 of
`POSTGRES-FIRST-RUN.md` was executed directly rather than by unskipping.
`tests/e2e`, `tests/a11y` and `tests/contract` are test-qa's trees and were not
touched; **the nine assertions §7 promised still need writing, by QA, now that
the engine exists.** Two of them are reserved by name and have been executed
here in the meantime (§10.1, §10.4 items 2 and 7).

Also, and smaller: `sqlmigrate` **cannot** render any of this DDL on either
engine. §1 records that it "has never generated this DDL" and implies a server
would fix that; it would not. These are `RunPython` operations, so `sqlmigrate`
prints *"THIS OPERATION CANNOT BE WRITTEN AS SQL"* — measured for 0002, 0003
and 0005. The catalog (`pg_get_functiondef`, `pg_trigger.tgenabled`) is the
only way to read the installed DDL, and it is better evidence anyway: it is
what the server kept rather than what we sent.

### 10.7 What this run does NOT prove

`POSTGRES-FIRST-RUN.md` §2 applies in full and is not restated. The three worth
repeating here because they are most often misread as covered:

1. **Double-booking is implemented nowhere and verified nowhere.** §5 is
   unchanged by this run. The partial unique index is on `transfers`, an S4
   table; there is no table, no index and no `accept_offer`. §10.4 item 8 is a
   **rehearsal** of the same mechanism on a table that exists — a pass there
   predicts a pass there, and is not one.
2. **Nothing about `listings`:** no price-immutability trigger (it does not
   exist — there are **five** plpgsql bodies, not six), and no engine-level
   rejection of a float *value* in the one money column beyond §10.2's finding
   that the rejection is a silent rounding.
3. **Nothing about evidence being true.** `campus_mou_ref = 'TODO'` still opens
   the gate, and a plausible fake `authorised_by_human` still passes. Every box
   filled is still not every box true (ADR-002 §4.2, QA-S0 B2).

And one addition to §2's list, from §10.3(a): **nothing about behaviour at
scale.** The retry budget was raised from a measurement at 40 appenders on one
near-empty table. `prev_hash UNIQUE` makes every audit append serialise by
construction, and no retry budget removes that — see §9 item 15.

---

## 12. S1 — slice additions, with one measured defect SQLite found first

**Version v1.5.** S1 adds nine tables, one shared plpgsql body, twelve SQLite
triggers and a privilege layer. Every row is labelled per `CLAUDE.md` rule 17.

### 12.1 New rows

| # | Property | PostgreSQL 16.15 | SQLite 3.45.1 | Label |
|---|---|---|---|---|
| 12.1 | `users.email` as `citext` | available, not used | no `citext` type | **VERIFIED HERE.** Stored lower-cased in `text`, normalised by `accounts.services.normalise_email`. The deciding reason is not the missing type: **`LIKE` is case-sensitive on PostgreSQL and case-insensitive on SQLite**, so an `__iexact` lookup written locally changes meaning in production. `test_magic_link.py::test_no_service_function_uses_a_case_insensitive_lookup` is the guard |
| 12.2 | `personal_data_access_log.fields_accessed` as `text[]` | available | no array type | **VERIFIED HERE.** `jsonb` list, exactly as `campuses.email_domains` (DATA-MODEL §1 A-16). Only operation is membership |
| 12.3 | `user_tombstones.salt_version` | — | — | **Schema addition on `COMPLIANCE.md` §7 row 24's instruction**, not in DATA-MODEL §2's column list. Row 24 requires *"retire a version when no live tombstone references it"*, which is unimplementable without it. Raised to cto as a one-line §2 amendment |
| 12.4 | `bookhop_append_only_guard()` — one body, three tables | `TG_TABLE_NAME` + `TG_OP` in the message; SQLSTATE `P0001` | six separate `RAISE(ABORT, …)` triggers, no SQLSTATE | **VERIFIED HERE both engines.** Message asserted on both; SQLSTATE asserted on PostgreSQL and **skipped on SQLite with the engine and slice named** |
| 12.5 | The privilege layer (`core/0008`) | `REVOKE`/`GRANT` per table | **no role system at all** — no `GRANT`, no `REVOKE`, one process with full file access | **VERIFIED HERE.** There is no weaker form to apply, so the layer is **absent** on SQLite rather than approximated. `test_least_privilege.py` skips with that stated |
| 12.6 | A revoke binds the table's **owner** | **yes** — `has_table_privilege` false, `TRUNCATE` refused with *permission denied for table audit_log* | n/a | **VERIFIED HERE.** And the owner can `GRANT` it straight back **in one statement**, also measured — which is why `core/0008` is necessary and not sufficient, and why ownership separation is escalated rather than claimed |
| 12.7 | Rate limiting | one owned table, atomic `hit_count = hit_count + 1` | identical | **VERIFIED HERE both engines.** A deviation from ADR-001 §2.4, recorded in §12.3 |

### 12.2 The defect SQLite found and PostgreSQL could not — a new row in §10.3's family, pointing the other way

**Measured.** After `accounts/0003` widened `notice_versions.kind`'s CHECK
(DATA-MODEL A-25), `sqlite_master` listed **ten of twelve** expected triggers:
`notice_versions_no_update` and `notice_versions_no_delete` were **gone**.

**Why.** SQLite cannot alter a CHECK constraint, so Django's SQLite backend
rebuilds the table — create new, copy rows, `DROP TABLE` old, rename — and
**triggers belong to the table, so the drop takes them.** Nothing puts them
back. On PostgreSQL `ALTER TABLE … DROP/ADD CONSTRAINT` leaves triggers
untouched, so **the engine production runs on would never have reported it.**

For one migration, on one engine, `notice_versions` was an ordinary mutable
table while DATA-MODEL §2 said *"Trigger blocks all UPDATE and DELETE"* and
`COMPLIANCE.md` §8.1 rested *"we can show what a user agreed to on a given
date"* on it.

**The hazard is general and bigger than this table.** On SQLite **any** future
`AlterField`, constraint change or column rename on a trigger-protected table
silently removes its guard — `audit_log`, `gate_authorisations`, `campuses`,
`consents`, `age_verification_events`, `notice_versions`, and every append-only
table S4 and S5 add. A migration can be reviewed by two agents, applied cleanly,
and leave tamper-evidence switched off with no symptom at all.

**Fixed in two parts, and the second is the one that matters:**
`accounts/0004_restore_append_only_guards` re-creates them idempotently, and
`tests/unit/test_append_only_triggers_exist.py` asserts **on both engines** that
every table claiming append-only has its guard installed — so the next table
rebuild fails the build instead of quietly removing the guarantee.

**Note for every later slice:** altering a trigger-protected table means
re-creating its triggers in the same migration. `accounts/0004` is the worked
example.

### 12.3 Deviations from the frozen contracts introduced by S1

| # | Contract | Deviation | Why |
|---|---|---|---|
| S1-1 | ADR-001 §2.4 — *"rate limiting … uses Django's database cache backend"* | An owned `rate_limit_counters` table instead | Django's cache table has a column named **`value`**, a W1b money token, so the P14 guard went red on a table created by a migration. `CLAUDE.md` rule 13's first resort is *rename our own name*, and owning the table is how a name becomes ours. The ADR's stated reason — *"it removes Redis"* — is unaffected. Second gain: the increment becomes atomic, where the cache backend's `incr` is a read-then-write |
| S1-2 | TASKS §1 — *"`bookhop/urls.py` … is not touched again by anyone"* | One `include` line added, for `/api/v1/` | That sentence is about the **web include** and about frontend never editing the file. There is no other root URLconf, so L2 has nowhere else to mount. A one-line TASKS clarification is raised rather than the change taken silently |
| S1-3 | DATA-MODEL §2 / API-CONTRACT §4.1 — `idempotency_keys.user_id FK NULL`, *"the FK to `users` that S1 adds"* | **FK not added** | 24 assertions in QA's trees and ~20 in backend's pass synthetic `user_id` values (`idempotent(user_id=7, …)`); the FK turns all of them red, most in another agent's tree. And the break it would guard — `user_id` reuse after purge, API-CONTRACT §4.1's third named break — **does not arise**: tombstone-plus-purge never deletes a `users` row, so no id is ever freed. Raised to cto with the measurement |
| S1-4 | S0's own code comment — *"FK to users lands in S1"* on `audit_log.actor_id` | **FK not added** | Adding it makes Django rebuild `audit_log` on SQLite, which **drops its append-only triggers** — §12.2's defect, on purpose. DATA-MODEL §8 specifies `actor_id NULL` with no FK, so the contract does not require one |

---

## Amendment log

| Date | Change | By |
|---|---|---|
| 2026-10-22 | **v1.5 — S1, §12.** Nine tables, one shared plpgsql body (six now, not five), twelve SQLite triggers, and a privilege layer that is PostgreSQL-only. **One defect measured, and SQLite found it where PostgreSQL could not:** widening `notice_versions.kind`'s CHECK rebuilt the table on SQLite and **silently dropped its append-only triggers**, so for one migration an immutable table was mutable and the engine production runs on would never have said so. Fixed in `accounts/0004` and guarded on both engines by `test_append_only_triggers_exist.py`, because the hazard applies to every trigger-protected table in the system. Also measured: **a `REVOKE` does bind a table's owner — and the owner can `GRANT` it back in one statement**, which is why RED TEAM §1's one-migration fix is necessary and not sufficient. Four S1 deviations in §12.3 | backend-developer |
| 2026-10-21 | **v1.4 — the first PostgreSQL run (16.15), §10.** Every `UNVERIFIED` label executed: 95 direct assertions with SQLSTATE *and* message text, 0 failures, plus the suite on both engines (571/60 PostgreSQL, 573/58 SQLite). Blocker fixed with `params=None` rather than by doubling `%`, because the doubling failure mode is silent (§10.1). **Three predictions in this document were wrong** — §3.8's exception class (psycopg 3 maps `RaiseException` to `ProgrammingError`, not `InternalError`; the "catch `DatabaseError`" mitigation is what made that cost nothing), §2.11's boolean probe (passing on SQLite for the wrong reason, with the wrong reason recorded here as deliberate), and §2.8's float rejection (a silent **rounding**, not an error) — §10.2. **Two defects found in shipped S0 code, both invisible to SQLite**: `record_audit`'s 4-attempt retry dropped an audit row under 12 concurrent appenders and reported it as a broken chain, and `allow_test_flush` bound a per-connection GUC to a pytest session, which would have failed in S4 teardown exactly as F9 predicted — §10.3. A finding against QA-S0 §7: its nine "skip → run" items have no body to run, and `sqlmigrate` cannot render `RunPython` DDL on either engine — §10.6. Escalations 15–17 added | backend-developer |
| 2026-10-21 | v1.0 — written during S0, from measurements on SQLite 3.45.1 / Django 5.2.8 / Python 3.11.9, with no PostgreSQL server available | backend-developer |
| 2026-10-21 | **v1.3 — closing pass, REVIEW-S0 C1.** A trim-based blank check is a whitespace deny-list, and four characters was not the list: vertical tab, form feed, **NBSP (a paste from Word)**, figure space and ogham space passed the database floor while the command above it blocked them, and **zero-width space and BOM passed both layers** — so the one field carrying "a named human signed this" could be satisfied by something that renders as nothing in the go/no-go packet. Migration 0005's set is now eleven codepoints, each with its reason, and **the invariant itself** — at least one visible character, asked of Python's Unicode database per character and therefore needing no list — is in `open_discovery.has_visible_character`, which also catches five invisibles the SQL list does not know. The asymmetry and its ceiling are declared in the migration: neither engine can express the test (SQLite has no regex, Postgres's `[[:graph:]]` is locale-dependent), so the floor enumerates and the layer above generalises. Also: `tests/unit/test_forbidden_response.py` written (P14 at the contract boundary — the compensating control for the jsonb and free-text limbs, named by ADR-003 §2.3 and ownerless for two review rounds). Escalations 12–14 added | backend-developer |
| 2026-10-21 | **v1.2 — second S0 rework, after QA-S0 v2.0.** §7.1 **corrected a second time**: v1.1 called the flush fixture mandatory and did not write it, and a claim of mine that a test asserts the GUC cannot be set under production settings is **withdrawn — no such test exists and none could**; the honest control is THREAT-MODEL §4 B5/B6's accepted scope, and `tests/conftest.py::allow_test_flush` now exists. New row §3.6c (the gate evidence checklist moves into the database, F8); §3.4 extended again (the anonymous key format and the replayed body, F10 — a demonstrated disclosure). P14's lists move to `apps/core/p14.py` (W1d) with W1c's source grep in `tests/unit/test_forbidden_source.py`; all 22 W1b tokens enforced over **every** column in **any** type, and the exemption scoped to two columns instead of the `listings` table (F6/F7). Escalations 9–11 added | backend-developer |
| 2026-10-21 | **v1.1 — S0 rework after REVIEW-S0 and QA-S0.** §7.1 **corrected**: it asserted the opposite of the truth and contradicted §3.6 (M5); the TRUNCATE guards gain one declared session escape so a Postgres test harness and the append-only guarantee can coexist. New rows: §3.6a (`ENABLE ALWAYS`), §3.6b (the gate column's write guard, M0), §3.8a (float money is now checked by type, not named), §4.3a (job lock expiry, M4), and §3.4 extended (anonymous idempotency, QA-S0 B3). Deviation 6 **withdrawn** (`find_spec` replaces the `try/except`); deviations 6a and 6b added. Escalations 6–8 added | backend-developer |
