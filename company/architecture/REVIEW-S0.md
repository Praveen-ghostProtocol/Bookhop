# REVIEW-S0.md — Code Review of slice S0

**Reviewer:** code-review · **Date:** 2026-10-21 · **Slice:** S0 (skeleton,
tenancy, gate, audit, jobs, idempotency) · **Author under review:**
backend-developer.

**Verdict: CHANGES REQUIRED.** Six must-fixes, then a re-review of those six
only. Nothing needs a redesign, but **M0 blocks integration on its own**: the
discovery gate column has no write guard, so `ADR-002` §4.1(b)'s central claim
is false as implemented. The charter set the threshold as "impossible to
bypass, not merely inconvenient". It is currently inconvenient.

**M0 was found by test-qa, not by me.** Its trees landed while this review was
in progress and I verified the finding independently. My own first pass
examined the bypass surfaces that exist and concluded there were none; I did
not test the column's own writability, which was the question. Recorded here
because "escaped defects found by someone else" is this agent's metric to own
(code-review charter, Metrics).

**Reviewed against:** `TASKS.md` §0–§4 · `DATA-MODEL.md` §1, §5, §8 ·
`API-CONTRACT.md` §2, §3, §4, §5.8 · `THREAT-MODEL.md` §1, §4, §6 ·
`ADR-001` §2.1–2.8 · `ADR-002` §2, §4 · `ADR-003` §2.1–2.3 ·
`ENGINE-DIVERGENCE.md` · `CLAUDE.md`.

**Authorship declaration** (charter hard rule 1): this agent wrote no line of
the code under review. It has written no application code at all.

**File ownership note:** `company/architecture/**` is cto-owned (`TASKS.md`
§1). This file was written here on explicit assignment; cto owns it from
receipt.

---

## 0. What was run, and on what

| | |
|---|---|
| Suite, at the start of review | `.venv/Scripts/python.exe -m pytest -v` → **92 passed, 21 skipped, 0.59s** |
| Suite, after test-qa's trees landed mid-review | `-q` → **5 failed, 231 passed, 44 skipped** |
| Engine | SQLite 3.45.1 · Python 3.11.9 · Django 5.2.8 · **no PostgreSQL server** |
| Migrations | `migrate` from empty ✓ · `migrate core 0001` (reverse 0002) ✓ · forward again ✓ · `migrate core zero` ✓ · forward again ✓ |
| `seed_demo` | on a fresh database ✓ — `discovery_enabled_at=None (NULL = closed)` |
| `verify_audit_chain` | ✓ `audit chain OK: 0 rows, head=000…0` |
| `open_discovery --campus demo-campus` | ✓ refuses, prints the checklist, **exit 1**, "Nothing was changed" |

Five findings below were confirmed by executing probe code rather than by
reading, because reading is how a reviewer talks themselves into a finding that
is not there. The probes ran against the project's own settings and test
database and were discarded; they are reproduced inline so anyone can repeat
them. Marked **[verified]**.

Three of `TASKS.md` S0's four "done when" criteria are met. The fourth —
*`seed_demo` produces a browsable-by-staff dataset* — cannot be met before
S1/S2 and is a `TASKS.md` defect, not a slice failure (see N12).

