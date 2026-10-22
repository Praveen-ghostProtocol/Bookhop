# ENGINEERING-MEMO — Red Team review of the engineering programme

**Date:** 2026-10-22 · **Author:** red-team · **Reports to:** founder, ceo-planning
**Scope:** D-040 engineering only. Business validation, market, campus access,
interviews and compliance advisory are **out of scope and not raised here.**
**Judged:** committed tree through `a18250d`. S1 is in flight; uncommitted work
is treated as direction, and where a finding lives in uncommitted code it says so.
**Method:** read every file in `apps/**`, `bookhop/**`, `web/views.py`,
`apps/accounts/services.py`, all migrations, `tests/conftest.py` and the
contracts; ran the suite on PostgreSQL 16.15 and SQLite; wrote seven
falsification probes and ran them against PostgreSQL. Every number below was
measured in this session unless marked `ASSUMPTION:`.

---

## 0. Verdict in one paragraph

**The apparatus is producing quality inside files and consuming it at the
seams.** Every defect the three reviews and five QA passes caught was a
within-artefact defect: a list with 15 of 22 entries, a trigger that did not
read `active`, a column stored and never compared. Every defect in this memo is
a **boundary** defect — between a trigger and the command above it, between the
schema's token list and the response boundary's, between a docstring and the
job runner it describes, between a sentinel and its callers, between the test
harness and the engine. The organisation has one reviewer per artefact and no
reviewer of the joins, and eighteen rules of which **every single one is about a
claim or a control and none is about end-to-end behaviour** — which is exactly
why 835 tests pass and no human has ever been served a page. I found nine
substantive defects in one pass, two of them critical, including one that opens
the legally load-bearing control in three statements. That is not an argument
for more process. It is an argument that the process is pointed at the wrong
axis.

---

## 1. CRITICAL — the discovery gate's enforced floor is three statements below
## the control ADR-002 §4.1(b) specifies

**Failure case, measured.** On PostgreSQL 16.15, against the migrated schema:

```
rows updated=1  discovery_open=True  audit rows written=0
entity CIN=None  inc20a=None  auth_entity=2  campus_entity=1
```

Three ORM statements — `LegalEntity.objects.create()` (empty),
`GateAuthorisation.objects.create(gate='C', scope_type='CAMPUS',
scope_id=campus.id, legal_entity=<a different entity>, evidence={six keys:
"x"}, authorised_by_human="a")`, then `Campus.objects.filter(id=...).update(
discovery_enabled_at=now())` — opened discovery on a campus whose legal entity
has **no CIN and no INC-20A filing**, under an authorisation granted against a
**different legal entity**, with every evidence value set to the literal string
`"x"` — which ADR-002 §4.1(b)'s own amended placeholder deny-list explicitly
rejects — and **wrote zero `audit_log` rows.**

The amendment to §4.1(b) made the *command* dramatically stronger: CIN shape,
`inc20a_filed_at >= incorporation_date`, `notice_version_ids` as real foreign
keys, an agent-name deny-list, placeholder rejection. None of that is in the
database, and nothing forces anyone through the command. Migration 0005 moved
*non-blankness* into a trigger and its docstring is honest about the limit; but
migration 0003 calls the trigger "the floor beneath" §4.1(b), THREAT-MODEL
§390 records the control as *"`Campus.objects.update(discovery_enabled_at=…)`
**cannot open the gate**"*, and REVIEW-S0 §9.1 marks M0 **FIXED**. All three are
literally true and all three read, to the next person, as the gate being
protected. The conformance test rule 9 demands **exists and passes** — because
it tests the floor the floor has, not the control the ADR specifies. This is the
answer to the question the brief asked: here, asserting the control exists moved
the lie up exactly one level.

The root cause is not the trigger. It is that **the application role holds the
privileges the control is supposed to withhold.** Rule 14 asks for two
independent layers; the gate has one layer twice, because both the trigger and
the command run as `bookhop`, which can insert `gate_authorisations` rows at
will. Measured: `current_user = bookhop`, `rolsuper = false`.

**What would have to be true for the current design to be right.** That no
agent and no application code path ever writes a `gate_authorisations` row, and
that `open_discovery` is the only thing that ever writes
`campuses.discovery_enabled_at` — both enforced by convention alone, in a repo
whose own rule 10 exists because "everyone independently doing the obvious
thing" produced three divergent copies of one legal rule.

**Cheapest test, pass/fail.** One conformance test, both engines, ~20 lines: run
the three statements above and assert the gate stays closed. **Fail = the gate
opens, or the audit row count is zero.** It fails today. Then the fix, which is
cheaper than another trigger: in one migration,

```sql
REVOKE INSERT, UPDATE, TRUNCATE ON gate_authorisations FROM bookhop;
REVOKE TRUNCATE ON audit_log FROM bookhop;
```

