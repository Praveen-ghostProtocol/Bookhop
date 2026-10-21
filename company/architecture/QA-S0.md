# QA-S0.md — independent QA pass on slice S0

**Owner:** test-qa · **Version:** v3.0 · **Date:** 2026-10-21
**Slice:** S0 (skeleton, tenancy, gate, audit, jobs), after the second rework

# VERDICT: **PASS.** S0 is QA-green and clears for integration.

Every finding QA raised across three passes — F1–F3, F4–F10, B1–B3, and the
M3 misreading QA itself had asserted into the baseline — is fixed, and each is
now a regression test named for the finding it came from, so the history is
traceable from the suite rather than from this document.

**Nothing blocks integration.** Four items remain open; each is real, each is
non-blocking, and each is named with the slice it belongs to in §5. One of them
(B2) is open by agreement rather than by oversight.

**The standing qualification, unchanged and more load-bearing than before:**
nothing has run on PostgreSQL, and the Postgres-only surface grew again this
round. §6.

**v3.0 supersedes v2.0.** v2.0's §3 — QA's own correction, that v1.0's P14
attack measured QA's transcription rather than the shipped control — stands and
is not restated. v2.0's findings F4–F10 are closed below.

**Written from:** `ADR-002` §2, §4 · `ADR-003` §2.1–2.3 as amended (W1–W5) ·
`API-CONTRACT.md` §2.2, §2.5, §4, §5.8 · `DATA-MODEL.md` §1, §8 ·
`ENGINE-DIVERGENCE.md` v1.2 §3.4, §3.6–§3.6c, §3.8a, §4.3a, §7.1, §9 items 9–11
· `TASKS.md` §1–§4 · `PRD.md` AC-M6.1/AC-M6.3/EX-18 · `.claude/agents/test-qa.md`.

**Method.** Tests only in `tests/e2e/**`, `tests/a11y/**`, `tests/contract/**`.
No file under `bookhop/**`, `apps/**`, `tests/unit/**`, `tests/api/**` or
`tests/conftest.py` was modified in any of the three passes. Nothing QA found
was fixed by QA.

---

## 1. The command, and its real output

```
$ cd C:\CodingSpace\BookHop
$ .venv/Scripts/python.exe -m pytest
...
======================= 481 passed, 54 skipped in 8.11s =======================
```

Split by owner, same run:

```
$ .venv/Scripts/python.exe -m pytest tests/unit tests/api -q
261 passed, 28 skipped in 1.01s

$ .venv/Scripts/python.exe -m pytest tests/e2e tests/a11y tests/contract -q
220 passed, 26 skipped in 7.55s
```

**Zero failures.** QA's tree is 246 tests: 220 pass, 26 skip with an
engine-and-slice reason, none fails. Across the three passes QA's tree went
169 → 182 → 246 tests and 3 → 10 → 0 failures.

Engine: **SQLite 3.45.1**, Python 3.11.9, Django 5.2.8, no PostgreSQL server,
no Docker.

**One caveat on the measurement, stated because it would otherwise look like
flakiness.** Backend was still editing while this pass ran: an intermediate run
showed 12 failures that an immediate repeat did not, and the cause was QA's
tests reading backend's files mid-write —
`apps/core/migrations/0005_gate_evidence_complete.py` at 20:52 and
`tests/unit/test_forbidden_source.py` at 20:54. **The numbers above are from two
consecutive identical runs at 20:55 and are stable.** Four of QA's tests read
backend-owned source as data — the P14 conformance tests, the source-grep
coverage tests, the flush-escape inventory and the migration text audit — which
is deliberate, and is what caught F4 and F9. It does mean a QA run during an
active edit can report a failure that is neither a defect nor a flake. **This
verdict is against the tree as it stood at 20:55**; if further changes have
landed since, the conformance tests are the ones to re-run first, and they name
the list or the file that moved.

---

## 2. The twelve failures: classification verified, then converted

Backend's classification was that each failing test's *setup* is now refused by
a new control, or that it characterises behaviour that is now fixed. **QA
verified the classification rather than accepting it, and it is correct in all
twelve cases.** What verification added, in each group:

