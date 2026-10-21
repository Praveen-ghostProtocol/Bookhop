# JOURNEYS — BookHop v1

**Owner:** `product-manager` · **Version:** v1.0 · **Date:** 2026-10-21 · Phase C
**Handoff:** `design-director`, `cto`, `test-qa`, `red-team`
**Companion:** `product/PRD.md` — stories, acceptance criteria, exclusions and
the five contract disagreements (`CG-1`…`CG-5`) referenced throughout.

---

## 0. How to read this, and the sequencing note

**These journeys were written after `DATA-MODEL.md` and `API-CONTRACT.md` were
frozen.** `PRD.md` §0 records what that cost. Three of the five consequences are
visible in this file: **J5 cannot be completed as designed** (no reschedule
transition, CG-1), **J9 has no student entry point** (CG-2), and **J4 has no
ending** (no want-matched notification and nothing writes
`fulfilled_by_transfer_id`, CG-3 + CG-4). Where a journey depends on an
amendment, the step is marked **⛔ BLOCKED (CG-n)** and the current behaviour is
described beside the intended one, so nobody implements the gap by accident and
nobody ships the blocked step thinking it works.

**Conventions.**

- **State** columns name the `listings.status` / `transfers.state` value from
  `DATA-MODEL.md` §6. A student **never sees these strings** — every screen
  renders the state in plain EN and TA (AC-H1.4).
- **Goes wrong** is not an appendix. Each journey's error states sit in the step
  table beside the step that produces them, because a failure a student sees at
  step 4 is part of step 4.
- **Staff** columns and the `-staff` journeys are specified to the same depth as
  the consumer side, per my charter. At pilot scale, "staff" is **one human**.
  Every staff journey is written for that reality and says where it strains.
- **Forbidden strings.** No copy in this file, EN or TA, may contain *safe,
  verified, protected, guaranteed, assured, trusted, certified, authentic*.
  Illustrative copy below is behavioural intent; `design-director` owns the
  final words.

**Journey index.**

| | Journey | Primary metric it serves |
|---|---|---|
| **J1** | First run, age, consent, campus confirmation | verified students |
| **J2** | Listing a book | valid listings; supply density; T1a |
| **J3** | The cash sale — the spine | match rate; completion rate; leakage band |
| **J4** | The book that is not there | match rate (request limb) |
| **J5** | The handover that fails | no-show rate; cancellation rate; `COORD` minutes |
| **J6** | The disputed condition | dispute rate |
| **J7** | Reporting a listing | reports/1,000 listings; time to moderate |
| **J8** | Account deletion | DSRs inside 7 days |
| **J9** | Getting help inside the product | support load — the D-009 trigger |
| **J2-staff** | Listing review queue | `INTAKE` minutes; confirmed misdescription |
| **J5-staff** | Reaching the other student (relay, then disclosure) | `AFTER` minutes; safety incidents |
| **J6-staff** | Resolving a dispute with no money in it | time to dispose |
| **J7-staff** | Moderation, takedown clocks, repeat infringers | zero missed statutory clocks |
| **J8-staff** | Age revocation, erasure, data-subject requests | DSRs inside 7 days |
| **J9-staff** | The support stopwatch | support load |
| **J10-staff** | Opening a campus | — (a gate, not a metric) |
| **J11-staff** | A safety incident | safety incidents — target zero |
| **J-DEFERRED** | Direct swap, kept warm | — |

---

## J1 · First run, age, consent, campus confirmation

**Who.** A 2nd-year student who was handed a slip at the library gate, or
followed a link a classmate sent.
**Entry point.** `GET /` on a mid-range Android over 3G. No app install, no
password, no phone number.
**Problem it serves.** US-A1, US-A2, US-A3. Every step here is a reason to
leave, and the student has not yet seen a single book.

| # | Step | Student sees | State after | If it goes wrong |
|---|---|---|---|---|
| 1 | Lands on `/` | One sentence on what BookHop is, one field: college email. No carousel, no tour (EX-8). If the campus gate is closed, the page says listings open when the service launches, names no date, and offers to be emailed | — | JS disabled: identical page, form POSTs normally |
| 2 | Submits email → `POST /auth/start` | "Check your email." **Plus the accepted domains, named generically:** *"We can only email addresses ending @example.ac.in — check you used your college address."* | — | **Wrong domain:** identical 202 and identical page (AC-A1.1). The domain line at step 2 is the only thing that stops this being a silent void. **No MoU yet** (`email_domains` empty, EC-11): the same page says the campus is not open for sign-ups yet. **Rate limited** (5/hr per email, 20/hr per IP): "too many requests, try again later" with `Retry-After` honoured |
| 3 | Opens the link → `GET /auth/c/{token}` | Signed in. Session rotated. Server returns `needs: ["age","consent","campus"]` and routes to the first outstanding one | `users.status='PENDING_VERIFICATION'` | **Expired** (>10 min) or **already used:** a plain page — "this link has been used, ask for a new one" — with a working button. Never a stack trace, never a bare code |
| 4 | Declares date of birth → `POST /account/age` | One `<input type="date">`. Copy states it is used once to confirm 18+ and not kept | `adult_verified=true`; `age_verification_events` ADULT_CONFIRMED / SELF_DECLARED_DOB_SERVER_CHECKED; DOB discarded (CG-5) | **Under 18:** refused, account deleted immediately, no `users` row, no `age_check_pending` row, **no DOB anywhere**. Copy states the rule and stops — no workaround suggested, no invitation to return with another date (AC-A2.3). Client block bypassed: same server result (AC-A2.2) |
| 5 | Grants consent → `POST /account/privacy` | Six purposes, listed individually, **none pre-ticked**, each one sentence, with the exact notice version named and linked | `consents` rows appended | **Declines a required purpose** (`account`, `listing_publication`): the screen says which action that blocks and leaves the student signed in. Declining `notifications` or `location_proximity` is fine and the product still works |
| 6 | Campus confirmed | Implicit — the email domain matched, so nothing is asked. "College email confirmed" | `campus_verified=true`; `campus_verifications` method `INSTITUTIONAL_EMAIL`. **No enrolment artefact is ever stored** | **Domain matched no campus:** should be impossible after step 2; if it happens, a staff manual-verification queue entry, and the student is told a human will look |
| 7 | Arrives at search | Search box, and the honest empty state. **Not** a feed, not a tour | `status='ACTIVE'` | **Gate closed** (EC-10): the pre-launch page, with no listing data on it, and an offer to be emailed at launch |

**What staff see.** Nothing, on the happy path — and that is the design. Staff
see only two things from J1: the `STAFF_MANUAL` campus-verification queue
(expected empty), and an `age_verification_events` row they never need to open
unless a revocation happens (J8-staff).

**Where this journey strains.** Steps 3–6 are four screens before the student
has seen a book. That is the legal minimum and it is still four screens.
`design-director`: steps 5 and 6 should be one screen with the consent list and
the "college email confirmed" line together, if that can be done without
pre-ticking anything.

---

## J2 · Listing a book

**Who.** A 3rd-year who has four finished books under the bed and no urgency
whatsoever.
**Entry point.** `GET /sell` from the main navigation, or the "sell a book"
action on an empty search result.
**Problem it serves.** US-S1 to US-S4. T1a's 60% bar is measured here.

