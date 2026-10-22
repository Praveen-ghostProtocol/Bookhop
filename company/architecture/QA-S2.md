# QA-S2.md — QA's S2 pass: the denormalised columns, the price trigger, and a coverage regression

**Owner:** test-qa · **Version:** v1.0 · **Date:** 2026-10-22
**Under test, frozen:** backend `49b7dc2`, frontend `59ad6cf`.
**Engines:** PostgreSQL 16.15 via `set -a && . ./.env && set +a` with
`BOOKHOP_TEST_DB_NAME=bookhop_qa_s2`; SQLite via `BOOKHOP_DB_ENGINE=sqlite`.
**Read with:** `DATA-MODEL.md` §3, §6.1 · `API-CONTRACT.md` §2.2, §2.5, §4.1,
§5.2 · `ADR-002` §2 (amendment 2026-10-22), §4 · `ADR-003` §2.1–2.3 ·
`THREAT-MODEL.md` §6 · `INFRA.md` §3 · `TASKS.md` §2 S2, §4.

---

## VERDICT

**S2 does not pass. One blocking finding set, five defects, one escalation.**

The slice is in much better shape than that sentence sounds. The price
trigger — P14's first executable control — survived every attack QA could
write, including the ones its author did not. The §6.1 state machine is
correct in all 34 cells. The four seam defects backend found by running real
HTTP are genuinely fixed, and no sibling of any of them recurs. Every S2
write obeys the full §2.5 Stack M precondition list. Accessibility is clean
on every S2 page in English, and the Tamil locale is closed and asserted
closed.

**What blocks it is the one thing backend itself named as the most serious
thing in the slice, and it is worse than backend thought.** ADR-002 §2's
amendment of 2026-10-22 specifies a composite foreign key that would make a
tenant-inconsistent child row *unwritable*. It is not built. QA wrote the
inconsistency directly, as that amendment explicitly instructs, and measured
the consequence: **a photo of a real student's listing, on a campus whose
`discovery_enabled_at IS NULL`, is served — 200, real image bytes — to a
student who does not own it.** That is a discovery-gate bypass, and under
this charter a failure of a gate-derived test is never negotiated down.

---

## 1. Commands and output

### 1.1 Baseline, reproduced exactly before touching anything

```
$ set -a && . ./.env && set +a && export BOOKHOP_TEST_DB_NAME=bookhop_qa_s2
$ .venv/Scripts/python.exe -m pytest -q
8 failed, 1385 passed, 57 skipped, 2 xfailed in 37.51s

$ BOOKHOP_DB_ENGINE=sqlite .venv/Scripts/python.exe -m pytest -q
7 failed, 1316 passed, 128 skipped, 1 xfailed in 33.32s
```

Matching the slice note exactly, and every failure in `tests/contract/**`,
which is QA's tree.

### 1.2 After this pass

```
$ set -a && . ./.env && set +a && export BOOKHOP_TEST_DB_NAME=bookhop_qa_s2
$ .venv/Scripts/python.exe -m pytest -q
13 failed, 1511 passed, 55 skipped, 2 xfailed

$ BOOKHOP_DB_ENGINE=sqlite .venv/Scripts/python.exe -m pytest -q
12 failed, 1437 passed, 131 skipped, 1 xfailed
```

**Every one of the thirteen is a reported finding below**, not a
work-in-progress. The eight baseline failures are closed: three were designed
handoffs (the plpgsql set, the command set, the preconditions matrix), two
were the coverage regression, and three were forward-dated placements whose
day arrived. SQLite is one fewer because the photo-cap race skips there,
naming the engine.

### 1.3 The new files, run alone

```
tests/contract/test_denormalised_scope_columns.py   7 failed,  2 passed  (both engines)
tests/contract/test_price_trigger_attack.py         17 passed, 1 skipped (PostgreSQL)
                                                    14 passed, 4 skipped (SQLite)
tests/contract/test_listing_state_matrix.py        34 passed             (both engines)
tests/e2e/test_s2_sell_journey.py                   4 failed, 14 passed  (PostgreSQL)
tests/e2e/test_s2_ui_journey.py                     1 failed,  2 passed  (both engines)
tests/a11y/ (whole directory)                      29 passed,  4 skipped
```

---

## 2. The coverage regression — **recovered, not retired**

### F30 · the float-money attack stopped measuring the day its subject became real

`tests/contract/test_p14.py`'s `ATTACKS` table has a row `float_money`:
`listings.asking_price_paise` declared `real`. **That is the single most
important case W1a has** — the one column ADR-003 §2.1 permits to hold money,
declared as a float. The helper created the table if absent and then
`ALTER TABLE … ADD COLUMN`. S2 made the column real, and the attack began
raising `DuplicateColumn`.

```
E  django.db.utils.ProgrammingError: column "asking_price_paise" of relation
   "listings" already exists
```

**One correction to how this has been described, because it matters.** It did
**not** stop silently. `test_attack_reaches_the_schema_the_control_reads` is a
separate per-shape assertion whose entire job is that an attack which fails to
apply can never be read as an attack that was caught, and it went red with its
sibling. The pattern worked. But a red row measures nothing either, so the
question is live.

**Decision: recover.** Three reasons, in order of weight.

1. **It measures a different thing from backend's replacement.** Backend's
   `tests/unit/test_listing_money_column.py::test_a_real_declaration_fails_via_
   introspection_despite_the_model` asks *"does the guard's type union see the
   float"*. QA's row runs `control_catches()`, which imports the shipped guard
   and calls its live-schema assertions, and asks *"would the build go red"*. A
   guard can see a thing and not assert it. Both questions are worth a row.
2. **The matrix's value is that it is exhaustive.** Nineteen shapes, each
   either caught or a declared ADR-003 §2.3 W5 residual. A row removed is a
   shape nobody attacks and a hole that reads as completeness.
3. Recovering costs one branch.

**How.** `_create` now alters a live column's type instead of adding it. On
SQLite there is no `ALTER COLUMN … TYPE` and declared types are not enforced
(ENGINE-DIVERGENCE §2.8), so the shape **skips naming the engine and the
slice** rather than passing. And a second assertion,
`_assert_declared_type_took`, reads `information_schema` to confirm the column
really became `real` — because once an attack can be installed by *altering*,
"the column exists" stops being evidence that anything changed, and a no-op
`ALTER` would make every verdict in the file about a clean schema.

**Backend's replacement stays.** It is better placed than QA's row for the
properties it covers — the predicate on both engines, and rule 12's
service-layer refusal of `300.75` and of `True`. Two controls asking two
questions is not duplication; one control that stopped testing was the
problem.

### F31 · three unconditional `pytest.skip`s in QA's own tree that could never start

Found while fixing F30, and this is QA's own defect three times over. All
three were bare `pytest.skip(...)` at the top of a function with no condition:

| Test | The reason it gave | Why it had expired |
|---|---|---|
| `test_p14.py::test_the_response_schema_guard_has_no_owning_slice` | *"it has no owning slice … there is no response payload in S0"* | the module exists in backend's tree; S2 serves thirteen |
| `test_p14.py::test_price_immutability_trigger` | *"`listings` is an S2 table … unexecuted text until a PostgreSQL server exists"* | both are now true |
| `test_response_boundary.py::test_the_control_runs_against_every_real_response` | *"S0 serves two responses and it already checks both"* | S2 serves thirteen |

`CLAUDE.md` rule 10's fifth disguise, verbatim: *"from outside, 'not yet
running' and 'running and passing trivially' are indistinguishable."* An
unconditional skip cannot notice its own expiry. All three are inverted: the
subject existing is now the condition under which they **assert**.

**What replaced the third one is the finding worth keeping.** ADR-003 §5.3
makes `tests/unit/test_forbidden_response.py` the compensating control for the
two residuals P14 cannot close, and THREAT-MODEL §6 states it must assert
*"no response anywhere carries a forbidden key, a money-shaped key, a contact
detail or an amount."* Its live-surface assertion walked `/healthz` and
`/readyz`. **The named compensating control for the whole product was
measuring two operational probes.** It now runs over all seventeen S2 payloads
— including the refusal bodies — with the walker **imported, not
re-implemented**, and `test_the_control_runs_against_every_real_response`
derives the route list from the URLconf so a new route must be swept or
recorded with a reason. Green.

---

## 3. The denormalised columns — **the blocking set. 7 red on both engines.**

ADR-002 §2's amendment of 2026-10-22 is both the specification and the test
brief, and QA followed it literally:

> **The test that matters is the one whose fixture CAN produce the failure**:
> a test that **writes an inconsistent child directly, bypassing the service,
> and asserts the database refuses it.** A test that goes through the service
> proves only that the service is correct, which was never the thing in doubt.

`tests/contract/test_denormalised_scope_columns.py` calls no service function.
It writes with `all_objects` and with raw SQL, which is the only way to reach
the state the control exists to prevent.

### F32 · `listings_tenant_identity` is not installed

The amendment quotes its own DDL. Neither half exists:

```
E  AssertionError: ADR-002 §2 (amendment, 2026-10-22) specifies
   `CREATE UNIQUE INDEX listings_tenant_identity ON listings
   (id, campus_id, city_id, is_seed)` … It is not installed.

E  AssertionError: `listing_photos` has no multi-column foreign key …
   Single-column FKs present: ['listing_photos_campus_id_…_fk_campuses_id',
   'listing_photos_city_id_…_fk_cities_id',
   'listing_photos_listing_id_…_fk_listings_id']
```

### F33 · the `city_id` constraint is absent, **and so is the check it replaced**

The amendment withdrew its own nightly consistency check on the grounds that
*"where a database can make a class of wrong state unrepresentable, that beats
detecting it"* — and replaced it with `FOREIGN KEY (campus_id, city_id)
REFERENCES campuses (id, city_id)`. Neither shipped. `listings.city_id` and
`book_requests.city_id` are checked by nothing at all, which is weaker than
the position the ADR started from.

### F34 · **a photo escapes the discovery gate.** The serious one.

Setup, all of it the only lawful pre-Gate-C state: a real (`is_seed=false`)
seller, a `LIVE` listing, a campus with `discovery_enabled_at IS NULL`, one
photo row written consistently. A second **real** student on the same campus,
owning nothing, asks for the photo and correctly gets 404. One `UPDATE` sets
the photo row's `is_seed` to true — nothing re-derives it, nothing refuses it
— and:

```
E  AssertionError: FINDING. A photo row whose `is_seed` disagrees with its
   listing is served (200) to a student who does not own the listing, on a
   campus whose `discovery_enabled_at IS NULL`.
