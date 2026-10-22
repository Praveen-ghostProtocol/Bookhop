# REVIEW-S1.md — Code Review of slice S1

**Reviewer:** code-review agent · **Date:** 2026-10-22 · **Commit:** `a8bde62`
**Scope:** accounts, magic-link auth, age eligibility, campus verification,
profiles, consent, deletion, the purge job, 12 JSON endpoints, the full
server-rendered interface, CSP middleware, the error-shape renderer, the locale
gate, EN + TA catalogues.
**Authored by:** backend-developer and frontend-developer. **I wrote no line of
this diff**, so I am competent to review it (charter hard rule 1).

---

## VERDICT

# CHANGES REQUIRED

Six blocking findings. The slice is, on the whole, unusually good engineering —
the append-only trigger loss (B/F3 below) is the best single piece of work in
the project so far, and the frontend's byte weights and CSP cleanliness are
exactly as reported, measured independently. But three of the six blockers are
the same failure the project has now found seven times: **a document, a
docstring or a test name asserting a property that the code does not have.**
Two of them are in the test harness itself, which means the reported numbers do
not mean what they say.

**The thing I checked last and most carefully**, and the reason this is not an
approval: I tried to reproduce `911 passed / 48 skipped / 2 xfailed, zero
failures`. I could not. Five identical runs of the identical tree on this box
gave **911, 922, 924, 927, 927 passed**, with **0 failures on the first run and
2 on each of the next four**. The suite's verdict is not a function of the
tree, the cause is measured and named in an *uncommitted* file in the working
tree, and `tests/conftest.py` carries a `VERIFIED HERE on PostgreSQL 16.15`
label asserting the opposite of what I measured. That is `CLAUDE.md` rule 17
broken inside the file that controls test isolation.

**QA has not verified this slice.** Nothing in this review substitutes for
that, and the a11y position is explicitly unverified: `tests/a11y/test_pages.py`
skips the keyboard-only walkthrough and the p75 LCP measurement with a stated
reason, so **S1 has no WCAG 2.2 AA pass** — only a structural HTML sweep. Do
not read this review as coverage of either.

---

## Reproduction: what I ran

```
PostgreSQL 16, BOOKHOP_TEST_DB_NAME=test_bookhop_review_*
  full working tree, 5 runs:     911 / 922 / 924 / 927 / 927 passed
                                 0 / 2 / 2 / 2 / 2 failed, 48 skipped, 2 xfailed
  committed tree only, 3 runs:   921 / 921 / 921 passed, 48 skipped, 2 xfailed
                                 (first attempt: 914 — see B1)
SQLite
  full working tree:             851 passed, 109 skipped, 1 xfailed
```

`--collect-only` is deterministic (972 / 965 tests). The *run* totals are not.
**The reported numbers were real when they were taken and are not reproducible.**
On the committed tree with the two untracked probe files excluded the suite is
green, and that green rests on the defect in B1.

---

# BLOCKING — must change before merge

### B1 · The suite's verdict is not a function of the tree, and `conftest.py` says it is

**Files:** `tests/conftest.py:131–170` (`_isolate_rate_limit_counters`
docstring) · `tests/conftest.py:30–66` (`allow_test_flush`) ·
`tests/conftest.py:69–105` (`restore_gate_privileges_for_the_harness`) ·
`tests/contract/test_s0_surface.py:376–425` (**uncommitted**)

`tests/conftest.py` states, under an explicit `CLAUDE.md` rule 17 label:

> **VERIFIED HERE on PostgreSQL 16.15:** a query issued from a test with no
> `db` fixture, with the session connection open, raises `RuntimeError:
> Database access not allowed` … So the undeclared-access half did not occur;
> **the swallow did**, and that is what is fixed here.

**Measured here, on PostgreSQL 16, four runs out of five: that claim is false.**
The uncommitted QA test in the working tree executes `SELECT 1` from a test with
no `django_db` marker and no `db` fixture, the query **succeeds**, and the test
fails with a message that already names the cause and the fix:

> MEASURED CAUSE: the alias is already connected when a non-`django_db` test
> starts … two session-scoped autouse fixtures in `tests/conftest.py` open one
> at session setup and never close it, `allow_test_flush` and
> `restore_gate_privileges_for_the_harness`. MEASURED FIX: `connection.close()`
> at the end of each of those fixtures restores the blocker — verified
> directly.

**Concrete failure:** any test in the repository can commit rows outside its
per-test transaction. Those rows survive into every later test, and because
`audit_log` is one hash chain across the whole table, the resulting failures
land on audit-chain tests rather than on whichever test leaked — a
**tamper-shaped error produced by test ordering**. This is the same failure
mode the first PostgreSQL run already found once (`AuditChainBroken` raised by
load) and it is now reachable from the harness. It also explains the 911 → 927
drift I measured: the pass count depends on which rows happened to leak.

**Smallest correct fix:** add `connection.close()` at the end of both
session-scoped fixtures (two lines), delete the `VERIFIED HERE` paragraph that
asserts the opposite, and **commit the QA test** — it is the only thing that
makes a green run mean anything. `_declare_flush_escape(None, connection)`'s
retroactive call then becomes redundant, as the failure message notes.

**Rule cited:** `CLAUDE.md` rule 17 (a `VERIFIED HERE` label on a platform
claim that is wrong), rule 12 (a green suite reported as coverage when it is
one sample of a distribution), rule 9.

---

### B2 · The working tree is not the commit, and it contains twelve tests with no assertions

**Files:** `tests/e2e/test_erasure_sessions.py` (**untracked**) ·
`tests/e2e/test_probe2.py` (**untracked**) · `tests/e2e/_weird_serializer.py`
(**untracked**) · `tests/contract/test_s0_surface.py` (**modified,
uncommitted**)

`git status` on the reviewed commit is not clean. Three files are untracked and
one guard-test file is modified and uncommitted. The two untracked test files
contain **seven test functions, every one of which has zero assertions** —
they are `print()`-only exploration scripts:

```python
def test_undecodable_beside_valid(...):
    ...
    print("before:", Session.objects.count(), _decodes_to(u.id))
    erase_account(u)
    print("after:", Session.objects.count(), _decodes_to(u.id))
```

Every one of them is counted in the reported `passed` total. One
(`test_serialiser_changed`) fails outright with
`ImportError: Module "tests.e2e.test_erasure_sessions" does not define a
"Weird" attribute/class`.

**Concrete failure:** `rule 12` in its purest form — seven tests reported as
coverage that cannot fail. And the numbers in the commit message were produced
from a tree that is not the commit, so the commit message's evidence does not
describe the commit.