| # | Step | Student sees | State after | If it goes wrong |
|---|---|---|---|---|
| 1 | Opens `/sell` | "Put up a book" and a single field: ISBN. A line explaining where the ISBN is on the back cover | — | — |
| 2 | Enters ISBN → `GET /sell/find-book` | The matched book: title, authors, edition label, publisher, year. "Is this the one?" | — | **Checksum invalid:** "that ISBN doesn't look right — check the digits" with the field preserved. **Not in catalogue:** offered the "add this book" form (title, authors, edition, publisher, year); the created `books` row is flagged for staff verification. **No ISBN on the book** (pre-ISBN): routed to staff approval, cannot self-publish (AC-S4.4) |
| 3 | Confirms the edition | — | `books` row resolved | **Two near-identical editions returned:** both shown with the edition label and year side by side. We do not guess |
| 4 | Describes the copy | `condition` as four plain descriptions attributed to the seller, never a grade or a score (AC-S3.1). `annotation_level` as neutral fact. `damage_flags` as a checklist **with an explicit "none of these"** the seller must tick (AC-S3.2) | — | **Damage list left untouched:** the form does not submit. An empty damage list that submits is an implied no-damage claim the seller never made |
| 5 | Sets a price | One field, in rupees. One line: *"This is the price you're asking. You can't change it later — you'd withdraw and put it up again."* **No suggested price, no range, no "similar books"** (EX-3) | — | **Non-numeric / negative / absurd:** field error. The ceiling is Rs 1,00,000 (schema CHECK) |
| 6 | Accepts seller terms | Short, plain: your own description; no photocopies, scans, spiral-bound reproductions, or copies marked for sale in another territory; you meet the buyer at a campus point | `seller_terms_acceptances` row against the current notice version | **Not accepted:** `403 SELLER_TERMS_NOT_ACCEPTED`, rendered as the terms screen again, not an error page |
| 7 | Creates the listing → `POST /sell` | "Saved as a draft" | `listings.status='DRAFT'`; `asking_price_paise` and `price_fixed_at` set and now **immutable by trigger** | — |
| 8 | Adds photos → `POST /sell/{id}/photos` | Up to 4, ≤8 MB each. Guidance: the cover, the spine, the edition page, any damage | `listing_photos` rows; `exif_stripped_at` NOT NULL — **the row cannot exist unless EXIF was stripped** | **Upload fails at photo 3 of 4 on 3G** (EC-13): listing stays `DRAFT` with photos 1–2 attached, fully resumable from `GET /sell`. **5th photo:** refused with the count shown. **Unsupported format:** refused, format list given |
| 9 | Publishes → `POST /sell/{id}/publish` | At pilot (`LISTING_REVIEW_ALL=true`): *"We'll look at this and put it up shortly."* No accusation, no implication of guilt, **the same copy whether or not `suspect_reproduction_flag` is set** (AC-S4.2–3) | `PENDING_REVIEW` | **Version conflict** (edited in two tabs): `409`, rendered as "this listing changed — here it is as it stands now" |
| 10 | Approved | In-app notification: it is up. Link to the live listing | `LIVE`; `published_at` set — **the start of time-to-match** | **Rejected:** the reason, in plain words, in-app. Terminal state `REJECTED`; the seller may create a new listing. The rejection reason is never blank (AC-M1.4) |
| 11 | Later: withdraws | "Take it down" with a confirm | `WITHDRAWN` (terminal) | **An offer is open** (EC-2): withdrawal succeeds, the transfer is `CANCELLED` with `cancelled_by='SELLER'`, and the buyer is told plainly and offered the want form. **Not** a silent disappearance |

**Duplicate listing (EC-6).** If the seller already has a live listing for the
same `book_id`, step 9 shows a warning naming it — and **publishes anyway** if
they continue. Two genuine copies is a real case and blocking it would be wrong.

**Staff side.** J2-staff.

---

## J3 · The cash sale — the spine of the product

**Who.** A buyer who needs a specific edition for a core subject this semester,
and a seller who has it.
**Entry point.** `GET /search`, from J1 step 7 or from the navigation.
**Problem it serves.** US-B1, US-B3, US-B4, US-H1, US-H2, US-H4, US-H5.
**This journey produces the completion record**, which `PRD.md` §3.2 establishes
is the only asset the surviving business model has.

### Buyer's path

| # | Step | Buyer sees | State after | If it goes wrong |
|---|---|---|---|---|
| 1 | Searches by ISBN, title or **course code** → `GET /search` | Results: title, edition, the seller's own condition words, asking price, `display_name` + campus. **Nothing else about the person** (AC-B4.1) | `search_events` row written | **Zero results:** → J4. The empty state distinguishes *not on your campus yet* / *we have it but it's reserved* / *we don't recognise that ISBN* (AC-B2.2). **Gate closed:** `403 GATE_CLOSED` rendered as the pre-launch page with no listing data |
| 2 | Opens a result → `GET /listing/{id}` | Photos, the seller's condition description, annotation level, damage flags, asking price, campus. Ranking explained at `/legal/ranking` | `search_result_opens` row written — this is what makes search success rate computable | **Reserved while they read:** the page says the book is reserved and offers the want form in the same view |
| 3 | **Edition check** | If `prescribed_texts` lists a different edition for a course on this campus: *"Your course MA8151 lists the 3rd edition. This copy is the 2nd."* Both named. **Does not block, needs no dismissal, suggests nothing** (US-B3) | — | **Nothing to say:** nothing is shown. **No positive "matches your syllabus" marker, ever** (AC-B3.3) — we do not know whether `prescribed_texts` is complete and a tick would be a claim about the syllabus |
| 4 | Offers → `POST /listing/{id}/offer` | One confirm. Optional short message. **No price negotiation field** — the asking price is the price | `transfers.state='OFFERED'`; `offered_at` set | **Blocked by the seller:** `404`, not `403` — a 403 would confirm the listing exists (AC-X4.1). **Own listing:** refused. **Duplicate offer:** `409 DUPLICATE_OFFER`, rendered as the existing transfer |
| 5 | Waits | The transfer in plain words: *"Waiting for the seller."* | `OFFERED` | **Declined:** told, with the seller's reason code in plain words, and offered the want form |
| 6 | Accepted | Notification. *"The book is held for you for 48 hours. Pick a place and time."* | `ACCEPTED`; listing `RESERVED`; `reservation_expires_at` = +48h | **Lost the race** (EC-1): `409 LISTING_ALREADY_RESERVED` → "this book is taken" **and the want form in the same view** |
| 7 | Reads the handover notice | The current `HANDOVER_SAFETY` version: *check the book before you hand over any money*; *meet at [named point] in daylight*. Guidance, **never a warranty**, and no mention of BookHop helping if it goes wrong — we hold no money and cannot | Acknowledgement on the transfer's event log | **Not acknowledged:** `SCHEDULED` is unreachable. The guard is enforced server-side (AC-H2.2) |
| 8 | Proposes point + window → `POST /transfer/{id}/propose` | A staff-curated point list for this campus, with `daylight_only` and opening hours shown. A window, ≤14 days out. **No free-text location field anywhere** (AC-H2.1) | still `ACCEPTED` | **Window in the past / >14 days:** field error. **Point inactive or another campus:** not offered |
| 9 | Seller agrees | *"Friday 3–4pm, Main Library gate."* Added to the transfer, with a reminder scheduled | `SCHEDULED` | **Reservation expires first** (EC-3): `422 RESERVATION_EXPIRED` → "the reservation ran out, the book is back up, here's the link to offer again." **Both parties notified at expiry** (AC-H1.3) |
| 10 | Meets, inspects, pays the seller directly | Nothing in the app asks about money, ever. The notice told them to check the book first | — | **They want to reschedule** → J5. **The other party doesn't show** → J5 |
| 11 | Confirms → `POST /transfer/{id}/confirm` | **One question: did the book change hands?** One tap from the notification, one from the transfer list. No intermediate screen. No amount field, no price field, no optional note (AC-H4.1) | `buyer_confirmed_at` set → `AWAITING_CONFIRMATION` or `COMPLETED` | **Only one side confirms:** stays `AWAITING_CONFIRMATION`. **One side alone is never a completion** (AC-H4.2) |
| 12 | Completed | *"Done. This tells us the book actually moved — it's the only way we know BookHop works."* **No reward, no credit, no badge** (EX-19) | `COMPLETED`; `completed_at` set; any `OPEN` request by this buyer for this book closes (**⛔ CG-3**) | — |
| 13 | 72h follow-up, if nobody confirmed | **Asked separately, never in the shared thread:** *"Did you end up getting [title]?"* Yes / No. Three attempts (+0h, +24h, +48h), then silence | `transfer_followups`; `leakage_class` classified at +72h | **No reply after 3:** `UNKNOWN_NO_REPLY`, no fourth attempt. **No follow-up question mentions money, a fee, a price or a platform, in any locale** (AC-H5.3) |

