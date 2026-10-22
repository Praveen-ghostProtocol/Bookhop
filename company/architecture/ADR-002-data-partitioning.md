# ADR-002 — Data partitioning: multi-campus and multi-city from day one

**Status:** Accepted · **Date:** 2026-10-21 · **Decider:** cto
**Depends on:** ADR-001. **Constrains:** `DATA-MODEL.md`, `API-CONTRACT.md`.
**Inputs:** `CLAUDE.md` §Engineering standard ("multi-campus and multi-city in
the data model from day one; no premature microservices") · D-007 (v1 is **one
campus**) · `INCORPORATION-AND-BLOCKERS.md` §3 Gate A item A0 and Gate B ·
`COMPLIANCE.md` §2.4, §7.

---

## 1. The problem, stated precisely

Three requirements that are easy to conflate and must not be:

1. **v1 ships one campus** (D-007). Shipping a campus switcher nobody uses is
   scaffolding for a future that may not arrive.
2. **The data model must support many campuses in many cities from day one.**
   The expensive mistake is a schema where "campus" is implicit — a single
   `settings.CAMPUS_ID`, or a hostname, or nothing at all — because retrofitting
   a tenant key onto listings, transfers, reports and every analytics query is a
   migration across the whole database plus a rewrite of every metric.
3. **Discovery must be legally gateable per campus** (Gate A0 / Gate B). A
   browsable listing surface makes BookHop an e-commerce entity under
   r.3(1)(b)/r.4(1)(a), so "can students here browse each other's listings yet"
   is a per-campus, per-legal-entity, auditable fact — not a deployment detail.

Requirement 3 is the one that usually gets lost, and it is the one that makes
the partitioning decision load-bearing rather than cosmetic.

---

## 2. Decision

**One PostgreSQL database, one schema, one deployable. Every tenant-scoped
table carries `campus_id NOT NULL` and `city_id NOT NULL`. Scoping is enforced
in one place — a single `scoped()` helper that every read of tenant data must
go through — and verified by a test that fails if any tenant-scoped model is
queried without it. Cross-campus visibility is a per-listing
`visibility_scope` enum defaulting to `CAMPUS`, so widening to multi-campus or
city-wide discovery is a data change, never a migration.**

Concretely:

```
cities    (id, name, state, country_code='IN', ...)
campuses  (id, city_id FK NOT NULL, name, slug, email_domains text[],
           legal_entity_id FK NULL,
           discovery_enabled_at timestamptz NULL,   -- the Gate (see §4)
           active, created_at)
```

Tenant-scoped tables (all carry both keys): `users`, `listings`,
`listing_photos`, `book_requests`, `transfers`, `threads`, `messages`,
`reports`, `disputes`, `grievances`, `safety_incidents`, `handover_points`,
`prescribed_texts`, `search_events`, `support_tickets`, `notifications`,
`user_tombstones`.

Explicitly **not** tenant-scoped, and the reason for each:

| Table | Why it is global |
|---|---|
| `books` | A book edition is a global fact. ISBN 978-… is the same edition in Chennai and Coimbatore. Scoping it would duplicate the catalogue per campus and break edition-locking, which is the entire wedge. |
| `cities`, `campuses` | They are the tenant registry. |
| `legal_entities`, `gate_authorisations` | Company-level facts. |
| `notice_versions`, `consents`, `seller_terms_acceptances` | Consent is to a notice version, which is global. The `users` row carries the campus. |
| `audit_log`, `personal_data_access_log`, `jobs`, `feature_flags`, `idempotency_keys` | Infrastructure. Each row references a scoped object where one exists. |
| `repeat_infringer_records` | r.5(5) is a company-level obligation and must survive a campus being switched off. |

### Why `city_id` is denormalised onto tenant rows

It is derivable from `campus_id`, so this is a deliberate denormalisation.
Reason: **every multi-city report and every future residency or
sharding boundary is a city-level predicate**, and a two-hop join on every
analytics query is both slower and easier to forget. A trigger (or the service
layer — one place either way) sets `city_id` from the campus at insert, and a
nightly consistency check asserts `city_id = campus.city_id` for every scoped
row. One integer column per row buys a clean `WHERE city_id = ?` everywhere.
`# ponytail: denormalised city_id. Ceiling: a campus physically moving city,
which is a manual data fix. Upgrade path: none needed — drop the column and
join if it ever stops paying.`

### Denormalised tenant and seed columns are held by a COMPOSITE FOREIGN KEY, not by a nightly check

**Amendment 2026-10-22, on backend's S2 escalation — which I agree is the
most serious thing in the slice, and which has a better remedy than the one I
originally specified.**

S2's child tables (`listing_photos`, `swap_wants`) now carry denormalised
`campus_id`, `city_id` and `is_seed` **that nothing re-derives**. Backend's
statement of the risk is exact: **if either is ever written inconsistently
with its parent listing, the gated manager silently returns the wrong rows** —
and **every test sets both through the same service that sets them correctly,
so the fixture cannot produce the failure mode.** That is rule 10's fourth
disguise, in the control rather than in a test.

**My original remedy for `city_id` — a nightly consistency check — detects
and does not prevent, and detects up to a day late. That is the weaker
answer and I am replacing it.**

> **A composite foreign key makes the inconsistency IMPOSSIBLE rather than
> detectable.** One extra unique index on the parent and one `FOREIGN KEY`
> clause per child:
>
> ```sql
> -- parent: id is already unique, so any superset is trivially unique
> CREATE UNIQUE INDEX listings_tenant_identity
>   ON listings (id, campus_id, city_id, is_seed);
>
> -- each child, in place of a bare listing_id FK
> FOREIGN KEY (listing_id, campus_id, city_id, is_seed)
>   REFERENCES listings (id, campus_id, city_id, is_seed)
> ```
>
> **A child row referencing a parent with a different campus, city or seed
> flag cannot be written, on either engine, by any path** — service, admin,
> raw SQL, a migration, or a fixture. No trigger, no job, no window.