and give `open_discovery` its own role via a second `DATABASES` alias. That is
rule 14's second independent layer, which the gate has never actually had, and
it closes §3 below in the same diff.

**Severity: CRITICAL.**

---

## 2. CRITICAL — the raw magic-link token is persisted in `jobs.payload`
## forever, and the docstring that licenses it is false

**Failure case.** `apps/accounts/services.py:251` enqueues
`{"token_id": token.id, "token": raw, "locale": ...}`. `jobs.payload` is a
jsonb column in the production database. `apps/accounts/jobs.py:44` licenses
this with:

> "the row is deleted on completion, while `email_login_tokens.token_hash`
> never holds the plaintext … for the job's lifetime the plaintext token exists
> in a `jobs` row, so a database read during that window can sign in as that
> student."

and bounds the ceiling at *"the seconds between enqueue and send."*

**The row is never deleted.** `apps/core/jobs.py:138-141` sets `completed_at`
and clears `locked_at` and saves; there is no `delete()` anywhere in `apps/`
that touches `Job`, and `purge_expired()` (`apps/accounts/services.py:1153`)
walks `email_login_tokens`, `idempotency_keys` and `personal_data_access_log`
and **does not touch `jobs`**. So the declared ceiling is wrong by a factor of
forever, the `token_hash` design is defeated for the whole window, and a failed
job (`failed_at` set, row retained with `last_error`) parks **live** tokens for
every user affected by a mail outage. A `pg_dump` taken in that window — and
INFRA's entire backup strategy is nightly `pg_dump` — hands an attacker working
single-use sign-in links for named students. `jobs` has no retention rule at
all, which also makes it a standing contradiction of COMPLIANCE §8.3 as quoted
in `PurgeLog`'s own docstring.

This is rule 9 broken inside the file that implements the credential path: a
document asserted a property, nothing checked it, and it is false.

**What would have to be true.** That job rows are short-lived — which the code
does not make true — and that nothing but the app can read `jobs`, which
backups, replicas and operators each falsify.

**Cheapest test, pass/fail.** `test_no_job_row_retains_a_credential`: enqueue a
magic link, run the queue, then assert `Job.objects.filter(kind=
"accounts.send_magic_link").exists()` is `False` **and** that no row in `jobs`
has a `payload` key named `token`. **Fail = either holds.** Both hold today.
Fix, in order of laziness: delete the row on success in `run_pending_jobs`, add
`jobs` to `purge_expired` for the failed ones, and scrub `payload` before
writing `last_error`. Correcting the docstring is part of the fix, not a
separate task.

**Severity: CRITICAL.** (Lives in uncommitted S1 code. It is the direction, and
the direction is wrong.)

---

## 3. MATERIAL — the audit log's TRUNCATE guard is defeated by two statements
## from the application's own role

**Measured:** as `bookhop` (not superuser),
`SET bookhop.allow_flush = 'yes'` succeeds and
`current_setting('bookhop.allow_flush', true)` returns `'yes'`. Migration 0003
then returns `NULL` from the guard and permits `TRUNCATE audit_log`.

Migration 0002's own justification is *"the audit trail has to resist the
application as well as the user."* The escape hatch added for Django's
`sql_flush` is reachable from the application. The project went to the trouble
of **proving** the other bypass is closed —
`test_finding_the_application_role_cannot_reach_the_replica_bypass` measures
SQLSTATE 42501 on `SET session_replication_role` — which makes the asymmetry the
finding: one bypass verified shut, a second one opened by our own hand and
never tested from the app's perspective. This is rule 13's own pattern, resolved
at step 3 (widen) while the memo records it as step 2.

**What would have to be true.** That THREAT-MODEL §4 B5's "direct SQL is out of
scope" also covers the application's own connection — but the whole point of a
database-side guard is that the application is in scope.

**Cheapest test.** Assert, from the app role, that
`SET bookhop.allow_flush = 'yes'` **or** the subsequent `TRUNCATE audit_log` is
refused. **Fail = both succeed.** Both succeed today. Fix: `REVOKE TRUNCATE ON
audit_log, gate_authorisations FROM bookhop` (same diff as §1), and give the
harness the escape via `ALTER ROLE <test_role> SET bookhop.allow_flush = 'yes'`
on a role production does not use.

**Severity: MATERIAL.**

---

## 4. MATERIAL — a failed idempotent write poisons its key for 24 hours, with
## no release path

**Failure case.** `apps/core/api.py:468-477`: the key row is claimed and
**committed** (`idempotent()` runs its own `transaction.atomic()`), the handler
then runs **outside any transaction** (`ATOMIC_REQUESTS: False`), and
`store_idempotent_response` is called after it. So:

- handler raises `ValidationFailed` → key row is committed with
  `response_status = NULL`. Client retries the same body →
  `409 IDEMPOTENCY_IN_PROGRESS`, forever, until `expires_at`. Client corrects
  the field → different `request_hash` → `409 IDEMPOTENCY_KEY_REUSED`. The
  student is wedged on both branches.
- process dies between handler commit and `store_idempotent_response` → the
  work happened and the client can never learn the result. Same 409 for 24h.

API-CONTRACT §4.1 specifies `IN_PROGRESS` for "a request still in flight". It
does not say what a *finished and failed* request leaves behind, and the
implementation chose the one answer that cannot be retried out of. On the
endpoints §4.1 argues hardest about — `/grievances`, the copyright notice form,
the doors a distressed non-user arrives at — a single mistyped field means the
form cannot be resubmitted.

**What would have to be true.** That every L3 form mints a fresh key on
re-render after an error. `web/views.py` would have to guarantee that; it is not
a property the mechanism has, and L2 callers get no such help.

**Cheapest test.** POST an idempotent endpoint with a body the handler rejects,
then POST the corrected body with the same key, then the original body again.
**Pass = the corrected body is accepted (or the key is released on a 4xx);
fail = 409 on both.** Fix: delete the key row when the handler raises a 4xx, or
store the error response as the idempotent result — one branch in `endpoint()`.

**Severity: MATERIAL.**

---

## 5. MATERIAL — the `SYSTEM` sentinel is compared by identity, so a
## deserialised actor silently becomes a `USER` in the audit trail

**Measured on PostgreSQL:**

```
json.loads('"SYSTEM"') == SYSTEM : True    is SYSTEM : False
visible_campus_ids(SYSTEM)       : [3]
visible_campus_ids(deserialised) : []
record_audit(deserialised, ...)  : actor_type = 'USER'
```

`apps/core/scoping.py:22` defines `SYSTEM = "SYSTEM"` and both
`visible_campus_ids` and `record_audit` test it with `is`. A string that arrives
from JSON — a job payload, an API body, a management-command argument, which is
exactly how job handlers will pass an actor from S2 onward — is equal but not
identical. Two consequences, pointing opposite ways:

- `scoped()` returns an **empty queryset** and the job silently does nothing.
  Fail-closed, so not a breach, but a background job that quietly processes zero
  rows is the hardest failure in the system to notice.
- `record_audit` falls through to the user branch and writes
  `actor_type='USER', actor_id=NULL` for a system action. **That is audit
  misattribution in the one table whose entire purpose is attribution**, and
  the CHECK constraint passes because `USER` is a legal value — rule 18 exactly:
  the constraint proves the box is filled, not that it is true.

**What would have to be true.** That `SYSTEM` only ever reaches these functions
as the module-level literal. CPython interns identifier-shaped literals in
*source*, which is why every current call site works and why this will survive
until the first job payload carries an actor.

**Cheapest test.** `assert record_audit(json.loads('"SYSTEM"'), ...).actor_type
== "SYSTEM"` and `visible_campus_ids(json.loads('"SYSTEM"')) ==
visible_campus_ids(SYSTEM)`. **Fail = either differs.** Both differ today. Fix:
`SYSTEM = object()` with a module-level `is_system(actor)` predicate that also
accepts the string, or compare with `==`. One line either way.

**Severity: MATERIAL.**

---

## 6. MATERIAL — `restrict_when_gate_closed` implements a per-row predicate as
## a per-query branch, and the mismatch bites the first multi-campus caller

**Failure case.** ADR-002 §4.1(c)'s SQL is `(:discovery_open OR is_seed)` — a
predicate evaluated **per row**. `apps/core/scoping.py:94` takes a single
`campus` and either returns `qs` whole or filters it to `is_seed=True`. The
composition the codebase already makes possible —
`restrict_when_gate_closed(scoped(qs, SYSTEM), some_open_campus)` — returns
every row on every campus, including the non-seed rows of campuses whose gate is
**closed**, because `visible_campus_ids(SYSTEM)` spans all active campuses and
the branch looked at one of them. There is no such caller yet (S2 lands
listings), which is the only reason this is material and not critical.

**What would have to be true.** That every caller passes a queryset confined to
exactly the campus it passes. Nothing in the signature or the tests enforces
that, and the docstring's named second audience — "staff and seed actors who
legitimately read a closed campus" — is precisely the multi-campus reader.

**Cheapest test.** One open campus, one closed campus, a non-seed row on each;
call `restrict_when_gate_closed(scoped(qs, SYSTEM), open_campus)` and assert the
closed campus's non-seed row is absent. **Fail = it is present.** Fix: make the
helper take the queryset only and express the ADR's predicate as written —
`qs.filter(Q(is_seed=True) | Q(campus__discovery_enabled_at__isnull=False,
campus__active=True))`. One row predicate, no campus argument, no caller able to
get it wrong. Rule 15, applied.