### Seller's path, same transaction

| # | Step | Seller sees | State after | If it goes wrong |
|---|---|---|---|---|
| 1 | Offer arrives | Notification `OFFER_RECEIVED`: the book, the buyer's `display_name` + campus, their message | `OFFERED` | — |
| 2 | Accepts → `POST /transfer/{id}/accept` | *"Held for the buyer for 48 hours."* | `ACCEPTED`; listing `RESERVED` | **Double tap on 3G:** accepted once, both taps see the same answer (`Idempotency-Key`, AC-H1.2). **Concurrent accept elsewhere:** `409` |
| 3 | Declines | A short reason code list. No free-text required | `DECLINED` (terminal); listing stays `LIVE` | — |
| 4 | Reads the handover notice, agrees the window | Same screens as the buyer | `SCHEDULED` | — |
| 5 | Meets, hands over, takes payment directly | — | — | — |
| 6 | Confirms | Same single question | `seller_confirmed_at` → `COMPLETED` | — |
| 7 | 72h follow-up, if unconfirmed | *"Do you still have [title]?"* Yes / No, asked separately | `transfer_followups` | — |

**What staff see across J3.** Nothing, if it works — and the per-transfer
support median exists to prove that. Staff appear only via J2-staff (the listing
review at step 9 of J2), J5-staff, J6-staff or J9-staff. **A J3 that touches
staff is a J3 that costs money**, and `support_work_log`'s `COORD` bucket is
where that shows up.

**Leakage classification at step 13** (`TEST-1` §4.1, in the app):
`IN_APP_CONFIRMED` · `ONE_SIDED_CONFIRMED` · `SILENT_CONFIRMED` (moved, fully
unreported) · `SOLD_ELSEWHERE` · `NOT_MOVED` · `SILENT_PARTIAL` ·
`UNKNOWN_NO_REPLY` · `UNKNOWN_TRUNCATED`. Reported as a **band with K and U
printed beside it, never a point**; above 20 points wide, the export states this
was not measured. There is no midpoint.

---

## J4 · The book that is not there

**Who.** A buyer at semester start, on a campus whose sellers release at
semester end. **In an antiphase market this is the modal journey, not the edge
case** (R-04, T4).
**Entry point.** A search with zero results, or `GET /wanted`.
**Problem it serves.** US-B2. **This journey has no ending in the frozen
contract** and that is CG-3 + CG-4.

| # | Step | Student sees | State after | If it goes wrong |
|---|---|---|---|---|
| 1 | Search returns nothing | **The three truths, kept apart** (AC-B2.2): *we don't have this on your campus yet* · *we have it, it's reserved right now* · *we don't recognise that ISBN*. Each with its own next action. **Never a bare "no results"** | `search_events` with `result_count=0` | **Right book, wrong campus** (EC-9): shown as *not on your campus yet*, which is true. Never as *no results*, which teaches the student the book does not exist |
| 2 | Records the want → `POST /wanted` | Form pre-filled from the query — ISBN and course code carried through — in ≤2 interactions. **No promise of a time, a probability, or that the book will arrive** (AC-B2.5) | `book_requests.status='OPEN'` | **Unknown ISBN** (EC-17): `free_text_title` carries it. This is one of the few places the product tells staff something about the syllabus we did not know |
| 3 | **Intended:** a matching listing is published and the student is told within 15 minutes | Notification `WANT_MATCHED` with a link to the listing | — | **⛔ BLOCKED (CG-4).** There is no `WANT_MATCHED` kind and no scan job. **Current behaviour: the student is never told anything.** The complete designed journey for a student whose book is absent is "state a want, hear nothing", and in antiphase that is most students |
| 4 | Offers on the matched listing | → J3 step 4 | `OFFERED` | — |
| 5 | **Intended:** the transfer completes and the want closes | The want disappears from "wanted", marked fulfilled | `status='FULFILLED'`; `fulfilled_by_transfer_id` set | **⛔ BLOCKED (CG-3).** Nothing writes that column. The **request-side match rate — one of three decisive metrics — returns zero permanently while the rows to compute it sit in the database** |
| 6 | Closes the want manually | "I don't need this any more" | `WITHDRAWN` | — |
| 7 | Want ages out | Expired after the term, with a notification | `EXPIRED` | — |

**What staff see.** The open-wants list, which is **the most informative screen
in the product for R-01**: a want with no supply is the measurement that says
the campus is illiquid. Staff use it for two decisions — which department's
reading list to seed next (J10-staff), and which prescribed titles are missing
from `books` entirely. Staff never contact a requester off-platform about it;
if they act, it is a `MATCH` bucket entry on a ticket (J9-staff).

**Why this journey is first in priority after the spine.** On a cold campus the
honest answer to most searches is "not yet". A dead end here teaches the student
once that BookHop does not work, and they are right, once. Fixing CG-3 and CG-4
is the highest-value product change in `PRD.md` §9.

---

## J5 · The handover that fails

**Who.** Either party, at a `SCHEDULED` handover that does not happen as agreed.
**Entry point.** The transfer screen, or the handover reminder notification.
**Problem it serves.** US-H3, US-M4. **The reschedule path does not exist in the
frozen contract** (CG-1), and this journey is where the support minutes that
decide the company get generated.

### J5a · "Can we make it tomorrow instead" — the common case

| # | Step | Student sees | State after | If it goes wrong |
|---|---|---|---|---|
| 1 | Opens the transfer before the window | The agreed point and window, and **"change the time"** | `SCHEDULED` | — |
| 2 | **Intended:** proposes a new point or window → `POST /transfer/{id}/reschedule` | *"Asked to change it. Waiting for them."* | back to `ACCEPTED`, then `SCHEDULED` on agreement. `transfer_events` records `reason_code='RESCHEDULE_REQUESTED'` | **⛔ BLOCKED (CG-1).** `SCHEDULED` exits only to `AWAITING_CONFIRMATION`, `NO_SHOW` (terminal) or `CANCELLED` (terminal). **Current behaviour: the only way to change a time is to cancel, which destroys a match both parties still want, relists a book that is not available, counts against T1b's 25% bar, corrupts time-to-match, and pushes the coordination into chat — where it becomes the `COORD` support minutes D-009's reversal trigger reads.** The measurement would be of our own omission |
| 3 | Second reschedule | Allowed | `SCHEDULED` | — |
| 4 | Third attempt | *"You've changed this twice. Go ahead with it or cancel."* | `SCHEDULED` | Cap of 2 (AC-H3.2) — unbounded rescheduling is how one party holds a book hostage indefinitely |
| 5 | Metric treatment | — | — | **A reschedule is never counted as a cancellation** in any query (AC-H3.3) |

### J5b · One party does not appear

