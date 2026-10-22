# TASKS.md — dependency-ordered build order

**Owner:** cto · **Version:** v1.0 · **Date:** 2026-10-21
**Reads with:** ADR-001 (stack) · ADR-002 (tenancy + gate) · ADR-003 (no money)
· `DATA-MODEL.md` · `API-CONTRACT.md` · `THREAT-MODEL.md`.
**Order follows** the founder's original brief where it still applies:
accounts → listings → discovery → offers and the transaction state machine →
handover with limited disclosure → reports/moderation/disputes/support →
notifications and analytics.

---

## 0. The rules that make parallel work safe

1. **One agent, one file. Never two agents in the same file.**
   (`CLAUDE.md` rule 6.) The ownership table in §1 is the whole answer; if a
   task seems to need a file you do not own, it is a contract gap — raise it
   with cto rather than editing.
2. **A slice is done when it is integrated, Code Review green, QA green**, and
   it works end to end for a real user journey. A merged branch with no UI is
   not a slice.
3. **Code Review never approves its own code. Test & QA verifies behaviour
   independently of implementation** (`CLAUDE.md` rule 5, cto charter).
3a. **The tree freezes when a slice goes to review. No agent edits until the
   verdict returns, and each agent's work commits separately.** Adopted
   2026-10-22 on review's observation that **four consecutive rounds measured
   a tree that was moving underneath them** — one mid-edit syntax error
   produced seven spurious failures in a run that had to be discarded.
   **A review and a QA pass are both statements about an artefact, and they
   mean nothing against an artefact being edited while measured.** Separate
   commits are the other half: bulk commits erase which agent did what, and
   authorship is what makes a finding traceable to the work that caused it.
4. **Instrumentation ships inside the slice that creates the behaviour**, not
   later. D-009's entire mitigation depends on this, and a retrofit is how it
   fails. A slice whose metric rows are not written is not done.
5. Every slice includes its **migration**, its **tests**, its **EN and TA
   strings**, and its **`COMPLIANCE.md` §7 reconciliation** for any new
   personal-data field.
6. **No deployment to any host** until the founder approves infrastructure
   spend (`COST-MODEL.md` §5). Everything through S4 is testable at Rs 0 on the
   founder's Windows machine.

---

## 1. File ownership — the authoritative map

