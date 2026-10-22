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