**Smallest correct fix:** delete the three untracked files (they were useful
scratch work — the questions they probe are the right ones, and R3 below is the
answer; they are not tests). Commit the `test_s0_surface.py` addition, which is
a genuine strengthening and belongs in the slice. Re-take the numbers.

**Rule cited:** `CLAUDE.md` rule 12, charter deliverable *"are the guard tests
still green and unmodified?"*

---

### B3 · `require_actor` — API-CONTRACT §2.5's standing preconditions — is called by nothing

**File:** `apps/accounts/services.py:1153–1191`

`require_actor` implements §2.5 correctly and in the contract's stated order.
**No caller exists.** `grep -rn require_actor apps web` returns the definition,
one unrelated docstring sentence and one test docstring. No service function,
no L2 handler and no L3 view invokes it. `sessions.session_user` excludes only
`status="TOMBSTONED"`, so a `SUSPENDED` account keeps a working session.

**Measured** (probe against `/api/v1/*`, PostgreSQL):

| action | actor state | result |
|---|---|---|
| `PATCH /api/v1/account` | required `account` consent **withdrawn** | **200**, name changed |
| `PATCH /api/v1/account` | `status = SUSPENDED` | **200**, name changed |
| `GET /api/v1/account/export` | `status = SUSPENDED` | **200**, full data file |
| `POST /api/v1/account/erase` | `status = SUSPENDED` | **200**, erased |

**Concrete failures:**
1. A suspended account — one suspended by `review_age`'s
   `REVOKED_MINOR_DISCOVERED` path, i.e. **a discovered minor** — can still
   read its own full export and change its profile. `errors.Suspended` exists,
   carries `http_status = 403`, and nothing raises it on these paths.
2. `withdraw_consent`'s own docstring says *"`require_actor` is what then
   refuses the write, with the missing `purpose_key` in the body"*, and
   `tests/unit/test_consent.py:213` repeats the claim in prose. **The claim is
   false.** JOURNEYS J1 step 5's guarantee that a student "is told which action
   it blocks" has no enforcement anywhere.
3. Charter item 6: authorisation is checked **in neither** the service nor the
   view.

**Smallest correct fix:** call `require_actor(user)` at the top of
`update_profile`, `record_nomination` and `export_account`, and have
`consume_magic_link`'s callers route through it for the §2.5 ordering. Add one
test per table row above. **One contract question for cto, not a free pass:**
whether `erase_account` should remain reachable while suspended — a suspended
data principal arguably keeps the s12 erasure right, which would make it the
single documented exemption rather than an oversight.

**Rule cited:** API-CONTRACT §2.5 · JOURNEYS J1 step 5 · THREAT-MODEL §5 (ASVS
V4) · `CLAUDE.md` rule 9.

---

### B4 · The notices endpoint bypasses the Tamil locale gate, and its guard test passes vacuously

**File:** `apps/accounts/api.py:323`

```python
locale = "ta" if request.headers.get("Accept-Language", "").startswith("ta") else "en"
```

This reads the raw header and never consults `feature_flags['i18n.ta_enabled']`.
`LocaleGateMiddleware` corrects the *translation catalogue*; it cannot correct a
handler that re-derives the locale from the header itself. THREAT-MODEL §6.1(c)
forbids exactly this by name: *"Tamil is absent from the language switcher **and
from `Accept-Language` negotiation** while `i18n.ta_enabled` is false."*

**Measured** (probe, PostgreSQL, flag confirmed `False`, one `en` and one `ta`
`notice_versions` row published):

```
GET /api/v1/notices/privacy  Accept-Language: ta
  -> 200   locale served: "ta"   body: the unreviewed Tamil notice
```

This is the one public, unauthenticated endpoint in the slice, and the body it
serves is a **legal notice** whose Tamil text no native speaker has reviewed
(`locale/ta/REVIEWED.toml` is empty, correctly).

**The guard test for this exact property passes vacuously.**
`tests/unit/test_locale_gate.py:73`
(`test_accept_language_ta_yields_english_on_a_json_endpoint`) hits this endpoint
with `Accept-Language: ta` and asserts `locale == "en"` — and passes **only
because its `privacy_notice` fixture publishes no Tamil row**, so
`current_notice` falls back to English for a reason that has nothing to do with
the gate. Its docstring calls it *"the half frontend's page helper could never
cover"*. It covers nothing. `CLAUDE.md` rule 12.

**Smallest correct fix:** ask the gate instead of the header —

```python
from django.utils import translation
locale = (translation.get_language() or "en").split("-")[0]
```

`LocaleGateMiddleware` has already run, so this routes through the one gate and
needs no second copy of the rule (rule 10). Then add a `ta` row to the fixture
in `test_locale_gate.py:73` so the assertion can fail.

**Rule cited:** THREAT-MODEL §6.1(c) · API-CONTRACT §2.1 · `CLAUDE.md` rules
10, 12, 14.

---

### B5 · `tests/unit/test_forbidden_copy.py` does not exist — the English deny-list has no enforcement

**Files:** absent · `locale/FORBIDDEN_EXCEPTIONS.toml` (read by nothing)

TASKS §2 S1 assigns it by name: *"backend writes `test_forbidden_copy.py`
(**English, whole-word, eight words**), `test_reviewed_locale.py` and
`test_locale_gate.py`."* Only the third exists. `grep -rn forbidden_copy` over
the repository returns **nothing outside `.claude/agents/frontend-developer.md`**,
and nothing anywhere reads `locale/FORBIDDEN_EXCEPTIONS.toml`.

**Concrete failure:** the eight forbidden words — *safe, verified, guaranteed,
protected, assured, trusted, certified, authentic* — plus Ban 2's four phrases
and the bare label `Price` are **unenforced in code** from the first slice that
ships copy. The manifest's `[strings]` emptiness, its two shape exemptions and
its `scanned_at_S1 = 122 / findings = 0` metadata all protect nothing, because
no scanner runs. The manifest header itself says it is *"Read by
`tests/unit/test_forbidden_copy.py`"* — a file that does not exist.

The frontend's `findings_in_shipped_copy_at_S1 = 0` is a **one-off manual scan
recorded in a comment**. I re-ran it by hand over all 122 `msgid`s and confirm
zero deny-list hits today — which is exactly why this must be fixed now rather
than after the first violation: the control is cheap while the baseline is
clean.

`test_reviewed_locale.py`'s job **is** adequately covered by
`test_locale_gate.py:218` (`test_the_flag_cannot_be_true_while_a_blocking_class_
string_is_unreviewed`), which guards against vacuity explicitly. That one is a
documentation correction, not a gap. `test_forbidden_copy.py` has no substitute.

