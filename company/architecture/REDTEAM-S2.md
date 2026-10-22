# Red Team — S2 per-slice pass

Slice: S2 (listings, photos, requests) · Tree frozen at `2ad8ca7`
Engines: PostgreSQL 16 and SQLite, both run · Probes: `tests/redteam/**`
Run with `BOOKHOP_REDTEAM=1 pytest tests/redteam -q` → **14 red, 11 green**

**Authorship note.** The probes and their measurements are the red-team
agent's. Its pass was stopped by the founder after the findings were
confirmed on both engines but before it wrote this memo; the CTO assembled
the memo from the probe assertions. Every number below is quoted from a
probe that runs, not from the agent's prose.

---

## Verdict

**S2 should not ship as built.** Not because it is incorrect — two gates
established that it is — but because **the thing the slice exists to deliver
does not reach a human**, and because the privacy guarantee it advertises is
not the one it provides.

Both gates passed a slice whose headline feature is invisible. That is the
finding about the gates, and it is the more useful half: Code Review asked
*is this correct*, QA asked *does this match the specification*, and the
photo pipeline is correct and does match. **Nobody owned the question "does
a photo reach an eye."** That question belongs in the per-slice pass, and it
is now the first thing this pass asks of every slice.

---

## F47 · The EXIF stripper never walks past the end of the image — CRITICAL

Owner: **backend-developer** · `apps/listings/images.py`

`strip_metadata` removes every metadata segment between SOI and SOS, and
`listing_photos.exif_stripped_at NOT NULL` encodes that as a structural
guarantee. The stripper stops at SOS. **Every byte after the EOI marker is
copied verbatim into storage.**

Every current Samsung and Pixel, with Motion Photo / Top Shot on **by
default**, appends a complete secondary media stream after EOI.
Multi-Picture Format (CIPA DC-007) appends a second whole JPEG — carrying
**its own, unstripped, APP1 EXIF with the GPS IFD**.

Measured: 78 bytes placed after EOI, including an APP1 block with a GPS tag,
reached disk at `listings/13/c7941….jpeg` — **with `exif_stripped_at` set**,
the row asserting a strip that did not happen. A second concatenated JPEG
keeps its `Exif` segment intact.

*What would have to be true for this to be fine:* that no student uploads
from a phone with Motion Photo enabled. The default is on.

*Cheapest disproving test:* already written —
`test_everything_after_the_eoi_marker_is_copied_into_storage`. **Pass
threshold: zero bytes after the primary image's EOI reach storage.** The fix
truncates at EOI; the regression belongs in the backend's tree.

---

## F48 · No page a student is served shows a photo — CRITICAL (to the slice)

Owner: **frontend-developer**

Two photos: stored, stripped, authorised, and served over HTTP with
`200 image/jpeg` — verified by the probe immediately before this one. Then:
**no page emits an `<img>`, names a `sha256`, or names either photo URL.**
Measured across `/sell`, `/sell/{id}/photos` and `/listing/{id}`.

The listing page says so, in words: *"BookHop has no way to show them yet."*
It is served to buyers. A buyer deciding on a used book is shown a sentence
explaining that the photos exist and cannot be seen.

*What would have to be true:* that a buyer will commit to meeting a stranger
for a physical book they have not seen. That is the slice's whole premise,
inverted.

*Cheapest disproving test:*
`test_no_page_a_student_is_served_points_at_a_photo`. **Pass threshold:
`/listing/{id}` emits one `<img>` per stored photo.** The probe also carries
a retirement assertion on the "no way to show" copy, so the sentence cannot
outlive the gap.

---

## F49 · `display_name` is an unlogged contact channel — MATERIAL

Owner: **backend-developer** (the field) + **privacy-compliance** (the claim)

`listing.html` states: *"No address, no phone, no email — **there is no such
field**."* `API-CONTRACT.md` §5.2 states: *"Listing responses never contain …
a phone number."* Both are claims about **key names**. Neither constrains
**contents**.