**`apps/core/**` and `bookhop/**` were not modified during this review** —
every mtime predates the session. What changed is that `tests/contract/**`,
`tests/e2e/**` and `tests/a11y/**` (test-qa's trees, `TASKS.md` §1) appeared
while it was in progress. Those files are outside this review's remit, but
their five failures are not, so they are triaged here so that backend-developer
does not chase the three that are not defects:

| Failing test | Triage |
|---|---|
| `test_s0_surface::test_the_gate_column_cannot_be_opened_outside_the_authorised_command` | **Real, severe, and correct.** A deliberate documented finding. **M0 below.** Verified independently. |
| `test_p14::test_p14_is_not_guaranteed_by_naming` | **Real.** A deliberate documented finding, corroborating S7 and adding the float-type limb. Folded into S7. |
| `test_s0_surface::test_only_the_gate_commands_write_discovery_enabled_at` | **False positive.** **[verified]** The only regex match in `seed_demo.py` is line 47, `self.stdout.write(f"discovery_enabled_at={campus.discovery_enabled_at!r} …")` — a print, not a write. Behaviourally, `seed_demo` leaves the column `None`, which I ran and confirmed. The regex `discovery_enabled_at\s*=(?!=)` cannot tell an f-string label from an assignment. **Do not change `seed_demo.py`; the test needs the fix.** |
| `test_p14::test_denylist_catches_a_forbidden_table_name[ledger_entries]` | **Cross-file ordering collateral**, not an S0 defect. **[verified]** `test_p14.py` run alone yields exactly one failure (the intended one); these two appear only in a full-suite run, because the attack test's `_create()` leaves real tables in the test database for later introspection to find. test-qa's to fix. |
| `test_p14::test_the_row_7_and_row_8_exemptions_are_table_scoped_not_global` | Same cause as the row above. |

Net: of five failures, **two are genuine S0 findings**, one is a false
positive against correct code, and two are pollution in the new test trees.

---

## 1. MUST-FIX BEFORE INTEGRATION

### M0 — The discovery gate column has no write guard, so the gate can be opened by one ORM call
`apps/core/models.py:66` · `apps/core/migrations/0002_append_only_triggers.py`

`ADR-002` §4.1(b), first line: *"Discovery cannot be opened by a `UPDATE
campuses SET discovery_enabled_at = now()`. It is opened by `manage.py
open_discovery`, which refuses unless…"* **As implemented, it can.**
`campuses.discovery_enabled_at` is an ordinary nullable column with no trigger,
no CHECK and no privilege separation. The model docstring at
`apps/core/models.py:49-53` asks future developers not to write it — "Do not
add a settings flag, a property or a convenience setter that writes this
column: the only writer is that command" — which is a comment, and the ADR
promises a control.

**[verified]** On a campus with no `gate_authorisations` row, no legal entity
(`legal_entity_id=None`), no CIN, no INC-20A and no MoU:

| Write path | Gate opened? | `audit_log` rows written |
|---|---|---|
| `Campus.objects.filter(pk=…).update(discovery_enabled_at=now())` | **yes** | **0** |
| `campus.discovery_enabled_at = now(); campus.save(update_fields=[…])` | **yes** | **0** |

and `assert_discovery_open(campus)` then **does not raise** — so the gate is
genuinely open to every reader, not merely marked open. For contrast, in the
same probe, the *same shape of write* on `gate_authorisations.evidence` was
**blocked** by migration 0002.

**Failure it causes.** Three distinct ones, and the first is the legal exposure
the whole slice exists to prevent:

1. Real students on an unauthorised campus become able to browse each other's
   listings the moment S3 exists — which `INCORPORATION-AND-BLOCKERS.md` §2 A0
   says makes BookHop an e-commerce entity under r.3(1)(b)/r.4(1)(a) *before
   the company exists*. One line in any future service function, job handler or
   management command does it.
2. **No audit row is written**, so the go/no-go packet (`README.md` §7,
   `ADR-002` §4.1(b)) would show a campus that was never authorised and no
   record of who opened it. The row that is supposed to be the audit artefact
   is simply absent, and `verify_audit_chain` cannot notice an event that was
   never recorded.
3. The evidence checklist becomes advisory. `open_discovery` is a careful,
   well-tested front door standing beside an open window.

**This is not the exposure `ADR-002` §4.2 concedes.** That paragraph accepts
"no protection against a staff member running SQL directly" and names RLS as
the only answer. M0 is the application's own ORM, reachable from ordinary
Python by any agent in any later slice — the case §4.1(b) explicitly claims to
have closed.

**Smallest fix.** The mechanism, the precedent and the engine support all
already exist in migration 0002, applied to the neighbouring table: a
`BEFORE UPDATE` trigger on `campuses` that raises if `discovery_enabled_at`
changes unless a live Gate C authorisation row exists for that campus. Written
for both engines, as 0002 already does twice. If reading
`gate_authorisations` from inside a trigger is judged too clever, the
strictly-smaller version still closes the hole: refuse **any** change to
`discovery_enabled_at` that does not set it to NULL, and have
`open_discovery` perform its one legitimate write through a single
`RAISE`-exempt path (a session GUC on Postgres, a companion flag table on
SQLite). Either is a day's work less than the first slice that needs it.

**Escalation:** this touches `ADR-002` §4, so the fix and any wording change to
§4.1(b)/§4.2 go to cto, not into a commit. If cto prefers to accept the gap
rather than close it, §4.1(b)'s sentence must change, because as written the
contract asserts a property the code does not have — and that sentence is what
a G4 reviewer will rely on.

### M1 — The P14 deny-list still carries the exception that CG-5 withdrew
`tests/unit/test_forbidden_schema.py:56-59`

```python
CONDITIONAL_COLUMNS = {
    "date_of_birth": "age_check_pending",   # DATA-MODEL §2: the only place a DOB lives
    "dob": "age_check_pending",
    "birth": "age_check_pending",
```

`ADR-003` §2.3 as amended 2026-10-21 reads: "`date_of_birth`, `dob`, `%birth%`
— **no exception** *(amendment 2026-10-21, CG-5: the former
`age_check_pending` exception is withdrawn)*". `DATA-MODEL.md` §2 deletes the
table outright: "~~`age_check_pending`~~ — **REMOVED by amendment A-5**". The
comment on line 57 cites `DATA-MODEL` §2 for the opposite of what §2 now says.

**[verified]** A column `age_check_pending.date_of_birth` passes the entire
deny-list today — all four tests, green.

**Failure it causes:** S1 recreates the table amendment A-5 deleted, stores a
declared date of birth, and the guard test that exists to stop exactly this
stays green. The amendment strengthened the control; leaving the file unchanged
silently reverted it. P14 and `COMPLIANCE.md` §7 row 7.

**Smallest fix:** all three values become `None`. Three characters.

**Handling:** this file is a founder escalation, not a review comment
(`ADR-003` §5.2, code-review charter, backend-developer charter). The fix lands
with cto's sign-off citing amendment A-5, not as a quiet commit.

### M2 — The same file will fail on a column ADR-003 itself mandates
`tests/unit/test_forbidden_schema.py:143-160`

`test_the_only_money_column_is_the_listing_asking_price` flags any column whose
name contains `price`, `paise` or `rupee` unless the full name is exactly
`listings.asking_price_paise`. `ADR-003` §2.1 and `DATA-MODEL.md` §3 both
require `listings.price_fixed_at NOT NULL`.

**[verified]** `listings.price_fixed_at` is caught by this assertion.

**Failure it causes:** S2 adds a column two frozen contracts mandate and meets
a red P14 guard test. The obvious local fix is to edit the deny-list file —
which is a founder escalation (`ADR-003` §5.2). A guard test whose first real
encounter with the codebase is a false positive teaches a developer that the
guard is wrong, and that is how the guard gets edited.

**Smallest fix:** compare against the two legitimate names now, before S2 meets
it:

```python
assert set(found) <= {"listings.asking_price_paise", "listings.price_fixed_at"}
```

### M3 — An idempotency key replays across different endpoints
`apps/core/services.py:228-258`

`idempotent()` stores `endpoint` and then never compares it. The reuse test is
body-only:

```python
existing = IdempotencyKey.objects.get(user_id=user_id, key=str(key))
if existing.request_hash != request_hash:
    raise IdempotencyKeyReused() from None
```

**[verified]** Key `k-1` claimed on `POST /api/v1/offers`, answered
`201 {"id": 42, "state": "OFFERED"}`. The same user, same key and same body
sent to `POST /api/v1/transfers/9/accept` returned
`Replay(status=201, body={"id": 42, "state": "OFFERED"})` — the offers
response, replayed to an accept request, with no transition performed and no
error.

**Failure it causes:** from S4 every transition endpoint shares one key
namespace per user (`UNIQUE (user_id, key)`), and `API-CONTRACT` §4.1 has L3
forms generate a key per render. A client that reuses one — a refresh, a
back-button, a retry against the wrong URL — receives another endpoint's stored
response verbatim and believes the transition happened. The `endpoint` column
exists in `DATA-MODEL.md` §5 precisely to prevent this.

**Smallest fix:**

```python
if existing.request_hash != request_hash or existing.endpoint != endpoint:
    raise IdempotencyKeyReused() from None
```

### M4 — A job claimed by a worker that dies is never run again
`apps/core/jobs.py:54-73`

`_claim` selects `locked_at__isnull=True` and compare-and-swaps on the same
predicate. Nothing anywhere expires a lock. The exception path clears
`locked_at` (line 92-93), so the leak is confined to a hard stop — SIGKILL,
OOM, power loss, a deploy mid-handler — which is the one case lock expiry
exists for.

**[verified]** A job locked 30 days ago by `dead-worker` was not run, not
retried and not marked failed across three successive `run_due_jobs()` calls:
`completed_at=None failed_at=None locked_at set=True attempts=1`.

**Failure it causes:** `ADR-001` §2.4 and `API-CONTRACT` §4.4 both guarantee
at-least-once delivery. A killed worker delivers the job **zero** times,
permanently and silently. From S1 that is `retention.purge` — a DPDP r.8(3)
obligation that stops running with no error. From S3 it is
`requests.match_scan`; from S5, the 72-hour `followup.*` clocks. `/readyz`
turns 503 and stays there, which is detection without recovery.

This also undercuts the deviation it belongs to: `FOR UPDATE SKIP LOCKED`
releases its lock when the connection dies; a `locked_at` column does not. The
docstring's claim that running N workers "is already safe" is less true without
expiry, not more.

**Smallest fix:** make a stale lock claimable, in both the candidate query and
the CAS:

```python
stale = Q(locked_at__isnull=True) | Q(locked_at__lt=now - JOB_LOCK_TIMEOUT)
```

Note that `tests/unit/test_jobs.py:84` currently asserts the losing behaviour
(§5, item 3).

### M5 — ENGINE-DIVERGENCE §7.1 is contradicted by its own §3.6, on the slice that needs both
`company/architecture/ENGINE-DIVERGENCE.md` §7.1 ·
`apps/core/migrations/0002_append_only_triggers.py:36-38`

§7.1 states: "On Postgres, flush uses `TRUNCATE`, which **row triggers do not
see** — so the same test would tear down cleanly there." §3.6, in the same
commit, adds `audit_log_no_truncate BEFORE TRUNCATE … FOR EACH STATEMENT`
precisely so that TRUNCATE no longer passes.

**[verified]** Django 5.2's `postgresql.DatabaseOperations.sql_flush` emits
`TRUNCATE "t1", "t2", …;` (read from the installed source). With migration 0002
applied, that statement fires `audit_log_no_truncate` and raises P0001
`audit_log is append-only`.

**Failure it causes:** on the first Postgres box, every `transactional_db` /
`TransactionTestCase` test errors in teardown. §5.3 of the same document
requires `tests/api/test_double_booking.py` to run on Postgres and skip on
SQLite, and a concurrency test must be transactional to commit at all — so the
collision lands exactly on the test §5 calls "the single most important
correctness property in BookHop". The tempting fix at that moment is to delete
the TRUNCATE trigger, which §3.6 calls the most important unverified thing S0
shipped. A removed check under schedule pressure is the failure mode the
charter's last hard rule names.

**Smallest fix:** correct §7.1 — it currently tells a future developer the
opposite of the truth — and give the guard one escape the harness can use, for
example raising only when
`current_setting('bookhop.flush_ok', true) IS DISTINCT FROM 'yes'`, set by a
session fixture. Either that or a documented
`ALTER TABLE audit_log DISABLE TRIGGER audit_log_no_truncate` around flush. The
decision matters less than writing it down before a Postgres box exists rather
than discovering it on one.

---

## 2. SHOULD-FIX

### S1 — The request-id regex accepts a trailing newline
`apps/core/middleware.py:15,24`. `_SAFE_ID.match` with `$` matches before a
trailing newline — a standard Python regex trap, and this field's entire stated
purpose is "no newlines (log injection)".

**[verified]** `match("abc\n")` → `True`; `fullmatch("abc\n")` → `False`.
`"abc\r"`, `"abc\nx"` and 65 characters are all correctly rejected.

Not exploitable through a conformant server (nginx and gunicorn reject LF in a
header value) and `json.dumps` escapes the log line regardless — so the real
consequence is narrower than the comment implies: `response["X-Request-Id"] =
"abc\n"` raises Django's `BadHeaderError`, i.e. a 500 on that request, and the
value also reaches `audit_log.request_id`. The code does not guarantee what its
comment claims. **Fix:** `_SAFE_ID.fullmatch(supplied)`. The companion test
covers a mid-string newline only (§5, item 2).

### S2 — `extra={…}` can overwrite the log line's retention class
`apps/core/logging.py:49-51`. The extras loop excludes `_RESERVED`, which is
derived from a live `LogRecord` and therefore does not contain `ts`, `level`,
`logger`, `log_class` or `event`.

**[verified]** A `bookhop.security` record carrying
`extra={"log_class": "app", "event": "nothing happened"}` emitted
`log_class="app"` with the message replaced.

`log_class` is what makes the 365-day retention floor "mechanical rather than a
judgement call" (the module's own docstring, `ADR-001` §2.7) and `event` is
what a CERT-In investigation reads. **Fix:** add those five keys to
`_RESERVED`, or merge extras first and let the computed fields win.

### S3 — `worker_id` is not unique
`apps/core/jobs.py:78`. `f"{socket.gethostname()}:{id(object())}"` — the
object is garbage-collected immediately and its address reused.

**[verified]** 200 generated ids produced **1** distinct value.

No correctness property breaks (claiming rests on the CAS, not on the
identifier), but `locked_by` is useless for the only question it answers —
which worker holds this lock — and that question becomes live once M4's expiry
lands. **Fix:** `uuid.uuid4().hex`.

### S4 — Whitespace passes as gate evidence
`apps/core/management/commands/open_discovery.py:72`.
`ok = bool(value) and (not isinstance(value, (list, dict)) or len(value) > 0)`
does not strip, while `authorised_by_human` is stripped on line 58. So
`evidence = {"campus_mou_ref": " "}` satisfies "Gate C1 — signed campus MoU".
The second clause of the `and` is also unreachable: `bool([])` and `bool({})`
are already `False`. ADR-002 §4.1(b) requires every evidence field "non-empty";
a space is not evidence of a signed MoU. **Fix:** strip strings before the
check; delete the dead clause.

### S5 — The authorisation's legal entity is never reconciled with the campus's
`apps/core/management/commands/open_discovery.py:61-67`.
`entity = campus.legal_entity or auth.legal_entity`, and because
`campus.legal_entity_id is not None` is itself a checked item appended before
the legal-entity items (and `handle` raises on the first failure), the `or`
branch is unreachable — dead code that reads as a fallback. The consequence is
that CIN, INC-20A and the grievance-officer facts are read from
`campus.legal_entity` while the authorisation row names its own
`legal_entity_id`, and a mismatch is unchecked: a row authorised against entity
A can open a campus whose evidence is read from entity B. **Fix:** one
checklist item asserting `auth.legal_entity_id == campus.legal_entity_id`;
delete the dead `or`.

### S6 — Two deny-list patterns are narrower than ADR-003 specifies
`tests/unit/test_forbidden_schema.py:32,41`. `ADR-003` §2.3 writes `%vpa%`
(substring); the test implements `("vpa", True)` (exact). The ADR's bare `pan`
is correctly exact, but nothing covers the obvious variant.

**[verified]** `users.vpa_handle` and `users.pan_card` both pass the entire
deny-list.

**Fix:** `("vpa", False)` and add `("pan_card", False)`.

### S7 — The deny-list is name-shaped, and a settlement table walks around it
`tests/unit/test_forbidden_schema.py:20-73`. `"settled"` is not a substring of
`"settlement"`; `NO_MONEY_TABLES_PREFIX` is `handover_`, so `handovers_cash`
misses; and the per-transaction-table money ban applies to four table prefixes
only.

**[verified]** All of these pass every test in the file today:
`settlements.amount_minor` · `settlement_records.consideration` ·
`transfer_settlements.consideration` · `handovers_cash.cash_received` ·
`receipts.total_inr`.

This is a ceiling of the control `ADR-003` specifies rather than a deviation
from it — the ADR describes a column-name check, and §5.3 of the same ADR
already concedes the deeper exposure is `asking_price_paise` plus
`state='COMPLETED'`, which no test can fix. But the threshold under s393 Table
Sl. 8(v) is nil, and the cheapest real breadth available is one line.

**Fix (best coverage per character):** widen the word list in
`test_the_only_money_column_is_the_listing_asking_price` — the test that
already asserts "exactly one money column anywhere" — from
`("price", "paise", "rupee")` to add `amount`, `consideration`, `settle`,
`cash`, `inr`, `_minor`, and apply the same list to table names. Land it with
M2, since both touch that assertion.

**Corroborated independently.** test-qa's
`tests/contract/test_p14.py::test_p14_is_not_guaranteed_by_naming` reaches the
same conclusion from the spec side and adds a limb I did not consider: the one
*permitted* column, `listings.asking_price_paise`, **declared as `real`**, also
passes — because a name-based control reads no types, and
`ENGINE-DIVERGENCE.md` §2.8 measured that this engine stores `300.75` in an
`integer NOT NULL` column and returns it as a float. So ADR-003 §2.1's
"integer paise. No floats for money, ever" is unenforced on the development
engine *and* invisible to the guard. **Add to the fix:** one type assertion on
that single column, which is cheap, exact, and the only part of P14 that can be
checked rather than named. QA's two related assertions correctly skip on SQLite
with the engine named.

### S8 — Four of five deny-list tests can pass vacuously
`tests/unit/test_forbidden_schema.py:88-95`. `test_no_forbidden_column_exists`
asserts `schema` is non-empty; `live_schema()` does not, so the other four pass
trivially if introspection ever returns nothing. **Fix:** move the assertion
into `live_schema()`.

### S9 — Nothing asserts that another campus's authorisation cannot open this campus
`tests/unit/test_gate.py`. `open_discovery` filters
`gate="C", scope_type="CAMPUS", scope_id=campus.id` — correct in code, and none
of the three selectors is tested. The suite covers every evidence key, three
legal-entity facts, revocation and the named human, but not "a neighbouring
campus signed an MoU and opened mine". For the control that makes building
before incorporation lawful, that case is worth three parametrised lines: wrong
`scope_id`, `gate='B'`, `scope_type='GLOBAL'`.

### S10 — The accounts stubs point S1 at the table amendment A-5 deleted
`apps/accounts/services.py:7`. The module docstring lists `age_check_pending`
among the tables whose "bodies land in S1". `DATA-MODEL.md` §2 deletes it and
`ADR-003` §2.3 withdrew its deny-list exception. With M1 unfixed, this
docstring reads as an instruction to recreate it and the guard will not object.
**Fix:** delete the name. Also `from datetime import date` on line 15 is
genuinely unused — the `noqa` comment says it is "named in the frozen
signatures" and it is not.

### S11 — `record_audit` reports every IntegrityError as a broken chain
`apps/core/services.py:146-156`. The retry loop catches `IntegrityError`
generically, which is correct for the `prev_hash` race it exists for and wrong
for every other integrity failure on the same insert.

**[verified]** An `audit_actor_type_chk` CHECK violation was retried **4
times** and surfaced as `AuditChainBroken: could not append to the audit chain
after 4 attempts` — the real cause discarded, in the audit path, where a
misleading diagnostic is most expensive.

**Fix:** include `last_error`'s message in the raise, or only retry when the
failure names `prev_hash`.

### S12 — `/readyz` returns internal state unauthenticated
`apps/core/views.py:55-64`. The body carries `migrations_applied` and
`jobs_overdue`, telling an anonymous caller whether a deploy is half-applied
and how deep the queue is. `API-CONTRACT` §5.8 reserves counters for the
token-protected `/metricsz` and specifies `/readyz` as a readiness signal.
ASVS V13 (minimal exposed surface). **Fix:** return `{"ready": bool}` and log
the detail. `tests/api/test_operational.py:17-24` asserts the detail is
present, so the test moves with it; fold into the §4 item-4 docstring change.

---

## 3. NOTES

- **N1 — No CSP anywhere, and no slice owns it.** `THREAT-MODEL` §4 B3 names
  "strict CSP (`default-src 'self'`, no inline script, nonce for the one
  bootstrap script)" as a stored-XSS control at ASVS V1/V3 **L2**. It is a
  response header, so it is backend middleware rather than a template, and
  `TASKS.md` assigns it to nobody. Flag to cto for slice assignment before S1
  ships the first HTML.
- **N2 — `tests/unit/test_forbidden_response.py` has no owning slice.**
  `ADR-003` §2.3 ("a second test asserts the API response schemas contain none
  of the forbidden keys") and `THREAT-MODEL` §6 both name it; `TASKS.md` S0
  lists four guard tests and this is not one, and no later slice claims it. It
  is also the compensating control for the jsonb limb of S7. A named control
  with no owner is never written. Escalate.
- **N3 — `API-CONTRACT` §2.2's error shape is not rendered anywhere.**
  `apps/core/errors.py` carries the codes, statuses and `retry_after`, and
  nothing maps them onto the JSON body; no handler guarantees "500 never echoes
  an exception message, the `request_id` is the only thing the user gets".
  Correct for S0 — no L2 endpoint exists — but it sits between backend L2 and
  frontend L3 and should be named explicitly as S1-backend so it does not fall
  between two agents.
- **N4 — `bookhop/urls.py:16-25`: the ceiling is avoidable today.** The
  `try/except ModuleNotFoundError` is a real need (S0 must boot before
  frontend's tree exists, and `TASKS.md` §1 forbids backend touching this file
  again) with a real declared ceiling: a genuine import error inside `web.urls`
  is swallowed as "not there yet", which is a silent outage of the entire
  student-facing surface. `importlib.util.find_spec("web") is not None`
  distinguishes the two cases in the same two lines and leaves nothing to
  delete later. Replace rather than schedule; a deletion that depends on
  someone remembering is the same bet the comment apologises for.
- **N5 — the gate's audit row says SYSTEM opened it.**
  `record_audit(None, …)` in `open_discovery`/`close_discovery` yields
  `actor_type='SYSTEM'` for the most legally significant action in the system.
  The named human survives in `gate_authorisations.authorised_by_human` and in
  the audit payload, so nothing is lost, but the row reads as if the machine
  decided. A `--by` argument is one line.
- **N6 — `jobs.last_error` holds 4,000 characters of traceback and `jobs` has
  no `purge_due_at`** (`DATA-MODEL.md` §8). From S1 payloads carry pseudonyms,
  and a database error can quote row values into a traceback. Reconcile against
  `COMPLIANCE.md` §7 when the retention job lands.
- **N7 — the Postgres triggers are created with the default enable state**, so
  `SET session_replication_role = 'replica'` or `ALTER TABLE … DISABLE TRIGGER`
  bypasses them. `THREAT-MODEL` §4 B5/B6 already accepts direct SQL as out of
  scope, so this is not a new exposure — but `ENABLE ALWAYS TRIGGER` is one
  line per trigger, closes the replication-role route, and matters for logical
  replication and restore. Worth taking while M5 is open.
- **N8 — `tests/unit/test_scoping.py:44`: `assert checked >= 0` is a
  tautology.** It cannot fail. Delete it or make it a comment; the vacuity it
  gestures at is genuinely covered by `test_pending_tenant_model_is_reported`
  and `test_registry_lists_no_model_that_exists_under_another_name`.
- **N9 — `test_whole_audit_table_cannot_be_truncated_by_delete` issues a
  DELETE.** The name implies TRUNCATE coverage that exists on neither engine
  (§3.6 of the divergence document is honest about this; the test name is not).
  Its sibling's docstring at line 77 also says "Drop the guard, tamper, verify,
  restore" and the code never restores — it relies on the transaction rollback.
  Rename one, correct the other.
- **N10 — `tests/unit/test_price_immutable.py:42` will error on the day S2
  unskips it.** `Listing.objects.first()` with `assert listing is not None` and
  no fixture creating one.
- **N11 — there is no lint, type or CI configuration in the repository.**
  `ruff` and `mypy` are commented out of `requirements-dev.txt` ("not installed
  on this machine"), and no `pyproject.toml`, `ruff.toml` or CI workflow
  exists. `TASKS.md` S0 lists "`ruff`, `mypy`, CI running the test suite" in
  scope while `TASKS.md` §1 assigns `.github/workflows/**` to platform-sre,
  "dormant until S8" — a contradiction inside `TASKS.md` rather than a
  developer omission. Consequence worth stating plainly: "boring, minimal,
  obvious" is currently enforced by this review and nothing else.
- **N12 — `TASKS.md` S0's fourth "done when" is unmeetable in S0.**
  "`seed_demo` produces a browsable-by-staff dataset" needs `users` (S1) and
  `listings` (S2). `ENGINE-DIVERGENCE.md` §8.7 says so. The command's refusal
  to fake it — printing "staff user and is_seed students: NOT created" — is the
  correct behaviour and the opposite of the failure the engineering standard is
  written against. `TASKS.md` should lose the criterion.
- **N13 — `seed_demo` matches `City` on `name` only** while the UNIQUE is
  `(name, state)`. Harmless at one city.

---

## 4. The declared deviations, ruled on

| # | Deviation | Ruling |
|---|---|---|
| 1 | `campuses.email_domains` jsonb, not `text[]` | **Acceptable** |
| 2 | Job claiming by conditional UPDATE, not `FOR UPDATE SKIP LOCKED` | **Acceptable with a condition: M4** |
| 3 | Python 3.11.9, not 3.12 | **Acceptable** |
| 4 | `/readyz` checks "no job overdue", not "last run recent" | **Acceptable with a condition** |
| 5 | `try/except ModuleNotFoundError` around `include("web.urls")` | **Acceptable with a condition: replace now, not later** |

**1. `email_domains` as jsonb — acceptable.** `ArrayField` is
`django.contrib.postgres`-only, and a per-engine field choice means two
migration paths for one schema, which is a worse failure than the type. The
only operation v1 performs is membership, and the data is a short list of
domains. The deviation is declared and escalated, which is the condition
already met. cto should amend `DATA-MODEL.md` §1 to `jsonb`, as the author
recommends, so the contract and the code stop disagreeing. One caveat for S1:
membership against a JSON list is a Python-side `in`, not a SQL predicate — at
one campus that cannot matter, and it should not quietly become a scan per
login at ten.

**2. Job claiming — acceptable with a condition, and the condition is M4.** The
reasoning is right and the measurement is the whole point: Django *silently
omits* the locking clause on SQLite rather than raising, so `SKIP LOCKED` would
have looked correct locally while locking nothing — which is worse than a
different mechanism, because it reads as evidence. A compare-and-swap UPDATE
gives the same "at most one worker claims a row" property in SQL that means the
same thing on both engines and can be read in the query log. **But the two
mechanisms are not equivalent in the case that matters:** `SKIP LOCKED`
releases the lock when the connection dies, and a `locked_at` column does not.
The deviation is fine; shipping it without lock expiry is not. `ADR-001` §2.4
should take the one-line amendment the author asks for.

**3. Python 3.11.9 — acceptable.** Django 5.2 supports 3.10–3.13 and nothing in
S0 uses a 3.12 feature. The only genuine risk is dev/prod drift, so the
condition is that the production box is pinned to 3.12 and the version is
asserted somewhere a human reads it — not that 3.12 be installed now.
Correctly declared, correctly low-risk.

**4. `/readyz` — acceptable with a condition.** The literal check needs a
heartbeat job and there is no scheduler, so it would report not-ready forever;
a readiness probe that is always red gets disabled, which is strictly worse
than a probe with a known blind spot. The declared ceiling — "a dead runner
with an empty queue reads as ready" — is exactly the failure the check exists
to catch, but it closes itself from S1, because `retention.purge` is a standing
recurring job and a dead runner then always leaves something overdue.
**Condition: say that in the docstring.** The upgrade path currently points at
S8's systemd timer when in fact S1's first recurring job is what makes the
check meaningful, and until S1 lands a green `/readyz` says nothing at all
about the runner. Fold S12 in while touching it.

**5. `try/except ModuleNotFoundError` — acceptable with a condition.** The need
is real and the alternative (backend editing `bookhop/urls.py` again later) is
forbidden by `TASKS.md` §1. But the declared ceiling is a silent routing
outage, and `importlib.util.find_spec` removes it for the same two lines. See
N4: replace it now rather than scheduling its deletion.

---

## 5. The three legally load-bearing controls — do they hold?

### 5.1 The discovery gate — **DOES NOT HOLD.** The front door is excellent and the column behind it is unguarded

This is the control the brief calls load-bearing for legal rather than
engineering reasons, and the charter set the threshold explicitly: *"It must be
impossible to bypass — not merely inconvenient."* It is inconvenient.

**What exists and works, verified by execution:** `discovery_enabled_at` is
NULL by default; `open_discovery` refuses without a non-revoked `gate='C'`
authorisation, a named human, five legal-entity facts and six evidence keys,
printing the checklist, exiting 1 and changing nothing; the authorisation row
cannot be deleted and its `evidence` cannot be rewritten; `close_discovery`
closes and revokes; both write an audit row. Every part of the *authorisation*
machinery is sound and well tested.

**What does not work: the column itself accepts any write (M0).** **[verified]**
`Campus.objects.filter(pk=…).update(discovery_enabled_at=now())` and
`campus.save(update_fields=["discovery_enabled_at"])` both open the gate on a
campus with no authorisation row and no legal entity, write **zero** audit
rows, and leave `assert_discovery_open` passing. `ADR-002` §4.1(b) states this
cannot happen. It can.

**Bypass surfaces I checked and correctly found absent**, which is the part of
my first pass that stands: `django.contrib.admin` is **not** in
`INSTALLED_APPS`, so there is no admin view of `campuses`; no raw SQL writes
the column; `seed_demo` leaves it NULL and says so (the QA static test flagging
it is a false positive, verified); there is no settings flag, property or
convenience setter, and `bookhop/settings/base.py:174-178` explains why there
deliberately is not. The transfers-side `CHECK (seller_is_seed =
buyer_is_seed)` is indeed S4 and cannot be subverted meanwhile because nothing
creates transfers (`tests/unit/test_seed_separation.py:9-10` says so rather
than implying it).

**Where my first pass went wrong, since it is the useful part of this
finding.** I enumerated the paths that *exist today* and found none, then
concluded the gate was unbypassable. The question the charter asked was whether
it *can* be bypassed, and the answer did not depend on any existing path: it
depended on whether the column has a guard, which is one probe I did not run.
Checking today's callers is the wrong test for a foundation slice whose entire
purpose is to constrain callers that do not exist yet. test-qa, writing from
the spec without reading the implementation, asked the right question —
which is exactly the division of labour `CLAUDE.md` rule 5 and `TASKS.md` §0
rule 3 are for, working as designed.

**What still does not exist, and correctly so:** any read path.
`assert_discovery_open` and `restrict_when_gate_closed` are opt-in helpers with
no caller, and `test_gate.py`'s end-to-end assertion is correctly skipped to S3
with the slice named. So nothing is exploitable *today* — there is no listing to
reach and no query to reach it with. That is why M0 is a must-fix rather than
an incident: the window closes before S3, if it closes now.

**The forward risk, worth deciding now rather than in S3.** Because the gate is
opt-in per call site, the first forgotten call is a silent legal exposure, and
no test in S0 — or in S3 — can enumerate call sites that do not exist yet.
`ADR-002` §2 anticipates this ("a convention alone will be broken by the third
developer on a Friday") and offers `test_scoping.py` as the second mechanism,
but that test proves the columns exist and are indexed, not that any query
filters, and its own ponytail note says so.

**Recommendation to cto — escalation, not a review comment, because it touches
`ADR-002` §2:** make the gated read the *default manager* on every model
carrying `is_seed` — `Listing.objects` gated, `Listing.all_objects` explicit —
so that forgetting the gate requires typing `all_objects`, which both a
reviewer and a grep can see. That is the same one-helper discipline `ADR-002`
asked for, moved from convention to default, and it is less code in every
service function rather than more.

**Summary of the gate's three parts, as of the end of S0:**

| `ADR-002` §4.1 part | State |
|---|---|
| (a) the nullable column, NULL = closed | **Guarded on the way in, unguarded on the way out.** Default correct; write path open (M0) |
| (b) `gate_authorisations` + the evidence-checked command | **Holds.** Append-only, evidence-complete, named human, refuses and exits 1, audited. Well tested. Add S4, S5, S9 |
| (c) seed/real separation | **Not yet built, honestly reported.** `restrict_when_gate_closed` exists and is unit-tested against a stand-in; the CHECK is S4; the end-to-end property is S3's. Nothing can cross the boundary today because nothing crosses it at all |

### 5.2 The append-only audit trail — holds on SQLite; unverified on Postgres; one hole now proven rather than suspected

The plpgsql was reviewed as text, since it is unparsed here. **I found no
syntax error and no wrong `OLD`/`NEW` reference.** Specifically:

- `gate_authorisations_is_append_only()` tests
  `IF TG_OP IN ('DELETE', 'TRUNCATE')` and raises **before** touching
  `NEW`/`OLD`. This is the detail that matters most in the whole migration:
  `OLD` and `NEW` are unassigned in a statement-level trigger, so had those two
  blocks been written in the other order, the `BEFORE TRUNCATE` guard would
  have failed with "record new is not assigned yet" instead of blocking the
  truncate — a guard that deploys and protects nothing, which is exactly the
  failure mode this review was asked to hunt. The ordering is correct.
- `audit_log_is_append_only()` raises unconditionally, so control never reaches
  the end of the function and the absent `RETURN` is not a defect.
- Format strings carry one `%` and one argument each; arity is correct.
- `IS DISTINCT FROM` on a `jsonb` column is valid (jsonb has equality).
- The immutable-column list covers every column except `revoked_at` and
  `revoked_reason`, which is what `DATA-MODEL.md` §1 specifies, and
  `close_discovery` touches only those two.
- `PG_REVERSE` drops triggers before their functions, so the reverse succeeds;
  verified by reversing and reapplying 0002 on SQLite, and the dependency order
  is correct for Postgres by inspection.
- `_run` raises `RuntimeError` for any third vendor — fail-closed.

**Verified properties:** the chain cannot fork (`prev_hash` UNIQUE, a duplicate
insert raises); a tamper is detected (the test drops the guard, rewrites a row
and `verify_audit_chain` names that row's id); an audit row rolls back with its
transaction; UPDATE, single-row DELETE and whole-table DELETE are all refused.

**The hole:** §3.6's TRUNCATE guard — which the author rightly calls the single
most important thing for a Postgres box to confirm — collides with Django's own
Postgres flush, which I confirmed is `TRUNCATE` (M5). So the first Postgres run
presents a choice between a working test harness and the TRUNCATE guard, on the
slice that needs both. The guard is right; the harness interaction was not
foreseen, and §7.1 asserts the opposite.

### 5.3 P14 — the control is real, and it has two name-shaped holes, one of them the exact exception CG-5 withdrew

The structure is right and better than the ADR requires: a live-schema
deny-list, a per-transaction-table money ban, a table-name check, and a
one-money-column assertion broader than the other three that does most of the
real work.

Against the charter's question — **can the deny-list be defeated?** Yes, three
ways, two of them inherent and one a defect:

- **A differently-named column: yes, verified.** `settlements.amount_minor`,
  `settlement_records.consideration`, `receipts.total_inr` and
  `handovers_cash.cash_received` all pass every test in the file (S7).
- **A jsonb blob: yes, by design.** `jobs.payload` and, from S3,
  `notifications.payload` are unexamined. The compensating control `ADR-003`
  §2.3 names — `test_forbidden_response.py` — does not exist and belongs to no
  slice (N2).
- **A computed property or a text field: yes, inherently.** A
  `@property settled_price` is invisible to schema introspection.

None of that is a deviation: `ADR-003` specifies a column-name control, and
§5.3 of the same ADR already concedes the deeper exposure is
`asking_price_paise` plus `state='COMPLETED'` and that the architecture cannot
fix it. **What is a defect is M1.** The `age_check_pending` exception the
2026-10-21 amendment explicitly withdrew is still in the file, so
`age_check_pending.date_of_birth` passes today, and the comment beside it cites
`DATA-MODEL` §2 for the opposite of what §2 now says. A legal control with a
naming-convention-shaped hole is not a control; a legal control still carrying
a withdrawn exception is worse, because the withdrawal is recorded and the code
is not.

The exposure is real and the threshold is nil (s393 Table Sl. 8(v): "any
e-commerce operator", 0.1% of gross amount, threshold nil). M1, M2, S6, S7 and
N2 are the whole of what I would change here, and none of them is more than a
few lines.

---

## 6. Tests that pass for the wrong reason

0. **`tests/unit/test_gate.py`, as a file.** 21 passed, 1 skipped — every
   assertion correct, and together they read as "the gate is enforced". What
   they verify is the *authorisation machinery*: 14 of the 21 drive
   `open_discovery` or `close_discovery` and establish that it refuses without
   complete evidence. Not one asks whether the column those commands guard can
   be written by anything else. The four `assert_discovery_open` cases test it
   against an in-memory object whose attribute the test sets by hand —
   `test_assert_discovery_open_passes_once_opened` (line 42) assigns
   `closed_campus.discovery_enabled_at = timezone.now()` and never saves it, so
   even that case never exercises a write to the column. A suite that only ever
   opens the gate through the front door cannot discover that the back door is
   unlocked. **M0.** The missing assertion is three lines and is now written,
   in test-qa's
   `test_s0_surface.py::test_the_gate_column_cannot_be_opened_outside_the_authorised_command`.
1. **`test_forbidden_schema.py::test_conditionally_forbidden_columns_only_where_permitted`**
   — green while permitting the DOB table amendment A-5 deleted (M1).
2. **`test_operational.py::test_a_hostile_request_id_is_replaced_not_echoed`** —
   tests `"abc\ninjected: yes"`, a mid-string newline the regex rejects
   anyway. The trailing newline is the only position that gets through, and it
   is untested (S1).
3. **`test_jobs.py::test_claiming_is_a_compare_and_swap_so_a_locked_job_is_skipped`**
   — the behaviour it asserts *is* M4. It passes, and what it demonstrates is
   that a job locked by a dead worker is never run again. The test enshrines
   the bug.
4. **`test_gate.py::test_restrict_when_gate_closed_adds_the_is_seed_predicate`**
   — asserts against a hand-rolled `FakeQuerySet`, so it proves the helper
   calls `.filter(is_seed=True)` and nothing about any real query or any
   caller. Honestly labelled in its docstring, and no stronger test is
   available in S0 (no S0 model has an `is_seed` column) — but the name reads
   stronger than the assertion, and the risk it does not touch (a caller that
   forgets the helper) is the one that matters.
5. **`test_scoping.py::test_every_tenant_scoped_model_has_both_keys_not_null`**
   — iterates zero models today and closes with `assert checked >= 0`, which
   cannot fail (N8).
6. Not wrong-reason, but the same caveat applies and the suite says so itself:
   every assertion in `test_partial_unique_index_engine.py` and every
   `*_mechanism_*` test passes **on SQLite, about SQLite**. The filenames,
   docstrings and the `engine` fixture all make that explicit, which is why
   they belong in the "right reason" column.

---

## 7. Praise — what to repeat

- **Every trigger assertion catches `django.db.DatabaseError`, the common
  parent**, exactly as `ENGINE-DIVERGENCE` §3.8 instructs. I checked all of
  them; the claim holds. SQLite raising `IntegrityError` where Postgres raises
  `InternalError` from a trigger is the single most likely engine trap in this
  codebase, and it was closed before anyone hit it.
- **`ENGINE-DIVERGENCE.md` itself.** A per-item verified/assumed/unverified
  ledger is worth more than most of the code it describes, and §5.3 — "a
  skipped test tells the truth; a green one does not" — is the right instinct
  stated at the right level of force. The two places the document is wrong
  (§7.1, and deviation 2's missing half) are both findable *because* it exists;
  without it they would be discovered in S4 by a failing CI run nobody could
  explain.
- **Skipping rather than faking, with a companion test for the engine
  capability.** `test_price_immutable`, `test_seed_separation` and
  `test_gate::test_non_seed_listing_*` are each skipped with the slice named,
  and each ships a probe proving the mechanism the real assertion will rest on
  — that this engine aborts an UPDATE from a BEFORE UPDATE trigger, that it
  enforces a two-column CHECK on INSERT and UPDATE. That is how to write a
  guard before the thing it guards.
- **The accounts stubs and `test_stubs_are_honest.py`.** Every stub raises, the
  message names the slice and forbids working around it, and the test pins both
  the frozen signature and the raising. A stub returning a plausible `User` is
  how a whole slice gets built against nothing, and it was designed out rather
  than warned about.
- **Log injection is prevented structurally, not by a deny-list.** The whole
  line goes through `json.dumps`, which escapes newlines and quotes
  unconditionally, and `_RESERVED` is derived from a live `LogRecord` so it
  survives a Python upgrade. (S2 is a gap in which *fields* win, not in the
  escaping.)
- **`close_discovery` is deliberately easier than `open_discovery`**, with the
  asymmetry reasoned in the docstring: "a wrong close costs a day of discovery,
  a wrong open is operating an e-commerce platform the company is not yet
  permitted to operate." That is the right default and the right way to record
  why.
- **The gate checklist prints every item's state with its Gate number and
  refuses on the first missing one.** An operator is told what to go and get,
  which is the difference between a control and an obstacle.
- **Nothing is over-built.** No dependency that a few lines replace (two
  runtime packages, the rest commented with the slice that turns them on), no
  abstraction with one implementation, no scaffolding for S4. The `ponytail:`
  notes name real ceilings with real upgrade paths. I looked for over-building
  as hard as for under-building and found one unreachable `or` (S5) and one
  redundant `and` clause (S4).

---

## 8. Verdict

**CHANGES REQUIRED.** S0 does not integrate as it stands.

S0 integrates once **M0–M5** are fixed. Re-review covers those six only; the
twelve should-fixes may land as follow-up commits inside S0 and I will take
them on trust if each is referenced in its commit message. The architecture is
right, the code is small and plain, nothing is over-built, and the author's own
account of what they could not verify is the most valuable artefact in the
slice.

**M0 is a blocking condition on its own.** It is the one finding that is not a
matter of degree: `ADR-002` §4.1(b) asserts a property the code does not have,
about the control that makes building before incorporation lawful, and the
mechanism to fix it is already in the repository applied to the table next
door. Everything else here could ship behind it; this cannot.

Of the rest, M1 and M3 are the two that would be expensive later — a legal
control carrying a withdrawn exception, and a correctness bug that lands in
every S4 transition endpoint. M4 and M5 are two lines and a document correction
each. M2 is three.

**On the shape of this review.** Two independent passes found two different
halves of the gate problem: this one found that the gate is opt-in per call
site for every future reader (§5.1, the default-manager recommendation);
test-qa's found that the gate's own column is writable. Neither pass would have
been sufficient. That is the argument for `CLAUDE.md` rule 5 in one slice, and
it is worth recording while it is concrete.

**Escalations to cto** (charter: always a founder escalation path, never a
review comment):

0. **M0 touches `ADR-002` §4.** Either the column gets the trigger, or §4.1(b)
   loses the sentence that says it cannot be opened by an UPDATE. The first is
   correct; the second must happen if the first is declined, because a contract
   that overstates its own control is worse than one that admits a gap — §4.2
   already models how to admit one honestly. **cto decides; this agent will not
   approve S0 with the sentence and the gap both in place.**
1. **M1 and M2 touch `tests/unit/test_forbidden_schema.py`**, a P14 guard file.
   Both fixes need cto sign-off citing amendment A-5 / `ADR-003` §2.1 in the
   same commit. M1 is a reverted control, not a new requirement.
2. **`ADR-001` §2.4** — the one-line amendment for the job-claiming mechanism,
   conditional on M4.
3. **`DATA-MODEL.md` §1** — amend `email_domains` to `jsonb`.
4. **`ADR-002` §2** — the default-manager recommendation in §5.1. A decision
   worth taking before S2 creates the first `is_seed` model, not after S3
   queries it.
5. **`TASKS.md`** — three defects: S0 scopes `ruff`/`mypy`/CI while §1 assigns
   CI to a dormant agent (N11); S0's fourth "done when" is unmeetable (N12);
   and `test_forbidden_response.py` plus the CSP header are named controls with
   no owning slice (N1, N2).

**The one thing checked last and most carefully** (before M0 arrived and
displaced it): the body of
`gate_authorisations_is_append_only()`, specifically whether the `TG_OP` guard
precedes the `NEW`/`OLD` field access. It does. Had it not, the `BEFORE
TRUNCATE` guard that S0's own divergence document calls its largest unverified
claim would have deployed, failed on an unassigned record, and protected
nothing — and no test on this machine could ever have told anyone.

**Coverage this review does not imply.** It covers code, contract fidelity and
the tests the author wrote. test-qa's trees arrived mid-review and are
triaged in §0 but not reviewed — they are test-qa's files and its own QA-S0
report is the place for them; where they and this review disagree, the §0
triage says which. **Every test in this slice ran on SQLite.** Per
`ENGINE-DIVERGENCE.md` that is a weaker statement than it looks: the Postgres
halves of both append-only triggers remain unexecuted text, the double-booking
guard is verified nowhere, and M5 says the first Postgres run will break the
harness before it confirms any of it. A local PostgreSQL 16 is the highest-value
Rs 0 action available to this project and `ENGINE-DIVERGENCE.md` §9 item 3 is
right that the trigger for it is earlier than it looks.

---
---

# PART TWO — RE-REVIEW OF THE REWORK

**Date:** 2026-10-21 · **Scope:** the six must-fixes M0–M5, the deferred
default-manager judgement, the ADR-003 suffix-list change, and anything the
rework introduced. Everything above this line is the original review and is
left unedited so the history of what was found reads straight through.

**Verdict: APPROVED. S0 integrates.** All six must-fixes verified fixed by
execution, not by reading the author's account. Two new should-fixes and two
notes below; none blocks. Both deferred judgements ruled on.

---

## 9. What I ran, and what it showed

`.venv/Scripts/python.exe -m pytest` → **6 failed, 298 passed, 51 skipped**.
All six failures classified below; none is an S0 defect. Plus:
`migrate` from empty → `migrate core zero` → forward again, all clean with
0003 and 0004 added; `seed_demo`; `open_discovery` refusing with no evidence
(exit 1); `open_discovery` succeeding through the real command path with a
complete authorisation; `close_discovery`; `verify_audit_chain` (2 rows, clean
head). Four fresh probes, listed inline. Marked **[verified]** where I executed
rather than read.

### 9.1 The six must-fixes

| | Claim | Verdict |
|---|---|---|
| **M0** | `BEFORE INSERT OR UPDATE` trigger on `campuses` | **FIXED** |
| **M1** | all three DOB patterns → `None`, pinned | **FIXED** |
| **M2** | dissolved by the whitelist, 17 columns pinned | **FIXED** |
| **M3** | `endpoint` compared alongside `request_hash` | **FIXED** |
| **M4** | stale lock reclaimable by timeout | **FIXED** |
| **M5** | TRUNCATE guards gain one declared session escape | **FIXED (text only — no Postgres)** |

**M0 — verified across every write path I can reach**, which is the right test
because the defect was never about the paths that existed:

| Write path, campus with **no** authorisation row | Result |
|---|---|
| `Campus.objects.filter(pk=…).update(discovery_enabled_at=now())` | **blocked** |
| `campus.discovery_enabled_at = now(); campus.save(update_fields=…)` | **blocked** |
| `Campus.objects.create(…, discovery_enabled_at=now())` | **blocked** |
| raw `UPDATE campuses SET discovery_enabled_at = …` via cursor | **blocked** |

and with a live Gate C authorisation the same update is **allowed**, so the
guard is a floor and not a wall. Wrong-campus (`scope_id` of another campus),
wrong-gate (`gate='B'`) and wrong-scope (`scope_type='GLOBAL'`) authorisations
are each **refused** — the three selectors I asked for a test of in S9 are now
enforced in the database, which is better than the test I asked for. Creating a
closed campus (`seed_demo`'s path) and renaming a campus both still work, so
the guard does not fire on non-gate writes. Note that the raw-SQL path is now
blocked too: `ADR-002` §4.2's concession that this is unprotected is, on this
one column, no longer true, and §4.2 could say so.

**The close-always-permitted asymmetry: ruled correct**, and for the reason
given. Setting the column to NULL can only ever *close*; there is no input to
the closing branch that opens anything, so the branch cannot be turned into a
bypass. The two failure modes are not symmetric: permitting an unauthorised
close costs a day of discovery, while forbidding a close would brick an open
campus whose authorisation has already been revoked — an open gate nobody can
shut, which is the legal exposure the whole control exists to prevent.
**[verified]** closing with no live authorisation is allowed, and
`close_discovery` works end to end — which matters because the command nulls
the column and revokes the authorisation in the same transaction, so a
symmetric guard would have deadlocked the one operation that must never fail.
This is the kind of exception that is occasionally wrong; here it is right, and
the asymmetric reasoning is recorded in the migration rather than left to be
re-derived.

**M1 — [verified] by QA's own adversarial test turning red**:
`test_demonstration_a_dob_column_passes_the_shipped_control` now fails with
*"P14 violation: age_check_pending.date_of_birth — permitted only at nowhere"*.
A test written to demonstrate the hole, failing because the hole is closed, is
the strongest available evidence. `test_the_withdrawn_dob_exception_is_gone`
pins it against a careless revert.

**M2 — fixed better than I specified.** I asked for `price_fixed_at` to be
allow-listed; the whitelist dissolves the problem instead — `price_fixed_at` is
a timestamp, so W1a never examines it. The 17 contract-mandated columns pinned
in `test_the_contract_mandated_columns_are_not_false_positives` are the right
generalisation: the defect class was "a guard test red on a column a frozen
contract requires", and that now has a test of its own.

**M3 — [verified].** Key `k-1` answered `201` on `POST /api/v1/offers`, then
the same key and body on `POST /api/v1/transfers/9/accept` → `IdempotencyKeyReused`
(409). A genuine replay (same key, same endpoint, same body) still returns the
stored response. Both halves correct.

**M4 — fixed, with one addition I did not ask for and would have.** The
claimable predicate is applied in both the candidate `SELECT` and the
compare-and-swap `UPDATE`, and after a successful claim the code re-reads the
row and skips it if `locked_by` is not this worker — cheap insurance against a
re-claim between the update and the fetch. `JOB_LOCK_TIMEOUT = 15 minutes`, and
the `ponytail:` note names the real ceiling (a handler legitimately exceeding
the timeout runs twice, safe only because handlers must be idempotent) with the
right upgrade path. `test_jobs.py`'s renamed test no longer asserts the losing
behaviour.

**M5 — correct as text; unverifiable here.** `bookhop_truncate_guard()` reads
`current_setting('bookhop.allow_flush', true)`, which yields NULL when unset,
so `NULL = 'yes'` is NULL, the `IF` is not taken and the function raises.
Default-deny by construction rather than by a default value someone can edit —
the right shape. Returning NULL from a statement-level `BEFORE TRUNCATE`
trigger does not cancel the statement, so the escape genuinely permits the
flush. `UPDATE` and `DELETE` get no escape, which keeps the append-only
property whole. §7.1 is corrected and now states the collision, the measurement
and the resolution; it also tells a Postgres session exactly what to set.
0002 is left untouched so an already-migrated database moves forward — right
call. **Still `UNVERIFIED`: no plpgsql in this repository has been parsed by a
server, and that remains the largest unverified thing S0 ships.**

Reading the new plpgsql as text, as with 0002: the `INSERT` branch returns
**before** the `OLD`-dependent comparison, so `OLD` is never touched on an
insert; `IS NOT DISTINCT FROM` is the correct null-safe equality for the
no-change early return; the SQLite `WHEN` clause is the faithful equivalent
(`IS NOT`, `NEW.active = 0`, correlated `NOT EXISTS`); and the message is
interpolated into both bodies from one constant, so the two engines cannot
drift in what they say. The `ENABLE ALWAYS` lines close N7. I found no syntax
error and no wrong `OLD`/`NEW` reference.

---

## 10. New findings — what the rework introduced

### R1 (should-fix) — W1b exempts the whole `listings` table, so a *second* money column on `listings` passes every layer
`tests/unit/test_forbidden_schema.py:124` (`MONEY_WORDS_EXEMPT_TABLE = "listings"`)

W1a permits any numeric column whose name ends in a declared non-monetary name;
W1b forbids money-shaped names everywhere **except the `listings` table**.
Individually both are defensible. Composed, they leave the one table that is
allowed to hold money as the one table where a second money column is
unguarded.

**[verified]** each of these passes W1a, W1b, W1c and the deny-list:

```
listings.paise_count          listings.rupees_count
listings.cash_total_count     listings.amount_count
listings.consideration_count  listings.handover_value_count
```

The same names on `transfers` are caught by W1b. `ADR-003` §2.1 says "exactly
one money column in the entire database", and
`test_there_is_at_most_one_money_column_and_it_is_the_permitted_one` uses the
same suffix filter, so it does not catch them either.

Not a regression — before the rework these passed on *every* table — but the
rework's own standard is higher, and the fix is the pattern backend already
applied elsewhere in the same file: when QA found `legal_entities.pincode`
passing, they rescoped the exemption from a table to a column
(`CONDITIONAL_COLUMNS["address"] → ("legal_entities", "registered_address")`).
**Fix:** do the same here — exempt `{("listings","asking_price_paise"),
("listings","price_fixed_at")}` rather than the table. Two lines, and
`test_the_contract_mandated_columns_are_not_false_positives` already pins both
columns so the change cannot break S2.

### R2 (should-fix) — `all_typed_columns()` lets model meta override introspection *for types*, which inverts W1c's stated purpose
`tests/unit/test_forbidden_schema.py:321-326`

W1c exists because "names carry no types" and QA's attack 7 declared
`asking_price_paise` as `real` in raw DDL. But the merge is
`merged = introspected_types(); merged.update(model_schema())` — model meta
wins. **[verified]** a `real` column is reported as `FloatField` only when no
model declares it; where a model does, the model's declared type is what the
assertion sees. In S0 `listings` has no model, so attack 7 is caught. **From
S2 it has one**, and an out-of-migration `ALTER COLUMN … TYPE real` would be
masked by the model's `IntegerField` — the exact scenario the docstring cites.

The precedence is right for *names* (a declared field is the stronger fact) and
backwards for *types* (the whole point is to see what the database actually
holds). **Fix:** for the float check only, fail if *either* route reports a
float — a union rather than an override.

### R3 (note) — anonymous idempotency is now a single global namespace
`apps/core/migrations/0004_anonymous_idempotency_key.py`

Correctly fixes QA's B3: `UNIQUE (user_id, key)` treats NULLs as distinct, so
anonymous requests previously got no idempotency at all. The partial unique
index on `key WHERE user_id IS NULL` is the available fix. The consequence
worth recording: anonymous keys now share one namespace across all callers, so
the stored response body of an anonymous request is returned to anyone
presenting that key. For `POST /auth/magic-link` that is harmless — it always
returns 202 with nothing in it (`API-CONTRACT` §5.1). For
`POST /grievances` (§5.6, unauthenticated, returns a `ticket_ref`) it is a
disclosure gated only on guessing a UUIDv4, which is not a feasible attack but
is a property someone should have chosen rather than inherited. **S6 should
confirm no anonymous endpoint stores anything in `response_body` that its
`ticket_ref` does not already reveal to the person who filed it.** Also a
schema change not in `DATA-MODEL.md` §5 — it needs its amendment line.

### R4 (note) — `ENGINE-DIVERGENCE.md`'s header still says `Version: v1.0`
Line 3, while the amendment log records v1.1 with a full and accurate entry.
One line. Mentioned only because this document is the one a future developer is
told to trust before trusting a green test run.

---

## 11. Ruling — the default-manager timing

**S2 is the right slice. Backend's deferral is correct and I withdraw any
implication that it should have landed now.** Three reasons:

1. **There is nothing to attach it to.** S0 creates no model with an `is_seed`
   column. A `Manager` subclass with zero models is an abstraction with one
   implementation and no caller — precisely what this project's engineering
   standard forbids and what I would have flagged had it shipped. I asked for
   the decision to be taken before S2, not for the code to exist before its
   models.
2. **The risk window is S3, not S2.** The first discovery read path is S3's
   `search_listings`. Landing the manager in S2, with the models, puts it one
   full slice ahead of the first query that could forget the gate. That is the
   right margin: earlier buys nothing, later is a retrofit across live call
   sites.
3. **Deferring costs no rework**, as backend argues: S2 creates `Listing`,
   `ListingPhoto` and `BookRequest` together, so the manager lands in the same
   commit as the fields it filters.

**Three conditions, because "S2" is otherwise a promise and this project has
twice now been bitten by a named control with no owning slice (N1, N2):**

- **(a) It goes into `TASKS.md` §2 S2's scope and its definition of done now**,
  as a line item, not into anyone's memory. cto owns that edit. A deferral
  recorded only in a review and a reply is the same failure as
  `test_forbidden_response.py`.
- **(b) `Meta.base_manager_name` must be set to the unfiltered manager**, per
  the CTO's first footgun, which is real. Django uses `_base_manager` for
  related-object descriptors, cascade collection and `refresh_from_db`; a
  default manager that filters rows out can make those silently fail to see a
  row that exists. One line per model, and it is the kind of line that is
  invisible when missing — which is why it belongs in the condition rather than
  in a reviewer's head.
- **(c) The reverse-relation gap is closed by a test, not by reasoning.** The
  CTO's second footgun is also real, and the honest position is that which
  access paths see the filtered manager differs by path and by Django version —
  direct queries, reverse accessors, `prefetch_related` and cascade do not all
  resolve the same manager. That is not something to settle by argument. S2
  should ship a test that, for each gated model, asserts the gate applies on a
  direct query *and* on the reverse accessor, and that `_base_manager` is
  unfiltered. If the test shows reverse relations are not covered, the manager
  is defence in depth and the service layer remains the control — which is
  fine, but it must be known rather than assumed.

**One design point that falls out of ruling on the timing, and matters more
than the timing.** The manager is **not** a substitute for
`assert_discovery_open`. A filtered manager makes a closed campus return *no
rows*; `API-CONTRACT` §2.5 step 7 and §5.3 require a real student on a closed
campus to receive **`403 GATE_CLOSED`**, and the frontend's empty state must
keep "not on your campus yet" apart from "we don't recognise that ISBN"
(`TASKS.md` S3's three truths). If S3 lets the manager stand in for the helper,
a closed campus silently renders an empty search page instead of the
`GATE_CLOSED` page, and the legal gate becomes invisible to the person it
applies to. **The manager sits underneath the helper, never instead of it** —
worth stating in the ADR-002 amendment so it is not discovered in S3.

---

## 12. Ruling — the ADR-003 suffix list read as bare names, plus `status`

**This is a vocabulary clarification, not a money widening. It stands, on
condition that cto ratifies the wording in ADR-003 §2.3 W1** — which backend
has already escalated (`ENGINE-DIVERGENCE` §9 item 6), and which should be
closed before S2 rather than carried.

The test I applied is not "does the diff touch an escalation-protected file" —
it does, and so will every legitimate fix to that file — but **"does the change
alter what money may be stored?"** It does not. The thirteen names are `id`,
`count`, `seconds`, `minutes`, `attempts`, `bytes`, `width`, `height`, `year`,
`position`, `version`, `no`, `status`. None denotes a currency, an amount or a
consideration; `total`, `sum`, `value`, `cash` and `rate` are all correctly in
`MONEY_WORDS` instead. `status` specifically admits
`idempotency_keys.response_status`, an HTTP status code, which is mandated by
`DATA-MODEL.md` §5.

And the counterfactual settles it. Read as suffixes only, the list rejects
`jobs.attempts`, `listing_photos.width`, `height`, `bytes`,
`support_work_log.seconds`, `search_result_opens.position` and
`idempotency_keys.response_status` — **seven columns frozen contracts
mandate.** Refusing the clarification would have recreated M2 seven times over:
a P14 guard test red on columns the contracts require, with the tempting fix
being an edit to a founder-escalating file. The clarification removes false
positives; it adds no true negative.

**Why ratification still matters, rather than being a formality.** The
escalation bar on this file is only credible if the provenance of
`NON_MONETARY_NAMES` is in the ADR. The next person to add a name must face a
real bar, and they cannot if the list's authority is a comment in a test
written by the developer the bar exists to constrain. One wording change in
§2.3 W1 and the bar is restored.

**The one caveat, and it is R1.** The suffix allowance is safe *on its own* and
safe *in combination with W1b everywhere except `listings`*. Composed with
W1b's table-wide exemption it opens the hole in R1 — `listings.paise_count`
passes. So: the vocabulary change is not the money widening, and there is a
money widening, and they are not the same decision. Fix R1 and the ruling above
needs no revisiting.

**On the quiet-narrowing hunt.** Backend reports its own guard-of-the-guard
caught `rupees_exchanged` escaping every layer until `rupee` and `paise` went
back into the word list. I checked the rest of the rewrite for the same shape
by diffing the old vocabulary against the new: nothing else was lost. `fee`
moved from `MONEY_WORDS` to the deny-list with an explicit `FEE_ALLOWED` pair,
which is a *tightening* and is documented; `ledger_entry` became `ledger`,
which catches Django's `ledger_entries` pluralisation and is also a
tightening; `value_paid` is subsumed by `value`; `vpa` became a substring and
`pan_card` was added, both as I asked in S6. Everything else is new coverage.
`test_the_control_would_catch_each_known_attack` is the reason the one
narrowing was caught during the rewrite rather than after it, and it is the
single best addition in this rework — see the praise below.

---

## 13. The six failing tests, triaged

Five are QA characterisation tests failing **because the defect they document
is fixed**. I confirmed each by its failure mode, not by its name:

| Test | Fails with | Means |
|---|---|---|
| `test_s0_surface::…gate_column_cannot_be_opened_outside…` | the 0003 trigger's error | **M0 fixed** |
| `test_p14::test_demonstration_a_dob_column_passes_the_shipped_control` | `P14 violation: age_check_pending.date_of_birth` | **M1 fixed** |
| `test_idempotency_contract::…different_endpoint_is_still_the_same_key` | `IdempotencyKeyReused` | **M3 fixed** |
| `test_idempotency_contract::…anonymous_request_gets_no_idempotency_at_all` | `Replay` | **B3 fixed** (R3) |
| `test_gate_journey::…inactive_campus_can_still_have_an_open_gate` | `GateClosed` from `scoping.py:91` | **QA B1's read half fixed** |

The sixth, `test_p14::test_p14_is_not_guaranteed_by_naming`, is the genuine
disagreement. I am not settling it, as instructed, and QA is re-pointing it at
the shipped control. One observation for whoever does settle it: on the two
specifics, **the shipped control catches a related settlement table**
(`transfer_settlements`, `settlements` and `handovers_cash` all fail W1b's
table-name limb — verified) **and catches float money today but not
necessarily from S2** (R2 — the model-meta override masks it once `listings`
has a model). So the likely resolution is that backend is right about the
related table and QA is right about float money for the wrong reason: the type
check exists, and its merge precedence will stop it working on the one table it
was written for. Fixing R2 makes both claims true at once.

**Suite red is therefore not evidence either way**, exactly as the coordinator
said. A re-pointed characterisation suite should go green on everything except
whatever survives R1 and R2.

---

## 14. Praise — the rework

- **`test_the_control_would_catch_each_known_attack`.** A unit test of the
  predicates against a hardcoded attack list, which by construction cannot pass
  vacuously the way a loop over an empty schema can — the defect class this
  project has now named four times. It caught a real narrowing *while the
  rewrite was being written*. That is a guard-of-the-guard that earned its
  keep on day one, and its sibling
  `test_the_contract_mandated_columns_are_not_false_positives` closes the other
  direction. Both should be the template for every future control in this
  codebase.
- **Deny-list → whitelist.** The right structural answer to S7, and a better
  one than I proposed: I asked for more words in the list, and compliance was
  right that more words is what a blacklist always needs. Inverting the burden
  so `transfers.value_x` fails on sight, without anyone having predicted the
  name, is the change that actually moves P14 from "a list someone maintains"
  to "a property of the schema".
- **M0's asymmetry is reasoned in the migration, not just implemented.** The
  three-line explanation of why closing is always permitted is exactly what a
  future developer needs to not "fix" it. Same for the `INSERT`-must-be-NULL
  branch, which removes the `NEW.id` question rather than answering it.
- **Fixing M2 by dissolving it.** The requested allow-list entry would have
  worked and left the defect class alive. Pinning 17 contract-mandated columns
  against future tightening addresses the class.
- **§7.1's correction says what it previously got wrong, and why.** A document
  that records its own reversal with the measurement that forced it is worth
  more than one that was right the first time and does not say how it knows.
- **N4 taken as recommended, with the ceiling removed rather than scheduled.**
  `find_spec` asks the one question that matters and lets a genuine
  `ImportError` propagate. The comment now ends "nothing here needs deleting
  later", which is the point.
- **S10 fixed better than asked.** I suggested deleting the stale table name;
  backend replaced it with an explicit paragraph stating the table does not
  exist and why. A negative statement blocks the recreation; a deletion merely
  stops suggesting it.
- **S5 is visible in the command's own output.** The checklist now prints
  `campuses.active` and
  `gate_authorisations.legal_entity_id == campuses.legal_entity_id`, so the
  reconciliation is something an operator reads rather than something a
  reviewer hopes for.

---

## 15. Revised verdict

**APPROVED.** S0 integrates.

M0–M5 are fixed and verified by execution. R1 and R2 are should-fixes on the
P14 guard file: both are narrower than the exposure that existed before the
rework, neither is reachable until S2 creates `listings`, and both are two-line
changes that should land **with S2 rather than before it**, in the same commit
as the ADR-003 §2.3 W1 wording ratification — one escalation, three changes,
rather than three trips. R3 and R4 are notes.

The twelve should-fixes and thirteen notes from Part One that I checked in
passing are done where I looked (S1 `fullmatch`, S2 `_COMPUTED`, S3
`new_worker_id`, S4/S5 in the gate checklist, S6 `vpa`/`pan_card`, S8 in
`live_schema`, S10, N4, N7 `ENABLE ALWAYS`, N8, N9). I did not re-verify every
one and do not need to: none gates integration.

**Correctly not done:** N1 (CSP) and N11 (lint/CI) — both were ownerless or
contradictory in `TASKS.md`, which was the finding rather than the task. cto
has since assigned CSP to S1. N11's contradiction still stands and still wants
a `TASKS.md` edit.

**The one thing checked last and most carefully, this round:** the
close-always-permitted branch of the `campuses` trigger — whether a write that
reaches it can be made to *open* the gate rather than close it. It cannot: the
branch is entered only when `NEW.discovery_enabled_at IS NULL`, and NULL is the
closed state, so the only reachable outcome is a closed gate. I then confirmed
by execution that the branch is load-bearing rather than merely harmless —
`close_discovery` revokes the authorisation in the same transaction as the
close, so a symmetric guard would have made the one operation that must never
fail depend on the row it is in the act of revoking.

**Coverage this approval still does not imply.** Every assertion in this slice
ran on SQLite. Four plpgsql bodies across migrations 0002 and 0003 — both
append-only guards, the gate write guard and the truncate escape — have never
been parsed by a PostgreSQL server. The double-booking guard is implemented
nowhere and verified nowhere, correctly, because it is S4's. M5's resolution is
reasoning about Postgres behaviour, and reasoning is what a Postgres box
replaces. **Getting one before S2 is now the highest-value action available to
this project**, and three of this review's six must-fixes were in code that
only a Postgres box can actually verify.

---
---

# PART THREE — CLOSING PASS

**Date:** 2026-10-21 · **Scope:** the four S0 re-approval conditions, QA's ten
P14 findings, and the two judgements routed to me. Parts One and Two unedited.

**Verdict: APPROVED. S0 integrates. Nothing blocks.** One new should-fix (C1,
below), one contract amendment that must land before S1 (C2), and both routed
judgements ruled on.

---

## 16. What I ran

`tests/unit tests/api` → **214 passed, 28 skipped in 0.94s**, matching
backend's report; full suite **358 passed, 54 skipped, 12 failed in 9.00s** —
the 12 classified in §20 and none an S0 defect. The 9-second figure confirms
the quadratic float check is gone. Plus: `migrate` from empty through 0005 →
`core zero` → forward again, clean; `seed_demo`; `open_discovery` refusing with
no authorisation (exit 1) and succeeding with a complete one through the real
command path; `close_discovery`; `verify_audit_chain`; and five fresh probes.

### The four conditions

| Condition | Verdict |
|---|---|
| `apps/core/p14.py` + F6/F7 in one commit | **DONE** — W1b's 22 tokens all enforced and applied to *every* type, not only numeric columns, which closes the `receipts.amt text` class; the `listings` exemption is now scoped to two columns (my R1), with `MONEY_WORDS_EXEMPT_TABLE` retained as `None` so the change is visible rather than silent |
| conftest flush fixture | **DONE** — `allow_test_flush` sets `bookhop.allow_flush` on the harness connection, which is what §7.1 asked for |
| gate-evidence completeness CHECK | **DONE** — migration 0005, both engines |
| R2 union semantics through the perf fix | **DONE and verified** — see §18 |

---

## 17. C1 (should-fix) — the trim near-miss has siblings, and two of them pass every layer

Backend found that both engines' bare `trim()` strips spaces only, so a single
tab passed as a named human, and fixed it by trimming an explicit four-character
set: space, tab, LF, CR. **A trim-based blank check is a whitespace deny-list,
and four characters is not the whole list.** This is the class the coordinator
asked me to check for siblings in; the sibling is the fix itself.

**[verified]** `gate_authorisations.authorised_by_human`, gate C INSERT:

| value | DB floor (0005) | command (`.strip()`) |
|---|---|---|
| empty, space, tab, LF, CR | blocks | blocks |
| vertical tab U+000B, form feed U+000C | **ACCEPTS** | blocks |
| **NBSP U+00A0** (what a paste from Word produces) | **ACCEPTS** | blocks |
| figure space U+2007, ogham space U+1680 | **ACCEPTS** | blocks |
| **zero-width space U+200B** | **ACCEPTS** | **ACCEPTS** |
| **BOM U+FEFF** | **ACCEPTS** | **ACCEPTS** |

The evidence values behave identically: `campus_mou_ref` is accepted as a
signed MoU for all seven. Two consequences, and the second is the one that
matters:

1. **For five of the twelve forms the floor is weaker than the command it sits
   under.** Python's `str.strip()` uses the Unicode whitespace property and
   catches NBSP, VT, FF and the exotic spaces; the SQL trim set does not. "The
   floor beneath it" (migration 0003's phrase, which 0005 inherits) is in this
   one respect above the floor — which is QA's F8 complaint, that the floor was
   lower than ADR-002 §4.1(b) reads, recurring one level down inside the fix
   for F8.
2. **Zero-width space and BOM pass both layers.** So
   `authorised_by_human = "​"` opens the gate and renders as an empty name
   in the audit row, in `gate_authorisations`, and in the go/no-go packet — in
   the one field whose entire purpose is naming an accountable human.

**Not blocking**, and I want to be precise about why. The gate still requires a
complete evidence set, a live unrevoked Gate C authorisation scoped to that
campus, `active = true`, the campus/authorisation legal-entity match and the
five legal-entity facts; none of those is weakened. A zero-width name is a
quality-of-evidence defect, not a bypass, and it requires deliberately typing
an invisible character.

**It is also the same finding backend already asserted the bound of.** Their
`test_the_database_floor_does_not_check_whether_the_evidence_is_true` says the
floor checks that a box is *filled*, never that it is *true*. "Filled" turns
out to include "filled with nothing visible". **Smallest fix:** add U+000B,
U+000C, U+00A0, U+200B and U+FEFF to the two trim sets, and extend that
existing bound test with a `"​"` case so the sentence in the test covers
the shape as well as the content. Then say in ADR-002 §4.1(b) that
`authorised_by_human` is checked for presence only — which is already true and
is now the honest claim.

---

## 18. The two things I was asked to look hardest at, besides the siblings

**The bound test says exactly what it claims. [verified] and worth reading in
full**, because it is the sentence the go/no-go packet rests on. With every
evidence item set to the string `"TODO"`, `notice_version_ids = [1]` and
`authorised_by_human = "TODO"`, `open_discovery` prints **sixteen ticked
boxes** and opens the gate. Not a simulation of the control — the real command,
the real trigger, the real checklist. Asserting the bound of one's own fix, in
a test, with the demonstration rather than a sentence, is the single best habit
in this slice. It makes ADR-002 §4.2's "auditable, not correct" concrete
instead of aspirational.

**The float check kept its correctness through the perf fix. [verified].** The
precedence split is exactly right and is the part that could have been lost:
`typed_columns_for_names()` keeps model-meta-wins (correct for *names* — a
declared field is the stronger fact), while `all_type_reports()` returns the
**union** of what both routes report (correct for *types* — the point is to see
what the database actually holds). The float assertion fails if **any** route
reports a float and fails closed on an unclassifiable type. I tested the R2
case directly: a `real` column added by raw DDL to `jobs` — a table that *has*
a Django model — is reported `['FloatField']` and caught. Before R2 that was
masked. Both routes are read once per call rather than once per column, which
is the whole of the 72s → 9s fix. Correctness was not traded for speed.

**And the token-shape exemptions cannot swallow an attack. [verified]:**
`due_at`, `purge_due_at`, `act_due_at`, `sla_due_at`, `overdue` and
`consume_magic_link` match no money token, while `amount_due`, `due_paise`,
`total_due`, `due_inr`, `due_amount` and `cash_due` all match. Three narrow
*shape* exemptions, each answered against the ADR's own discriminating
question, each escalated rather than claimed as obvious — and `run_due_jobs`
was **renamed** to `run_pending_jobs` rather than earning an exemption. "Where
the name was ours, it was renamed instead of exempted; a tightening beats an
allowance" is the right instinct and should be the standing rule.

---

## 19. C2 (must resolve before S1, not blocking) — ADR-002 §4.1(b) now describes a workflow that cannot happen

Migration 0005 refuses the INSERT of an incomplete gate C authorisation, so a
*saved* row is always complete. ADR-002 §4.1(b) describes the opposite
workflow: the row exists, and "the command prints the checklist with each
item's state and exits non-zero on the first missing one." With 0005 the
command can never print a partially-ticked checklist for a saved row — the only
reachable incomplete state is "no row at all". **[verified]**: that is why
eight of QA's `test_gate_journey` tests now fail at fixture setup with
`IntegrityError` rather than at the command.

I checked ADR-002 and the complete-or-absent invariant **is not ratified
there**. Backend's escalation item 11 acknowledges the consequence and defends
it well — the checklist still tells an operator which item to fetch, and it is
tested directly on an unsaved row via `checklist(campus, auth=...)`.

**I agree with the choice and not with leaving it undocumented.**
Complete-or-absent is a cleaner invariant than drafts-allowed, and the control
is strictly stronger, so this is not a reason to revert. But it is the same
defect class as M5 inverted: M5 was a contract asserting a property the code
lacked; this is a contract describing an operator workflow the code has
removed, in the document the go/no-go packet rests on. ADR-002 §4.1(b) needs
one paragraph saying a gate C authorisation is written complete or not at all,
that the per-item checklist is a pre-flight affordance rather than a report on
a stored draft, and that an operator assembling evidence over days holds it
outside the database until it is complete. cto owns that edit. QA re-points
eight tests.

---

## 20. The twelve failures, classified

Eleven are QA characterisation tests failing **because the defect they document
is fixed** — eight in `test_gate_journey.py` (incomplete authorisations now
refused at INSERT, F8) and three in `test_idempotency_contract.py` (short
anonymous keys and replayed anonymous bodies, F10). The twelfth,
`test_migration_guards.py::test_no_test_in_the_repository_sets_the_flush_escape`,
is not a conflict with the M5 resolution I approved: QA's own docstring says
*"it will fail the day the fixture lands, which is the right moment to re-read
it."* The fixture landed. The test did what it was built to do.

**One substantive point in that test survives the fixture, and belongs in the
contract rather than in a QA docstring:** there is no mechanism by which
production could refuse `SET bookhop.allow_flush`. A custom GUC is settable by
any role in any session. The escape is therefore gated by THREAT-MODEL §4
B5/B6's accepted scope — direct SQL is out of scope — and not by anything
Django can enforce. §7.1 should say that in those words, because "a setting
production forbids" is a claim the mechanism does not support, and this project
has now twice been bitten by a document claiming a control it did not have.

---

## 21. Ruling — the anonymous-key UUID format scope

**Backend's narrowing is correct on the merits, and the coordinator is right
that it must be stated in `API-CONTRACT.md` §4.1 as a deliberate boundary.**

Correct on the merits: with `UNIQUE (user_id, key)`, an authenticated short key
can collide only with that same user's keys; M3 now compares endpoint and body,
so a collision with either different → `409 IDEMPOTENCY_KEY_REUSED`, and a
collision with both the same is by definition the same request, which is what
idempotency is for. There is no path to another principal's data. The anonymous
namespace is different in kind because it is global, which is why it needs the
format rule — and backend did not stop at the format rule but also made an
anonymous replay return `Replay(status, None)`, so no anonymous caller can
receive another's body even if a key is guessed. Defence in depth on a measured
disclosure (`{"grievance_ref": "GRV-000123"}` reaching a stranger, on
`/grievances`, which is the door a distressed non-user reaches us through).
That is the right shape and more than I would have required.

**Why it still needs writing down, and what to write.** The narrowing is safe
because of an invariant, not because of the conclusion: *`user_id` partitions
the key namespace, and every key in a partition is written by that one
principal.* State the invariant, not just the rule, because the conclusion is
what rots silently and the invariant is what a future developer can check
against their own design. Three ways it breaks, all reachable from the current
roadmap:

- **a staff tool acting on a student's behalf** — S5's support flow and S6's
  moderation put staff inside a student's objects; the moment any endpoint
  writes an idempotency key under the student's `user_id` on staff action, the
  partition has two principals and the anonymous namespace's property arrives
  in the authenticated one;
- **any impersonation or service-account path**, for the same reason;
- **`user_id` reuse after deletion** — narrow, but `ENGINE-DIVERGENCE` §2.10
  already records that SQLite reuses the max rowid after the highest row is
  deleted, and S1 adds purge. A reused id inherits the old user's unexpired
  keys for up to the 24-hour retention window.

So §4.1 should read, in substance: *an `Idempotency-Key` on an unauthenticated
request MUST be a UUID; on an authenticated request the format is
unconstrained. This is deliberate and rests on `user_id` partitioning the key
namespace with one principal per partition. If any endpoint ever writes a key
on another principal's behalf, the authenticated namespace acquires the
anonymous one's property and the UUID rule extends to it.* Three sentences, and
the third is the one that matters. Also: migration 0004's partial unique index
is a schema change not in `DATA-MODEL.md` §5 and still wants its amendment
line.

---

## 22. Ruling — `test_forbidden_response.py`, specified but absent

**I am content for S0 to integrate with it absent.** My original objection in
N2 was not that the control was missing — it is an S1 control for a response
schema that does not exist yet — but that it was *named by two frozen documents
and owned by nobody*, and that a named control with no owner is never written
while the packet quietly rests on it. Both halves are now closed, and the
second is closed better than I asked:

- it has an owner and a slice (backend, S1, in `TASKS.md`), as does W1c's
  source grep, assigned to S1's first commit;
- and **ADR-003 §5.3.1 makes the packet sentence incapable of overstating the
  control.** The G4 sentence now reads, in the version that gets used until the
  second is earned, that the two controls are *"specified and scheduled but not
  yet written, so the `@property`, jsonb and free-text residuals currently have
  no automated control"*. A conformance test in `tests/contract/` asserts that
  every control §5.3 names is present, so the ADR cannot claim one the
  repository lacks.

That last move is the right generalisation of the whole problem — the claim and
the check become one artefact — and it is W1d's principle turned on the ADR's
own prose. An absent control that the compliance document correctly reports as
absent is a known gap; an absent control the document claims is a false
statement to a regulator. S0 ships the first and not the second, which is what
I needed.

---

## 23. Closing verdict

**APPROVED. S0 integrates.**

All six must-fixes from Part One and both should-fixes from Part Two (R1, R2)
are fixed and verified by execution. **C1** (the whitespace deny-list bound) is
a should-fix for S1, best landed with the extension to the bound test that
already states the principle. **C2** (ADR-002 §4.1(b) describing a removed
workflow) is cto's amendment and must land before S1, because it is the
document the go/no-go packet rests on. Neither blocks.

**What I checked last and most carefully:** whether the perf fix to the float
check had quietly reverted R2 — because a union collapsed back into an override
would have looked identical in every green test, removed the only part of P14
that can be *checked* rather than named, and done it in a commit whose stated
purpose was speed. It had not: the union is explicit, the names/types
precedence split is documented, and a raw-DDL `real` on a modelled table is
still caught.

**What this approval still does not cover, in the strongest terms available.**
Nothing in this slice has executed against PostgreSQL. **Six plpgsql bodies
across migrations 0002, 0003 and 0005 — both append-only guards, the truncate
escape, the gate write guard and the evidence-completeness guard — have never
been parsed by a server.** Five of those six are the security controls this
review spent three passes on. They are reviewed as text by two agents and
verified by neither. The SQLite halves are exercised and green, and SQLite is
not the production engine. **A local PostgreSQL 16 costs Rs 0 and remains the
highest-value action available to this project**; after three review passes it
is now the only thing standing between "these controls are argued to work" and
"these controls are known to work."
