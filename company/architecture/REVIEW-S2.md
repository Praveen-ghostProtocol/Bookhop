# REVIEW-S2.md — Code Review of slice S2

**Reviewer:** code-review agent · **Date:** 2026-10-22
**Commits reviewed:** backend `49b7dc2`, frontend `59ad6cf`. **Both are
committed**, so this approval attaches to two commits and not to a working
tree — which matters more than usual this round, because the working tree is
*not* the commits (see E3).
**Scope:** catalogue, listings, photos, book requests, the 8-state machine,
the price-immutability trigger, the correction endpoint, the moderation queue,
the gated default manager; the sell flow, listing page, want form, EN + TA
strings.
**Authored by:** backend-developer and frontend-developer. **I wrote no line
of either diff** (charter hard rule 1).

---

## VERDICT

# CHANGES REQUIRED

**Four blocking findings.** Two of them — B1 and B2 — are things that only a
real engine and a real request could show, which is the same lesson the slice
note draws about its own four seam defects, arriving one layer deeper than the
note reached. B3 is the one money column in the database taking a 500 at the
only layer ADR-003 §2.1 says detects a bad money input. B4 is the risk backend
itself nominated, and it is real: **measured, not argued.**

This is good work. The price-immutability trigger is the best-specified
control in the project, the misspelling test is a model for rule 10's
both-sides corollary, and declining Pillow is a correct security decision that
backend undersells. The copy-guard narrowing is a genuine measurement
answering the CTO's condition, and reverting the two "amount"-substituted
strings rather than greening a grep is rule 13 obeyed under exactly the
pressure it was written for.

**But three of the four blockers share one shape, and it is the shape this
project keeps finding: a control whose test cannot produce the condition the
control exists to prevent.** The four-photo cap, the denormalised child
columns and the money-input refusal each ship with tests that pass, and each
fails when something the fixture cannot construct actually happens.

**And I cannot give you a stable number for this slice.** I measured
**PostgreSQL 16: 15 failed / 1408 passed / 55 skipped / 2 xfailed** and
**SQLite: 13 failed / 1321 passed / 127 skipped / 1 xfailed**. Neither matches
the 8/7 in the brief, a parallel reviewer measured 7/1388 an hour earlier, and
`pytest tests/contract` currently dies at **collection** with
`KeyError: 'correction'`. See E3 — this is TASKS §0 rule 3a's exact failure
mode, two days after rule 3a was adopted to stop it.

**What I checked last and most carefully:** the negative control on the price
trigger, because a trigger that refused every UPDATE would pass the two
obvious tests and break every transition in DATA-MODEL §6.1. It is correct,
twice over — a raw non-price `.update()` and an ORM `save()` that rewrites the
unchanged price both succeed, on both engines.

**QA has not verified this slice.** This approval, when it comes, will cover
what I read and ran. It implies no behavioural coverage that QA has not
independently signed.

---

## BLOCKING — must change before merge

### B1 · A 404 condition answers 500, and the state that causes it is the one claim 5 describes

`C:\CodingSpace\BookHop\apps\listings\api.py:332`

```python
    except ServiceError as exc:
        return error_response(exc)
    return services.photo_response(photo)        # <- outside the try
```

`photo_response` raises `NotFound` at
`C:\CodingSpace\BookHop\apps\listings\services.py:873` when `read_object`
returns `None` — the row is present and the file is absent. That raise is
outside the `except ServiceError`, so it escapes the view as a 500 with a
stack trace. Reproduced on **both engines**.

The state that produces it is a database restored without the media
directory — so B1 is what R11 looks like at runtime. THREAT-MODEL forbids
echoing an exception message in a response; the catch-all does suppress the
text, but the contract's answer here is 404, not 500.

`test_a_purged_photo_is_404_rather_than_a_crash` covers the adjacent case
(`storage_key IS NULL`) and passes, which is why this reads as covered.

**Fix:** move line 332 inside the `try`. One line.

### B2 · The four-photo cap is lost on PostgreSQL and holds on SQLite — measured

`C:\CodingSpace\BookHop\apps\listings\services.py:450`

```
PROBE, two concurrent uploads at 3 photos:
  PostgreSQL 16 -> photos stored = 5   (cap is 4); refusals = []
  SQLite        -> photos stored = 4   (cap is 4); refusals = ['database table is locked']
```

`ListingPhoto.all_objects.filter(listing=listing).count()` then insert, inside
`transaction.atomic()`, with no row lock and no database constraint. Under
READ COMMITTED both writers read 3 and both insert. **SQLite holds only
because it serialises writers — an accident of the engine, not a design.**

So the cap holds on the engine the suite runs on by default and fails on the
engine production uses. That is the worst possible distribution of a defect.

`C:\CodingSpace\BookHop\apps\listings\models.py:~283` declines the counting
trigger because *"the append path is already single-writer per listing."*
**That explanation is now measured false**, and `CLAUDE.md` rule 9's corollary
applies: when an explanation and a measurement disagree, delete the
explanation. It also cites "rule 17", which no longer exists.

I do not accept the "needs the seller to race themselves" framing. A
double-tap on a 3G form, or a retried upload the client believes timed out, is
one person producing two in-flight requests. No malice required.

**Fix, ladder rung 4 rather than a trigger per engine:** add `position`
(0–3) with `UNIQUE(listing_id, position)` and
`CHECK (position BETWEEN 0 AND 3)`. `position` is an **exact match** in
`NON_MONETARY_WORDS` (`apps/core/p14.py:55`) so it passes W1 with no ADR
amendment, and `search_result_opens.position` is the precedent. The race then
surfaces as `IntegrityError`, for which `add_photo` already has handler shape.

No test exists for this and none could: `test_a_fifth_photo_is_refused_with_the_count`
is sequential. **Rule 10, "a guard whose fixture cannot produce the condition."**

### B3 · The one money column takes a 500 on a non-ASCII digit, at both layers

`C:\CodingSpace\BookHop\web\forms.py:538` and
`C:\CodingSpace\BookHop\apps\listings\services.py:176`

```python
if not cleaned.isdigit():          # True for '²' and '①'
    raise forms.ValidationError(...)
rupees = int(cleaned)              # ValueError
```

Measured:

```
ListingForm(asking_price_rupees='²')  -> UNCAUGHT ValueError
_coerce_minor_units('²')              -> ValueError, not ValidationFailed
```

`POST /sell` with `asking_price_rupees=²` is a 500. `POST /api/v1/listings`
with `asking_price_paise:"²"` is a 500 instead of `400 VALIDATION_FAILED`.

This is the one money column ADR-003 §2.1 permits, and §2.1 names the service
layer as **the only** layer that detects a bad money input. So `CLAUDE.md`
rule 12's question — *name the other layer that still catches it* — has no
answer: **both layers carry the identical bug.** `'300.75'` and `'-1'` are
correctly refused; the corpus never tried a non-ASCII digit.