Measured: `update_profile(seller, display_name="Priya R — wa.me/919840012345
· call me")` is accepted without comment — the only rules are non-empty and
≤60 characters, with no character class at any layer. It then renders on
`/listing/{id}` **twice** (the seller block, and the `<cite>` attribution
under the seller's own condition quotation — two independent sites, so a fix
that sanitises one leaves the other), and ships in the L2 JSON payload.

This is the **disintermediation** standing target arriving as a product
defect: one seller types it once, and every buyer leaves the platform.

*Cheapest disproving test:*
`test_a_phone_number_reaches_the_listing_page_twice`. **Pass threshold: zero
renderings.** The rule must be asked as a property, not enumerated as
patterns (rule 11).

---

## F50 · The moderator deciding a pirated book sees neither the claims nor the photos — MATERIAL

Owner: **backend-developer** · `apps/listings/staff.py`, `review_listings`

At pilot `LISTING_REVIEW_ALL=true`: every listing stops at `PENDING_REVIEW`
and a human decides. That human is **the only control** between a photocopied
textbook and a buyer.

Probe fixture — the pirated-copy shape, in values a seller really types: a
₹900 prescribed textbook offered at **₹60** (the campus-gate photocopy price
named in `company/README.md` §1), claimed `AS_NEW`, no damage, no
annotations, four photos. Every field lawful; the *combination* is the signal.

What the reviewer is actually shown:

```
#14  2026-10-22 12:38  signup  9788177589139  Engineering Mathematics
     photos=4  verified_book=False  suspect=False  seed=True
```

- **`condition` and `damage_flags` are absent.** `queue_rows` returns them;
  the only command that reads it does not print them.
- **The asking price never reaches the reviewer at all** — not in the line,
  not in `queue_rows`' keys. The strongest piracy signal is the one number
  the decision cannot see.
- **No photo.** `get_photo_for_download` refuses staff (not the owner, gate
  closed, row not seed), so a moderator whose documented job is *"about the
  book **and the images**"* cannot obtain an image through any shipped
  surface.

*Cheapest disproving test:* the three probes in
`test_what_the_moderator_sees.py`. **Pass threshold: the queue line carries
condition, damage flags and asking price, and one staff path resolves photo
bytes.**

---

## F51 · The photo gate is bypassable at the deployment seam — CRITICAL

Owner: **cto** (contract conflict) + **platform-sre** (deployment)

`API-CONTRACT.md` §5.2 (A-20) requires photo bytes behind a Django
authorisation decision, *"off any publicly-routable path"*, served only via
`X-Accel-Redirect` from an nginx `internal` location. **Two frozen documents
describe the opposite:**

- `ADR-001-stack.md` §2.6 — *the clause A-20 cites as its own authority* —
  puts `MEDIA_ROOT` on a location *"served by nginx"*.
- `INFRA.md` §1's topology diagram routes `/media/` direct.

Neither names an `internal` location; neither sets
`BOOKHOP_MEDIA_INTERNAL_PREFIX`, which `settings/base.py` tells the operator
to set **by pointing at the document that specifies the opposite
arrangement.**

And the path is **derivable**: `add_photo` builds
`listings/{id}/{sha256[:32]}.{fmt}`, and `listing_payload` publishes the full
`sha256` and the id. Anyone who can read one listing response can write down
the exact path on disk and hand it to anyone at all — **the authorisation
decision stands in front of a door whose key is printed on the door.**

*What would have to be true:* that the operator reads A-20 rather than the
two deployment documents. The operator reads `INFRA.md`.

*Cheapest disproving test:*
`test_the_two_deployment_documents_put_media_root_on_a_public_nginx_location`.
**Pass threshold: both documents describe the `internal` location, and the
stored filename is not derivable from any field in a listing response.**

---

## F52 · The shipped photo route is not the frozen one — MINOR

Owner: **cto**

Three divergences from a *frozen* contract:

| | Contract (A-20) | Shipped |
|---|---|---|
| path | `/media/listing-photo/{photo_id}` | `/api/v1/listings/{id}/photos/{sha256}` |
| identifier | `photo_id` | `sha256` |
| cache | `private, max-age=86400` | `private, max-age=3600` |

The contract path is **unrouted** — it 404s. Minor alone; it matters because
the identifier change is what makes F51 exploitable, and a frozen contract
that diverges silently is how F51 came to be written.

