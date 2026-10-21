# QA-S0.md — independent QA pass on slice S0

**Owner:** test-qa · **Version:** v4.0 · **Date:** 2026-10-21
**Slice:** S0 (skeleton, tenancy, gate, audit, jobs) — closing pass

# VERDICT: **PASS.** S0 is QA-green and clears for integration.

Four passes, 17 findings raised (F1–F15, B1–B3), all fixed or accepted. Every
one is now a regression test named for the finding it came from, so the history
is readable from the suite and not only from this document.

**Nothing blocks integration.** Five items remain open; each is real, each is
non-blocking, and each is named with the slice that owns it in §6. One (B2) is
open by agreement; one (F14) QA recommends recording rather than fixing.

**The one qualification on this PASS, and it is about to lift:** every number
below was measured on SQLite. **Five plpgsql function bodies, attached by six
triggers with six `ENABLE ALWAYS` statements, have never been parsed by a
PostgreSQL server.** PostgreSQL 16 is being installed; §7 is the execution
checklist for that server, in priority order, with what each test would prove.

**v4.0 supersedes v3.0**, which was written but not delivered before the session
ended. v2.0's correction of v1.0 — QA's P14 attack had measured QA's own
transcription rather than the shipped control — stands and is not restated.

**Written from:** `ADR-002` §2, §4 · `ADR-003` §2.1–2.3 (W1–W5), §5.3, §5.3.1 ·
`API-CONTRACT.md` §2.2, §2.5, §4, §5.8 · `DATA-MODEL.md` §1, §5, §8 ·
`THREAT-MODEL.md` §4 B5/B6, §6, A12 · `ENGINE-DIVERGENCE.md` v1.2 §3.4,
§3.6–§3.6c, §3.8a, §4.3a, §7.1, §9 · `CLAUDE.md` rules 9–14 ·
`.claude/agents/test-qa.md`.

**Method.** Tests only in `tests/e2e/**`, `tests/a11y/**`, `tests/contract/**`.
No file under `bookhop/**`, `apps/**`, `tests/unit/**`, `tests/api/**` or
`tests/conftest.py` was modified in any of the four passes. Nothing QA found was
fixed by QA. Specification first, implementation second — and v1.0's error is
this project's best evidence for why, so the method is kept rather than
softened.

---

## 1. The command, and its real output

```
$ cd C:\CodingSpace\BookHop
$ .venv/Scripts/python.exe -m pytest
...
======================= 570 passed, 55 skipped in 11.82s ======================
```

Run immediately again, identical: `570 passed, 55 skipped in 12.30s`.

Split by owner, same state:

```
$ .venv/Scripts/python.exe -m pytest tests/unit tests/api -q
261 passed, 28 skipped in 1.12s

$ .venv/Scripts/python.exe -m pytest tests/e2e tests/a11y tests/contract -q
309 passed, 27 skipped in 10.60s
```

**Zero failures.** QA's tree is 336 tests: 309 pass, 27 skip with an
engine-and-slice reason, none fails. Across four passes QA's tree went
169 → 182 → 246 → 336 tests, and 3 → 10 → 0 → 0 failures.

Engine: **SQLite 3.45.1**, Python 3.11.9, Django 5.2.8, no PostgreSQL server
yet, no Docker.

> **A note on reading a QA run during an active edit.** In the previous pass an
> intermediate run showed 12 failures that an immediate repeat did not; the
> cause was QA's tests reading backend's files mid-write. Four of QA's tests
> read backend-owned source as data — the P14 conformance tests, the source-grep
> coverage tests, the flush-escape inventory and the migration text audit. That
> is deliberate, and it is what caught F4, F9 and F15. It also means a run taken
> during an edit can report a failure that is neither a defect nor a flake. The
> numbers above are two consecutive identical runs on a quiet tree.

---

## 2. The twelve conversions — verified correct, not assumed

The coordinator is right that a test converted to assert the *wrong* fixed
behaviour is worse than one left red, because nothing then draws attention to
it. So each conversion was re-checked against the specification, and each was
given a **positive counterpart** — a control that fails if the new guard has
replaced a hole with an outage.