**Fix, both sites:** `if not (cleaned.isascii() and cleaned.isdigit()):`.
One word. It forces one decision to take deliberately rather than by accident:
`'௨௮௦'.isdigit()` is `True` and `int('௨௮௦')` is `280`, so **Tamil numerals are
silently accepted today**, and `isascii()` starts refusing them. Nothing
documents or tests that acceptance. Given the pilot is Chennai, decide it on
purpose — and if Tamil numerals stay, they need a row and a test.

### B4 · The denormalised child columns — the manager silently returns the wrong rows

`C:\CodingSpace\BookHop\apps\listings\models.py:287-303, 373-397` ·
`C:\CodingSpace\BookHop\apps\core\scoping.py:131-135`

Backend nominated this and was right to. Measured on the frozen tree:

```
LISTING campus=1 is_seed=True
A  consistent photo, visible via .objects : True
B  after flipping ONLY the child's is_seed:
     child  visible via .objects          : False
     parent visible via .objects          : True
     reverse accessor listing.photos.all(): []
     database refused the write?          : no -- the UPDATE succeeded
```

`ListingPhoto` and `BookRequest` each carry their own `campus_id`, `city_id`
and `is_seed`, denormalised from the parent at insert and **re-derived by
nothing**. `GatedManager.get_queryset()` filters on the child's own copy. The
two can disagree and the database does not object, so the listing stays
visible while its photos vanish — silently, with no error anywhere, including
through the reverse accessor. The inverse is worse: a child with `is_seed=True`
under a real student's listing on a closed campus is visible through the
manager while its parent is not.

Every test sets both through `add_photo`, which sets them correctly. **The
fixture cannot produce the failure mode** — rule 10 again, and the third
instance in this one slice.

The serve path does not use the manager today (`get_photo_for_download` uses
`scoped(... all_objects ...)` with a hand-rolled gate branch), so this is not
a live disclosure in S2. It becomes one in S3, when discovery reads through
the manager.

**This is already specified and already red.** `tests/contract/test_denormalised_scope_columns.py`
carries seven failing tests naming the fix: a unique index
`listings_tenant_identity (id, campus_id, city_id, is_seed)` on the parent and
a composite FK `(listing_id, campus_id, city_id, is_seed)` on each child, so
the inconsistent state is **unrepresentable** rather than merely untested.
That is the right answer — declarative, one definition, both engines, no
trigger — and it is the smallest correct fix. Ship it.

> **On fairness of the date.** ADR-002 §2's amendment specifying this is
> *uncommitted*, so it postdates `49b7dc2` and backend cannot be held to it.
> **I am blocking on the measurement, not on the contract date.**

---

## REQUIRED — must change, may be a follow-up commit in this slice

**R1 · The a11y harness drops 17 of 35 routes silently, and the slice reports
a11y green.** `C:\CodingSpace\BookHop\tests\a11y\test_pages.py:86` skips any
route containing `<`, so `/listing/<int:listing_id>` and
`/sell/<int:listing_id>/photos` — `listing.html` (224 lines) and
`sell_photos.html` (129) — **have never been swept**. `/sell/find-book` *is*
swept but fetched with no query string, so the entire intake form (condition
radios, annotation group, damage checkboxes, price, terms checkbox) is never
rendered to the harness. Net: **none of S2's new interactive surface is
covered.** `test_the_sweep_reports_what_it_did_not_check` reconciles against
the *already-filtered* list, so the invariant is true over the subset and
cannot notice the gap. This is rule 10 bullet 4 verbatim — the instrument does
not assert its own reach — and S2 is the first slice where it costs something.
QA's tree; routed to QA, but it invalidates the slice's a11y claim and so it
is Required, not a note.

**R2 · `sell.condition.hint` fails COPY-DECK §1.2.** Rendered at
`C:\CodingSpace\BookHop\templates\sell_find.html:66`:

> "Torn pages, writing, a bent cover, a missing CD — say it plainly. **Buyers
> believe a description that admits things.**"

