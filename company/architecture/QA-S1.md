# QA-S1.md — QA's S1 pass: three re-pointings, and a harness finding

**Owner:** test-qa · **Version:** v1.0 · **Date:** 2026-10-22
**Engine:** PostgreSQL 16.15 (`.env`), cross-checked on SQLite 3.45.1
**Scope:** the three tests S1 made wrong, the a11y harness against S1's pages,
and one finding about the test harness itself.
**Reads with:** `QA-S0.md` v5.0 (the S0 verdict, unchanged) · `CLAUDE.md`
rules 9–18 · `THREAT-MODEL.md` §6.1(c) · `TASKS.md` §1.

---

## 1. Verdict on the three re-pointings

**All three re-pointings are accepted, and two of them changed what the test
asserts rather than only which routes it visits.** Frontend was right on every
point it argued, including the one QA would have defended. The reasoning is kept
in the tests, not just the outcome.

### 1.1 The `[ta]` parameter — **frontend is right, and QA's test was asking for the violation it checks for**

QA's test demanded `<html lang="ta">` for an `Accept-Language: ta` request. With
`feature_flags['i18n.ta_enabled']` false, no reviewed Tamil is served, so the
strings on those pages are English — and SC 3.1.1 is about *the default human
language of the page*. A Tamil-tagged English page is the real 3.1.1 failure,
and it is the one that hurts: a screen reader switches to a Tamil voice and
reads English as noise. **Passing QA's test would have made the product worse.**
That is the sharper half of frontend's argument and it is correct.

QA also agrees with the half frontend did not have to argue. Serving English
beats refusing: `Accept-Language` is a preference, not a demand (RFC 9110); a
large part of the target population has an Android set to Tamil; and a `406`
would lock those students out of signing in, reading the privacy notice and
**reaching the grievance officer** — an IT Rules r.3(2)(a) route, and a path
`THREAT-MODEL.md` §5.7 says may never require an account. Refusing a locale we
were never going to serve, in order to avoid mislabelling it, is the worse
failure by a wide margin.

**Adopted, with one addition QA thinks the proposal needed.** The parameter is
derived from `web.context.offered_locales()`, so it activates with no edit when
the flag flips, and the gated locale **skips naming the flag and the slice**.
But QA did not simply delete the assertion, because removing a wrong check and
leaving nothing is how `THREAT-MODEL.md` §6.1(c)'s claim stops being checked at
all (`CLAUDE.md` rule 9). Two tests now run **today**:

* `test_an_unserved_locale_is_served_in_a_language_the_page_is_actually_in` —
  over `ta`, `ta-IN`, `ta;q=0.9, en;q=0.1`, `zz` and an empty header, on four
  pages. Four properties each: the page is **served, not refused**; `lang` names
  the language the page is actually in; **`Content-Language` agrees with
  `lang`** (two statements of one fact must not disagree, or a client that
  trusts the header and a screen reader that trusts the attribute do different
  things); and the page still passes every structural rule in the language it
  was served in.
* `test_no_page_claims_a_locale_it_does_not_serve` — the same thing as an
  invariant rather than per header, so the regression the `[ta]` parameter was
  reaching for is caught from **any** direction, including a template
  hard-coding `lang`.

### 1.2 `NOT_PAGES` — **a list became an invariant, and the list is gone rather than shortened**

`/sw.js`, `/robots.txt` and `/manifest.webmanifest` were being parsed as HTML
and failing four rules each. Frontend's read is right and it is `CLAUDE.md`
rules 11 and 15: the harness now **skips on the response `Content-Type` not
being `text/html`**, which asks the property instead of enumerating the cases.

Worth noting what the invariant swallowed: it subsumed the **whole** of the old
list, including the two operational endpoints it was originally written for.
`/healthz` is `text/plain` and `/readyz` is JSON, so both are now skipped for
the same reason as the service worker — by what they are, not by being named.

