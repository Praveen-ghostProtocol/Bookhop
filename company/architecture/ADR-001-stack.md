# ADR-001 — Stack

**Status:** Accepted · **Date:** 2026-10-21 · **Decider:** cto
**Supersedes:** nothing. **Superseded by:** nothing.
**Inputs:** `CLAUDE.md` §Engineering standard · `company/README.md` §1 ·
`decisions/DECISIONS.md` D-004, D-007, D-008, D-009 ·
`ops/INCORPORATION-AND-BLOCKERS.md` §2 (P1–P14), §3 (Gates A/B/C) ·
`evidence/COMPLIANCE.md` §1.5–1.7, §5.1–5.3, §7, §8 · `metrics/METRICS.md` ·
`risks/RISK-REGISTER.md` R-18, R-26, R-28.

---

## 0. Decision in one paragraph

**Django 5.2 LTS + PostgreSQL 16 + server-rendered HTML with htmx, as one
modular-monolith repository, served by gunicorn behind nginx on a single Linux
VM in an Indian region, with a Postgres-backed job queue and no Redis, no
Celery, no SPA build pipeline, no third-party error tracker and no SMS
vendor.** Student authentication is an emailed magic link against the campus
email domain, which collapses "account identity", "campus verification" and
"no password to steal" into one mechanism. Photos are stored on the VM's own
disk at pilot. Nightly `pg_dump` plus a media tarball, encrypted, pulled
off-box, with a **restore test that runs on the founder's Windows machine for
free**.

**The single strongest reason:** every statutory artefact BookHop must build
before it may show a listing to a real student — consent ledger, age-gate
audit trail, tombstone-plus-purge deletion, 24h/2h/3h/36h/7d takedown clocks,
repeat-infringer record, personal-data access log, moderation queue — is a
*back-office CRUD-and-audit problem*, and Django gives us migrations, an admin
console, per-object permissions, i18n (EN/TA), argon2 password hashing and
timezone-correct datetimes on day one. The alternative stacks all require us
to hand-build the staff console that Gate B's B6/B7/B11 depend on. **We are
not building a consumer app with some compliance bolted on; we are building a
compliance ledger with a small student-facing surface, and that is what
decides the stack.**

---

## 1. What this has to survive

Ranked by how hard each one constrains the choice. The constraint, not the
preference, picked the stack.

| # | Constraint | Source | Stack consequence |
|---|---|---|---|
| C1 | **180-day ICT system logs maintained within Indian jurisdiction**, NTP-synced to NIC/NPL | CERT-In No. 20(3)/2022-CERT-In, Directions (i) and (iv), in force 27 Jun 2022 — `INCORPORATION-AND-BLOCKERS.md` §0 | Hosting region must be in India. Rules out every PaaS without an Indian region (Fly, Render, Railway, Heroku, Vercel functions). |
| C2 | **6-hour breach notification** | same, Direction (ii) | We must be able to read our own logs fast and know the detection timestamp. Favours logs on a box we control over a vendor's dashboard. |
| C3 | **Never store a settled transaction price**; no PAN, no Aadhaar, no durable DOB | P14 (binding), D-009 | Needs a DB-level enforcement point: a CHECK/trigger plus a schema deny-list test. Any stack with a real migration system can do this; ORMs that let developers add columns casually without a reviewed migration cannot. |
| C4 | **Deletion is tombstone-plus-purge, never `DELETE FROM users`** | DPDP r.8(3) + r.6(1)(e) — `COMPLIANCE.md` §1.5, §1.6, §7 | Needs explicit, reviewable, transactional data-lifecycle code and a scheduled expiry job. Rules out BaaS platforms whose cascade-delete semantics we do not control. |
| C5 | **Takedown clocks: 2h / 3h / 24h ack / 36h / 7d dispose / 21-day hold** | IT Rules 2021 as amended G.S.R. 120(E) in force 20 Feb 2026; Copyright Rules r.75 — `COMPLIANCE.md` §5.1, §5.3 | Needs a staff console with SLA timers and a reliable minute-granularity scheduler. A free admin framework is worth real money here. |
| C6 | **Mid-range Android over 3G, WCAG 2.2 AA, EN + TA** | `CLAUDE.md` §Engineering standard | Server-rendered HTML with progressive enhancement. A ~200 KB JS framework bundle is a cost we cannot justify and an accessibility liability we would have to re-earn. Rules out the SPA default. |
| C7 | **Solo-or-tiny team, Windows development** | D-009 context; this brief | One language for application code. A stack that needs Node *and* Python *and* a container runtime for local dev costs a day a week in yak-shaving. |
| C8 | **Rs 16,500 approved for the whole programme, no infrastructure budget, spend is a founder authority** | D-007 item 2, D-008 ledger | Running cost must be low *and* the build must cost Rs 0 until Gate B. Rules out managed Postgres, rules out AWS-managed anything at pilot. |
| C9 | **This may be thrown away** | D-009, R-21 | Prefer a stack where the *data model* is the durable asset and the framework is replaceable. Postgres is the asset. |
| C10 | **Modular monolith, no premature microservices**; multi-campus/multi-city in the model from day one | `CLAUDE.md`; this brief | One repo, one deployable, one database, app-level module boundaries. See ADR-002. |
| C11 | **Every vendor touching personal data needs a signed DPA** | DPDP r.6(1)(f); Gate B item B15 | **Each third-party service is a legal document the founder must sign.** Minimising vendors is not an aesthetic preference here; it is a reduction in blocking legal work. This argument killed Sentry, an SMS gateway and Google Analytics. |