---

## F53 · The intake form costs six decisions against a promise of three — MATERIAL

Owner: **product-manager** + **design-director**

`sell_find.html` promises *"about two minutes: the ISBN, what's wrong with
it, and your price."* Measured: **6 required decision groups across 18
individual controls**, then **5 round trips** from "I have a book" to a row
**not yet visible to anyone** — it lands at `PENDING_REVIEW`.

The benchmark named in `company/README.md` §1 is posting a photo to the batch
WhatsApp group: **one action, zero required fields, instantly visible.**

A claim to test against a real student, not a defect to fix in code. **Pass
threshold: a student completes the flow unaided in under two minutes** —
which is also the first thing the ₹0 concierge pilot can measure.

---

## F54 · This probe tree joined the suite both gates quote — MINOR

Owner: **cto** · `pytest.ini`

The charter says `tests/redteam/**` is *"excluded from the default suite
run."* **It was not** — `testpaths = tests` with no `norecursedirs`, so every
red probe would have joined the headline count the moment the directory
existed. The agent implemented the opt-out in its own `conftest.py`, skipping
with a reason that names the switch and the slice (rule 10), because
`pytest.ini` is outside its write scope during a freeze. The exclusion should
move to `pytest.ini`.

---

## Seams number

**6 of 7 findings are at seams between artefacts; 1 is within one.**

Only F47 lives inside a single file. Every other finding is a gap *between*
two things that are each correct alone: a backend that serves photos and a
frontend that never asks for one; a field in `accounts` and a claim about it
in `listings`; a queue builder and the command that reads it; a contract and
the two deployment documents that contradict it; copy and the form beneath it.

**86% seams.** The gate is still earning its cost. Per the charter, the number
to watch is whether it drops — if two consecutive passes produce only what
Code Review or QA could have caught, re-point the pass; do not drop the gate.

---

# Red Team — S2 **re-report**, scoped to the fixes

Tree frozen at `6f4660d` · Probes `tests/redteam/**`, both engines run
Run: `BOOKHOP_REDTEAM=1 ./.venv/Scripts/python.exe -m pytest tests/redteam -q`
→ **PostgreSQL 16: 8 red, 22 green** · **SQLite: 11 red, 19 green**

**Polarity, stated because this tree now has two authors' conventions in it:
every assertion asserts the SAFE outcome, so red is a finding and green is
closed.** The three engine-divergent reds are named by engine below.

Scoped to the eight findings and the A-26→A-33 rework, per the charter's
termination rule. This is not a fresh pass; nothing outside the fixes was
re-measured.

## The eight, measured

| | state | measurement |
|---|---|---|
| **F47** EXIF past EOI | **closed** | `test_what_survives_the_strip.py` green both engines. Closed **wider than found**: the progressive-JPEG inter-scan and WebP limbs were not in the finding |
| **F48** no page shows a photo | **closed** | `test_the_photo_nobody_sees.py` green both engines, including the retirement assertion on the *"no way to show them"* copy and `Cache-Control: private, max-age=86400` — which also closes F52's cache row |
| **F49** `display_name` as a channel | **closed** | all three probes now fail **in setup**: `update_profile` raises `ValidationFailed` — *"Use a name, not a way to reach you…"*. The condition cannot be constructed, which is the strongest form of closed |
| **F50** moderator blind | **closed** | condition, damage flags and asking price green. Photo limb closed by a **new** authorisation (`photos_for_review`, staff-only, writes `personal_data_access_log`) with `get_photo_for_download` left refusing staff — a separate authorisation, not a widening (rule 12) |
| **F51** derivable storage key | **closed** | probe red with *"the key is no longer derivable from the payload"*: `listings/1/d380…` vs `listings/1/e8c5…`. Random token, so the sha256 in the payload buys nothing |
| **F52** deployment seam / frozen route | **closed** | `test_the_two_deployment_documents_…` green both engines: both documents now carry the `internal` location / `X-Accel-Redirect` |
| **F53** intake friction | **open, by decision, and correctly** | both probes still red on both engines: **6 required decision groups across 18 controls, 5 round trips**, landing at `PENDING_REVIEW`. Not a code defect — my own text said so. **It is the only one of the eight that decides whether S2 was worth building** |
| **F54** probe tree in the suite | **closed** | exclusion moved to `pytest.ini`; the `conftest.py` opt-out is now belt-and-braces rather than the only layer |