**And the guard on the invariant**, because a content-type skip is silent by
construction and a page route that started returning JSON would vanish from the
sweep while the sweep stayed green (rule 12, in QA's own harness):
`test_the_content_type_invariant_skips_only_non_html_routes` asserts the split
is exactly the five non-HTML routes the contracts declare, and
`test_the_sweep_reports_what_it_did_not_check` asserts every route is accounted
for as checked-anonymously, checked-signed-in, or non-HTML.

### 1.3 The route-count test — **re-pointed to two invariants, neither of which is a list**

The coordinator's suspicion is right: QA wanted "no route reaches a listing
while the gate is closed", not "the surface is small". A count was a stand-in
for *"nobody can add a route without someone looking at it"*, and as a flat list
it is rule 11's shape — it needs an entry per slice, and the entry gets added
without the looking. Replaced by three things:

1. **`test_the_root_urlconf_registers_no_student_facing_route_itself`** — the
   root URLconf is an *ownership* boundary (`TASKS.md` §1), so the invariant is
   that it declares operational endpoints and includes and **no third thing**. A
   route registered there belongs to nobody's slice and gets nobody's gate test.
   This does not grow with pages.
2. **`test_no_route_serves_campus_scoped_data_while_the_gate_is_closed`** — the
   property the count stood in for, in the form available today. `listings` is
   S2, so that assertion has no subject and saying it now would be a vacuous
   guard; **campus-scoped tenancy data exists**, and the same question can be
   asked of it. Sweeps **every** route — operational, L2 and L3 — with a
   gate-closed campus seeded, and fails if any response carries its name or
   slug. It extends to listings by adding one needle in S2, not eighteen routes.
3. **`test_the_student_facing_tree_cannot_reach_a_listing_because_it_cannot_reach_the_orm`**
   — frontend's claim that none of its eighteen routes is a discovery read path,
   asserted structurally. `TASKS.md` §1 says `web/**` *"calls L1 services, never
   the ORM, never L2 over HTTP"*; measured, no file in `web/**` uses a queryset,
   imports a model, or imports `requests`/`urllib`. **That is the whole
   argument**: a view that cannot query a model cannot return a listing except
   through a service function, and every discovery service function begins with
   `assert_discovery_open`. It is also the check that stays true as pages are
   added — the alternative is re-asserting the gate on every new route, which is
   the list again.

QA agrees the gate **journey** lands in S2/S3, and the skip that says so now
names the table rather than the engine.

---

## 2. What the harness found about S1's pages

**Frontend's eleven HTML pages pass all nine structural rules, in English,
anonymously and signed in, on the first run.** The only a11y failures were
QA's own two wrong assumptions, above.

**And the harness was reaching four pages out of eleven.** Seven redirect to
`/auth/start` without a session, and `status_code != 200` meant *skip* — rule
12's shape again, in QA's own harness, reported as coverage for a whole slice.
There is a `users` table now, so the harness signs in:
`test_every_signed_in_page_passes_the_structural_a11y_rules` reaches
`/account`, `/account/age`, `/account/privacy`, `/account/delete` and the rest.
It asserts the **property** rather than a count — every route that redirects
anonymously and answers 200 with a session must be in the sweep — plus
specifically that `/account/privacy` is reached, because the consent-withdrawal
page is the one S1 page a DPDP complaint is most likely to be about.

Still not a WCAG 2.2 AA pass, and the keyboard-only walkthrough in both locales
is still the charter's requirement and still unautomated. 2.4.11, 2.5.7, 2.5.8
and **3.3.8 accessible authentication** — which lands directly on the
magic-link flow S1 just shipped — remain unverified by anything.

---

## 3. The isolation finding: **Red Team's finding is still open, and here is the measured cause**

The coordinator asked for the number of tests that change verdict once isolation
is real. **It is not real yet**, and the measurement is better than a count.

### 3.1 The definitive check, and it fails

`tests/contract/test_s0_surface.py::test_a_test_without_the_django_db_marker_cannot_reach_the_database`
takes **no `django_db` marker and no `db` fixture** and executes `SELECT 1`. If
the blocker worked, that must raise. **It succeeds.** Counting fixtures cannot
answer whether the blocker works; only trying can, and this is QA's one failing
test.

### 3.2 The cause, measured

* The alias is **already connected** when a non-`django_db` test starts
  (`connection.connection is not None`, measured), and the blocker cannot close
  a connection it did not open — which is exactly the mechanism Red Team named.
* Two **session-scoped autouse** fixtures in `tests/conftest.py` open that
  connection at session setup and never close it: `allow_test_flush` and
  `restore_gate_privileges_for_the_harness`.

### 3.3 The fix, measured rather than proposed

`connection.close()` at the end of each of those fixtures restores the blocker.
Verified directly: with the connection closed, the same query raises
`RuntimeError: Database access not allowed, use the "django_db" mark`. For
`allow_test_flush` the retroactive `_declare_flush_escape(None, connection)`
call then becomes **redundant as well**, because `connection_created` fires for
the connection the next real test opens — which is the whole point of having
moved it onto that signal.

### 3.4 **QA owns part of this**

`allow_test_flush` exists because of QA-S0 **F9**, where QA told the harness it
needed a session-scoped fixture and did not say to close the connection
afterwards. The recommendation was right and incomplete, and the incompleteness
is what defeated the blocker for the rest of the session. That is the fourth
time in six passes that a defect was found in something QA wrote, and all four
were caught by someone reading QA's output against theirs.

### 3.5 What it cost, measured

On an unchanged tree, five consecutive full-suite runs gave **0, 1, 4, 13 and
14 failures** with up to **15 teardown errors**, and the failing set moved
between unrelated tests. The failures concentrated on **audit-chain** tests —
`test_record_audit_writes_a_row_and_chains_it`,
`test_verify_audit_chain_passes_on_a_clean_chain`,
`test_a_tampered_chain_is_detected`, `test_concurrent_appenders_cannot_fork_the_chain`
and nine more — and **not** on whichever test leaked, because the chain is one
linked list across the whole table, so a single committed row breaks
`verify_audit_chain` in a *later* test. QA's own canary
(`test_the_test_database_carries_no_committed_rows_between_tests`) fired in two
of those runs, which is the direct evidence of rows crossing a test boundary.

**So the answer to "how many tests change verdict" is, today, a range rather
than a number: up to 14 tests' verdicts were not a function of the code.** A
green run was one sample of a distribution.

### 3.6 One thing QA must not overstate

A second cause was present in those runs and it is **not** the isolation defect:
the test database was **stale**, missing `rate_limit_counters` from migration
`core/0007`, so `transactional_db` teardown flushes errored and left rows
behind. With `--create-db` the suite settles to green. **Both causes produce the
same signature**, and QA separates them rather than attributing the whole spread
to Red Team's finding:

| Cause | Evidence | Fix |
|---|---|---|
| The blocker does not contain the alias | the no-marker query succeeds; the alias is pre-connected | `connection.close()` in the two session fixtures — **still open** |
| A stale test database | `relation "rate_limit_counters" does not exist` in teardown | `--create-db` after any migration lands. **An operational note worth writing down**: every migration silently invalidates the reused test DB, and the failures it produces land nowhere near the cause |

**Superseded — see the F19 withdrawal in §5.** The blocker works; QA measured it from a module that could not ask the question. The verdict delta from the whole isolation episode is **zero**, and the variance was the stale test database and nothing else. The
instrument is in place and will answer it in one command: when
`test_a_test_without_the_django_db_marker_cannot_reach_the_database` passes, the
suite's spread should collapse to zero, and the canary is what proves it.

Current state, three consecutive runs on a current test DB:
`1 failed, 913 / 915 / 917 passed, 48 skipped, 2 xfailed` — the one failure
being the finding above. QA's trees alone: **371 passed, 21 skipped, 1 failed.**

---

## 4. A file-ownership finding

**Four files appeared in `tests/e2e/**` today that QA did not write**, at
11:52–11:54:

```
tests/e2e/test_erasure_sessions.py    (since removed by its author)
tests/e2e/_weird_serializer.py
tests/e2e/test_probe2.py   test_probe3.py   test_probe4.py
tests/e2e/test_probe5.py   test_probe6.py   test_probe7.py
```

**And they are still arriving.** Between QA starting this report and finishing
it, `test_probe4` through `test_probe7` appeared. So this is not one agent
borrowing a directory once — it is an ongoing write into a tree `TASKS.md` §1
assigns to someone else, while that someone else is measuring in it. Every
number in §3 had to be taken with an `--ignore-glob` for it.

`tests/e2e/**` is test-qa's tree (`TASKS.md` §1) and `CLAUDE.md` rule 6 says
never two agents in the same files. Two of them are named `probe`, which reads
like scratch work rather than a deliverable, and `test_erasure_sessions.py`
**fails on an ImportError** — so it currently presents as a QA failure in QA's
tree, which is the specific thing the ownership rule exists to prevent.

**QA has not deleted them**, because deleting another agent's work silently is
worse than reporting it, and because the erasure/session subject is a real one
that may deserve a home. The numbers in §3 are measured with those three test
files excluded, and that exclusion is stated in the command so nobody reads
around it.

**This needs a cto ruling, not a QA edit:** whichever agent wrote them has no
tree in `TASKS.md` §1's ownership table, which is the actual gap. Red Team
reviewing by *running probes* is the right instinct and it needs somewhere to
put them — `tests/redteam/**` would cost one row in the table.

---

## 4a. The precondition stacks — the handover backend asked for

Backend's framing was the right one: *"it chose those lists by reasoning about
the contract and wrote its tests from the same reasoning. A list one entry too
short grants a write to an actor who should not have it, and every test it
wrote would still pass."* So QA did not enumerate the code's stacks. The matrix
in `tests/contract/test_standing_preconditions_matrix.py` is derived from two
contract facts and nothing else: **§2.5 as amended** (the two stacks, their
ordered checks, and the endpoint membership table), and **§5.1's `needs` order**
— `age` then `consent` then `campus` — which is the contract telling us which
preconditions a student can legitimately not yet satisfy, and when.

**45 cells. 41 pass. 4 fail, and they are one finding.**

### F23 · `POST /account/nominee` is Stack S in the contract and Stack M in the code

§2.5's membership table lists **`POST /account/nominee` (s14)** in Stack S,
beside export (s11) and erasure (s12(3)), under the heading that ends *"And
nothing else. Not `ACTIVE`, not `adult_verified`, not `campus_verified`, not
consent… A right that a precondition can switch off is not a right."*
`apps/accounts/api.py` runs `_may_write(user)` on it — the full Stack M.

Measured: a **suspended**, an **under-verified**, a **campus-unverified** and an
**unconsented** student are each refused their s14 nomination, with the four
different §2.5 Stack M codes. Four cells, one cause.

**This is exactly the shape backend asked QA to look for, one level up from
where it was looking.** The lists *within* each stack are right; the
**assignment of this endpoint to a stack** is not, and a test that enumerates
the code's stacks agrees with the code by construction. It took deriving the
membership from the contract table to see it.

Severity: low in practice today — nomination is one field in privacy settings
and not a path a suspended student is likely to be on — and the correction is
one word, `_may_write(user)` to `_stack_s(user)`. It matters because the
amendment that created Stack S exists precisely to stop a moderation decision
switching off a statutory right, and s14 is in the Act beside s11 and s12.

### What passed, and is worth recording because each was a plausible place to fail

* **`PATCH /account` is split by field, not by endpoint** — `locale` under
  Stack S, `display_name` under Stack M — and the both-fields-at-once body
  correctly takes the stricter stack, so a suspended student cannot rename
  themselves by sending a locale alongside. That is the placement most likely to
  have been implemented as "whichever stack the endpoint is in", and it was not.
* **Export, erasure and locale serve a suspended actor**, which is the ruling
  working.
* **A tombstoned actor gets `401 NOT_AUTHENTICATED`, not `403`**, on every
  write — §2.5 Stack S calls out that exact distinction (*"not 403 — the
  account is gone"*) and the code gets it right.
* **A fresh student can walk age then consent without being refused**, which is
  the "one entry too long" direction and the one no enumeration of lists can
  catch, because the lists would agree with each other.

### Two places QA was wrong first, recorded because they are the same trap

QA's first draft reported four extra findings and all four were QA's error:

* it treated `PUT /account/consents/{key}` as a single Stack S endpoint. The
  code splits it by **direction** — withdrawing is S, granting is M minus the
  consent limb the endpoint establishes — and that split is in §2.5's prose
  (*"withdrawal above all"*) rather than in its table. QA agrees with the code;
  a student granting a marketplace consent is taking on a capability, not
  exercising a right.
* it reused one test client across actors. `client.session` mints a new key on
  each save while the cookie still points at the first, so every actor after
  the first was anonymous and every endpoint answered `401`. **Four cells of
  nonsense that looked exactly like a finding.** The fixture now returns a
  fresh client per actor, so the actor is the only variable.

Both are in the file's docstrings. The second is the more useful warning: a
precondition matrix with a shared-session fixture produces confident,
uniform, entirely wrong results.

---

## 4b. Three ruled placements, asserted four slices before they can be built

Backend named the right next thing: three authorization placements are **ruled
in §2.5 and cannot be implemented until S5 and S6**, and the reasoning is in a
comment. *"By S5 the comment will be four slices old and the person
implementing it will be reading the table, not the reasoning. That is the same
gap that produced the nominee error, one slice later and with a safety report
on the other end of it."*

`tests/contract/test_future_stack_placements.py` writes each ruling as an
assertion that **skips while its app does not exist and runs the day it is
mounted** — the shape the erasure assertions already use. Seven rows, each
carrying the contract's own words for *why*, because the why is what decides
the next ambiguous case and it is the part that gets lost:

| Ruling | Stack | Slice |
|---|---|---|
| `POST /reports`, `SAFETY_INCIDENT` and `NCII_OR_IMPERSONATION` | **S** | S6 |
| `POST /reports`, any other category | **M** | S6 |
| `POST /support/tickets/{id}/replies` — the appeal channel | **S** | S5 |
| `POST /support/tickets` — opening a fresh queue item | **M** | S5 |
| `POST /grievances` | **S** | S6 |
| `POST /account/correction` (s12(1)–(2)) | **S** | unassigned — **F24** |

Both sides of each split are rows, asserted by
`test_both_sides_of_each_split_endpoint_are_covered`, because a split endpoint
checked on one side only is the nominee error again — and §2.5 splits
`POST /reports` by **category**, which is the same field-dependent shape that
already went wrong once on `PATCH /account`.

**The failure mode of a forward-dated skip, and how it is closed.** A skip like
this can skip *forever*: if the endpoint ships at a path the test did not
predict, nothing runs, the endpoint ships in whichever stack somebody chose,
and the guard was theatre with a four-slice fuse.
`test_every_ruled_endpoint_is_reachable_once_its_app_exists` inverts it — once
the owning app is **installed**, a ruled path that does not resolve is a
**failure**. The skip is only legitimate while the app itself is absent.

That guard immediately earned itself twice:

* it caught **a bug in QA's own helper**: `resolve()` matches everything,
  because `web/urls.py` ends in a catch-all `^.*$` for the 404 page. The naive
  check returned True for every path, so every assertion in the file would have
  passed vacuously the moment its app was installed. The check now requires the
  match to come from an `apps.*` urlconf.
* and then it found **F24**.

### F24 · `POST /account/correction` is named twice in §2.5 and does not exist

§2.5 lists it in the Stack S row with its citation, `(s12(1)–(2))`. It then
uses it a second time, as **the justification for putting `display_name` in
Stack M**: *"The right is satisfied by `POST /account/correction`, which is in
S, staff-reviewed and logged."*

Measured: no such route in `apps/accounts/urls.py`, no handler in `api.py`, and
no slice in `TASKS.md` assigns it.

So today a suspended student **cannot change their display name** — Stack M
refuses, correctly and deliberately — and **cannot use the correction route
either**, because it is not built. The statutory right the contract points at
to make that restriction defensible has no path at all. This is `CLAUDE.md`
rule 9's shape exactly: a document naming a control as the reason another
control is acceptable, with nothing asserting the first one exists.

Not blocking S1 — the restriction it justifies is itself correct, and the gap
is a missing right rather than a wrong grant. But **§2.5's `display_name`
reasoning should not be quoted as satisfied until the endpoint exists**, and
the endpoint needs a slice. The two failing tests are the standing reminder.

### Also forward-dated: the two §2.5 preconditions S1 cannot exercise

Preconditions **6** (scope → `404`) and **7** (the discovery gate → `403
GATE_CLOSED`) have no subject in S1, because every S1 endpoint is about the
caller's own account. They are the two most likely to be forgotten by the first
endpoint that needs them and the two with the largest consequences — one leaks
the catalogue, the other is the gate. Recorded as skips naming the precondition
verbatim, and the placeholder **fails rather than skips** once `apps.listings`
exists, with a test asserting that the `pytest.fail` branch is still there so
nobody converts it into a permanent skip.

---

### 4b.1 Converted to strict xfail, and the guard kept its teeth

Code review is right that a permanently red suite is the wrong mechanism for a
correct finding: **every later run carries a known failure and the only way to
tell a new one is to read the names**, which is how a real failure gets waved
through — and this project has already paid for failures landing on tests that
did not cause them (QA-S1 F20). `xfail(strict=True)` has the semantics the
finding wants: quiet while the gap is open, **red the day it closes**.

Both reds are converted, reason text verbatim. One design point QA added while
doing it: the inversion guard **excludes rows with an open finding** rather
than being xfailed itself. If the known gap sat inside it, the whole guard
would be an expected failure and a *second* row going unreachable later would
be absorbed into it — a known failure buying silence for the next one, which is
the exact thing the conversion was meant to prevent. One known gap, one xfail;
the guard still fails on anything new.

**The Stack S assertion is tightened** as review asked. The claim is about the
gate, so any response proving the actor reached the handler answers it —
including a `400` for a body QA could not predict four slices early. But four
families prove nothing: `401`/`403` is the refusal itself; **`404`/`405` mean
the request never reached the gate**, so the cell is unmeasured rather than
passing; **5xx would mask a crash inside the gate as a pass**; and **`429`
leaves the gate's answer unobservable — and on a safety row it contradicts the
very rule that row cites**, THREAT-MODEL §5.7, that no safety path is rate
limited to zero. Each is a separate assertion with its own message, so a cell
says which of the four it hit.

### 4b.2 Two caveats for anyone reusing the pattern — one encoded, one retired

* **It cannot serve an L3 path.** `_route_exists` defines existence as
  "handled by an `apps.*` module", which is true of L2 and false of `web/**` by
  design — so an L3 row would skip forever and assert nothing, reopening the
  failure mode the inversion guard closes. Now asserted: every ruled path must
  start with `/api/v1/`. Checking at L2 is enough because both layers call the
  same L1 services, but that is a reason one layer suffices, not a licence to
  list an L3 path.
* **Review's second caveat was already out of date, and QA measured it rather
  than recording it.** The warning was that `@endpoint` returns a closure, so
  every handler reports `apps.core.api` and tightening the module check to the
  owning app would break every row. Measured now: `/api/v1/account/export`
  reports **`apps.accounts.api`**. The `functools.wraps` that fixed the
  `inspect.getsource` defect also copies `__module__` — **one change retired
  two caveats**. The check is still not tightened, for a different reason:
  `apps.*` is exactly the question being asked (did this reach a real L2
  handler, or fall into `web/urls.py`'s catch-all `^.*$`?), and tightening adds
  a second thing to keep in step per row for no extra discrimination. The test
  now records which of the two facts is current, and fails if `wraps` is ever
  removed — which would also mean `inspect.getsource` is reading the decorator
  again.

**QA's trees: 492 passed, 38 skipped, 1 xfailed, 0 failed.** Full suite, two
consecutive runs: `1158 passed, 65 skipped, 3 xfailed`.

---

### 4b.3 F21 closed, F20 instrumented, and one thing the recount surfaced

**F21 is closed, verified rather than relayed.** `tests/e2e/` holds ten files
and no probes; the transient files are gone and review's own probes were never
in that tree. The `--ignore-glob` is dropped and the numbers in this report
need no caveat: **PostgreSQL `1174 passed, 65 skipped, 3 xfailed`, zero
failures.**

**One correction to the recount, and it is not about probes.** Five of those
ten files are not QA's: `test_deletion.py`, `test_first_run_journey.py`,
`test_no_dob_independently.py`, `test_erasure_sessions.py` and
`_weird_serializer.py`. Three of them are, by name, the deliverables
`TASKS.md` §3 and `DATA-MODEL.md` §10.3 assign to test-qa — and §10.3 assigns
`tests/e2e/test_deletion.py` to test-qa **"and written independently"**, which
is the one property the file now cannot have, because the implementer wrote it.

QA read it rather than objecting to it, and **the content is sound**: it
asserts (b) the pseudonym survives and (c) the record cannot be relinked, adds
the retention floor and the point-of-no-return disclosure, and defers (a), (d),
(e) and (g) — which need `transfers`, `reports` and `threads` — with a test
asserting the deferred ones are *skipped and not silently absent*. That is QA's
own pattern, used correctly. **No rework is needed and none is proposed.** What
is lost is independence, not coverage, and the ledger should say so rather than
record a QA deliverable as met: the agent that wrote the deletion code wrote
the test that says deletion works.

**F20 is now instrumented** — `tests/contract/test_test_database_is_current.py`.
A stale reused database does not fail where it is stale: teardown flushes a
table it does not have, leaves rows committed, and the failures surface on
whichever test next reads global state, which in this schema is the audit chain
because it is one linked list across the whole table. Three checks now make the
cause name itself — no unapplied migration, every managed model has its table,
and every table `sql_flush` will enumerate exists — each failing with the
`--create-db` advice and the F20 reference, so **one named failure replaces a
scatter of unrelated ones.** The underlying cause is unchanged and belongs to
whoever documents the test command; what QA can own is that it stops being a
mystery, and that is done.

---

### 4b.4 The §10.3 independence gap — QA's answer, with evidence

The ruling is **carry to S4**, and QA agrees with the timing. But QA will not
agree on the strength of the evidence it had, because *"I read it and the
content is sound"* is a reading, and the risk independence addresses is not
sloppiness — it is a **shared blind spot**. A test written from the
implementation inherits the implementation's misconceptions, and both are then
wrong together in a way no amount of reading detects, because reading tells you
a test is internally coherent, not that it is right.

So QA converted the reading into a measurement, without touching the file:
`tests/contract/test_erasure_properties_independently.py` re-derives from
§10.1's table the properties checkable today, choosing the two where
implementer and test are likeliest to share an assumption.

* **§10.1 step 7's "untouched" list.** The direction a deletion feature gets
  wrong, because every instinct in "delete my account" pulls towards deleting
  more — and what must survive is precisely the record that the deletion was
  lawful. The `consents` ledger, the audit rows and the erasure's own audit row
  all survive. **Pass.**
* **The salt's location.** §10.1's re-identification claim rests on a secret
  *"not stored in the database"*, which is a property of deployment rather than
  of code and is exactly what a test written beside the code assumes, because
  from inside the process the secret is simply there. Checked the way an
  attacker with a dump would: the hash is not the plain digest of the address,
  and the secret is not in the tombstone row. **Pass.**
* Plus step 2's identity-gone/pseudonym-unchanged pair, §10.1a layer 2 against
  a **brand-new** session planted after erasure (so layer 1 cannot be what
  refuses it), and §10.1a's WARNING that layer 2 must refuse `TOMBSTONED` only
  and never `SUSPENDED`. **All pass.**

**Five independent derivations, five agreements.** So the deferral is safe, and
QA can now say so with a measurement rather than with a reading. **QA does not
ask for the rewrite today**, and the reason is better than "it would cost a
slice": the four deferred §10.3 assertions gain their subjects in S4, the file
is rewritten then regardless, and **independence arriving with the coverage is
worth more than independence arriving on its own** — a rewrite now would
produce a second file asserting the same three live properties this one already
asserts, by a different hand, and change nothing a regulator could read.

**One condition QA does attach, and it is the whole of its disagreement:**
*independence deferred is not independence waived.* The gap is recorded against
§10.3, carried to S4 with its reason, and named in the go/no-go packet — and
the five derivations above are what makes the carry defensible rather than
merely convenient. Without them the ledger would be recording a gap it had not
measured.

---

## 5. Findings

| # | Finding | Status | Owner |
|---|---|---|---|
| **F24** | *(now `xfail(strict=True)`, red the day it is built)* `POST /account/correction` is named twice in §2.5 — in the Stack S row and as the justification for `display_name` being in Stack M — and does not exist in any slice (§4b) | **OPEN** — QA's two failing tests | cto to assign a slice |
| ~~F23~~ | `POST /account/nominee` was Stack M where §2.5's table puts it in S. **Closed by backend**; QA's four cells now pass, and backend's own control now parses the Stack table out of the markdown, so the derivation-from-contract method is permanent rather than a thing QA did once | closed | — |
| ~~F19~~ | **WITHDRAWN.** QA's blocker test lived in a module declaring `pytestmark = pytest.mark.django_db`, so it had database access by its own file's declaration and its premise was false. Backend's verbatim-copy experiment settled it: `1 failed, 1 passed`, one line of difference. Two of the three wrong claims about the mechanism were QA's and one reached the founder as fact. The blocker works; the test now lives in `tests/contract/test_db_blocker_is_wired.py`, which declares no marker and guards that it never acquires one | withdrawn | — |

| **F20** | *(now self-identifying — see §4b.3)* A stale reused test database produces up to 14 phantom failures and 15 teardown errors, landing on audit-chain tests rather than near the cause. Any migration invalidates it | **OPEN**, operational | backend / whoever documents the test command |
| ~~F21~~ | Foreign probe files in `tests/e2e/**`. **CLOSED** — verified by listing the tree: ten files, no probes, all tracked. Superseded by a different observation in §4b.3: three of QA's named S1 deliverables in that tree were written by the implementer, so `DATA-MODEL.md` §10.3's *"written independently"* is not satisfied. Content sound; independence is what is missing | closed / noted | ledger |
| F14, B2 | Carried unchanged from `QA-S0.md` v5.0 §7 | record / by agreement | — |
| F11, F13, F15, F17 | **CLOSED this pass** — all four were characterisation tests that now fail because the defect is fixed, and all four are converted to regressions named for the finding | closed | — |

The four closures are worth a line each, because three of them were QA's
highest-severity open items: the anonymous idempotency key is now checked for
**version 4** and not merely UUID shape (F11); W1c's source grep now sees a
property *assigned* rather than decorated, a bare class constant and a bare
annotation — the first being the exact shape QA used to demonstrate the residual
(F13); `test_forbidden_response.py` gained the value and contact-detail limbs
(F15); and `tests/unit/test_plpgsql_refusal_sqlstate.py` puts rule 16's SQLSTATE
half into the repository, which QA had encoded only in its own trees (F17).

`tests/contract/test_postgres_catalog.py`'s plpgsql inventory is also
re-pointed: S1 added a sixth function, so the count is six again **for a
different reason than the one `POSTGRES-FIRST-RUN.md` §0(a) corrected** — the
earlier "six" is still wrong. It is now asserted as an exact set per slice, so
the next addition is a deliberate edit rather than a surprise, and S2's
`listings_price_is_immutable` will land in a third set.

---

## 6. One more thing QA did this pass, unasked

While re-pointing, QA found that **migration `core/0008`'s privilege layer — the
control Red Team asked for — was verified structurally and by nothing
behavioural.** `tests/conftest.py` re-grants all of it for the whole session,
for good and documented reasons, so every guard test in the repository exercises
the **trigger** layer on a database with one layer where production has two.

`GRANT`/`REVOKE` are transactional in PostgreSQL, so QA put the production state
back **inside one test's transaction** and asserted the behaviour, which had
never been done: `tests/contract/test_least_privilege_independently.py`, seven
tests. The one that matters is
`test_truncate_is_refused_by_privilege_even_with_the_trigger_escape_granted` —
the escape granted so the **trigger permits** the TRUNCATE, the privilege
revoked, and the statement refused with **42501**. That is `CLAUDE.md` rule 14's
independence proof, and RED TEAM §3's finding was precisely that the gate had
one layer twice. The matrix is asserted in both directions, with the
both-granted case as a negative control so the two single-layer tests cannot be
measuring one thing twice.

Recorded as **F18** in that file: the suite's default state is the weaker of the
two layers, so a developer reading a green run is reading the trigger. The
deeper fix is the one 0008 already names — move table ownership off the
application role, after which the harness could not re-grant and the question
would not arise.

---

## Amendment log

| Date | Change | By |
|---|---|---|
| 2026-10-22 | v1.0 — S1 pass. Three re-pointings accepted, two of them changing what the test asserts; `[ta]` replaced by a fallback invariant that runs today; `NOT_PAGES` replaced by a content-type invariant with its own rule-12 guard; the route count replaced by an ownership invariant, a no-tenant-leak sweep and the ORM-reachability argument. The a11y harness now signs in and reaches eleven pages instead of four. F11, F13, F15 and F17 closed and converted to regressions. New findings F18 (privilege layer tested structurally only, with the behavioural test now written), F19 (the blocker, with measured cause and fix — QA's F9 is a contributing cause), F20 (stale test DB), F21 (foreign files in QA's tree) | test-qa |

---
---

# QA-S1 v2.0 — the erasure pass

**Owner:** test-qa · **Version:** v2.0 (appended to v1.0 above, which stands
unchanged) · **Date:** 2026-10-22
**Engines:** PostgreSQL 16.15 via `set -a && . ./.env && set +a` with
`BOOKHOP_TEST_DB_NAME=bookhop_qa_s1`; SQLite via `BOOKHOP_DB_ENGINE=sqlite`.
**Scope of this pass:** the erasure path's session scan · the deletion journey
end to end · the three claims most worth distrusting (no DOB persisted, the two
strict xfails, the append-only guards after a migration) · J1's unhappy column
and J9's help surface.
**v1.0 covered the three re-pointings and the harness isolation finding. All
three re-pointings are already in the tree and were re-verified green this
pass; they are not re-argued here.**

---

## 7. Commands and output

### 7.1 Baseline, before this pass — reproduced, matching what was reported

```
$ set -a && . ./.env && set +a && export BOOKHOP_TEST_DB_NAME=bookhop_qa_s1
$ .venv/Scripts/python.exe -m pytest -q
911 passed, 48 skipped, 2 xfailed in 35.60s

$ BOOKHOP_DB_ENGINE=sqlite .venv/Scripts/python.exe -m pytest -q
851 passed, 109 skipped, 1 xfailed in 25.59s
```

Both xfails are `tests/unit/test_least_privilege.py`; the second skips on SQLite
because SQLite has no `TRUNCATE` and no role system, which is why the counts
differ by one. That is consistent and is asserted in §9.2 below.

### 7.2 After this pass

```
$ set -a && . ./.env && set +a && export BOOKHOP_TEST_DB_NAME=bookhop_qa_s1
$ .venv/Scripts/python.exe -m pytest -q
1 failed, 1005 passed, 57 skipped, 2 xfailed in 30.77s
FAILED tests/contract/test_s0_surface.py::test_a_test_without_the_django_db_marker_cannot_reach_the_database

$ BOOKHOP_DB_ENGINE=sqlite .venv/Scripts/python.exe -m pytest -q
1 failed, 952 passed, 120 skipped, 1 xfailed in 24.39s
FAILED tests/contract/test_s0_surface.py::test_a_test_without_the_django_db_marker_cannot_reach_the_database
```

Counts above the baseline come from this pass's seven files **and** from work
other agents landed in the same window (§11.3); the pass/fail verdict is what
matters here, not the delta. The one failure is **F19 from v1.0 §3, still open
and unchanged** — Red Team's
test-isolation finding, with its measured cause and measured fix already written
in that test's own message. It is not a finding of this pass and nothing in this
pass touches it.

### 7.3 The seven files this pass added, run alone on both engines

```
$ .venv/Scripts/python.exe -m pytest \
    tests/e2e/test_erasure_sessions.py tests/e2e/test_deletion.py \
    tests/e2e/test_no_dob_independently.py tests/e2e/test_first_run_journey.py \
    tests/contract/test_append_only_by_behaviour.py \
    tests/contract/test_open_criticals_are_honest.py \
    tests/contract/test_standing_preconditions.py -q

PostgreSQL : 66 passed,  9 skipped     (+1 failed when run, since fixed - see 11.2)
SQLite     : 64 passed, 11 skipped     (+1 failed when run, since fixed - see 11.2)
```

The nine/eleven skips are enumerated in §13. **Every one names the slice or the
engine and the reason**; none is a quiet pass.

---

## 8. The session scan — the attack, and what it found

`DATA-MODEL.md` §10.1 step 3 says *delete … `sessions`*. The implementation
scans the session table, **decodes each row** and matches a user id — the only
step in the erasure transaction that rests on a decode rather than a column
comparison, with the decode exception swallowed by design. The question put to
QA was whether the scan can silently match nothing while `erase_account` reports
success, leaving a deleted account signed in on a phone.

**Answer: the scan can be made to match nothing — three ways — and
`erase_account` reports success in all three. No live session results, because a
second and independent layer rejects a `TOMBSTONED` user at request time. That
layer was undocumented and, before this pass, untested.**

`tests/e2e/test_erasure_sessions.py`, 10 tests, both engines, every session
created by walking J1 for real (`POST /auth/start`, run the queue, read the link
out of the email the way a student reads it, `GET /auth/c/{token}`).

| Attack | Scan finds | `erase_account` | Row/cookie survives | Student signed out |
|---|---|---|---|---|
| Nothing — the control | the session | success | no | **yes** |
| Two devices, one deletes | both | success | no | **yes, both** |
| Undecodable row beside a valid one | both valid ones | success | the foreign row only, correctly | **yes** |
| Key rotation **with** `SECRET_KEY_FALLBACKS` | the session | success | no | **yes** |
| Key rotation **without** a fallback | **nothing** | success | **yes, carrying the user id** | yes |
| `SESSION_SERIALIZER` changed | **nothing** | success | **yes, carrying the user id** | yes |
| `SESSION_ENGINE = signed_cookies` | **nothing to scan** | success | **the cookie, unchanged** | yes |

### 8.1 What is sound, and worth saying

* **The swallow is per row, not per scan.** An undecodable row planted beside
  two valid ones does not abort the scan: both valid sessions go. If the
  exception handling had sat around the loop, one unreadable row — from an old
  key, a half-written row, a rolled-back deploy — would have left every session
  after it alive while the transaction committed and reported success.
* **The scan does not over-delete.** The unattributable row is left alone. A
  scan that deleted what it could not read would be deleting another student's
  session on a guess.
* **Rotation with a fallback is handled correctly**, which is the supported
  rotation and the one that matters: the session is genuinely live mid-rotation
  (`GET /account` is 200, asserted, so the test is not passing on a dead row)
  and erasure reaches it.
* **Erasure reaches every device**, not only the one that pressed the button.

### 8.2 FINDING S-1 (minor) — the scan is coupled to two settings and nothing says so

Under **any** of: a signing-key rotation without a fallback, a changed
`SESSION_SERIALIZER`, or a non-database `SESSION_ENGINE`, the scan contributes
**nothing** to J8's *"Signed out"*, and `erase_account` still reports success.

For the first two, a session row survives the erasure **carrying the erased
student's user id in its data**. That is two things at once:

1. `DATA-MODEL.md` §10.1 step 3 says *delete* `sessions`; a surviving row is
   retained personal data after an erasure the student was told had completed;
2. the row is unreadable only while the old key or serialiser is unavailable.
   Restore either — a backup, a rolled-back deploy, a `SECRET_KEY_FALLBACKS`
   entry added later — and it decodes to the erased user again.

This is `CLAUDE.md` rule 17's `ASSUMED THERE` case: a compliance guarantee
resting on a prediction about two Django settings, written down nowhere. **The
lazy fix is not a bigger scan.** Either delete by a means that needs no decode,
or add a one-line conformance test that `SESSION_ENGINE` is the database backend
and `SESSION_SERIALIZER` is the one the rows were written with — so a deployment
that changes either fails the build rather than the erasure.

### 8.3 FINDING S-2 (material, and the most important thing in this pass) — the layer that is actually doing the work has no owner

The reason none of the three attacks produces a live session is that **a request
carrying a session naming a `TOMBSTONED` user is refused at request time**.
Measured by planting a *brand-new* session for the erased user **after**
erasure — so the scan demonstrably cannot have deleted it, because it did not
exist when the scan ran — and getting a redirect to `/auth/start`.

That is `CLAUDE.md` rule 14's second independent layer, and it is the layer
holding the guarantee. **But:**

* **no document names it.** `DATA-MODEL.md` §10.1 step 2 sets
  `status='TOMBSTONED'` as a *state change*; nothing says a request must refuse
  it. Rule 18 exactly: a control guaranteeing a state is not thereby a control
  detecting a bad input;
* **before this pass no test asserted it.** A refactor of the session-to-user
  lookup — a plausible S2 change, once there is more than one thing to look up —
  removes it with no test going red, and *then* all three attacks in §8 become
  live sessions on deleted accounts;
* it is **narrow**. Measured: only `TOMBSTONED` is refused. A session naming a
  `SUSPENDED` user is accepted and serves `/account`. For a read that is
  defensible — a suspended student keeps their DPDP s11 access and s12 erasure
  rights — and it is recorded rather than asserted either way, because no
  document rules on it. The *write* side was a separate finding; see §11.2.

Both properties are now asserted in
`test_a_tombstoned_user_is_rejected_by_something_other_than_the_session_scan`
and `test_the_second_layer_is_narrow_and_only_tombstoned_is_refused`. **To cto:
the second layer needs a line in `DATA-MODEL.md` §10.1, because a control
nobody wrote down is a control the next refactor removes.**

---

## 9. The three claims most worth distrusting

### 9.1 "No date of birth is persisted in any state" — **holds, and holds better than the claim required**

`tests/e2e/test_no_dob_independently.py`, 9 tests, both engines. Written as a
second reading rather than a copy of the column sweep, and it differs in four
ways that each close a route a column sweep cannot see: it drives the real HTTP
surface (L3 **and** L2) in both outcomes; it sweeps the session store,
`jobs.payload`, `idempotency_keys.request_hash`/`response_body`, the
`bookhop.security` log stream and the rendered response bodies; it covers the
staff-review and rejection paths; and it checks the export file, which is a
document the student receives.

Its own planted-date control is independent of backend's: the date is planted in
each of the five places the file searches and each sweep is asserted to find it,
because a sweep that cannot find a date it was handed is not evidence about a
date it was not.

Results, all clean:

* an accepted declaration on **both** surfaces persists nothing, logs nothing,
  echoes nothing;
* an **idempotency replay** of the declaration hands back no date — the stored
  `response_body` is a persistence site a column sweep only reaches if somebody
  thinks to replay;
* the **rejection path** — three writes in one transaction, the most sensitive
  date the product ever sees — leaves no date in any column, in the session, in
  the security log or on the refusal page; the `users` row is gone; the
  `REJECTED_UNDER_18` event survives by pseudonym with a NULL FK. The refusal
  also suggests no workaround, which AC-A2.3 requires;
* the **export** carries no date and asserts `date_of_birth_held: false` — the
  claim and its check in one test, per rule 9;
* **the free-text note is refused, not merely discouraged.** `DATA-MODEL.md` §2
  says `age_verification_events.note` *"must not contain a date of birth"* and
  routes it to *"code review item"* — a human as the only control. Measured: the
  service **raises** `ValidationFailed` with a message naming the rule, before
  the row is written. That is rule 18 answered properly: detection above the
  schema floor, not a state guarantee mistaken for one. **It is now asserted**,
  because the specification does not require it and a refactor could drop it
  without failing anything else. The permitted branch is asserted beside it — a
  guard that refused every note would make §1.4's human review unperformable.

### 9.2 The two strict xfails — **both honest, verified by their failure mode and not by their presence**

`tests/contract/test_open_criticals_are_honest.py`, 4 tests.

The defect class: `xfail` records *that* a test failed, not *which* assertion,
and treats an exception identically to a failed assertion. Both xfails have two
limbs and only the first is the attack, so each could report its tracked
exposure while failing on something else entirely.

Measured with `--runxfail`:

```
$ .venv/Scripts/python.exe -m pytest tests/unit/test_least_privilege.py --runxfail -q
E  AssertionError: three ORM statements opened the discovery gate: ADR-002 4.1(b)'s
   floor is below the control it describes
   assert datetime.datetime(2026, 10, 22, ...) is None
   tests\unit\test_least_privilege.py:174
E  AssertionError: the application role emptied the audit log
   assert False  +  where False = exists()
   tests\unit\test_least_privilege.py:207
2 failed, 4 passed
```

**Each fails on its first, named assertion — the attack itself.** The gate
genuinely opens (not the audit-row limb, not an exception); the TRUNCATE
genuinely succeeds (not a 42501 permission error, which would have meant the
xfail was reporting the inverse of the truth while the privilege layer held).

The honesty check is kept as a durable test rather than a one-off measurement,
and the attacks are **reproduced from `ENGINEERING-MEMO.md`'s own text** so the
claim rests on QA's reproduction and not on reading the file being audited. Each
test passes while the exposure is open and goes **red** when §1 or §3 is fixed,
with a message saying to de-xfail the other file in the same commit — because a
strict xfail left on a passing test fails the build and a non-strict one stops
tracking the critical at the one moment tracking is for. A fourth test asserts
both marks are still `strict=True` and still cite the memo section, read out of
the source rather than by importing it.

### 9.3 The append-only guards after a migration — **behaviour holds on both engines; FINDING A-1 on the control**

`tests/contract/test_append_only_by_behaviour.py`, 12 passed / 5 skipped on
SQLite, 13 / 4 on PostgreSQL.

`tests/unit/test_append_only_triggers_exist.py` closed a measured, shipped
defect the right way — SQLite rebuilt `notice_versions` to widen a CHECK and the
rebuild took the table's triggers. QA's question is the next one, and it is
rules 16 and 18: **an existence check is a state guarantee; it cannot tell a
trigger that refuses from a trigger that does not.**

So this file derives the table set **from `DATA-MODEL.md`'s own headings** rather
than a hand-kept dictionary (rule 11 — the list that gets edited instead of
extended; this one gains entries the day the contract does), and asserts the
**behaviour**: raw-SQL `UPDATE` and `DELETE` against a live row on every declared
table, on both engines, **asserting the guard's message text and that it names
the table** — not the exit status, per rule 16. Raw SQL rather than the ORM,
because §8's claim is that *"the audit trail has to resist the application as
well as the user"* and an ORM-only test would be satisfied by a `save()`
override.

All five S0/S1 tables refuse both operations on both engines, with their own
messages. The one **permitted** UPDATE —
`gate_authorisations.revoked_at`/`revoked_reason` — is asserted to still work,
because a guard that refused it would make closing a gate impossible and the
symptom would arrive while somebody was trying to shut a campus down.

**FINDING A-1 (material) — a migration shape that defeats the existence
control.** On PostgreSQL the existence control's second assertion is
`assert names` — *any* trigger on the table. `audit_log` carries two:
`audit_log_append_only`, which refuses UPDATE and DELETE, and
`audit_log_no_truncate`, which refuses only TRUNCATE. Measured, inside a
rolled-back transaction:

```
audit_log triggers: ['audit_log_append_only', 'audit_log_no_truncate']
baseline UPDATE: refused -> audit_log is append-only (DATA-MODEL.md section 8):
                            UPDATE is not permitted
after drop:        ['audit_log_no_truncate']
POST-DROP UPDATE: PERMITTED  <-- audit log is now mutable
existence control would see: True
```

**So the defeating migration is any migration that drops or re-creates the
append-only trigger while leaving its sibling** — including the SQLite
table-rebuild case that control was written for, if a restore migration happens
to put back one of the two. The fix is not a longer list of trigger names; it is
the behavioural parametrisation above, which asks the property and cannot be
satisfied by a sibling. The finding is recorded as a passing test that goes red
if the two triggers are ever merged, with a note to delete it then.

On SQLite the same control matches names containing `no_update` and `no_delete`,
so the sibling shape does not defeat it there; the SQLite exposure is the table
rebuild, which that file's own docstring measures. The test skips on SQLite with
that reason, naming the engine and the slice.

---

## 10. The deletion journey as a whole

`tests/e2e/test_deletion.py` — `DATA-MODEL.md` §10.3 names this file by path and
assigns it to test-qa to be written independently.

### 10.1 Five of the seven assertions have no subject in S1, and say so

(a), (b) and (g) need `transfers` (S4), (e) needs `messages` (S5), (d) needs
`repeat_infringer_records` (S6). Each is a **parametrised skip naming the model
and the slice**, driven from §10.3's own list, and each **fails rather than
skips** if the model appears — so the day S4 lands, the skip becomes a red test
demanding the assertion rather than quietly continuing to skip.

**This includes `PRD.md` AC-X1.3, the assertion product calls the one it would
keep if it could keep only one.** It is not verified and cannot be until S4.
Said plainly rather than worked around.

### 10.2 What is verified

* **the pseudonym survives unchanged** and is on the tombstone — the key every
  §9 metric groups by, and the thing AC-X1.3 will rest on;
* **the identity columns are gone** (email, display name, password), status is
  `TOMBSTONED`, tokens and `campus_verifications` are deleted, and the coarse
  campus/city code is kept as §10.1 step 4 requires;
* **§10.3(c) — the retained record cannot be re-linked** — fully testable today
  because it is a claim about the mapping, not about the transfer. Three
  assertions: the raw address appears in **no column of any table** (a catalogue
  sweep, not a remembered column list, so it covers `django_session` and
  anything a migration made outside the ORM); the stored hash is **not** the
  unsalted sha256 of the address, which is what makes the salt load-bearing
  rather than decorative; and a guard that the test can tell a salt from a typo;
* **the one-year floor, in both directions.** `purge_due_at` is
  `tombstoned_at + 365 days`. The expiry job run on the day of deletion purges
  **nothing** and writes **no** `purge_log` row — tested because only testing the
  second direction would pass on a job that purged everything immediately, and
  an early purge destroys the record the floor exists to keep. With a
  **time-shifted** fixture the same job purges the tombstone, NULLs the salted
  hash and writes exactly one `purge_log` row with `mode='PURGE'` — **§10.3(f)**,
  and the only way to observe a one-year rule without waiting a year;
* **`consents` survive untouched**, including a withdrawal row, which is §10.1
  step 7 and is the record that the deletion itself was lawful.

### 10.3 FINDING D-1 (material) — found, reported, and fixed by frontend during this pass

`PRD.md` AC-X1.2 and `JOURNEYS.md` J8 step 3 require *the truth, before the point
of no return*. The confirmation screen made all three disclosures AC-X1.2 names —
and then closed with **"Everything else goes now."**

Measured after a real deletion, these survive and every one is about the student:

| Survives | Retention | Told? |
|---|---|---|
| the `users` row — campus, city, pseudonym, both verification booleans | indefinite | no |
| `user_tombstones.email_hash` — a **salted hash of their email**, for **ban-evasion detection and dispute linkage** (§7 row 3) | 1 year | no |
| `age_verification_events` — their age decision, by pseudonym | account life + 1 yr | no |
| `audit_log` — one row per action, with `actor_pseudonym`, `ip`, `user_agent` | 1 year | no |

**Every one of those retentions is lawful. The defect was the sentence** —
`CLAUDE.md` rule 9's shape in student-facing copy, on the one screen the project
calls the point of no return, with no test between the claim and the system until
this one. The email hash is the sharp end: it is the item a reasonable person
accepts when told and resents when discovered, and the screen never mentioned it.

The test is written so a cosmetic reword does not turn it green — it fails only
while the totality claim **and** the survivors are both present.

**Status: FIXED during this pass.** `templates/delete_confirm.html` now drops the
totality claim entirely and enumerates four more items, leading with the email
hash and naming its mechanism, period and purpose. The test passes. Two things
worth recording about the fix, because both are right: there is now **no
totality claim in either direction** ("nothing else is kept" would have been the
same defect mirrored), and `repeat_infringer_records` is deliberately deferred to
S6 with its reason written down rather than left out.

---

## 11. Other findings from this pass

### 11.1 The J1 unhappy column and J9 — `tests/e2e/test_first_run_journey.py`, 19 tests, clean

The charter puts the unhappy paths first, so the happy path appears once as the
control that makes the refusals meaningful. All pass on both engines:

* **the account-enumeration oracle is closed, asserted as indistinguishability**
  rather than as a status code — status, redirect target and *rendered page* are
  compared between a known-good campus address and an address on a domain no
  campus accepts, with only the address masked. A test asserting `== 302` on each
  separately would pass while the two pages said different things, which is the
  whole oracle. **And the side effect matches too:** no email is sent to the
  unrecognised domain, which a page comparison cannot see and which is the same
  oracle by another route;
* a campus with **no MoU** (`email_domains = []`) creates no account and issues
  no token — EC-11;
* the **rate limit bites at the published number**, parametrised one request at a
  time so the report shows *where* it bit: attempts 1–5 pass, 6 is a 429 with a
  usable `Retry-After`. A limit below its published number would lock students
  out of the only entrance, and a single loop asserting "a 429 happened
  somewhere" cannot tell the two apart;
* **four dead ends converge on one page** — reused link, expired link, malformed
  token, well-formed-but-never-issued token — each a plain page that mentions the
  link and offers a way on, with no stack trace. A path traversal in the token
  position is asserted **separately** as an ordinary 404, because folding it in
  would have meant weakening the dead-link test's assertion, and a guard loosened
  to accommodate an unrelated case is how guards stop guarding;
* **nothing on the consent screen is pre-ticked** — E-Com r.4(9), in force today,
  one `checked` attribute away from being breached;
* **declining a required purpose names what it blocks and leaves the student
  signed in.** The second half is the one a reasonable developer breaks: consent
  obtained on pain of losing the account is not freely given;
* **J9: the help page says what BookHop cannot do before the student types**
  (AC-H6.5), and **no surface anywhere publishes a phone number or a WhatsApp**
  (AC-H6.4) — swept over every concrete route plus the sign-in email, with the
  grievance officer's statutory contact declared as the one exemption **and its
  rationale carried beside it**, per A-17's lesson about criteria that outgrow
  their reason. This is a measurement control as much as a support one:
  off-platform minutes are invisible, and that number is D-009's reversal
  trigger.

### 11.2 FINDING P-1 (material) — `API-CONTRACT.md` §2.5 precondition 2 was not enforced; fixed during this pass

`tests/contract/test_standing_preconditions.py`. Measured on both engines: with
`users.status='SUSPENDED'`, `PATCH /api/v1/account` returned **200** and changed
the display name, and `PUT /api/v1/account/consents/notifications` returned
**200** and appended a consent row. §2.5 requires `403 SUSPENDED`, second in the
order.

Material in a slice whose writes are small, for two reasons. Suspension is the
documented response to `REVOKED_MINOR_DISCOVERED` — *suspend, erase, log* — and
`user_tombstones.reason` carries `STAFF_ENFORCEMENT`, so an account that keeps
writing after suspension makes both procedures advisory. And it is **one check in
one place that every S2 listing write and every S4 offer write inherits**: the
cheapest moment to find it absent is now.

**Status: FIXED during this pass** (backend edited `apps/accounts/api.py` and
`services.py` while this report was being written). Both halves now return
`403 SUSPENDED`, and the test — including its rule-12 control that an *active*
student gets a 200 through the same call — passes on both engines.

**One thing deliberately NOT asserted, and escalated instead.** §2.5 read
literally refuses a suspended student their DPDP s12 erasure and s11 access
rights. Measured behaviour is that erasure succeeds for a suspended student,
which is almost certainly correct and is a **contradiction in the specification,
not a defect in the build**. It is routed to cto rather than smuggled into an
assertion.

### 11.3 Observation, not a finding — two agents in one tree at once

`tests/contract/test_s0_surface.py` (QA's file) gained a test from another agent
during this pass, and `apps/accounts/api.py` was mid-edit and did not parse when
a run was taken at 12:13, producing seven spurious `IndentationError` failures in
`test_p14.py` and `test_forbidden_source.py`. Those are **not** findings and are
not counted anywhere above; the numbers in §7 are from runs on a parsing tree.

Recorded because `CLAUDE.md` rule 6 is *"never two agents editing the same files
concurrently"*, and a QA run against a tree being edited underneath it produces
failures that look exactly like defects. The counter-observation is that the
concurrency also worked: D-1 and P-1 were both fixed within the hour, each
citing QA's test by path.

---

## 12. Verdict

**S1 passes QA, with one pre-existing open failure (F19, the harness isolation
finding from v1.0 §3) and three material findings, two of which were fixed during
the pass.**

| # | Finding | Severity | Status |
|---|---|---|---|
| S-1 | The erasure session scan contributes nothing under a key rotation without a fallback, a changed `SESSION_SERIALIZER` or a non-database `SESSION_ENGINE`; a row survives carrying the erased user's id | minor | **open** — to backend |
| S-2 | The layer that actually keeps a deleted account signed out (`TOMBSTONED` refused at request time) is named in no document; now asserted by QA | material | **open** — to cto, one line in §10.1 |
| A-1 | On PostgreSQL the append-only **existence** control is satisfied by a surviving unrelated trigger while the table is mutable | material | **open** — the behavioural test is the mitigation |
| D-1 | "Everything else goes now" on the point-of-no-return screen, with four surviving categories | material | **fixed** by frontend |
| P-1 | §2.5 precondition 2 (`403 SUSPENDED`) not enforced on any S1 write | material | **fixed** by backend |
| F19 | Test isolation: a test with no `django_db` marker reaches the database | material | **open** from v1.0 |
| — | §2.5 would refuse a suspended student their s11/s12 rights | spec | **escalated** to cto |

**The most serious gap remaining is not any of them. It is that no student has
completed a journey**, and the second is that **five of `DATA-MODEL.md` §10.3's
seven assertions — including AC-X1.3, the one product says it would keep above
all others — have no subject until S4.** Deletion is verified as far as S1 can
verify it, which is the identity half. The measurement half is unverified and
will stay unverified for three slices.

---

## 13. What was NOT verified, and why

**Skips in this pass's files, every one naming the slice or the engine:**

| Skipped | Reason |
|---|---|
| §10.3 (a), (b), (d), (e), (g) | `transfers` is S4, `messages` S5, `repeat_infringer_records` S6. Each becomes a **red test** the day its model appears |
| Append-only behaviour for `transfer_events`, `moderation_actions` | declared append-only in DATA-MODEL §5 and §6; tables are S4/S6 |
| F-A1, the sibling-trigger defeat | PostgreSQL only; skips on SQLite naming the engine and the different exposure there |
| The TRUNCATE xfail-honesty test | PostgreSQL only; SQLite has no TRUNCATE and no role system |

**Not verified at all, carried forward from v1.0 and unchanged:**

* **Four WCAG 2.2 AA criteria need a browser or a human** and cannot be decided
  by an HTML-level harness. The keyboard-only walkthrough of every flow — which
  the charter says is required and which automated checks explicitly do not
  substitute for — **has not been done**; there is no browser automation on this
  machine. S1 is the first slice with flows to walk, so this is now a real gap
  rather than a theoretical one.
* **Tamil is not verified and must not be reported as verified.** `i18n.ta_enabled`
  is false, no reviewed Tamil is served, and the banned-vocabulary grep is
  English-only until `locale/ta/REVIEWED.toml` exists (accepted risk A9). The
  test that runs today is that the locale is **closed** and that a Tamil
  `Accept-Language` is served English on both an L3 page and an L2 endpoint.
* **p75 LCP and p95 search latency** — need a browser and a throttling profile.
  S3's, and still unverifiable here.
* **No restore test.** S8, platform-sre.
* **Nothing is deployed and no student journey has ever been completed**
  (`ENGINEERING-MEMO.md` §11). Everything above is behaviour on a developer
  machine against seed data.

---

## Amendment log, v2.0

| Date | Change | By |
|---|---|---|
| 2026-10-22 | v2.0 — the erasure pass. Attacked `_delete_sessions_for` four ways and established that the scan **can** be made to match nothing while `erase_account` reports success, but that an **undocumented, previously untested second layer** (`TOMBSTONED` refused at request time) is what prevents a live session — findings S-1 and S-2. §10.3's deletion acceptance test written at the slice it can be, with five of seven assertions as skips that become red tests when their model lands. No-DOB verified independently across both surfaces, both outcomes, the replay, the staff note and the export — clean, and the note refusal is detection rather than convention. Both strict xfails verified honest by failure mode under `--runxfail`. Append-only re-asked as behaviour on both engines with message-text assertions, finding A-1: a surviving sibling trigger satisfies the existence control while the table is mutable. J1's unhappy column and J9 driven end to end. Findings D-1 (deletion-screen totality claim) and P-1 (§2.5 precondition 2 unenforced) raised and both fixed within the pass | test-qa |