| Path | Owner | Notes |
|---|---|---|
| `bookhop/settings/**`, `bookhop/urls.py`, `bookhop/wsgi.py` | **backend-developer** | **Clarified 2026-10-22:** `bookhop/urls.py` is backend's and **backend may add includes to it** — S1 added `/api/v1/`, and S5/S6 will add more. v1.0's "included once in S0 and not touched again" was over-tight: it was written to stop *two agents* editing one file, and that invariant is **"frontend never edits it; it only ever edits `web/urls.py`"**. That is the rule; the once-only phrasing was a proxy for it that would have blocked every later slice |
| `apps/core/**` | backend-developer | scoping, gate, audit, jobs, flags, idempotency |
| `apps/accounts/**` | backend-developer | |
| `apps/catalog/**` | backend-developer | |
| `apps/listings/**` | backend-developer | |
| `apps/discovery/**` | backend-developer | |
| `apps/transfers/**` | backend-developer | |
| `apps/safety/**` | backend-developer | |
| `apps/support/**` | backend-developer | |
| `apps/notify/**` | backend-developer | |
| `apps/analytics/**` | backend-developer | SQL views + `export_metrics` |
| `web/views.py`, `web/forms.py`, `web/urls.py`, `web/context.py` | **frontend-developer** | HTML routes; **calls L1 services, never the ORM, never L2 over HTTP** |
| `templates/**` | frontend-developer | |
| `static/**` (css, `htmx.min.js` vendored, `sw.js`, `manifest.webmanifest`, icons) | frontend-developer | |
| `locale/en/**`, `locale/ta/**`, `locale/FORBIDDEN_EXCEPTIONS.toml`, `locale/ta/REVIEWED.toml`, `locale/ta/BLOCKING_CLASSES.toml` | frontend-developer | EN + TA `.po` files **and the two copy-enforcement manifests** (`THREAT-MODEL.md` §6.1). **A diff to either manifest is a Code Review escalation, not a review comment** — adding a hash is functionally granting a reviewer sign-off |
| `tests/unit/**`, `tests/api/**` | backend-developer | including the CI guard tests |
| `tests/e2e/**`, `tests/a11y/**`, `tests/contract/**` | **test-qa** | written **independently of implementation** |
| `tests/redteam/**` | **red-team** | **Added 2026-10-22 on QA-S1 F21.** Adversarial probes, written to be run and often to be thrown away. **Excluded from the default suite run** (`--ignore=tests/redteam` in `pytest.ini`'s `addopts`, or its own marker) and run deliberately. **A probe is not a regression test:** when a probe finds something real, the finding goes to the owning agent and the *regression* is written in that agent's tree, not here |
| `deploy/**`, `ops/runbooks/**` | **platform-sre** | **dormant until S8.** **Correction 2026-10-21 (REVIEW-S0):** platform-sre owns **deployment** pipelines only. The CI workflow that runs lint, types and tests is **developer tooling and belongs to backend-developer in S0** — v1.0 put `ruff`/`mypy`/CI in S0's scope while this table made CI dormant until S8, which is a contradiction that would have left S0 unable to finish. |
| `.github/workflows/**` *(or the chosen CI)*, `pyproject.toml`, `ruff.toml` | **backend-developer** | From S0. Test/lint/type CI only; nothing that deploys. |
| `company/architecture/**` | **cto** | no developer edits these |
| `.claude/agents/**` | **cto** | |
| `requirements.txt`, `requirements-dev.txt` | backend-developer | **adding a package needs Code Review sign-off**; one touching personal data needs a founder DPA signature |
| `README.md` (repo root), `CONTRIBUTING.md` | backend-developer | |
| `fixtures/seed_*.json`, `apps/core/management/commands/seed_demo.py` | backend-developer | seed data (ADR-002 §4.1(c)) |

> **F21 recorded, and the gap was in this table rather than in anyone's
> conduct.** Eight files appeared in `tests/e2e/**` from the Red Team
> engineering pass — and kept arriving while QA was measuring in that tree —
> one of which failed on an `ImportError`, **so another agent's broken scratch
> file presented as a QA failure in QA's own report. That is precisely what
> rule 6 exists to prevent, and it happened because this table had no row for
> adversarial work.** Red Team reviewing by *running probes* is the right
> instinct; it had nowhere to put them.
>
> **QA was right not to delete them.** Silently deleting another agent's work
> is worse than reporting it, and it excluded them from its numbers with the
> exclusion stated in the command so nobody reads around it. **Both halves of
> that are the correct handling and worth copying.**
>
> `tests/e2e/test_erasure_sessions.py` raised a real subject — erasure and
> sessions — which belongs in **test-qa's** tree as an S1 regression if it
> holds up, not in a probe tree. Routed to test-qa to adopt or decline on the
> merits.

**The shared-file risks, and how each is removed:**

| Risk | Resolution |
|---|---|
| Both agents want `bookhop/urls.py` | Backend wires `path("", include("web.urls"))` in S0. Frontend only ever edits `web/urls.py`. |
| Frontend needs a new service function | **Contract change → cto amends `API-CONTRACT.md` §3 → backend implements → frontend consumes.** Frontend never adds one. |
| Frontend needs a model field | Same route. `DATA-MODEL.md` is normative. |
| Both want `static/css/tokens.css` | Frontend owns it outright. Backend never emits inline styles. |
| Both want a template | Backend owns **no** templates — not even for emails. Email bodies are templates under `templates/email/` and **frontend owns them**; backend passes a context dict, specified in `API-CONTRACT.md` §3's `notify()` payloads. |
| QA wants to fix a bug it found | **QA does not fix.** It writes the failing test and hands it back. |

---

## 2. The slices

**S0–S3 are the first three delivery slices plus the skeleton.** Assignment is
in §3.

### S0 — Skeleton, tenancy, gate, audit, jobs *(backend only)*

Nothing else can start without it. One day of work that removes a week of
rework.

- Repo, `bookhop/settings/{base,dev,prod}.py`, `pytest-django`, `ruff`,
  `mypy`, and **a CI workflow that runs lint, types and tests —
  backend-developer's, per §1, and not platform-sre's**; platform-sre owns
  deployment pipelines only and stays dormant until S8. *(v1.0 scoped CI here
  while §1 made it dormant until S8; the contradiction is resolved in
  backend's favour because this is developer tooling, not infrastructure.)*
  Postgres is reached **via the CI service container at Rs 0** — see the S2
  gate below; local Postgres is a convenience, not a dependency, and Docker is
  not required for it.
- `apps/core`: `cities`, `campuses`, `legal_entities`, `gate_authorisations`,
  `feature_flags`, `audit_log` (hash chain + `verify_audit_chain`), `jobs` +
  `run_jobs`, `idempotency_keys`, `scoping.py`, `assert_discovery_open`.
- `manage.py open_discovery` / `close_discovery` with the full evidence
  checklist (ADR-002 §4.1(b)).
- `manage.py seed_demo` — one city, one campus, staff user, `is_seed` students.
- **The CI guard tests**: `test_forbidden_schema`, `test_scoping`, `test_gate`,
  `test_price_immutable` (trigger lands in S2; the test is written now and
  skipped with a reason until then).
- `/healthz`, `/readyz`, `X-Request-Id` middleware, structured JSON logging,
  `bookhop/urls.py` including `web.urls`.
> **S0 RE-APPROVAL CONDITIONS (QA-S0 v2.0, approval suspended 2026-10-21).**
> Four items, all backend's, all small, and **the first two must land in one
> commit** because fixing the tokens without the module is the fifth hand-made
> copy of the same rule:
> 1. **`apps/core/p14.py`** — W1d's single source of truth. Tests import it;
>    nothing retypes it. **Urgent, not tidy:** F6/F7 are its own predicted
>    divergence, already live.
> 2. **F6/F7 in the same commit** — all **22** tokens with `rs_` matching as a
>    **prefix** (ADR-003 §2.3 W1b's new match-rule column), and the exemption
>    scoped to the two permitted **columns**, not the `listings` table.
>    `amt`, `paid`, `payment` and `due` are currently caught by nothing.
> 3. **`tests/conftest.py` flush fixture** — three lines; without it the first
>    Postgres run of S4 fails in teardown and the tempting fix is deleting the
>    guard (ADR-001 §2.2 correction).
> 4. **The `gate_authorisations` completeness CHECK** — six evidence keys
>    present, `authorised_by_human` non-blank (ADR-002 §4.1(a), QA-S0 F8).
>
> **Not conditions:** W1c and `test_forbidden_response.py` are S1 (below), and
> the Postgres run is the S2 gate. Those are scheduled, not suspended.

- **Done when** *(corrected 2026-10-21 on QA-S0 B5 — v1.0's bar could not be
  met in S0 and was scored as unmet rather than green, which is the right
  outcome but the wrong bar)*: `pytest` is green **or skipped with a reason
  naming the engine and the slice**; `seed_demo` creates **one city, one
  campus with the gate closed, and one staff user** and prints what it did
  *not* create; `open_discovery` refuses on a campus with no CoI;
  `verify_audit_chain` passes; and **the eight guard tests exist, including
  the ones whose tables arrive later** — skipped with a stated reason, never
  absent.
  **"`seed_demo` produces a browsable-by-staff dataset" moves to S2**, which is
  the first slice in which a listing exists to browse.

### S1 — Accounts, age, campus verification, profile, deletion

**First in the founder's order, and correctly so:** nothing else can be built
without an adult, campus-verified actor, and deletion is cheapest to build
before there is data to delete.

Backend: magic-link request/consume,
`age_verification_events`, server-side 18+ rejection **with no DOB persisted
anywhere** (amendment A-5 — the `age_check_pending` table is gone), staff
age-review queue **which reviews the account and the outcome, never a date**,
`campus_verifications`, `notice_versions`, `consents` (append-only, six
purpose keys), `data_subject_requests`, `user_tombstones`, `erase_account`
(`DATA-MODEL.md` §10.1), **the `retention.purge` job in the same slice**,
`personal_data_access_log`, account export (s11) and nominee (s14).

Frontend: sign-in, "check your email", age declaration (`<input type="date">`),
per-purpose consent screen with **no pre-ticked boxes**, profile, privacy
settings with a **withdrawal toggle per purpose**, two-step delete with the
plain-language one-year retention explanation, legal pages, EN + TA.

**Four named controls that v1.0 left ownerless now land here** (REVIEW-S0
N1–N3, QA-S0 F1) — **S1 backend**, because S1 ships the first HTML and the
first L2 endpoints, and *a named control with no owner is never written*:
- **CSP** (`default-src 'self'`, no inline script, nonce for the one bootstrap
  script) as response middleware — an ASVS V1/V3 **L2** control named in
  `THREAT-MODEL.md` §4 B3 and assigned to nobody. It must exist **before the
  first HTML page ships**, not after.
- **`tests/unit/test_forbidden_response.py`** — named by ADR-003 §2.3 and
  `THREAT-MODEL.md` §6, claimed by no slice. It is **the compensating control
  for the jsonb and free-text limbs of P14** (ADR-003 §5.3), so it must
  exist before any response schema does. **QA-S0 F5 confirms it is still
  unwritten; "assigned" was not enough, so it is now the first commit of S1
  alongside W1c.**
- **ADR-003 W1c's source grep — `tests/unit/test_forbidden_source.py`** *(the
  contract corrected to match the repository, 2026-10-21; see the note below —
  it shipped early, in S0)*.
  **QA measured that no test in `tests/unit` or `tests/api` reads a source file
  at all** — no `rglob`, no `read_text`, no `Path(__file__)`. W1c is the
  **only** control for the `@property` residual that W5 accepts, so until it
  exists that residual has **no** control. **First commit of S1, before the
  first response schema exists.** With `test_forbidden_response.py` also
  unwritten, two of W5's three controls were specifications rather than code —
  see ADR-003 §5.3.1.
- **`tests/unit/test_p14_conformance.py`** — asserts every control ADR-003 §5.3
  names actually exists, so the section cannot claim what the repository does
  not have. QA has already written the two detectors; adopt them.

> **Filename ruling (ENGINE-DIVERGENCE §9.13, 2026-10-21): the contract changes
> to match the repository, and not because the repository got there first.**
> Backend renamed the file to match this document, then reverted, because
> **test-qa's `tests/contract/test_p14.py` imports that module path in three
> places and those tests are green.** Turning three passing tests red to match
> a filename is the wrong direction, and it would cost three agents' work to
> fix a document that can be right in one line.
>
> **But the decisive reason is that `test_forbidden_source.py` is the better
> name:** it is consistent with its three siblings —
> `test_forbidden_schema.py`, `test_forbidden_response.py`,
> `test_forbidden_copy.py` — and a guard family whose members are named by one
> convention is easier to find, to review as a set, and to notice a gap in.
> My `test_no_money_shaped_source.py` was more descriptive and less
> consistent, and consistency wins for a family of four. **So this is not an
> expedient deferral to the incumbent; the incumbent was right.**
- **The `API-CONTRACT.md` §2.2 error-shape renderer**, including *"500 never
  echoes an exception message; the `request_id` is the only thing the user
  gets"*. It sits between backend L2 and frontend L3 and would otherwise fall
  between two agents.
- **`apps/core/p14.py`** as the single expression of the P14 token sets, suffix
  allow-list, deny patterns and frozen column lists (ADR-003 §2.3 W1d), with the
  contract test asserting it matches the ADR.

**Copy enforcement lands here too** (`THREAT-MODEL.md` §6.1), because S1 is
where the first `.po` strings and the first legal pages appear:
- backend writes `test_forbidden_copy.py` (**English, whole-word, eight
  words**), `test_reviewed_locale.py` and `test_locale_gate.py`;
- frontend creates `locale/FORBIDDEN_EXCEPTIONS.toml`,
  `locale/ta/BLOCKING_CLASSES.toml` and an initially-empty
  `locale/ta/REVIEWED.toml`;
- `feature_flags['i18n.ta_enabled']` is seeded **`false`** and stays false
  until the native-speaker review lands. **Tamil strings may be written, and
  are, but no student is offered the Tamil locale while any blocking-class
  string is unreviewed.** That is the gate, and it is a test, not a promise.

QA: `test_deletion.py` (seven assertions, `DATA-MODEL.md` §10.3),
`test_no_dob_persisted.py`, the auth matrix, a11y on every S1 page —
**in English, and in Tamil only once the flag is on**.

**Done when:** a 17-year-old cannot create an account and no DOB is persisted
anywhere; an adult can sign in by email, grant and **withdraw** consent per
purpose, and delete their account; after deletion the transaction record
survives, is pseudonymous, and cannot be relinked.

### S2 — Catalogue and listings

> **Three S1 carry-overs to land before or with S2** (frontend S1 escalations,
> ruled 2026-10-22). None blocks S2 starting; the first blocks the seller
> block:
> 1. **`INSTITUTIONAL_EMAIL` spelling** fixed in `SYSTEM.md` §4.11a,
>    `COPY-DECK.md` §3.2 and **criterion 7h** — **design-director**; then
>    frontend drops its both-spellings tolerance. **S2 builds the seller block
>    on this string, so this one is first.**
> 2. **Criterion 7f narrowed** to *another person's* domain, second limb
>    unchanged — **design-director**. Contract position is already normative
>    (`API-CONTRACT.md` A-17).
> 3. **`LocaleGateMiddleware`** in `apps/core/middleware.py` — **backend** —
>    replacing frontend's view-helper enforcement, plus the L2 half of the
>    test (`THREAT-MODEL.md` §6.1).
> Plus: **`RANKING` and `GRIEVANCE_PROCEDURE`** notice kinds (backend,
> migration) so two required publications become publishable.

> **GATE ON S2 (ADR-001 §2.2 amendment, 2026-10-21): S2 may not start until
> the test suite can reach a PostgreSQL 16.** P14's price-immutability trigger
> is created in this slice and is **unverifiable on SQLite**
> (`ENGINE-DIVERGENCE.md` §3.9). **Take the CI route — a Postgres service
> container costs Rs 0 and is not a founder spend decision.** S0 and S1 may
> complete on SQLite.
>
> **The gate got MORE urgent, not less, and the number moved the wrong way.**
> **GATE OPEN — 2026-10-21. The first PostgreSQL run passed all nine items**
> (PostgreSQL 16.15, commit `09e2323`; Postgres 571 passed, SQLite 573 passed,
> six triggers live and all `ALWAYS`). **S2 may start.** Record:
> `POSTGRES-FIRST-RUN.md`, findings in `ENGINE-DIVERGENCE.md` §10.
>
> **Two S0 defects were found that SQLite could not have shown**, and both
> would have landed on S4: an audit row **dropped** under 12 concurrent
> appenders and reported as `AuditChainBroken` — a tamper-shaped error raised
> by load — and a session-scoped fixture binding a **per-connection** GUC, which
> `test_double_booking.py` would have tripped because it needs both
> `transactional_db` and several real connections. **That is the gate earning
> its keep: the run's value was the two defects, not the nine passes.**
>
> **Still open (A14a):** four properties remain unexecuted because their tables
> do not exist — price immutability (S2), double-booking and MVCC (S4), metric
> SQL (S7). Their test shapes are pre-written in `POSTGRES-FIRST-RUN.md` §3.
>
> **Five plpgsql bodies across migrations 0002, 0003 and 0005 have never been
> parsed by a server, and all five are security controls.** *(Corrected from
> "six": the price-immutability trigger does not exist, because `listings` is
> an S2 table — see `POSTGRES-FIRST-RUN.md` §0.)* Reviewed as text by two
> agents; **verified by neither.**
>
> **The first run is a deliverable with a written checklist:
> `POSTGRES-FIRST-RUN.md`** — nine items ordered by what is most expensive to
> discover late, each stating what a failure *means*; plus §2, what the run
> will **not** prove; and §3, the properties deferred to S2/S4/S7 with the
> exact shape to test when their tables arrive. **File the completed checklist
> with §2 attached**, because §2 is what stops the run being read as more than
> it is.
>
> **The first PostgreSQL run is itself a named deliverable, and its checklist
> is now written: `POSTGRES-FIRST-RUN.md`.** This paragraph's earlier sketch of
> what the run must demonstrate is superseded by that document, which corrects
> two things the sketch got wrong: **the price-immutability trigger and the
> double-booking index are on S2/S4 tables and cannot be exercised by this
> run** (they are deferred, with their exact shapes, in §3 there).
>
> **Superseded by the run, 2026-10-21: all five are now executed.** The
> pre-run statement was that five security controls were specified, reviewed as
> text and unexecuted, and that text review had meaningfully touched two of
> nine checklist items. **That ratio turned out to be the right way to have
> framed it** — the run's value was the two defects it found, both in the seven
> items reading could not reach.

**`POST /account/correction` lands here (QA F24).** s12(1)–(2), Stack S, a
`CORRECTION` data-subject request on the 7-day clock, staff-reviewed and
logged, plus the staff decision screen. **It is the justification for keeping
`display_name` in Stack M, and that justification is currently unbuilt** —
`API-CONTRACT.md` §2.5 forbids quoting the reasoning as satisfied until the
conformance test is green, and **QA's two red tests are the correct state and
must not be skipped.** S2 is the right slice on the merits: `display_name` is
visible to nobody but its owner until listings exist, **so the restriction
only starts costing a student anything in S2.**

**Also landing here, from S1 (2026-10-22):** the **Django admin** — backend
deferred it from S1 and that is right, because the moderation queue it exists
for is an S2 surface and an admin with no models to moderate is scaffolding.
And the **expired-only-DELETE triggers** on `consents` and
`age_verification_events` with their `purge_due_at` columns
(`DATA-MODEL.md` §2), which resolve a contract contradiction S1 could only
record. Both engine halves, plus `tests/contract/test_append_only_is_enforced.py` —
**behavioural and structural limbs both** (THREAT-MODEL §6.3).

**One judgement from S1 confirmed rather than re-opened:** backend declined to
reword an **already-applied** migration's trigger text to satisfy a cosmetic
grep. **Correct.** An applied migration is history; editing its text changes
what a future `migrate` from empty produces without changing any deployed
database, so the two diverge and the grep is satisfied by a lie. **If the text
must change it changes in a new migration, and if it is only cosmetic it does
not change at all.**

**The gated default manager lands here** (ADR-002 §2.3) — recorded as a line
item because *a deferral recorded only in a review is how an ownerless control
becomes an unwritten one*, and this project has hit that failure mode twice
(N1, N2):
- `GatedManager` as `objects` on `Listing`, `ListingPhoto`, `BookRequest`, and
  **retrofitted onto `User`** in the same commit.
- `all_objects = models.Manager()` and **`Meta.base_manager_name =
  "all_objects"` on every one of them** — one line per model, and *the kind of
  line that is invisible when missing*.
- The `all_objects` call-site allow-list, enforced in CI.
- **The reverse-relation test**: for each gated model, the gate applies on a
  direct query **and** on a reverse accessor, and `_base_manager` is
  unfiltered. **A test, not an argument** — if it shows reverse accessors are
  uncovered, that is a known limit rather than an assumed one.
- **It sits underneath `assert_discovery_open`, never instead of it**
  (ADR-002 §2.3). A manager returning no rows is not a `403 GATE_CLOSED`.

Backend: `books` (ISBN-13 checksum, trigram index), `prescribed_texts`,
`listings` (**with the `asking_price_paise` immutability trigger**),
**W1b's exemption rescoped from the `listings` table to the two permitted
columns (ADR-003 §2.3, REVIEW-S0 R1) and the W1a float check changed to a
union of both introspection routes (R2)** — both land with `listings`,
`listing_photos` (EXIF stripped before the row exists), **`GET /media/listing-photo/{photo_id}`** —
gate- and scope-checked in Django, bytes via nginx `X-Accel-Redirect`, 404 out
of scope (`API-CONTRACT.md` §5.2); **until it exists the data-saver criterion
is passing vacuously and is reported as NOT passing**, `swap_wants`
(UI-hidden), `book_requests`, `seller_terms_acceptances`,
`suspect_reproduction_flag` → `PENDING_REVIEW`, the moderation queue in admin
with `work_seconds`, seed fixtures including **one department's real reading
list** (R-01's test).

Frontend: sell flow (find-by-ISBN → confirm edition → condition, annotations,
damage, price → photos → publish), my-listings, listing detail, "wanted" form,
EN + TA.

QA: price immutability, photo EXIF, listing status machine, forbidden-copy
check, a11y; **and `listings.paise_count` is rejected by the schema guard**
(the R1 regression test — the shape that passed every layer before this slice).

**Done when:** a seed seller can list a book by ISBN with photos; the price
cannot be changed; a photocopy-flagged listing goes to review; swap and
general-reading rows can be created by fixture but appear nowhere in the UI;
**and all four of these, which are conditions on the default-manager deferral,
not nice-to-haves:**
- [ ] every gated model's default manager is `GatedManager` and its
      `Meta.base_manager_name` is `all_objects`;
- [ ] the reverse-relation test runs and **its result is recorded** — covered
      or not covered, stated either way;
- [ ] `all_objects` appears only in allow-listed call sites;
- [ ] **`listings.paise_count` fails the P14 guard** and
      `asking_price_paise` declared `real` fails it **via introspection even
      though the model declares `IntegerField`** (R2's union).

**And the two §4 requirements that are new since S2 was written, called out
here because S2 is in flight and a done-when written before them would
otherwise be read as complete:**
- [ ] **One real journey end to end through the actual UI** — for S2 that is
      *sign in → find a book by ISBN → set condition, annotations, damage,
      price → upload a photo → publish → see it listed*, driven by a client
      that was served the pages.
- [ ] **Red Team has reported, after review and QA both passed** (§4.1).
      S2's pass is pointed at **the listing surface meeting a real student**,
      and it is free to conclude the slice is not worth having.

### S3 — Discovery, behind the gate, instrumented · **plus notifications (amendment A-4)**

Backend: `search_listings` (exact ISBN, then trigram title, then course code),
cursor pagination, `search_events`, `search_result_opens`, the browse and
wanted indexes, `/legal/ranking`, **`assert_discovery_open` on every path**,
the `is_seed` restriction when closed.
**Added by A-4:** the `notifications` table, `notify()`, the **in-app channel
only**, and the `requests.match_scan` job with its **gate guard** (a closed
campus never notifies a real student) and its blocks/consent guards.

Frontend: search box, results, empty state — **the three truths kept apart**
(*not on your campus yet* · *we have it, reserved right now* · *we don't
recognise that ISBN*), never a bare "no results" — filters, the `GATE_CLOSED`
page, **the in-app notification list**, EN + TA.

QA: the gate test as a user journey (real student on a closed campus sees no
listings); **`match_scan` does not notify across a closed gate** — this is a
gate test, not a notification test; p95 search latency; p75 LCP on a throttled
mid-range Android profile; a11y.

**Done when:** `METRICS.md`'s search success rate and the request-side match
rate both return numbers from real rows, the gate test passes, and a seeded
want produces a `WANT_MATCHED` notification within one job cycle **on an open
campus and not on a closed one**.

> **Why notifications moved here from S7.** S4, S5 and S6 all generate events
> that must tell a student something. In v1.0 none of them had anywhere to
> write a notification until S7 — which meant either three slices of dead
> `notify()` calls or a retrofit across all three, and §0 rule 4 forbids the
> retrofit. One table and one list page, three slices earlier.

### S4 — Offers and the transfer state machine

Backend: `transfers`, `transfer_events`, the **partial unique index**, all
eleven states and every guard in `DATA-MODEL.md` §6.2, idempotency +
`expected_version` on every transition, the `reservation.expire` job.
**`accepted_at` is write-once** from the first commit — it is cheaper to get
right than to backfill (amendment A-1).

Frontend: offer, offer inbox, accept/decline, transfer detail with the state
shown in plain words, cancel.

QA: `test_double_booking.py` (N concurrent accepts), `test_idempotency.py`,
`test_system_transitions.py`, an exhaustive transition matrix — **every
state × every endpoint**, asserting 2xx or 422.

**Done when:** completion rate, cancellation rate and time-to-match are
computable from `transfer_events`.

### S5 — Handover coordination, limited disclosure, leakage follow-up · **plus reschedule, relay and student support (A-1, A-2, A-3, A-6)**

Backend: `handover_points`, propose/agree scheduling, the mandatory
**`HANDOVER_GUIDANCE`** acknowledgement before `SCHEDULED` (A-7),
dual confirmation, no-show, `transfer_followups` + the 72-hour `followup.*`
jobs + `classify_leakage`, `contact_disclosures` with the two-person CHECK,
threads and messages with `contact_pattern_flag`.
**Added by amendment:**
- **A-1** `reschedule_handover` (`SCHEDULED → ACCEPTED`, max 2, resets
  `reservation_expires_at`, does not rewrite `accepted_at`).
- **A-6** `relay_to_counterparty` + the `COUNTERPARTY_NUDGE` notification +
  the relay-first guard on `request_contact_disclosure`.
- **A-2** `support_tickets` / `support_work_log` / `support_messages`,
  `open_ticket_as_student`, `reply_to_ticket`, the admin server timer, the
  batch rule, and the `close_ticket` zero-seconds guard. **Moved from S6.**
- **A-3** `confirm_handover` closes matching `OPEN` `book_requests`.

Frontend: pick a handover point, agree a window, the **handover guidance**
notice, "did the book change hands?", no-show, **"change the time"**,
**"ask BookHop to reach them"** (never "request contact details"), the
follow-up question, chat, and the **help surface** — contextual "get help with
this" on every transfer, listing and account screen, the five static answers,
the ticket thread.

QA: the handover journey end to end; every `leakage_class` path; **the
reschedule cap at 2 and that a reschedule is never counted as a cancellation**;
**the relay writes no `contact_disclosures` row**; the two-person rule blocking
a self-approved disclosure; **a student cannot open or read another student's
ticket**; **`close_ticket` refuses with zero logged seconds**; forbidden-copy
on the guidance screens.

**Done when:** the leakage band query returns a band, no response anywhere
contains a contact detail, **support minutes per transfer is computable
(`DATA-MODEL.md` §9.4)**, and **the request-side match rate returns a non-zero
number for a seeded want that completed**.

### S6 — Reports, moderation, legal clocks, disputes, grievances, support timers

Backend: `reports` with per-category clocks, `legal_notices` with 3h/2h/36h +
the 21-day hold and automatic restoration, `repeat_infringer_records`,
`moderation_actions`, `disputes`, `grievances` (unauthenticated),
`safety_incidents` (+ founder escalation), `blocks`, the
`QUARTERLY_RULES_REMINDER` job.
*(The support tables moved to S5 — amendment A-2. The staff-side moderation
timers still land here, using the `support_work_log` built in S5.)*

Frontend: report form, grievance form (public), copyright-notice form (public),
my-reports, block/unblock, dispute form.

QA: `test_sla_clocks.py`; the 21-day restore; a report never auto-removes;
safety paths are **not** rate-limited to zero; **and the R3 condition — no
anonymous endpoint stores anything in `idempotency_keys.response_body` that its
`ticket_ref` does not already reveal to the person who filed it.** Anonymous
keys share one global namespace (`API-CONTRACT.md` §4.1), so a stored response
is returned to anyone presenting that key. Guessing a UUIDv4 is not a feasible
attack, **but it is a property we should choose rather than inherit** — and
`POST /grievances` is the endpoint where it would matter.

**Done when:** every clock in `COMPLIANCE.md` §8.4 is enforced by the system
rather than by a spreadsheet.

### S7 — Notification delivery channels and analytics

Backend: **email via SES, Web Push via VAPID**, `notification_preferences`,
`push_subscriptions`, **all `apps/analytics/sql/` views**, `export_metrics`
producing the weekly CSV with the §9.4 reference lines and the "not
catastrophic is not viable" sentence (R-25).
*(The `notifications` table, `notify()` and the in-app channel moved to S3 —
amendment A-4.)*

Frontend: preference screen, push opt-in, email templates in EN + TA.

QA: notification idempotency under job retry; the metric views against a seeded
dataset with known answers; **the §9.2 repeat-transfer query against a
time-shifted fixture**, which is the only way to test a 90-day metric before 90
days have passed.

**Done when:** the weekly export reproduces every row of `METRICS.md` §9.1 or
states why a row is not computable.

### S8 — Infrastructure *(platform-sre activates here, not before)*

Provisioning, nginx + TLS, systemd units, chrony → NPL/NIC, logrotate at one
year, nightly encrypted backup, **the tested restore**, uptime monitoring,
the daily digest, `deploy.sh` + rollback, the breach-runbook rehearsal
(Gate C3). All of `INFRA.md`.
**Gated on founder approval of spend** (`COST-MODEL.md` §5).

---

## 3. First assignments — who starts where, exactly

**backend-developer starts: S0, then S1 backend.**
Owns and creates: `bookhop/settings/*`, `bookhop/urls.py`, `apps/core/**`,
`apps/accounts/**`, `tests/unit/**`, `tests/api/**`, `requirements*.txt`,
`fixtures/seed_*.json`.
First commit is the skeleton plus the CI guard tests, **before any feature** —
because a guard added after the thing it guards is a guard that was never
tested. **That now means eight guard tests, not four** (`THREAT-MODEL.md` §6):
the whitelist money assertion and the frozen-column assertion are written
against the *expected* schema and fail loudly until the tables exist, which is
the correct direction of failure.

**frontend-developer starts: S1 front end**, in parallel, as soon as S0 lands
and `API-CONTRACT.md` §3's accounts signatures exist as stubs (backend commits
stubs that raise `NotImplementedError` at the end of S0 — a one-hour task that
unblocks a whole slice).
Owns and creates: `web/**`, `templates/**`, `static/**`, `locale/**`.
First commit is the base layout, `static/css/tokens.css`, the service worker,
the manifest, and the sign-in + age + consent screens in EN with TA stubs.

> **Dependency RESOLVED 2026-10-21.** `design/SYSTEM.md`, `DIRECTIONS.md`,
> `COPY-DECK.md` and `design/tokens.css` now exist. **Frontend takes
> `design/tokens.css` as the source for `static/css/tokens.css` rather than
> inventing provisional values**, and `COPY-DECK.md` is the source for both
> `.po` files. The ADR-001 §7 escalation on the missing design system is
> closed; the PRD and journeys exist too, so §6.1 and §6.2 below are closed as
> well. **One dependency remains open and it is a gate, not a blocker: the
> Tamil locale stays off until the native-speaker review lands
> (`THREAT-MODEL.md` §6.1).**

**test-qa starts: with S1, not after it.** Owns `tests/e2e/**`,
`tests/a11y/**`, `tests/contract/**`. First deliverables:
`test_deletion.py` (written from `DATA-MODEL.md` §10.3 **without reading the
implementation**), the auth matrix, and the a11y harness.

**code-review starts: at S0's first PR.** Owns no files. Reviews every PR.

**platform-sre: created now, dormant until S8.** Does not start, does not
review, does not comment, until infrastructure work begins.

### The parallel plan for the first three slices

| | backend-developer | frontend-developer | test-qa |
|---|---|---|---|
| **S0** | skeleton, core, gate, jobs, audit, guard tests, **service stubs** | *(waits; may scaffold `templates/base.html` + import `design/tokens.css`)* | a11y harness, e2e harness |
| **S1** | accounts services, age (**no DOB stored**), consents, deletion, purge job, **the three copy-enforcement tests** | sign-in, age, consent, profile, delete, legal pages (**`handover-guidance`**), EN strings + TA drafts, **the three locale manifests** | `test_deletion.py`, `test_no_dob_persisted.py`, auth matrix, a11y S1 (EN) |
| **S2** | catalog, listings, photos, moderation queue, price trigger | sell flow, my listings, listing detail, wanted, **`/dev/states`** | listing journeys, EXIF, forbidden-copy, a11y S2 |
| **S3** | search, instrumentation, gate enforcement, **`notifications` + `notify()` + `match_scan`** | search UI, the three-truths empty state, gate page, **notification list** | gate journey (**including `match_scan` across a closed gate**), latency, LCP, a11y S3 |

No file appears in two columns in any row. That is the check.

**One new ownership boundary worth stating** (amendment A-9): frontend owns the
locale **manifests**, backend owns the **tests** that read them, and the
**reviewer named inside them is a human, not an agent.** Neither agent can both
write a sign-off and write the test that checks it.

---

## 4. Definition of done, per slice

A slice is done when **all** of these are true:

- [ ] Migration applied and reversible; `migrate` from empty succeeds.
- [ ] L1 service functions match `API-CONTRACT.md` §3 exactly.
- [ ] L2 and L3 both work; **L3 works with JavaScript disabled**.
- [ ] **One real journey exercised end to end through the actual UI, by a
      client that was served the pages.** Added 2026-10-22 and it is not a
      restatement of the line above. `CLAUDE.md` rule 9's own D-041 note
      records the reason: **"a suite of 835 tests passed while nobody had ever
      been served a page."** Every rule in that set is about claims and
      controls, **and the worst defects found since were at the seams between
      artefacts — a seam is specified nowhere, so no spec-first test reaches
      it.** This checkbox is the only thing in the project that does.
- [ ] Every new personal-data field has a `COMPLIANCE.md` §7 row, or an
      escalation raised.
- [ ] Instrumentation rows are written by the behaviour, not by a later job.
- [ ] EN strings complete and taken from `COPY-DECK.md`; no hard-coded English
      in a template. **TA strings drafted; a TA string is "complete" only when
      it has a reviewer-signed entry in `locale/ta/REVIEWED.toml`**
      (`THREAT-MODEL.md` §6.1).
- [ ] a11y: automated pass plus a keyboard-only walkthrough — **in English,
      and in Tamil once `i18n.ta_enabled` is on**. **The harness must assert
      it reached the page**: QA found its own harness covering **4 of 11
      pages**, because seven redirect without a session and a non-200 counted
      as a *skip* — **rule 12 inside the harness, reported as coverage for a
      whole slice.** It signs in now. **Consequence: S0's accessibility result
      was weaker than it read, and any a11y number is quoted with the count of
      pages actually reached.**
- [ ] Guard tests still green — **including the three copy-enforcement tests,
      unmodified**.
- [ ] Code Review approved by `code-review` — **not by the author**.
- [ ] QA green, with QA's tests written against the spec, not the code.
- [ ] **Red Team has reported, AFTER review and QA both passed.** Founder
      instruction, standing for every remaining slice. **A slice is not done
      until Red Team has reported** — reported, not "found nothing"; a clean
      report closes it. Findings resolve like any other gate's: **fixed, or
      carried with a tripwire that fires when the gap closes.** A critical
      objection it cannot get resolved **escalates to the founder** per its
      charter, and that path is not absorbed by this checkbox. See §4.1.
- [ ] `audit_log` rows exist for every state-changing action in the slice.
- [ ] Slice lead time and first-pass rate recorded (`METRICS.md` Delivery).

### 4.1 Red Team's per-slice pass — placement, scope, and two things it collides with

**Placement: after code review and QA, and I agree with it.** The reasoning
holds and the evidence is already in: **every defect the apparatus caught was
within an artefact, and every defect Red Team found was at a seam between
them.** Review asks *is this correct*; QA asks *does this match the
specification*; **Red Team asks what the strongest failure case is and whether
the thing is worth having** — and running it earlier would collapse it into a
third correctness review, which is the one thing this project demonstrably
does not need more of. Attacking an artefact two gates have already approved
is the point, not an inefficiency.

**Refinement 1 — this ADDS a touchpoint, it does not move the existing one.**
Red Team's charter already has it reviewing **every gate**, on the plan,
before the spend. That pass can still kill a slice before it is built, which
is the cheap place to do it. **The per-slice pass attacks what was actually
built.** The two are not in tension, and keeping both is what makes the
coordinator's scoping note affordable: a slice pass is **free to conclude the
slice is not worth having**, and **if it does, that conclusion is also a
finding about the gate that let it through** — which should be said in the
report, because a slice-level kill that the gate pass missed is the more
valuable half of the finding.

**Refinement 2 — the loop has to terminate.** If Red Team's finding is fixed,
the fix re-enters review and QA **for the fix only**, and Red Team re-reports
**on the fix only** — not a fresh full pass. Without that, three gates in
series with no scoping rule is an unbounded cycle, and the pressure to skip
the third would arrive within two slices.

**Collision with §0 rule 3a, resolved now rather than discovered.** The tree
freezes when a slice goes to review, because a measurement of a moving
artefact means nothing. **Red Team's pass is such a measurement, so the freeze
holds through it** — application code and other agents' test trees stay
frozen until Red Team reports. **It may write freely in `tests/redteam/**`
throughout, which is exactly why that tree exists** (§1, QA F21). The
freeze is on the artefact under measurement, never on the instrument.

**Scope, so the passes stay sharp rather than ritual.** Each pass is pointed
at *that slice's* strongest failure case, not at the apparatus in general.
**For S2 that is the listing surface meeting a real student:** a seller who
misdescribes; a photo that leaks location; **a price that means something
different to the two people reading it**; and the gate opening wider than
anyone intended now that there is finally something behind it to show.

**The rule on its tree stands:** a probe is not a regression test. When a
probe finds something real, the finding goes to the owning agent and the
**regression is written in that agent's tree**, not in `tests/redteam/**`.

> **Companion edit, routed to ceo-planning:** `.claude/agents/red-team.md` is
> ceo-planning's charter to maintain, and a standing founder instruction that
> does not reach the charter has the same problem this encoding was meant to
> fix — **it lives in one place and the agent reads another.** The charter
> wants the per-slice pass in its Deliverables, and the gate-versus-slice
> distinction above in its Authority.

---

## 5. What is not in this build order, and when it arrives

| Not built | Trigger |
|---|---|
| Direct swap UI | D-007 reversal (swap-only users shown to be the cheapest supply). Data model already supports it |
| General reading UI | D-007 reversal, **after** copyright exposure is reassessed (R-26) |
| Credits / wallet / balance of any design | Blocked by P12, D-003; counsel C9 dormant; R-20 may remove the option |
| Payments, escrow, custody | ADR-003. Founder payment-activation authority only |
| Settled price, Cash GMV | ADR-003 §2.5. **Not on any roadmap** |
| Reputation, ratings, reviews | Counsel C6 + a second campus |
| Multi-campus discovery UI | ADR-002 §6 step 1, on a second MoU |
| Postgres RLS | ADR-002 §6 step 2 |
| Institutional / B2B features | Only if the Rs 0 librarian probe succeeds — and N2's compliance surface reopens first |
| CI/CD to production, containers, HA | ADR-001 §6 |
| Any generative AI in listing creation | **A compliance change, not a feature** — route to `COMPLIANCE.md` §5.1 |

---

## 6. The known-unknowns this plan carries

Recorded so a developer never has to guess, and so nobody mistakes silence for
a decision.

1. ~~**No PRD and no journeys.**~~ **CLOSED 2026-10-21.** `product/PRD.md` and
   `product/JOURNEYS.md` exist. Five contract gaps were raised against the
   frozen contracts and all five were accepted — see the amendment log. The
   standing rule survives: product may change copy, ordering and emphasis
   freely; **anything that changes the state machine or the schema comes back
   to cto**, which is exactly the route CG-1 to CG-5 took and it worked.
2. ~~**No design system.**~~ **CLOSED 2026-10-21.** `design/SYSTEM.md`,
   `DIRECTIONS.md`, `COPY-DECK.md` and `design/tokens.css` exist. §3's note.
2a. **The Tamil locale is gated, not blocked.** Tamil strings are written in
   every slice; the locale is not offered to a student until a native speaker
   has signed off the three blocking classes. **This is the one genuinely open
   dependency in the plan, it is enforced by a test rather than by a promise
   (`THREAT-MODEL.md` §6.1), and it is recorded as accepted risk A9.** It needs
   a human the programme has not yet engaged — escalated below.
3. **`business_seller_flag` has no threshold.** Mechanism built, number unset
   (`DATA-MODEL.md` §11.5).
4. **`LISTING_REVIEW_ALL=true`** at pilot means every listing is human-reviewed.
   That is a support-minutes cost that lands directly on R-13 and D-009's
   reversal trigger. **It is the right default given R-26 and it should be
   measured, not assumed** — the `INTAKE` bucket in `support_work_log` is where
   it will show up, and turning it off is a one-line config change once the
   data says so.
5. **Rs 2.84/minute** (G1-MEMO O-4) is the conversion the analytics use. If the
   operator's loaded cost changes, one constant in
   `apps/analytics/sql/support.sql` changes.

---

## 7. Amendment log

| # | Date | Change to this plan | Source |
|---|---|---|---|
| — | 2026-10-21 | v1.0 | — |
| **A-1** | 2026-10-21 | S4 gains write-once `accepted_at`; **S5 gains `reschedule_handover`** | PRD CG-1 |
| **A-2** | 2026-10-21 | **Support tables move S6 → S5**, with the student help surface and the `close_ticket` guard | PRD CG-2 |
| **A-3** | 2026-10-21 | S5's `confirm_handover` closes matching `book_requests` | PRD CG-3 |
| **A-4** | 2026-10-21 | **`notifications` + `notify()` + in-app channel + `match_scan` move S7 → S3**; S7 keeps email, push, preferences, analytics | PRD CG-4 |
| **A-5** | 2026-10-21 | S1 drops `age_check_pending`; **no DOB is persisted**; age review reviews the account, not a date | PRD CG-5 |
| **A-6** | 2026-10-21 | S5 gains the relay and the relay-first guard on contact disclosure | cto's own gap |
| **A-7/A-8/A-9** | 2026-10-21 | S1 gains **three copy-enforcement tests + three locale manifests + `i18n.ta_enabled` default false**; S1 uses `handover-guidance`; S2 gains `/dev/states`; the design-system dependency closes | Design TR-8, `SYSTEM.md` §7.7–7.8 |
| **Q-1** | 2026-10-21 | **Three TASKS defects fixed:** CI/lint/types reassigned to **backend from S0** (§1 previously made CI dormant until S8 while S0 scoped it); **S0's "done when" corrected** to what S0 can produce, with the browsable dataset moved to S2; **four ownerless controls assigned to S1 backend** — CSP, `test_forbidden_response.py`, the error-shape renderer, `apps/core/p14.py` | QA-S0 B5 · REVIEW-S0 N1–N3 |
| **Q-2** | 2026-10-21 | **S0/S1 gain the gate write-guard trigger, the evidence-typing checks and the `active` condition**; S1 gains the anonymous-idempotency sentinel **before the first anonymous endpoint ships** | QA-S0 F3/B1/B2/B3 · REVIEW-S0 M0 |
| **Q-3** | 2026-10-21 | **S2 gains the gated default manager** (ADR-002 §2.3), retrofitting `users.is_seed` in the same commit. **ADR-003 §2.3's non-monetary word list clarified** (suffix-or-exact, plus `status`) — a vocabulary clarification, not a money widening, with the discriminating test written down. `email_domains` → `jsonb`; job claiming → compare-and-swap. **Anonymous idempotency specified as a partial unique index, and anonymous POSTs confirmed to require a key** (one exemption: the L3 `GET /auth/c/{token}`) | ENGINE-DIVERGENCE §9.1, §9.2, §9.6, §9.6a, §9.6b, §9.7 |
| **F-1** | 2026-10-21 | **S0 re-approval conditions written into S0** (p14 module + F6/F7 in one commit, the flush fixture, the gate completeness CHECK). **W1c's source grep and `test_forbidden_response.py` named as S1's first commit** — both were unwritten, so **two of W5's three controls were specification rather than code**. **The first PostgreSQL run becomes a named deliverable with a six-item checklist**, because the rework raised the count of unexecuted security-relevant SQL | QA-S0 v2.0 **F4, F5, F6, F7, F8, F9**, §6 |
| **R-1** | 2026-10-21 | **S2 scope and definition of done now carry the default-manager deferral as four checkable line items** — manager + `base_manager_name`, the reverse-relation test with its result recorded, the `all_objects` allow-list, and the R1/R2 regression assertions. *A deferral recorded only in a review is how an ownerless control becomes an unwritten one* | REVIEW-S0 §11 condition (a), passed through as binding |
| **R-2** | 2026-10-21 | **S0's CI contradiction resolved in backend's favour** (developer tooling, not infrastructure); Postgres reached via the CI service container at Rs 0, Docker not required. **S6 gains the R3 condition** on anonymous `response_body` | REVIEW-S0 N-items · **R3** |
| **E-1** | 2026-10-21 | **S2 gated on a PostgreSQL 16 reachable by the test suite** (CI service container, Rs 0 — not a founder spend). S0/S1 may finish on SQLite. Guard tests must run on both engines or be **skipped with a reason naming the engine** | `ENGINE-DIVERGENCE.md` §9 · ADR-001 §2.2 amendment |
| **A-10 … A-12** | 2026-10-21 | S0's guard tests grow: the **whitelist** money assertion, **frozen column lists** on four tables, metric-label and flag-reset tests. **These land in S0, before the tables they guard** — a guard added after the thing it guards was never tested | `COMPLIANCE.md` §4.3.2 (nine items, all accepted) |

**Net effect on the critical path: none.** Two slices gained work (S3, S5), one
lost it (S7), one lost a table (S1), and S0 gained four assertions. **Backend is
mid-S0, so every amendment lands ahead of the code that implements it** — which
is the outcome the "contracts before parallel work" rule exists to produce, and
it is worth noting that it held under seven incoming changes from three agents.