### 2.1 Eight in `test_gate_journey.py` — verified, and widened

Each created an incomplete `gate='C'` authorisation. Migration 0005 refuses it
at INSERT. QA checked the refusal is **the ADR-002 4.1(b) guard** and not an
unrelated error landing in the same place: the assertion now requires
`"4.1(b)"` in the exception text, so a future unrelated `IntegrityError` here
would fail rather than read as the control working.

Converted and widened, because a rising floor is a chance to test more of it:

* each of the six evidence items is attacked **in three shapes** — key absent,
  key present but whitespace-blank, key present but an empty list. "Missing" has
  three spellings and a guard that knew one would have had two holes. 18 cases,
  all refused.
* `authorised_by_human` is attacked with five whitespace strings including a
  bare tab, because `trim()`/`btrim()` strip spaces only on both engines and the
  migration says it named the characters explicitly for that reason. Verified,
  not read.
* the **printed** checklist is now unreachable from the database, which
  ENGINE-DIVERGENCE §9 item 11 flags. QA agrees it is not pointless — it is what
  tells an operator which item to fetch, with its Gate number — so it is
  asserted directly on an unsaved row through `checklist(campus, auth=...)`, one
  item at a time. Without that, six branches would be dead code nothing noticed.
* **the launder route is closed, and QA checked both braces**: saving an
  unconstrained `gate='B'` row and updating it to `'C'` is refused by migration
  0005's UPDATE trigger *and* by 0002's append-only trigger. Belt and braces
  only counts if both exist.
* the positive cases are asserted too — a complete authorisation still saves and
  still opens the gate, and `gate='B'`/`'D'` rows remain unconstrained as the
  migration intends — because a control that replaces a hole with an outage is
  not an improvement.

### 2.2 Three in `test_idempotency_contract.py` — verified; see §3.1

### 2.3 One in `test_migration_guards.py` — verified, and inverted

`test_no_test_in_the_repository_sets_the_flush_escape` asserted the absence of
the fixture ENGINE-DIVERGENCE §7.1 called mandatory. `tests/conftest.py::
allow_test_flush` now exists. QA asserted **what it does**, not that it exists:
session-scoped and autouse, so a teardown failure is not something a test opts
out of; depends on `django_db_blocker`, so the setting lands on the connection
the harness flushes with; a deliberate no-op off PostgreSQL; and it sets the
escape and nothing else — no `DISABLE TRIGGER`, no `DROP`, no `ALTER TABLE`,
each asserted absent. The inventory test now requires the string to appear in
exactly two files, the migration and the fixture, because an escape hatch with
three declarers is three hatches.

---

## 3. The three claims verified hardest

### 3.1 F10 — no path leaks a body, and authenticated replay is intact

Backend made two changes rather than one, and QA tested them as two.

**The UUID requirement.** Seven non-UUID anonymous keys — `1`, `abc`, `null`,
`4`, `-`, `retry-1` and a truncated UUID — are all refused with
`VALIDATION_FAILED` / 400, and no row is written. A conforming UUID still works.

**No body on an anonymous replay.** QA walked **every** path on which an
anonymous second caller gets an answer about a key a first caller claimed, and
asserted none carries content:

| Path | Result |
|---|---|
| `Replay`, same endpoint and body — the exact path that leaked `{"grievance_ref": "GRV-000123"}` in F10 | status `201`, **body `None`** |
| `IdempotencyInProgress` | no body attribute |
| `IdempotencyKeyReused`, different body | no body attribute |
| `IdempotencyKeyReused`, different endpoint | no body attribute |

**There is no remaining path on which one anonymous caller receives another's
response.** The surviving channel is the **status code**, which a colliding
caller does learn. That is precisely what API-CONTRACT §4.1 now promises — "the
consequence of a collision is a 409" — it requires guessing a UUID to reach, and
it carries no content. QA records it as the accepted residual rather than
leaving "never" unqualified.