**The same move upgrades the `city_id` rule above**: a composite FK to
`campuses (id, city_id)` replaces the nightly check, so `city_id` on a scoped
row cannot disagree with its campus either. **Where a database can make a
class of wrong state unrepresentable, that beats detecting it — and I reached
for a job when a constraint was available.**

**The test that matters is the one whose fixture CAN produce the failure**
(§6.3's behavioural limb): a test that **writes an inconsistent child
directly, bypassing the service, and asserts the database refuses it.** A test
that goes through the service proves only that the service is correct, which
was never the thing in doubt.

`# ponytail: composite FK over a nightly job. Ceiling: the parent's tenant
columns become immutable in practice, since changing one would orphan its
children — which is correct, a listing does not change campus. Upgrade path:
none.`

### How scoping is enforced, so it cannot be forgotten

Two mechanisms, because a convention alone will be broken by the third
developer on a Friday:

1. **One helper, used everywhere.** `apps/core/scoping.py` exposes
   `scoped(qs, actor)` which applies `campus_id__in=actor.visible_campus_ids`
   (today: exactly one). Every service function that reads tenant data takes an
   `actor` and calls it. The service layer is the only place that reads models
   — views and API handlers never touch the ORM (`API-CONTRACT.md` §3).
2. **A test that cannot be argued with.** `tests/unit/test_scoping.py` walks
   every model listed as tenant-scoped, asserts `campus_id` and `city_id` are
   both `null=False`, and asserts that each has an index leading with
   `campus_id`. A new tenant table without the keys fails CI.
   `# ponytail: structural test rather than row-level security. Ceiling: it
   proves the columns exist and are indexed, not that every query filters.
   Upgrade path in §6.`
3. **The gated read is the DEFAULT manager, not an opt-in call**
   — **amendment 2026-10-21, accepting REVIEW-S0's proposal.**

> **Accepted, and it is a correction to my own §2 rather than an addition to
> it.** The review's argument is the one I should have made: *opt-in means
> every future reader must remember, and M0 has just demonstrated what happens
> when a control depends on remembering.* Mechanism 1 above said "one helper,
> used everywhere" and then relied on everyone choosing to use it — which is a
> convention wearing a constraint's clothes, exactly what §4's gate column
> turned out to be. **It is also less code in every service function rather
> than more**, which is the tell that it is the right rung.

**Slice: S2, confirmed 2026-10-21.** Backend asked for the slice to be named
rather than left as "in principle", and chose S2 on the grounds that the first
`is_seed` model arrives then, so it costs one Manager class and no rework.
**Confirmed, with one correction to the reasoning that is worth stating so
nobody later reads S1 as an oversight:** `users.is_seed` lands in **S1**, not
S2 — so the first `is_seed` *model* is S1. But **nothing in S1 reads users
through a gate**: there is no user directory, no member search and no
discovery of people, so a gated manager on `users` in S1 would gate nothing.
`listings` is the first model where a gated read has something to gate, and
that is S2. **So: the Manager class, `base_manager_name`, the allow-list and
the test all land in S2, and `users` is retrofitted in the same commit** — one
line, no rework, and S1 ships no ungated read because S1 has no such read.

> **RULING · `User` does NOT get the gated default manager. The premise above
> is FALSE and it is mine · cto, 2026-10-22** *(S2 backend escalation 1)*
>
> **Measured, not argued: applied exactly as this ADR and TASKS require, the
> retrofit broke 26 tests, all identity lookups.** The predicate hides every
> non-seed row on a closed campus — **which is every real student before Gate
> C** — and **every read of `users` is by identity.** My sentence *"S1 ships
> no ungated read because S1 has no such read"* is false: **S1 ships the
> session lookup and the magic-link request**, and both read `users`.
>
> **The error was a conflation, and naming it is the useful part.** I treated
> *"a read that needs gating"* and *"a read through the default manager"* as
> the same set. They are not. The gated manager gates **every** read through
> `objects`, including `User.objects.get(pk=session_user_id)` — which is the
> one read that must never be gated, because **authentication happens before
> any gate and cannot depend on one.**
>
> **And the 26 failures are not friction; they are the design saying the model
> does not apply.** Had it "worked", a real student on a closed campus could
> not be resolved from their own session — that is not a visibility control,
> it is an outage. **The discovery gate governs what you can SEE, never
> whether you EXIST.**
>
> **The criterion, so S4 does not re-ask it:**
>
> > **The gated default manager belongs on models whose rows are surfaced to a
> > user who did not create them, by search or browse — models that are
> > DISCOVERED. It does not belong on models RESOLVED by identity or by
> > ownership.**
>
> Discovered: `listings`, `listing_photos` (through its listing),
> `book_requests`. Resolved: `users`, sessions, tokens — **and `transfers`,
> which is read per-actor and is scoped by participation, not discovery**, so
> S4 should not add one there either. `scoped()` and the service layer remain
> the control for resolved models.
>
> **What enforces seed/real separation on `users` instead** — it was never the
> manager's job: `transfers`' `CHECK (seller_is_seed = buyer_is_seed)`, the
> `is_seed = false` filter on every metric view, and the discovery predicate
> on `listings` (a seller's identity reaches a reader *through a listing*,
> never through a user query). **`users.is_seed` is data those filters read,
> not a manager's predicate.**
>
> **Backend applied the base-manager and explicit-manager halves anyway, and
> they stay** — `all_objects` and `Meta.base_manager_name` on `User` cost
> nothing and keep the family consistent. **Only the gated default is
> refused.** The refusal is recorded as a test rather than a comment, which is
> the right artefact: a future retrofit attempt fails loudly instead of
> rediscovering 26 broken tests.

Every model carrying `is_seed`:

```python
class Listing(models.Model):
    objects     = GatedManager()      # excludes non-seed rows on a closed campus
    all_objects = models.Manager()    # explicit, greppable, reviewable

    class Meta:
        base_manager_name = "all_objects"   # see the Django note below
```

**Forgetting the gate now requires typing `all_objects`**, which a reviewer and
a grep both see. A test asserts (i) every `is_seed` model's default manager is
a `GatedManager`, and (ii) `all_objects` appears only in an allow-listed set of
call sites: fixtures, `seed_demo`, the staff/admin surface, the retention purge
and the metric exports. A new use outside that list fails CI.

> **THE DESIGN POINT THAT MATTERS MORE THAN THE SLICE — the manager sits
> UNDERNEATH `assert_discovery_open`, never INSTEAD of it.**
>
> A filtered manager makes a closed campus return **no rows**.
> `API-CONTRACT.md` §2.5 step 7 and §5.3 require a real student on a closed
> campus to receive **`403 GATE_CLOSED`**, and `TASKS.md` S3's three truths
> require the empty state to keep *"not on your campus yet"* apart from
> *"we don't recognise that ISBN"*.
>
> **If S3 lets the manager stand in for the helper, a closed campus silently
> renders an empty search page instead of the gate page — and the legal gate
> becomes invisible to the person it applies to.** That is strictly worse than
> the convention this replaces: the convention could be forgotten, but this
> would *look* like it was working.
>
> It is also exactly the substitution a future developer would make **believing
> it was a simplification** — two controls doing "the same thing", one deleted.
> They do not do the same thing. **One filters rows; the other tells a student
> why there are none.** `assert_discovery_open` is the legal control and the
> manager is defence in depth behind it; deleting the helper because the manager
> exists is a Code Review escalation, not a cleanup.

**Two Django specifics that make this safe rather than clever**, both stated
because a filtering default manager is a known footgun:
- **`Meta.base_manager_name = "all_objects"`.** Django uses the *base* manager
  for related-object descriptors and internal operations; pointing it at the
  unfiltered manager keeps `dumpdata`, migrations, cascade deletes and
  `refresh_from_db` correct. Without this line a filtering default manager
  silently breaks data integrity operations, which would be a far worse bug
  than the one it fixes.
- **Reverse relations: MEASURED 2026-10-22, and my prediction was WRONG in the
  helpful direction.** **Reverse accessors ARE gated on Django 5.2** — the
  reverse manager is built from the default manager, while `base_manager_name`
  keeps cascades and `refresh_from_db` correct. I predicted they were not
  covered and required a test either way; **the test is why we know, and
  "either way" is why the result is usable rather than a surprise.**
  Backend labelled it a **cross-library claim and pinned it**, so a Django
  upgrade turns it red instead of silently losing coverage — **rule 9's
  cross-engine limb used exactly as intended**, on a library rather than an
  engine.
  **Consequence: the manager covers more than I claimed, which strengthens the
  defence-in-depth case but changes nothing about the control.** `scoped()`
  and the service layer remain required, because `_base_manager` and raw SQL
  still bypass — and the composite FK above is what holds the tenant columns
  those paths would otherwise be free to break.
- *(Superseded, kept for the reasoning:)* **the gap is closed by a TEST, not
  by my argument.**
  v1.0 of this amendment asserted flatly that reverse relations are not
  covered. **That was reasoning where a measurement was available, and the
  reviewer is right to refuse it:** which access paths resolve the filtered
  manager differs by path *and* by Django version — direct queries, reverse
  accessors, `prefetch_related` and cascade collection do not all behave the
  same. **S2 ships a test that, for each gated model, asserts the gate applies
  on a direct query AND on a reverse accessor, and that `_base_manager` is
  unfiltered.** If it shows reverse relations are uncovered, the manager is
  defence in depth and the service layer remains the control — **which is fine,
  but it must be known rather than assumed.** Either way the `scoped()` helper
  and the service-layer discipline remain required.
  `# ponytail: gated default manager + base_manager_name escape. Ceiling:
  measured by the S2 test, not asserted here. Upgrade path: Postgres RLS (§6
  step 2), which is the only thing that closes raw SQL.`

---

## 3. What was considered and rejected

| Option | Why plausible | Why rejected |
|---|---|---|
| **No tenant key at all** (`settings.CAMPUS_ID`, one deploy per campus) | Simplest possible v1. Honestly the most "lazy" answer on the surface | Rejected by the engineering standard, and correctly: campus two means either a second database with a second backup, restore test, migration run and set of credentials — or the migration this ADR exists to avoid. It also makes every cross-campus metric a manual merge of two datasets, and `METRICS.md`'s "supply density per active campus" presupposes one dataset. |
| **Schema-per-campus** (Postgres schemas, `search_path` switching) | Strong isolation; a familiar Django multi-tenant pattern | Rejected on operations. Every migration runs N times and can half-fail, so migration state becomes per-tenant; `pg_dump`/restore gets N times more interesting; and every analytics query becomes a `UNION ALL` over a dynamic schema list. We are buying isolation we have no requirement for, at a price paid on every deploy and every restore test. |
| **Database-per-city** | The honest answer *if* a city ever needs separate residency or a separate legal entity | Rejected as premature: there is one city and one campus. It is recorded as the **upgrade path** (§6) rather than the design, and the schema is deliberately shaped so it stays available. |
| **Postgres row-level security on `campus_id`** | Defence in depth; enforcement in the database rather than in a helper | Rejected **for now**, not on principle. RLS needs a per-request database role or a reliably-set session variable, which means connection-pool discipline and a migration for every policy; and it does not help at all against the actual v1 risk, which is a staff member with legitimate access over-reaching (addressed by `personal_data_access_log` and the two-person rule in `THREAT-MODEL.md` §5.8). With exactly one campus, RLS protects against nothing that exists. Kept as the first upgrade step in §6 — and the reason it stays cheap to adopt is precisely that `campus_id` is already `NOT NULL` on every scoped row. |
| **Campus as a label, with discovery filtered in the UI** | Fastest | Rejected: it makes Gate A0 a front-end concern. The gate must be server-side and auditable (§4). |
| **Sharding / Citus / microservice-per-city** | — | Premature by any reading. No. |

---

## 4. The legal gate on discovery — the part that is not optional

`INCORPORATION-AND-BLOCKERS.md` is unambiguous: *"The moment participants can
browse each other's listings, BookHop is operating a platform, and r.4(1)(a)
(be a company), r.4(2) and r.4(4) attach immediately — before the company
exists."* D-009 restates it: code may be written and tested against seed data;
real students seeing each other's listings is gated on the Certificate of
Incorporation, INC-20A, a grievance officer, takedown SOPs and counsel C1–C3.

**This is implemented as data, plus a server-side guard on reads, plus a
database write guard, plus an append-only authorisation row that the audit
chain points at. Not as a comment, not as a feature flag someone can flip, and
not as a front-end condition.**

> **Amendment 2026-10-21, on QA-S0 F3/B1/B2/B4 and REVIEW-S0 M0.** QA threw 33
> tests at this gate. **(b) held against every one of them** — it refused on
> each individual evidence key, every legal-entity fact, a blank human name,
> the wrong gate letter, GLOBAL scope, another campus's row and a revoked row.
> **(a) did not.** Four defects, all mine, all amended below: the column had no
> write guard (§4.1(a)), an inactive campus could still be open (§4.1(a)),
> evidence was checked for presence rather than truth (§4.1(b)), and this
> section's own sentence *"plus an audit row"* overstated what the audit row
> contains (§4.1(d)).

### 4.1 The four parts *(was three)*

**(a) `campuses.discovery_enabled_at` — nullable, NULL means closed — and both
halves are now guarded.**

```python
def assert_discovery_open(campus):
    if not campus.active:                      # amendment, QA-S0 B1
        raise GateClosed(campus)
    if campus.discovery_enabled_at is None:
        raise GateClosed(campus)               # -> HTTP 403, code GATE_CLOSED
```

**`active` is a second, independent gate condition.** QA found that an
`active=false` campus could still have an open gate, because
`assert_discovery_open` never looked at `active` and `visible_campus_ids`
filtered it only for the SYSTEM actor. **Ruling: deactivation closes discovery.**
`active=false` means "we are not operating here", and that is precisely a state
in which students must not be browsing each other's listings.

**But deactivation must NOT clear `discovery_enabled_at`.** Clearing it would
destroy the authorisation record and force a fresh Gate C authorisation to
resume a campus that was paused for a term break. The two facts are
independent: `active` is operational, `discovery_enabled_at` is legal.
Reactivating a campus restores discovery **only if** its authorisation is still
unrevoked — which falls out of the design for free.

**The write guard — ADR-002 §4 said this was a constraint and it was not
(REVIEW-S0 M0, QA-S0 F3).** Measured by QA:

```
Campus.objects.filter(pk=campus.pk).update(discovery_enabled_at=timezone.now())
→ gate open. gate_authorisations rows: 0. audit_log rows: 0.
```

No CoI, no named human, nothing in the chain. **§4.2 conceded that the design
does not stop someone running SQL directly; this is not that.** It is the
application's own ORM, reachable from any future service function, job handler,
management command — **or the Django admin that S2 introduces, which by default
makes every model field editable.** A static grep catches three spellings today
and would miss an admin form, raw SQL or `save(**kwargs)`.

**Ruling: a `BEFORE UPDATE` row trigger on `campuses` refuses any change that
sets `discovery_enabled_at` from NULL to non-NULL unless a live, unrevoked
`gate_authorisations` row with `gate='C'`, `scope_type='CAMPUS'` and
`scope_id = NEW.id` exists.** The precedent, the shape and the engine support
all already exist — migration `0002_append_only_triggers` does exactly this for
`gate_authorisations`. **This is what makes §4's claim true by constraint
rather than true by convention**, and it is the cheapest available fix because
the pattern is already in the repository.

> **Amendment 2026-10-21 on QA-S0 F8 — the trigger checks that an
> authorisation EXISTS, not that it is COMPLETE, and §4.1(b) read stronger
> than the floor it guaranteed.** QA measured it:
> `GateAuthorisation.objects.create(gate='C', scope_type='CAMPUS',
> scope_id=…, evidence={}, authorised_by_human='')` plus an ORM update
> **opens the gate** — empty checklist, unnamed authoriser.
>
> **Ruling: raise the floor rather than lower the wording, because QA is right
> that the cheaper half is writable today.** The evidence checklist is a
> **fixed** list, so a `CHECK` on `gate_authorisations` requiring all six
> evidence keys present and `authorised_by_human` non-blank on any `gate='C'`
> row moves that much of §4.1(b) into the database. One constraint.
>
> **And the honest limit, which is why the wording also gets a clarifying
> sentence rather than being left to imply more:** a `CHECK` **cannot reference
> another table**, so the five typed `legal_entities` facts and the
> `notice_version_ids` FK resolution **cannot** be enforced by it. Those stay
> in `open_discovery`. So §4.1(b) is enforced at **two layers, and the table
> above now says which is which:**
>
> | Layer | Enforces |
> |---|---|
> | **Database** (CHECK + trigger) | The six evidence keys are present; `authorised_by_human` is non-blank; a live unrevoked Gate C row exists for this campus; the campus is `active`. **Cannot be bypassed by any code path, including `psql`** |
> | **`open_discovery` command** | The typed `legal_entities` facts, date sanity, CIN shape, `notice_version_ids` resolving to published notices, the placeholder and agent-name checks |
>
> **Why not push everything into the database:** it would need triggers reading
> three tables to validate a row, re-implementing the command in plpgsql, and
> the plpgsql half would be **unexecuted text until a Postgres box exists** —
> which is the very problem QA's §6 says got worse this rework. **The split is
> the right trade, and the point of writing it down is that §4.1(b) must not
> read as though the database guarantees all of it.**
>
> **THE BOUND OF THE DATABASE FLOOR, ASSERTED RATHER THAN DESCRIBED.** Backend
> added `test_the_database_floor_does_not_check_whether_the_evidence_is_true`,
> which demonstrates that **`campus_mou_ref='TODO'` still opens the gate.**
> That test is preserved deliberately and must not be "fixed":
>
> > **"Every box filled" is not "every box true".**
>
> **And the same bound on the authoriser's name, which is a different claim
> and must not be collapsed into the first** (ENGINE-DIVERGENCE §9.14(b),
> REVIEW-S0 C1): **`authorised_by_human` is checked for PRESENCE, not for
> TRUTH.** It must now contain at least one **visible** character — twelve
> blank forms are refused by the database, and the Unicode-category test above
> it refuses the invisible forms the database's enumerated list does not know.
> **But `'TODO'` is still a name as far as the system is concerned, and so is
> any plausible invention.**
>
> So there are now **two distinct claims about this field, and the packet needs
> both:**
>
> | Claim | True? |
> |---|---|
> | The field is non-blank, and not blank-by-invisible-character | **Yes — enforced at two layers** |
> | The field names a real person who really authorised this | **No. Nothing in the system can know that** |
>
> **The go/no-go packet must carry the second row, not just the first.** A
> reviewer who sees "named human: present, validated" will reasonably read it
> as "a person signed this", and that is precisely the inference §4.1(b) item 5
> says cannot be drawn. The control on truth is, and remains, **a named human's
> signature and the fact that the row is permanent and attributable** — not a
> constraint.
>
> The CHECK proves the checklist was answered. **It proves nothing about the
> answers.** `TODO` passes it because the placeholder deny-list lives in the
> command, not the constraint — and even the command's placeholder check only
> catches a box nobody filled in, never one filled in falsely (§4.1(b) item 5).
> **The go/no-go packet must not read this floor as verification**, and a
> passing test that says so in its own name is a better guarantee of that than
> a sentence in this ADR, because the test is read by whoever changes the
> constraint next.
>
> Residual, named: a forged authorisation row is still possible from
> application code. **But it is an INSERT plus an UPDATE into a table whose
> rows can afterwards be neither deleted nor rewritten — so a forgery is
> permanent, attributable evidence of itself.** That is a materially better
> position than F3's single `UPDATE`, and it is the one QA agrees is small.

Engine note: the plpgsql half is unverifiable on SQLite, so it joins
`ENGINE-DIVERGENCE.md`'s must-confirm-on-Postgres list alongside the P14 and
TRUNCATE triggers. Both engine bodies are written in the same migration, which
migration 0002 already branches for.

**(b) `gate_authorisations` — append-only, evidence required.** Discovery
cannot be opened by a `UPDATE campuses SET discovery_enabled_at = now()`. It is
opened by `manage.py open_discovery --campus <slug>`, which **refuses unless**
a `gate_authorisations` row exists for that campus with `gate='C'` and every
one of these evidence fields non-empty:

| Evidence field | Maps to | Check — amendment on QA-S0 B2 |
|---|---|---|
| `legal_entity.cin` | Gate B1 — Certificate of Incorporation | **Typed.** Read from `legal_entities`, not from `evidence`. CIN **shape** validated (21 chars, the published format). Shape ≠ existence — said plainly below |
| `legal_entity.incorporation_date` | Gate B1 | **Typed.** A real date, **not in the future** |
| `legal_entity.inc20a_filed_at` | Gate B2 — s10A | **Typed.** A real date, not in the future, **and ≥ `incorporation_date`** |
| `legal_entity.grievance_officer_name` + email + phone | Gate B4, IT Rules r.3(2)(a), E-Com r.4(2)/r.4(4) | **Typed.** Email parses; phone is a plausible Indian number; name passes the placeholder check |
| `notice_version_ids` for PRIVACY, TERMS, SELLER_TERMS | Gate B5 | **Fully verifiable, and the strongest item here.** Real FKs that must resolve to `notice_versions` rows of those three kinds with a non-NULL `published_at`. `["none"]` cannot resolve |
| `breach_rehearsal_at` | Gate C3 | **Typed.** A real date, not in the future. *QA's example — `"not yet"` — now fails to parse* |
| `counsel_engagement_ref` | Gate B5 — counsel C1–C3 | **Reference. Placeholder check only** — see below |
| `takedown_sop_ref` + `oncall_rota_ref` | Gate B6, Gate C4 | **Reference. Placeholder check only** |
| `campus_mou_ref` | Gate C1 — signed MoU | **Reference. Placeholder check only** |
| `authorised_by_human` | **A named human.** No agent writes this row | **Placeholder check + an agent-name deny-list.** This field is the whole control and QA defeated it with `"agent"` |

**The ruling, in the terms the question was put: it is both, and which one applies
is now stated per field instead of implied across all of them.** The previous
state — *"reads as typed validation, behaves as a signature prompt"* — is the
actual defect, and the fix is to make both halves explicit rather than to pick
one.

**1. Everything the schema already types is read from the typed column, not
from the `evidence` blob.** `legal_entities.cin`, `incorporation_date`,
`inc20a_filed_at` and the grievance-officer fields are **already columns**
(`DATA-MODEL.md` §1). Half of QA's attack worked because the command read
free text where a typed fact was sitting one table away. `evidence` jsonb now
holds **only** the four genuinely-external references. **Less code, strictly
stronger** — the same move as ADR-003 §2.3's whitelist.

**2. `notice_version_ids` become real foreign keys.** This is the one evidence
item that is verifiable end to end inside the database, and it should carry the
weight the others cannot.

**3. The four remaining references get a placeholder check, which is honest
about what it is.** Rejected, case-insensitively, trimmed:
`TODO`, `TBD`, `TBC`, `none`, `n/a`, `na`, `-`, `--`, `.`, `?`, `x`, `xxx`,
`pending`, `not yet`, `notyet`, `placeholder`, `test`, `temp`, `later`,
`unknown`, `asap`, and anything shorter than 4 characters.
**This catches a field nobody filled in. It does not and cannot catch a field
filled in falsely.**

**4. `authorised_by_human` additionally rejects every name an agent would
type**: `agent`, `system`, `admin`, `bot`, `claude`, `ai`, `assistant`,
`automation`, `script`, `cto`, and **every charter name in `.claude/agents/`**
(`ceo-planning`, `product-manager`, `design-director`, `cto`, `market-finance`,
`marketplace-ops`, `privacy-compliance`, `red-team`, `backend-developer`,
`frontend-developer`, `code-review`, `test-qa`, `platform-sre`). The field
exists to carry *"no agent writes this row"*, and QA proved that an agent
typing `"agent"` satisfied it. Plus: at least two characters, containing a
non-digit.

**5. And the acknowledgement, written down because items 3 and 4 are a
tripwire and not a proof.**

> **Beyond the typed fields, the control on this gate is a named human's
> signature. The reference fields are a prompt that makes the Gate B/C
> checklist visible and refuses to be left blank; they are not evidence that
> the underlying document exists.** A CIN of the right shape is not a company;
> a `campus_mou_ref` that is not a placeholder is not a signed MoU. **Anyone
> reading a `gate_authorisations` row — and specifically anyone assembling the
> G4 go/no-go packet — must treat it as a record that a named person asserted
> these things on a date, not as verification that they were true.**
> `README.md` §7's packet must carry that sentence next to this row, so the
> packet is never read as stronger evidence than it is. **Routed to
> ceo-planning**, since §7 is not my file.

**Why not go further and require, say, an uploaded certificate?** Because it
would be theatre at this scale: nothing in the system can validate a PDF of a
CoI either, and we would have added a document store, a retention rule and a
DPA for an unchanged guarantee. **The honest control is a human who signs, a
checklist that cannot be blank, and a packet that says which is which.**

Closing discovery again is one command and writes a `revoked_at`.

**RATIFIED · complete-or-absent — cto, 2026-10-21 (REVIEW-S0 C2)**

> **A Gate C authorisation row is written complete or not at all. There is no
> such thing as a saved draft.** Migration 0005 refuses the INSERT of an
> incomplete `gate='C'` row, so the only reachable incomplete state is **no row
> at all**.
>
> **This ratifies a change the code already made and this ADR still described
> the opposite of.** v1.0 said *"the command prints the checklist with each
> item's state and exits non-zero on the first missing one"* — which, with 0005
> in place, **can never happen for a saved row**. That sentence is removed. The
> reviewer is right that leaving it was the same defect class as
> `ENGINE-DIVERGENCE` §7.1 asserting the opposite of the truth — **a contract
> describing an operator workflow the code has removed — and it sat in the
> document the go/no-go packet rests on.** It is the third time I have had to
> correct a document that claimed more, or other, than the code does.
>
> **Consequences, stated so the operator experience is not discovered:**
> - **The per-item checklist is a pre-flight affordance, not a report on a
>   stored draft.** `checklist(campus, auth=…)` is called on an **unsaved**
>   candidate row and still tells an operator exactly which item to go and
>   fetch. That is the useful half and it survives intact.
> - **An operator assembling evidence over days holds it outside the
>   database** — in the CS's email, a folder, a note — until every item is in
>   hand, and then writes one complete row. **This is a real workflow cost and
>   it is the right trade:** a half-filled authorisation sitting in the table
>   for a week is exactly the artefact someone later mistakes for an
>   authorisation.
> - Complete-or-absent is a **cleaner invariant than drafts-allowed** and the
>   control is strictly stronger, so this is not a reason to revert.
>
> **It does not change what the floor proves.** See the bound below: every box
> filled is still not every box true.

**(d) Where accountability actually lives — amendment on QA-S0 B4, because §4's
own wording overstated it.**

QA is right: `audit_log` stores **hashes** of before/after, not values
(`DATA-MODEL.md` §8), which is correct for privacy and means **the audit row
for `discovery.open` does not record who authorised it.** That fact lives only
in `gate_authorisations.authorised_by_human`. §4's opening sentence cited "an
audit row" as the artefact; **on its own it is not, and that sentence is now
corrected.**

**Ruling — accept the split, and state the two guarantees separately, because
they are genuinely different:**

| Artefact | Guarantee | Mechanism |
|---|---|---|
| **`gate_authorisations` row** | **Immutability of the content** — the named human, the evidence, the date cannot be altered or deleted afterwards | Append-only row trigger, verified by QA: UPDATE refused except `revoked_at`/`revoked_reason`, DELETE refused, TRUNCATE refused |
| **`audit_log` chain entry** | **Tamper-evidence over the fact and the time** — that an authorisation happened then, and that no later edit or back-dating went unnoticed | Hash chain + `prev_hash UNIQUE`, chain head published daily (`INFRA.md` §5) |

**Neither substitutes for the other, and the row is adequate as the system of
record precisely because it is append-only.** One addition so the two are
linked rather than merely coexisting: **the `discovery.open` audit entry carries
`object_type='gate_authorisations'` and `object_id` = that row's id.** The chain
then proves *which* authorisation was acted on and when, while the row holds the
name — so following the chain reaches the named human in one hop, without the
chain ever storing a person's name. That is the right division: the chain is
tamper-evident and privacy-preserving; the row is immutable and identifying.

**The `gate_authorisations` row, not the audit row, is the artefact for the
go/no-go packet** (`README.md` §7) — read with the acknowledgement in (b).

**(c) Seed data is structurally separated from real data.** `users.is_seed` and
`listings.is_seed`, both `NOT NULL DEFAULT false`. Before a campus's gate is
open, the discovery query is additionally restricted to `is_seed = true`:

```sql
WHERE campus_id = :campus
  AND status = 'LIVE'
  AND (:discovery_open OR is_seed)      -- closed campus: seed listings only
```

**This is the design that makes D-009 workable.** Developers and QA exercise
search, ranking, offers, the full transfer state machine and every metric
query against seed listings, with full coverage, while **no real student's
listing is reachable by any other real student**. A real user who somehow
reaches the discovery endpoint on a closed campus gets a 403 `GATE_CLOSED`
page explaining that listings open when the service launches; a staff account
sees seed data only.

A constraint prevents the two from mixing: `transfers` has
`CHECK (seller_is_seed = buyer_is_seed)` — a seed account and a real account
can never form a transfer, so seed traffic never contaminates
`METRICS.md` numbers. All metric views filter `is_seed = false`, and the
weekly export prints the seed-row count it excluded, so a silent
contamination is visible rather than invisible.

### 4.2 What this buys and what it does not

- It buys: a bright line that is **a row in a table with a named human on
  it**, testable in CI (`tests/unit/test_gate.py`: a non-seed listing is never
  returned for a campus with `discovery_enabled_at IS NULL`), and reversible.
- **Corrected 2026-10-21: it now DOES buy protection against direct SQL on
  this column.** v1.0 of this section said *"it does not buy protection against
  a staff member running SQL directly; nothing short of RLS would"*. **That is
  no longer true of `discovery_enabled_at`**, because §4.1(a)'s trigger is a
  database-level guard: a `psql` session gets the same refusal as the ORM, and
  it fires on anything that is not an authorised open. The concession was
  accurate when the gate was application code; it survived into a version where
  the gate is a constraint, and leaving it would have understated the control
  to anyone reading this for the go/no-go packet.
- **What it still does not buy:** protection against someone with database
  privileges who **drops the trigger first** — and against that, nothing short
  of RLS plus privilege separation would help, which is a people control
  (`THREAT-MODEL.md` §5.8, risk A8) and not a schema one. The difference
  matters: the gate can no longer be opened *by accident or by ordinary code*,
  only by a deliberate act that removes a guard, and a dropped trigger is
  itself visible in the audit chain and in the schema guard tests.
- **Uncertainty note carried forward:** `INCORPORATION-AND-BLOCKERS.md` rates
  its own A0 reading as MODERATE uncertainty and says "it is not a position I
  would hold at 300 handovers". This design makes the position *auditable*; it
  does not make it *correct*. That remains privacy-compliance's call.

---

## 5. Cross-campus and cross-city visibility, without shipping a feature

`listings.visibility_scope` enum `{CAMPUS, CITY, NATIONAL}`, `NOT NULL DEFAULT
'CAMPUS'`. The discovery predicate is written once, for all three, now:

```sql
WHERE (
      (l.visibility_scope = 'CAMPUS'   AND l.campus_id = :actor_campus)
   OR (l.visibility_scope = 'CITY'     AND l.city_id   = :actor_city)
   OR (l.visibility_scope = 'NATIONAL')
  )
```

In v1 every row is `CAMPUS` and the UI offers no control, so the second and
third branches are dead in production — **but they are exercised by seed data
in tests**, so they are known to work. Widening to city-wide discovery is
`UPDATE listings SET visibility_scope='CITY' WHERE …` plus a UI control. No
migration, no query rewrite, no backfill of a missing column.

This is the whole of "multi-campus and multi-city from day one": the keys, one
predicate, and a default that keeps v1 to one campus.

---

## 6. Upgrade path, in order, with the trigger for each step

| Step | Trigger | Work |
|---|---|---|
| 1. Multi-campus discovery | A second campus signs an MoU and its gate opens | Flip `visibility_scope` for the listings that should be shared; add the campus filter control to the UI. **No schema change.** |
| 2. Postgres RLS on `campus_id` | A campus requires contractual data isolation, or staff headcount grows past the point where `personal_data_access_log` review is credible | Add policies per scoped table and a per-request role. Cheap **because `campus_id` is already `NOT NULL` and indexed on every scoped row** — that is the point of doing it now. |
| 3. Database-per-city | A city requires separate residency, a separate legal entity, or a regulator asks for separation | `city_id` is already on every scoped row, so the extraction predicate is `WHERE city_id = N`. `books` and the notice/consent tables replicate; the rest moves. Painful but **pre-planned**, not archaeological. |
| 4. Read replica / partitioning of `search_events`, `transfer_events`, `audit_log` | These three are the only tables with unbounded row growth | Declarative monthly range partitioning on `occurred_at`, which also makes the retention purge a `DROP PARTITION` instead of a `DELETE`. Noted now because the retention job's cost is the first thing that will hurt. |

---

## 7. Deliberately not built in v1

| Not building | Add when |
|---|---|
| Campus switcher / "browse other campuses" UI | Step 1 above |
| Row-level security | Step 2 above |
| Per-city databases, sharding, replicas | Step 3/4 above |
| Campus-level branding or theming | Never, unless an MoU requires it |
| Per-campus feature flags beyond the discovery gate | `feature_flags` already has `scope_type`/`scope_id` for it; no UI until a second campus exists |
| Geographic/proximity search within a campus | No purpose stated, and precise location is explicitly not collected (`COMPLIANCE.md` §7 row 20). Handover points are a fixed, curated list. |

## 7a. Amendment log

| Date | Change | Source |
|---|---|---|
| 2026-10-21 | v1.0 | — |
| 2026-10-21 | **§2.3 — the gated read becomes the DEFAULT manager** (`objects` gated, `all_objects` explicit, `base_manager_name` set), correcting §2's convention-dressed-as-constraint | REVIEW-S0 proposal, accepted |
| 2026-10-21 | **§4.1(a) — write guard on `discovery_enabled_at`** (trigger requiring a live unrevoked Gate C authorisation); **`active=false` closes discovery** and does not clear the authorisation | QA-S0 F3/B1, REVIEW-S0 M0 |
| 2026-10-21 | **§4.1(b) — evidence typing.** Typed facts read from `legal_entities`; `notice_version_ids` become real FKs; four external references get a placeholder check; `authorised_by_human` gets an agent-name deny-list; **and the explicit acknowledgement that beyond the typed fields the control is a human signature** | QA-S0 B2 |
| 2026-10-21 | **§4.1(b) — complete-or-absent RATIFIED.** A Gate C authorisation is written complete or not at all; the per-item checklist is a pre-flight affordance on an unsaved row, not a report on a stored draft; an operator assembling evidence holds it outside the database until complete. **The v1.0 sentence describing the removed workflow is deleted** — a contract describing an operator workflow the code no longer has is the same defect class as asserting a property the code lacks | REVIEW-S0 **C2** (must-resolve before S1) |
| 2026-10-21 | **§2.3 — the manager sits UNDERNEATH `assert_discovery_open`, never instead of it.** A filtered manager returns no rows; the contract requires `403 GATE_CLOSED`, and S3's three truths depend on the distinction. Substituting one for the other makes the legal gate invisible to the person it applies to | REVIEW-S0 §11 closing point |
| 2026-10-21 | **§2.3 — the reverse-relation gap is closed by a TEST, not by my argument.** v1.0 asserted flatly that reverse relations are uncovered; which paths resolve a filtered manager differs by path and Django version, so S2 measures it and records the result either way | REVIEW-S0 §11 condition (c) |
| 2026-10-21 | **§4.2's concession corrected.** "No protection against direct SQL" is **no longer true of `discovery_enabled_at`** — §4.1(a)'s trigger is a database-level guard that refuses a `psql` session too. What remains unprotected is someone who drops the trigger first | REVIEW-S0 |
| 2026-10-22 | **§2.3 — `User` does NOT get the gated default manager, and the premise that said it should was FALSE.** Measured: 26 broken tests, all identity lookups; S1 *does* ship ungated reads of `users` (session, magic link). **Criterion recorded so S4 does not re-ask: the gated manager belongs on models that are DISCOVERED, not on models RESOLVED by identity or ownership** — so `transfers` should not get one either | S2 backend escalation 1 |
| 2026-10-22 | **§2 — denormalised tenant and seed columns on child tables are held by a COMPOSITE FOREIGN KEY, replacing the nightly consistency check.** Inconsistency becomes unwritable rather than detectable-a-day-late; the same move upgrades the `city_id` rule. **The test must write an inconsistent child directly, bypassing the service** — a service-routed test proves only the service | S2 backend escalation, "fixture cannot produce its own failure mode" |
| 2026-10-22 | **§2.3 — reverse accessors ARE gated on Django 5.2; my prediction was wrong.** Measured and **pinned as a cross-library claim**, so an upgrade turns it red rather than silently losing coverage | S2 backend measurement |
| 2026-10-21 | **§2.3 slice confirmed: S2.** The Manager class, `base_manager_name`, the `all_objects` allow-list and the test land with `listings`; `users.is_seed` (S1) is retrofitted in the same commit, because nothing in S1 reads users through a gate | ENGINE-DIVERGENCE §9.6, slice question |
| 2026-10-21 | **§4.1(d) added — accountability split.** The `gate_authorisations` row is the system of record (immutability); the audit chain is tamper-evidence over the fact and time and now carries `object_type`/`object_id` pointing at it. §4's "plus an audit row" corrected | QA-S0 B4 |

## 8. Reversal triggers

- **If a second campus requires contractual data isolation before step 2 is
  cheap**, revisit: RLS may need to come before multi-campus discovery rather
  than after.
- **If `city_id` consistency drifts** (the nightly check fires twice), drop the
  denormalisation and join through `campuses`.
- **If privacy-compliance rejects the §4 gate design** as insufficient for
  A0/r.3(1)(b), the fallback is harder and must be said out loud: no discovery
  endpoint exists in the deployed build at all until Gate C, with the code
  present but its URL unrouted. That is worse — it is untestable in the
  deployed environment — which is why the gate-as-data design is preferred.
