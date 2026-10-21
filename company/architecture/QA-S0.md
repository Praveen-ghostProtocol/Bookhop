# QA-S0.md — independent QA pass on slice S0

**Owner:** test-qa · **Version:** v5.0 · **Date:** 2026-10-21
**Slice:** S0 · **Engine:** PostgreSQL 16.15 **and** SQLite 3.45.1, both measured
**Against:** commit `09e2323`

# VERDICT: **PASS, on PostgreSQL and on SQLite.** S0 clears for integration.

Five passes, 20 findings raised (F1–F17, B1–B3), all fixed, accepted, or owned by
a named later slice. **The engine qualification that stood on every previous
verdict is lifted:** the five plpgsql bodies are installed, parsed and
**measured firing with the right SQLSTATE and the right message**, and the
chain's tamper-detection — QA's charter question — now runs on the engine that
will hold the data rather than only on the development one.

**Nothing blocks integration.** Seven items remain open; every one is
non-blocking and named with the slice that owns it in §7.

**v5.0 supersedes v4.0.** v4.0's §7 contained a mistake that ENGINE-DIVERGENCE
§10.6 found; §2 below takes the correction and records what QA did about it.
Earlier corrections — v2.0's against v1.0's P14 measurement, v4.0's against
v1.0's reading of M3 — stand and are not restated.

**Written from:** `ENGINE-DIVERGENCE.md` v1.4 §10 · `POSTGRES-FIRST-RUN.md` v1.1 ·
`CLAUDE.md` rules 9–16 · `ADR-002` §4 · `ADR-003` §2.1–2.3, §5.3 ·
`API-CONTRACT.md` §4 · `DATA-MODEL.md` §8 · `THREAT-MODEL.md` §4, §6 ·
`.claude/agents/test-qa.md`.

**Method.** Tests only in `tests/e2e/**`, `tests/a11y/**`, `tests/contract/**`.
Across five passes no file under `bookhop/**`, `apps/**`, `tests/unit/**`,
`tests/api/**` or `tests/conftest.py` has been modified by QA — confirmed by
`git status`. Nothing QA found was fixed by QA.

---

## 1. The commands, and their real output

```
$ cd C:\CodingSpace\BookHop && set -a && . ./.env && set +a
$ .venv/Scripts/python.exe -m pytest -q
617 passed, 49 skipped in 12.26s
```

Three consecutive PostgreSQL runs, no flakes — which matters because this pass
added thread-based concurrency tests: `617 passed, 49 skipped` in 13.38s,
11.17s, 11.36s.

```
$ BOOKHOP_DB_ENGINE=sqlite .venv/Scripts/python.exe -m pytest -q
579 passed, 87 skipped in 9.51s
```

QA's trees alone:

| Engine | QA passed | QA skipped |
|---|---|---|
| PostgreSQL 16.15 | **350** | 21 |
| SQLite 3.45.1 | 315 | 56 |

**Zero failures on either engine.** QA's tree went 169 → 182 → 246 → 336 → **371
tests**, and 3 → 10 → 0 → 0 → **0** failures. The install converted 35 skips into
assertions.

---

## 2. The correction to QA-S0 §7, taken

ENGINE-DIVERGENCE §10.6 is right and the finding is accepted without
qualification: **§7's "*(skip → run)*" could not happen for any of its items,
because those tests had no body.** Each was a single unconditional
`pytest.skip()` whose reason was an f-string interpolating the live vendor into
a sentence about SQLite — honest on SQLite, and on PostgreSQL a skip reason that
names the wrong engine and is no longer true.

That is `CLAUDE.md` rule 12 in a shape QA wrote rather than caught, and it is
the same error as v1.0's: **a placeholder that reads like coverage.** QA had
been the agent insisting that a reason naming an engine is what makes a skip
honest, and had not noticed that a reason is all those tests were.

**What QA did about it, rather than only agreeing:**

* **The nine assertions are written** — §3, in QA's trees, with bodies, running
  on PostgreSQL. The two reserved by name (the TRUNCATE refusal, which needs the
  flush escape withdrawn, and the escape surviving a connection close) are
  included.