**Severity: MATERIAL.**

---

## 7. MATERIAL — P14's shape exemptions mask a money token anywhere in a name,
## not only in the exempted position

**Measured against the shipped control (`apps.core.p14`):**

```
'inr_due_at' : W1b hits = []   shape_exempt=True
'due_at_inr' : W1b hits = []   shape_exempt=True
'usd_due_at' : W1b hits = []   shape_exempt=True
control: 'due_inr' -> ['due']
```

`money_tokens_in` strips each exempted shape as a **substring anywhere** in the
name. `due_at` therefore masks the `due` token in any position, and because W1
inspects only *numeric* columns, `receipts.inr_due_at text` holding
`"300 due"` passes every layer of P14 on a green build. This is QA-S0 F6's
`due_inr text` attack with four characters added, and
`test_the_token_shape_exemptions_cannot_swallow_a_known_attack` tests the old
spelling. Rule 15 predicted this: the exemption is a list, and the ceiling
declared in `p14.py` names the token collision but not the positional
generalisation.

**What would have to be true.** That no future column name contains an exempted
shape anywhere except as the suffix the discriminating question was answered
for.

**Cheapest test.** Parametrise the existing attack test over
`("inr_due_at", "due_at_inr", "usd_due_at")`. **Fail = `money_tokens_in`
returns `[]`.** It does. Fix, one line and strictly tightening: match the
exemption at suffix position — `name.endswith(shape)` or
`name.endswith("_" + shape)` — which keeps every mandated SLA column
(`purge_due_at`, `sla_due_at`, `disposal_due_at`) green. `consume` needs the
same treatment or, better, rule 13 step 1: rename it. It is ours.

**Severity: MATERIAL.**

---

## 8. MATERIAL — the response boundary enforces 4 of the 22 money tokens the
## schema enforces

**Measured:** `p14.W1B_MONEY_TOKENS` has 22 entries;
`p14.FORBIDDEN_RESPONSE_KEYS` has 4 (`price`, `amount`, `total`, `value`).
Never checked in a response body:

```
paise, rupee, rs_, amt, cash, money, fee, cost, sum, consideration,
settle, settled, tender, charge, paid, payment, due, balance
```

So `{"settled_paise": 30000}` or `{"cash_received": true}` leaves the API
without tripping anything, while the identically-named column cannot exist. Both
lists live in the same file, four screens apart, as two hand-made expressions of
one rule — which is rule 10's defect inside the file that exists to prevent rule
10's defect. `p14.py`'s own header says "the tests import it rather than
retyping it"; the problem is not retyping, it is that the one definition
contains two.

**What would have to be true.** That a response key can only leak money under a
name containing one of four words. ADR-003 §2.3 asserts the 22 for the schema
and does not explain why the response surface deserves fewer.

**Cheapest test.** Assert `set(FORBIDDEN_RESPONSE_KEYS) >=
set(W1B_MONEY_TOKENS)`, or delete `FORBIDDEN_RESPONSE_KEYS` and have the
response boundary read `W1B_MONEY_TOKENS` with `MONEY_WORDS_EXEMPT` applied.
**Fail = the response list is a proper subset.** It is. The second option is
smaller and removes the divergence rather than testing for it.

**Severity: MATERIAL.**

---

## 9. MATERIAL — campus-scoped feature flags cannot exist, and `flag()`'s
## campus branch is dead code

**Measured:**

```
per-campus override REFUSED: duplicate key value violates unique constraint
  "feature_flags_pkey"  DETAIL: Key (key)=(listings.swap_ui)
flag(global)=False  flag(campus)=False
```

DATA-MODEL §1 gives `feature_flags` `key text PK` **and** `scope_type`,
`scope_id` columns. One key, one row. `services.flag(key, campus)` implements a
two-level resolution — campus override, else global — over a table that can
physically hold only one row per key, so the first branch is unreachable. The
document declares a capability, the schema forbids it, the service layer
implements it, and no test asks whether the two rows can coexist. D-007's
"representable in the model, absent from the UI" for `listings.swap_ui` is the
exact case a per-campus rollout would want.

**What would have to be true.** That no flag is ever scoped to a campus — in
which case `scope_type`, `scope_id` and half of `flag()` should go.

**Cheapest test.** The probe above: create a GLOBAL row and a CAMPUS row for one
key. **Pass = both exist and `flag(key, campus)` prefers the campus row; fail =
IntegrityError.** Fix is a decision, not code: either `UNIQUE (key, scope_type,
scope_id)` with a surrogate PK, or delete the two columns and the branch. Do not
leave it as it is — this is the shape rule 9 was written for.

**Severity: MATERIAL.**

---

## 10. MATERIAL — the most legally significant audit row does not contain the
## authorising human's name