| Group | Conversion | Positive counterpart that makes it honest |
|---|---|---|
| **8 gate tests** | Each created an incomplete `gate='C'` row and asserted the *command* refused. Migration 0005 refuses the **INSERT**, so each now asserts `DatabaseError` **carrying "4.1(b)"** — not merely that something raised, which an unrelated `IntegrityError` would have satisfied | `test_a_complete_authorisation_is_still_accepted` — the legitimate row still saves **and still opens the gate**; and `test_an_incomplete_authorisation_for_another_gate_is_still_permitted`, because migration 0005 constrains Gate C only and says so |
| | The six evidence items are now attacked in **three shapes each** — absent, whitespace-blank, empty list — 18 cases, because "missing" has three spellings | `test_the_printed_checklist_still_names_each_missing_item` — the command's per-item branch is unreachable from the database now (ENGINE-DIVERGENCE §9 item 11), so it is asserted directly on an unsaved row via `checklist(campus, auth=…)`. Six dead branches would otherwise go unnoticed |
| | `authorised_by_human` attacked with five whitespace strings **and** 26 invisible forms (§3.1) | `test_a_real_name_is_still_accepted_by_the_command_invariant` — seven real names including Tamil, CJK, punctuation, and names *containing* a zero-width space |
| **3 idempotency tests** | Anonymous keys must be UUIDs and an anonymous replay returns the status with **no body** | `test_the_f10_narrowing_did_not_break_authenticated_replay` and `test_an_authenticated_key_is_not_required_to_be_a_uuid` — the mechanism the fix exists to protect, asserted separately |
| **1 flush-escape test** | Asserted the fixture's **absence**; now asserts what the fixture **does** — session-scoped, autouse, `django_db_blocker`, a deliberate no-op off PostgreSQL, and `DISABLE TRIGGER`/`DROP TRIGGER`/`ALTER TABLE` each asserted **absent** from it | The inventory test: the string must appear in exactly two files, the migration and the fixture. A third declarer is a third hatch |

**One conversion is a correction to QA, kept visible on purpose.** v1.0 asserted
that a key replayed across two endpoints returning the first endpoint's response
was deliberate contract semantics. It was a bug (REVIEW-S0 M3); code review was
right. The regression test carries that history in its docstring, because a
characterisation test is only as good as the contract reading behind it and this
one asserted a bug into the baseline.

---

## 3. The three claims verified hardest this pass

### 3.1 The invisible-name invariant — **it catches ZWSP and BOM, and twenty-four more**

Code review found that zero-width space and the byte-order mark satisfied both
layers, so the one field carrying the whole "a named human signed this" rule
could be filled with something that renders as nothing — in the audit row and in
the go/no-go packet. Backend closed it with a **Unicode invariant** rather than a
character list: *printable, non-whitespace, category not `Cf`*.

QA's test is whether that is genuinely a property and not a list in disguise, so
QA derived **26 invisible forms independently** and ran all of them:

| Measured | Result |
|---|---|
| **U+200B ZERO WIDTH SPACE** — code review's finding | refused (`Cf`, not printable) |
| **U+FEFF BYTE ORDER MARK** — code review's finding | refused (`Cf`, not printable) |
| U+200C ZWNJ, U+200D ZWJ, U+200E LRM, U+2060 word joiner, U+00AD soft hyphen, U+180E Mongolian vowel separator | refused — six forms **no list in this repository has ever named** |
| U+00A0 NBSP, U+1680 ogham space mark, U+2000 en quad, U+2007 figure space, U+202F narrow NBSP, U+205F medium mathematical space, U+3000 ideographic space | refused |
| NUL, DEL, tab, LF, CRLF, VT, FF, space, empty, and a mixture of five | refused |

**All 26 refused.** A control that consults no list cannot be defeated by a form
absent from the list, and that is the whole argument for the invariant. It holds,
and it is the right shape — it is `CLAUDE.md` rule 11's principle reached by a
better route than a per-entry list: a property that needs no entries.