**The narrowing did not break the mechanism it exists to protect.** Asserted
separately, because dropping the body for everyone would have traded a narrow
disclosure for a broken retry on every transition endpoint from S4: an
**authenticated** replay still returns the stored body. The first caller's own
row still holds the body, so their retry is unaffected. And the UUID requirement
is scoped to the anonymous namespace — an authenticated `tap-1` is still legal,
which it must be, since `(user_id, key)` collides with nobody.

Residual: **F11**, §5.

### 3.2 The rebuilt P14 control — full attack list re-run, and the new allowance attacked

The control now reads **every column in any type** rather than only numeric
ones, which is what let a text column through, with the exemption scoped to two
named columns and `MONEY_WORDS_EXEMPT_TABLE` set to `None`.

**QA's full 21-shape attack list was re-run against the shipped control** (raw
DDL, one transaction each, each column confirmed present in the schema the guard
reads before the verdict is taken). **All six shapes that escaped in v2.0 are
now caught:**

| v2.0 escape | Now |
|---|---|
| `receipts.amt text` | **CAUGHT** |
| `receipts.paid text` | **CAUGHT** |
| `handover_log.payment_received text` | **CAUGHT** |
| `receipts.due_inr text` | **CAUGHT** |
| `listings.cash_received text` | **CAUGHT** |
| `listings.settlement text` | **CAUGHT** |

The two ADR-003 §2.3 W5 residuals — a number in a jsonb document, a number in
free text — still escape, and the suite asserts they **must**, so that W5 and
the control cannot silently disagree. The third residual, a Python `@property`,
is still invisible to every schema assertion; that is W1c's job, §3.3.

**And QA attacked the new allowance.** `MONEY_TOKEN_SHAPE_EXEMPTIONS` —
`due_at`, `overdue`, `consume` — is an *allowance*, escalated as one in
ENGINE-DIVERGENCE §9 item 9, and an exemption is a hole until someone tries to
climb through it. QA re-derived 21 cases from the contract rather than re-running
backend's six, choosing the ones where stripping an exempted shape could destroy
evidence. Every contract-mandated name passes (`purge_due_at`, `act_due_at`,
`sla_due_at`, `disposal_due_at`, `jobs_overdue`, `consume_magic_link`) and
**every one carrying an amount still fails** — `amount_due_at`, `due_at_paise`,
`cash_due_at`, `settlement_due_at`, `overdue_amount`, `cash_overdue`,
`overdue_balance`, `consume_price`, `consumed_total`, `consume_amount_paise`,
`due_inr`, `amount_due`, `due_paise`, `sum_paise`, `cash_sum`. **The allowance
cannot hide an amount.** QA supports the three shapes being stated in ADR-003
§2.3 W1b as §9 item 9 asks: each answers the ADR's own discriminating question,
and the counterfactual — a P14 guard red on fifteen contract-mandated SLA
columns, with the tempting fix being an edit to a founder-escalating file — is
REVIEW-S0 M2 again.

Residual: **F12**, §5.

### 3.3 `apps/core/p14.py` — the three-copies problem, and QA's own copy

**The structural fix is real.** The module exists, and QA asserted more than its
existence: every shared list the guard uses is **the object `apps/core/p14.py`
exports**, by identity, not an equal copy — because an equal copy is exactly
what drifted last time. Nine lists checked.

**QA's decision on `tests/contract/denylist.py`: it stays independent and does
not import.** The reasoning, recorded in the module and here because the
opposite choice is defensible:

* importing would make the conformance tests tautologies (`assert p14.TOKENS ==
  p14.TOKENS`) and delete the only check that the **specification** and the
  **enforcement** still agree;
* `apps/core/p14.py` removes the drift between the guard and the module. It
  cannot remove the drift between the module and the ADR, because the ADR is
  prose in a document no test can read. Something must hold the ADR's text in a
  comparable form, and that something must not be the thing it is comparing to;
* **the condition, which is the real lesson of F1:** an independent
  re-derivation is only a check if the comparison is deliberate. v1.0 held this
  file beside the guard and compared them *by accident*, through a human reading
  two reports — which is how QA's own error survived a round. The comparison is
  now explicit, named and automatic: `test_conformance_*` asserts
  `apps/core/p14.py` against QA's ADR transcription one list at a time, and a
  divergence fails naming the list. This file is a reference, never a judge:
  every attack verdict comes from running the shipped control.