* **The eight self-contradicting skips are gone.** Four are now real tests, and
  each old site carries a five-line comment naming the test that replaced it, so
  a reader looking for "where is the double-booking test" is not left guessing.
  The other four are **blocked by a table, not by an engine**, and now say so
  through `tests/contract/engine_limits.py::unavailable()`, which composes the
  reason from what is actually missing on the engine in front of it. On
  PostgreSQL they read *"requires `transfers`, created in S4"* and no longer
  claim an engine limit that has lifted.
* **The `sqlmigrate` half of §7 item 0 was also wrong** and QA takes that too:
  these are `RunPython` operations, so no server would ever have made
  `sqlmigrate` emit the DDL. The catalog is the route, and it is better
  evidence — it is what the server kept.

---

## 3. The nine assertions, written and run

All in QA's trees; all run on PostgreSQL; all skip on SQLite through a marker
that names the engine they need and why.

| § 7 item | Written as | What it proves |
|---|---|---|
| **1** · the plpgsql append-only half | `test_audit_tamper.py::test_the_plpgsql_append_only_trigger_body_fires` | `audit_log` is append-only **on the engine that will store it**. UPDATE and DELETE each refused with **P0001** and a message naming the operation. Until this run that body was unexecuted text |
| **1a** · the exception class | `…::test_the_append_only_guard_is_a_programming_error_not_an_integrity_error` | `ProgrammingError`, **not** the `InternalError` §3.8 predicted, and **not** `IntegrityError` — so a caller that branched on the class would have been wrong, and the surviving instruction ("catch `DatabaseError`") is the only correct one. This is the test that would have caught the wrong prediction |
| **2** · TRUNCATE refused *(reserved for QA)* | `…::test_truncate_cannot_empty_the_audit_log`, parametrised over both guarded tables | The hole that exists on PostgreSQL and not on SQLite, because row triggers do not fire on TRUNCATE. The escape is **withdrawn inside the test** to see the guard at all. Each message must name **its own** table, which is `TG_TABLE_NAME` interpolating in a statement trigger that has no `NEW` to resolve from |
| **2a** · the escape is an escape | `…::test_the_truncate_escape_is_an_escape_and_not_dead_code` | Four states: unset → refused, `'no'` → refused, **`'YES'` wrong case → refused**, `'yes'` → permitted. A guard that refused unconditionally would pass item 2 while breaking every teardown |
| **2b** · the escape is narrow | `…::test_the_truncate_guard_does_not_block_update_or_delete_for_the_wrong_reason` | With the escape **fully granted**, UPDATE and DELETE are still refused. QA had asserted this as migration text; it is now behaviour. Otherwise one `SET` turns append-only off entirely |
| **3** · the escape survives a connection close *(reserved for QA)* | `test_postgres_concurrency.py::test_the_flush_escape_survives_connections_being_closed_mid_test` + `…_opened_inside_a_thread` | The regression for §10.3(b): `connections.close_all()` mid-test, then a fresh connection must carry the declaration — and it does. Plus the thread case every race test depends on |
| **4** · the two guards with no SQLite equivalent | `test_postgres_catalog.py`, 5 tests | `campuses_gate_is_authorised` on **both** its branches (UPDATE and INSERT — *a different branch is a different first execution*, which is the whole of rule 16) and `gate_authorisations_evidence_complete` per evidence key plus its empty-array branch. P0001 and the interpolated key name each time |
| **5** · the whole suite on PostgreSQL | §1 | 350 QA assertions pass where the types are real |
| **6** · concurrent appenders | `test_postgres_concurrency.py::test_concurrent_appenders_cannot_fork_the_chain` at 12 and 24 | `prev_hash UNIQUE` keeps the chain linear under real contention, **and the row count is asserted** — §10.3(a)'s defect dropped a row, and a lost row with no exception is worse than a raised one because nothing signals it |
| **7** · "the insert of the key row is the lock" | `…::test_the_idempotency_insert_is_the_lock`, both namespaces | 12 threads, 12 connections, barrier-released: exactly one winner, one row, and **every loser arrives as a service error** the API can render as a 409 rather than as a 500 |
| **8** · two job workers | `…::test_two_job_workers_cannot_claim_the_same_job` | ADR-001 §2.4's `SKIP LOCKED` was replaced by a compare-and-swap on the grounds the properties match; §4.3 records the property as `UNVERIFIED` **on both engines**, so this was the one checklist item never exercised anywhere. 12 workers, one job, one claim |