---

## 2. The decision

### 2.1 Language and framework — **Python 3.12 + Django 5.2 LTS**

Django 5.2 is the current LTS line, supported into 2028, which outlives any
plausible pilot. We pin to LTS and do not chase feature releases.

What we take from the framework and therefore do not write:

| Need | Django gives us | What we would otherwise build |
|---|---|---|
| Migrations with a reviewable diff (C3) | `makemigrations` / `migrate`, squashing, `RunSQL` for triggers | A migration tool, or hand-rolled SQL files |
| Staff console for moderation, takedown clocks, age review, support timers (C5) | `django.contrib.admin` with custom ModelAdmins and actions | Several weeks of internal CRUD UI, which is exactly the work Gate B blocks on |
| EN/TA (C6) | `gettext` + `.po` files, `{% translate %}`, locale middleware, `LANGUAGE_CODE` fallback | An i18n layer |
| Password hashing for staff accounts | argon2 via `django.contrib.auth.hashers` | A crypto decision we should not be making |
| CSRF, clickjacking, secure cookies, HSTS, SQL-injection-safe ORM | Middleware and the ORM by default | ASVS V1/V3/V13 basics by hand |
| Timezone-correct datetimes (every SLA clock depends on this) | `USE_TZ=True`, aware datetimes everywhere | A class of bug that would be found by a regulator |
| Per-object staff permissions, group-based access | `auth` permissions + groups | ASVS V4 access control |

**The admin is the load-bearing reason.** Items B6, B7, B11 and C5/C6 of
`INCORPORATION-AND-BLOCKERS.md` §3 are all staff tooling. In a stack without
an admin framework the Gate B critical path grows by the time it takes to
build a staff console, and that console is the least interesting code in the
project.

> **AMENDMENT 2026-10-22 — the Django admin is NOT being used, and this
> paragraph was one of my stated reasons for choosing the stack. Facing that
> rather than letting it pass.**
>
> Backend escalated with four measured reasons, and they compound rather than
> repeat: **its log table carries a column that fails the money whitelist and
> is not ours to rename** — rung 1 is structurally unavailable for vendor code,
> and exempting a third-party column would widen the money guard **for code we
> do not control**, which is the one place an exemption cannot be audited;
> **two of its columns are free text with no data-model or inventory row**, and
> `COMPLIANCE.md` §7's standing rule is that a personal-data field without a
> row is a defect by definition; it pulls in an app this ADR excludes; and its
> **two-factor requirement cannot ship** because the package is uninstalled
> with no network. **Accepted.**
>
> **What this costs the stack argument, stated plainly: one of the four
> reasons I gave for Django has not materialised.** The choice still holds on
> the other three — migrations with a reviewable diff, i18n for EN/TA, and the
> security defaults — **but anyone re-reading §2.1 should know that the
> strongest-sounding reason in it is now the one that did not pay.**
>
> **What replaces it, and when.** S2's moderation queue ships as a **service
> plus a management command**, which is sufficient while every listing is seed
> data. **It is not sufficient for Gate C:** `JOURNEYS.md` J2-staff specifies a
> queue ordered by time remaining on the shortest applicable clock, with a
> visible running timer — and **a management command cannot show a timer to
> the person being timed.** So **the staff console becomes a first-party
> surface in `web/`, owned by frontend, scheduled before Gate C and not
> before.** That is more work than the admin would have been, and it is the
> honest consequence of the four findings rather than a preference.

### 2.2 Database — **PostgreSQL 16, one database, one schema**

- Transactional storage with real constraints: partial unique indexes (which
  is how we prevent double-booking — see `API-CONTRACT.md` §6), CHECK
  constraints, triggers (which is how P14's immutable asking price is
  enforced), `citext`, `jsonb`, and `pg_trgm` for title search.
- `pg_dump` is a boring, text-inspectable, restorable backup format. The
  restore test runs on Windows against a local Postgres in Docker at Rs 0.