**One of those eight closures was mis-measured by my own instrument, and it is
mine to report.** F50's photo probe asked `get_photo_for_download(staff, …)`
and inferred from that one refusal that *"no shipped surface"* resolves bytes.
The fix moved the surface. **The probe therefore stayed red against a closed
finding** — it enumerated a case where it should have asked a property
(`CLAUDE.md` rule 11, applied to this agent's own tree). Re-pointed to sweep
every public staff callable; now green. A probe tree that reports closed
findings as open is the performative-objection metric going non-zero, so it is
recorded here rather than quietly fixed.

## F55 · A-29 §3's sentence is false a fourth time, in the same shape — MATERIAL

Owner: **cto** (the ruling) + **backend-developer** (`search_books`)
Probes: `tests/redteam/test_the_gate_that_only_withholds_the_answer.py`

> A-29 §3: *"no seller-written catalogue text reaches another student without
> a named human having looked at it."*

That sentence is what authorised deleting `CATALOGUE_CHANNEL_KINDS` entirely.
Code Review and QA both attacked **what the gate serves**, and so does
`tests/unit/test_catalogue_text_gate_is_enforced.py`, which walks `apps/**`
and `web/**` for reads of the four `SELLER_WRITTEN_TEXT` **attribute names**.

**Nobody asked what the database is permitted to *match* on.** A value you may
not read is still a value you may filter by. `GET /api/v1/books?q=` is live,
signed-in, and calls `search_books`, which matches on `title_norm` — **a copy
of the seller's words in a column that is not in `SELLER_WRITTEN_TEXT`**, so
the gate's own AST instrument cannot see this path even in principle. The
extraction never names a sealed attribute.

Measured, same probe, both engines (**VERIFIED HERE**, not assumed):

| engine | `?q=call 9840012345` | digits recovered |
|---|---|---|
| **SQLite** | selects the row | **10 of 10** |
| **PostgreSQL 16** | selects nothing | 0 — no foothold |

Ten signed-in `200` searches per digit recover a phone number out of a column
the same response refuses to print (`title: null`, `text_withheld: true`), with
**no listing in existence** — asserted — so A-29 §2's structural gate is not a
layer over this path, and `review_listings` still prints *"Nothing is waiting
for review."*

**Why this is material and not "SQLite only":**

1. `search_books`' own docstring fixes the contract: *"the contract either
   engine satisfies is the weaker one — substring — so nothing above this
   function may assume fuzziness."* **The weaker contract is the oracle.**
   A-29 §3 is false against the documented contract and true only against one
   engine's implementation of it.
2. On the engine that ships, the sentence holds **by trigram arithmetic** — a
   15-character needle cannot reach `similarity() >= 0.3` against a
   53-character title. Nobody chose that, and no document records that the
   gate's safety depends on it. `ENGINE-DIVERGENCE.md` records the functional
   half of this divergence (*a misspelling finds nothing*) and not the half
   that decides whether gated text is readable.
3. **The obvious improvements reopen it.** A substring or prefix fallback for
   short needles is the natural fix for "a misspelling finds nothing", and
   `search_books`' own `ponytail` note already schedules a change to this
   predicate in S3.

*What would have to be true for A-29 §3 to stand:* that "reaches a student"
means "is serialised into a response body". It does not; it means the student
learns the text.

*Cheapest disproving test:* the four probes in that file. **Pass threshold: a
needle appearing only in withheld seller-written text does not change the
result set, and no document-level claim about the gate is engine-conditional
without saying so.** The regression belongs in backend's and cto's trees — one
test on the predicate, one line in `ENGINE-DIVERGENCE.md`.

**This is the finding the founder asked for, and it lands in the predicted
shape with one difference worth more than the finding.** Across A-26, A-28 and
A-30 the clause that failed measurement was every time the one asserting
another layer made a narrowing safe. A-29 §3 is the fourth — and it failed for
a new reason. Not an unmeasured layer this time: the layer it names (staff
review) is real and measures fine. What was never enumerated is **the set of
ways text reaches a student**, before the sentence quantified over it.
**Rule 12 as amended today would not have caught this.** The missing demand is
narrower and is the one to add: *a claim quantified over "every path" names the
paths it was measured against.*

## F56 · A-32's two halves collide: the own-words remedy cannot reach the screen it exists for — MATERIAL

Owner: **backend-developer** (no update path) + **cto** (the idempotency clause)
Probe: `…::test_a_student_cannot_replace_the_bare_line_with_their_own_words`

A-32 shipped two clauses in one ruling: *a student's own words are served back
to that student in place of a withheld row's text*, and *idempotency for a
request carrying a book FK keys on `book_id` and `course_code`, never on the
typed label*. Each is right alone.

Walk the journey the first clause exists for. A student looks up an ISBN,
finds an unverified row, types no title — the form does not require one once
the ISBN resolves — and is shown the bare `ISBN 9789387432147` line with the
withheld disclosure. They then do the one thing that screen invites: they go
back and type the title.

**The second clause swallows it.** Same `book_id`, same `course_code` (`None`,
because the field is optional), so `create_request` returns the existing row
and the typed title is discarded — with a flash reading *"That is on your list
below"*, which is true and useless. Measured on both engines:
`free_text_title=None` after the second submission, one row, page still bare.
**There is no `update_request`, so the state is terminal.**

This is **F51's defect — "a student's own typed title is silently discarded" —
re-created by the ruling that fixed it**, on the retry path instead of the
first submission. A-33 recorded what A-32's key swap *gains* (two course codes
are two wants); this is what it costs, and it was not recorded.