**And one assertion §7 did not think to ask for, which turned out to matter
most.** QA's five tamper-detection tests — a rewritten row detected by id, a
deleted middle row, a forged append, a half-fixed hash, and the
tamper-evident-not-tamper-proof ceiling — **skipped off SQLite**, because the
helper that disables the guards was written against `sqlite_master`. So the
chain's *prevention* was verified on PostgreSQL by backend's run while its
**detection** had only ever been verified on the development engine. Those are
two different claims. The helper now branches (`ALTER TABLE … DISABLE TRIGGER
USER`, asserting afterwards that no guard is left enabled, or the tamper would
be blocked and the detection assertions would pass for the wrong reason), and
**all five now run on both engines.**

---

## 4. The two defects, verified — including the direction that would have been worse

### 4.1 Contention is no longer tamper — **and tamper is still tamper**

Both halves asserted, because a fix that made contention look like contention
while also making a real tamper look like contention would be strictly worse
than the bug, and it is the obvious way to get this wrong.

* **Contention → `AuditAppendContention`.** Forced deterministically (budget
  set to zero, which is the state a real exhaustion ends in) rather than by
  hoping a race loses twelve times. Asserted: the class raised, that it is
  **not** an `AuditChainBroken` and not a subclass, and that the chain still
  verifies — which is the new class's whole claim.
* **A real tamper → `AuditChainBroken`.** A rewritten row, with the guards
  disabled, on PostgreSQL. Asserted: `AuditChainBroken` **is** raised, it is
  **not** an `AuditAppendContention`, and the message names the row id.
* **Neither class is reachable from the other by `except`.** Asserted as the
  property an on-call rota actually needs: the two have identical parents and
  neither appears in the other's MRO, so a monitor subscribing to the tamper
  class is not woken by a load spike.

The 12/24-appender runs confirm the budget and backoff work: every row lands,
the chain verifies, and no two rows share a `prev_hash`.

### 4.2 The flush escape survives a connection close

Verified by performing the exact sequence that broke it — `connections.close_all()`
mid-test, assert the connection really closed, then force a fresh one and read
`current_setting('bookhop.allow_flush', true)` back as `'yes'` — and then by
using the escape on that connection. Plus the thread case: four worker threads,
each opening its own connection, each reading the declaration live.

Moving it to `connection_created` is the right fix: **a per-connection setting
belongs on a per-connection hook**, and every race test in QA's new file closes
connections in its workers, so the whole file is a continuous exercise of it.

---

## 5. Rule 16 — the standard is right, and half of it did not come back into the repository

**FINDING F17, non-blocking.** ENGINE-DIVERGENCE §10 reports *"95 direct
assertions, 0 failures, each asserting the SQLSTATE **and** the exception
message text"*. The standard is correct and QA has adopted it. But those 95 ran
**directly against the server**, and measured: the string `P0001` appears in
`tests/unit/**` and `tests/api/**` exactly **once, in a comment**. No test in
backend's trees asserts a SQLSTATE.

So the **message** half of rule 16 is in the repository — and
`test_the_append_only_message_names_the_operation_it_refused` is a good test,
engine-neutral, and catches the `%`-escaping hazard §10.1 found — while the
**SQLSTATE** half is not. A guard that began refusing with a different mechanism
(a CHECK constraint, 23514; or `RAISE … USING ERRCODE`) while keeping its text
would pass `pytest` tomorrow.