**Measured:**

```
columns containing the human's name: []
actor_type='SYSTEM' actor_id=None actor_pseudonym=None after_hash=90a3772a...
```

REVIEW-S0 N5 found that `discovery.open`'s audit row read `actor_type='SYSTEM'`
with no human named, and the fix put the name in `record_audit`'s `after`
payload. But `AuditLog` stores `after_hash`, not `after` — by design, per
DATA-MODEL §8. So the name is **hashed and discarded.** You can verify it if you
already know it; you cannot read it out of the audit trail, and "the audit row
gets a human either way" in `open_discovery`'s own comment is not true of the
row. The go/no-go packet still cannot name who opened the gate from the audit
log alone.

**What would have to be true.** That the `gate_authorisations` row is always
available and always joinable — which is nearly true (the row is append-only and
its id is in the hashed payload, also unreadable). The audit log is supposed to
be the self-contained record.

**Cheapest test.** Open the gate through the command; assert some column of the
resulting `audit_log` row contains the authorising human's name.
**Fail = none does.** None does. Fix: pass the human as `actor` so `actor_type`
and a name column carry it, or add the one text column DATA-MODEL §8 needs.
Either way the claim and the check become one artefact.

**Severity: MATERIAL.**

---

## 11. MATERIAL — nothing has been deployed, no backup has been restored, there
## is no CI, and no student journey has ever been completed

No `.github/`, no CI of any kind: the "both engines" property that three
findings in this memo depend on is enforced by a human remembering to type
`BOOKHOP_DB_ENGINE=sqlite`. INFRA.md §3 specifies backups with a tested restore;
zero backups exist and zero restores have been attempted, so the one claim
`ENABLE ALWAYS` is defence for — a restore or a replication apply worker — has
never been exercised. 835 tests have proved a large number of *properties*.
Nothing has proved the *product*. The programme is about to stack listings on
accounts on a foundation that has never served a page to a person.

**What would have to be true.** That properties compose into a working product.
Every finding in this memo is a counterexample: each one is a property that
holds locally and fails at a join.

**Cheapest test, and it is cheap.** One VM, one deploy, one `pg_dump`, one
restore into a scratch database with migrations applied, and one human
completing request-link → email → consume → age → consent → profile. **Pass =
the journey completes and the restored database passes `verify_audit_chain`;
fail = anything in that sentence does not happen.** Timebox it to one day. It is
the single highest-information day available to this programme.

**Severity: MATERIAL** (structural, and the first of the three ranked changes
below is not this one only because §1 is a legal exposure).

---

## 12. Minor findings, stated once and not argued