```

The bytes come back. `image/jpeg`, 200.

**Why it is the gate and not a scoping nicety.** `get_photo_for_download`
asks `assert_discovery_open(listing.campus)`, gets `GateClosed`, and then
consults **the photo row's own** `is_seed` to decide whether to convert it to
a 404. So the child row decides whether the parent is visible, and
API-CONTRACT §5.2 says the opposite in one sentence: *"a photo is as gated as
the listing it belongs to, and a guessable media URL would be a side channel
around ADR-002 §4."*

**Reachable by what?** Not by a student. By anything that can write a child
column: the staff moderation surface, `seed_demo`, a fixture, a data
migration, a future slice's bulk update. That is precisely the set the
composite FK exists to close, and the reason ADR-002 chose a constraint over a
nightly job in the first place.

### F35 · the same attack on `campus_id` crosses the tenancy boundary

With **both** campuses' gates lawfully opened — so the gate is out of the
question and only `scoped()` is being measured — repointing the photo row's
`campus_id` serves a photo of campus A's listing to a student on campus B
(200). `scoped()` filters on the child's copy of the key.

### F36 · the gated manager returns the child while hiding the parent

No HTTP involved. `Listing.objects` excludes the listing; `ListingPhoto.objects`
includes its photo. ADR-002's own words, measured: *"the gated manager
silently returns the wrong rows."* The consequence is forward: anything that
starts from `ListingPhoto.objects` — a derivative job, a metric, S3's
discovery read — begins outside the gate.

### F37 · `book_requests.city_id` can name a city its campus is not in

`UPDATE book_requests SET city_id = <another city>` succeeds. Every
`METRICS.md` query that groups by city counts it in the wrong one, and §9.3's
match rate is one of them.

**Recommended fix is ADR-002's own and QA has no better one:** the unique
index on the parent and the composite FKs on the children. The seven tests
above are written so that **landing the constraint turns them green through
their refusal branch** rather than making them unwritable, so they keep
guarding the fix. `test_the_attack_can_actually_produce_the_state` is the
guard on that: it performs the write and reads the row back, so the file
cannot quietly become seven refusal-branch no-ops.

---

## 4. The price trigger — **attacked hard, no defects.** 17 pass, 1 named skip.

P14's first executable control. `tests/contract/test_price_trigger_attack.py`
asks a different question from backend's unit file: not *"is the column
immutable"* but *"which routes reach the trigger, which must not, and is the
refusal the right refusal"* — one route at a time, because
`POSTGRES-FIRST-RUN.md` §1 item 1 is right that plpgsql resolves identifiers
**at the first execution of each branch**.

**Refused, every one, by message text and not by exit status:** `QuerySet.update`;
`Model.save()` with the attribute changed (a one-column change inside a
twenty-column `SET`); `save(update_fields=["asking_price_paise"])`;
`bulk_update` (a `CASE` expression, a third statement shape); raw SQL; and an
**unqualified `UPDATE listings SET asking_price_paise = 500`** with no `WHERE`
— the migration-script shape, where one statement rewrites every price in the
pilot. On PostgreSQL the refusal carries SQLSTATE `P0001`, the phrase *"fixed
at intake"*, and the listing id, and is asserted **not** to be an
`undefined_column`-class error — which would abort the statement identically
and look like the guard working.

**Not refused, which matters as much** (rule 13: a guard that fires on the
contracts it protects will be edited, not obeyed): status transitions; a full
`save()` that rewrites every column at its current value; writing the same
price back; the publish → withdraw journey over real HTTP; and ADR-003 §2.2's
own sanctioned remedy, withdraw-and-relist at a new price.

**Backend's guard-for-the-guard claim: verified, not relayed.** The slice note
says a no-op body replacement shows the structural limb passing while the
behavioural one fails. QA reproduced it independently, against the **catalog**
limb `test_postgres_catalog.py` uses rather than the assertion backend wrote,
so the two files are independent witnesses. It is true. QA added the two limbs
backend does not have: a **dropped** trigger (caught by name, not by
behaviour-only), and a **disabled** trigger — `ALTER TABLE … DISABLE TRIGGER`
leaves the object in `pg_trigger` under its own name, so a name check passes
while the column is freely updatable. That is `CLAUDE.md` rule 9's earning
case, one table over, and `tgenabled` is what catches it.

### F39 · `ENABLE ALWAYS` is **ASSUMED THERE**, not VERIFIED HERE — for all seven triggers

```
SKIPPED: NOT VERIFIABLE WITH THIS ROLE (vendor=postgresql, slice=S2):
`SET session_replication_role` needs superuser and the application role is
not one on this box (ProgrammingError('permission denied to set parameter
"session_replication_role"')).
```

`ENABLE ALWAYS` exists for exactly one reason, stated identically in the
migration and in ENGINE-DIVERGENCE §3.6a: *"`session_replication_role =
'replica'` is what a logical-replication apply worker and some restore paths
use, and a guard a restore bypasses is a guard that is off exactly when a bad
row is being written."* **Nothing in this repository has ever executed that
sentence**, for the price trigger or for the six older ones. `tgenabled = 'A'`
is asserted; what `'A'` buys is not. Under rule 9's labelling rule that is a
prediction and is now written as one. It belongs in `INFRA.md` §3.3's restore
test, which runs as a privileged user on a throwaway database.

**One catalog fix, QA's own.** `test_postgres_catalog.py`'s ENABLE-ALWAYS
sweep hard-coded three table names into its query, so `listings_price_immutable`
— the newest guard, on the newest table — was outside it. The query is now
derived from `EXPECTED_TRIGGERS_BY_TABLE`, so a guard on a new table joins the
sweep by being added once.

---

## 5. The four seam defects — **fixes correct, regressions under-pinned**

Backend's four fixes are right and nothing QA threw at them regressed. The
charter's question was whether the regressions **pin the seam or the
symptom**, and the answer is the symptom in all four. That is not a criticism
of the fixes; it is a statement about what the tests will catch next slice.

| Seam | Backend's regression pins | The seam is | QA's re-pin |
|---|---|---|---|
| multipart 500 | `/listings/{id}/photos` | `apps.core.api.endpoint` consuming the request stream | every POST route in the URLconf gets a multipart body; **no 5xx** on any of 13 |
| timestamp 500 after commit | two paths that return a timestamp today | the idempotency store's JSON encoder | the encoder itself with `datetime`, `date`, `UUID`, `Decimal` and a nested `datetime`; plus every POST route called twice — **no 5xx** |
| 422 where 409 was right | `publish` | the precondition order in L1 | both transition endpoints, **derived from the URLconf** so S4's join automatically |
| the terms route that did not exist | the tick records the acceptance | *an L1 function the journey needs with no route reaching it* | two journeys that call **no service function at all** — L2 and L3 |

The photo route is the only multipart endpoint today, which is exactly why a
regression written against it stops measuring the moment S5 adds support
attachments or S6 adds report evidence. The sweeps assert their own reach
(`len(checked) >= 10`), so they cannot report coverage for a route they never
called.

**One §4.1 rule none of the four regressions covers**, named in the charter:
*same key with a different body is a 409*. Added and **passing** —
`409 IDEMPOTENCY_KEY_REUSED`.

### Three new defects at the seams

**F40 · a photo row whose file is missing is a 500, not a 404.**
`photo_bytes` wraps `get_photo_for_download` in `except ServiceError` and
calls `photo_response` **outside** that block; `photo_response` raises
`NotFound` when `read_object` returns `None`. Backend's
`test_a_purged_photo_is_404_rather_than_a_crash` does not reach it — a purged
photo has `storage_key = NULL` and is caught inside the try. The uncaught case
is key present, file absent. See §7: that is the state a database-only restore
produces for every photo at once.

**F41 · `403 CONSENT_REQUIRED` does not name the missing `purpose_key`.**
API-CONTRACT §2.5 requires it in parentheses on precondition 5. Measured, on
publish after `listing_publication` was withdrawn mid-flow:

```
{"error": {"code": "CONSENT_REQUIRED",
           "message": "This needs your permission first. You can change it any time."}}
```

The student is told a permission is missing and not which one. The rest of
that journey is correct and worth recording: the refusal is a clean 403, and
**the draft survives** — a withdrawal that destroyed unpublished work would be
a reason not to withdraw, which is what DPDP r.3(c)(i) forbids making it.

**F42 · `320,00` is stored as Rs 32,000.** `web/forms.py::clean_asking_price_rupees`
strips commas on the line **before** it checks for a decimal point. Its own
docstring names this input: *"the three mistakes a student actually makes —
₹280, `2,80`, 280.50 — each deserves a different sentence."* `280.50` gets its
sentence. `2,80` gets none; it becomes 280.

```
All outcomes: {'320.755': (400, None), '-5': (400, None), '1e3': (400, None),
               '320,00': (302, 3200000), '': (400, None), '275': (302, 27500)}
```

A hundredfold error on a column that is **immutable by trigger**, so the
seller cannot correct it — they withdraw and relist, and in the meantime the
listing carries a price they did not set. The fix is not "stop stripping
commas": the strip is what makes `1,200` work, which is the Indian grouping a
student really does type. It is to refuse a comma that is not in a valid
grouping position — the distinction the docstring already draws.

> **A note on how F42 was nearly missed, because it is the pass QA owes this
> project.** The first draft of that test omitted `damage_flags` entirely.
> Every post returned 400 on *"Tick what is damaged, or tick 'No damage to
> report'"*, every assertion that nothing was stored held, and the test was
> **green while measuring nothing** — rule 10's first disguise. It surfaced
> only because a sibling test failed for the same reason and was noisy about
> it. The test now posts a valid control price in the same loop and asserts it
> **is** accepted, so the refusals cannot be refusals of the form.

---

## 6. The photo cap — **measured, and the declared ceiling understates it**

`add_photo`'s own note declares the ceiling: *"two simultaneous uploads on the
same listing could both see three and both insert, giving five … the cost of
exceeding it is a fifth thumbnail."* A declared ceiling is a prediction until
someone runs it.

Run: a listing with three photos, six uploads released together on a barrier.

```
E  AssertionError: FINDING. DATA-MODEL §3 says 'Max 4 photos per listing'.
   After three sequential uploads and 6 simultaneous ones, the listing holds
   **9** photos and 6 of the 6 racers were accepted
   (outcomes: [201, 201, 201, 201, 201, 201]).
E  assert 9 <= 4
```

**Not two-into-five. Every concurrent writer passes.** `count() >= 4` is read
inside each transaction under READ COMMITTED with no lock on the listing row
and no unique constraint for a loser to collide on, so there is no bound short
of the 40/day rate limit.

**QA is not asking for the counting trigger.** Backend's argument for
declining two engine-specific bodies is sound. What is wrong is the number the
decision was reasoned against — *"a fifth thumbnail"* is not what nine is —
and S7's derivative generation will size its work off `MAX_PHOTOS_PER_LISTING`
believing it is enforced. Skips on SQLite naming the engine, because one
database writer would prove serialisation rather than the property.

The **sequential** cap is correct: the fifth upload is `422 TOO_MANY_PHOTOS`.

---

## 7. Images and the restore — including one finding QA got wrong and withdrew

**Image content, recorded rather than graded.** `apps/listings/images.py` is
explicit and correct that it parses containers and never decodes, and its
security argument — *"a decoder is the attack surface"* — is good. QA is not
asking for Pillow. What was not written down is the product consequence, now
measured: a file that is a valid JPEG container with one byte of
entropy-coded data is **accepted**, and the stored `width`/`height` are what
the SOF0 segment *claims*. A 4000×3000 row of 130 bytes is stored as a
4000×3000 photo. There is no later gate — no decode in the moderation queue —
so the first person to discover a listing whose four photos render as garbage
is a student at a handover. S7's derivative sizing must not trust those
numbers and nothing today says so. The container check is **not** vacuous: a
non-image is `400 VALIDATION_FAILED` with `field_errors`, which is §2.2's
correct code (QA's first draft expected 422 and the contract corrected it).

### WITHDRAWN · "the media directory is in no backup scope"

**This was wrong and the measurement says so.** `INFRA.md` §3.1 reads:

```
pg_dump --format=custom bookhop   →  db-<UTC-ts>.dump
tar -cz /var/lib/bookhop/media    →  media-<UTC-ts>.tar.gz
```

The photos are backed up. `apps/listings/storage.py`'s note — *"a restore has
to carry the media directory … flagged in the slice note"* — is out of date in
the direction that overstates the gap, and rule 9's corollary says delete the
explanation rather than keep the finding.

### F44 · the restore **test** covers half the backup

§3.3 is seven numbered steps and **every one acts on the database dump**:
fetch and decrypt, `pg_restore`, `migrate --check`, `verify_audit_chain`, a
read-only assertion set (which does include *"`listings_price_immutable`
trigger present"*), print RESTORE OK. **The media tarball is produced nightly
and opened by nothing.**

Paired with F40, the consequence is concrete: restore from the dump alone, as
§3.3 does, and every photo URL in the pilot answers **500**. The script prints
RESTORE OK. §3.3's own closing sentence is the standard it misses — *"a
restore that has not been tested this month is reported as untested, not as
working"* — and the media half has never been tested and is reported as
working.

The fix is a step 5b: extract the tarball and assert a sample of
`listing_photos.storage_key` resolves to a file. S8 and platform-sre own it;
**S2 is when it has to be written down**, because S2 created the files and by
S8 the script will be written against a step list that never had them.

---

## 8. The gate, the preconditions, and one escalation

### F45 · ESCALATION TO CTO · §2.5 precondition 7 and ADR-002 §4 disagree

Measured: a real (`is_seed=false`), ACTIVE, adult- and campus-verified,
consented student on a campus with `discovery_enabled_at IS NULL` posts to
`/api/v1/listings` and gets **201**. `POST /api/v1/requests` likewise.

- **§2.5's reading.** Its eight preconditions are **standing** —
  *"checked in L1 in this order"* — and its membership table puts *"listings
  and photos, `book_requests`"* in Stack M with no carve-out. Precondition 7
  is *"campus discovery gate open, or both parties are seed → else `403
  GATE_CLOSED`"*. Literally, this must be a 403.
- **ADR-002 §4's reading.** The gate is *"data, plus a server-side guard on
  **reads**, plus a database write guard"* — that write guard being the one on
  `discovery_enabled_at` itself. §4.1(c) defines the closed state as *"the
  **discovery query** is additionally restricted to `is_seed = true`"*. And
  `INCORPORATION-AND-BLOCKERS` fixes the trigger at *"the moment participants
  can **browse each other's** listings"*, which a `DRAFT` nobody can see is
  not. On this reading 201 is right.

This is `CLAUDE.md` rule 10's second disguise, named in the rule itself: **a
criterion broader than its own rationale, which the main journey must violate
to work** — and it surfaced, as the rule predicts, *"only when someone tried
to build against it."*

**QA does not pick a side**, and the cost of each is real. Refusing the write
means BookHop does not take a seller's r.6(4)(a) prior written contract before
Gate C, which is a defensible legal position. Permitting it means §2.5's
"standing" is not standing and the document has to say so. Either way one
frozen document needs amending in the same commit as the test. Recorded as a
hard red test rather than an xfail, because under this charter a gate-derived
disagreement is not negotiated down to a known issue.

### Precondition 6 — green

A cross-campus listing detail and a cross-campus photo are both **404, never
403**, which is §2.2's requirement and the reason for it: *"a 403 would
confirm existence and leak the catalogue."*

### QA-S1 F24 — **closed**

`POST /account/correction` exists and a **suspended** student can use it. The
`xfail(strict=True)` that carried the finding **XPASSed** the day the endpoint
was mounted and turned the suite red, which is the instrument doing exactly
what it was converted to strict for. The xfail is removed and the assertion is
live. One change: the body is §3's `{stated_problem}`, not the `{field, value}`
the row guessed four slices early — the contract withdrew that shape itself.
§2.5's `display_name`-in-Stack-M reasoning is quotable again.

### All six S2 writes are in the standing-preconditions matrix

`listing_create`, `listing_photos`, `listing_publish`, `listing_withdraw`,
`request_create`, `request_close`, plus `correction` in Stack S. 98 pass. Every
S2 write refuses an unauthenticated caller with `401 NOT_AUTHENTICATED`,
refuses each of the four narrowable preconditions with the contract's own code
in the contract's own order, and answers a tombstoned actor **401, not 403**.

---

## 9. The listing state machine — 34/34, no defects

`DATA-MODEL.md` §6.1 transcribed from the diagram, not from the code: every
one of the eight states × `publish`, `withdraw`, add-photo and read. Every
legal source 2xx, every illegal one `422 TRANSITION_NOT_ALLOWED`, never 403 —
the actor is the owning seller with every precondition met, so a 403 would be
a finding in itself. The permitted and refused sets are asserted to partition
the states (rule 10's corollary: *both sides are rows*), and the state list is
checked against the **database's** CHECK constraint rather than the model's
`choices`, so a ninth status added by a migration fails here.

**Two cells no document rules**, recorded and routed to cto rather than
graded:

- **Adding a photo, by state.** §6.1 is a diagram of `status` transitions and
  this is not one. The build refuses the four terminals and allows the rest,
  which is defensible and written down nowhere. The `RESERVED` cell is a
  product question — changing the photos of a book someone has agreed to
  collect — not a technical one.
- **The seller reading their own `REMOVED_LEGAL` listing.** §6.1 preserves the
  content 180 days *for investigation*; nothing says *served to the seller*.
  The build serves it, which is also the due-process answer: a seller who
  cannot see what was taken down cannot contest it.

---

## 10. Accessibility — green in English, Tamil correctly closed, keyboard still not run

29 pass, 4 skip. All five S2 pages pass the structural rules with zero
violations: `/sell`, `/sell/find-book`, `/wanted`, and **the two the main
sweep cannot reach** — `/listing/<id>` and `/sell/<id>/photos`.

`_page_routes()` skips every parameterised route, which was right when every
page was zero-argument and is now the reason the two pages the product is
actually about were outside the sweep. The main sweep's reach assertion is
*"some gated route answered 200"*, which the account pages satisfy, so nothing
would have reported them missing — **rule 10's fourth disguise in QA's own
harness for the second time.** `tests/a11y/test_s2_pages.py` covers them and
asserts its reach by name; a page that redirects or 404s is a **failure**
there, not a skip.

**Tamil.** The locale is closed and the test written is that it is closed, per
the charter. Each S2 page requested with `ta`, `ta-IN` and a quality-weighted
`ta;q=0.9` comes back `lang="en"`. `locale/ta/REVIEWED.toml` exists and is
**deliberately empty**; S2 added 615 lines of Tamil copy that nobody has read.
A test asserts the manifest is still empty, because the file's existence is
not the sign-off and a later reader could take it for one.

**NOT VERIFIED, and not claimable:** the keyboard-only walkthrough. No browser
automation exists on this machine. Automated checks alone are not a pass; the
charter says so and this report does not report around it. Likewise p75 LCP
and p95 search latency (S3).

---

## 11. What was NOT verified, and why

1. **Keyboard-only walkthrough of every flow.** No browser automation. The
   structural harness decides what HTML can decide and no more.
2. **Tamil accessibility, and Tamil copy generally.** The locale is closed, so
   a11y on it would measure nothing. The banned-vocabulary check remains
   **English only** and S2's 615 new Tamil lines are unread by any person.
   THREAT-MODEL §6.1 accepted risk A9 stands, undiminished by the manifest
   existing.
3. **`ENABLE ALWAYS` under `session_replication_role = 'replica'`** — F39. The
   application role is not superuser. ASSUMED THERE for all seven triggers.
4. **p75 LCP, p95 search latency** — S3, and they need a browser.
5. **The §9 metric queries.** `TASKS.md` S2's gate note assigns metric SQL to
   **S7**; there is nothing to run. The charter's time-shifted 90-day fixture
   is S7's item, not an S2 omission.
6. **The whole slice with the gate OPEN.** Every test ran against
   `discovery_enabled_at IS NULL` except the two that open it deliberately,
   because that is the only lawful state. What that leaves unverified is
   larger than it sounds and is set out below.

### 11.1 What "no real student has ever read a listing" leaves unverified

- **The read side of the open gate does not exist yet.** `apps/discovery` is
  S3. `restrict_when_gate_closed`'s open branch returns the queryset
  unchanged and has been exercised by unit tests, never by a journey.
- **No two real students have ever interacted.** Every actor in S2's fixtures
  is `is_seed=True` except the ones QA built for F34–F37 and F45. Anything
  that only appears with two real parties on one open campus is untested
  behaviour, not passing behaviour.
- **`publish_listing` enqueues `requests.match_scan` (A-4).** The notification
  crossing a closed gate is S3's named guard and nothing in S2 exercises it.
  F34 is a warning about that shape: the first thing that reads a child table
  to decide who to tell is the next place the gate can be bypassed.
- **The seed/real boundary has never been load-bearing.** `CHECK
  (seller_is_seed = buyer_is_seed)` is S4. Until then `is_seed` is a filter
  nobody has had to defend, which is why F34 — a child row flipping it —
  found an open door.

---

## 12. Findings index

| # | Severity | Finding | Owner |
|---|---|---|---|
| F30 | QA's own, closed | the float-money attack stopped measuring; **recovered**, not retired | test-qa |
| F31 | QA's own, closed | three unconditional skips that could never start; all inverted | test-qa |
| F32 | **BLOCKING** | `listings_tenant_identity` + composite FK on `listing_photos` not built (ADR-002 §2 amendment) | backend |
| F33 | **BLOCKING** | `(campus_id, city_id) → campuses` FK absent, and the nightly check it replaced is gone too | backend |
| F34 | **BLOCKING** | a photo with an inconsistent `is_seed` is **served** past a closed gate | backend |
| F35 | **BLOCKING** | an inconsistent `campus_id` crosses the tenancy boundary | backend |
| F36 | **BLOCKING** | `ListingPhoto.objects` returns the child while `Listing.objects` hides the parent | backend |
| F37 | high | `book_requests.city_id` can name a city its campus is not in | backend |
| F38 | medium | `MEDIA_ROOT` is process-global; nothing isolates it between tests. QA caused one cross-tree failure this way and fixed its own fixture; the shared directory remains | backend (conftest) |
| F39 | gap, labelled | `ENABLE ALWAYS` is ASSUMED THERE for all seven triggers | platform-sre / S8 |
| F40 | high | a photo row whose file is missing is a **500**, not a 404 | backend |
| F41 | medium | `403 CONSENT_REQUIRED` does not name the missing `purpose_key` (§2.5) | backend |
| F42 | high | `320,00` stored as Rs 32,000 on an immutable column | frontend |
| F43 | medium | the four-photo cap is **nine** under six concurrent uploads | backend |
| F44 | high | `INFRA.md` §3.3's restore test never opens the media tarball | cto / platform-sre |
| F45 | **ESCALATION** | §2.5 precondition 7 vs ADR-002 §4: a real student can create a listing on a closed campus | cto |
| — | unspecified | photo upload by listing state; the seller reading their own `REMOVED_LEGAL` listing | cto |
| — | withdrawn | "the media directory is in no backup scope" — §3.1 backs it up; QA was wrong | test-qa |

**To pass S2:** F32–F36 closed, F45 ruled. F40, F42 and F44 are not
negotiable down to known issues either, but they do not block on the gate
argument. F39 and the keyboard walkthrough are standing gaps carried forward,
named, and not reported around.

---

## Amendment log

| Date | Change | By |
|---|---|---|
| 2026-10-22 | v1.0 — S2 pass. Coverage regression recovered; three unconditional skips inverted; the ADR-002 denormalisation amendment measured and found unbuilt with three live consequences; the price trigger attacked on eleven routes with no defects; the four seam regressions re-pinned at the seam; the photo-cap ceiling measured at nine; one backup finding raised and withdrawn, replaced by a narrower one; §2.5 precondition 7 escalated to cto | test-qa |

---
---

# QA-S2 v2.0 — the rework pass

**Owner:** test-qa · **Version:** v2.0 (appended to v1.0 above, which stands
unchanged) · **Date:** 2026-10-22
**Under test:** backend `57c6689`, frontend `f24b133`, on `ac2d622`.
**v1.0's verdict was "does not pass" on five blocking findings and one
escalation. All six are closed.**

---

## VERDICT · **S2 PASSES** — with one document gap carried to S8 and one engine-specific migration defect routed to backend.

```
$ set -a && . ./.env && set +a && export BOOKHOP_TEST_DB_NAME=bookhop_qa_s2
$ .venv/Scripts/python.exe -m pytest -q
1 failed, 1588 passed, 60 skipped, 2 xfailed in 48.35s
FAILED tests/e2e/test_s2_sell_journey.py::test_the_backup_scope_and_the_restore_test_cover_the_same_things

$ BOOKHOP_DB_ENGINE=sqlite .venv/Scripts/python.exe -m pytest -q
2 failed, 1516 passed, 132 skipped, 1 xfailed in 37.13s
FAILED tests/e2e/test_s2_sell_journey.py::test_the_backup_scope_and_the_restore_test_cover_the_same_things
FAILED tests/contract/test_tenant_fk_migration.py::test_the_migration_round_trips_forward_reverse_forward
```

Baseline before this pass reproduced exactly as reported: PostgreSQL 3 failed
/ 1570 passed, SQLite 5 failed / 1493 passed.

**Neither remaining failure blocks the slice**, for the reasons in §15 and
§14.1. Neither is a listing, photo, price or gate defect; both are about
operations.

---

## 13. The five rulings and re-points

### 13.1 The gate ruling — re-pointed, and both halves are rows

A-22 settled the escalation **against what QA's test asserted**, from the
compliance rationale rather than from either document's precedent, and added
a reason QA did not have and should have had: blocking the write means a
campus opens with zero listings and the first search fails, which is R-01
materialising by design. That is the stronger argument and it is recorded in
the test.

`test_precondition_7_the_gate_is_a_read_control` is now the regression, and
it is written as **both halves of the ruling** rather than the permitted one:

| A-22 | Asserted |
|---|---|
| *create a listing* permitted pre-gate | `201` |
| *record a want* permitted pre-gate | `201` |
| *upload its photos* permitted pre-gate | `201` |
| *read your own rows* permitted pre-gate | `200`, and `/listings/mine` returns exactly the actor's own |
| *all discovery still gated* | a second real student on the same closed campus gets `404` on the photo route — not `403`, per §2.2 |

**And A-22's narrowest clause has its own test**, because it is the one a
later change erases without noticing: *"the create flow may surface no other
user's row **including a count**."* A count is not a row and it is a
disclosure — *"3 other students are selling this book"* tells a student the
campus has supply, which is the browsable surface in aggregate.
`test_the_create_flow_surfaces_no_other_students_row_not_even_a_count` drives
`/sell`, `/sell/find-book` and `/wanted` as a real student with another
student's LIVE listing in the database. Green.

### 13.2 The guard-for-the-guard — converted, and it kept its teeth

`test_the_attack_can_actually_produce_the_state` asserted that the
inconsistent write **succeeds**, which was the only honest way to prove the
fixture could produce the failure mode. The composite FK makes that
unwritable, so the test could not pass — correctly.

Deleting it would have taken the no-op guard with it. It is now
`test_the_inconsistent_write_is_refused_and_the_writer_still_works`, two
limbs, in this order:

1. **`_force` still writes** — demonstrated on `width`, a column no
   constraint guards. Asserted first, so a failure says *"the writer is
   broken"* rather than *"the constraint held"* when both are true.
2. **The same statement shape on a guarded column is refused**, and the
   refusal names a constraint.

Without limb 1, a `_force` that silently stopped issuing SQL would make limb
2 and **every refusal branch in the other six tests** pass for the wrong
reason. The guard survives the fix instead of being replaced by it.

### 13.3 The SQLite introspection limit — fixed, and QA's finding was wrong

Django's SQLite introspection flattens a composite FK into **one
`get_constraints` entry per column**, so QA's `len(columns) > 1` test saw four
single-column FKs and reported the control missing. It is not missing:
`PRAGMA foreign_key_list` shows one constraint spanning four columns, and the
write is refused.

`_composite_fks()` now reads the right catalog per engine. **The property was
never in doubt** — the behavioural limbs asserted it on both engines
throughout — which is itself the argument for shipping both limbs rather than
the structural one alone.

The `city_id` test needed the same treatment for a different reason: on
SQLite that control is a **trigger pair**, not an FK, because rebuilding
`listings` would drop `listings_price_immutable`. Trading P14's guard for
ADR-002's would be a widening dressed as a fix, and the migration is right to
decline it. The test asserts **both** triggers, insert and update, because a
guard that checks only inserts is a guard an update walks past.

### 13.4 The photo-cap race — re-measured, and the cap holds

v1.0 measured **nine photos from six concurrent uploads** on a four-photo cap.
Backend fixed the cause without reproducing the race, so QA re-ran it.

```
$ pytest tests/e2e/test_s2_sell_journey.py::test_the_four_photo_cap_survives_simultaneous_uploads
1 passed   (three consecutive runs)
```

The `SELECT … FOR UPDATE` on the listing row serialises the count; the losers
get `422 TOO_MANY_PHOTOS`. **The test stays as the regression and is
deliberately not softened to "the lock is present":** the lock is one line,
and a refactor that moves the count outside the locked block would restore
the defect with every unit test still green, which is how it got here. The
subject is the number of rows, measured.

### 13.5 F40, F41, F42 — closed and re-verified

The missing-file photo is a `404`; the `403 CONSENT_REQUIRED` body names the
missing `purpose_key`; `320,00` is refused rather than stored as Rs 32,000.
All three regressions are the ones v1.0 wrote, and none was edited to fit the
fix.

---

## 14. What was attacked hardest this pass

### 14.1 The SQLite migration splice — the splice is sound; **the reverse is not**

The composite FK arrives on SQLite by **rebuilding the table**: the existing
`CREATE TABLE` is read out of `sqlite_master`, a `FOREIGN KEY` clause is
spliced in before the closing parenthesis, rows are copied, the table is
renamed. Deriving the statement rather than retyping it is the right call and
is why no column or CHECK can drift from the models. **What makes the splice
land in the right place is `original.rfind(")")`.**

**The splice itself is correct, and that is now pinned rather than assumed.**
`test_the_last_paren_really_is_the_tables_closing_paren` takes the live
statement, cuts it at `rfind(")")`, and asserts the prefix has exactly one
unclosed `(` — with single-quoted literals stripped first, so a parenthesis
inside a future enum value cannot fool the count. The trailing-CHECK case is
measured on `book_requests`, which really is that case: it ends
`… IS NOT NULL)))`, three parentheses of which only the third is the table's.
Both CHECKs and every column survived the rebuild.

**The round trip did not.**

```
FAILED tests/contract/test_tenant_fk_migration.py::test_the_migration_round_trips_forward_reverse_forward
  OperationalError: foreign key mismatch - "listing_photos" referencing "listings"