**Severity: low, and QA says so rather than inflating it.** The hazard rule 16
names — an unresolved identifier in an unexercised plpgsql branch — produces
*different text* as well as a different SQLSTATE, so the message assertions
catch it. The SQLSTATE adds the narrower case where the text is right and the
mechanism changed. **QA has encoded the SQLSTATE half for all five bodies**, in
`test_postgres_catalog.py` and `test_audit_tamper.py`, which is where it belongs
— QA's trees run on both engines in CI, and the helper states rule 16's
reasoning at the one place every call site shares.

### 5.1 The negative controls — one verified, one QA cannot reach

| Control | Verified? |
|---|---|
| **The nested `atomic()`.** Removing it must show the transaction poisoned | **Verified independently.** With `services.idempotent`'s savepoint the loser's outer transaction is still usable (a query runs, so a 409 is renderable); **without** one the same unique violation leaves it broken (`TransactionManagementError`). The control genuinely fails, which is what makes it a control. S4's `accept_offer` must keep that savepoint |
| **Downgrading a trigger off ALWAYS under the replica role** | **NOT verified by QA, and recorded as such rather than skipped quietly.** It needs a superuser. QA verified the *premise* — the application role is refused `SET session_replication_role` with **42501**, so the bypass is unreachable from the application at all — and the *state* it measures (all six triggers `tgenabled='A'`, read from `pg_trigger`). The control itself rests on backend's run as `postgres`. QA also asserts the test role is not a superuser, so the privilege finding is what it appears to be |

The privilege finding is worth keeping as a test in its own right: it means
`ENABLE ALWAYS` is defence against a **restore or a replication apply worker**,
not against the application — which is where `INFRA.md` §3.3 should assert it,
and the S8 escalation stands.

---

## 6. Siblings of the "explained rather than measured" defect — four found, none a defect

§10.2's boolean finding is the defect class QA has hunted all project, found in
the document whose job is to describe engine differences: §2.11 said the probe
used `1`/`0` *"for that reason"*, and on PostgreSQL that INSERT never reached
the CHECK at all. **A test passing for a stated-but-wrong reason is invisible
precisely because the reason is stated.**

So QA went looking for rows whose "SQLite measured" column is an argument rather
than a measurement, or whose evidence is a Django capability flag rather than a
behaviour. Four were found and all four are now measured, on whichever engine the
suite runs — `tests/contract/test_engine_claims_measured.py`:

| Row | What it offered as evidence | Measured |
|---|---|---|
| **§3.1** every enum CHECK is "enforced" | `supports_table_check_constraints = True` — a claim about what **Django believes the backend can do** | A fourth value in `audit_log.actor_type` is refused on both engines, and all three contract values insert. This is the closest sibling to §2.11: the flag was standing in for a rejected row |
| **§3.12** DDL in a transaction is "identical" | `can_rollback_ddl = True`, another flag | A table created inside a savepoint is gone after rollback on both engines. **QA's own P14 attacks depend on this** — every one creates a real table with raw DDL and relies on the rollback; if it failed on one engine those attacks would leak tables and the suite's results would depend on ordering |
| **§2.10** identity vs rowid | an explanation of both engines, plus the reasoning that it "matters only for a table whose rows are deleted and whose ids are referenced elsewhere" | Insert, delete the highest, insert again. PostgreSQL never reuses; SQLite may. **The reasoning is the part that could have been wrong:** S1's `purge_log.object_pk` records the primary key of a deleted row, which is exactly that table |
| **§3.4** NULLs-distinct is "identical by the SQL standard" | a citation | Two `(NULL, 'k')` rows coexist in a composite UNIQUE on both engines, and a partial index on the non-NULL column **does** fire. The claim was right — and worth measuring, because migration 0004's fix for QA-S0 B3 only makes sense if the premise holds on the engine that runs it |

**None of the four was a defect. That is a useful result, not a wasted pass:
they were *unmeasured*, which is a different thing from wrong, and the
difference is only visible once someone runs them.** QA also added the
regression for §10.2 itself, from QA's side: a boolean probe must use
`true`/`false`, and on PostgreSQL the refusal must carry **23514** (the CHECK)
and not 42804 (a type mismatch), because 42804 is the finding recurring.

---

## 7. What remains open — seven items, none blocking