The first clause is an instruction and passes. The second fails row 1 (it
predicts how buyers will react, with nothing behind it) and row 6 (the subject
is a person who is not us, and the predicate is a disposition — the "Priya is
a careful seller" shape, not the "Priya wrote this 3 days ago" shape). No grep
catches it; the string was edited in S2 to drop "trust", so it was looked at
and the predictive clause survived. **Fix:** delete the second sentence, or
replace it with the mechanism — *"The description is all a buyer has before
they see the book."*

**R3 · The idempotency fingerprint excludes `request.FILES`, so a different
photo under a reused key is answered with the first photo's document.**
`C:\CodingSpace\BookHop\apps\core\api.py:166-176`. `_parse_body` returns
`request.POST.items()` for multipart — the file is not in the fingerprint.
Measured:

```
first                                : 201 {"id": 1, "sha256": "e8e20d49...", "width": 4, "height": 3}
second (SAME key, DIFFERENT file)    : 201 Idempotency-Replayed: true, byte-identical document
photos actually stored               : 1  [(4, 3)]
```

The second photo is silently discarded and the client is told 201. The control
that exists to turn this into `409 IDEMPOTENCY_KEY_REUSED` — *"same key,
different body → 409"*, `apps/core/services.py:328` — is defeated on the only
multipart endpoint in the product. The HTML journey does not hit it
(`web/views.py:1252` calls `add_photo` directly), so this is API-only today
and S4's transition endpoints are where it bites. **Fix:** fold a digest of
`request.FILES` into the body dict in `_parse_body`.

**R4 · `MEDIA_ROOT` is not isolated in tests, and backend's own test is red
because of it.** `tests/unit/test_listing_photos.py::test_the_original_is_never_written_anywhere`
`rglob`s the real `media/` directory, which every test writes into and nothing
cleans. It **passes in isolation and fails in the full suite** — I confirmed
both — because `tests/contract/test_denormalised_scope_columns.py` leaves an
EXIF-bearing file under `media/qa/denorm/`. So the brief's claim that *every*
failure is in QA's tree is **not true as measured**: this one is in backend's
tree, and its root cause is in `tests/conftest.py`, which is also backend's.
A suite that writes into a shared, persistent, production-shaped directory is
history-dependent, and a test asserting "no EXIF anywhere on disk" over it is
asserting something about the machine. **Fix:** one autouse fixture setting
`settings.MEDIA_ROOT = tmp_path`.

**R5 · The timestamp seam is fixed at the seam and tested at the symptom.**
`jsonable` (`apps/core/api.py:126`) is the right fix in the right place, and
it has **no direct test** — the only coverage is two endpoints that happen to
return a timestamp. A third endpoint in S4 returning a `Decimal` or a `UUID`
is covered by `default=str` in fact and by nothing in test. Of the four seam
defects, this is the one whose regression pins the symptom rather than the
seam. The other three are pinned correctly, each with its other side as a row
(JSON-after-multipart; 422-when-the-version-is-current; terms-recorded-only-
when-ticked). **Fix:** one test over `jsonable()` with a datetime, a Decimal
and a UUID.

**R6 · The service-worker fix misses the two rendered shell entries.**
`C:\CodingSpace\BookHop\web\views.py:1605-1655`. The fix is sound for static
files — `css/app.css` is hashed, `activate` deletes every non-matching cache,
`/sw.js` is served `no-cache`. But `/offline` and `/manifest.webmanifest` are
hashed from **template source**, not rendered output, and `offline.html`
carries five `{% translate %}` tags. A copy change alters what those routes
serve while the template bytes are unchanged, `VERSION` does not move, and an
installed PWA keeps the old offline copy indefinitely — **the identical
failure mode this fix was written for, surviving in the two entries that are
rendered.** The sw.js comment's claim that "changing any of them changes this
name" is false for those two. **Fix:** add the catalogue as a hashed input.

**R7 · Three `role="alert"` regions share one `id` on the intake page.**
`templates/sell_find.html:40, 50, 56` each include `_errorslot.html`, which
hard-codes `id="form-errors"`. Duplicate `id` is invalid HTML; three assertive
live regions announce in DOM order, so a student with errors hears three error
counts; and the summary links `<a href="#id_{{ name }}">` resolve against
whichever duplicate the browser picks. **Fix:** pass the id in.

**R8 · The seller-terms checkbox is the one required control with no required
marker.** `templates/sell_find.html:154-157`. Every other field routes through
`_field.html` / `_group.html`, which emit `({% translate "required" %})` per
SYSTEM §4.4. The hand-rolled `.check` div emits none — and this is the single
tick r.6(4)(a) exists for. The accessible-name fix itself is **correct**; the
required-ness is what was lost with it. One span.

**R9 · `_strip_webp` has zero tests, and one defect by reading.**
`C:\CodingSpace\BookHop\apps\listings\images.py:184-215`. 32 lines of byte
arithmetic over attacker-supplied data, three dimension-parsing branches, on a
format `CONTENT_TYPES` accepts — and `grep -rn "webp\|VP8" tests/` returns
nothing, while JPEG and PNG each have several. Line 209 drops `EXIF`/`XMP `/
`ICCP` chunks but copies `VP8X` through verbatim, including the feature-flag
bits that *declare* those chunks present. **Fix:** clear bits 2/3/5 of
`payload[0]` when rewriting VP8X, plus one round-trip test per branch.

**R10 · The 8 MB cap is applied after the whole upload is in memory.**
`C:\CodingSpace\BookHop\apps\listings\services.py:433` — `data = upload.read()`
then `if len(data) > MAX_PHOTO_BYTES`. No `DATA_UPLOAD_MAX_MEMORY_SIZE` or
`FILE_UPLOAD_MAX_MEMORY_SIZE` in settings, no `client_max_body_size` in
`INFRA.md`. An authenticated student POSTing 2 GB has it spooled to disk and
then pulled entirely into RAM before the refusal; the 40/day rate limit does
not help because one request suffices. The test docstring says "refused before
it is **parsed**" — true, and narrower than "before it is read". **Fix:**
`upload.read(MAX_PHOTO_BYTES + 1)`. One line, trusts no client-supplied size.

**R11 · `INFRA.md` §3.3's restore test prints RESTORE OK having proved nothing
about photos — and backend's claim 5 is wrong in their own favour.** Backend
says the media directory is in no backup scope. **It is:** `INFRA.md:117`
already has `tar -cz /var/lib/bookhop/media`. The real defect is one layer in —
§3.3's seven steps fetch and decrypt **the dump only**, and step 6 goes as far
as asserting `listings_price_immutable` is installed without checking a single
photo byte. So the scripted restore whose result `METRICS.md` records as the
charter's restore test would print RESTORE OK on a restore that lost every
photo. Rule 10: an instrument that does not assert its own reach. Not blocking
on S2 *code* — `deploy/restore_check.*` does not exist and platform-sre is
dormant until S8 — but it is cto's document, it costs two lines now, and **B1
is what that state looks like at runtime.**

**R12 · COPY-DECK carries two live rows for `sell.published`, and the stale
one has a Tamil draft attached.** `company/design/COPY-DECK.md:561` and `:651`.
Line 651 is the v1.7 amendment (`Saved.`, NOT DRAFTED). Line 561 was never
struck and still reads *"It's on the list. We'll tell you when someone
offers."* — **with a completed Tamil translation beside it.** A Tamil reviewer
working from §6.1 would sign off the exact string v1.7 withdrew for being
false in both halves. The code is correct; the deck is not. Rule 11.
*Separately:* `COPY-DECK.md` is **design-director's** file per TASKS §1, and
frontend added 211 lines to it. Raise with cto.

**R13 · Neither side of the gate split on the photo route is a row.**
`C:\CodingSpace\BookHop\apps\listings\services.py:823-835`. The test that
looks like it covers this — `test_another_students_photo_is_404_and_never_403` —
uses a student on the **same** campus against a `DRAFT` listing, so it returns
404 on the *status* branch at line 824 and never reaches the gate at 827. I
probed both sides and both are correct (closed + `is_seed=False` → 404 with
`gate.refused` logged; closed + `is_seed=True` → served), so this is a
coverage gap rather than a defect. **Rule 10's corollary: where a rule splits
a set, both sides are rows.** Two rows, using `closed_campus`.

---

## ESCALATIONS — founder/cto routes, not review comments

**E1 · `locale/FORBIDDEN_EXCEPTIONS.toml` (+112).** Adds `[shapes.bare_label]`
narrowing `BANNED_LABELS` to label-shaped text with an `asking` qualifier.
`[strings]` stays empty and **no reviewer name is written anywhere** — correct,
and the right instinct. Two things for cto: `ratified_by = "PENDING —
cto/code-review"` on all three shape blocks, with a test asserting that PENDING
state, so ratifying means editing that test in the same change; and
`implemented_in` still says *"NOT IMPLEMENTED. The guard is RED on six strings
until it is"*, **which is now false** — `49b7dc2` implemented it and the test
is green. A manifest that misstates the live state of the control it governs
is the thing rule 9 is about.

**E2 · `locale/ta/BLOCKING_CLASSES.toml` (+12).** Three counters only
(86 blocking-class strings, 60 without a draft, 254 total). No prefix narrowed,
no `[exceptions]`, no reviewer name. Benign, but escalation-class by the rule.
`locale/ta/REVIEWED.toml` is **untouched and empty**; no agent wrote a name
into it; `i18n.ta_enabled` cannot be turned on. Correct conduct, reported
because the charter says a diff to these files is reported.

**E3 · The tree is not frozen, and this is the finding with the longest tail.**
At the time of review, `git status` shows **twelve modified files** against
HEAD — nine documents (`ADR-001`, `ADR-002` +130, `ADR-003` +177,
`API-CONTRACT`, `DATA-MODEL`, `TASKS`, `THREAT-MODEL`, `DECISIONS` +445,
`red-team.md`) and **three in `tests/contract/**`** (+431 lines). Consequences
I measured rather than inferred:

- `pytest tests/contract` **fails at collection** with `KeyError: 'correction'`.
  That is a mid-edit error in another agent's tree presenting as this slice's
  result — F21's exact shape, and the exact thing rule 3a was adopted for on
  **2026-10-22**, the same day.
- Three reviewers have now measured three different failure counts for one
  slice (8/1385, 7/1388, 15/1408). **The number everyone is quoting is not
  reproducible against any commit.**
- `ADR-002`'s amendment specifying B4's fix exists only in the working tree, so
  the contract the implementation is being judged against is itself unversioned.

Every file I reviewed under `apps/`, `tests/unit/`, `tests/api/`, `bookhop/`,
`web/`, `templates/`, `static/` and `locale/` is clean at its commit, so **the
approval target is intact.** The measurement around it is not. Rule 3a needs an
enforcement mechanism, not another paragraph: a review that cannot reproduce
its own numbers is a review nobody can act on.

---

## The seven questions, answered

**1 · The price-immutability trigger. PASS, and it is the best control in the
project.** Both limbs are real. The behavioural limb asserts the message text
(`P14`, `asking_price_paise`, `fixed at intake`) and not the exit status, and
SQLSTATE `P0001` is separately asserted in
`tests/unit/test_plpgsql_refusal_sqlstate.py` §6 — so rule 10's last bullet is
genuinely closed, not cited.

**The guard-for-the-guard demonstrates exactly what it claims.** I read it line
by line looking for the way it could be vacuous and did not find one: it
replaces the body with `BEGIN RETURN NEW; END` inside a transaction, asserts
the structural limb still finds the trigger by name, then asserts the price
actually changed — *"the no-op body did not take effect, so this test is not
demonstrating what it claims"* is the right assertion and most people would
have omitted it.

**The negative control is present twice**, which is what I checked last: a raw
`.update(status=..., version=...)` succeeds, and an ORM `save()` that rewrites
the unchanged price succeeds. The second is the one that matters — `IS DISTINCT
FROM` / `IS NOT` spelled correctly on both engines, so the state machine is not
broken by the guard. `VERIFIED HERE` on both, correctly labelled.

One honest gap, correctly handled rather than hidden: **`ENABLE ALWAYS` is
`ASSUMED THERE`, not verified here.** `SET session_replication_role` needs
superuser and this box's role is not one, so
`test_price_trigger_attack.py` **skips naming engine, slice and the exact
`ProgrammingError`** rather than passing. That is rule 10 obeyed. It also means
the property the restore path depends on is unmeasured, and R11 is where it has
to be measured.

**2 · The coverage regression. The replacement is sound; retire nothing.**

QA's `float_money` attack built `listings` with `asking_price_paise real` by
`ADD COLUMN`; when S2 made the column real it started raising `DuplicateColumn`.
**It stopped loudly, not silently** — the applicability assertion
`test_attack_reaches_the_schema_the_control_reads` is a separate test per shape
precisely so an attack that fails to apply cannot read as an attack that was
caught, and both rows went red. That design is why this was detectable at all,
and it is worth copying.

Backend's replacement (`tests/unit/test_listing_money_column.py::
test_a_real_declaration_fails_via_introspection_despite_the_model`) is
**independent and correct**: it `ALTER COLUMN … TYPE real` inside a rolled-back
transaction and asserts the *union* catches it while the model still declares
`IntegerField` — which is R2's inversion, demonstrated rather than described. It
skips on SQLite naming engine and slice, and the predicate half is asserted on
both engines so the property is not only true where it can be installed.

**Judgement: the original is recoverable and must be restored, not retired** —
by changing the live column's type instead of adding it, which is exactly what
QA has already drafted in the uncommitted tree. The two are not duplicates: one
asks whether the *guard's union* sees a float, the other whether the *attack
corpus* still reaches the schema. Losing either loses a different question.

**3 · The four seam defects. Three of four pin the seam; one pins the
symptom — and the same decorator has a fifth defect.**

Multipart (seam, with the JSON side as its own row — a branch tested on one
side only is a branch with an untested half, and they wrote that down).
409-before-422 (seam, with current-version-illegal-transition as the other
row). Seller terms (seam, with refused-without-tick and recorded-only-when-
ticked as both rows). All three correct.

The timestamp one is R5: the fix is at the seam, the tests are at two
endpoints that happen to carry a timestamp.

And R3 is a **new** defect at the same seam the multipart fix touched — the
fingerprint that excludes `request.FILES`. Worth saying plainly: four defects
found by running the journey, and a fifth sitting in the fix for the first one.
**The lesson is not "run the journey once"; it is that this decorator is the
highest-density defect site in the codebase and needs its own test file.**

**4 · The denormalised columns. Confirmed, measured, Blocking — see B4.**
Backend's instinct was right and their own tests could not reach it. The fix is
already specified and already red in QA's tree; ship the composite FK.

**5 · The copy guard's scope correction. Verified by measurement — backend's
claim is correct in substance, and wrong in one detail not to carry forward.**

```
OLD matcher (\bprice\b anywhere) => 6 findings
  price.label.full   LABEL-SHAPED  "Seller's asking price"  (permitted: carries "asking")
  price.negotiable   prose
  price.seller.hint  prose
  sell.empty.body    prose
  sell.price.locked  prose
  sell.price.relist  prose
NEW matcher                       => 0 findings
```

Five prose plus one label-shaped permitted by its qualifier. **No string
exception is needed, and none was taken** — the CTO's condition is answered.
But **there is no CSS class among the six.** The CSS-class hit was a *separate*
first-draft extractor defect over `templates/listing.html` (`class="price__label"`),
now covered by its own test. Two different measurements, conflated in the commit
message. `Price` and `Max price` still fire. ADR-003 §2.5a holds: "seller's
asking price", never "Price", and there is no numeric offer control anywhere.

**6 · The five unverified claims — my judgement on each.**

| Claim | Judgement |
|---|---|
| Images never decoded | **Backend understates their own work.** No decoder means no decompression bomb and no image-CVE surface, and the serve path closes the XSS vector properly: content type from the server-generated key's extension, format from magic bytes never filename, `nosniff` on both branches, a `.jpg` containing HTML rejected at `strip_metadata`. "Renders as garbage" is the real and only risk, and it is acceptable. **No finding — except R9, where the untested format is the gap.** |
| `X-Accel-Redirect` untested against a real server | **Far better covered than stated.** `test_the_authorisation_is_identical_whichever_path_serves_the_bytes` asserts a *refused* request carries no `X-Accel-Redirect` — that turning nginx on cannot turn authorisation off. Most codebases never ask that. Genuinely untested: real nginx, correctly marked with a `ponytail:` ceiling. **But B1 is a real dev-500/prod-404 divergence on an error path the docstring claims is identical.** |
| Fuzzy search PostgreSQL-only | **Handled better than backend's own framing admits.** `test_a_misspelling_is_found_on_postgres_and_not_on_sqlite` asserts *opposite* properties per engine rather than skipping the weak one, so "SQLite finds nothing" is pinned rather than assumed. Neither vacuous nor skipped — **this is the model for rule 10's both-sides corollary.** Only gap: no existence test for the trigram index (`search_books` uses `similarity()`, which seq-scans, so the index could fail to create and every test would still pass). Suggestion S1. |
| Four-photo cap racy | **Worse than stated. B2.** Not "two simultaneous uploads could both pass" — measured, five stored, on the production engine only. |
| Media in no backup scope | **Wrong in backend's own favour, and the real defect is worse. R11.** Media *is* backed up; what is not tested is the restore, and the restore test reports OK regardless. |

**7 · The three frontend self-found defects.** Service worker: fix is sound for
static files and **incomplete for the two rendered entries** — R6. Checkbox:
accessible-name fix is **correct**, `<label for>` with real text and the link
moved to a sibling, but the required marker went with it — R8; and no test
asserts the computed accessible name, so the regression is prevented by nobody.
Brand link: **correct** — `display:inline-flex` plus `min-height`, and
`min-height` alone would have been inert on a plain inline `<a>`, which is the
non-obvious part. Nothing tests the 44px floor.

**All three were found by looking at a real browser, and each writes down why
the harness passed it correctly.** Combined with backend's four, this slice's
most valuable output is the evidence that **the harness is the thing that needs
work, not the diligence.** R1 is the same point from the other direction.

---

## What this slice introduced that the suite cannot see

Stated separately because it is the part no number covers.

1. **A seller can upload four photos and nobody — not even the seller — can
   see one.** `GET /media/listing-photo/{photo_id}` is in TASKS S2 and does not
   exist, so `listing.html` emits no `<img>` and `sell_photos.html` renders byte
   counts. Frontend handles this correctly and refuses to report the data-saver
   criterion as passing. The suite is green on a photo feature with no photos.
2. **Tamil is 0% reviewed and 86 blocking-class strings deep.** Nothing in the
   suite can tell you that the Tamil a Chennai student reads is undrafted,
   because `i18n.ta_enabled` is off and every test runs in English.
3. **The restore.** R11. The one instrument that would catch a lost-photo
   incident reports OK without looking.
4. **`ENABLE ALWAYS` on the price trigger is unverified on this box** and the
   only place it can be verified is the restore test that does not check it.
5. **Concurrency, generally.** B2 is the one case someone thought to probe. The
   state machine's transitions, the `expected_version` bump and `add_photo` all
   run under `pytest.mark.django_db`, which is one connection in one
   transaction. **No test in this slice runs two connections at once.** S4's
   double-booking work cannot be the first time that is tried.
6. **The suite is not hermetic** (R4) and **not frozen** (E3), so three of its
   properties — the failure count, the a11y coverage number, and
   `test_the_original_is_never_written_anywhere` — are statements about this
   machine's history rather than about either commit.

---

## PRAISE — what to repeat

- **`tests/unit/test_price_immutable.py`.** Both limbs, the guard-for-the-guard
  that asserts it is actually demonstrating its own claim, the negative control
  treated as load-bearing, and every skip naming engine and slice. This is the
  standard.
- **`test_a_misspelling_is_found_on_postgres_and_not_on_sqlite`.** Opposite
  properties per engine instead of skipping the weak one. Copy this shape
  everywhere a property is engine-dependent.
- **Declining Pillow.** A dependency not added is the best kind of security
  work, and the reasoning is written where the next person will read it.
- **The applicability assertion as a separate test per attack shape** — the only
  reason the float-money regression was visible at all.
- **Reverting the two "amount"-substituted strings and shipping the guard red.**
  Rule 13 obeyed under exactly the pressure it was written for, with the
  reasoning recorded so nobody re-litigates it.
- **`templates/_group.html`** — the fieldset/legend sibling to `_field.html`,
  with ids built from `field.name` so `aria-describedby` resolves on every radio
  option, `tabindex="-1"` so the error-summary link lands, and a comment
  explaining *why `_field.html` could not be reused* in terms of the computed
  accessible name. Best-reasoned template in the repo.
- **`_seller_block` / `_disclosure_is_notified`** — two independent gates over
  one string, the second asking the live privacy notice at runtime rather than
  assuming it, both failing closed, and **nothing rendered in the false
  branch.** The absence is the correct output and the code says so.
- **`storage.py:56-68`** answers containment with `Path.resolve()` and a parents
  check rather than scanning for `..` — rule 11's "ask the property, do not
  enumerate the cases", correct on symlinks and UNC paths.
- **`jobs.py:60-66`** deletes the object *before* marking the row, with the
  reasoning written down. The reverse order reports a successful purge while the
  personal data is still on disk, and it is precisely the kind of thing someone
  "tidies" later.
- **`_is_jpeg_metadata` asks "is this an APPn or a COM"** rather than listing
  markers, and the PNG side declares its list's ceiling in the same place.
- **`seller_words()` drops an unrecognised enum rather than printing it raw**,
  and the "zero condition enums in visible text" claim holds on inspection.
- **The `all_objects` allow-list's sixth entry.** The `User` retrofit was
  escalated rather than shipped, on a *measurement* (26 broken tests, sign-in
  impossible before Gate C) rather than an argument, with the other-layer
  question asked **before** the allowance rather than after. That is rule 12
  used correctly, and the ADR's premise being false is the right thing to have
  found.

---

## Verdict line

# CHANGES REQUIRED

**Blocking:** B1 (photo 404 answers 500) · B2 (four-photo cap lost on
PostgreSQL) · B3 (money input 500 on a non-ASCII digit, both layers) · B4
(denormalised child columns, gated manager returns wrong rows).

**Re-review needed on:** B1–B4 and R1–R5. R6–R13 may land as a follow-up
commit in this slice. E1–E3 go to cto, not back to the authors.

**Checked last and most carefully:** the negative control on the price
trigger — a non-price `.update()` and an ORM `save()` both succeed on both
engines, so the guard is narrow enough that the state machine still works.
**QA has not verified this slice; nothing here implies behavioural coverage
that QA has not independently signed.**

---
---

# REWORK PASS — `2af14de..998af8d` (2026-10-22, code-review)

**Scope: this diff only.** The original S2 verdict above stands unamended;
this section reviews the four rework commits against `REDTEAM-S2.md` F47–F54
and the two contract amendments A-25 and A-26 that landed with them. I wrote
none of this code and none of these tests.

**Measurement.** Full suite, both engines, at `998af8d`:

| Engine | Result |
|---|---|
| PostgreSQL (`BOOKHOP_TEST_DB_NAME=test_cr`) | **1 failed**, 1715 passed, 59 skipped, 2 xfailed |
| SQLite | **2 failed**, 1643 passed, 131 skipped, 1 xfailed |

`test_the_backup_scope_and_the_restore_test_cover_the_same_things` fails on
both and **is pre-existing** — verified by running it in a worktree at
`2af14de`, where it fails identically. It is QA's F44 reported as a red test.
`test_the_migration_round_trips_forward_reverse_forward` fails on SQLite only;
it also failed at `2af14de`, but **not in the same way, and the difference is
a finding** (R-R2).

`norecursedirs = tests/redteam` was checked rather than assumed: the tree is
still collectable when named explicitly (`BOOKHOP_REDTEAM=1 pytest
tests/redteam` collects 25). F54 is closed without losing the probes.

**Coverage of Red Team's eight.** F47, F48, F49, F50, F51, F52 and F54 are
addressed in this diff. **F53 is not, and correctly so** — it is owned by
product-manager and design-director and its own text says it is *"a claim to
test against a real student, not a defect to fix in code."* Nothing in the
code range pretends otherwise.

---

## Blocking

### B-R1 · `dialable` refuses real book titles — `apps/catalog/services.py:224` (`_refuse_contact_channel`), via `apps/core/contact.py:86` (`_NUMBER_SEPARATORS`) and `:88` (`_DIGIT_RUN`)

`_NUMBER_SEPARATORS` contains `-`, `.`, `/`, whitespace and the U+2010–U+2015
dash range, and `_DIGIT_RUN` joins digit groups across any run of them.
Applied to catalogue text by A-26, that refuses legitimate input. **Measured,
not predicted** — `contact_channels_in(v, ("addressed", "dialable"))`:

| Value | Field | Result |
|---|---|---|
| `A History of India 1707-1947` | `title` | `['dialable']` → **refused** |
| `Cambridge 2020-2021` | `publisher` / `edition_label` | `['dialable']` → **refused** |
| `Physics ISBN 978-93-5260-123-4` | `title` | `['dialable']` → **refused** |

The sentence the seller is shown is *"Enter what is printed on the book"* —
while they are entering exactly what is printed on the book. `create_book` is
JOURNEYS J2 step 2 and is the **only** path for a book not already in the
catalogue, so there is no workaround: that student cannot list that book.

This is `CLAUDE.md` rule 13's named failure, and A-26 walks into it on the
limb it *kept* rather than the one it exempted. A-26 reasoned carefully about
`/` in `Physics/Chemistry Combined` and did not ask the same question of `-`
between two years. What happens next is rule 13's own prediction: a red test
on a real book title, and an edit to `apps/core/contact.py` under schedule
pressure — the shared definition, which S4's `contact_pattern_flag` also
reads.

It is also rule 10's second disguise. `tests/unit/test_catalog.py:283
test_real_catalogue_text_is_accepted` enumerates eleven real strings and
**not one has a hyphenated or space-separated digit run**, so the accepted
side of the split reads as covered and is not. Where a rule splits a set,
both sides are rows.

**What would fix it** — a contract decision, so this is an escalation to cto
against A-26 rather than a comment to backend. Three shapes, none of which I
should pick: give `dialable` a limb-local rule that a run spanning more than
one separator group needs more than seven digits to count; or set a different
`MIN_DIALABLE_DIGITS` for catalogue text, declared in `contact.py` beside the
limb and not copied into `catalog`; or exempt `dialable` on catalogue fields
too and name the review queue as the catching layer, which A-26 has already
written the paragraph for. Whichever lands, the accepted side gets rows: a
year range, an ISBN, and a volume run.

---

## Required

### R-R1 · An empty limb selector silently selects nothing — `apps/core/contact.py:122` (`contact_channels_in`)

```python
selected = CHANNEL_KINDS if kinds is None else {k: CHANNEL_KINDS[k] for k in kinds}
```

`kinds=()` and `kinds=[]` are not `None`, so they produce `{}` and the
function returns `[]`. Measured:
`has_contact_channel("wa.me/91 98400 12345 priya@x.com", ())` → `False`.

The docstring is explicit that *"a name that is not a limb **raises** rather
than matching nothing: a typo'd kind would be a guard that silently stopped
guarding and was still reported as coverage (rule 10)."* An empty selector is
that same guard, by a different typo, with no exception. No caller passes one
today; this is new public API written for S4 to call.

**Fix:** raise on a falsy-but-not-`None` `kinds` in the same breath as the
`KeyError`, and assert it in
`tests/contract/test_display_name_is_not_a_channel.py:100`, which already
owns the "every limb is reachable" property.

### R-R2 · `listings/0004` destroys F46's diagnostic and the test's own cleanup — `tests/contract/test_tenant_fk_migration.py:316` (`_restore`, line 330)

A regression introduced by this diff, in the shape rule 12 warns about.

At `2af14de` the test failed with its own worded finding
(`assert OperationalError('foreign key mismatch …') is None`, line 248): the
reverse raised, the test captured it, measured the damage, and printed the
F46 analysis.

At `998af8d` it fails with an **unhandled** `OperationalError: foreign key
mismatch - "listing_photos" referencing "listings"`, raised out of the
`finally` block. Mechanism: `migrate listings 0002` reverses `0004` cleanly
and then fails inside `0003`; `_restore` line 330 runs `migrate listings`
forward; `0004` is no longer recorded as applied, so Django re-applies it;
its `ALTER TABLE "listing_photos" ADD COLUMN` makes the SQLite schema editor
run `PRAGMA foreign_key_check` against the table F46 left damaged, and it
raises.

Two things are lost. The F46 finding text — the only place that analysis is
written down as a measurement rather than as prose — is replaced by a raw
traceback. And `finally`'s `_cleanup(listing)` is never reached, which is the
precise thing the test docstring says the `finally` exists to prevent:
*"a half-migrated schema would follow it into every test after."* Nothing
downstream failed in this run, so the damage appears contained today; that is
an observation, not a guarantee.

`ENGINE-DIVERGENCE.md` §13.3 predicts this mechanism exactly — *"every
subsequent `ALTER TABLE` on that table dies with `foreign key mismatch`"* —
and then closes *"**Still open. It does not block S2.**"* The measurement
disagrees with the explanation, so under rule 9's corollary the closing line
goes, replaced by what was measured: 0004 is the first migration to collide
with F46, and it collides inside the harness that reports F46.

**Fix:** capture the restore the same way the reverse is captured, so the
test still reports F46 rather than dying of it, and make `_cleanup` run
regardless. Owner: test-qa, with cto for the §13.3 sentence.

### R-R3 · `INFRA.md` §1 names a verification step that §3.3 does not contain — `company/architecture/INFRA.md`

The new `/media/` box closes with:

> **Verification is a step in §3.3, not a claim here.** With the app stopped:
> `curl … /_protected_media/listings/1/x.jpeg` must print `404`.

§3.3 has steps 1–7 plus 5a. **None of them is that probe**, and nothing else
in the repository performs it — it is nginx configuration, so no conformance
test can. A-25 makes the `internal` location one of the two layers standing
between a student's bedroom photograph and the internet (the other being the
underivable filename, which this diff does build). The document says the
layer is verified somewhere; it is verified nowhere.

This is `CLAUDE.md` rule 9's earned example verbatim: *"a section named four
controls, two of which did not exist."* Either add step 5b to §3.3 or delete
the sentence. Owner: cto and platform-sre.

### R-R4 · The page varies on a request header and sends no `Vary` — `web/views.py:920` (`_save_data`), `:146` (`_page`)

`listing_detail` and `sell_photos` emit a materially different body depending
on the `Save-Data` request header. `_page` sets `Content-Language` and
nothing else: no `Vary: Save-Data`, no `Cache-Control`. Any shared cache in
front — nginx `proxy_cache`, or the transcoding and compressing proxies
common on Indian mobile networks, which are the exact population `Save-Data`
exists for — may serve the image-bearing variant to a data-saver request.
Criterion 9 is then defeated at the cache rather than in the template, and
the template test cannot see it: `grep -n "Vary"
tests/a11y/test_s2_photos.py` returns nothing.

**Fix:** `patch_vary_headers(response, ["Save-Data"])` on any response
`_save_data` was consulted for, and an assertion beside the existing
both-sides split.

### R-R5 · The 0004 backfill is not safely re-runnable, and the tolerant branch is what loses the photos — `apps/listings/migrations/0004_photo_storage_token.py:98` (`forward`), `:76` (`_rename`)

`forward` performs filesystem renames inside a migration Django runs in a
transaction. The renames are not transactional. If anything later in the
migration fails — most plausibly `CREATE UNIQUE INDEX
listing_photos_one_copy_per_listing` on a database that already holds two
rows with one `(listing_id, sha256)` — the database rolls back to the old
`storage_key` values while the files sit at their new random paths.

The re-run then does the damage. `_rename` finds the source missing, returns
`False` *by design*, and `forward` mints a **fresh** token and saves it. Every
affected row now points at a path that has never existed, and the real bytes
are orphaned under a token recorded nowhere. They are unreachable by the app
and invisible to `purge_media`, so `COMPLIANCE.md` §7 row 9's deletion
obligation cannot be met for them either.

`tests/contract/test_photo_storage_key.py:501
test_the_backfill_tolerates_a_row_whose_file_is_already_gone` asserts the
tolerant branch, and it is the branch that causes this. The tolerance is
right for a genuinely purged row; it cannot distinguish that from a
half-applied migration.

**Fix (backend's choice):** make `forward` idempotent — carry the existing
`storage_token` when one is already set and only mint a token for a row that
has none; or copy-then-delete with the delete in `transaction.on_commit`; or
`atomic = False` with a documented recovery. Any of the three; the current
code has none.

### R-R6 · `--photos DIR` writes personal data outside every retention and purge path — `apps/listings/management/commands/review_listings.py:131` (`_write_photos`)

`path.write_bytes(data)` puts a student's listing photographs into an
arbitrary operator-chosen directory, in plaintext, with no expiry.
`COMPLIANCE.md` §7 row 9 governs listing photographs — *"Delete originals and
derivatives from object store and CDN after 1 yr; purge EXIF at upload"* —
and these copies are in neither the object store nor the CDN. `purge_media`
cannot reach them; erasure cannot reach them; the §7 retention clock does not
run on them.

The access **log** row is written (correctly, the naming suggestion below
aside); the **retention** side of the same obligation is not addressed at
all. Charter item 7: a new personal-data path needs a §7 row, a retention
rule and a purge path, and this one shipped with none.

**Fix (the lazy version is fine):** default `DIR` to `tempfile.mkdtemp()`,
print the deletion command on the same lines as the paths, and add the §7
row. Owner: the command's author, with privacy-compliance via cto.

### R-R7 · A-26's amendment-log row cites a finding that does not exist — `company/architecture/API-CONTRACT.md`, amendment table

The A-26 row's source column reads `REDTEAM-S2 F55`. `REDTEAM-S2.md` contains
F47 through F54 and no F55. A-26's own body is honest about the provenance —
*"Backend found this while writing F49's boundary sweep"* — so the table and
the body disagree, and the table is the index a future reader uses. Rule 1:
every factual claim carries a source. One-word fix. Owner: cto.

---

## Suggestions

- **`photos_for_review` logs the wrong field name.** `apps/listings/staff.py:176`
  passes `["listing_photos.storage_key"]`. What the moderator read is the
  photograph; `storage_key` is, after A-25, the one part of that row that is
  *not* personal data. A DPDP r.6(1)(c) reader auditing this log cannot tell
  an image was viewed. `listing_photos.image` or similar.
- **`photo_response`'s cache window.** A-25 corrected the code to the frozen
  `max-age=86400`, which is procedurally right. The contract value may not be:
  the URL is stable (`sha256`), so after `purge_media` nulls `storage_key` the
  student's own browser continues to render the photograph for up to 24 hours.
  `3600` was the safer number, and the amendment chose the contract over the
  measurement without saying it had noticed the trade. cto's call.
- **`_photo_rows`' sort key can 500 the page.** `web/views.py:962`:
  `rows.sort(key=lambda p: (getattr(p, "uploaded_at", None), getattr(p, "id", 0)))`.
  If `uploaded_at` is ever absent, the `None` default makes the tuple
  comparison raise `TypeError`, outside the `try` above it, which only wraps
  `.all()`. Either trust the column or give the default a sortable value.
- **`search.photos_gate` is a `search.`-prefixed key used only on
  `listing.html` and `sell_photos.html`.** No functional effect — it is
  correctly not a blocking class — but the same commit renames
  `listing.photo.alt` to `trust.photo.alt` *because prefixes carry meaning*,
  which makes this one read as an oversight rather than a decision.
- **The `?photos=1` opt-in is lost on the next POST.** `sell_photos.html`'s
  upload form posts to `/sell/{id}/photos` with no query, so a data-saver
  seller who opted in is re-gated after every upload.
- **Two reachable branches of the entropy walk have no fixture.** To QA:
  `_jpeg_entropy_end`'s `marker == 0xFF` fill-byte branch
  (`apps/listings/images.py:184`), and a JPEG carrying a frame header and no
  scan at all. Both are one fixture line and both are currently asserted by
  nothing.

---

## Escalations to cto (not review comments)

1. **B-R1 is an escalation against A-26**, which is cto's own amendment. See
   above.
2. **`locale/ta/BLOCKING_CLASSES.toml` is in the diff** (charter item 10a: a
   diff to a locale manifest is an escalation by construction, because adding
   a hash is functionally granting a reviewer's sign-off). **Checked and
   benign.** No hash is added; no `reviewer` field is written; no class scope
   or prefix is widened; `locale/ta/REVIEWED.toml` is not in the diff; and
   `i18n.ta_enabled` is untouched, so the new blocking-class string's
   unreviewed Tamil draft is not served. What the file gains is three
   `_at_S2_rework` counts and a `measured_by` line that **declares the new
   counts are not comparable with the existing `_at_S2` row and does not
   explain the discrepancy away** — which is rule 10's instrument rule
   honoured, and the right call.
3. **No ADR-003 §2.3 trigger in this diff.** Checked: no settled price, PAN,
   Aadhaar, DOB, UPI handle, address, balance or credit; no offer, bid or
   counter-offer amount; **no new numeric column at all** (`storage_token` is
   a `TextField`); and no new column on, or widened CHECK in, `transfers`,
   `transfer_events`, `messages` or `transfer_followups` — none of those
   tables exists yet. `queue_rows` newly **reads** `asking_price_paise`, which
   is the one whitelisted money column, and `_as_written` divides only for a
   printed line and stores nothing.

---

## Praise

**The entropy walk is correct, and I checked it as byte arithmetic rather
than taking the comment's word.** `_jpeg_entropy_end`
(`apps/listings/images.py:170`) terminates on every input: the main loop's
fill-byte consumption advances `i` by at least one each iteration, and the
walk is monotone in `j`, so even when it returns `i` unchanged the preceding
`i += length` has already made progress. It cannot read past the buffer —
`j < end - 1` guards the only two-byte read, and every other access is a
Python slice. Stuffed `FF 00`, RST0–RST7 and `FF` fill are each consumed;
anything else ends the scan; a scan that runs off the end returns `end`, which
`saw_eoi` converts into `ImageRejected` rather than into a stored file whose
end nobody located. Choosing the walk over `data.find(b"\xff\xd9")` is the
right call for the reason the comment gives: the one-liner would have stopped
at a progressive JPEG's first scan and copied every inter-scan APP1 unexamined
— the same defect, relocated.

**Asking the other two containers the same question instead of asserting they
were fine.** PNG is recorded as *verified, no change needed* with the reason;
WebP turned out to have the same defect and was fixed in the same pass. *"The
other formats do not have this problem"* is a claim, and it was measured.

**`photos_for_review` is a genuinely separate authorisation, and I verified
each half.** `get_photo_for_download` is byte-for-byte unchanged across
`2af14de..998af8d`. `listing_for_review` refuses a non-staff actor before any
row is touched, and `log_personal_data_access` re-checks `is_staff_member`
independently — two layers, as rule 12 asks. The access row is per **opening**
and `queue_rows` deliberately writes none, which is the right line.
`test_the_student_photo_path_was_not_widened_to_let_staff_in` pins the
non-widening so a future "simplification" fails by name. The purged-row case
returns `None` rather than crashing, and the caller says so in words.

**`0004`'s `SeparateDatabaseAndState`, and §13.1's claim is true.**
`listings/0003` installs `listing_photos_parent_tenant_fk` with raw SQL, so it
is absent from Django's model state, and the SQLite backend implements
`AddField` and `AddConstraint` by rebuilding the table from that state. A
plain `AddField` would have dropped the composite FK on SQLite only and
silently. Raw `ALTER TABLE` / `CREATE UNIQUE INDEX` avoids the rebuild on both
engines, and `test_the_composite_foreign_key_survived_0004` asserts it on
both rather than predicting SQLite from PostgreSQL. **And the replacement
constraint went in *in the same migration* as the token that removed its
predecessor** — I checked the operation order, and
`test_the_database_refuses_it_too_whatever_the_service_does` proves the
database holds the property and not merely the service. Rule 12, honoured
where it is easiest to skip.

**The alt text passes the limb no grep can check.** *"Photo 2 of 4, uploaded
by the seller"* is position plus provenance: it describes a mechanism and
names a fact, and makes no prediction and no judgement about a book, a person
or an outcome — `COPY-DECK.md` §1.2's six-row table, passed on the side
`test_forbidden_copy.py` cannot see. The Tamil
(*"%(n)s படங்களில் %(i)s-வது படம், விற்பவர் பதிவேற்றியது"*) renders the same
fact and warrants nothing; *"open the full-size photo"* is an instruction and
*"Show {n} photos (about {kb} KB)"* is an instruction plus a measured number.
None of the eight forbidden words appears, and nothing says "Price". The
`listing.photo.alt` → `trust.photo.alt` rename is rule 13's first resort used
correctly: one key name, control at full strength, nothing added to a
manifest.

**The deleted string.** `listing.photos.pending` — *"BookHop has no way to
show them yet"* — is removed from both catalogues rather than left to go
quietly false, and `web/selfcheck.py`'s *"check that has not started"*
sentence is deleted rather than softened now that the line it described
exists. Rule 9's corollary, applied twice in one diff, to the authors' own
prose.

---

## Verdict line (rework)

# CHANGES REQUIRED

**Blocking:** B-R1 — `dialable` refuses `A History of India 1707-1947`,
`Cambridge 2020-2021` and any ISBN typed into catalogue text, on the only
path a seller has for a book not yet in the catalogue. It is an escalation
against A-26 and not a comment to the author.

**Required before merge, or as a follow-up commit in this slice:** R-R1
(empty selector), R-R2 (F46 diagnostic destroyed), R-R3 (INFRA §3.3 step that
does not exist), R-R4 (`Vary: Save-Data`), R-R5 (backfill not re-runnable),
R-R6 (photo export outside retention), R-R7 (A-26 citation).

**Not introduced here:** both red tests predate the diff
(`test_the_backup_scope…` on both engines, F44's surviving half) — except for
the *shape* of the SQLite one, which is R-R2.

**Checked last and most carefully** — recorded although this is not an
approval, because it is the thing a later reader will want to know was
checked: the JPEG entropy walk, against the specification, for termination
and for out-of-bounds reads on every input shape I could construct —
stuffing, restart markers, `FF` fill, truncation mid-scan, truncation
mid-header, a second concatenated image, and a file with a frame header and
no scan. It terminates on all of them and reads nothing it does not own.

**QA has not independently verified this rework.** The behavioural assertions
cited above are the authors' own tests, read and run by me; nothing in this
section implies coverage test-qa has signed.