**Three copies became two by design, and the two are compared on every run.**
The fourth copy — the inline boolean inside the guard's own attack test, which
v2.0 flagged — is gone; that test now imports the module's matchers.

### 3.4 W1c's source grep, and its own guard

The guard exists (`test_the_grep_actually_sees_each_declaration_shape`), and
**backend's reasoning for it is right**: a grep that silently matches nothing is
this project's recurring defect, so the detector needs a detector. QA verified
it two ways rather than re-running its cases:

* **derived the shapes from the ADR, not from the guard.** All five declaration
  kinds W1c names — model field, `@property`, `@cached_property`, serialiser key,
  API response key — plus a plain method, are each proved visible to at least one
  regex and recognised as money-shaped.
* **asserted the grep is actually reading the tree**: it finds more than 100
  declarations in `apps/**`, carries its own "would pass vacuously" assertion,
  and its exclusion list is exactly `{"apps/core/p14.py"}` with no wildcard — so
  the exclusion cannot widen into the file that has the property in it.

Residual: **F13**, §5 — three declaration shapes the grep does not see.

---

## 4. Everything QA has now verified about S0

Collected because this is the closing pass and "what was verified" is the
deliverable.

**The discovery gate** (ADR-002 §4, PRD AC-M6.1). Closed by default; the refusal
is `403 GATE_CLOSED` with a reason code; a `None` campus is closed; an inactive
campus is closed on **both** the read and the write path; `seed_demo` opens
nothing. The command refuses on a missing authorisation, each of five
legal-entity facts, a wrong gate letter, a GLOBAL scope, another campus's
authorisation, a revoked authorisation, a campus with no legal entity and an
unknown slug. The **database** refuses: an INSERT that arrives open, an opening
without a live Gate C row for that campus, an opening of an inactive campus, a
reopen after close with no new authorisation, and now an authorisation that is
incomplete in any of three shapes or unnamed in any of five. Closing is always
permitted, including with the authorisation already revoked; an unrelated UPDATE
on an open campus still works. The whole HTTP surface is `/healthz` and
`/readyz`, neither leaks tenant data, no admin is installed, and only
`open_discovery`/`close_discovery` write the gate column.

**The audit trail.** UPDATE, single-row DELETE and whole-table DELETE refused;
the triggers proved to exist by querying the live schema rather than trusting the
migration. With them dropped — a tamperer's first move — the chain detects a
rewritten row **by id**, a deleted middle row, a forged append and a half-fixed
hash. An audit row rolls back with the transaction that wrote it. The two
ceilings `DATA-MODEL.md` §8 admits — tail truncation and a full rewrite by an
attacker holding the hashing code — are measured and asserted so they stay
admitted.

**Idempotency.** All four branches for authenticated and anonymous callers,
key-order insensitivity, value sensitivity, per-user scoping, endpoint binding,
the 24-hour retention asserted against the contract's number, the two namespaces
proved not to collide in either order, and §3.1's disclosure walk.

**P14.** §3.2, plus: the deny-list rows the amendment added (items 4–7), the four
frozen tables, both `transfer_followups` enum value sets by value, and the
response-boundary check on S0's two responses.

**The PostgreSQL-only guards, as far as text allows** (§6).

**Accessibility.** Unchanged: 15 self-check tests prove every harness rule fires,
and the page runner still skips because no HTML page exists. Still not a WCAG
2.2 AA pass, and the eight criteria no HTML-level harness can decide — including
**3.3.8 accessible authentication**, which lands directly on S1's magic-link
flow — remain unverified.

---

## 5. What remains open — four items, none blocking