| # | Item | Why not blocking | Slice |
|---|---|---|---|
| **F17** | Rule 16's SQLSTATE half is not in backend's trees (§5) | The message assertions catch the hazard rule 16 names; QA has encoded the SQLSTATE half for all five bodies in its own trees | backend, S1 |
| **F16** | The retry budget of 12 was sized from 40 appenders on a **near-empty** table. Two things production has that the bench did not: the commit window grows with index maintenance on a table that is append-only and never pruned, and the real appenders are **asymmetric** — one long mutation holding its transaction open (a moderation action with `work_seconds`) racing many short ones, and the long one is the one that cannot afford to lose | The class on exhaustion is now diagnosable, so whatever the right budget is, exceeding it is not misreported. QA cannot assert 12 is enough because the load profile does not exist yet. **The cheap instrument is one line**: count the attempts each append needed and expose the distribution, so the budget is set from production contention. Nothing currently reports how close to the budget a normal day runs, and `DATA-MODEL.md` §8's daily-chain-head upgrade does not help — different failure | S1/S4 |
| **F15** | `test_forbidden_response.py` implements two of the four limbs THREAT-MODEL §6 names: **an amount as a value** and **a contact detail** are unchecked, and the value limb is what ADR-003 §5.3 relies on for the free-text residual | Assigned to backend in **S1** by §5.3.1; it landed early with half its scope. S0 serves two responses, neither with a free-text field. It blocks a **sentence** — §5.3's stronger G4 wording — and a QA test enforces that | S1 |
| **F11** | `uuid.UUID(key)` accepts any version, so §4.1's "UUIDv4" is enforced as "UUID-shaped" | No longer costs a disclosure (the body is never returned), so a collision yields exactly the 409 the contract claims. Fix: `.version == 4` | S1 |
| **F12** | W1b's `rs_` token matches any plural-plus-underscore (`offers_count`, `members_count`) | No such column exists; QA asserts that too, which is what makes it a prediction. `MONEY_TOKEN_SHAPE_EXEMPTIONS` is the mechanism, and rule 13's order of resort applies — rename ours first | S2/S4 |
| **F13** | W1c's grep misses a property *assigned* rather than decorated, a bare class constant, and an annotation with no assignment | The schema control catches any that reaches a column; nothing in `apps/**` uses the three shapes, asserted. Two regexes; QA explicitly does **not** recommend a blanket `^\s*(\w+)\s*=` | S1 |
| **F14** | Three blank-rendering **printable** codepoints pass the invisible-name invariant (U+2800, U+3164, U+115F) | **Record, do not fix.** Closing it needs a list — which the invariant was adopted to avoid — or data Python does not expose. Needs someone with write access obscuring their own name in an append-only audited row | record only |
| **B2** | The gate floor cannot check whether evidence is **true** | Open by agreement; ADR-002 §4.2 and migration 0005 both say so. QA keeps the test so the packet is not read as stronger than it is | cto, before Gate C |

---

## 8. What is weaker than it looks in this run

Said plainly, because a run this good is where over-reading happens.

1. **The 95 direct assertions are not in the suite.** They were the right
   assertions to the right standard, and `pytest` enforces the message half of
   them, not the SQLSTATE half (§5). A one-off run is evidence about one moment.
2. **Item 3's negative control cannot be reproduced by QA** (§5.1). It rests on
   backend's run as `postgres`, and the application role provably cannot reach
   the bypass — which is reassuring about the exposure and is also why the
   control is unreproducible here. It belongs in the S8 restore rehearsal, where
   the role doing the work genuinely is privileged.
3. **`idempotency_anon` under contention is a rehearsal of double-booking, not a
   proof of it.** `POSTGRES-FIRST-RUN.md` §0(b) and §10.7 say so; QA's own test
   says so in its docstring. The partial unique index is on `transfers`, an S4
   table that does not exist. **A pass there predicts a pass there and is not
   one.**
4. **Three of the four §2/§7 predictions that came true produced no test
   failure**, because nothing in S0 exercises them — `uuid`, `inet` and
   `smallint` validation are live at the engine level and have no subject matter
   until S1. §10.5 is right to call that absence of subject matter rather than
   coverage. The one that *will* bite is **`LIKE` becoming case-sensitive**: on
   SQLite `__contains` behaved like `__icontains`, so every S2 search test
   written locally can pass and then fail here.