**Smallest correct fix:** write it, reading the word list and both shape rules
**from the TOML** rather than retyping them (rule 10), scanning every `msgid`,
`msgid_plural` and `msgstr` in `locale/**/*.po` and every rendered span of
`templates/**` with `{% comment %}` bodies and `msgctxt`/`context` arguments
excluded — the shape rules the manifest already specifies as data.

**Rule cited:** TASKS §2 S1 · THREAT-MODEL §6.1(a) · `CLAUDE.md` rule 9 ·
D-026.

---

### B6 · Two shipped strings promise a service that does not exist (COPY-DECK §1.2)

**Files:** `templates/help.html:78` · `templates/gate_closed.html:21` ·
`locale/en/LC_MESSAGES/django.po`

This is charter item 10(b) — the check no grep in any language can perform.
COPY-DECK §1.2: *"BookHop's voice may describe a mechanism, name a fact, or
give an instruction. It may never make a prediction or a judgement about a
person, a book, or an outcome."*

**`help.response`**, under the heading *"If you need a person"*:

> "We read every message. We aim to reply the same day — we're a small team."

`web/views.py::help_page`'s own docstring says the opposite, correctly: *"there
is no door to open one … every support L1 function takes `staff`, no endpoint
exists, and **nothing stores what a student writes**."* So the sentence makes a
**prediction about an outcome** (§1.2 row 1) about a channel that does not
exist. There is no message to read and nobody to reply. It also undercuts
AC-H6.5, which the page is built around: *state what we can and cannot do
**before** the student types anything.*

**`gate.closed.body`**, the whole of the gate-closed notice:

> "You can leave a note saying which book you need, and we'll tell you when
> listings open."

`gate_closed.html` contains **no form**. `book_requests` is S2 and
`notifications` is S7. The page tells the student an action is available that
is not, and promises a notification nothing sends — *"we'll tell you"* is a
prediction. SYSTEM §4.22 asks this page for *"a full-page notice, no listing
data, and no date, because we do not have one"*; the copy supplies an
interaction instead.

Neither string contains a banned word, which is precisely why §1.2 is a review
item and not a test (and why B5 would not have caught them either).

**Smallest correct fix:** replace both with a fact or an instruction. For
`help.response`, name the routes that do exist (the page already lists the
statutory ones) and delete the promise. For `gate.closed.body`, state the
mechanism: listings are not open on this campus yet, and nothing can be listed
or searched until they are.

**Rule cited:** COPY-DECK §1.2 rows 1 and 5 · PRD AC-H6.5 · SYSTEM §4.22 ·
`CLAUDE.md` rule 1 (a commitment nothing performs).

---

# REQUIRED — must change, may be a follow-up commit in this slice

### R1 · Both strict xfails can never xpass, so the tripwire they claim does not exist

**File:** `tests/unit/test_least_privilege.py:145–207` ·
`apps/core/migrations/0008_least_privilege.py:255–261`

**The xfails are honest today.** I ran them with `--runxfail`: both fail on
their own assertion, with the gate genuinely opened
(`discovery_enabled_at = 2026-10-22 06:18:31`) and the audit log genuinely
emptied. Neither xfails for an unrelated reason. The three-part structure of
the file — the control exists / the live state measured / the attack tracked —
is the right shape, and the migration's honest four-row "what this buys" table
is exactly what `CLAUDE.md` rule 9 asks for. The reasoning about ownership is
correct and I verified the measurement independently:
`pg_tables.tableowner = current_user` for both tables.

**But the claim repeated in three places is false:**

> `strict=True`, so this file goes red the day it is fixed and must be
> de-xfailed then.

It will not. On the day the control lands, every success path **raises instead
of asserting**:

* `test_three_orm_statements_cannot_open_the_discovery_gate` — once `campuses`
  UPDATE is withheld or the trigger refuses, `Campus.objects.filter(...)
  .update(...)` raises a `DatabaseError`, the asserts are never reached, and
  pytest records **XFAIL** (an exception in an xfail-marked test is an xfail,
  not an xpass). Worse, its second assertion
  `AuditLog.objects.count() > audit_before` is **unsatisfiable by any
  implementation**: nothing in the test body writes an audit row, and a
  *refused* gate write correctly writes none. So even on the path where the
  first assert passes, the test still fails.
* `test_the_application_role_cannot_truncate_the_audit_log` — once TRUNCATE is
  withheld, `cursor.execute("TRUNCATE audit_log")` raises `permission denied`
  and the result is again XFAIL.

**Concrete failure:** a tracked CRITICAL that can never stop being tracked
automatically. The day platform-sre moves ownership, the suite stays green with
two xfails and nobody is told the finding closed — which is the one thing
`strict=True` was chosen for.

**Smallest correct fix:** make refusal an *accepted outcome* rather than an
error, and drop the unsatisfiable audit assertion:

```python
from django.db import DatabaseError
try:
    Campus.objects.filter(id=campus.id).update(discovery_enabled_at=timezone.now())
except DatabaseError:
    pass                      # refused — which is the fix landing
campus.refresh_from_db()
assert campus.discovery_enabled_at is None
```

The test then xfails today (the gate opens) and **xpasses** the day it is
closed, which is what the comment promises. Same shape for the TRUNCATE test.

**Rule cited:** `CLAUDE.md` rules 9 and 12 · charter *"a strict xfail that
would pass for an unrelated reason is worse than a skip"* — this is the
mirror case, and it costs the same thing.

### R2 · One of the two xfails has no engine guard, and on SQLite it xfails for a cause its reason text does not name

**File:** `tests/unit/test_least_privilege.py:145`

Its sibling at line 197 skips on SQLite with a correct reason. This one does
not, so on SQLite it is reported as **XFAIL** under the message *"It closes
when ownership … moves off the application role (a superuser deployment step;
**this box has rolsuper=false**)"* — a sentence about a PostgreSQL role system
that does not exist on SQLite. On SQLite the attack succeeds because
`campuses_gate_authorised` is satisfied by **any** live authorisation row, even
one whose evidence values are all `"x"` and which was granted against a
different legal entity. That is a real second cause, present on both engines,
and the reason text attributes the whole finding to privileges.

**Fix:** either skip on SQLite like its sibling, or split the reason so the
trigger's existence-only check is named as a separate limb. The second is
better: *"a live authorisation row is checked for existence, not validity"* is a
finding about ADR-002 §4.1(b)'s floor that belongs in the record.

### R3 · `_delete_sessions_for`: the swallow is dead code, the scan can silently match nothing, and the guarantee comes from somewhere else