| # | Item | Why not blocking | Slice |
|---|---|---|---|
| **F11** | `uuid.UUID(key)` accepts any version and variant, and 32 bare hex digits, so API-CONTRACT §4.1's "UUIDv4" is enforced as "UUID-shaped". `00000000-0000-0000-0000-000000000001` is a legal anonymous key | **It no longer costs a disclosure** — the body is never returned — so the consequence of a deliberate collision is exactly the `409` the contract claims. What remains is a bounded availability edge against a client that generates low-entropy UUIDs, and §4.1 has L3 forms carry a server-generated key. Fix is `uuid.UUID(key).version == 4` | **S1**, with `/auth/magic-link`, the first anonymous endpoint |
| **F12** | W1b's 22nd token `rs_` is now enforced and matches any plural-plus-underscore: `offers_count`, `members_count`, `users_seen`, `followers_count`, `authors_count` each carry `rs_` and nothing else | No such column exists today, so the guard is green. It becomes live at the first one, and `offers_count` on a listing is plausible. Backend rejected `rs_` for this exact reason a round ago and then enforced all 22 to close F6 — the right trade, but it reinstates the collision. The mechanism to fix it already exists (`MONEY_TOKEN_SHAPE_EXEMPTIONS`) and deciding it now is cheaper than deciding it in a slice with a red founder-escalating file | **S2/S4** |
| **F13** | W1c's grep misses three money-shaped declaration shapes: a property *assigned* rather than decorated (`settled_price_paise = property(lambda self: 30000)` — the exact shape QA used to demonstrate the residual), a bare class constant, and an annotation with no assignment | The schema control catches any of these that reaches a column, and two require an unusual spelling. But W1c is the **only** control for a computed money value, so a gap in it is a gap in the whole of that control. Nothing in `apps/**` uses any of the three today, asserted. Fix is two regexes; QA explicitly does **not** recommend a blanket `^\s*(\w+)\s*=`, which would match local variables and teach a developer the guard is wrong | **S1** |
| **B2** | The gate floor requires every evidence item present and non-blank; it cannot check whether any is **true**. `campus_mou_ref="TODO"`, `breach_rehearsal_at="not yet"`, `authorised_by_human="agent"` all save and open the gate | **Open by agreement, not oversight.** ADR-002 §4.2 already says the design makes the position auditable rather than correct, and the migration says so too. QA keeps the test so the go/no-go packet is never read as stronger evidence than it is: the gate records a claim by a named human, it does not verify one. Two items are cheaply checkable and are not — `breach_rehearsal_at` is specified as a date, and `authorised_by_human` is the field "no agent writes this row" rests on | cto / ceo-planning, before Gate C |

**Also carried, unchanged:** `tests/unit/test_forbidden_response.py` is named by
ADR-003 §2.3 and THREAT-MODEL §6, is the compensating control W5 leans on for
the jsonb and free-text residuals, and **still has no owning slice**
(ENGINE-DIVERGENCE §9 item 7). QA cannot write it — it is backend-developer's
tree — and there is no response payload in S0 to run it against. A named control
with no owner is never written.

---

## 6. The engine limits — the one qualification on this PASS

26 skips in QA's tree, every one naming the engine and the slice. Unchanged: the
double-booking race, `expected_version`'s failure mode, two simultaneous
retries, concurrent chain appenders, multi-worker job claiming, a reservation
expiring during an accept; the plpgsql append-only body, the TRUNCATE guard's
behaviour, the P14 price trigger, the engine's rejection of float money;
`is_seed`, the seed/real CHECK, the metric views, the real-student journey; the
keyboard walkthrough and p75 LCP.

**What QA could do instead, and did.** `tests/contract/test_migration_guards.py`
audits the Postgres-only guards as text, which is `VERIFIED` about the text and
`UNVERIFIED` about the behaviour — a distinction the file states in its own
skips. Verified this round:

* the TRUNCATE escape **defaults to deny**: the two-argument
  `current_setting('bookhop.allow_flush', true)` so an unset GUC yields NULL
  rather than raising, an `= 'yes'` equality test so NULL is not a match, and
  none of `IS DISTINCT FROM`, `<>`, `!=`, `IS NULL` or `COALESCE` anywhere in
  the guard body — each of which would have inverted it. **A guard whose escape
  hatch defaults open is worse than no guard, and this one defaults closed.**