The other half matters as much (`CLAUDE.md` rule 13 — a guard that fires on
legitimate input gets edited, not obeyed). Seven real names pass, including a
Tamil name, a single CJK character, and **a real name with an embedded
zero-width space**: "at least one visible character" has not become "no
invisible characters anywhere", which would have refused anything pasted out of
a document.

**The database floor, and its declared ceiling — verified honest.** Migration
0005 keeps an explicit eleven-codepoint set and declares its own ceiling in the
migration: *"an invisible character not on the list passes this floor. The real
invariant lives one layer up … so the command stays strictly stronger than the
floor, which is the right relationship."* The reasoning for the asymmetry is
sound and QA agrees with it — SQLite has no regex, and Postgres's `[[:graph:]]`
is libc- and locale-dependent, so a category test in SQL would be *less*
predictable than an enumeration, not more.

QA verified the ceiling in the direction that can hurt an operator:

* **the floor is never stronger than the command.** For all 26 forms, the
  command refuses — so there is no value an operator is told is complete that
  the database then rejects. That failure mode reads as a broken deploy rather
  than as a guard, and it does not exist here.
* **the ceiling is real, and therefore the two layers are independent.**
  Measured: U+200C zero-width non-joiner is **not** on the eleven-codepoint
  list, the database accepts it, and the command refuses the open. Exactly what
  the migration describes. Two genuinely different mechanisms, which is
  `CLAUDE.md` rule 14's "two independent layers" rather than two copies of one
  list.
* **the rule applies to the six evidence items too**, not only to the human's
  name — including to the *elements* of a list item, so
  `notice_version_ids: ["\u200b"]` is not a published notice.

Residual: **F14**, §6 — three blank-rendering *printable* codepoints.

### 3.2 The rebuilt P14 control — full attack list re-run, allowance attacked

Carried forward from v3.0 and re-run green this pass. The control reads **every
column in any type** rather than only numeric ones, with the exemption scoped to
two named columns and `MONEY_WORDS_EXEMPT_TABLE` set to `None`.

All six shapes that escaped in v2.0 are **caught**: `receipts.amt text`,
`receipts.paid text`, `handover_log.payment_received text`,
`receipts.due_inr text`, `listings.cash_received text`,
`listings.settlement text`. The 21-shape attack list runs against the **shipped**
control via `tests/contract/shipped_control.py`, so "caught" means the build
would go red. The two ADR-003 §2.3 W5 residuals still escape and the suite
asserts they **must**, so W5 and the control cannot silently disagree.

**The new allowance was attacked, not accepted.**
`MONEY_TOKEN_SHAPE_EXEMPTIONS` — `due_at`, `overdue`, `consume` — is escalated
as an allowance in ENGINE-DIVERGENCE §9 item 9. QA derived 21 cases rather than
re-running backend's six, choosing the ones where stripping an exempted shape
could destroy evidence. Every contract-mandated name passes; **every name
carrying an amount still fails** — `amount_due_at`, `due_at_paise`,
`cash_due_at`, `settlement_due_at`, `overdue_amount`, `cash_overdue`,
`overdue_balance`, `consume_price`, `consumed_total`, `consume_amount_paise`,
`due_inr`, `amount_due`, `due_paise`, `sum_paise`, `cash_sum`. **The allowance
cannot hide an amount.** QA supports stating the three shapes in ADR-003 §2.3
W1b as §9 item 9 asks.

`apps/core/p14.py` exists and the guard imports from it; QA asserts the nine
shared lists are **the same objects**, by identity, not equal copies — because an
equal copy is what drifted. The fourth copy (an inline boolean in the guard's own
attack test) is gone.

**QA's decision on `tests/contract/denylist.py`: it stays independent and does
not import.** Recorded in the module and here, because the opposite choice is
defensible. Importing would make the conformance tests tautologies and delete the
only check that the **specification** and the **enforcement** still agree:
`apps/core/p14.py` removes drift between the guard and the module, but it cannot
remove drift between the module and the ADR, because the ADR is prose no test can
read. The condition — and the real lesson of F1 — is that an independent
re-derivation is only a check if the comparison is **deliberate**. v1.0 compared
the two *by accident*, through a human reading two reports, which is how QA's own
error survived a round. The comparison is now explicit, named and automatic:
`test_conformance_*` asserts `apps/core/p14.py` against QA's ADR transcription
one list at a time and names the list that moved. **Three copies became two by
design, and the two are compared on every run.**