| # | Step | Student sees | State after | If it goes wrong |
|---|---|---|---|---|
| 1 | Waits at the point | The transfer screen. **"They didn't show" is not available until 15 minutes after the window start** — the schema's own definition | `SCHEDULED` | Before 15 min, the only action offered is "change the time" (J5a, ⛔ CG-1) |
| 2 | Reports no-show → `POST /transfer/{id}/no-show` | A confirm that says plainly what happens: the book goes back up, and **nothing happens to the other person** | `NO_SHOW` (terminal); listing relisted to `LIVE` | **Both parties are notified, and there is no automatic penalty** (schema guard). An automatic penalty on a 15-minute rule would punish a late bus |
| 3 | The no-show party's view | *"[Name] says the handover didn't happen. The book is back up."* No accusation, no strike, no score | `NO_SHOW` | **They dispute it:** the dispute route (J6) is open to either party within 7 days of `handover_window_end` |
| 4 | Buyer's next step | The listing is live again and they can offer again, or record a want (J4) | — | — |

### J5c · They have gone quiet

| # | Step | Student sees | State after | If it goes wrong |
|---|---|---|---|---|
| 1 | No reply in the thread for days | **"Ask BookHop to reach them"** — not "request contact details" (AC-M4.1) | `ACCEPTED` or `SCHEDULED` | — |
| 2 | Relay | BookHop reopens the thread and notifies the counterparty. **No disclosure, no staff decision, no `contact_disclosures` row, no two-person rule engaged** | — | **Still no reply after two notifications over 72 hours:** the field-disclosure request becomes available (step 3) |
| 3 | Disclosure request | The student writes a justification | `contact_disclosures` row, pending | → J5-staff. Often **refused**, and the refusal always says what was done instead (AC-M4.5) |
| 4 | Nothing resolves | Timers finish it: reservation expiry → `EXPIRED` and relist, or window close → 72h follow-up → `EXPIRED` with a `leakage_class` | terminal | **A party deleted their account** (EC-4): the counterparty sees *"this student has deleted their account"* and may cancel; otherwise the timers resolve it. Erasure does not cancel a transfer and nothing in the state machine lets SYSTEM do so |

**What staff see across J5.** A relay request is a **zero-touch** event by
design — the whole point is that it needs no human. A disclosure request lands
in the queue (J5-staff). If a student instead opens a help ticket (J9), it is
pre-bound to the transfer and timed in the `COORD` bucket.

**The honest reading of this journey.** J5a is the most common failure and it is
currently unrepresentable. Every occurrence of it becomes either a destroyed
match or a chat conversation that costs staff minutes. **CG-1 is the cheapest
change in `PRD.md` §9 and it protects the most expensive number.**

---

## J6 · The disputed condition

**Who.** A buyer who got the book, paid, walked away, and then found the water
damage — or the wrong edition.
**Entry point.** The completed transfer screen, within 7 days of
`handover_window_end` or `completed_at`.
**Problem it serves.** US-M3, and US-S3's and US-B3's accountability.
**The governing constraint: BookHop holds no money and cannot refund.** A
dispute flow that looks like a refund flow creates an expectation we cannot
meet, and an unmet promise of protection is itself a form of vouching (R-16).

| # | Step | Student sees | State after | If it goes wrong |
|---|---|---|---|---|
| 1 | Opens the transfer | "Something's wrong with this book" | `COMPLETED` or `AWAITING_CONFIRMATION` | **Outside 7 days:** the action is gone, and the screen says the window has passed and points at the grievance channel, which has no such limit |
| 2 | **Expectation screen — before any form** | *"Filing this puts it on record and we'll look at the listing and the seller. We can't refund you or make the seller take the book back — we never hold the money."* No forbidden word (AC-M3.1) | — | **This screen is the single most important copy in the product.** Without it the dispute flow is a refund promise we cannot keep, and the Tamil phrasing is a **blocking** task for `design-director` because a literal translation turns it into a promise |
| 3 | Picks a category | `CONDITION` · `AUTHENTICITY` · `EDITION_MISMATCH` · `NON_DELIVERY` · `OTHER` | — | — |
| 4 | Describes it | Free text. Photos are **not** collected here — `listing_photos` already holds what the seller claimed, and that comparison is the evidence | — | — |
| 5 | Files → `POST /transfer/{id}/dispute` | Ticket number on screen. Acknowledgement inside 24 hours **as a job, not a human remembering**. Disposal inside 7 days | `DISPUTED`; `disputes` row; `sla_due_at = opened_at + 7 days` (**product decision filling a hole**, AC-M3.3) | **Already disputed:** shown the existing dispute |
| 6 | Seller's view | *"[Name] has raised a problem with this book. A person at BookHop will look at it."* The buyer's words are shown. The seller can respond once | `DISPUTED` | The seller is **not** asked to refund, return or compensate anywhere in the copy |
| 7 | Resolved | The outcome and the reason, in plain words, in-app: book returned / kept / no fault / unresolved | `COMPLETED`, `CANCELLED`, or `CLOSED_UNRESOLVED` | **Staff cannot resolve it:** `CLOSED_UNRESOLVED` is a real, named, honest outcome. Better than a fabricated verdict |
| 8 | Consequence to the listing | — | A confirmed misdescription produces a `moderation_actions` row | **This is how US-S3 is held accountable:** the condition field makes no platform claim, and the dispute rate is the number that tells us whether seller-stated descriptions are good enough |

**Staff side.** J6-staff.

**What is deliberately absent.** No refund field, no return label, no "BookHop
decides", no compensation, no seller rating consequence (EX-1), no automatic
suspension. A dispute is **a record with a stopwatch**, and saying so up front
costs one screen and prevents the one belief that would make us a vouching
platform.

---

## J7 · Reporting a listing

**Who.** Any signed-in student; or a rights holder, a parent or a college who is
not a user at all.
**Entry point.** "Report this" on a listing, a profile, a message or a transfer;
or the public `POST /grievance` and `POST /legal/copyright-notice` forms.
**Problem it serves.** US-X3, US-X4. Reports are our only early signal on R-05
and R-26 — and R-26 says copyright exposure **rose** when general reading was
cut, because v1 concentrated onto exactly the titles whose photocopies
circulate.

| # | Step | Reporter sees | State after | If it goes wrong |
|---|---|---|---|---|
| 1 | Taps "report this" | One routing question, because the three doors have different legal clocks and a misfiled item costs staff minutes: *a book that changed hands* → dispute (J6) · *someone's behaviour or a listing that shouldn't be here* → report · *anything else* → help (J9) | — | — |
| 2 | Picks a category | `COUNTERFEIT_OR_PIRATED` · `MISDESCRIBED` · `PROHIBITED_ITEM` · `HARASSMENT` · `NCII_OR_IMPERSONATION` · `SAFETY_INCIDENT` · `OTHER` | — | — |
| 3 | Describes it, submits → `POST /report` | **A ticket number on screen**, and the clocks in plain words for that category: acknowledged within 24 hours; acted on within 2 hours (NCII/impersonation) / 36 hours (copyright and everything else); disposed within 7 days | `reports` row; `acknowledge_due_at`, `act_due_at`, `disposal_due_at` **computed at insert from the category** | **Rate limited** (10/day **per reporter, never per target** — a low limit on a target is itself an abuse vector): told, with `Retry-After`. **The listing is still live immediately after filing** (AC-X3.3) — filing never auto-removes |
| 4 | Acknowledgement | Notification `REPORT_ACKNOWLEDGED` inside 24 hours, **sent by a job** | `acknowledged_at` | — |
| 5 | Follows it | `GET /reports` — their own reports with current status | — | The reporter is **never** told the counterparty's identity or what action was taken against a person, only that the report was disposed of |
| 6 | Blocks the person as well | `POST /block` | `blocks` row | **Mutual invisibility** in search, listings, threads and offers; a guard on `→ OFFERED`. The blocked user gets `404`, not `403` — a 403 would confirm the listing exists (AC-X4.1) |

### J7-public · A rights holder or a parent, with no account