* the escape appears in **exactly one** plpgsql function body across all
  migrations — the TRUNCATE guard. UPDATE and DELETE have none, so the
  append-only guarantee is not one `SET` away from nothing.
* both triggers running it are `BEFORE TRUNCATE`.
* all `ENABLE ALWAYS` statements name triggers the migrations actually create —
  a typo there would fail the first PostgreSQL migration after sign-off.
* both engine halves of the gate guard check the same five conjuncts, and the
  INSERT half exists on both. Only the SQLite half is ever executed here, so a
  divergence would mean the property QA verified is not the one production
  enforces.
* the reverse migration restores a guard rather than leaving none.

**The qualification, stated plainly for the integration decision: this PASS is a
pass on SQLite.** The rework added a third Postgres-only guard
(migration 0005's plpgsql half), so the unexecuted security-relevant SQL went up
again. ENGINE-DIVERGENCE §9 item 3 asks for a local PostgreSQL 16 before S2;
**QA's position is that it should land before S1 merges**, because it costs Rs 0,
it runs natively on Windows without Docker, and five guards now rest on text
nobody has executed. That is not a blocker on S0 — S0's own correctness does not
depend on it — but it is the next thing this project should buy, and it is free.

---

## 7. Escalations

**To cto, none blocking:**
1. **ENGINE-DIVERGENCE §9 item 9 — grant it.** State `due_at`, `overdue` and
   `consume` in ADR-003 §2.3 W1b. QA attacked the allowance with 21 derived
   cases and it cannot hide an amount; the alternative is REVIEW-S0 M2 again on
   fifteen contract-mandated columns.
2. **F12 — decide `rs_` now**, before the first `*rs_count` column makes it a
   schedule problem.
3. **F11, F13** — one line and two regexes respectively, both S1.
4. **B2** — two of the six evidence items are cheaply validatable
   (`breach_rehearsal_at` as a date, `authorised_by_human` as a non-agent); the
   rest cannot be, and the packet should say so.
5. **ADR-003 §2.3 rows 5 and 8 still lag the code** in the code's favour
   (`%ledger%`, `users.address`). Amend the rows.
6. **`test_forbidden_response.py` needs an owning slice.**

**To backend-developer:** F11, F12, F13. Nothing else; the rework answered every
other QA finding, and it answered several more thoroughly than QA asked — the
`reason` code on the gate refusal, the whitespace-character enumeration in the
evidence guard and the `auth` injection point for the printed checklist were all
unasked-for and all correct.

**To ceo-planning:** B2, and §6's PostgreSQL ask, which is a decision rather
than a spend.

**To red-team:** ADR-003 §2.3 W5's sentence — *"P14 is enforced, not
guaranteed"* — is now accurate rather than optimistic, and QA has measured both
halves of it. The two residuals are a number in a jsonb document and a number in
free text; the compensating controls are PRD EX-18's product rule, W2's frozen
column lists, and a response-schema test that does not exist yet.

---

## Amendment log

| Date | Change | By |
|---|---|---|
| 2026-10-21 | v1.0 — first independent QA pass. 169 tests; 3 fail as findings F1–F3 | test-qa |
| 2026-10-21 | v2.0 — re-pass after the M0–M5 rework. §3 corrected v1.0's P14 measurement **against QA**: it measured QA's own transcription, not the shipped control. Five findings converted to regressions; new findings F4–F10; 182 tests, 10 fail | test-qa |
| 2026-10-21 | **v3.0 — closing pass. VERDICT: PASS.** All twelve newly-failing tests verified against backend's classification (correct in all twelve) and converted, with the evidence-item cases widened from 6 to 18 and the whitespace and launder routes added. F10 verified by walking every anonymous-response path and by asserting authenticated replay intact; the rebuilt P14 control re-attacked with the full 21-shape list (all six v2.0 escapes now caught) plus 21 derived cases against the new token-shape allowance; `apps/core/p14.py` asserted shared by identity, not by equality. QA's `denylist.py` **stays independent by decision**, with the comparison made explicit. New non-blocking findings F11–F13. 246 QA tests: 220 pass, 26 skip, **0 fail** | test-qa |