**File:** `apps/accounts/services.py:1102–1122`

Backend's instinct is right, and the mechanism is *more* fragile than the
docstring admits. **Measured in the installed Django 5.2.8:**
`django/contrib/sessions/backends/base.py::decode` catches `BadSignature` and
every other exception and **returns `{}`**. It never raises.

So under a signing-key rotation without `SECRET_KEY_FALLBACKS`, a changed
`SESSION_SERIALIZER`, or a non-database session backend:

* `row.get_decoded()` returns `{}` — no exception;
* `{}.get(SESSION_USER_KEY)` is `None`, which never equals `user.id`;
* **zero rows are deleted, no exception is raised, nothing is logged**;
* `erase_account` returns normally, writes a `data_subject_requests` row with
  `outcome="COMPLETED"` and an `accounts.erased` audit row.

DATA-MODEL §10.1 step 3 is **reported executed when it was not**, and
`ERASURE_STEPS[(3, …, "S1", True)]` asserts it ran. The
`except Exception: # pragma: no cover - a corrupt session is not this path's
problem` is unreachable for the failure modes it was written for, and the
`pragma` hides that from coverage.

**The failure you named — "a deleted account still signed in on the student's
phone" — does not occur, and the reason is worth keeping:**
`sessions.session_user` loads the user with `.exclude(status="TOMBSTONED")`,
gets `None`, and **flushes the session**. So the device is signed out on its
next request regardless of whether the row was deleted. That is a genuine
independent second layer (`CLAUDE.md` rule 14), it is the thing actually
providing the guarantee, and **nothing tests it.**

**Is the gap closable at this layer?** Partly, and cheaply:

1. `_delete_sessions_for` returns a count; `erase_account` logs it. "deleted 0
   sessions for an account that had one" becomes visible instead of silent.
   One line each. This does not make the scan correct — it makes its failure
   detectable, which is `CLAUDE.md` rule 18's distinction between a floor and
   detection.
2. Add the test for the layer that holds: erase, then assert a request carrying
   the *undecodable* cookie cannot reach a signed-in page. That is the property
   the product relies on and it is currently unasserted.
3. The durable fix is the one the `ponytail:` note already names — a
   `user_id` column on a sessions table we own. It is a new table and a
   migration; **it is not S1's**, and the ceiling note is the right way to
   carry it. Do not take it now.

### R4 · `django_session` has no §7 row, no retention rule and no purge path

**Files:** `apps/accounts/services.py:1197–1285` · `COMPLIANCE.md` §7

S1 ships the first session in the product (API-CONTRACT §2.1's 14-day rolling
cookie). `purge_expired` walks `email_login_tokens`, `idempotency_keys`,
`personal_data_access_log`, `jobs` and `user_tombstones`. It does **not** walk
`django_session`, nothing calls `clearsessions`, and `Session.objects` appears
exactly once in all of `apps/**` — the read in `_delete_sessions_for`. No
`COMPLIANCE.md` §7 row names it.

**Concrete failure:** expired session rows accumulate forever. COMPLIANCE §8.3
— *"Retaining beyond the purpose without a legal basis is its own breach"* — is
the clause `PurgeLog`'s own docstring quotes, and this is the third table in
two slices with no retention rule (`idempotency_keys` in S0, `jobs` found by
Red Team, now this).

**Smallest correct fix:** three lines in `purge_expired` deleting
`Session.objects.filter(expire_date__lt=now)` with a `purge_log` row, plus the
§7 row. The expiry job already exists; this is one more rule inside it, which
is why charter item 7 asks for both together.

### R5 · `purge_expired` walks only *finished* jobs, so the claimed second layer does not cover an undrained queue

**File:** `apps/accounts/services.py:1248–1267` · `apps/core/jobs.py:56–86`

The credential fix is sound and I verified each of its four parts: `redacted()`
keeps key names only (an invariant, not a secret-name list — rule 15 applied
correctly); `_scrub` removes payload values ≥ 12 characters, which covers the
43-character `token_urlsafe(32)`; `purge_expired` walks `jobs`; the docstring
now matches the code.

**The stated residual is correctly bounded.** A retryably failing
`accounts.send_magic_link` holds its token across the 1+4+9+16-minute backoff;
the token dies at 10 minutes and the handler then refuses to deliver it. That
is a live credential for ≤ 10 minutes and a dead string for ~20 more. Accept.

**The residual that is not stated is the one that bites.** `purge_expired`
selects on `completed_at` and `failed_at`. A job that is **never claimed** has
neither, so it is never purged and never redacted. The pilot's cadence is
`manage.py run_jobs` from cron and *"the schedule is a systemd timer in S8"* —
so a queue that is not being drained (cron not installed, worker down, a
development box) accumulates **unredacted payloads with no bound at all**. The
migration-adjacent claim in `purge_expired`'s comment —

> `run_pending_jobs` now redacts a finished payload, so this is the second layer
> (`CLAUDE.md` rule 14): even a row whose redaction somehow did not run is gone
> within the window.

— is **false for a row that never finishes**, which is the only row whose
redaction did not run. Per rule 14 the exemption is affordable only if another
layer rejects the same thing, and here none does.

**Smallest correct fix:** add a bound on unclaimed rows — e.g. purge
`run_after < now - JOB_RETENTION` with `completed_at`/`failed_at` null and
`attempts = 0` — or redact the payload at the moment the token expires. State
whichever is chosen in the comment, because the comment is currently the
control's only description.

**Other paths a secret could reach durable storage — checked, all clean:**
`deliver_email` logs `{"template", "locale"}` only, never the body; `record_audit`
hashes its `before`/`after` payloads and the magic-link audit row carries no
payload at all; `idempotency_keys` stores `request_hash`, never the body (which
is also what keeps the declared DOB out of storage on
`POST /account/age-declaration`); `export_account`'s file contains the
student's own data and is served `Cache-Control: no-store` with
`Content-Disposition: attachment`; the token never appears in a URL that is
logged, because `auth_consume` redirects immediately so the token leaves the
address bar. One note at N3.

### R6 · The append-only existence control degrades to a presence check on PostgreSQL, and its claim-list guard is a tautology

**File:** `tests/unit/test_append_only_triggers_exist.py`