| # | Step | They see | State after |
|---|---|---|---|
| 1 | Finds the grievance officer | `/legal/grievance` — name, email, and the process, published under E-Com r.4(2) and IT Rules r.3(2)(a) | — |
| 2 | Files a grievance → `POST /grievance`, **unauthenticated** | Ticket number; acknowledgement inside 24 hours; disposal inside 7 days | `grievances` row |
| 3 | Or files a copyright notice → `POST /legal/copyright-notice`, **unauthenticated** | A form capturing r.75's requirements: the work, the infringing location, their authority, and the **undertaking to sue within 21 days** | `legal_notices` kind `COPYRIGHT_R75`; `act_due_at` = +36h; `hold_expires_at` = `acted_at` + 21 days |
| 4 | Gets a copy of their complaint | From 1 Jan 2027, E-Com r.4(5) requires giving the complainant a copy of the complaint as recorded. **Built now** | `copy_provided_at` |

**Staff side.** J7-staff — the queue, the clocks and the repeat-infringer
record.

---

## J8 · Account deletion

**Who.** A student who got their book, finished the semester, or simply wants
out.
**Entry point.** `GET /account` → "delete my account".
**Problem it serves.** US-X1, US-X2. Deletion is cheapest to build before there
is data to delete, which is why it is in S1 and not S8.