### 3.3 `test_forbidden_response.py` — the recursion claim holds; two of four limbs are missing

**The recursion reasoning is correct and QA verified it twice.** Backend's stated
reason — *"the jsonb limb of P14 is a nested document, so a walker that only
inspected top-level keys would miss the one shape this control exists for"* — is
right: ADR-003 §2.3 W5's residual is a value inside `jobs.payload` or
`notifications.payload`, which reaches a response as a nested object.

* **In behaviour:** seven container shapes QA derived from the API's own
  envelopes — a jsonb payload, `{"items": [...]}`, a list inside a list,
  alternating lists and dicts, and depth 6, two levels deeper than the control's
  own guard — all caught.
* **In the code:** `forbidden_keys_in` recurses in two places, for dict values
  **and** for list elements. A dict-only or list-only recursion would leave the
  other container unwalked and happen to pass several of the behavioural cases,
  so the structural check is the one that rules it out.
* It stays quiet on six shapes the contracts mandate, including the SLA-clock
  names and both permitted money names, and its permitted set is **derived from
  `apps/core/p14.py`** rather than retyped (`CLAUDE.md` rule 10).

**And attacked the way the schema guard was attacked, it covers two of the four
limbs the specification names.** THREAT-MODEL §6: *"No response anywhere carries
a forbidden key, a money-shaped key, **a contact detail** or **an amount**."*

| Limb | Status |
|---|---|
| a forbidden response key name (`price`, `amount`, `total`, `value`) | **implemented** |
| a money-shaped key at any depth | **implemented** |
| **an amount as a *value*** — `{"handover_note": "Paid Rs 300"}` passes | **not implemented** |
| **a contact detail** — `{"message": "call me on +91 90000 00001"}` passes | **not implemented** |

A third, smaller gap: a **double-encoded** payload, `{"payload": "{\"paid\":
30000}"}` — JSON inside a string — is one harmless key to the walker, and
`jobs.payload` is a real jsonb column.

**The value limb is the one that matters, and it is the reason this is a finding
rather than a note:** ADR-003 §5.3 names this control as the compensating control
for the free-text residual, and **the free-text residual is a value.** As
implemented, the compensating control does not reach the thing it compensates
for. Finding **F15**, §6, slice **S1** — where ADR-003 §5.3.1 already assigns it.