- It is the artefact that survives a rewrite (C9).

**Search: `pg_trgm` GIN index on title + exact ISBN-13 lookup. No
Elasticsearch, no Meilisearch, no OpenSearch.** v1 is edition-locked
prescribed textbooks, so **the primary discovery path is an exact ISBN-13
match**, and the secondary path is a trigram-fuzzy title search over at most a
few thousand rows.
`# ponytail: pg_trgm over one campus's listings. Ceiling ~100k listings or
the moment we need relevance ranking, synonyms or Tamil stemming; upgrade
path is Postgres full-text with a Tamil configuration first, a dedicated
search engine only if that fails p95 search latency.`

> **Amendment 2026-10-21 — ruling on `ENGINE-DIVERGENCE.md`'s escalation.**
> **§2.2 is NOT amended: production is PostgreSQL 16.** Backend found that the
> machine S0 was built on has neither PostgreSQL nor Docker, selected the
> engine from an environment variable, and documented every divergence rather
> than hiding it. **That was the right call and the document is better than the
> problem that caused it** — it found a hole nobody else had: row triggers do
> not fire on `TRUNCATE`, so the `audit_log` append-only guarantee had a
> Postgres-only gap that SQLite could never have revealed. That is a real
> defect in my §8 design, caught by writing the divergence down.
>
> **Ruling, in three parts:**
> 1. **Accepted as a temporary divergence for S0 and S1 only.** Neither slice's
>    load-bearing constraints are engine-specific.
> 2. **S2 may not start until the test suite can reach a PostgreSQL 16.** Not a
>    preference — **P14's price-immutability trigger (ADR-003 §2.2) is
>    unverifiable without it** (`ENGINE-DIVERGENCE.md` §3.9), and P14 is the
>    single most important schema constraint in v1. S4's double-booking guard
>    (§5 there) is the second. Shipping either on an unverified trigger would
>    mean the control exists in prose only.
> 3. **The cheap route is CI, not the founder's machine.** A Postgres service
>    container in CI costs **Rs 0** and runs the Postgres half of every trigger
>    and concurrency test on every push — so this is **not** a founder spend
>    escalation and should not be routed as one. A local install stays available
>    as a convenience, not a dependency. **Backend: take the CI route first.**
>
> Two consequential knock-ons, both already handled above: ADR-003 §2.3's W4
> corrects the schema test to introspect engine-neutrally, and the analytics
> SQL in §9 of the data model (`percentile_cont`, `FILTER`, `date_trunc`) is
> **declared Postgres-only** — those tests are skipped with a stated reason on
> SQLite rather than rewritten twice.
>
> **Standing rule this establishes:** where a constraint is enforced by the
> database, the test for it must either run on both engines or be **skipped
> with a reason that names the engine**. A silently-passing guard is worse than
> no guard, because it is reported as coverage.
>
> **Addendum 2026-10-21 — the TRUNCATE guard versus Django's own flush
> (REVIEW-S0 M5).** Django 5.2's `postgresql` backend emits
> `TRUNCATE "t1", "t2", …` from `sql_flush`, so the `audit_log_no_truncate`
> statement trigger fires in **every** `transactional_db` /
> `TransactionTestCase` teardown. The collision lands precisely on
> `tests/api/test_double_booking.py`, which must be transactional to commit at
> all and which `ENGINE-DIVERGENCE.md` §5 calls the single most important
> correctness property in BookHop. **So the first Postgres box presents a
> choice between a working harness and the guard — and the tempting fix at that
> moment is to delete the guard.**
>
> **Ruling: the guard stays; the harness yields.** The trigger raises unless
> `current_setting('bookhop.flush_ok', true) = 'yes'`, a session GUC set **only
> by a pytest teardown fixture**. Not `ALTER TABLE … DISABLE TRIGGER`: that
> needs table ownership and disables the guard for every session for as long as
> it is off, which is a worse trade than a session-scoped variable.
> **Correction 2026-10-21 (QA-S0 F9) — I specified a test that cannot be
> written, and I am withdrawing it.** This addendum said *"a test asserts the
> GUC is unset under production settings, so the escape cannot exist on a
> deployed box."* **That is not achievable and the reasoning was wrong: a
> custom GUC is settable by any role in any session, `current_setting` reads
> whatever that session set, and Django settings have no say in it.** No
> mechanism can make production refuse the `SET`.
>
> **What is actually true, stated as the scope it rests on rather than as a
> control it does not have:** the escape is gated by **nothing**, and that is
> acceptable **only** because direct SQL is already outside the protected scope
> under `THREAT-MODEL.md` §4 B5/B6 and accepted risk A8. **The guard stops
> Django's own `sql_flush` and an accidental TRUNCATE; it does not stop a
> determined session, and it was never going to.**
>
> **What QA did verify, by reading the migration rather than the report
> describing it, and it holds:** two-argument
> `current_setting('bookhop.allow_flush', true)` so an unset GUC yields NULL;
> the test is `= 'yes'` so NULL falls through to `RAISE EXCEPTION` — **deny by
> default**; none of `IS DISTINCT FROM`, `<>`, `!=`, `IS NULL` or `COALESCE`
> appears in the guard body, each of which would have inverted it; and the
> escape appears in **exactly one** plpgsql body, so UPDATE and DELETE have no
> escape. **An escape in the append-only guard would have made `audit_log`
> mutable with one `SET`.** The construction is sound; it was my claim *about*
> the claim that was wrong.
>
> **The fixture this requires does not exist and is three lines.** `tests/conftest.py`
> must `SET bookhop.allow_flush = 'yes'` for a Postgres session, or the first
> Postgres run of S4's transactional `test_double_booking.py` fails in teardown
> — **and the tempting fix at that moment is deleting the guard**, which is the
> failure mode the charters' last hard rule names. Assigned to backend as an
> S0 re-approval item; it is not QA's file to write.
>
> Default remains `django_db` (transaction rollback) everywhere; a test needing
> real commits declares it and the fixture does the rest.
>
> `ENGINE-DIVERGENCE.md` §7.1 currently states the opposite of the truth — that
> row triggers do not see TRUNCATE so teardown is clean on Postgres — and
> **that correction is backend's to make in its own file**; it is recorded here
> because the ruling is mine. Deleting a check under schedule pressure is the
> failure mode the charters' last hard rule names, and this is the first live
> instance of it.