**The finding and the fix are excellent and I want to be clear about that
before the two gaps.** `accounts/0004`'s diagnosis is exactly right: SQLite
cannot alter a CHECK, Django rebuilds the table, the `DROP TABLE` takes the
triggers, and PostgreSQL — the engine production runs on — would never have
shown it. Importing `APPEND_ONLY_TABLES` from `0002` rather than retyping it
(rule 10) and generating the restore statements from it is the right
construction. The general control is the right response, it runs on both
engines, it guards against its own vacuity (`assert triggers, "…would pass
vacuously"`), it carries a per-entry citation rather than a flat list (rule 11),
and `test_the_introspection_would_notice_a_missing_trigger` proves the reader is
not blind. This is the best work in the slice.

**Does it assert that *every* table claiming append-only has its guard, on both
engines?** On SQLite, yes, including both limbs separately. **On PostgreSQL,
no.** `test_each_append_only_table_blocks_both_update_and_delete` reduces to:

```python
else:
    assert names, f"{table}: no guard on {engine}"
```

which is the same assertion as the existence test above it. On the production
engine a table whose row-level `*_append_only` trigger was dropped while its
`*_no_truncate` trigger survived **passes both tests**. The property the file
is named for is unchecked on the engine that matters.

*Fix:* read the definition, not just the name —
`SELECT tgname, pg_get_triggerdef(oid)` and assert `UPDATE` and `DELETE` both
appear in the row-level guard's definition. `tests/contract/test_postgres_catalog.py`
already does the adjacent work (`tgtype` statement-vs-row at line 134), so the
query is in the repository twice over; this is the one place it is needed and
missing.

**Second gap.** `test_the_claim_list_covers_every_table_the_contract_calls_
append_only` is:

```python
assert set(APPEND_ONLY) == {"audit_log", "gate_authorisations", "consents",
                            "age_verification_events", "notice_versions"}
```

— a five-element literal compared against the same five elements typed thirty
lines above it, in the same file. It cannot detect a table that DATA-MODEL §2
calls append-only and that nobody added; it detects only someone editing one
copy and not the other. Its docstring claims more than it does: *"Read from
`apps/core/p14.py`'s frozen-table knowledge where it overlaps"* — the test does
not import `p14` at all. That is D-026's shape inside the file written to
prevent it.

*Fix:* either delete the tautology and keep only the two `assert … not in
tables` tripwires below it (which **are** real — they fail when S4/S5 create
their tables), or import the overlapping set from `p14` as the docstring says.
Deleting is the lazier and the honest option; the tripwires carry the weight.

**This hazard applies to S4's and S5's field changes exactly as the note says.**
Worth adding to ENGINE-DIVERGENCE §12 in one line: *any* `AlterField`,
`AddConstraint` or `RemoveConstraint` on a table in `APPEND_ONLY` must carry a
trigger-restore `RunPython` in the same migration, as `0004` does.

### R7 · `/legal/grievance-officer` can never render, and A-25's composition is not implemented

**Files:** `web/views.py:61–89` (`_notice_kind`), `web/views.py:667–685`
(`legal`) · `apps/accounts/api.py:299–311` (`NOTICE_SLUGS`)

`_notice_kind("grievance-officer")` derives `"GRIEVANCE_OFFICER"`.
`notice_versions.kind`'s CHECK allows `GRIEVANCE_PROCEDURE`. So the route
resolves to a kind that can never exist and renders *"not published yet"*
permanently — and will keep doing so after the notice is published.

The docstring's escalation is **stale**: it says *"neither `ranking` nor
`grievance-officer` is in the CHECK constraint, so neither can ever be
stored"*, but DATA-MODEL A-25 (dated the same day) added both and backend
shipped them in `accounts/0003`. `/legal/ranking` works now. `/legal/grievance-officer`
does not, and for a different reason than the one recorded.

A-25 and API-CONTRACT §5.1 are also explicit about what this route must do:
*"the last composes the `GRIEVANCE_PROCEDURE` notice with the officer fields
read from `legal_entities` **at render time**, never copied into a notice."*
The view reads no `legal_entities` row and composes nothing.

**Concrete failure:** E-Com r.4(2) and IT Rules r.3(2)(a) require the grievance
officer's details to be *published*. The route exists, is linked from the footer
of every page, and cannot ever show them. The two L2/L3 slug maps also disagree
(`grievance` → `GRIEVANCE_PROCEDURE` at L2; `grievance-officer` →
`GRIEVANCE_OFFICER` at L3), so the same contract line is implemented two
different wrong ways.

**Smallest correct fix:** make `legal`'s one irregular slug explicit —
`grievance-officer` → `GRIEVANCE_PROCEDURE` — and pass the campus's
`legal_entities` officer fields into the template, rendering nothing where they
are absent (`INCORPORATION-AND-BLOCKERS.md` §4.1 is right that inventing them
is a misrepresentation; rendering the heading with no details is not). Note
that `_notice_kind`'s "rule not a list" is the *cause* here: deriving a kind the
enum does not contain is an input nothing validates, which is `CLAUDE.md` rule
18 — the derivation guarantees a *state* (the page renders) and does not detect
a *bad input* (a kind that can never exist). Validating the derived kind against
the model's `NOTICE_KINDS` closes the class, and is one import.

### R8 · The trust string never renders, and `signed_in_with_college_email` has zero tests

**Files:** `web/views.py:529–531` · `web/context.py:127–132` ·
`templates/account.html:32–37`

You asked whether the trust string renders only for `INSTITUTIONAL_EMAIL` and
fails closed otherwise. **It fails closed always, because it never renders at
all.** `getattr(user, "campus_verification_method", None)` names an attribute
that exists **nowhere in the codebase** — the only matches for
`campus_verification_method` are a CHECK constraint name in the migration and
this one call site. There is no model field, no property and no annotation, so
the value is permanently `None` and `college_email_signin` is permanently
`False`.

The fail-closed direction is the right one and the escalation (the
`EMAIL_DOMAIN` vs `INSTITUTIONAL_EMAIL` divergence across three documents) is
correct and well argued. But:

1. **Acceptance criterion 7h, SYSTEM §4.11a and COPY-DECK §3.2 condition 3 are
   unimplemented**, not merely gated. The slice's own hand-back says so; this
   review records it as a required item rather than a note because S2's seller
   block depends on the same read.
2. **`signed_in_with_college_email` has no test of either branch.** `grep -rn
   "signed_in_with_college_email\|college_email_signin\|trust.campus_mail"
   tests` returns nothing. So the "fails closed on `STAFF_MANUAL`, on `None`
   and on any unknown value" claim — which `context.py` presents as the layer
   that makes the spelling escalation safe to defer (rule 14) — is asserted and
   unchecked. `CLAUDE.md` rule 9.