**ADR-003 §5.3.1 adopted QA's conformance detectors as the gate on its own
prose** (*"the packet sentence may only name a control that a test proves
exists"*). QA has written the third detector that implies:
`test_finding_the_control_covers_two_of_the_four_limbs_the_spec_names` measures
the limbs, and `test_the_control_is_not_claimed_complete_anywhere_qa_can_read`
asserts §5.3.1's status table does not claim this control is "implemented and
verified" while two limbs are absent. **So §5.3's stronger G4 sentence cannot be
quoted yet, and now a test says so rather than a person remembering.** That is
`CLAUDE.md` rule 9 working as intended.

---

## 4. Everything QA has verified about S0

**The discovery gate.** Closed by default; the refusal is `403 GATE_CLOSED` with
a reason code; a `None` campus is closed; an inactive campus is closed on **both**
the read and the write path; `seed_demo` opens nothing. The command refuses on a
missing authorisation, each of five legal-entity facts, a wrong gate letter, a
GLOBAL scope, another campus's authorisation, a revoked authorisation, a campus
with no legal entity, and an unknown slug. The **database** refuses: an INSERT
that arrives open, an opening with no live Gate C row for that campus, an
opening of an inactive campus, a reopen after close with no new authorisation, an
authorisation incomplete in any of three shapes on any of six items, an unnamed
human in any of 26 invisible forms, and the launder route (save `gate='B'`, update
to `'C'`) — refused by migration 0005's UPDATE trigger **and** by 0002's
append-only trigger, both checked. Closing is always permitted, including with
the authorisation already revoked. An unrelated UPDATE on an open campus still
works. The whole HTTP surface is `/healthz` and `/readyz`, neither leaks tenant
data, no admin is installed, and only `open_discovery`/`close_discovery` write
the gate column.

**The audit trail.** UPDATE, single-row DELETE and whole-table DELETE refused,
with the triggers proved to exist by querying the live schema rather than
trusting the migration. With them dropped — a tamperer's first move — the chain
detects a rewritten row **by id**, a deleted middle row, a forged append and a
half-fixed hash. An audit row rolls back with its transaction. The two ceilings
`DATA-MODEL.md` §8 admits — tail truncation, and a full rewrite by an attacker
holding the hashing code — are measured and asserted so they stay admitted.

**Idempotency.** All four branches for authenticated and anonymous callers,
key-order insensitivity, value sensitivity, per-user scoping, endpoint binding,
24-hour retention asserted against the contract's number, the two namespaces
proved not to collide in either order, and the disclosure walk in §3 of v3.0:
every path on which an anonymous second caller gets an answer carries no body.

**P14.** §3.2, plus the deny-list rows the amendment added (items 4–7), the four
frozen tables, both `transfer_followups` enum value sets by value, W1c's source
grep proved to see all five declaration shapes the ADR names and proved to be
reading the tree, and the response boundary in §3.3.

**The PostgreSQL-only guards, as far as text allows.** The TRUNCATE escape
**defaults to deny** — two-argument `current_setting(name, true)`, an `= 'yes'`
equality test, and none of `IS DISTINCT FROM`, `<>`, `!=`, `IS NULL` or
`COALESCE` anywhere in the guard body, each of which would have inverted it. The
escape appears in exactly one plpgsql body across all migrations, so UPDATE and
DELETE have none. Both triggers running it are `BEFORE TRUNCATE`. **Every**
PostgreSQL trigger the migrations create is `ENABLE ALWAYS` — asserted as a
property across all migrations, not against a list of five, because 0005 added a
sixth and a fixed list is how the seventh goes unnoticed. Both engine halves of
the gate guard check the same five conjuncts; the INSERT half exists on both; the
reverse migration restores a guard rather than leaving none; and every vendor
branch refuses a third engine rather than creating a database with no guards.

**Accessibility.** 15 self-check tests prove every harness rule fires; the page
runner still skips because no HTML page exists. Not a WCAG 2.2 AA pass, and the
eight criteria no HTML-level harness can decide — including **3.3.8 accessible
authentication**, which lands on S1's magic-link flow — remain unverified.

---

## 5. What S0 is not

Unchanged and stated for the integration record: double-booking is implemented
nowhere and verified nowhere (S4, correctly). The gate journey is verified at the
level of the guard, the trigger and the predicate, not as a journey, because
there is no `users` (S1) and no `listings` (S2). Deletion, retention, SLA clocks,
the age gate, metrics and performance are S1–S7. `TASKS.md` S0's "done when
`seed_demo` produces a browsable-by-staff dataset" is **not met and cannot be**
before S1/S2; the command prints that it created no users, which is the honest
behaviour.

---

## 6. What remains open — five items, none blocking

| # | Item | Why not blocking | Slice |
|---|---|---|---|
| **F15** | `test_forbidden_response.py` implements two of the four limbs THREAT-MODEL §6 names. **An amount as a value** and **a contact detail** are unchecked, and the value limb is the one ADR-003 §5.3 relies on for the free-text residual. Double-encoded JSON is a third, smaller gap | ADR-003 §5.3.1 assigns this control to **backend, S1**; it has landed early with half its scope, which is better than not landing. S0 serves two responses, neither with a free-text field or a nested payload. What it does block is a **sentence** — §5.3's stronger G4 wording — and a test now enforces that | **S1** |
| **F11** | `uuid.UUID(key)` accepts any version and variant, and 32 bare hex digits, so §4.1's "UUIDv4" is enforced as "UUID-shaped" | **No longer costs a disclosure** — the body is never returned — so a deliberate collision yields exactly the `409` the contract claims. What remains is a bounded availability edge against a client that generates low-entropy UUIDs, and §4.1 has L3 forms carry a server-generated key. Fix is `uuid.UUID(key).version == 4` | **S1**, with `/auth/magic-link` |
| **F12** | W1b's token `rs_` matches any plural-plus-underscore: `offers_count`, `members_count`, `users_seen`, `followers_count`, `authors_count` each carry `rs_` and nothing else | No such column exists today, so the guard is green; QA asserts that too, which is what makes this a prediction and not a bug. It goes live at the first one, and `offers_count` is plausible in S4. The mechanism to fix it exists (`MONEY_TOKEN_SHAPE_EXEMPTIONS`), and `CLAUDE.md` rule 13's order of resort applies — rename ours first | **S2/S4** |
| **F13** | W1c's grep misses three money-shaped declaration shapes: a property *assigned* rather than decorated (`settled_price_paise = property(...)` — the exact shape QA used to demonstrate the residual), a bare class constant, and an annotation with no assignment | The schema control catches any that reaches a column, and two need an unusual spelling. But W1c is the only control for a computed money value. Nothing in `apps/**` uses any of the three, asserted. Fix is two regexes; QA explicitly does **not** recommend a blanket `^\s*(\w+)\s*=`, which would match local variables and teach a developer the guard is wrong | **S1** |
| **F14** | Three blank-rendering **printable** codepoints pass the invisible-name invariant: U+2800 BRAILLE PATTERN BLANK, U+3164 HANGUL FILLER, U+115F HANGUL CHOSEONG FILLER | **QA recommends recording, not fixing.** Closing it needs either a list — which is what the invariant was adopted to avoid — or Unicode's `Default_Ignorable_Code_Point` plus a blank-glyph set, which Python does not expose and which would reject legitimate Hangul filler. The exposure needs someone with write access deliberately obscuring their own name in a row that is append-only, audited and permanently attributable. Recorded so nobody reports "invisible names are impossible" without this sentence beside it | record only |
| **B2** | The gate floor requires every evidence item present and non-blank; it cannot check whether any is **true**. `campus_mou_ref="TODO"`, `breach_rehearsal_at="not yet"`, `authorised_by_human="agent"` all save and open the gate | **Open by agreement.** ADR-002 §4.2 says the design makes the position auditable rather than correct, and the migration says so too. QA keeps the test so the packet is never read as stronger evidence than it is: the gate records a claim by a named human, it does not verify one. Two items are cheaply checkable and are not — `breach_rehearsal_at` is specified as a date, and `authorised_by_human` is the field "no agent writes this row" rests on | cto / ceo-planning, before Gate C |

---

## 7. The PostgreSQL execution checklist

**Five plpgsql function bodies, six triggers, six `ENABLE ALWAYS` statements,
never parsed by any server:**

| Function | Migration | Attached as |
|---|---|---|
| `audit_log_is_append_only()` | 0002 | `audit_log_append_only` (BEFORE UPDATE OR DELETE) |
| `gate_authorisations_is_append_only()` | 0002 | `gate_authorisations_append_only` (BEFORE UPDATE OR DELETE) |
| `campuses_gate_is_authorised()` | 0003 | `campuses_gate_authorised` (BEFORE INSERT OR UPDATE) |
| `bookhop_truncate_guard()` | 0003 | `audit_log_no_truncate` + `gate_authorisations_no_truncate` (BEFORE TRUNCATE, FOR EACH STATEMENT) |
| `gate_authorisations_evidence_complete()` | 0005 | `gate_authorisations_evidence_complete` (BEFORE INSERT OR UPDATE) |

**Do this before anything else, and in this order.** The first item is not a test
— it is the thing that decides whether the rest can run at all.

| # | Run | What it proves | Blocks |
|---|---|---|---|
| **0** | `BOOKHOP_DB_ENGINE=postgres manage.py migrate` **from empty** | That all five bodies parse and all six triggers and six `ENABLE ALWAYS` statements are accepted. **Nothing below can run until this does**, and ENGINE-DIVERGENCE §1 records that `sqlmigrate` has never even generated this DDL. A syntax error here is a one-line fix found at the cheapest possible moment; found later it is found in production | everything |
| **1** | `tests/e2e/test_audit_tamper.py::test_the_plpgsql_append_only_trigger_body_is_valid` *(skip → run)* | That `audit_log` is append-only **on the engine that stores it**. The SQLite half is verified; this is the half that matters. Also confirms ENGINE-DIVERGENCE §3.8's prediction that the exception arrives as `InternalError`, not `IntegrityError` — which S2's price handler and S4's `accept_offer` must branch on | `COMPLIANCE.md` §8.5's audit claim |
| **2** | `tests/e2e/test_audit_tamper.py::test_truncate_cannot_empty_the_audit_log` *(skip → run)* | That `TRUNCATE audit_log` is refused. §3.6 calls this **"the single most important thing for a Postgres box to confirm"**, because row triggers do not fire on TRUNCATE and the hole exists on Postgres and not on SQLite. Pair it with the inverse: `SET bookhop.allow_flush='yes'` then TRUNCATE **succeeds**, which proves the escape is an escape and not dead code | the append-only guarantee |
| **3** | `tests/contract/test_migration_guards.py::test_the_flush_escape_permits_a_transactional_teardown` *(skip → run)* | That `tests/conftest.py::allow_test_flush` actually lets a `transactional_db` test tear down. If it does not, **every transactional test on Postgres fails in teardown** and the tempting fix is deleting the guard from item 2. This is the single highest-value skip to run early, because it is the one whose failure would be misdiagnosed | **S4 entirely** |
| **4** | `tests/contract/test_migration_guards.py::test_the_postgres_guards_actually_fire` *(skip → run)* | The umbrella for items 0–3 plus the two guards with no SQLite equivalent to compare against: `campuses_gate_is_authorised` and `gate_authorisations_evidence_complete`. QA has asserted both halves agree **as text**; this is the first time the Postgres half executes | the gate's database floor |
| **5** | Re-run **all** of `tests/e2e`, `tests/a11y`, `tests/contract` on Postgres | That the 309 assertions that pass on SQLite also pass where the types are real. ENGINE-DIVERGENCE §2 predicts four behaviour changes QA's tests will meet: `uuid` and `inet` columns validate (§2.3, §2.4), `smallint` range is enforced (§2.7), and `LIKE` becomes case-**sensitive** (§7.3), which `__contains` relies on from S2. Expect failures here and treat them as information, not regression | nothing — this is the measurement |
| **6** | `tests/e2e/test_audit_tamper.py::test_concurrent_appenders_cannot_fork_the_chain` *(skip → run)* | That `prev_hash UNIQUE` does the job it was added for: two appenders racing, the loser retrying against the new head. SQLite has one writer, so this property has never been exercised anywhere | the audit chain under load |
| **7** | `tests/contract/test_idempotency_contract.py::test_two_simultaneous_retries_cannot_both_execute` *(skip → run)* | API-CONTRACT §4.1's claim that **"the insert of the key row is the lock"** — a concurrency claim that SQLite's write lock satisfies for the wrong reason | every retry path from S1 |
| **8** | `tests/contract/test_concurrency_limits.py::test_two_job_workers_cannot_claim_the_same_job` *(skip → run)* | That the compare-and-swap claim is single-claim with two real workers. ENGINE-DIVERGENCE §4.3 records this as `UNVERIFIED` **on both engines** — it is the only item on this list that is unverified everywhere | `retention.purge`, a DPDP r.8(3) obligation from S1 |

**Needs Postgres *and* a later slice's tables — schedule with the slice, not with
the server:** the double-booking race and the partial unique index (S4);
`expected_version`'s failure mode (S4); a reservation expiring during an accept
(S4/S5); the price-immutability trigger and the engine's rejection of float money
(S2); `is_seed` and the seed/real CHECK (S1/S2/S4); the metric views, which cannot
run on SQLite at all (S7); `citext` for case-insensitive email (S1); trigram
ranking (S2/S3).

**What a green Postgres run would and would not change in this report.** It would
retire the qualification in the header and convert roughly nine skips into
assertions. It would not change any finding in §6, all five of which are
engine-independent. **And it would not make §5 untrue:** double-booking would
still be implemented nowhere.

---

## 8. Escalations

**To cto, none blocking:**
1. **ENGINE-DIVERGENCE §9 item 9 — grant it.** State `due_at`, `overdue` and
   `consume` in ADR-003 §2.3 W1b. QA attacked the allowance with 21 derived
   cases and it cannot hide an amount.
2. **F15 — the value and contact-detail limbs**, in S1, where ADR-003 §5.3.1
   already assigns them. Until then §5.3's stronger G4 sentence stays unquoted,
   and a test now enforces that rather than a person remembering.
3. **F12 — decide `rs_` now**, before the first `*rs_count` column makes it a
   schedule problem under a red founder-escalating file.
4. **F11, F13** — one line and two regexes, both S1.
5. **F14** — QA recommends recording the three blank-rendering printables in
   ADR-002 §4.1(b) or the migration, and **not** fixing them.
6. **B2** — two of the six evidence items are cheaply validatable; the rest are
   not, and the packet should say which.
7. **ADR-003 §5.3.1's status table is now stale** in the safe direction: W1c,
   W1d and `test_forbidden_response.py` all exist. Updating it is the moment to
   record F15, so the table says "partially implemented" rather than flipping to
   "implemented".
8. **ADR-003 §2.3 rows 5 and 8 still lag the code** in the code's favour
   (`%ledger%`, `users.address`). Amend the rows.

**To backend-developer:** F11, F12, F13, F15. Nothing else. The rework answered
every other QA finding, and several more thoroughly than QA asked — the `reason`
code on the gate refusal, the eleven-codepoint set with a declared ceiling, the
`auth` injection point for the printed checklist, and deriving the response
guard's permitted set from `p14.py` rather than retyping it were all unasked-for
and all correct.

**To platform-sre, for S8 and dormant until then:** item 2 of §7 is also a
restore-path test. `ENABLE ALWAYS` exists because
`session_replication_role = 'replica'` is what some restore paths use; the
restore rehearsal (`INFRA.md` §3.3) should assert the triggers still fire after a
restore, not only that the data came back.

**To red-team:** ADR-003 §2.3 W5's sentence — *"P14 is enforced, not
guaranteed"* — is accurate rather than optimistic, and QA has measured both
halves. The two residuals are a number in a jsonb document and a number in free
text; their compensating controls are PRD EX-18's product rule, W2's frozen
column lists, and a response-schema test that **covers keys and not yet values**
(F15). That last clause is the one worth challenging.

**Verdict, restated for the integration decision: PASS on SQLite, with five
non-blocking items owned by named slices and one engine qualification that §7
exists to lift.** S0's gate is a database constraint, its audit chain is
tamper-evident and honest about its ceilings, its idempotency mechanism works for
authenticated and anonymous callers without leaking a body, and its P14 control
now says what ADR-003 says and is compared to it on every run. Slice 0 can close.

---

## Amendment log

| Date | Change | By |
|---|---|---|
| 2026-10-21 | v1.0 — first independent QA pass. 169 tests; 3 fail as findings F1–F3 | test-qa |
| 2026-10-21 | v2.0 — re-pass after the M0–M5 rework. §3 corrected v1.0's P14 measurement **against QA**: it measured QA's own transcription, not the shipped control. Five findings converted to regressions; new findings F4–F10; 182 tests, 10 fail | test-qa |
| 2026-10-21 | v3.0 — written but not delivered; superseded by v4.0 | test-qa |
| 2026-10-21 | **v4.0 — closing pass. VERDICT: PASS.** All twelve conversions verified against the specification and each paired with a positive counterpart. The invisible-name invariant attacked with 26 independently derived forms — ZWSP and BOM both refused, plus six forms no list here has named — and the database floor's declared ceiling verified honest and genuinely independent. `test_forbidden_response.py` attacked: its recursion reasoning holds, in behaviour and in code, and it covers **two of the four limbs** THREAT-MODEL §6 names (F15). The migration text audit widened to span every migration, so 0005's sixth guard is covered. New findings F14, F15. §7 is the PostgreSQL execution checklist for five never-parsed plpgsql bodies. 336 QA tests: 309 pass, 27 skip, **0 fail** | test-qa |