5. **SQLite's skip count tripled, from 21 to 56.** That is correct and it is the
   honest shape of a two-engine suite — those tests genuinely require
   PostgreSQL. But it means a developer running the default local engine now
   sees a third of QA's guard coverage skip, and the S2 instruction that follows
   is: **run the suite on PostgreSQL before asking for review**, not after.
6. **The metric views are the largest block of QA coverage the install
   unlocked, and it unlocks nothing yet.** `DATA-MODEL.md` §9's SQL can execute
   now; there are no rows for it to execute over until S1–S4. The engine stopped
   being the blocker and the tables became it, which is what that skip now says.

---

## 9. Escalations

**To cto, none blocking:** F15, F16, F17, F11, F12, F13 as scoped in §7; F14 to
record rather than fix; B2's two cheaply-validatable evidence items; and
ENGINE-DIVERGENCE §9 item 9 (state `due_at`, `overdue`, `consume` in ADR-003
§2.3 W1b — QA attacked the allowance with 21 derived cases and it cannot hide an
amount).

**To backend-developer:** F11, F12, F13, F15, F17. The S0 rework answered every
other QA finding, and several more thoroughly than QA asked.

**To platform-sre, for S8:** the `ENABLE ALWAYS` hardening is defence against a
restore or a replication apply worker, not against the application role, which
is provably refused (42501). `INFRA.md` §3.3's restore rehearsal is where it
earns its place, and it should assert **the triggers still fire after a
restore**, not only that the data came back. Item 3's negative control belongs
in the same rehearsal.

**To cto, a process note worth one line:** three of QA's five passes found a
defect in something QA itself had written — the P14 transcription, the M3
reading, and now §7's bodyless skips. Each was caught by someone else reading
QA's output against theirs. That is the control working, and it is an argument
for keeping the two reports side by side at every gate rather than taking either
one as settled.

**Verdict, restated: PASS on PostgreSQL 16.15 and on SQLite 3.45.1.** The gate
is a database constraint on both engines, the audit chain is tamper-evident and
now proved so where the data will live, contention and tamper are
distinguishable in both directions, the flush escape is per-connection and
survives the sequence that broke it, and the five plpgsql bodies refuse with the
SQLSTATE and the text they claim. Seven open items, all owned, none blocking.
**Slice 0 can close.**

---

## Amendment log

| Date | Change | By |
|---|---|---|
| 2026-10-21 | v1.0 — first pass. 169 tests; 3 fail as F1–F3 | test-qa |
| 2026-10-21 | v2.0 — after the M0–M5 rework. Corrected v1.0's P14 measurement **against QA**. New F4–F10; 182 tests, 10 fail | test-qa |
| 2026-10-21 | v3.0 — written, not delivered; superseded by v4.0 | test-qa |
| 2026-10-21 | v4.0 — closing SQLite pass. VERDICT: PASS. Invisible-name invariant attacked with 26 derived forms; `test_forbidden_response.py` attacked (F15). 336 tests, 0 fail | test-qa |
| 2026-10-21 | **v5.0 — first PostgreSQL pass. VERDICT: PASS on both engines.** §10.6's finding against §7 **accepted**: the skips had no body, and eight named the wrong engine on PostgreSQL. All nine assertions now written with bodies, including the two reserved for QA; four placeholders replaced by real tests and four reasons re-pointed at the table that actually blocks them. Both halves of the contention/tamper fix verified, including that a real tamper is still reported as tamper. The flush escape verified across `close_all()` and in worker threads. Rule 16's SQLSTATE half encoded for all five plpgsql bodies — and **F17**: it was not in backend's trees. Four siblings of §10.2's explained-not-measured defect found and measured; none a defect. QA's five tamper-**detection** tests, previously SQLite-only, now run on both engines. **371 QA tests: 350 pass on PostgreSQL, 0 fail, three consecutive clean runs** | test-qa |