```

**`listings/0003` cannot be reversed on SQLite, and the failure is worse than
an error.** The reverse drops `listings_tenant_identity` and the eight
`*_campus_city_*` triggers, and **deliberately leaves the composite FK on the
rebuilt children** — *"dropping it would need a second rebuild, and a reverse
that recreates a table is a reverse that can lose data; the constraint is
harmless to leave."* It is not harmless: the child FK then references a parent
tuple with no unique index behind it, which is SQLite's `foreign key
mismatch`.

Measured state after the failed reverse:

| | |
|---|---|
| `listings_tenant_identity` | **gone** |
| `*_campus_city_*` triggers | **0 of 8** |
| `django_migrations` | **still records 0003 as applied** |
| `UPDATE listings SET city_id = …` to a foreign city | **accepted** |
| a photo whose `is_seed` disagrees with its listing | **accepted — F34 reopened** |
| `migrate listings` to recover | **a no-op** |
| what actually recovers it | `migrate listings 0002 --fake`, then a real forward |

The migration is `atomic = False`, so the reverse stops halfway; and because
the `RunPython` raised before Django could delete the ledger row, **`migrate
--check` is clean while both controls are off.** That is a guard that is off
and reports as on — the defect class F32–F37 were about, reintroduced by
their own fix's rollback path.

**PostgreSQL round-trips cleanly** (VERIFIED HERE), because its reverse drops
the constraints before the indexes. The two paths are not equivalent and only
one of them had been run.

**Severity and routing.** SQLite is the development engine (ADR-001 §2.2) and
production is PostgreSQL, so `INFRA.md` §4's rollback is unaffected. What is
affected is every developer: a rollback attempt leaves them testing against a
database whose tenant-identity controls are silently off, with nothing saying
so. **It does not block S2** — the forward path is correct on both engines and
that is what ships — but it should not reach S4, when `transfers` adds the
next composite key. Routed to backend as **F46**.

### 14.2 The copy catalogue — verified independently, and it holds

Frontend found three shipped sentences sitting in the catalogue as empty or
truncated message ids (`sell.isbn.checksum`, `sell.photos.unsupported`, and
`sell.photos.too_big`, which stopped at the em-dash). The deny-list reads the
catalogue, so for those three it was scanning nothing — **a banned word in
any of them would have shipped past a clean suite.** That is this project's
defect class landing in the copy control, found by someone writing the
verification that did not exist.

`tests/contract/test_copy_catalogue_is_the_shipped_copy.py` verifies the fix
**without reading the `.po` to decide what should be in the `.po`**, which is
the circularity that let the gap exist. Strings are extracted from the
source — `pgettext` calls in `apps/**` and `web/**`, `{% translate %}` and
`{% blocktranslate %}` in `templates/**` — and compared both ways. Six tests,
all green:

- the extractor reached a real corpus (**≥150 strings**, from both Python and
  templates), asserted before anything else;
- no context carries two different sentences;
- every shipped sentence is in `locale/en` **byte-identical** — not merely
  present, because `too_big` was present and truncated, and a presence check
  would have called it covered;
- every `{% plural %}` half has an `msgid_plural`;
- `locale/en` and `locale/ta` carry **exactly** the same contexts;
- **every Python-authored sentence actually reaches the deny-list's corpus**,
  which is the standing property the three empty ids broke: the scan reads
  templates and the English catalogue and *not* `.py` files, by design, so a
  view's sentence is in scope only through its catalogue entry.

Two of QA's own extractor limits were found and fixed rather than reported as
defects: implicitly-concatenated Python literals, which made a correct
four-line string in `web/views.py` look truncated, and `{{ x }}` → `%(x)s`,
which is Django's own rewrite. **An extractor that cries wolf about correct
copy is the shape rule 13 names.**

### 14.3 `web/selfcheck.py` — wired, and its reach measured

Frontend wrote the guard and said plainly that until a line ran it, it was
*"a check that has not started … one of the six disguises."* It owns no test
directory; the guard is about accessible names; `tests/a11y/**` is QA's. It is
wired at `tests/a11y/test_template_invariants.py`.

**Wiring is not trusting.** The suggested line — `assert run() == []` — passes
on an empty corpus, on a regex that stopped matching, and on a neutered
detector. Four assertions instead of one:

1. frontend's own `selfcheck_detector()` runs, and the case set is asserted to
   contain both positives and negatives, so the rule cannot be widened until
   it fires on correct markup;
2. the corpus is real — **27 templates, 4 hand-written labels**;
3. the rules are clean over `templates/**`;
4. the docstring's "has not started" disclosure is now stale, reported as a
   skip naming frontend as owner rather than edited in their tree.

**And the declared ceiling is quantified and then closed.** Frontend's note
said the Django-rendered labels *"are not covered … 'safe by construction' is
an argument, not a measurement."* Measured: **4 hand-written labels in the
templates, 31 in the pages a signed-in student is served** — so the source
guard sees roughly one label in eight, and the seven it misses include every
radio group in the sell flow, which is the form the whole defect was on.
`test_no_rendered_page_puts_interactive_content_inside_a_label` applies
**frontend's own `check_source`** to the served HTML, covering all 31 with no
second copy of the rule (rule 11). Clean.

What neither can decide is the accessible **name**, which only a browser
computes. That remains `test_pages.py`'s standing skip.

### 14.4 The two frontend fixes, verified from the outside

- **The publish disclosure.** A-22 required it, so rule 9 requires a test that
  it exists *and* behaves. Asserted on the served page: the seller is told
  *"Nobody can see this yet"*, the mechanism clause survives, and the sentence
  carries **no** undertaking that the campus will open — `soon`, `shortly`,
  `will open`, `launching` and `next week` are all asserted absent, because
  COPY-DECK v1.5 names no date and a disclosure whose purpose is to stop a
  seller feeling tricked must not create a second expectation.
- **The stale clock.** Frontend's find, and QA could not have made it: the
  warning counted from `published_at`, so on the morning a campus opened its
  whole backlog would have greeted the first buyer with *"listed 40 days ago
  — this may be gone"*. Verified with a time-shifted fixture, **both sides**:
  a listing published 40 days ago onto a campus that never opened is **not**
  stale, and a listing visible for 40 days on an open campus **is**. The
  second half matters as much — a clock that never fires would pass the first
  and silently delete the control.

---

## 15. The one finding carried forward · F44's media half

`INFRA.md` §3.3 gained **step 5a** on 2026-10-22: `SET
session_replication_role = 'replica'`, then re-run every append-only refusal.
That is the right home for F39 and the amendment says why — *"this test is the
one context where we hold superuser legitimately."* **Asserted and green**:
the step cannot now disappear without a red test.

**The media half is still open.** Every step in §3.3 acts on the database
dump, 5a included. The tarball §3.1 produces nightly is opened by nothing. A
restore verified by that script restores every row, passes
`verify_audit_chain`, re-proves every refusal under replica role, prints
RESTORE OK — and has not established that one photo came back.

§3.3's own closing sentence is the standard it misses: *"a restore that has
not been tested this month is reported as untested, not as working."*

The fix is a step 5b in the same place 5a went: extract the tarball, assert a
sample of `listing_photos.storage_key` resolves to a file. **Document change,
cto and platform-sre, S8.** It does not block S2, and the test stays red
deliberately — an open gap with no red test is how this one survived v1.0.

---

## 16. What is still NOT verified

Unchanged from v1.0 except where noted:

1. **The keyboard-only walkthrough.** No browser automation. Automated checks
   alone are not a pass.
2. **Tamil, anything.** The locale is closed and asserted closed; the
   banned-vocabulary check is still English-only. **Improved this pass:** the
   two catalogues are now known to carry exactly the same contexts, so the
   gate counts the real number of unreviewed strings rather than a subset.
3. **`ENABLE ALWAYS` under replica role.** Still ASSUMED THERE here — the
   application role is not superuser — but it now has a home that will verify
   it (§3.3 step 5a) rather than no home at all.
4. **p75 LCP, p95 search latency** — S3, and they need a browser.
5. **The §9 metric queries** — S7 per `TASKS.md`.
6. **The slice with the gate open.** A-22 makes this narrower: the pre-gate
   write path is now *ruled* rather than merely untested, and both halves of
   the ruling are exercised. What remains is the read side, which is
   `apps.discovery` and does not exist (S3), and any behaviour needing two
   real students interacting on one open campus.
7. **The accessible name**, which only a browser computes — the one thing the
   newly-wired template guard explicitly cannot decide.

---

## 17. Findings index · v2.0

| # | Status | Finding |
|---|---|---|
| F30–F31 | closed in v1.0 | QA's own coverage regression and three unconditional skips |
| F32–F37 | **CLOSED** | composite FK installed on both engines; all seven tests green, the guard-for-the-guard converted to a regression that keeps its first limb |
| F38 | open, low | `MEDIA_ROOT` is process-global between tests; QA's fixture no longer pollutes it |
| F39 | **routed** | `ENABLE ALWAYS` now has a verification home in `INFRA.md` §3.3 step 5a |
| F40 | **CLOSED** | a photo row whose file is missing is a 404 |
| F41 | **CLOSED** | `403 CONSENT_REQUIRED` names the missing `purpose_key` |
| F42 | **CLOSED** | `320,00` refused rather than stored as Rs 32,000 |
| F43 | **CLOSED** | the four-photo cap holds at four under six concurrent uploads, re-measured |
| F44 | **open** | §3.3's restore test still never opens the media tarball (5a landed, 5b did not) |
| F45 | **CLOSED** | ruled by A-22; re-pointed, both halves plus the no-count clause |
| **F46** | **NEW, backend** | `listings/0003` cannot be reversed on SQLite; the failed reverse silently disables both tenant controls while `migrate --check` stays clean |
| — | verified | the copy catalogue is byte-identical to the shipped copy, both locales, derived from source |
| — | verified | `web/selfcheck.py` is wired, its detector runs, its reach is 4 of 31 labels, and the other 27 are covered by the same rule over rendered HTML |

---

## Amendment log

| Date | Change | By |
|---|---|---|
| 2026-10-22 | v2.0 — rework pass. **S2 passes.** Five blocking findings and the escalation closed; A-22 re-pointed with both halves and the no-count clause; the guard-for-the-guard converted rather than deleted; the SQLite introspection limit corrected (QA's finding was wrong); the photo race re-measured green; the copy catalogue verified independently of the fix; `web/selfcheck.py` wired with its reach measured at 4 of 31 and the gap closed over rendered HTML; both frontend fixes verified from the outside with a time-shifted fixture. One new finding (F46, the SQLite reverse) and one carried (F44's media half) | test-qa |

---
---

# REWORK PASS — `2af14de..81e8f60` (2026-10-22, test-qa)

**Scope: this diff only.** The v2.0 verdict above stands unamended. This
section verifies the rework that followed `REDTEAM-S2.md` F47–F54,
`REVIEW-S2.md`'s rework pass (B-R1 and R-R1…R-R7) and amendments **A-25
through A-28**. I wrote none of the code and none of the tests under review;
the 81 tests quoted below are mine and are in six new files, none of which
edits a file owned by another agent.

## VERDICT

**DOES NOT PASS. One blocking finding set, one required, both against A-28 —
not against the build.**

Four of the caller's five priorities pass cleanly and two of them pass
emphatically. **The EXIF stripper survived every real-world shape I could
build**, including the two that would have put a GPS tag in a stored object,
and it survived 3,200 mutated uploads without once raising anything but
`ImageRejected`. The migration's refusal is not only correctly worded, the
recovery it prints **converges when followed**, which is the half a
message-text assertion cannot reach. P15's sweep is an age, in both roots,
across the whole boundary, and it runs on an invocation that dies on its
first argument. The `Vary` exemption is honest and its declared ceiling is
real, measured rather than read.

**What blocks is A-28's rule-12 discharge.** A-28 exempts `dialable` and
`linked` from four catalogue fields and makes the exemption conditional on
one named layer — the review queue, *"after F50 the reviewer is shown the
title, the publisher and the edition"*. Measured: for one of the four fields
the reviewer is shown **nothing**, and for all four the catalogue row reaches
a student on a path the review queue is not on. Under rule 12 that makes the
exemption a widening on those surfaces, not a clarification.

## 18. Measurement, with the reach of each instrument

### 18.1 Baseline at `81e8f60`, confirmed not assumed

cto's table reproduced exactly, both engines, before I added anything:

| Engine | Result | Skips | Wall |
|---|---|---|---|
| PostgreSQL 16 (`BOOKHOP_TEST_DB_NAME=test_qa_rework`) | **1 failed**, 1752 passed, 2 xfailed | 59 | 52.6s |
| SQLite (`bookhop.settings.dev` default, `.env` **not** sourced) | **2 failed**, 1680 passed, 1 xfailed | 131 | 40.8s |

Both failures are the two open documents findings cto named: F44 on both
engines, F46's round-trip on SQLite only. **Nothing contradicted.** The skip
count is the engine tell and both matched, so neither run was silently on the
other engine.

### 18.2 After this pass — 81 new tests

| Engine | Result | Skips |
|---|---|---|
| PostgreSQL 16 | **4 failed**, 1829 passed, 2 xfailed | 60 |
| SQLite | **5 failed**, 1757 passed, 1 xfailed | 132 |

The three new failures are identical on both engines and are all mine: the
three A-28 findings in §18.4. The pre-existing two are unchanged. **Run
budget honoured: two full-suite runs on each engine, baseline and final,
nothing in between.**

The new set measured alone, so its reach is quoted rather than inferred —
**81 collected, 77 passed, 3 failed, 1 skipped**:

| File | Collected | Reached | Result |
|---|---|---|---|
| `tests/contract/test_the_exif_stripper_under_real_shapes.py` | 42 | 42 | green |
| `tests/contract/test_the_backfill_refusal_is_actionable.py` | 12 | 12 | green |
| `tests/contract/test_the_review_copy_sweep_is_an_age.py` | 16 | 15 | green, 1 platform skip |
| `tests/contract/test_the_vary_exemption_is_narrow.py` | 3 | 3 | green |
| `tests/contract/test_the_document_checks_can_still_fail.py` | 4 | 4 | green |
| `tests/contract/test_a28_the_layer_that_was_named.py` | 4 | 4 | **3 red — the findings** |

### 18.3 Priority 1 — the EXIF stripper, run rather than read

Code Review verified termination and bounds by reading. **Verified here by
running, on both engines, 42 of 42 subjects reached.**

Seven real-world shapes, each asserted accepted *and* carrying nothing out —
both halves in one subject, because a stripper that refused all of them would
satisfy a "no metadata survives" assertion vacuously:

| Shape | Why it is the shape that matters | Result |
|---|---|---|
| Google Motion Photo / Top Shot — MP4 `ftyp` + `moov` after EOI | F47's own example: the old copy ran to `len(data)` | **stripped at EOI** |
| MPF (CIPA DC-007) second image **with its own EXIF APP1 and GPS IFD** | the sentence in the module docstring, built and run | **second image gone** |
| Progressive JPEG, SOF2, three scans, APP1 and COM **between** scans | the case the one-line `find` would have got wrong | **all three segments gone** |
| EXIF APP1 containing a whole JPEG thumbnail with its own SOI/EOI | the trap a `find(b"\xff\xd9")` falls into — every phone writes one | **not truncated** |
| `FF FF FF` fill bytes before markers | permitted by the specification | accepted |
| entropy containing `FF 00`, RST0/RST1/RST7 and the sequence `FF 00 D9` | the three things the walk must not read as an end-of-scan | accepted, walk correct |
| no metadata at all | the negative control | accepted |

Plus, on each of the seven: exactly **one** EOI in the output and it is the
last two bytes; and **idempotence** — a second strip returns identical bytes,
which matters because `sha256` is the content half of the storage key and the
UNIQUE `(listing_id, sha256)` index 0004 adds.

Eleven refusal shapes, each refused by name with a non-empty reason, never a
bare exception: SOI only, dangling `FF`, four truncation points, EOI removed,
4,000 markers and no frame header, length past the end, length below the
minimum, a frame header too short for dimensions, and a non-marker byte where
a marker must be.

**Reach quoted because it is the point:**

* **truncation sweep — 395 of 395 prefixes** of the 395-byte baseline tried.
  Exactly one was accepted (the whole file) and it ends at an EOI. A dropped
  3G upload cannot produce a stored object whose end nobody can locate.
* **mutation fuzz — 8 seeds × 400 mutations = 3,200 mutated uploads** across
  five base shapes (baseline JPEG, Motion Photo, MPF, PNG with `tEXt`, WebP
  with `EXIF`), 1–6 byte-flip / truncate / append operations each. **Every
  one returned or raised `ImageRejected`** — no `IndexError`, no
  `struct.error`, no hang. Wall clock for the whole file: 0.9s against a 20s
  per-seed budget, so the super-linear half of "termination" is measured too.
  *Ceiling, declared:* it samples. A shape needing three coordinated
  mutations is not reachable from here; the seven named shapes are the
  structured half.
* **the boundary the row claims, not the function's** — one journey test
  uploads the Motion Photo through `add_photo` and reads the object back out
  of the store: no `ftyp`, no `Exif\0\0`, no canary, `exif_stripped_at` set,
  `bytes` equal to the stored length, and `sha256` equal to the digest **of
  the stored object** and not of the upload. Between `strip_metadata` and the
  row sits code that could have hashed the original, and the unit tests
  cannot see it.

**PASSES.** Two non-blocking observations in §18.9.

### 18.4 Priority 2 — A-28 attacked. THREE FINDINGS, ALL RED

#### F47-Q1 · BLOCKING · A-28's named layer does not cover `authors`

`tests/contract/test_a28_the_layer_that_was_named.py::test_the_moderator_is_shown_the_authors_field_that_was_exempted`

`create_book` checks `authors` per element for the reason A-26 gave — *"a
channel in `authors[1]` renders exactly as widely as one in `title`"* — and
`authors` renders on `/listing/{id}`, `/sell`, `/sell/find-book` and
`/sell/{id}/photos`. A-28 removed `dialable` and `linked` from it and named
the review queue as the layer.

**Measured.** A book with `authors = ["B S Grewal", "notes wa.me/919840012345"]`,
a listing of it in `PENDING_REVIEW` (premise asserted), and **the complete
reviewer-facing output of both `review_listings` modes**:

```
#1  2026-10-22 14:47  signup  9788177589139  Engineering Mathematics  Rs 300.00  GOOD  damage=none  photos=0  verified_book=False  suspect=False  seed=True
#1  PENDING_REVIEW  signup
  book          9788177589139  Engineering Mathematics
  edition       44th edition  Khanna  -
  asking        Rs 300.00
  condition     GOOD  annotations=NONE
  damage        none claimed
  category      PRESCRIBED_TEXTBOOK  language=en
  book verified False  suspect=False  seed=True
```

`authors` is on neither line. `queue_rows` does not assemble it and `_show`
does not print it. **For one of the four exempted fields there is no second
layer at all** — the channel reaches every student who opens the listing and
no human who could stop it. Rule 12: *"before granting any exemption, name
the other layer that still catches it — if none does, it is a widening."*

Cheapest fix, and it is not mine to make: one line in
`review_listings._show`. The alternative — re-applying the limbs to `authors`
only — is a contract decision and runs into the same false-positive question
A-26/A-27/A-28 spent three rounds on.

#### F47-Q2 · BLOCKING · the catalogue is not behind the review queue at all

`…::test_a_poisoned_catalogue_row_reaches_a_student_without_any_listing`

`books` is global (`ADR-002` §2) and live at `create_book`. The review queue
reviews **listings**. Measured, in one journey:

1. `create_book(title="Engineering Mathematics wa.me/919840012345")` — accepted
   under A-28, correctly per the ruling;
2. `review_listings --staff …` prints **"Nothing is waiting for review."**
   (asserted, so this is genuinely the no-listing path);
3. a signed-in student GETs `/sell/find-book?isbn=9788177589139` → **200**, and
   the body contains `thematics wa.me/919840012345</p>`.

So the channel is being served to students while the layer A-28 names has
nothing in it. The view's own docstring is explicit that showing the
catalogue is intended — *"What this page may show is the catalogue … no
listing, no price and no person"* — which is why this is a finding against
the **ruling**, not against the view. Two consequences the ruling does not
address: a seller who never publishes leaves the row poisoned indefinitely,
and **rejecting a listing does not unwrite the row**, so the next seller's
listing of that ISBN carries it.

**Escalation to cto against A-28.** F47-Q1 and F47-Q2 are one question: the
exemption was granted on a layer that covers the listing surface and not the
catalogue surface the exemption is about. I am not proposing which way it
resolves; the options I can see are a reviewer view of `authors`, a staff
check on `books` before a row is searchable, or `addressed`-plus-something on
catalogue text. All three are contract decisions.

#### F47-Q3 · REQUIRED · the limb A-28 kept fires on a real title shape

`…::test_the_kept_limb_does_not_fire_on_a_real_published_title`

A-28: *"`addressed` stays because an `@` followed by a non-space has no
false-positive class in bibliographic text; it is the limb that never fired
on anything real."* `_addressed` is `re.search(r"@[^\s@]", text)`. Measured
on `contact_channels_in(v, ("addressed",))`:

| Title | Result |
|---|---|
| `@War: The Rise of the Military-Internet Complex` | `['addressed']` → **refused** |
| `Love@First Site` | `['addressed']` → **refused** |
| `Chat@Work: Email and the Office` | `['addressed']` → **refused** |

`@War` is a published book (Shane Harris, 2014). **I cannot check an ISBN
from this machine**, so the claim I am making is the narrower and sufficient
one: titles of this shape exist in print, and `create_book` is the only path
for a book not already in the catalogue, under the sentence *"Enter what is
printed on the book."* No workaround exists.

This is the third round of rule 13's named failure on one rule, and it landed
on the limb A-28 kept — the same way A-27's landed on the limb A-26 kept.
A-27 wrote the lesson: *"asking the question once and treating it as asked is
its own failure mode."* A-28 asked it of `dialable` and `linked` and asserted
the answer for `addressed`.

**Severity is lower than B-R1's** and that is why this is required rather
than blocking: a hyphenated year range is in a large fraction of Chennai
syllabus titles, an `@` is in very few. It is still a red test on a real
title, which rule 13 says precedes an edit to `apps/core/contact.py` under
schedule pressure.

The accepted side is a row too (rule 10's corollary): the five strings that
broke A-26 and A-27 — `A History of India 1707-1947`, `Journal 2019 2020
2021`, `Physics/Chemistry Combined`, `Physics ISBN 978-93-5260-123-4`,
`Collected Works 1 2 3 4 5 6 7 8 9 10` — are all **accepted and stored
unchanged**, asserted, green. A-28's own ruling holds on every shape it was
written for.

### 18.5 Priority 3 — the migration's backfill refusal. PASSES

Backend's own test asserts the exception type and two message fragments on
one of three reachable causes. Twelve subjects added, all green:

* **eight clause subjects, one parametrised test each** — the row id, *"will
  not mint a token"*, `purge_media`, `erasure`, *"NULL storage_key"*,
  *"re-run"*, *"put it back"*, `INFRA.md`. One assertion per clause, because
  an aggregate lets a second missing clause hide inside the first.
* **three identifiers interpolated, not described** — row pk, listing id and
  the `storage_key` that does not resolve are all in the message.
* **two refusal causes nothing had reached.** A file **is** in the listing
  directory and is **not** this row's bytes → refused on the content check,
  the row unchanged, and **the stray file survives** (a migration that
  deleted what it declined to adopt would destroy what recovery 2 asks the
  operator to put back). And the whole `media/listings` tree removed — the
  `INFRA.md` §3 restore state — which returns from `_adopt` before reading
  anything and is a different code path from one missing file.
* **the recovery converges, which is the assertion a message-text check
  cannot make.** Two photographs on one listing, one file gone for good. The
  backfill refuses; the operator does exactly what the message says (*"null
  it and re-run"*); the re-run completes, the surviving photograph still
  reads back **byte-for-byte**, its row carries a token, and the nulled row
  is **not** given a key again.

Rule 10's sixth disguise is specifically that a refusal can look like the
guard working. Here the refusal is the guard working, and the instruction it
prints is one an operator can follow at 3am.

### 18.6 Priority 4 — P15's sweep is an age. PASSES

`COMPLIANCE.md` §7 row 25's enforcement clause is *"a sweep of
`bookhop-review-*` directories older than 24h, in `tempfile.gettempdir()`
and in any `--photos DIR`, run at the top of every `review_listings`
invocation."* Sixteen subjects, 15 reached:

* **the boundary from both directions, seven ages, one subject each** — 0s,
  30min, 23h and 24h−60s survive; 24h+60s, 25h and 30 days go. Two points do
  not locate a threshold: an inverted comparison or a 24-*minute* constant
  passes a 25h-goes/60s-stays pair. `REVIEW_COPY_TTL_SECONDS == 24*3600` is
  asserted in the same test, so the rows cannot be testing a different rule.
* **the forbidden side of the name rule, which nothing asserted** — five
  stale-by-a-month bystanders in the same root survive: `pytest-of-praveen`,
  `pip-build-env-x7`, and the near misses `bookhop-export-stale`,
  `review-bookhop-stale`, `bookhopreview-stale`. Our own stale copy in the
  same root goes in the same call. A sweep that `rm -rf`'d everything stale
  in `gettempdir()` satisfies every assertion in
  `test_the_review_copies_expire.py` and destroys the developer's and the
  operating system's working directories.
* **`is_dir()` is load-bearing, so it is a row** — a stale *file* named
  `bookhop-review-notadirectory` survives, and does not stop the sweep
  reaching the real stale copy beside it.
* **it runs on an invocation that fails early.** `--staff
  nobody@nowhere.invalid` raises `CommandError`, **and the stale copies are
  gone and the deletion is printed**. If the sweep sat after `staff_actor`,
  the clock would run only on successful invocations — which is not a clock.
  The fresh copy survives that path too.
* **NOT VERIFIED, skipped with a reason rather than passed:** whether the
  prefix match is case-sensitive. `Path.glob` inherits the filesystem's case
  rules, so `BOOKHOP-REVIEW-x` matches here (win32/NTFS) and would not on the
  ext4 deployment target — and the two names cannot coexist as directories on
  this machine, so the row came out of the parametrised list rather than
  being quietly dropped. **ASSUMED THERE.** Nothing creates such a name
  today; `REVIEW_COPY_PREFIX` is the only writer.

### 18.7 Priority 5 — the `Vary` exemption and its ceiling. PASSES

* **The declared ceiling is real, measured.** The ponytail comment claims *"a
  header read in `web/context.py`, `web/forms.py` or a template tag is not
  seen. No such read exists today."* An AST walk over every module in `web/`
  except `views.py` finds **zero** `.headers` attributes and zero `HTTP_*`
  constants. There is no `templatetags` package anywhere in the tree. The
  claim holds.
* **The exemption is honest as used.** `_ip_ua` reads `User-Agent` and
  `REMOTE_ADDR`; the UA goes to `accounts.request_magic_link`, whose rate
  limits are keyed on the **email and the IP** and not on it, so nothing in
  any body depends on it. Checked, not taken on trust.
* **The exemption is wider than its defence, and that is now narrowed from
  my tree.** `HEADER_READERS_THAT_NEED_NO_VARY` exempts a **function**; the
  sentence justifying it is about **one header**. A `Save-Data` read added
  inside `_ip_ua` tomorrow is exempt for free, and `_ip_ua` is called from
  most write paths in the file.
  `test_an_exempted_function_reads_only_the_header_its_exemption_defends`
  asserts the resolved set of headers read inside each exempted function is a
  subset of `{user-agent}`, and fails by name otherwise. Rule 10's corollary
  on marks. Green today; no change to frontend's file.
* **One more hole closed from outside.** The structural walk keys on
  `Attribute(value=Name('request'), attr='headers')`, so `req.headers` or
  `self.request.headers` in a helper is invisible to it.
  `test_no_header_is_read_off_a_request_under_any_other_name` asks the
  property — **any** `.headers` access, whatever it hangs off — and is green,
  because the house style is `request` throughout. Cheap now, expensive later.

### 18.8 The F44 shape, hunted elsewhere as instructed

**cto's narrowing of F44's media check is correct and I am not overruling
it.** The retired pattern was `\bmedia\b|tarball|tar -|photo` over §3.3; the
new one asks for the control — an archive extracted **and** a stored-file
reference resolved. I have added three guards rather than a second opinion,
in `test_the_document_checks_can_still_fail.py`:

1. **Inverted, per rule 10's fifth disguise.** It imports and **runs** F44's
   real check and asserts it still raises *with the words "never opens it"*.
   There is one definition of the control and this cannot drift from it. It
   goes red on the commit that genuinely closes F44 — at which point it is
   deleted in that diff — and it goes red first on any accidental greening.
2. **The retired word-grep is shown to be green right now**, so the recorded
   reason for the narrowing is a measurement and not a story.
3. **The narrowed check is shown to be satisfiable** by the step cto
   proposes (`tar -xzf …` plus a `storage_key` resolution), because a control
   no reachable document can meet is rule 10's second disguise and gets
   deleted rather than met.

**The same shape found elsewhere — one instance, non-blocking.** Every test
in the tree that reads a document was inspected
(`test_append_only_by_behaviour`, `test_precondition_stacks`,
`test_open_criticals_are_honest`, `test_response_boundary`,
`test_s2_pages`'s REVIEWED.toml check, `test_s2_photos`'s locale checks,
F44's). All but one parse structure and carry a non-vacuity guard.

The exception is `tests/contract/test_open_criticals_are_honest.py`: after
extracting the two `xfail` marks it asserts the memo citation with
`re.search(r"ENGINEERING-MEMO\s*§1", source)` over the **whole file**.
Measured: `ENGINEERING-MEMO` occurs twice in `test_least_privilege.py`, at
line 3 (module docstring) and line 136 (the reason constant). **The docstring
alone satisfies it**, so the reason could lose the citation and the assertion
the test's own message describes would still pass. And it cannot be fixed by
searching the extracted mark text, because both marks are written
`reason=LIVE_CRITICAL` — the mark text is `'strict=True, reason=LIVE_CRITICAL'`
and contains no citation at all.
`test_the_open_critical_citation_is_asserted_on_the_reason_not_the_file`
resolves the constant through the AST and asserts the sentence a reader
actually sees on a skipped test. Green. Additive; their file is untouched.

**A disappearing failure, treated with the same suspicion as a new one:**
R-R2. `test_tenant_fk_migration.py::test_the_migration_round_trips_forward_reverse_forward`
still fails on SQLite, and it now fails **with the F46 finding** — the
`foreign key mismatch`, the cause quoted out of the migration's own reverse,
the measured control state (`tenant_identity_index: False`,
`campus_city_guards: 0`), the measured behaviour (*"a photo whose is_seed
disagrees with its listing was accepted, which is F34 reopened"*) and the
measured recovery (plain `migrate listings` raises; `--fake` to 0002 then
forward works). That is what R-R2 asked for and it is not a failure that went
quiet. **Verified.**

### 18.9 Other things found that no document specifies — non-blocking

1. **`_PNG_METADATA_CHUNKS` is dead and its docstring claims two uses that do
   not exist.** `apps/listings/images.py:208` says the named list is *"kept
   only for the error message and for the test's own assertions"*. Grepped:
   the name appears **once in the whole repository**, at its own definition.
   No error message interpolates it and no test reads it. The ancillary-chunk
   property below it is what does the work, which the comment also says.
   Rule 9's corollary — delete the explanation, or the constant.
2. **`PLTE` in `_PNG_KEEP_ANCILLARY` is dead.** `b"PLTE"[:1].isupper()` is
   `True`, so it is critical and kept by the `critical` branch before the
   allow-list is consulted. A reader could conclude the ancillary allow-list
   is what preserves palettes. It is not.
3. **`queue_rows`' printed line truncates the title to 48 characters**
   (`row['title'][:48]`). A channel placed past character 48 is invisible in
   the queue listing; `--listing N` shows the title untruncated, so the layer
   survives only if the moderator opens the listing. Observation, not a
   defect — but it is a second reason F47-Q1's fix should land in `_show`.
4. **The Tamil gate is closed and asserted closed, by existing tests**, which
   is what my charter requires rather than something I needed to add:
   `test_locale_gate.py` asserts the flag is absent-or-false by default, that
   it **cannot** be true while a blocking-class string is unreviewed, that a
   published Tamil notice is not served while it is off, that a stored user
   locale is gated too, and it carries a fixture-can-produce-the-condition
   guard. `locale/ta/REVIEWED.toml` exists and is asserted empty.
   `trust.photo.alt` is asserted inside a blocking class. **No Tamil copy is
   reported as verified anywhere in this section.**

### 18.10 NOT VERIFIED in this pass, and why

1. **Accessibility.** Unchanged from v2.0: no browser automation on this
   machine, so WCAG 2.2 AA is HTML-level only and the keyboard walkthrough
   and accessible-name criteria are still manual. This rework added CSS and
   template changes (`static/css/app.css` +50, `templates/listing.html` +94)
   that I have **not** re-walked.
2. **p75 LCP and p95 search latency.** S3, and they need a throttled browser
   profile.
3. **The `/media/` nginx `internal` probe** (A-25, R-R3). It is nginx
   configuration; no conformance test can run it and §3.3 step 6b is where it
   lives. **ASSUMED THERE.**
4. **F44's media half.** Still open, and now guarded against greening by
   accident.
5. **F46.** Open, backend's, and its diagnostic is intact.
6. **The EXIF fuzz samples; it does not prove.** Declared in §18.3.
7. **The case-sensitivity of the sweep's prefix on ext4.** §18.6, skipped
   with a reason naming platform and slice.
8. **Everything in the diff outside the five priorities**: `apps/accounts/services.py`
   (+20), `apps/listings/models.py` (+29), the `web/views.py` changes beyond
   the header recorder, and `COMPLIANCE.md` §8's new rows. Not examined. This
   was a scoped rework pass, not a second S2 pass.

## 19. Blocking list

| # | Finding | Owner | Test |
|---|---|---|---|
| **F47-Q1** | A-28's named layer does not cover `authors` — the reviewer is shown nothing, the student is shown everything | **cto** (ruling), then backend or frontend for `_show` | `test_the_moderator_is_shown_the_authors_field_that_was_exempted` |
| **F47-Q2** | The catalogue surface is not behind the review queue at all: a poisoned `books` row is served to a student with the queue empty | **cto** | `test_a_poisoned_catalogue_row_reaches_a_student_without_any_listing` |

## 20. Required (not blocking)

| # | Finding | Owner | Test |
|---|---|---|---|
| **F47-Q3** | `addressed` refuses a title of the `@War` shape; A-28's stated ground for keeping the limb is contradicted | **cto** | `test_the_kept_limb_does_not_fire_on_a_real_published_title` |
| F47-Q4 | `test_open_criticals_are_honest.py`'s memo citation is satisfied by the module docstring; the fix is to resolve the reason constant | test-qa (mine) | covered green by `test_the_open_critical_citation_is_asserted_on_the_reason_not_the_file` |
| F47-Q5 | Two dead declarations in `apps/listings/images.py` whose comments describe uses that do not exist | backend | none — a reading, not a behaviour |

## 21. Findings index · rework

| # | Status | Finding |
|---|---|---|
| F44 | **open, guarded** | §3.3 still never opens the media tarball; the check can no longer go green by accident |
| F46 | **open, diagnostic intact** | R-R2 fixed: the test reports F46 rather than dying of it |
| **F47-Q1** | **NEW, BLOCKING** | A-28's layer does not cover `authors` |
| **F47-Q2** | **NEW, BLOCKING** | A-28's layer does not cover the catalogue surface |
| **F47-Q3** | **NEW, required** | `addressed` fires on a real title shape |
| F47-Q4 | **NEW, low** | a memo-citation check satisfied by a docstring |
| F47-Q5 | **NEW, cosmetic** | two dead declarations with live-sounding comments |
| — | **verified** | the EXIF stripper, on 7 real-world shapes, 395 truncations and 3,200 mutations, at the function **and** at the row |
| — | **verified** | the 0004 backfill's refusal: every clause, three causes, and the printed recovery converges |
| — | **verified** | P15's sweep is an age across the whole boundary, in both roots, with the forbidden side asserted, and it runs on an invocation that fails early |
| — | **verified** | the `Vary` exemption is honest, its declared ceiling is real, and it is now narrowed to the one header it defends |
| — | **verified** | cto's F44 narrowing; endorsed and guarded three ways |

---

## Amendment log — rework

| Date | Change | By |
|---|---|---|
| 2026-10-22 | **Rework pass `2af14de..81e8f60`. DOES NOT PASS: two blocking, one required, all three against A-28 and none against the build.** EXIF stripper verified by running on Motion Photo, MPF-with-GPS, progressive-with-metadata-between-scans and an EXIF-embedded thumbnail, plus 395 truncations and 3,200 mutations, at the function and at the row. Backfill refusal verified clause by clause with the printed recovery executed. P15's sweep verified as an age across the boundary and on an early failure, with the forbidden side of the name rule asserted for the first time. The `Vary` ceiling measured and the exemption narrowed from QA's tree. cto's F44 narrowing endorsed and guarded by an inverted test; the same shape found in one other instrument and closed additively. Baseline reproduced exactly on both engines; two full-suite runs per engine and no more | test-qa |

---

# SECOND REWORK PASS — `8fbb63e..81b9153` (2026-10-22, test-qa)

Scoped to the A-29/A-30/A-31 rework fix. The original verdict, v2.0 and the
first rework pass above are untouched. **The instrument backend wrote is now
the control, so this pass audited the instrument by mutation rather than by
reading it** — every claim below has a mutation or a measurement behind it.

## VERDICT

# S2 PASSES — second rework

**Blocking: none.** Nothing measured in this pass serves seller-written
catalogue text to a reader who is not its author, on any of the five surfaces
that exist, on either engine.

**Three holes in the control were found and closed in QA's own tree**, one of
them live-and-unmeasured; **one behaviour nobody specified** was measured and
is handed to cto and product; the pre-existing F44/F46 reds are confirmed and
unchanged.

### Suite, once per engine, as the brief required

| Engine | Passed | Failed | Skipped | xfail | Wall |
|---|---|---|---|---|---|
| **SQLite** (no `.env`) | **1803** | **2** | **133** | 1 | 50.65s |
| **PostgreSQL** (`.env` sourced) | **1875** | **1** | **61** | 2 | 59.17s |

**cto's baseline is confirmed, arithmetically and by name.** The brief measured
SQLite 1794/2/132 and PostgreSQL 1866/1/60 on this commit. This pass adds nine
passing tests and one named skip, so 1794+9 = 1803 / 132+1 = 133 and
1866+9 = 1875 / 60+1 = 61. Both engines land exactly there, which is a stronger
confirmation than re-running the same number would have been.

The reds are the two already routed elsewhere, and they are the same two:
`test_the_backup_scope_and_the_restore_test_cover_the_same_things` (**F44**,
both engines, an `INFRA.md` §3.3 amendment) and
`test_the_migration_round_trips_forward_reverse_forward` (**F46**, SQLite only,
`listings/0003`'s reverse). Neither is this diff's — it contains no migration
and nothing under `INFRA.md`. **That is reasoning from the failure identity,
not a bisect**, same caveat as Code Review's.

---

## 22. The instrument — audited by mutation. It holds, and it has three holes.

`tests/unit/test_catalogue_text_gate_is_enforced.py` (543 lines, 26 tests with
the order test). The brief's question was *"can it be satisfied while a leak
exists?"* The answer is yes, three ways, **none of which has an instance in the
tree today**, and all three now have a test.

### 22.1 What the walk does catch — measured, not read

Three mutations, each applied to the clean tree at `81b9153` and reverted
(`git status` clean after each):

| Mutation | Result |
|---|---|
| inject `_leak = req.book.title` into `web/views._request_row` | **RED**, by name: `web/views.py:1814 in _request_row() — req.book.title` |
| rename the pinned receiver `_listings()` → `_svc` at `web/views.py:1559`, same object | **RED** twice: unknown receiver `_svc` **and** the stale-pin assertion for `_listings()` |
| inject `Book.objects.values_list("title", flat=True)` into `web/views.wanted` | **GREEN. All 25 tests passed.** |

So: the two defects' own shapes are caught with file, line and receiver; the
pin is genuinely keyed on receiver *spelling* and reddens on a changed receiver
even when the object is identical; and the third row is the hole.

**The declared ceilings are real.** `SEALED` is imported from
`SELLER_WRITTEN_TEXT`, and `test_catalog.py::test_every_seller_written_column_on_books_is_behind_the_gate`
forces any new text column on `books` into either that tuple or a declared
exempt set — so "a fifth column is sealed the same day with no edit to this
file" is a closed chain and not a hope. `title_norm` is exempt **and** is a
derived copy of `title`; the exemption is correct (`normalise_title`, never
typed) and I checked it is not served anywhere. The syntax narrowing
(`kind.title()` is a method, not a read) is asserted on seven read shapes and
five non-read shapes, both sides as rows.

**`ALLOWED` cannot go stale into a false exemption**, by construction and in
one measured case: it is keyed on the *enclosing function*, not the file, and
`test_every_allowance_matches_a_live_access` is parametrized per entry so an
entry matching nothing fails by name. I verified the equivalent staleness
assertion on the dynamic pin empirically (mutation 2 above fired it); the
`ALLOWED` one I verified by construction only.

### 22.2 Hole 1 · The ORM naming the column as a string — **declared, unmeasured, and the one I would have shipped**

The instrument's own docstring declares it: *"`values()` / `values_list()`
naming the columns as strings. Nothing in the tree does … Not covered here,
and no instance exists."* The first half is a claim about the repository and
nothing asserted it. Mutation 3 above is the measurement: a `values_list("title")`
in a student-facing view left **all 25 tests green**.

Rule 12 as amended today is the exact test to apply — *before granting any
exemption, name the other layer that still catches it; if none does, it is a
widening*. There is no other layer. `F("book__title")` inside an `annotate` is
the worse form: it reaches a payload with **no attribute access anywhere** for
a name-based walk to see.

**Closed, in QA's tree**, because tests are QA's and `tests/unit/**` is not:
`tests/contract/test_catalogue_text_gate_blind_spots.py::test_no_sealed_column_is_named_as_a_string_to_the_orm`.
It walks `apps/**`, `web/**` **and `bookhop/**`** for a sealed column named as
a string literal to `values` / `values_list` / `only` / `defer` / `F` /
`Value` / `annotate` / `aggregate`, matching `title` and `book__title` but not
`title_norm` or `isbn13`. Re-run with the mutation in place: **RED**,
`web/views.py:1747 values_list('title')`. Clean tree: **green, 0 rows.**

`order_by` was in that list **for one run** and matched three live legitimate
sites (`apps/catalog/services.py:293`, `:302`, `:456` — a search and
`prescribed_for_course`, ordered by `title` / `book__title`). Ordering by a
column does not put it in the result set, so the match was *wrong* rather than
inconvenient, and rule 13 says the answer is to narrow my own guard, not to
leave a red on correct code. Narrowed to the calls that carry a value out, with
the removal and its reason recorded in the file.

### 22.3 Hole 2 · Roots the walk never opens — **undeclared**

The walk's scope is `apps/**` and `web/**`. `bookhop/**` — the URLconf, the
settings package, the WSGI entry point — is walked by nothing and is not among
the three declared holes. No instance exists (I grepped it for all four sealed
names: zero hits), and an L2 handler is conventionally under `apps.`, which is
what `_route_exists` relies on. But an undeclared scope gap is the same shape
as the two misses.

Closed by `test_no_sealed_attribute_is_read_in_a_root_the_instrument_does_not_walk`,
which **reuses backend's `_sealed_reads`** rather than restating what a read is
(rule 11: if backend widens the definition this moves with it; if the function
is deleted this errors on import instead of passing quietly) and asserts its
own reach — `bookhop/**` must yield at least one parsed module or the clean run
means nothing.

### 22.4 Hole 3 · `Book.__str__`'s allowance names a surface that is not installed

`ALLOWED[("apps/catalog/models.py", "Book.__str__")]` reads *"`__str__` reaches
the Django admin and the logs, both of which are staff surfaces."*

**Measured: `django.contrib.admin` is not in `INSTALLED_APPS` at all** — zero
hits across `bookhop/settings/*.py`. And the logs half is thinner than it
sounds: the one log line in `apps/**` that touches a book logs `book.id`
(`apps/catalog/services.py:248`). So the allowance permits a read whose named
consumers are one non-existent surface and one that does not use it — while
every call site it *could* acquire (`str(book)`, `f"{book}"`, `{{ book }}`,
`"%s" % book`) is invisible to a walk keyed on attribute names. From outside,
*"nobody stringifies a `Book`"* and *"the allowance is covering a leak"* are
indistinguishable, which is rule 10's fifth disguise.

Inverted rather than argued:
`test_nothing_stringifies_a_book_while_str_returns_seller_written_text` reddens
the day a `str(book)` / f-string / `{{ book }}` lands in `apps/**`, `web/**`,
`bookhop/**` or `templates/**`, and
`test_the_admin_named_in_the_str_allowance_is_still_absent` reddens the day the
admin is installed. **Ceiling declared in the file:** rows 1 and 3 match source
text, so a column named through a variable or a `Book` stringified through an
alias gets through, and the layer above that is a human reading the diff —
stated as the honest ceiling rather than papered over with a second
instrument.

**To backend, not blocking:** the allowance's reason should say what is true —
that `__str__` has **no call site** — rather than naming the admin.

### 22.5 The sixth read path — what I looked for and did not find

Ruled out by grep and then by reading each hit, across `apps/**`, `web/**`,
`bookhop/**`, `templates/**`:

- **Templates.** All six include sites of `_withheld.html` and every
  `{{ …title }}` / `.authors` / `.publisher` / `.edition` read in
  `listing.html`, `sell.html`, `sell_find.html`, `sell_photos.html`,
  `wanted.html` read `_book_of`'s or `_request_row`'s **dict**, never a model.
  **And this is now measured behaviourally, not just read** — see §23: the raw
  title's absence is asserted in the rendered body of all five page shapes,
  `<title>` included. That is a stronger instrument for templates than an AST
  walk could be, and it closes the one declared hole whose only evidence was
  *"Code Review verified"* (rule 9: a document's claim is not evidence).
- **Serializers.** There is no DRF, no pydantic, no ninja `Schema`, no
  `from_orm`, no `ModelSerializer`, **no `ModelForm`** — `web/forms.py` is
  hand-written. A `ModelForm` bound to a `Book` would render the title into an
  `value=` attribute with no attribute read in our source; that vector is
  empty, and it is empty because the project has no model-bound forms at all.
- **Stringification and reflection.** No `str(book)`, no `f"{book}"`, no
  `model_to_dict`, no `vars()`, no `operator.attrgetter`. The two `__dict__`
  uses are `apps/core/logging.py`'s on a `LogRecord`.
- **Computed attribute names.** Two sites in the tree, both pinned, both
  verified live by the pin's own staleness assertion (`web/views._transition`
  on the services **module**; `open_discovery.checklist` on a `legal_entities`
  row). Neither receiver can be a `Book`.

### 22.6 One stale sentence inside the control — rule 9's corollary

`test_the_walk_does_not_fire_on_these` still carries the parametrize reason
`'x = getattr(book, name)'` → **"a computed name — covered by
test_forbidden_source"**. That is precisely the claim the same file's docstring
withdraws four paragraphs earlier, and the one backend self-caught. The
docstring is right and the parametrize id is the withdrawn version, printed in
test output. **Delete the explanation** (rule 9's corollary); the shape still
belongs in that list, the reason is now the pin below it. Not blocking — the
behaviour is correct and the pin is real — but a withdrawn claim left live in
the file whose job is to stop withdrawn claims.

---

## 23. The withheld branch — a11y evidence, five of five page shapes

Code Review's gap: *"QA's fixtures use the verified `book`, so no a11y test has
rendered `_withheld.html` at all."* Correct, and it was rule 10's fourth
disguise in **QA's own harness for the third time** — the S2 sweep asserted it
reached five pages and every one of them was the verified branch.

Closed, not skipped. `tests/a11y/test_s2_pages.py` gains a `withheld_pages`
fixture and two tests. The branch needs a reader who is **not** the catalogue
entry's author, and `conftest.py`'s `seller` *is* `student`, who wrote
`unverified_book` — so the fixture is a second seed actor who lists and wants
Priya's row. The listing stays **DRAFT**, because A-29 §2 is the reason no other
status exists for it.

**Count actually reached: 5 of 5**, asserted in the test rather than quoted in
this report:

| Page shape | Reached | Withheld sentence | Raw title in body |
|---|---|---|---|
| `/sell` | yes | yes | **no** |
| `/sell/find-book?isbn=…` | yes | yes | **no** |
| `/listing/{id}` | yes | yes | **no** |
| `/sell/{id}/photos` | yes | yes | **no** |
| `/wanted` | yes | yes | **no** |

**Structural WCAG 2.2 AA violations on the withheld branch: 0** (SQLite and
PostgreSQL). Two guard assertions run *before* any a11y rule, so a fixture that
stopped producing a withheld row fails loudly instead of reporting verified-branch
coverage twice: the `trust.book.withheld` sentence must be present, and the
seller's raw title must be absent from the whole body — which covers
`document.title`, since `{% block title %}` reads the same dict. The final
assertion is `reached == len(pages) == 5`, so the number in this table is a
measurement.

Tamil: `test_no_withheld_page_serves_tamil_while_the_locale_is_closed` asserts
all five answer `Accept-Language: ta` with `lang="en"`. `trust.book.withheld`
is a **new blocking-class string with an unread Tamil draft**
(`locale/ta/BLOCKING_CLASSES.toml`'s own counter records `+1 string, +1
blocking`), so the only check available is that it is unreachable, and that is
the check. **This is not Tamil a11y verification and must not be reported as
any.**

**Still not verified, same as every pass:** the keyboard-only walkthrough. No
browser automation exists on this machine; `test_pages.py`'s skip names the
slice and this file does not weaken it. **Automated structural checks alone are
not an accessibility pass**, and the withheld branch's new `.meta` paragraph has
not been met by a screen reader.

---

## 24. `--verify-book` — the order assertion reddens, and nothing else can stamp

**Mutation: `self._show(listing)` moved back inside `if not options["action"]`,
after the verify block — the exact pre-fix shape.**

- `test_the_review_command_prints_the_text_before_it_stamps_the_book` → **RED**:
  `'Higher Engineering Mathematics' never reached the terminal`. The captured
  output of the one-command invocation was two lines — the stamp confirmation
  and `listing 1 is now LIVE` — with **none of the four strings printed.** The
  defect was real and the order test is the test that sees it.
- `test_the_review_command_prints_authors_and_can_check_the_book` → **PASSED on
  the broken code**, which confirms Code Review's reasoning for writing an
  order assertion instead of a presence one: the sibling test runs `--listing`
  and `--verify-book` as two commands, which is the safe ordering.

**No other path can stamp.** Measured: `verify_book` has exactly **one** caller
in `apps/**` + `web/**` (`review_listings.py:129`), `staff_verified_at` is
assigned in exactly **one** place (`apps/catalog/services.py:437`), `_show` now
runs unconditionally for every `--listing` invocation *before* that block, and
there is no API endpoint and **no Django admin** through which the column could
be written. The order assertion covers the only path that exists.

---

## 25. The dynamic-`getattr` gap — confirmed closed, and confirmed it was open

Backend's self-correction is accurate and I verified both halves independently.

- **The gap was real.** `tests/unit/test_forbidden_source.py::test_apps_contains_no_dynamic_attribute_construction`
  matches `node.func.id in ("setattr", "delattr")` and nothing else. A *read*
  through a computed name was outside every control in the repository.
- **It is closed.** `test_a_dynamic_attribute_name_is_pinned_to_a_non_book_receiver`
  walks `web/**` **and** `apps/**`, flags any `getattr` whose second argument is
  not a string literal, and its stale-pin assertion proves both pinned sites are
  live (it would fail if either had moved).
- **It reddens on a changed receiver.** Mutation 2: `_listings()` → `_svc`, same
  module object, same call. Two failures — the unknown receiver and the now-stale
  pin. The key really is the receiver's source text, as documented.

This is `CLAUDE.md` rule 12's amended shape found inside the file whose job is to
prevent it, and self-caught before QA arrived. Recorded as the control working.

---

## 26. The S3 forward guard — written, with its failure branch exercised now

Nobody owned it. `apps.discovery` is S3's, it is the first listing read where
the reader is a **buyer** rather than the row's own actor — so it is the first
place A-29 §1 is the **only** layer — and nothing obliged its author to ask the
gate. `test_listing_detail_is_still_an_own_rows_read` reddens on the promised
one-line swap, which tells the author the *reader* changed and says nothing
about whether the new module asks the gate at all.

Written in `tests/contract/test_future_stack_placements.py`, which is where this
shape already lives, as three tests:

1. `test_the_discovery_listing_read_asks_a29s_gate_the_day_the_app_exists` —
   **inverted** per rule 10's fifth disguise. While `apps.discovery` is absent it
   skips *naming the app and the slice*; once it is in `INSTALLED_APPS`, three
   things become failures: the app has no Python, nothing in it calls
   `served_book_text` / `book_block` / `_book_of`, or the gate has been renamed
   out from under the spelling this guard matches. It deliberately does **not**
   predict which function reads the listing or what the payload is called — S3 is
   not designed, and a guard that predicts shape is the one that gets edited
   (rule 13).
2. `test_the_failure_branch_of_the_discovery_guard_still_exists` — **the guard
   for the forward-dated guard.** The predicate is a pure function of source
   text, so both sides run **today**, on three synthetic modules: one that serves
   `row.book.title` raw (must be False), one that keeps its **own copy** of the
   `staff_verified_at` condition instead of asking (must also be False — that is
   the rule 11 defect and the one a reviewer waves through), and one that calls
   `book_block` (must be True). Without this, *"skipping until S3"* and *"a
   predicate that cannot return False"* are indistinguishable.
3. `test_the_discovery_app_is_still_absent_so_the_skip_is_honest` — absence
   checked **two** ways, `INSTALLED_APPS` and the directory. A half-landed
   `apps/discovery` on disk but not installed would make guard 1 skip during
   exactly the commits it exists for.

Status on this commit: **2 passed, 1 skipped with its reason naming app and
slice** (`apps.discovery does not exist yet (S3) — engine-independent`), on both
engines.

---

## 27. A-29, A-30, A-31 — the sixth ruling, measured

The brief asked for this plainly, so plainly: **A-31 holds. Both halves. This is
the first of the six I could not find a way to break.**

**A-31(a) — `text_withheld` on the requests `book` sub-object.** Exercised on
both engines, both branches — **by backend's own test, which QA ran rather than
wrote**, and that provenance is stated because running the author's test is not
independent verification:
`GET /api/v1/requests` returns `text_withheld: true` with
`title: "ISBN 9789387432147"` on the unverified row and `text_withheld: false`
with the real title on the verified one, and the raw string appears nowhere in
the unverified response body. The ruling's reason is the right one and is
testable as stated: without the key a client renders a book *called*
`ISBN 978…`, which is the gate producing a falsehood instead of a silence.

**A-31(b) — the viewer-form is strictly tighter than the owner-form.** This is
the claim to attack, because it is the one that overrules the contract with the
code. I attacked it and it holds. Construct the S3 case: `discovery.get_listing`,
buyer reading a listing whose seller **is** the book's author, layer 1 regressed.
Owner-form passes the seller → `may_read_unverified_text` is true → **the raw
string reaches the buyer.** Viewer-form passes the buyer → withheld. The two
differ exactly where it matters and the code's choice is the safe one, so the
wording yielding to the code is correct, and *"my wording would have made this
page depend on one layer where the code makes it depend on two"* is the
accurate statement of it.

**A-30, as it now stands.** The `Vary` paragraph is struck through in
`API-CONTRACT.md` with the three measurements that killed it, and the surviving
ground — the author wrote the string, so withholding it from them protects
nobody — is the one the code rests on. I checked the strike-through is a strike
and not a rewrite, and that A-30's live text no longer asserts an unmeasured
layer. It does not.

**A-29 §1's narrowing, re-checked against QA's own test.**
`test_a_poisoned_catalogue_row_reaches_a_student_without_any_listing` fetches
`/sell/find-book?isbn=` as the author and passes **without being edited**, which
is the outcome to prefer and the one A-30 predicted.

So: of six rulings on this question, the outcome has held twice (A-29 §1–§3,
A-31) and the reasoning now survives measurement for the first time, because the
sentence that did not survive has been deleted rather than repaired. The pattern
cto recorded about itself — *three times rule 12 was satisfied by naming a layer
and never measuring it* — did not recur in A-31. **It recurred once in this
diff, in backend's file, and backend caught it itself** (§25). That is the
control working rather than the pattern continuing.

---

## 28. Behaviour no document specifies — **measured, and handed over**

### F51 · A student's own typed title is discarded when their ISBN matches somebody else's unverified row

Not a leak, not a regression of this diff's fix, and **nobody's defect** — it is
two correct decisions composing into a page the product never described.

Measured end to end through the real form, as a second student (`/wanted`,
POST `isbn=9789387432147`, `title="Higher Engineering Mathematics"`,
`course_code=MA8151`):

| What | Measured |
|---|---|
| HTTP | `200` |
| `book_requests.free_text_title` stored | **`None`** |
| `book_requests.book_id` stored | `1` |
| the title the student typed, anywhere on `/wanted` | **absent** |
| what the row shows instead | `ISBN 9789387432147` + the withheld sentence |
| occurrences of the bare ISBN in the page | **3** |

The cause is `web/views.py:1779` — `free_text_title=None if book is not None
else (title or isbn)` — which predates this diff and was invisible while
`_request_row` served the book's raw title. A-29 §1 is what makes it visible:
the student now has a want list whose row has **no title at all, although they
typed one**, and their own words are not withheld but were never stored.

**The remedy is available and the schema already permits it.**
`DATA-MODEL.md` §3's CHECK is `(book_id IS NOT NULL OR free_text_title IS NOT
NULL)` — an **OR**, so storing both is legal, and the two clauses that key on
`free_text_title` requests (§ lines 1273, 1576) key on `book_id IS NULL`, which
a both-stored row does not satisfy. So `_request_row` could fall back to the
requester's own words when the catalogue text is withheld — which is exactly
what its docstring already says the gate does not touch.

**One consequence to decide with it, so the fix is not naive:**
`create_request`'s idempotency-by-shape filters on `free_text_title=title`, so
storing the typed title would make two submissions with different typed titles
for the same book two rows instead of one, and *"the match rate counts people
rather than taps"* is that filter's stated purpose.

**No test written for it**, deliberately: there is no specified answer to assert,
and inventing one in QA's tree would be QA ruling on product copy. **To cto and
product-manager.**

### F52 · A seller cannot see the title of their own listing

Same mechanism, different surface, and this one is A-29 §1 working exactly as
ruled. A student who finds an existing catalogue row by ISBN and lists their copy
is **not** that row's author, so `/sell`, `/sell/{id}/photos` and `/listing/{id}`
show them `ISBN 9789387432147` for a book they are selling. Measured on all three
in §23's fixture — that is what the five green page shapes are green *on*.

Correct per the ruling and per A-30's second ground. Whether it is the product
anybody wants is not in `PRD`, `JOURNEYS` or `COPY-DECK`, and the seller has no
way to learn why or to ask for the row to be checked. **To product-manager and
design-director**; the ISBN-twice duplication on `/wanted` is the fifth instance
of Code Review's S2-R2-S3 and is now also created on this surface.

---

## 29. What was NOT verified in this pass

- **Keyboard-only walkthrough of the withheld branch.** No browser automation on
  this machine. Structural HTML checks only, and they are not an accessibility
  pass.
- **Tamil, on anything.** The locale is closed and the test written is that it is
  closed. `trust.book.withheld`'s Tamil draft is unread by any native speaker.
  The banned-vocabulary check remains **English only** (THREAT-MODEL §6.1,
  accepted risk A9): **a Tamil string that warrants would pass this green suite**,
  and nothing in this pass changes that.
- **Performance.** No p75 LCP, no p95 search latency this pass; the withheld
  branch adds one paragraph and removes four strings, so no measurement was taken
  and none is claimed.
- **F44 and F46** — confirmed red, not diagnosed. Routed to `INFRA.md` §3.3 and
  backend respectively, as before.
- **`ALLOWED`'s staleness assertion** — verified by construction and by reading;
  only the dynamic pin's equivalent was verified by mutation.
- **`create_book`'s allowance is function-scoped**, so any future read added
  inside `create_book` inherits an exemption written for one `audit_log` line.
  No instance; worth one clause in that entry's reason. Suggestion only.
- **A whole-tree bisect** of either pre-existing red.

## 30. Findings index · second rework

| ID | Where | What | To |
|---|---|---|---|
| **F51** | `web/views.py:1779` | the requester's own typed title is discarded when the ISBN matches another student's unverified row; the want row shows no title at all. Schema already permits storing both | cto, product-manager |
| **F52** | A-29 §1, three surfaces | a seller is shown `ISBN …` for their own listing when they did not type the catalogue row; unspecified, no recourse path | product-manager, design-director |
| **F53** | `tests/unit/test_catalogue_text_gate_is_enforced.py` | hole 1 — the ORM naming a sealed column as a string was declared and unmeasured; an injected `values_list("title")` left all 25 tests green. **Closed in QA's tree** | backend (fyi) |
| **F54** | same file | hole 2 — `bookhop/**` is walked by nothing and the gap is undeclared. **Closed in QA's tree** | backend (fyi) |
| **F55** | same file, `ALLOWED` | hole 3 — `Book.__str__`'s allowance names the Django admin, which is **not installed**, and the permitted read has no call site. Tripwires written; the reason should say what is true | backend |
| **F56** | same file | the parametrize reason `"a computed name — covered by test_forbidden_source"` is the claim the same file's docstring withdraws. Delete the explanation | backend |

**Nothing above is blocking.** F53–F56 are findings against the control's text
and scope, each with a test now behind it; F51 and F52 are behaviours no
document specifies, which is the finding the charter asks for by name.

## Amendment log — second rework

| # | Change | Reason |
|---|---|---|
| 1 | verdict **S2 PASSES — second rework**, no blocking | three mutations on the control and five behavioural journeys found no reader served text they did not write |
| 2 | §22 added — the instrument audited by mutation, three holes, all closed in QA's tree | the brief: *"That instrument is now the control. So audit the instrument"* |
| 3 | §23 added — withheld-branch a11y, **5 of 5** reached, 0 violations | Code Review's *"the withheld branch has never been through an accessibility sweep"* |
| 4 | §24 added — the order assertion reddens on the old ordering; the sibling presence test passes on it | the brief's item 2, and it is the reason the order shape was the right one |
| 5 | §26 added — S3's forward guard, with its failure branch exercised on synthetic sources today | the brief's item 5, rule 10's fifth disguise |
| 6 | §27 — A-31 attacked on its own terms and holds | the brief: *"If the sixth is wrong, say so with the measurement"* |
| 7 | F51, F52 recorded with measurements and handed to cto and product rather than tested | no document specifies either; QA does not rule on product copy |