**SQLite was seriously considered and rejected.** At 200 users it would work.
It was rejected on three specific grounds, not on taste: (a) the audit log,
moderation queue and job runner all want concurrent writers, and SQLite's
single-writer lock turns a 36-hour takedown clock into a contention problem on
the worst possible day; (b) we need `jsonb`, trigram indexes and partial
unique indexes, and emulating them costs more code than Postgres costs money;
(c) the backup story we have to *demonstrate* at G3/G4 is easier to argue with
`pg_dump` plus a tested restore than with a file copy of a live database.
Postgres is also what we would migrate *to*, so starting there avoids a
migration we can already predict.

### 2.3 Front end — **Django templates + htmx 2.x, progressive enhancement, PWA shell**

- **Every core flow works with JavaScript disabled**, as plain HTML forms
  posting to Django views. htmx adds fragment swaps on top; it is an
  enhancement, never a requirement. This is the cheapest route to C6 (3G,
  mid-range Android) and the cheapest route to WCAG 2.2 AA, because semantic
  HTML with real form controls and real page navigation starts compliant
  instead of being made compliant.
- Native platform features over libraries: `<input type="date">` for the age
  gate, `<input type="file" accept="image/*" capture>` for listing photos,
  `<details>` for disclosure, CSS for layout. No date-picker library, no
  component library, no CSS framework.
- **PWA = a `manifest.webmanifest` plus a ~40-line service worker** caching the
  app shell, the stylesheet and an offline page. Nothing else. No Workbox.
  Installability and an offline fallback is the whole requirement; offline
  *writes* are explicitly out of scope (see §6).
- Web Push for notifications via VAPID, which needs **no vendor and no DPA**
  (C11), degrading to in-app and email.
- CSS: one hand-written stylesheet with custom properties as design tokens.
  **Blocked dependency:** `design/SYSTEM.md` does not exist yet. The frontend
  agent owns a provisional token file and swaps the values when the design
  system lands. Escalated — see §7.

### 2.4 Background work — **a `jobs` table and one management command, run by cron**

We need: reservation expiry, handover-window transitions, the 72-hour leakage
follow-up, SLA-breach alerts, the retention/purge expiry job, the quarterly
IT-Rules r.3(1)(c) user reminder, email and push sending, and the weekly
metrics export. All of it is minute-granularity at worst and low-volume.

```
jobs(id, kind, payload jsonb, run_after, attempts, max_attempts,
     locked_at, locked_by, completed_at, failed_at, last_error)
```

A single `python manage.py run_jobs --once` claims due rows, runs a handler
registered by `kind`, retries with backoff, and exits. systemd timer every
minute.

**Claiming mechanism — amendment 2026-10-21, accepting backend's
recommendation (`ENGINE-DIVERGENCE.md` §4.3, §9 item 2).** v1.0 specified `SELECT ... FOR UPDATE SKIP LOCKED`, which is
**silently a no-op on SQLite** — it parses and locks nothing, so a divergence
would have been carried undocumented. The specification is now a
**compare-and-swap UPDATE**: claim by `UPDATE jobs SET locked_at=now(),
locked_by=? WHERE id=? AND locked_at IS NULL`, acting only if one row is
affected. **The at-least-once and single-claim properties are identical**, it
is engine-neutral, and it needs no row lock at all. `SKIP LOCKED` returns as a
Postgres-only optimisation **if and when more than one worker is actually
run** — which §2.4's own ceiling note already anticipates — and not before.