**Smallest correct fix:** a four-line parametrised unit test over
`signed_in_with_college_email` covering `INSTITUTIONAL_EMAIL`, `EMAIL_DOMAIN`,
`STAFF_MANUAL`, `None` and `"ANYTHING_ELSE"`. That makes the fail-closed claim
real and costs nothing. The feature itself waits on cto's ruling and on an L1
read, correctly.

### R9 · Internal contract references reach user-facing `message` fields

**Files:** `apps/accounts/services.py:912–917`, `:530–534` ·
`apps/core/services.py:380–384`

API-CONTRACT §2.2 defines `message` as *"already localised"* and L3 renders it
directly. Several `ValidationFailed` messages are developer notes:

* `POST /account/nominee` with an extra key → *"A nomination holds a name and
  an email and nothing else; got ['phone']. A third party's other details would
  be personal data with **no COMPLIANCE.md §7 row**."* Reachable by any
  student.
* `POST /auth/magic-link` with a non-UUID key → *"An Idempotency-Key on an
  unauthenticated request must be a UUIDv4 (**API-CONTRACT §4.1**). Anonymous
  keys share one namespace…"*
* `review_age` with a date in the note → *"(**DATA-MODEL §2**: no DOB is
  persisted anywhere, in any state)"*. Staff-facing, but still rendered.

These are also untranslated — they bypass `GENERIC_MESSAGES`, which is the one
translated table — so they would ship English into a Tamil page the day the
flag opens, and they are outside B5's scanner even once it exists, because they
are Python literals and not `.po` entries.

**Fix:** keep the diagnostic in the raised exception's `context` (where a log
line can carry it) and give the `message` a student sentence from
`GENERIC_MESSAGES`. The split already exists; these three raises bypass it.

### R10 · `locale/FORBIDDEN_EXCEPTIONS.toml` ships two unratified shape exemptions — **escalation, not a review comment**

**File:** `locale/FORBIDDEN_EXCEPTIONS.toml` (new in this slice)

Per charter item 10a I am recording this and routing it to cto rather than
ruling on it. `[strings]` is empty, which is correct, and `locale/ta/REVIEWED.toml`
is empty with an unusually clear explanation of why no agent may add to it —
both exactly right.

But the file carries **two shape exemptions** (`[shapes.msgctxt]`,
`[shapes.template_comment]`), each with `ratified_by = "PENDING — cto/code-review"`
and the file's own statement that *"this file is the proposal, not the
ratification."* Both arguments are good — `trust.campus_mail` is cited by name
in COMPLIANCE §2.5a so rule 13 resort 1 genuinely does not apply, and a guard
that fires on its own rationale is rule 13's whole point — and both name the
other layer that still catches the thing, as rule 14 requires.

**What I will say, and the limit of it:** the reasoning satisfies rule 13 resort
2 and rule 14 on its face. I am not ratifying it, because the thing being
exempted is a control that **does not exist yet** (B5), so there is nothing to
measure the exemption against. Ratify it together with `test_forbidden_copy.py`,
where the shape rules can be read from this file and their effect observed. Also:
`ratified_by` names *"cto/code-review"* — a reviewer cannot ratify an exemption
to a guard in a diff the same reviewer is approving, which is charter hard rule
1's logic. **cto's and the founder's call.**

### R11 · A non-`ServiceError` never reaches the §2.2 error renderer

**File:** `apps/core/api.py:155–185` · `bookhop/urls.py` (no `handler500`)

`endpoint`'s `except` clauses catch `Replay` and `ServiceError` only. Any other
exception propagates to Django, and no `handler500` or `handler404` is declared
in the root URLconf. In production (`DEBUG = False`) an `/api/v1/*` 500 then
returns Django's **HTML** error page, not API-CONTRACT §2.2's JSON error shape.

This is reachable: `public_origin()` raises `RuntimeError` when
`BOOKHOP_PUBLIC_ORIGIN` is unset, inside `request_magic_link`, inside
`POST /api/v1/auth/magic-link`. `accept_seller_terms` raises
`NotImplementedError`. A JSON client gets an HTML body and no `code`.

The §2.2 *content* rule holds — Django with `DEBUG=False` echoes no exception
message and `RequestIdMiddleware` still sets `X-Request-Id`, so the "500 never
echoes an exception message, the `request_id` is the only thing the user gets"
half is satisfied by accident. The *shape* is not.

**Fix:** `except Exception as exc: log.exception(...); return error_response(
ServiceError())` as the last clause in `endpoint`. One line, and it is the
function TASKS §2 put in this slice precisely because it *"sits between backend
L2 and frontend L3"*.

---

# NOTE / SUGGESTION — take or leave

* **N1.** `export_account` performs two writes (a `data_subject_requests` row
  and an `audit_log` row) on a `GET`, with no rate limit. A student reloading
  `/account/export` ten times creates ten `ACCESS` rows. Suggest the same
  `consume_quota` the erase endpoint uses; the DSR row is right to exist (the
  s11 clock needs it), the unbounded growth is not.
* **N2.** `templates/base.html:48` links the language switcher to
  `?lang={{ code }}`. **Nothing reads a `lang` query parameter** — no view, no
  middleware, no `set_language` route. The switcher only renders when more than
  one locale is offered, so it is dead today; the day `i18n.ta_enabled` opens,
  the switcher will render and do nothing. The suite cannot see this because
  the flag is off.
* **N3.** `apps/core/jobs.py::_scrub` iterates `payload.values()` at the top
  level only. A future handler with a nested payload (`{"email": {"token": …}}`)
  would leak into `last_error`. Today's payloads are flat, so this is a note;
  `redacted()` has no such gap because it only keeps key names.
* **N4.** Three more strings describe mechanisms that are not built, in the
  present tense: `trust.exif` *"We remove the location and camera details from
  your photos"* (photo upload is S2), `help.scope` *"We can help you reach the
  other student, put a book back up, or look at a listing"* (messaging S5,
  listings S2), `run.what_it_is` *"BookHop matches the exact edition your
  syllabus asks for with a copy someone on your campus already owns"* (no
  catalogue, no matching). §1.2 permits describing a mechanism; describing one
  that does not exist is a statement of fact that is false. Less urgent than B6
  because none of them invites an action, but they are the same class and
  should go out together.
* **N5.** `apps/accounts/migrations/0002` names
  `tests/unit/test_append_only_s1.py` as asserting its message. That file does
  not exist; the work is in `test_consent.py` and
  `test_append_only_triggers_exist.py`. One-line docstring correction — but it
  is the fourth instance in this review of a document naming an artefact that
  is not there, which is why it is worth listing.