| # | Step | Student sees | State after | If it goes wrong |
|---|---|---|---|---|
| 1 | Opens account settings | Profile, privacy (per-purpose toggles), **export my data**, **nominee** (one field, not promoted — EX-17's sibling reasoning), delete | — | — |
| 2 | Exports → `GET /account/export` | A JSON summary of their personal data and processing activities, generated live, **with no staff step** | — | — |
| 3 | Taps delete — step 1 of 2 | **The truth, before the point of no return** (AC-X1.2): what is deleted now; that the record of completed transfers is kept **without their name** for one year, and why; and **that chat content is not deleted and is purged one year after the last message** | — | **This is the disclosure `COMPLIANCE.md` §7 row 11 requires, and the student must learn it here, not from a support ticket** |
| 4 | Confirms — step 2 of 2 → `POST /account/delete` | "Your account is gone." Signed out | **One transaction:** `user_tombstones` inserted (pseudonym, campus, city, salted `email_hash`, `purge_due_at` = +1 year); email, display name and password NULLed; `status='TOMBSTONED'`; tokens, push subscriptions, sessions, `age_check_pending`, notification preferences and `campus_verifications` deleted; listings, requests, transfers, threads, messages, reports and disputes keep their **pseudonym** and lose their FK | **Rate limited** at 3/day |
| 5 | What survives, deliberately | — | `repeat_infringer_records` (r.5(5), **never purged, retention job explicitly skips it**), `audit_log`, `personal_data_access_log`, `age_verification_events`, `consents` — the record that the deletion itself was lawful | — |
| 6 | A transfer was mid-flight | — | **Not cancelled** (EC-4). The counterparty sees *"this student has deleted their account"* and may cancel; otherwise the timers resolve it | — |
| 7 | They come back later | A new account, a new pseudonym | **Repeat transfer @90d undercounts them** and the export says so. We could link via the tombstone's `email_hash`, but that hash exists for ban evasion and dispute linkage only — using it for analytics would be purpose creep. **We accept the undercount** | — |

**The assertion that matters most.** After deletion, the §9.2 repeat-transfer
query **still returns their transfers under their pseudonym** (AC-X1.3). That is
the test that proves erasure and measurement coexist, and it is the single QA
assertion I would keep if I could keep only one.

**Staff side.** J8-staff.

---

## J9 · Getting help inside the product

**Who.** Anyone, at any point, confused or stuck.
**Entry point.** "Get help with this" on every transfer, listing and account
screen.
**Problem it serves.** US-H6. **⛔ This journey has no student entry point in
the frozen contract (CG-2)** and it is the one whose absence breaks D-009's
measurement mitigation, not just the experience.

| # | Step | Student sees | State after | If it goes wrong |
|---|---|---|---|---|
| 1 | Taps "get help with this" on a transfer | The routing question (J7 step 1), then — for "anything else" — the help form | — | **⛔ BLOCKED (CG-2).** No endpoint and no L1 function lets a student open a ticket. **Current behaviour: the student has nowhere on-platform to say "the seller hasn't replied in three days"** — it is not a report, not a grievance and not a dispute. They ask in the batch WhatsApp group and do not come back, and `METRICS.md` and `DATA-MODEL.md` §11.3 both state that off-platform support makes the support number unmeasurable |
| 2 | Reads what we can and cannot do, **before typing** | *"We can help you reach the other student, put a book back up, or look at a listing. We can't refund you — we never hold the money."* (AC-H6.5) | — | Saying this up front is cheaper than saying it in a reply, and it is the one unmanaged expectation that turns into the belief that BookHop vouches for the trade |
| 3 | Sees an answer first | The five commonest questions, as static copy — not a CMS. Each ends with "this didn't answer it", which carries a reason code into the ticket | — | **We are not measuring deflection.** No table holds article views and I am not inventing one. What we do measure is mis-routing, via the reason code |
| 4 | **Intended:** opens a ticket | Pre-bound to this `transfer_id` or `listing_id` | `support_tickets` with `channel='IN_APP'`, `transfer_id` set | **A generic help page alone is not acceptable:** unbound tickets land in `DAILY_UNALLOCATED` and are **excluded from the per-transfer median that decides the business**. Contextual entry is a measurement requirement, not a convenience (AC-H6.1) |
| 5 | Gets a reply | **In the same place**, with the history. The student is never told to check their email for the answer (AC-H6.2) | `support_messages` | **Tamil ticket, English-reading staff** (EC-19): answered in the student's locale or not at all. An operating commitment nobody has made yet — flagged to `marketplace-ops` |
| 6 | What is never offered | **No phone number and no WhatsApp number, anywhere** in the product, the emails, the notices or any listing of the service (AC-H6.4) | — | The statutory grievance email is published because it must be (r.4(2)), and **every message arriving there is opened as a ticket with `channel='EMAIL'` and timed like any other** — so those minutes are measured too. Only unlogged WhatsApp is invisible, and that is why none is published |
| 7 | Response expectation | *"We read every message. We aim to reply the same day — we're a small team."* **No SLA number for help.** Statutory clocks apply to reports, grievances and disputes, and those are stated exactly | — | Promising a time one staff member cannot keep is how a help surface becomes a complaint surface |

**Staff side.** J9-staff.

---

## J2-staff · The listing review queue

**Who.** One staff member, with `LISTING_REVIEW_ALL=true`, reviewing **every**
listing at pilot scale. `TASKS.md` §6.4 is right that this cost lands directly
on R-13 and D-009's reversal trigger and must be measured, not assumed.
**Entry point.** Django admin → listings pending review.

| # | Step | Staff sees and does | Writes | Where it strains |
|---|---|---|---|---|
| 1 | Opens the queue | Pending listings ordered by **time remaining on the shortest applicable clock, ascending** — not arrival order (AC-M1.1). Rows inside 25% of their window are distinct **without relying on colour alone** | — | Listing review has no statutory clock; it inherits a service target. Reports and legal notices in the same working session do, and US-M2's single clock screen is what stops the untimed work crowding out the timed work |
| 2 | Opens a listing | Photos, the ISBN and the resolved `books` row, condition and damage claims, `suspect_reproduction_flag`, whether the `books` row is staff-verified. **A server timer starts and the elapsed time is visible while they work** (AC-M1.3) | `support_work_log` bucket `INTAKE`, `source='SERVER_TIMER'` | A timer the staff member cannot see is a timer they forget. Visibility is the whole control |
| 3 | Judges the photos | Spiral binding, a visible photocopy gutter, a scanned page, a "for sale in South Asia only" marking being misrepresented — the R-26 signals | — | This is a judgement with no training set and one reviewer. It will be wrong sometimes, in both directions, and the dispute rate (J6) is the feedback loop |
| 4 | Passes it | `REVIEW_PASS`, with a `legal_basis` and a **non-empty reason** (AC-M1.4) | `moderation_actions` with `work_seconds`; `audit_log`; listing → `LIVE`, `published_at` set | **There is no bulk-approve** (AC-M1.5). One listing, one decision, one logged reason. At pilot volume that is affordable and the audit trail is the point |
| 5 | Rejects it | A reason in plain words that the seller will read | `moderation_actions`; listing → `REJECTED` (terminal) | The reason is shown verbatim to the seller, so it has to be written for them, not for the log |
| 6 | Resolves a duplicate book | `merge_books` sets `merged_into_id` | **No row is deleted** — listings point at it, and a listing on a merged book still loads (EC-7) | — |
| 7 | Verifies a student-created `books` row | `staff_verified_at` | — | A student creating a prescribed title we do not have is a **catalogue signal**, and it belongs on the same screen as the open-wants list (J4) |
| 8 | Saves | Timer stops | `support_work_log` row with `seconds >= 6`; **anything under six seconds records as 0.1 minutes, never 0** | — |

**The honest cost.** Every listing reviewed by one human is the largest single
`INTAKE` cost in the product, and turning `LISTING_REVIEW_ALL` off is a one-line
config change **once the data says so**. It should not be turned off because the
queue feels long.

---

## J5-staff · Reaching the other student — relay, then disclosure

**Who.** One staff member, handling a `contact_disclosures` row.
**Entry point.** Django admin → pending disclosures. **The relay path never
arrives here, by design** (AC-M4.1) — if it does, the design has failed.

| # | Step | Staff sees and does | Writes | Where it strains |
|---|---|---|---|---|
| 1 | Relay happens without them | The thread reopens and the counterparty is notified. **No row, no queue, no decision** | — | This is the whole design: the common case is zero-touch, so the two-person rule never has to be satisfied for it |
| 2 | A disclosure request arrives | Only after the relay failed — no reply to two notifications over 72 hours. The requester's justification in their own words. **Opening it writes `personal_data_access_log`, and the screen says so to the staff member** (AC-M5.6) | `personal_data_access_log` | Visibility that the access is logged is most of the control (`THREAT-MODEL.md` §5.8) |
| 3 | Considers what could even be disclosed | **An email, and nothing else.** No address exists in the database to disclose, and `fields_disclosed` may never contain one (AC-M4.4) | — | The r.5(3)(a) proviso is about reaching a seller after a purchase. The relay has already done that. The disclosure adds nothing except a personal-data disclosure about a student who did not consent |
| 4 | Tries to approve | `CHECK (approved_by_id IS NULL OR approved_by_id <> requested_by_id)` plus the service guard. The **second person is a named human in `legal_entities`** — the grievance officer or the nodal contact, who exists because the law requires them to (AC-M4.3) | `contact_disclosures.approved_by_id` | **If the only staff member is that same person, the disclosure cannot be approved — and that is the correct outcome** (EC-15). The relay has already done the useful thing, and one operator unilaterally handing one student another student's email is exactly the insider action the rule exists to stop. **The queue blocking is the rule working, not a bug** |
| 5 | Refuses | `outcome='REFUSED'` with a note | `contact_disclosures`; `audit_log` | **The refusal always tells the student what was done instead** (AC-M4.5). A refusal that is a silence is worse than no feature |
| 6 | Logs the time | `AFTER` bucket on a ticket | `support_work_log` | — |

**The product answer to the CTO's flag, stated once.** The two-person rule does
not need weakening, and it does not need a second staff member hired to satisfy
it. It needs the common case to stop arriving at it. **The relay is that
change**, it needs no contract amendment, and it leaves the rule intact for the
only case that should ever reach it.

---

## J6-staff · Resolving a dispute with no money in it

**Who.** One staff member, inside a 7-day disposal clock.
**Entry point.** Django admin → open disputes, surfaced on US-M2's clock screen.

| # | Step | Staff sees and does | Writes | Where it strains |
|---|---|---|---|---|
| 1 | Acknowledges inside 24h | Done by a **job**, not by remembering | `disputes`; notification | — |
| 2 | Opens the dispute | The buyer's words, the seller's response, the listing as it was — **`listing_photos` and the seller's own condition claims, which is the whole evidence base**. Opening it writes `personal_data_access_log` and the screen says so | `personal_data_access_log` | There is no third party, no inspection, no courier record. Two accounts and some photos is all there will ever be, and the resolution vocabulary is honest about that |
| 3 | Reads the thread if needed | Logged access, stated on screen | `personal_data_access_log` | — |
| 4 | Decides | `RESOLVED_BOOK_RETURNED` · `RESOLVED_KEPT` · `RESOLVED_NO_FAULT` · `UNRESOLVED`, with notes. **No refund field exists and no screen offers one** (AC-M3.2) | `disputes.resolution`; transfer → `COMPLETED` / `CANCELLED` / `CLOSED_UNRESOLVED`; `transfer_events`; `audit_log` | `CLOSED_UNRESOLVED` is a named, honest outcome and staff must be willing to use it. A fabricated verdict is worse than an admitted stalemate |
| 5 | Acts on the listing | A confirmed misdescription produces a `moderation_actions` row against the listing or the seller | `moderation_actions` | This is US-S3's feedback loop: the condition field makes no platform claim, so the dispute rate is the only evidence that seller-stated descriptions are good enough |
| 6 | Tells the student | The outcome and the reason, in plain words, in-app | notification `DISPUTE_UPDATE` | — |
| 7 | Logs the time | `AFTER` bucket | `support_work_log` | Disputes are the most expensive minutes in the product per event, and the cheapest thing that reduces them is J6 step 2's expectation screen plus US-S3's honest condition copy |

**Clock.** Acknowledged inside 24 hours, disposed inside 7 days — matching the
statutory grievance channel, because a tighter promise is one a single operator
cannot keep and a looser one is worse than the channel the student could have
used instead (AC-M3.3).

---

## J7-staff · Moderation, the takedown clocks, and the repeat-infringer record

**Who.** One staff member, against four different statutory clocks. **A missed
clock is the loss of safe harbour, and it should be escalated to the founder
like a safety incident.**
**Entry point.** Django admin → the single clock screen (US-M2).

| # | Step | Staff sees and does | Writes | Where it strains |
|---|---|---|---|---|
| 1 | Opens the clock screen | **Every** open `reports`, `legal_notices`, `grievances` and `disputes` item, with its own due time and the statutory basis named. Nothing that has a clock is absent from it (AC-M2.1). All times rendered `Asia/Kolkata`, stored UTC | — | Four clocks cannot be held in a person's head. This screen is the mitigation and it is the only one |
| 2 | Reads the clocks | Computed from the category **at insert** — the SLA is data, not a convention: NCII/impersonation act +2h · court order or government notification act +3h · copyright act +36h · everything else act +36h, dispose +7d · acknowledge +24h on all (AC-M2.2) | — | — |
| 3 | Acts on a report | `HIDE` / `REMOVE` / `RESTORE` / `SUSPEND_USER` / `REINSTATE_USER` / `ESCALATE`, each with a `legal_basis` and a reason. Timer visible | `moderation_actions` with `work_seconds`; `audit_log`; `reports.acted_at` | Removing content under the Rules, including by automated tools, does not itself forfeit safe harbour (r.2(1B)) — so acting is not the risk; **not acting in time is** |
| 4 | Handles a copyright notice | Checks the work is identified, the complainant's authority, and **the undertaking to sue within 21 days**. Removes within 36h | `legal_notices.acted_at`; `hold_expires_at = acted_at + 21 days`; content preserved 180 days (r.3(1)(j)) | A rights-holder claim arriving without an undertaking is recorded and not acted on as an r.75 notice. The form captures it so this is not a judgement call |
| 5 | The 21-day hold expires | **Access is restored automatically** unless a court order arrived, recording `restored_at` and the **named deciding human** (AC-M2.3) | `legal_notices.restored_at`, `restore_decision_by_id` | Automatic restoration with a logged decision is `COMPLIANCE.md` §5.3 item 4 exactly. Nobody has to remember day 21 |
| 6 | Writes the repeat-infringer record | On every statute-based removal, keyed to the **pseudonym**, minimum content | `repeat_infringer_records` — **never user-deletable, no `purge_due_at`, retention job explicitly skips it and a test asserts that it does** (AC-M2.5) | This is the one record that survives everything, and it is mandatory under E-Com r.5(5) |
| 7 | Handles an unauthenticated grievance | Acknowledged inside 24h by a job; disposed inside 7 days; from 1 Jan 2027 the complainant gets a **copy of the complaint as recorded** | `grievances`; `copy_provided_at` | The grievance channel is the only route for a non-user, and it is the one place the published email is unavoidable (J9 step 6) |
| 8 | Quarterly rules reminder | Nothing — it is a **scheduled job**, not a manual task (IT Rules r.3(1)(c)) | `notifications` kind `QUARTERLY_RULES_REMINDER` | — |
| 9 | Never exports in bulk | **There is no bulk export screen.** Data extraction is a management command run on the box, logged by the shell and the audit chain | `audit_log` | Insider risk. The absence of the screen is the control |

---

## J8-staff · Age revocation, erasure, and data-subject requests

| # | Step | Staff sees and does | Writes | Where it strains |
|---|---|---|---|---|
| 1 | A minor is discovered (EC-12) | Suspend, erase, log. `age_verification_events` with `outcome='REVOKED_MINOR_DISCOVERED'`, `method='STAFF_REVIEW'`, reviewer recorded. **The note must contain no date of birth** — a code-review item | `age_verification_events`; `user_tombstones` reason `MINOR_DISCOVERED` | Adult verification is a server-checked **declaration** (R-28). This path exists because we cannot prevent the case, only handle it |
| 2 | POCSO duty surfaces | A `safety_incidents` row with `minor_involved = true` is raised, and the admin UI shows the mandatory-reporting duty **as a required next step**, not as a note | `safety_incidents`; `notify.founder_escalation` | A legal duty rendered as a note is a legal duty that gets missed |
| 3 | A data-subject request arrives | Access / correction / erasure / nomination, `due_at = received_at + 7 days` — **not 90.** 90 is DPDP's ceiling; the tightest applicable clock governs | `data_subject_requests` | Access and erasure are self-serve (J8 steps 2 and 4), so this queue should be near-empty. If it is not, the self-serve path is failing and that is the finding |
| 4 | Completes it | Outcome recorded; `audit_log` row written | `data_subject_requests.completed_at`; `audit_log` | — |
| 5 | Nightly purge runs | `retention.purge` walks every table with a `purge_due_at` and writes a `purge_log` row per row acted on | `purge_log` — **the proof the expiry job ran**, for G3/G4 | Skip-list: `repeat_infringer_records`, and anything held by `preserved_until` (180 days) or an open `safety_incidents` / `disputes` / `legal_notices` |
| 6 | Audit chain verified | `verify_audit_chain` | — | The chain assumes one appender. **Printing the daily chain head in the daily digest costs nothing and removes that assumption** — a cheap S8 item worth doing |

---

## J9-staff · The support stopwatch

**Who.** One staff member. **This journey produces the single number D-009's
reversal trigger reads**, and a number that is easy to not record will not be
recorded.
**Entry point.** Django admin → open tickets.

| # | Step | Staff sees and does | Writes | Where it strains |
|---|---|---|---|---|
| 1 | Opens a ticket | **The timer starts automatically** and the elapsed time is visible. `source='SERVER_TIMER'` | `support_work_log` | A timer that must be started by hand is the failure mode. Automatic start is the design |
| 2 | Picks a bucket | Exactly `TEST-1` §3.2's names — `INTAKE` · `MATCH` · `COORD` · `HANDOVER` · `AFTER` · `CHASE` · `UNALLOCATED` — **so the app's numbers are directly comparable to the thresholds set for the concierge design** (AC-M5.2) | `support_work_log.bucket` | Changing a bucket name breaks comparability with the pre-registered thresholds. These names are frozen for that reason, not out of sentiment |
| 3 | Switches records | Stops one timer, starts another. One record at a time | two rows | The stopwatch rule, verbatim: *start when you begin doing something to one specific record; stop when you stop; if you switch records, stop and start again* |
| 4 | Runs a batch match | One `batch_run_id` with its `batch_match_count`; the per-transfer attribution divides equally and **the divisor is stored, so the arithmetic is reproducible by anyone who doubts it** (AC-M5.4) | `support_work_log.batch_run_id`, `batch_match_count` | A batch run producing no match goes to `DAILY_UNALLOCATED` — real cost, not attributable to a transfer |
| 5 | Logs off-platform minutes | `MANUAL_ENTRY`, against a ticket, with a note. **Reported separately**, because a hand-entered number is weaker evidence | `support_work_log.source='MANUAL_ENTRY'` | **The operating discipline the schema depends on** (`DATA-MODEL.md` §11.3): no support phone number and no WhatsApp is published, and any off-platform minute is entered here. Without it R-13 stays unmeasured and D-009's mitigation fails quietly. Owned by `marketplace-ops` |
| 6 | Closes the ticket | **Refused if no `support_work_log` row exists** (AC-H6.6) | `support_tickets.closed_at` | This guard is what stops the decisive number being silently zero |
| 7 | Daily unallocated | One `kind='DAILY_UNALLOCATED'` ticket per day for work that is real but not attributable — posters, standing at a table, the daily close | `support_tickets` | **Reported separately and never folded into the per-transfer number.** In a product nobody is standing at the canteen; including it would measure the scaffolding |
| 8 | Weekly export | Support minutes per completed transfer, **twice**: including chase minutes (**the pre-registered pass number**) and excluding them, labelled *"instrument cost removed, not the pass number"*. Plus the three reference lines — 4.00 min = Rs 11.36, 2.11 = Rs 6.00, 1.06 = Rs 3.00 — and the sentence *"passing the 4-minute bar means not catastrophic, not viable."* Plus the per-bucket breakdown, so a bad number can be acted on rather than argued about | — | **If the two figures straddle the threshold it is a fail, not a debate** (AC-M5.5). D-009's reversal trigger fires above 4.00 minutes at n ≥ 30 |

---

## J10-staff · Opening a campus

**Who.** A named human, not an agent. **No agent writes a `gate_authorisations`
row.**
**Entry point.** `manage.py open_discovery --campus <slug>` on the box.

| # | Step | What happens | Writes | Gate |
|---|---|---|---|---|
| 1 | Before anything | `campuses.discovery_enabled_at` is **NULL = closed**. A real student sees the pre-launch page with **no listing data on it**; seed users see seed listings (AC-M6.1) | — | A browsable listing surface makes BookHop an e-commerce entity under r.4(1)(a) |
| 2 | Supply is seeded | One department's reading list into `prescribed_texts`, plus seed listings with `is_seed=true`. **This is R-01's test** | `prescribed_texts`, `listings` | — |
| 3 | The evidence checklist | `counsel_engagement_ref`, `takedown_sop_ref`, `oncall_rota_ref`, `breach_rehearsal_at`, `campus_mou_ref`, `notice_version_ids` | `gate_authorisations.evidence` | Gate B: CoI, INC-20A, grievance officer, takedown SOPs, counsel C1–C3 |
| 4 | The command runs | **Refuses on a campus with no `legal_entity_id` and no CoI** (AC-M6.2) | `gate_authorisations` with `authorised_by_human` — a person's name | s10A bars commencing business before INC-20A is filed |
| 5 | Open | `discovery_enabled_at` set. Real students can search, list and offer | — | — |
| 6 | Seed separation holds | `CHECK (seller_is_seed = buyer_is_seed)` — seed and real never mix. Every metric view filters `is_seed = false` **and prints the excluded seed count**, so contamination is visible rather than silent (AC-M6.3) | — | — |
| 7 | Closing it again | `close_discovery` sets `revoked_at` and `revoked_reason` on the authorisation. Append-only: no UPDATE except those two columns | `gate_authorisations` | — |

---

## J11-staff · A safety incident

**Who.** One staff member, and then the founder. **Target is zero, and any
incident is a founder escalation** (`METRICS.md`).
**Entry point.** A `SAFETY_INCIDENT` report (J7), a walk-up, or a dispute that
turns out to be something else.

| # | Step | Staff sees and does | Writes | Where it strains |
|---|---|---|---|---|
| 1 | Records it | `safety_incidents` in a **separately permissioned** table: campus, severity, description, `minor_involved`, the transfer if there is one | `safety_incidents`; **`notify.founder_escalation` enqueued automatically** | Escalation is a job, not a judgement call about whether to bother the founder |
| 2 | Acts on the accounts | Suspend, block, remove listings — each with a `legal_basis` and a reason | `moderation_actions`; `audit_log` | — |
| 3 | If a minor is involved | The POCSO mandatory-reporting duty appears **as a required next step** in the UI | `pocso_reported_at` | — |
| 4 | Police referral | `police_referred_at`, if it happens | `safety_incidents` | BookHop has no address, no phone number and no precise location for anyone. **What we can provide is a pseudonymous transaction record, a named public handover point and a time** — and that is deliberately all |
| 5 | What copy never says | **Nowhere** in the product does it say BookHop makes a handover safe, or that BookHop will help if something happens offline | — | s79 safe harbour covers third-party information, **not offline harm** (R-06). The more we vouch, the more we own |
| 6 | Retention | 1 year **with identifiers**, in the separately permissioned table | — | An open incident blocks the purge job for the rows it holds |

---

## J-DEFERRED · Direct swap — kept warm, not built

**Status.** Cut from v1 by D-007. **Representable in the schema and absent from
the UI:** `listings.intent='SWAP'`, `swap_wants (listing_id, book_id)`, and
`feature_flags['listings.swap_ui'] = false`. Rows are writable by staff and
fixtures, and `TASKS.md` S2 requires them **tested with seed data** so they are
known to work when swap returns.

**Why it was cut, so nobody reinstates it by enthusiasm.** Supply and demand
peak in **antiphase** — sellers release at semester end, buyers need books at
semester start — and a direct swap requires two mutually matching needs **at the
same moment**. It also generates zero cash, which matters less now that the
student side is free, and matters more for liquidity: a swap consumes two wants
and produces two listings that both leave the market.

**What reinstating it would need — the whole list, so it is not archaeology.**

1. **A decision**, recorded in `DECISIONS.md`, reversing D-007 item 3 on
   evidence that swap-only users are the cheapest supply we can acquire.
2. **Flip one flag:** `listings.swap_ui = true`. No migration.
3. **Journey J2 gains one step** after the condition step: *"what would you want
   in exchange?"* → one or more `swap_wants` rows against the listing. The
   asking price becomes optional, and that is the one schema question to settle
   first: `asking_price_paise` is NOT NULL, so a pure swap listing must store
   `0`, and **a `0` must never render as "free"** — it renders as "swap only".
   That is a copy requirement, and it is the trap.
4. **Journey J3 gains a matching step** between search and offer: a swap is a
   **two-sided match**, so the offer carries which of the seller's wants the
   buyer can satisfy, and both sides reserve. The current partial unique index
   is per `listing_id`; a swap reserves **two** listings, and that is the one
   real contract question — it needs either two linked transfers or one transfer
   with a second listing reference. **Do not design it now.** Record that it is
   the question.
5. **Journey J6 gets harder:** a disputed swap has two books and no money, and
   `disputes` has one `transfer_id`. Resolution vocabulary would need a look.
6. **No metric changes.** Completion, leakage and repeat transfer all already
   key off `transfers`, and a swap is a transfer.

**What does not need revisiting.** No money is involved, so ADR-003, P14 and the
whole fee question stay exactly where they are. Swap is the one deferred feature
that is **free of the monetisation argument entirely**, which is why it is worth
keeping warm.

---

## Appendix A · What a student is never shown, in any journey

A single checklist, because these recur in every journey and a reviewer should
be able to check them in one pass.

| Never shown | Why | Where asserted |
|---|---|---|
| A phone number, an email, an address, precise coordinates | None is collected; the relay replaces disclosure | AC-B4.1, AC-M4.4 |
| A settled price, a "sold for", a price history, a struck-through price, a was/now, a discount | P14 (s194-O, threshold nil) and r.4(13) | AC-S2.2 |
| A suggested price or a price range | Price-setting on our own marketplace, and it needs a settled-price history | EX-3 |
| A rating, a review, a reputation score, a trust score | R-16, O-11, and no statistical content at pilot n | EX-1, EX-20 |
| A condition grade, badge, star, letter or colour-coded quality marker | R-16; the field is the seller's description, not our grade | AC-S3.1, EX-2 |
| A positive "matches your syllabus" marker | We do not know whether `prescribed_texts` is complete | AC-B3.3 |
| The words *safe, verified, protected, guaranteed, assured, trusted, certified, authentic* | Safe harbour does not cover offline harm | `test_forbidden_copy.py` |
| A promise that BookHop will help if something goes wrong offline | We hold no money and cannot | AC-H2.3, AC-H6.5 |
| A raw state name (`AWAITING_CONFIRMATION`) | Plain words, EN and TA | AC-H1.4 |
| An amount field on any transfer screen or endpoint | ADR-003 §2.4, P14 | AC-H4.1, EX-18 |
| A phone or WhatsApp support number | Makes support minutes unmeasurable and voids D-009's mitigation | AC-H6.4, EX-7 |
| A listing in a search engine | r.3(1)(b); `Disallow: /` + `X-Robots-Tag: noindex` | AC-B4.3 |
| A listing from another campus | `visibility_scope='CAMPUS'`; the empty state says *not on your campus yet* | EC-9 |
| Any listing at all, before the campus gate opens | Gate B, r.4(1)(a) | AC-M6.1 |

## Appendix B · The four blocked steps, in one place

For `cto` triage. Full scoping in `PRD.md` §9.

| Blocked step | Journey | Contract gap | Severity | Recommended slice |
|---|---|---|---|---|
| Reschedule a `SCHEDULED` handover | J5a step 2 | **CG-1** — no `SCHEDULED → ACCEPTED` transition | **Blocking.** Every occurrence becomes a destroyed match or `COORD` support minutes, and support minutes are the number D-009 reads | S5, before the handover flow ships |
| A student opens a support ticket | J9 step 1, step 4 | **CG-2** — every support L1 function takes `staff`; no endpoint; nowhere to store what the student wrote | **Blocking.** D-009's measurement mitigation runs through in-app support and the contract leaves no on-platform door | S5, one slice ahead of the support tables |
| A want closes when the book arrives | J4 step 5 | **CG-3** — nothing writes `fulfilled_by_transfer_id` | Material. The request-side match rate reports zero permanently | S5, inside `confirm_handover` |
| A student hears that their want was matched | J4 step 3 | **CG-4** — no `WANT_MATCHED` kind, no scan job | Material, and the highest-value fix for the student. Without it J4 has no ending, and J4 is the modal journey on a cold campus | S3 if possible, S5 at the latest |

---

## Amendment log

| Date | Change | Approved by |
|---|---|---|
| 2026-10-21 | v1.0 — first journeys. Written after contracts were frozen (§0). Four blocked steps recorded in Appendix B | product-manager |