**No Celery. No Redis. No RQ. No APScheduler.** Celery plus a broker is two
more processes, two more failure modes, one more thing to monitor and a
second place state lives — for a workload of a few hundred jobs a day.
`# ponytail: single-process polling job runner, ~90 lines, one-minute
granularity, at-least-once delivery. Ceiling: sub-second scheduling, or more
job throughput than one worker handles. Upgrade path: run N workers (SKIP
LOCKED already makes that safe), then a real broker only if that fails.`

Rate limiting and the small amount of caching use **Django's database cache
backend**, for the same reason: it removes Redis.
> **Amendment 2026-10-22 — backend's S1 rate-limiting deviation is accepted,
> including its rule-13 rename.** §2.4 specified a DB-cache fixed-window
> limiter; backend deviated and renamed rather than exempting a colliding
> name, which is **order-of-resort step 1** and the preferred resolution.
> Accepted on the standing condition that applies to every deviation from a
> frozen contract: **it is recorded in `ENGINE-DIVERGENCE.md` with a row, not
> carried silently.** The property that matters is unchanged — a per-key
> window enforced server-side, no Redis, and the limits in
> `API-CONTRACT.md` §2.4 are the contract of record.

`# ponytail: DB-backed fixed-window rate limiter. Ceiling: a few hundred
req/s, and window edges are sloppy. Upgrade path: Redis token bucket.`

### 2.5 Authentication — **emailed magic link for students; password + TOTP for staff**

Students have **no password column at all**. Sign-in posts an institutional
email address; we send a single-use token (10-minute expiry, hashed at rest,
bound to the requesting user-agent family, consumed on first use).

This is one decision that pays four separate dividends:
1. **Campus verification and account identity become the same mechanism.** The
   email domain *is* the campus evidence, so `campus_verification_evidence`
   (data inventory row 6) is satisfied with a boolean, a method and a
   timestamp and we store no enrolment artefact at all.
2. **Credential stuffing and password reuse disappear** — there is nothing to
   stuff. Data inventory row 4 (password) applies to staff only.
3. **No SMS vendor**, so no per-message cost, no OTP gateway DPA (C11) and no
   phone number required at signup.
4. It is less code than a password flow with reset, lockout and strength
   rules.

**Cost:** account access depends on the institution's mail working, and a
student who loses institutional email access loses the account. Accepted at
one campus; the recovery path at pilot is a logged staff-assisted
re-verification, which is also the age-review touchpoint.

Staff accounts use the Django admin, so they have argon2 passwords **plus a
mandatory TOTP second factor** (`django-otp`, one small dependency, admin
integration included). This is a named control against admin insider risk —
see `THREAT-MODEL.md` §5.8.

### 2.6 Media — **the VM's own disk at pilot, not object storage**

Listing photos are resized to a max edge of 1600px, re-encoded, **EXIF
stripped at upload** (data inventory row 9), and written to a local directory
served by nginx with `Cache-Control: private`. At one campus with a few
thousand listings and ~3 photos each at ~150 KB after re-encode, this is
single-digit GB.

This removes an object-storage vendor *and* its DPA *and* a CDN *and* the
question of which region the bucket is in (C1, C11). The upgrade path is real
and short.
`# ponytail: local disk media. Ceiling ~15 GB or the first time we need a
second app server. Upgrade path: an Indian-region S3-compatible bucket plus a
signed-URL helper — one storage backend swap, because all media access
already goes through one module.`

### 2.7 Deployment — **one Linux VM in an Indian region, gunicorn behind nginx, deployed by one script**