| | Finding | Cheapest check |
|---|---|---|
| m1 | `record_audit(obj=<unsaved model>)` writes `object_id = 'None'` — the string, not NULL. Measured. `str(getattr(obj,"pk","")) or None` stringifies `None` to a truthy value | assert `object_id is None` for an unsaved object |
| m2 | `is_canonical_uuid4`'s `str(key).strip().lower()` — the `.strip()` is dead (`uuid.UUID` already rejects padded input on length) but reads as a normalisation the function does not perform. Harmless now; it is the line a future reader will trust | assert a space-padded UUID is rejected, and drop the `.strip()` |
| m3 | `endpoint()` catches `ServiceError` only. A `ValueError` in a handler returns Django's **HTML** 500 from a JSON endpoint, so API-CONTRACT §2.2's "one error shape, everywhere" is false for the one case it matters | assert a handler raising `ValueError` returns `application/json` with `code: INTERNAL` |
| m4 | `/readyz` builds a full `MigrationExecutor` graph per probe — unauthenticated, uncached, disk + `django_migrations` query on every load-balancer poll | assert the handler does not re-read the migration graph more than once per N seconds, or cache it |
| m5 | `request_magic_link` neither caps nor invalidates prior unconsumed tokens; the 5/hour limit means five live links per address | assert requesting a second link consumes or invalidates the first |
| m6 | `record_audit` computes `occurred_at` once before the retry loop, so a row that took 12 attempts (~0.8 s of `time.sleep` **inside the caller's open transaction**) is stamped before its retries | assert `occurred_at` is within tolerance of commit time under contention |
| m7 | `store_idempotent_response` is absent from `services.__all__` while every sibling is present | assert `__all__` covers the public surface API-CONTRACT §3 names |

---

## 13. Live regression, handed back rather than scored

As of this session, an **uncommitted** autouse fixture in `tests/conftest.py`
(`_clear_rate_limit_cache`, calling `cache.clear()` on the new `DatabaseCache`
backend) gives **99 tests** a database access they do not declare. Measured now:
99 errors on **both** engines; before the edit, zero. Two things worth saying:

1. The mechanism is engine- and order-dependent. Earlier in this session the
   same 99 tests **passed on PostgreSQL and errored on SQLite**, because the
   session-scoped `allow_test_flush` fixture leaves a PostgreSQL connection open
   and pytest-django's blocker cannot block an already-connected alias. That is
   the project's signature defect — green for the wrong reason — introduced by
   the *fix* for QA-S0 F9, and it would have presented as "SQLite is broken."
2. Nothing in three reviews and five QA passes is shaped to catch it. Running
   the suite on the second engine is. See ranked change 3.

Not scored as a defect against the committed tree. It is the argument for CI.

---

## 14. The architecture, on its merits

**The stack is right and I could not make a case against it.** Django 5.2 +
PostgreSQL 16 + server-rendered HTML + htmx + no Redis + no Celery + no SPA, on
one VM, for 2–3 campuses is the correct answer, and the two places it deviates
from convention are the two places the reasoning is strongest: a `jobs` table
instead of a broker (with the conditional-UPDATE claim, because SQLite silently
omits `FOR UPDATE SKIP LOCKED` — measured, not assumed), and magic-link auth
with no password column, which removes the entire credential-storage chapter.
The job claim is a correct compare-and-swap with a lock timeout; I attacked it
and it holds.

**The audit chain holds under the attack I brought.** I spent real effort trying
to make `verify_audit_chain`'s id-ordered walk disagree with the `prev_hash`
chain under concurrency, and it cannot: `prev_hash UNIQUE` forces a losing
appender to block until the winner commits or aborts, so a committed row always
follows the then-maximum visible id, and id order equals chain order **by
construction**. `APPEND_MAX_ATTEMPTS = 12` measured rather than guessed, and
`AuditAppendContention` separated from `AuditChainBroken` so a load spike is not
reported as a tamper, are the two best pieces of work in the repository. Leave
them alone. The declared ceiling — that the chain serialises every append — is
correctly stated and correctly escalated rather than edited.

**Over-built:** the 11-state transaction machine and the four frozen tables are
specified in full for slices S4 and S5 that do not exist, and `FROZEN_TABLES`
pins 31 column names on a table nobody has created. The global audit chain is
over-built in a specific way: a single linear chain across all campuses makes
every append in the system contend with every other, and the upgrade path
(per-scope chains) is already written down — which means the cheap version was
chosen with the expensive version designed. That is fine; what is not fine is
that `record_audit` sleeps up to ~0.8 s **inside the caller's transaction**,
holding row locks, to resolve that contention.

**Under-built, and these are the gaps that matter:** no row-level security and
no second database role, which is what makes §1 and §3 reachable at all; no
retention rule on `jobs`, which is what makes §2 permanent; and nothing between
the service layer and the database on the gate. Multi-campus and multi-city in
the data model from day one is **not** over-built — it is two columns and an
index, and ADR-002's "widen by data, never by schema" is why §6's fix is a
one-line predicate instead of a migration.

**The tombstone deletion design** and `has_visible_character` survived scrutiny
and should not be touched. The latter is the best single illustration of rule 15
in the repo: it consults no list, asks Unicode per character, and the SQL floor
below it declares its own ceiling in the same place.

---

## 15. The test regime

**835 collected, and the count is the least interesting thing about them.**

**Load-bearing, keep:** `tests/e2e/test_postgres_concurrency.py` and
`tests/unit/test_audit_chain_race.py` — these are the only tests in the suite
that found anything no reviewer could have, and both of this project's two
real production-grade defects came from them. `test_postgres_catalog.py`
reading installed DDL back from `pg_get_functiondef` and `pg_trigger.tgenabled`
rather than trusting the migration source is exactly right. `test_p14.py`'s
attack tests — the ones that *attack* rather than *document*.

**Ceremony, and I would cut it:** the 10 `test_finding_*` tests. These assert
that a known gap **still exists**. The consequence is mechanical and is
happening right now:
`test_finding_the_key_is_checked_for_uuid_shape_not_for_uuid_version` is **red
on PostgreSQL today because the gap was closed.** A test that turns red when the
defect is fixed trains the next person to either re-open the gap or delete the
test, under schedule pressure, which is rule 13's failure mode pointed at the
suite instead of at a guard. A known gap belongs in `xfail(strict=True)` — which
goes red only when it is *silently* fixed and tells you to update the register —
or in the QA-S0 findings table where it already is. **Cost of deleting: zero.
The register is the artefact; the green assertion is a decoy.**

**Passing for the wrong reason — the project's signature, found a sixth time.**
§13 above: 99 tests that declare no database access were green on PostgreSQL
because a session fixture left a connection open, and the blocker that exists to
guarantee the property was off for the whole session. Rule 12 says a vacuous
guard is worse than none because it is reported as coverage; here the *isolation
mechanism*, not a guard, was vacuous, and the suite counted 99 tests as
evidence of something they did not test.

**Where "QA writes from specification without reading implementation" produced a
test of the specification rather than the behaviour:** §1. QA tested the
database floor — the thing the specification said the trigger does — and passed
it. It is the composition of the floor with the command above it that fails, and
that composition is not in any specification, so writing from specification
could not have found it. The method is sound and has a blind spot with a name:
**it cannot test a seam, because a seam is not specified anywhere.** That is the
single most important thing in this memo about the method.

**And the conformance-test idea itself.** It works — rule 9 is the reason
`p14.py` exists as one importable definition, and `p14.py` is what I used to
falsify §7 and §8 in four minutes. But §1 is the counterexample that bounds it:
asserting a control *exists* does not assert the control is **where the document
implies it is**. The conformance test for the gate passes, is honest, and tests
the floor; the document's summary of it reads as a wall. Rule 9 needs one more
clause: **a conformance test must assert the control at the boundary the
document claims, not at the boundary the implementation chose.**

---

## 16. The apparatus — the objection pressed, and then answered

**The case against the apparatus, as strongly as I can make it.** Slice S0 was a
Django skeleton, a feature-flag table, an audit table and a 153-line job runner.
It consumed three code-review passes, five QA passes, 40 logged decisions, 18
project rules and a suite that is now 835 tests. Measured volumes: **3,778 lines
of actual code** in `apps/ + bookhop/ + web/`, carrying **2,664 lines of prose
inside them** (1,896 docstring + 768 comment — 71% of the code volume), beneath
**11,776 lines of architecture markdown** and **2,640 lines of decision log**.
That is roughly **3.8 lines of document per line of code**, and every one of
those lines is a maintenance liability for one person: rule 9 says a document
may not assert a property without a conformance test, so each of those 14,400
lines is a potential test obligation. The eighteen rules are not independent —
11, 13 and 15 are three statements of "a list is the wrong shape," and 9, 17 and
18 are three statements of "the document is not the control." A solo founder
reading them cold at 2 a.m. in six months will not hold eighteen distinct
things; they will hold three, and the other fifteen will be the thing that gets
skipped first.

**The case for it, from the evidence.** Two defects were found **only by
executing PostgreSQL** — an audit row dropped under contention and reported as
tamper, and a session-scoped GUC bound to one connection — and both would have
shipped green on SQLite and failed first in production, one of them presenting
as a tamper alert during a load spike. A guard enforced 15 of 22 entries and the
gap was worth four text columns each holding a settled price. A control did not
cover the case it was written for (`active=false`). The `endpoint` column was
stored and never compared, which replayed one endpoint's response to another.
Those are not process artefacts; they are four real defects in a 3,778-line
codebase, which is a high density, and three of the four are the kind that get
found in production or not at all. And the artefacts themselves have compounding
value: `p14.py` as one importable definition, the `ponytail:` ceiling notes, and
ENGINE-DIVERGENCE's `VERIFIED HERE` / `ASSUMED THERE` labels are what let a
hostile stranger — me — find nine substantive defects in a single pass without
asking anyone a question. That is not theatre. That is the documentation working.

**Which way the evidence actually falls.** **The apparatus earns its keep; the
*ceremony* does not, and they are separable.** The things that found defects were:
running the second engine, running real concurrency, reading installed DDL back
from the catalog, and keeping one importable definition per rule. The things that
found nothing were: review passes two and three, the decision log past about
D-030, nine of the eighteen rules, and the `test_finding_*` genre. The ratio the
brief asks about is real, but it is not ceremony-to-feature — it is
**artefact-to-transcript**. REVIEW-S0 at 1,627 lines and the 2,640-line decision
log are transcripts of deliberation, and a transcript has no readers. A solo
founder will not maintain them and should not try.

**What I would delete, specifically.**

1. **The 10 `test_finding_*` tests.** Convert to `xfail(strict=True)` or move to
   the findings register. One is red right now for being fixed.
2. **Review passes 2 and 3 as a standing gate.** Replace with one review plus
   one mandatory **adversarial execution** pass — a named agent whose only job
   is to run the thing on the other engine, under concurrency, and against the
   written claim. That is the pass that found everything.
3. **Rules 11 and 13, folded into 15.** Three rules, one idea: ask the property,
   not the list; where you must use a list, give each entry a match rule and
   declare the ceiling in the same place. Keep 15's text, keep 13's
   rename-first-exempt-second ordering as a sub-clause, delete the rest.
   Eighteen rules that are really twelve will be obeyed; eighteen will not.
4. **REVIEW-S0.md and QA-S0.md reduced to their findings tables.** Keep every
   finding and its verdict. Delete the deliberation prose — roughly 2,000 lines
   that no future reader will open.
5. **`FROZEN_TABLES`' 31 pinned column names for S4/S5 tables that do not
   exist.** Pin them in the slice that creates them. Today they are a founder
   escalation attached to a table nobody has written.

**What I would not delete, under any schedule pressure:** rule 9, rule 10,
rule 15, rule 17; `p14.py` as one importable definition; the `ponytail:` ceiling
comments; and the both-engines run — which, see ranked change 3, is currently
protected by nothing but memory.

---

## 17. The three things I would change first, ranked

**1. Move the gate and the audit log from a trigger to a privilege.** One
migration: revoke `INSERT`/`UPDATE`/`TRUNCATE` on `gate_authorisations` and
`TRUNCATE` on `audit_log` from the `bookhop` role; give `open_discovery` a
second `DATABASES` alias with its own role; keep every existing trigger. This
closes §1 (critical) and §3 (material) in the same diff, and it gives rule 14's
"two independent layers" its first genuinely independent second layer — today
the gate has one layer twice. Cost: one migration, one settings block, one line
in INFRA. **Do this before S2.**

**2. Stop persisting the raw magic-link token, and make the docstring true.**
Delete the job row on success, add `jobs` to `purge_expired` for the failed
ones, scrub `payload` before writing `last_error`, and add the conformance test
from §2. Closes the second critical. Cost: four lines of code and one test.
**Do this before the first real email is sent.**

**3. One deploy, one restore, one journey, one CI file.** Put it on a VM, take a
`pg_dump`, restore it into a scratch database, run `verify_audit_chain` against
the restore, and walk one student from request-link to profile. Add a GitHub
Actions file that runs the suite on **both** engines on every push — which is
~15 lines and is the only thing that would have caught §13, and the only thing
that keeps the second engine from quietly becoming optional. Timebox: one day.
This is the cheapest remaining way for this programme to discover it is wrong,
and it is the one thing 835 tests structurally cannot tell you.

---

## 18. What survived scrutiny and should not be touched

- **The audit hash chain and its concurrency argument.** `prev_hash UNIQUE`
  makes id order equal chain order by construction; I tried hard to break it and
  could not. The split of `AuditAppendContention` from `AuditChainBroken`, and
  the measured rather than guessed retry budget, are the best work here.
- **The job runner's conditional-UPDATE claim plus `JOB_LOCK_TIMEOUT`.** Correct
  CAS, correct release, correct declared ceiling, and the reason it deviates
  from ADR-001's `SKIP LOCKED` is measured on the engine that silently omits it.
- **Single-use magic-link enforcement by conditional UPDATE on
  `consumed_at IS NULL`.** Right mechanism, right place, correctly argued as
  API-CONTRACT §4.1's idempotency exemption.
- **`has_visible_character`,** and the honest declaration that the SQL floor
  below it enumerates while it asks the invariant.
- **The close-always-permitted asymmetry on the gate.** Correct, and the
  asymmetric reasoning is recorded where the next reader will find it.
- **`p14.py` as the single importable expression of ADR-003 §2.3.** The highest-
  leverage artefact in the repository; it is what made this review possible.
- **The stack.** Django + PostgreSQL + htmx + a `jobs` table + one VM. No
  objection.
- **Multi-campus/multi-city in the data model from day one.** Two columns and an
  index, and it is why §6's fix is a predicate rather than a migration.

---

## 19. Objections register for this gate

| # | Objection | Severity | Proposed test | Status |
|---|---|---|---|---|
| 1 | Gate floor below ADR-002 §4.1(b); ORM opens the gate, no audit row | **critical** | 3-statement probe, both engines | measured, open |
| 2 | Raw magic-link token persisted in `jobs.payload` forever; docstring false | **critical** | no job row retains a credential | measured, open |
| 3 | `bookhop.allow_flush` reachable from the app role | material | app role refused the SET or the TRUNCATE | measured, open |
| 4 | Failed idempotent write poisons the key for 24 h | material | reject-then-correct-then-repeat | open |
| 5 | `SYSTEM` compared by identity; audit says `USER` | material | deserialised sentinel round-trip | measured, open |
| 6 | `restrict_when_gate_closed` is per-query, spec is per-row | material | two campuses, SYSTEM actor | open |
| 7 | P14 shape exemptions mask tokens in any position | material | `inr_due_at` parametrisation | measured, open |
| 8 | Response boundary enforces 4 of 22 tokens | material | superset assertion | measured, open |
| 9 | Campus-scoped flags unrepresentable; `flag()` branch dead | material | two rows, one key | measured, open |
| 10 | `discovery.open` audit row does not name the human | material | name appears in a column | measured, open |
| 11 | Never deployed, never restored, no CI, no journey | material | one deploy, one restore, one journey | open |
| 12 | Seven minor findings, §12 | minor | per row in §12 | open |

Two critical objections escalate to the founder per charter. Objections 1, 2 and
3 are closed by two diffs.