* **N6.** `require_actor` calls `consent_state(user)` once per purpose inside
  the loop — six queries where one would do. Irrelevant at pilot volume, and
  it becomes live the moment B3 is fixed, so fix it then: hoist the call.
* **N7.** `"The things students ask most"` (help page) is a factual claim about
  support data we do not have — J9 is BLOCKED and nothing stores a question.
  `"The questions this page answers"` costs nothing.
* **N8.** `record_audit` calls `time.sleep()` inside the caller's open
  transaction on each retry (up to 12 × ~0.1s). The backoff is right and was
  chosen from measurement; holding row locks while sleeping is a throughput
  ceiling worth naming in the existing `ponytail:` note.

---

# PRAISE — what to repeat

* **The append-only trigger loss (R6's subject) is the best finding in the
  project to date.** It was found on the engine nobody treats as
  authoritative, about a hazard invisible on the engine that is, and the
  response was a restore migration *plus* a general control *plus* an entry in
  ENGINE-DIVERGENCE — in that order of importance. Importing
  `APPEND_ONLY_TABLES` from `0002` rather than retyping it is rule 10 applied
  without being told.
* **`PUBLIC_ORIGIN` has no default and `public_origin()` raises.** Verified:
  `settings.PUBLIC_ORIGIN = env(..., "")`, the raise is unconditional, the
  conftest fixture that supplies it is autouse *and* the refusal is asserted
  explicitly in a test that clears it again. A `localhost` default would have
  passed every test and failed only for the student. This is the right instinct
  and it is the second time this slice chose "raise" over "plausible default".
* **The `Host`-header claim checks out.** `request.get_host()` is validated
  against `ALLOWED_HOSTS` by Django, and `ALLOWED_HOSTS` is a closed list in
  **both** environments — `["localhost", "127.0.0.1", "[::1]"]` in dev,
  `required=True` from the environment in prod, with no `"*"` anywhere. So a
  Host header cannot put an attacker's domain into a sign-in email. I checked
  this because it is the kind of claim that is usually true in prod and false
  in dev; here it is true in both.
* **The authentication surface is sound.** `secrets.token_urlsafe(32)` = 256
  bits; the token is stored as a bare `sha256` so a database read cannot sign
  anyone in; single use is a conditional `UPDATE … WHERE consumed_at IS NULL`
  checked on the **row count**, not a read-then-write; the 10-minute expiry is
  one constant imported by the handler and the template context; the 202 is
  byte-identical across unknown address, unrecognised domain and suspended
  account, with the rate limiter consumed **before** the campus lookup so its
  own timing is not an oracle; `cycle_key()` on login closes session fixation;
  `auth_consume` redirects immediately so the token leaves the address bar.
  Soft user-agent binding logged and not enforced is the right call and the
  reason given (webmail prefetch, mail-on-laptop) is the real one.
* **The frontend's reported weights are exact.** Measured here: **952 bytes**
  gzipped for the first-run document, **10,793 bytes** for a first visit
  (document + `tokens.css` + `app.css` + `sw-register.js`). Both numbers as
  claimed, to the byte.
* **CSP cleanliness verified independently, not taken on assurance.** The live
  header is `default-src 'self'; script-src 'self' 'nonce-…'; style-src 'self';
  img-src 'self' data:; connect-src 'self'; font-src 'self'; object-src 'none';
  base-uri 'none'; form-action 'self'; frame-ancestors 'none'` — no
  `'unsafe-inline'`, no `'unsafe-eval'`, on any directive. And the templates
  earn it: `grep` over `templates/**` and `static/js/**` finds **zero** inline
  `<script>`, zero `style=` attributes, zero `onclick`/`onsubmit`, zero `|safe`
  and zero `mark_safe` anywhere in the repository. One external script. The
  single `{% autoescape off %}` is in a `text/plain` email body, where it is
  correct. No webfont is requested on any page. Zero application JavaScript,
  and every route works as a plain form POST.
* **`_has_visible_character` asks Unicode a question instead of consulting a
  list** (rule 15), and the docstring explains why a whitespace list could
  never catch a zero-width space. This is the rule being applied, not cited.
* **`DSR_DEADLINE` was renamed rather than exempted.** `DSR_DUE_AFTER` tripped
  the money-token source grep; the author renamed their own constant instead of
  widening `MONEY_TOKEN_SHAPE_EXEMPTIONS` database-wide. Rule 13 resort 1,
  chosen unprompted, and the reasoning left in the comment where the next person
  will read it.
* **`ERASURE_STEPS` as a registry rather than prose.** Each entry carries the
  slice that lands it, and the test asserts every entry is either executed or
  explicitly pending. This is the right answer to "a deferral recorded only in
  a docstring is how an ownerless control becomes an unwritten one" — and it is
  the mechanism that makes R3 and R4 findable at all.
* **`PURGE_SKIP_LIST` names the `consents` / `age_verification_events`
  retention-vs-trigger conflict as a conflict and routes it to cto instead of
  resolving it locally.** Correct escalation; see below.
* **No DOB reaches storage, and the controls are layered.** The date is a
  parameter that dies with the request; the audit payload does not contain it;
  `idempotency_keys` stores a hash of the body and never the body; `review_age`
  refuses a note matching three date shapes **and** declares the ceiling of
  that refusal in a `ponytail:` note pointing at the schema layer beneath it
  (rule 18, correctly applied). The under-18 `DELETE FROM users` is the one
  place the module deletes, and the three-bullet argument for why
  tombstone-plus-purge would be *worse* there is the best piece of reasoning in
  `services.py`.
* **`conftest._isolate_rate_limit_counters` removed a vacuous swallow and said
  so.** The old version ran a doomed query inside `except RuntimeError: pass`
  for every test without a `db` fixture. Replacing it with a fixture-name check
  is exactly rule 12. (Its *measurement* is wrong — B1 — but the fix it shipped
  is right.)
* **No phone number and no WhatsApp number appears anywhere in the product.** I
  checked all 122 strings. METRICS' D-009 note makes this load-bearing: a
  published phone line voids the support-minutes mitigation. The one copy
  problem on that page (B6) is a promise, not a channel.
* **The §1.2-conformant trust strings are genuinely good copy.** *"BookHop
  hasn't checked this book."* · *"Look at the book before you hand over any
  money."* · *"If it isn't the book described, don't pay. Tell us and we'll
  take the listing down."* · *"There are no ratings on BookHop."* · *"You and
  the other student settle the money between yourselves, in person."* Every one
  of them names a mechanism or gives an instruction, and the set reads as more
  trustworthy than the category's boasting. Repeat this.
* **`web/context.py` deleted its own three hand-copied rules and said what the
  divergence had already cost** — a local consent list that marked four
  purposes required where `REQUIRED_CONSENT_PURPOSES` is `("account",)`, which
  would have told a student that declining `chat` blocked messaging. Rule 10
  found in one's own code and reported, which is the hardest version.

---

## Checklist disposition

| # | Item | Verdict |
|---|---|---|
| 1 | Contract fidelity | §2.5 unwired (**B3**); §2.2 shape incomplete (**R11**); §5.1 grievance route (**R7**). Error codes, idempotency, `expected_version` → `version` handling otherwise correct |
| 2 | **The hard constraints** | **Clean. No founder escalation required.** No settled price, PAN, Aadhaar, DOB, UPI handle, address, balance or credit. New numeric columns: `users.version`, `jobs.attempts`/`max_attempts`, `rate_limit_counters.hit_count`, `idempotency_keys.response_status`, `audit_log.actor_id`, `*.scope_id` — none carries a W1b token and each bare one is non-monetary by name. `transfers`, `transfer_events`, `messages`, `transfer_followups` do not exist and no CHECK on them was widened |
| 3 | The gate | No discovery read path in S1. `assert_discovery_open` unchanged. `users.is_seed NOT NULL DEFAULT false` present and now verified on PostgreSQL. ADR-002 §4.1(b)'s floor is weaker than its prose — see **R2** |
| 4 | Correctness | One transaction per mutation with the audit row inside it, verified call by call. `transaction.on_commit` on the only notification. Both job handlers idempotent. `_activate_if_ready` is one guarded assignment in one place |
| 5 | Scoping | No new tenant read path. `scoped()` unchanged and still tested |
| 6 | Security (ASVS L2) | **B3** (V4 authorisation), **B4**, **R11**. No `|safe`, no `mark_safe`, no raw SQL interpolation outside migration DDL, no secret in the repo, no exception message in a response |
| 7 | Retention and deletion | **R4** (`django_session`), **R5** (`jobs`). Everything else has a §7 row, a rule and a purge path, and the expiry job shipped in the slice |
| 8 | Instrumentation (D-009) | **Satisfied.** "Verified students" is computable from `users.adult_verified` + `campus_verified` + `is_seed`, `campus_verifications` and `age_verification_events`, all written in this slice. No phone/WhatsApp channel |
| 9 | Migrations | Reversible, expand-then-contract, no destructive change beside the code that stops needing the column. `accounts/0004` is a worked example of the SQLite rebuild hazard |
| 10 | Accessibility and copy | **B6**, **N4**, **N7**, **R9**. Structure is strong: one `<h1>`, real landmarks, skip link, `aria-describedby` wired once in `_Form`, no `maximum-scale`, no pre-ticked consent box (guaranteed by the form class, not the template), native `<input type="date">`, no CAPTCHA (SC 3.3.8 by construction), consistent footer on 404. **WCAG 2.2 AA is NOT verified** — the keyboard walkthrough and p75 LCP skip with a stated reason |
| 10a | Locale manifests | **R10 — escalated to cto.** `REVIEWED.toml` empty and correct. `i18n.ta_enabled` false, with a non-vacuous test keeping it false. Two unratified shape exemptions |
| 11 | Simplicity | Good. No new dependency, no abstraction with one implementation, no stubbed S2 route. `ponytail:` notes name real ceilings with real upgrade paths. The one deletion I recommend is R6's tautology; the three untracked probe files in B2 are the other |
| 12 | Tests | **B1, B2, B5, R1, R2, R6, R8** and the vacuous guard in **B4**. 972 collected is a lot of real coverage, and seven of the best tests in the repository are in this slice — but four separate guards here assert a property they do not check |

---

## On the nine backend escalations

They are cto's, not mine, and I have not seen the hand-back list. Two
observations about the boundary:

1. **The ownership migration is correctly an escalation.** `core/0008` is a
   partial fix that measures and states its own ceiling, and the remaining
   limb needs a superuser this box does not have. Carrying it as a tracked
   CRITICAL is the right call. **But R1 must be fixed in this slice**: the
   mechanism chosen to track it does not work, and an escalation whose tripwire
   is inoperative becomes a forgotten escalation. That is a review comment, not
   an escalation — the test is ours.
2. **Two things that may be on that list are defects, not escalations, and I am
   requiring them here:** the §2.5 wiring (**B3** — `require_actor` existing
   and uncalled is not a contract gap, it is an unfinished call site), and the
   missing `test_forbidden_copy.py` (**B5** — TASKS §2 S1 assigns it by name to
   this slice). Neither needs a ruling to proceed.
3. **R10 is an escalation and I am not ratifying it**, for the reason given
   there: the control the exemption applies to does not exist yet.
4. `PURGE_SKIP_LIST`'s `consents` / `age_verification_events` conflict
   (append-only by trigger vs. a stated retention of "account life + 1 year")
   is a genuine contract contradiction and is correctly routed to cto. It is
   not a code defect and I am not requiring anything on it.

---

## Re-review

Send B1–B6 back together. B1 and B2 first and in one commit, because every
other verification in this review — including mine — is conditional on the
suite's verdict being a function of the tree. I will re-run both engines five
times and will not approve on a single green run.

---

## Postscript — the tree moved during this review (2026-10-22)

Everything above was measured against commit `a8bde62`. While I was reviewing,
test-qa began landing S1 verification into the same working tree. At the time I
filed this, `git status` showed `QA-S1.md` plus six new test files and a
modified `tests/conftest.py`, none of it committed. Two consequences, and both
are good news rather than a conflict:

* **B1's fix is already in flight and is not in the commit.** The uncommitted
  `tests/conftest.py` adds `connection.close()` to both session-scoped fixtures
  and deletes the false `VERIFIED HERE` paragraph — the same one-line fix the
  finding asks for, reached independently. B1 therefore stands against the
  commit and should be closed by committing QA's change, not by writing a
  second one.
* **Four of my findings appear to have been reached independently**, judging by
  the new filenames: `tests/contract/test_standing_preconditions.py` (B3),
  `tests/contract/test_open_criticals_are_honest.py` (R1),
  `tests/contract/test_append_only_by_behaviour.py` (R6) and
  `tests/unit/test_zz_blocker_probe.py` (B1). I have not read them and have not
  adjusted any finding to match them. Two agents arriving at the same four
  defects from different directions is corroboration; whoever integrates should
  reconcile the tests, not the conclusions.

I have **not** re-run anything against the moved tree, and this review's
verdict is about `a8bde62`. The counts in *Reproduction* were taken before
these files appeared; the untracked probe files named in B2 were present
throughout and are counted there.