*Cheapest disproving test:* the probe. **Pass threshold: after the second
submission the student's own words are on the page.** The cheapest fix is not
an update endpoint — it is `wanted` filling `free_text_title` on an existing
row when it is `NULL` and the student typed one.

## Seams number

**2 of 2 artefact findings are at seams between artefacts. 100%.**

- **F55** sits at three seams at once: the gate (which controls values) and the
  query layer (which controls predicates); the four sealed attribute names and
  `title_norm`, an unsealed copy of one of them; and the two engines, where one
  ruling's truth value differs and no document says so.
- **F56** sits at the seam between two clauses of a single ruling, each correct
  in isolation.

Counting my own stale probe as a third finding — it is one, and it is *within*
an artefact (this tree) rather than between two — the number is **2 of 3,
67%**. Both are reported; the charter's metric is about artefacts, and by that
measure the pass is still 100% seams. Neither F55 nor F56 is a defect Code
Review or QA could have caught under their own questions: both gates asked
about the serving path, and both were right about it.

## Verdict

**Ship S2. Do not spend on the pilot yet, and F53 is why.**

The verdict changed, and not because the slice got stronger where I attacked
it — seven of eight closed, several wider than the finding, and the two new
ones do not reach a buyer on the shipping engine. F55 is a false sentence in a
frozen document guarding a real hole on a non-shipping engine; the remedy is a
test on the predicate and a line in `ENGINE-DIVERGENCE.md`, not a rework. F56
costs one student a bare line on their own want list.

**What has not moved at all is the only question that decides whether S2 was
worth building.** F53 is still red: six decision groups, eighteen controls,
five round trips, and the row is invisible to everyone when it lands. The
benchmark is a photo in a batch WhatsApp group — one action, zero fields,
instantly visible. Three gates and six contract rulings have made S2 correct
and trustworthy. **Nothing in any of them made it wanted.** That is the
charter's "correct and still not worth having" outcome in its conditional
form, and the cheapest test that resolves it costs ₹0: one student, one
unaided attempt, two minutes on a clock.

**One finding about the gates themselves, since every blocking finding in the
three rework gates was against the contract rulings and not against the
build:** the defect source for this slice was the contract document, not the
code. A fourth gate would not have helped. The intervention that would is the
one F55 argues for — a ruling that quantifies over "every path" ships with the
list of paths it was measured against — and it costs a sentence, not a gate.