- Ubuntu LTS, Postgres and the app on the same box at pilot.
- `chrony` synchronised to **NPL / NIC NTP** (CERT-In Direction (i)).
- Structured JSON application logs to disk, `logrotate` with a **one-year**
  retention (the longest applicable floor — CERT-In 180 days is subsumed by
  DPDP r.6(1)(e) and r.8(3)'s one year; `COMPLIANCE.md` §5.2).
- Deploy = `git pull && pip install -r requirements.txt && manage.py migrate
  && systemctl restart`, in one shell script, with the previous commit SHA
  recorded so rollback is `git checkout <sha>` plus a restart. See `INFRA.md`.
- **No Docker in production.** One box, one Python virtualenv, systemd units.
  Docker *is* used in local development on Windows, for Postgres only.
  `# ponytail: scripted VM deploy. Ceiling: a second app server, or a
  blue/green requirement. Upgrade path: containerise then, not now.`

### 2.8 The whole dependency list

Application: `django`, `psycopg[binary]`, `gunicorn`, `pillow` (resize + EXIF
strip), `argon2-cffi`, `django-otp` (staff 2FA), `pywebpush` (VAPID),
`boto3` **only** when media moves off-box. Front end: `htmx` (vendored, no
build step). Dev/test: `pytest`, `pytest-django`, `playwright` (QA e2e +
accessibility), `ruff`, `mypy`.

**That is the list.** Anything added to it is a code-review conversation and,
if it processes personal data, a founder signature (C11).

---

## 3. What was considered and rejected

| Option | Why it was plausible | Why rejected |
|---|---|---|
| **Next.js / React SPA + Node API + Prisma** | The industry default; large talent pool; good DX | Four rejections, any one sufficient. (a) **C6**: a framework bundle plus hydration on a mid-range Android over 3G is a self-inflicted LCP problem, and we have a p75 LCP metric to hit. (b) **C5**: no admin framework, so the entire staff console — moderation queue, SLA timers, age-review queue, support stopwatch — is bespoke, and that is the Gate B critical path. (c) **C7**: two runtimes, two package managers, a build step, and Node native-module pain on Windows. (d) Accessibility and i18n both become libraries and discipline rather than defaults. |
| **Ruby on Rails 8 + Postgres + Hotwire** | A genuinely close call. Equivalent batteries, better defaults in places, Solid Queue removes Redis the way our `jobs` table does, and Hotwire is the same progressive-enhancement bet as htmx | Rejected on two margins, both narrow and both about *this* team: **Windows is a second-class Rails development platform** (native extensions, `tzinfo-data`, WSL-or-bust in practice), and Django's `contrib.admin` is a stronger out-of-the-box staff console than Rails has without adding one. If the founder's team were Ruby-fluent this ADR would flip, and it would not be a mistake. Recorded as the runner-up. |
| **Supabase / Firebase (BaaS)** | Fastest to a working prototype; auth, storage and a database for ~Rs 0 at this scale | Rejected primarily on **C1 and C4**. We would be asserting to CERT-In that 180 days of ICT system logs are maintained in Indian jurisdiction on the strength of a vendor's region selector and its control-plane logging, which we cannot inspect and did not read. Separately, **C4**: tombstone-plus-purge with per-field retention and a one-way pseudonymisation step is precisely the logic BaaS cascade semantics make hard to reason about, and "delete my account" is the one operation we cannot afford to get subtly wrong. Also C11 (a DPA with a foreign processor becomes blocking) and C9 (vendor lock-in on the asset we most want to keep). |
| **AWS Mumbai, managed: RDS + ECS/Fargate + S3 + CloudWatch** | ap-south-1 satisfies C1 cleanly; managed Postgres with PITR is a genuinely better backup story than ours | Rejected on **C8**. The floor for RDS plus a Fargate task plus a load balancer is roughly Rs 5,000–8,000/month `ASSUMPTION: list-price arithmetic, not quoted; verify on the AWS calculator before any spend`, against a programme with Rs 2,600 unallocated. We would be spending an order of magnitude more than the pilot's entire remaining budget on infrastructure for ~200 users. Revisit at multi-campus, where the PITR and the managed upgrades start to be worth the money. |
| **.NET 9 + ASP.NET Core + EF Core on Azure India** | Best-in-class Windows development story (C7); Azure has Indian regions (C1) | Rejected on **C5 and C8**: no admin scaffold comparable to Django's, so the same bespoke-staff-console problem as Next.js, and Azure's floor for App Service plus Azure Database for PostgreSQL is in the same range as AWS. No offsetting advantage for a solo team that is not already .NET-fluent. |
| **PHP + Laravel** | Cheapest possible hosting, excellent shared-hosting story in India, Filament gives an admin panel | Serious contender on cost. Rejected because Filament is an added dependency stack (Livewire + Alpine + Tailwind) rather than a framework default, which reintroduces a build step and the C11 dependency-count argument; and because the team's Python familiarity is the tiebreak once the framework capabilities are this close. |
| **Celery + Redis** for background work | The default Django answer | Rejected per §2.4: two extra processes and a second state store for a few hundred jobs a day. |
| **Sentry / any hosted error tracker** | Would genuinely help a solo operator | Rejected on **C11 and C1**: stack traces and request context contain personal data, which makes the vendor a Data Processor needing a signed DPA (Gate B item B15) and puts error data outside India. Replaced by structured logs on the box plus a daily digest email to the on-call address. `# ponytail: no error aggregation UI. Ceiling: when log-grepping stops finding things. Upgrade path: self-hosted GlitchTip on the same box — same DPA-free property.` |
| **Google Analytics / any analytics SDK** | Free, familiar | Rejected. It is a US processor on every page view, a consent-banner problem, and **it cannot answer any metric in `METRICS.md`** — match rate, time to match and support minutes all come from our own tables. A third-party pageview counter would add legal surface and measure nothing we need. |
| **SMS OTP (MSG91, Twilio, etc.)** | The Indian default for student signup | Rejected per §2.5: a per-message cost, a vendor DPA, and a phone number we then have to retain, hash and purge — all replaced by a campus email domain that we needed to verify anyway. |
| **A native Android app** | Better install story on campus | Rejected. Two codebases, a Play Store review loop, and a store listing that would publicly describe a service the company is not yet legally permitted to operate (Gate B). The PWA is installable. |
| **Microservices, or a separate "compliance service"** | Tempting because the compliance surface is large | Explicitly forbidden by the engineering standard, and wrong anyway: the audit trail must be transactionally consistent with the thing it audits, which is exactly what a service boundary destroys. |

---

## 4. Running cost at pilot scale, and who pays

Full workings, assumptions and the Rs 0 development path are in
`COST-MODEL.md`. Headline:

| Configuration | Monthly | What it is for |
|---|---|---|
| **Tier 0 — build and test** | **Rs 0** | Everything runs on the founder's Windows machine: Postgres in Docker, Django dev server, seed data. **No cloud spend is needed to build, test and QA every slice through Gate B.** |
| **Tier 1 — minimum pilot** | **≈ Rs 630 / month** | 1 vCPU / 1 GB VM in an Indian region, provider weekly snapshots, nightly encrypted dump pulled to the founder's machine, transactional email. |
| **Tier 2 — recommended pilot** | **≈ Rs 1,750 / month** | 1 vCPU / 2 GB VM, provider snapshots, **off-site managed object storage for nightly encrypted backups** (so a backup survives the founder's laptop dying), transactional email, domain. |

**Who pays: the founder. It is not approved.** Infrastructure spend is a
reserved founder authority (`README.md` §2) and D-007's Rs 16,500 is fully
allocated (Rs 2,600 unallocated, and incorporation at Rs 8,000–20,000 is
already outside the envelope per D-008). **Escalated, not assumed** — see §7.
Tier 2 at Rs 1,750/month is roughly Rs 21,000/year, which is larger than the
entire approved programme budget, and the founder should see that number
before the first slice is deployed anywhere.

**Every figure in `COST-MODEL.md` is tagged `ASSUMPTION:` with the URL to
verify it on.** None was re-verified today; this agent did not browse.

---

## 5. ~~The one constraint this stack does not cleanly satisfy~~ — **RESOLVED 2026-10-21, in our favour**

> **Privacy-compliance has ruled. Uncertainty drops from MODERATE to LOW; the
> §8 reversal trigger is NOT fired; `INFRA.md` §2's hold is released; do not
> move providers and do not spend the hedge.** Deployment is blocked only on
> founder spend approval (§7.1), which is not a compliance matter.
>
> | Question | Answer |
> |---|---|
> | Does an Indian region of a foreign-owned provider satisfy Direction (iv)? | **Yes** |
> | Must we move to an Indian-incorporated provider? | **No** |
> | Spend money or time on the hedge? | **No** |
>
> **And the reason is worth internalising, because it credits a decision made
> for a different purpose.** Direction (iv) binds *BookHop* to maintain
> *BookHop's* logs. Because **§3 rejected Sentry, hosted APM and third-party
> analytics, every log we owe lives on a filesystem we control** — compliance's
> phrase is that *"the nationality of the landlord is immaterial when the
> filing cabinet is ours."* Had we shipped logs to a vendor's SaaS log product
> the question would be live and harder, not because a region selector is
> untrustworthy but because **producibility in a reasonable time would depend
> on someone else's support queue.**
>
> So §3's rejection of hosted error tracking — argued there on DPA-count and
> cost grounds — turns out to be **the control that settles CERT-In residency**,
> and §3's rejection of BaaS was right for a better reason than it gave: not
> that the region selector is untrustworthy, but that **we would not have been
> the entity in possession of the logs.** The dependency-minimisation argument
> paid a dividend it was not making a case for.

The original analysis is kept below, unamended, because the reasoning is what
made the question answerable.

### 5.1 The original open question (superseded)

**C1, "logs maintained within the Indian jurisdiction", on a foreign-owned
cloud provider's Indian region.** CERT-In Direction (iv) requires ICT system
logs to be "maintained within the Indian jurisdiction". A VM in a Bengaluru or
Mumbai region of a US-incorporated provider puts the *bytes* in India; whether
that satisfies *maintenance within the jurisdiction* when the operator is
subject to foreign process is **not settled by anything I read**, and
`INCORPORATION-AND-BLOCKERS.md` §0 does not address it either.

- **My position:** bytes-in-India is the ordinary reading and is defensible at
  pilot scale.
- **Uncertainty: MODERATE.** This is my reading, not a sourced conclusion.
- **The cheap hedge, if privacy-compliance disagrees:** use an
  Indian-incorporated provider for the same money (E2E Networks, CtrlS and
  similar operate Indian-region VMs in the same price band
  `ASSUMPTION: price band not quoted; verify before committing spend`). The
  stack is provider-agnostic — one VM, Postgres, systemd — so this is a DNS
  change and a restore, not a re-architecture. **That portability is itself a
  reason for choosing a plain VM over a managed platform.**
- **Action: routed to privacy-compliance as a question, not resolved here.**
  Nothing is deployed anywhere until it answers, and nothing is blocked
  meanwhile because Tier 0 is local.
  → **Answered 2026-10-21. See §5 above. The hedge is not needed.**

---

## 6. Deliberately not built in v1

Stated here so nobody has to guess, with the trigger that should bring each
one back. Scope items (swap, general reading, credits) are in
`DATA-MODEL.md` §12; this list is the *technical* omissions.

| Not building | Why | Add when |
|---|---|---|
| Offline **writes** in the PWA | Conflict resolution on a reservation is a distributed-systems problem for a feature nobody asked for | Never, unless field evidence shows campus connectivity actually drops mid-flow |
| Any payment integration, wallet, escrow, credit or balance | D-004, D-007, D-009 — and ADR-003 | Only on founder authorisation after payment-provider and compliance review |
| Reputation score / star ratings / free-text reviews | Increases "vouching" exposure (R-16, `COMPLIANCE.md` §2.5) and there is no data to compute it from at one campus | After counsel question C6, and not before a second campus |
| Redis, Celery, a message broker | §2.4 | When one job worker measurably cannot keep up |
| A search engine | §2.2 | When p95 search latency or relevance fails against real listings |
| Hosted error tracking, APM, analytics SDK | §3 (C11) | Self-hosted on the same box if log-grepping stops working |
| SMS / OTP | §2.5 | If a second campus has no usable institutional email |
| Native mobile apps | §3 | Not before G4, if ever |
| Multi-region, read replicas, PITR, autoscaling | Disproportionate to ~200 users | At multi-city, which is when ADR-002's upgrade path also triggers |
| CI/CD to production | One `deploy.sh` run by a human is auditable and sufficient | When there is more than one person deploying |

---

## 7. Escalations raised by this ADR

1. **To founder, via ceo-planning — infrastructure spend.** Rs 0 to build;
   Rs 630–1,750/month from Gate B. Not approved, not committed. No deployment
   to any host occurs until it is. `COST-MODEL.md` §5 is the packet.
2. ~~**To privacy-compliance — §5.**~~ **CLOSED 2026-10-21: yes, it satisfies
   Direction (iv). Uncertainty LOW. No provider move, no hedge spend.**
3. ~~**To ceo-planning — missing Phase B inputs.**~~ **CLOSED 2026-10-21.**
   `product/PRD.md`, `product/JOURNEYS.md`, `design/DIRECTIONS.md`,
   `design/SYSTEM.md`, `COPY-DECK.md` and `design/tokens.css` all now exist.
   Five contract gaps came back from product and two from design; all were
   accepted and amended (see each document's amendment log). **G2's entry
   criteria are now satisfiable.**
4. ~~**To privacy-compliance — one new personal-data field.**~~ **ANSWERED
   2026-10-21** along with four others. Compliance **refused** the proposed
   basis for `messages.contact_pattern_flag` — correctly — and added a
   requirement the schema had missed; see `DATA-MODEL.md` A-10.
5. **To design-director — the negotiability limb.** ADR-003 §2.5a: the s194-O
   position now rests partly on copy making it visibly true that price is
   negotiated between the parties. **A schema cannot carry that limb.**

## 8. Reversal triggers

- **p75 LCP on a mid-range Android over 3G fails** after template and image
  work: revisit the front end, in the direction of *less* client code, not a
  framework.
- **One job worker cannot keep up**, or a clock SLA is missed because of job
  latency: add workers first (SKIP LOCKED already permits it), a broker only
  if that fails.
- ~~**Privacy-compliance rejects §5**: move the VM to an Indian-incorporated
  provider.~~ **NOT FIRED — compliance confirmed the reading on 2026-10-21.
  This trigger is spent; do not act on it.**
- **Second campus onboards and campus email is unusable there**: revisit §2.5
  only, not the stack.
- **The pilot is killed** (R-21, D-009 reversal trigger): the artefact worth
  keeping is the Postgres schema and the metric SQL. Nothing else in this ADR
  is load-bearing after that point, which is the intended property.
