# PRD — BookHop v1

**Owner:** `product-manager` · **Version:** v1.0 · **Date:** 2026-10-21 · Phase C
**Handoff:** `design-director`, `cto`, `test-qa`, `red-team`
**Reads with:** `README.md` §1 · `decisions/DECISIONS.md` D-006…D-009 ·
`product/DISCOVERY.md` v0.2 · `evidence/RED-TEAM/G1-MEMO.md` ·
`architecture/DATA-MODEL.md` v1.0 (FROZEN) · `architecture/API-CONTRACT.md` v1.0
(FROZEN) · `architecture/TASKS.md` · `ops/TEST-1-CONCIERGE-PILOT.md` §3–§4 ·
`metrics/METRICS.md` · `risks/RISK-REGISTER.md`

**Companion:** `product/JOURNEYS.md` — every journey named here is specified
there, step by step, including the staff side.

---

## 0. SEQUENCING NOTE — read this before anything else

**This PRD was written after the contracts were frozen.** `DATA-MODEL.md` v1.0
and `API-CONTRACT.md` v1.0 were frozen on 2026-10-21; backend slice S0 is being
implemented while this document is written; the design system does not exist
yet. G2's entry criteria (*PRD + design system + ADRs + contracts frozen*,
`README.md` §6) were therefore **not met when the build started**. The CTO
flagged this in `TASKS.md` §6.1 and was right to. This section records what the
inversion cost, because the cost is real and will show up later as rework by
somebody who was not told why.

**What it cost, specifically:**

1. **The transaction state machine was designed without a journey.** It is a
   good state machine, and it is missing one transition that a real handover
   needs: **there is no way to reschedule a `SCHEDULED` handover** (CG-1). The
   only exits are no-show (terminal) or cancel (terminal). Students reschedule
   constantly. Had the journeys existed first, this would have been one row in a
   table instead of an amendment to a frozen contract.
2. **In-app support was specified as a measurement surface, not a product
   surface.** Every function in `API-CONTRACT.md` §3 `apps/support/services.py`
   takes `staff` as its first argument. `support_tickets.channel` offers
   `'IN_APP'` and **no endpoint anywhere lets a student open a ticket** (CG-2).
   D-009's entire measurement mitigation runs through in-app support, and the
   contract as frozen has no student-facing door into it. This is the single
   most consequential gap and it exists because nobody wrote the journey where a
   student is confused.
3. **The demand side dead-ends.** `book_requests` exists, `fulfilled_by_transfer_id`
   exists, and **nothing writes it** (CG-3); there is no `WANT_MATCHED`
   notification (CG-4). A student can state a want and, by contract, never hear
   anything again. In an antiphase market (T4) that is the *most common* journey
   on a cold campus, and it currently has no ending.
4. **Product decisions were made by the CTO under protest, correctly.**
   `TASKS.md` §6.1 says that where a product decision was needed and absent, the
   CTO chose "the smallest thing that satisfies a cited rule". That is the right
   fallback and it produced a compliance-shaped product with no opinion about
   the student. The opinion is in §3 and §4 of this document, arriving late.
5. **Frontend is building against provisional design tokens** it owns and will
   swap (`TASKS.md` §3). That is a cheap, well-handled consequence. It is also
   the only one of the five that was anticipated.

**What it did not cost.** The schema is not wrong. Having read all of it, I am
accepting it almost entirely: it is more careful about erasure, the legal
clocks, and the measurement surface than a schema written from my journeys
would have been. Five disagreements are listed in §9, four of them small. The
sequencing was wrong; the work was not.

**What I am not doing.** I am not retrofitting the PRD to the contracts and
calling the gap closed. Where the right product needs a contract change, §9
says so, scopes it, and escalates it. Where the contract is right and my
instinct was wrong, §9 says that too.

---

## 1. Persona — a hypothesis, and still zero students interviewed

Carried from `DISCOVERY.md` §1.1 **unchanged and unupgraded**. Repeating the
banner from that document because a persona that migrates into a PRD tends to
acquire the authority of a finding on the way:

> **ZERO interviews conducted. ZERO surveys fielded. ZERO students spoken to.**
> Every statement about what a student wants, feels, pays or does in this
> document is a **HYPOTHESIS**. The interviews and the survey in `DISCOVERY.md`
> §4–§5 are written, pre-registered, funded (Rs 4,500 of the Rs 16,500 approved
> at D-007), unrun, and blocked on three named campus contacts. D-009 opened the
> build; it did not produce any evidence.

**Primary persona (HYPOTHESIS) — "the second-year who already paid once."**
2nd or 3rd-year undergraduate, Anna-University-affiliated engineering or an
arts & science course, not medicine. Both a buyer and a seller in the same term,
which no other cohort is. Mid-range Android 2–4 years old with storage near
full, a daily-cap prepaid data pack, reads technical content in English and
negotiates in Tamil. Pays for books from an allowance or by asking a parent — the
single most load-bearing unknown in the persona and tagged a pure guess in
`DISCOVERY.md`. Will meet a stranger from their own campus in a public campus
spot in daylight, and will not go off-campus. Pays by UPI, phone to phone, at
the handover.

**The persona is not claiming felt pain.** `DISCOVERY.md` §2 argues the opposite
case deliberately and I am carrying that forward: an unused book costs its owner
nothing per day, so the seller has no urgency, and the buyer's alternatives are
cheaper and faster than us.

**Counter-persona (HYPOTHESIS) — "Vignesh", and he matters more.**
3rd-year CSE, WhatsApp-native, PDF-sufficient. Batch Drive with three years of
PDFs; for the two subjects that need paper he photocopies four chapters at the
gate for under Rs 100. Has never paid for a textbook with his own money. **Every
design decision in this PRD assumes Vignesh is a large share of the campus**,
because if he is the modal student our addressable demand is a residue. The
product's job is not to convert him. It is to be found quickly by the minority
for whom the whole book, for the whole semester, is the actual requirement.

**Second counter-persona:** the student with a well-stocked department library
or a reliable senior-handover tradition. Marginal cost zero and social. We have
nothing to add and should not pretend otherwise.

---

## 2. Problem statement

### 2.1 The problem, stated so it can be attacked

> A Chennai undergraduate who needs a **specific edition** of a **prescribed**
> textbook, for a **whole semester**, often cannot get a physical copy quickly
> or affordably — and a student who has finished with that same book has no
> low-effort way to turn it into money. The books exist, on the same campus,
> within walking distance, and the two students cannot find each other.

### 2.2 What we are competing against, and where we lose

From `DISCOVERY.md` §2.2–§2.3, ranked. **A product plan without an explicit
answer to #1 and #2 is not finished**, so the answers are stated here.

| # | Alternative | Cost | Where it beats us | Our answer |
|---|---|---|---|---|
| 1 | Partial photocopy at the gate | Rs 60–200 | Price, speed, legality, sized to the actual need | **We do not beat it and will not try.** We win only where the need is the whole book for the whole semester — a core subject carried across terms, lab or drawing work, or reading that is unbearable on a phone. Everything in §4 is scoped to that subset. |
| 2 | Free PDF in the batch group | Rs 0 | Price, speed, social frictionlessness | **Only on the reading experience, and only for people who actually read long-form.** We never argue against the PDF in copy. The listing surface simply has to be faster than asking a group and waiting. |
| 3 | Campus WhatsApp resale | Rs 0 | Already installed, already populated, people you can place socially | **Exact-edition search, a structured handover at a named point, and no phone number exposure.** That is the whole claim, and R-07 records that we have not established how those groups actually work. |
| 4 | Seniors' hand-me-downs | Rs 0 | Free, trusted, comes with the previous owner's notes | **No answer, by design.** We serve the student who does not have that senior. If that group is small, so are we. |
| 5 | Department library / book bank | Rs 0 | Institutional and free | Availability at peak — which is also when our supply is scarcest. Also, per D-007 item 4, the hypothesised payer. |
| 6 | Buying new | Rs 349–689 | Certainty of edition and condition | Price. Our clearest win and the smallest segment. |

### 2.3 The one thing only we can do

Nothing in the list above knows **which edition your course prescribes**. The
photocopy shop does not care, the Drive has whatever someone uploaded three
years ago, and the WhatsApp group answers with a title and no ISBN. BookHop is
the only one of the seven that can hold `prescribed_texts` for a campus and tell
a buyer *"your course lists the 3rd edition and this copy is the 2nd"*.

That is the product. It is one screen (US-B3), it fits the frozen schema
exactly, and it is the only feature in this PRD with no competitor.

---

## 3. The thesis, sharpened so the app itself can falsify it

### 3.1 Statement

> BookHop is a **syllabus-to-shelf matching layer for edition-locked prescribed
> textbooks on one campus**. We believe that for the subset of books a student
> needs **whole, for a whole semester**, they will accept a slower,
> higher-priced, stranger-mediated acquisition than the photocopy shop or the
> batch Drive — because for that subset neither alternative delivers the object
> required. The **student side is free, permanently and by design**: no fee, no
> escrow, no custody, no credits. The hypothesised payer is the **institution**,
> and what the institution would be buying is not matches but a **record of
> provision** it can put against a budget line.

**Status:** the monetisation thesis is FALSIFIED (D-006 condition 1, on O-10).
The product thesis stands, **unvalidated**. The institutional payer is a
hypothesis with an unrun Rs 0 test attached (D-007 item 4) and **zero sources**
behind it (O-12, `DISCOVERY.md` §8.1 item 6). It is not a direction and this PRD
does not build toward it.

### 3.2 Why "the record" is the load-bearing phrase

D-008 Ruling 2 re-scoped O-10 from a revenue risk to an **evidence** risk, and
that is the sentence that decides what v1 must do. With no fee, a pair who meet
through BookHop and settle in silence cost us no money. They cost us the only
asset the surviving business model has. So:

- **Every feature that produces a completion record outranks every feature that
  produces a pleasant experience.** US-H4 (dual confirmation) and US-H5 (the
  72-hour follow-up) are therefore first-class product features, not telemetry.
- **The record must be obtainable without ever asking about money** (P14,
  `TEST-1` §4.1). The confirm question is about a physical object: *did the book
  change hands?* There is no amount field anywhere in v1 and no screen asks for
  one.

### 3.3 What the app must observe for this thesis to be falsifiable

Thresholds already pre-registered elsewhere are **reused, not reinvented** —
inventing a parallel set would let us pick whichever one passes.

| Observable | Threshold | Where it comes from | Computable by |
|---|---|---|---|
| Listing rate — account creators who list within 14 days | **≥ 60%** | T1a, `DISCOVERY.md` §3.1, **locked** | S2 + S1 rows |
| Seller cancellation of accepted offers | **≤ 25%** | T1b, **locked** | `transfer_events` (S4) |
| In-app completion within 72h of a match | **≥ 60%** | Product's T3 amendment, `DISCOVERY.md` §3.1 | §9.5 leakage band (S5) |
| Median support minutes per completed transfer | **≤ 4.00** at n ≥ 30 | D-009 reversal trigger; `TEST-1` §3.4 | §9.4 (S6) |
| Search success rate, after ≥1 department's list is seeded and ≥50 real searches | **≥ 25%** → below this, R-01 is confirmed | **Mine, and weak.** Derived from the 1-in-3 matchability guess that sets T2a's bar — a `[G]` resting on a `[G]`. A **review trigger, not a kill**, and labelled as such in the export | §9.1 (S3) |
| Repeat transfer @90d | **No threshold pre-registered, deliberately** | See below | §9.2 (S7) |

**Why I am not setting a repeat-transfer threshold.** R-24 makes repeat transfer
at 90 days the real observable for O-10, and no prior exists for it anywhere in
the evidence base. A number invented now, by the agent whose thesis it tests,
before any cohort has existed, would be a number invented to be passed. The
requirement is that the metric be **computed and reported with its n from the
first 90-day cohort** (`DATA-MODEL.md` §9.2 already guarantees it survives
account deletion). The threshold gets set once, by `ceo-planning`, on the first
real reading — and then it is locked.

**One sentence that must appear in the weekly export**, carried from R-25 and
`TEST-1` §3.4: *passing the 4-minute support bar means "not catastrophic", not
"viable".* The model needs 2.11 minutes. `DATA-MODEL.md` §9.4 already requires
this line; it is repeated here so Product is on record as owning it too.

---

## 4. User stories and acceptance criteria

**The rule I am applying, from my charter.** Every story states a user problem
and carries at least one acceptance criterion that is **behavioural, observable
from outside, and checkable by `test-qa` without reading the implementation**.
A story without both is rejected, and the rejections are in §5.2 — that list is
the most useful part of this document.

**Vocabulary constraint on every story below.** The words **safe, verified,
protected, guaranteed, assured, trusted, certified, authentic** are forbidden
strings in all product copy, EN and TA (`API-CONTRACT.md` §5.4,
`COMPLIANCE.md` §5.5, `INCORPORATION-AND-BLOCKERS.md` §4.1). Safe harbour does
not cover offline harm (R-06) and the more we vouch the more we own (R-16).
Approved substitutes, which `design-director` owns and must use consistently:
"college email confirmed", "18 or over confirmed", "the seller's own
description", "check the book before you pay", "meet at a public point in
daylight". `tests/unit/test_forbidden_copy.py` greps every template and `.po`
file; **a story is not done if that test is red.**

### 4.1 First run — getting an actor who is allowed to exist

#### US-A1 · Sign in with a college email and nothing else
**Problem.** A student with a 2-year-old Android and a daily data cap will not
install an app, create a password, or hand over a phone number to find out
whether a Rs 200 book exists. Every one of those is a reason to go back to the
group chat.
**Behaviour.** Enter a college email → receive a single-use link → be signed in.
No password (students have none by design, `DATA-MODEL.md` §2), no phone column
in the database, no social login.
**AC-A1.1** Submitting any syntactically valid address returns the same page and
the same 202 status whether or not the address exists or its domain is
recognised. QA asserts byte-identical responses for a known address, an unknown
address at a recognised domain, and a gmail address.
**AC-A1.2** That page names the domains this campus accepts, generically and
without echoing the submitted address — e.g. *"We can only email addresses
ending @example.ac.in. Check you used your college address."* **This is a
product requirement, not polish:** without it the enumeration-proof 202 and the
`EmailDomainNotRecognised` raise in L1 combine into a silent dead end that is
the most likely first-run failure in the product.
**AC-A1.3** The link works once and expires in 10 minutes; a second use shows a
plain "this link has been used — ask for a new one" page with a working button,
never a stack trace or a raw error code.
**AC-A1.4** The whole screen renders and submits with JavaScript disabled.
**Metric:** verified students. **Journey:** J1.

#### US-A2 · Be told I am too young, once, and have nothing kept
**Problem.** First-year Chennai undergraduates are routinely 17 (R-18). A minor
who signs up is not a product problem, it is an architectural one — behavioural
moderation on a minor's account is the thing we cannot do.
**Behaviour.** A date-of-birth field, checked on the server. Under 18 → refused,
account deleted immediately, nothing retained but the audit event.
**AC-A2.1** A declared DOB under 18 returns 403 and, after the request, there is
**no `users` row and no `age_check_pending` row** for that email, and **no DOB
anywhere in the database.** Exactly one `age_verification_events` row exists
with `outcome='REJECTED_UNDER_18'`, and its `note` contains no date.
**AC-A2.2** The client-side block never substitutes for the server one: QA posts
the under-18 DOB directly to the endpoint with the form bypassed and gets the
same result.
**AC-A2.3** The refusal copy does not suggest a workaround, does not invite the
student to come back with a different date, and does not use the word "sorry" as
a lead — it states the rule and stops.
**Honest limitation, stated in the product and not only in a risk file:** this
is a server-checked **declaration**. A 17-year-old who types an adult date is
admitted and we cannot detect it (R-28). If discovered, J8-staff runs
`REVOKED_MINOR_DISCOVERED` → suspend, erase, log, and raise a
`safety_incidents` row with `minor_involved = true`, which surfaces the POCSO
duty. **No copy anywhere implies an age check stronger than a declaration.**
**Metric:** verified students; safety incidents. **Journey:** J1, J8-staff.

#### US-A3 · Agree to things one at a time, and be able to undo it
**Problem.** A single "I agree" checkbox covering six purposes is not consent,
and a withdrawal that requires emailing someone is not a withdrawal.
**AC-A3.1** The consent screen presents the six purpose keys in
`DATA-MODEL.md` §2 individually, **none pre-ticked**, and the form cannot be
submitted with a hidden default of true. QA asserts no `checked` attribute on
any consent input in the rendered HTML, in both locales.
**AC-A3.2** Each purpose has a toggle in privacy settings; turning it off
appends a `consents` row with `withdrawn_at` set and **never updates a row in
place.** QA asserts row count increases and no prior row changed.
**AC-A3.3** The screen names the exact `notice_versions` version the student is
agreeing to, and `/legal/{kind}` serves that version's text in EN and TA.
**Metric:** none directly; this is a legal precondition for every other metric
being lawfully collectable. **Journey:** J1.

### 4.2 Supply — the easier claim, and the whole cold start

#### US-S1 · Put a book up in under three minutes, on a bad phone, on 3G
**Problem.** The seller's book costs them nothing per day to keep. There is no
urgency, so there is no patience. Every extra field is a reason to abandon.
**Behaviour.** Type or scan an ISBN → confirm it is the right edition → describe
condition and damage → set a price → up to 4 photos → publish.
**AC-S1.1** From a signed-in start, a listing reaches `LIVE` (or
`PENDING_REVIEW`) in **≤ 8 interactions** and **≤ 3 screens** of required input.
QA counts them on the rendered flow.
**AC-S1.2** p75 LCP on the sell flow's first screen, on a throttled mid-range
Android profile over simulated 3G, meets the budget in `METRICS.md`. A flow that
is fast for me and slow for the persona has not met this story.
**AC-S1.3** An abandoned listing stays `DRAFT` and is resumable from
`GET /sell` with every entered field and every uploaded photo intact. QA kills
the connection after photo 2 of 4 and resumes.
**AC-S1.4** Every screen works as a plain HTML form POST with JavaScript off,
including ISBN lookup (which degrades from typeahead to a submit button).
**Metric:** valid listings; supply density; listing rate (T1a ≥60%).
**Journey:** J2.

#### US-S2 · Set my own price, once, and not be told what it should be
**Problem.** The only price in the system is between the two students. If the
platform suggests one, the platform is setting prices on a marketplace it also
runs, and it needs a settled-price history to do it — which P14 forbids outright
(s194-O, threshold nil).
**AC-S2.1** `asking_price_paise` is set at intake and **cannot be changed** by
any route: UI, L2, L3, or admin. QA attempts all four and asserts the trigger
rejects. (The guard test exists already as `test_price_immutable`.)
**AC-S2.2** No screen, email, notification or export contains: a suggested
price, a price range, a "similar books sold for", a struck-through price, a
"was/now", a discount percentage, or a settled price. QA greps the rendered
response schema, not only the database.
**AC-S2.3** Changing the price requires withdrawing and relisting, and the UI
says so plainly at the point the seller looks for an edit button.
**Metric:** book value moved (asking prices only — never cash GMV, which is not
computable in v1 and never will be). **Journey:** J2.

#### US-S3 · Describe the book's condition without the platform vouching for it
**Problem.** R-16 and O-11 together: a condition grade the platform appears to
endorse moves us toward product-seller liability, and a grade it disclaims is a
form with a dropdown that a WhatsApp group already provides. So the field must
do the smallest honest job — tell the buyer what to expect — and must not look
like a quality rating.
**Answer to `DATA-MODEL.md` §11.4, which routed this to me.** Keep the four
values. They are **descriptions, not grades.**
**AC-S3.1** `condition` is labelled as the seller's own words throughout —
listing form, listing detail, search results, notifications. The string
"BookHop" never appears adjacent to a condition value. No badge, no chip, no
colour-coded quality indicator, no star, no letter grade, no numeric score, no
"best condition first" sort option.
**AC-S3.2** `damage_flags` must be **affirmatively confirmed**, including an
explicit "none of these" the seller ticks. An untouched damage list that submits
as empty is an implied claim of no damage that the seller never made, which is
exactly the misdescription we would have authored.
**AC-S3.3** `annotation_level` is presented as neutral fact (pencil,
highlighting, heavy notes), never as a defect and never as a feature. Previous
owners' notes are the one thing a senior's hand-me-down has that we cannot
replicate; we are not going to call them damage.
**AC-S3.4** `tests/unit/test_forbidden_copy.py` is green across every condition
string in EN and TA.
**Metric:** dispute rate (condition disputes ÷ completed transfers) — this
story's accountability is that the number stays low *without* the platform
making a claim. **Journey:** J2, J6.

#### US-S4 · Not be able to list a photocopy, and be told why
**Problem.** R-26: cutting general reading **raised** copyright exposure by
concentrating v1 on exactly the titles whose photocopies and pirated reprints
circulate. Prevention at intake is far cheaper than a 36-hour takedown with a
21-day hold and a repeat-infringer record.
**AC-S4.1** The seller undertaking at listing time states, in plain EN and TA,
that photocopies, scans, spiral-bound reproductions and copies marked for
another territory may not be listed. It is a tick the seller makes, recorded as
`seller_terms_acceptances` against a `notice_versions` row.
**AC-S4.2** A listing whose photos or text trip `suspect_reproduction_flag`
goes to `PENDING_REVIEW` and **the seller is told it is being looked at before
it appears**, with no accusation in the copy and no implication of guilt.
**AC-S4.3** At pilot scale `LISTING_REVIEW_ALL=true`, so every listing is
reviewed. The seller-facing wait copy is the same in both cases, so turning the
config off later changes no strings.
**AC-S4.4** An ISBN is required. A listing with no ISBN needs staff approval and
cannot self-publish.
**Metric:** counterfeit/misdescription confirmed rate; reports per 1,000
listings; `INTAKE` support minutes (which is where the review cost lands, and
`TASKS.md` §6.4 is right that it must be measured rather than assumed).
**Journey:** J2, J7, J7-staff.

### 4.3 Demand — the claim most likely to kill us

#### US-B1 · Find the exact edition my course prescribes
**Problem.** Every alternative in §2.2 answers with a title. None answers with
an ISBN. The student's actual requirement is an edition, and getting the wrong
one wastes the money and the week.
**Behaviour.** Search by ISBN, by title, or **by course code** — the third is
the one that matches how a student actually knows what they need.
**AC-B1.1** An exact ISBN match ranks above every trigram title match, always.
QA seeds a near-title collision and asserts ordering.
**AC-B1.2** A course-code search returns the listings whose `book_id` appears in
`prescribed_texts` for that `(campus_id, course_code)` — i.e. the syllabus
lookup works without the student knowing any ISBN.
**AC-B1.3** Ranking is `published_at DESC` within an exact-ISBN match, then
trigram similarity, with **no personalisation and no promoted placement**, and
is documented in descending order of significance at `/legal/ranking`. QA
asserts the page exists, is reachable unauthenticated, and matches the
implemented order.
**AC-B1.4** p95 search latency meets `METRICS.md`; every search writes a
`search_events` row and every result click writes a `search_result_opens` row,
**in the slice that creates the behaviour** — a search surface that does not
write both rows is not done, because search success rate becomes measurable for
the first time here (R-27) and a retrofit is how D-009 fails quietly.
**Metric:** search success rate; match rate (search limb); time to match.
**Journey:** J3.

#### US-B2 · State what I need when it is not there, and actually hear back
**Problem.** **This is the modal journey on a cold campus and in an antiphase
market** (R-01, R-04, T4): sellers release at semester end, buyers need books at
semester start, and the honest answer to most early searches is "not yet". An
empty result with a dead end teaches the student that BookHop does not work, and
they are right, once.
**Behaviour.** The empty state offers one action: record the want. When supply
arrives, the student is told.
**AC-B2.1** A search with zero results offers the want form pre-filled with the
query — ISBN and course code carried through — in ≤ 2 interactions.
**AC-B2.2** The empty state **distinguishes three different truths** and never
collapses them into "no results": *we do not have this book on your campus
yet*; *we have it but it is reserved*; *we do not recognise this ISBN at all*.
These are different problems with different next actions and the student can
only act on the right one.
**AC-B2.3** When a listing is published that matches an `OPEN` `book_request`
for the same `book_id` and campus, the requester receives a notification within
15 minutes. **This requires CG-4** and the story is **blocked** until that
amendment lands. Without it, `book_requests` is a suggestion box.
**AC-B2.4** When a transfer completes, any `OPEN` request by that buyer for that
book closes with `fulfilled_by_transfer_id` set. **This requires CG-3**; without
it the request-side match rate — one of the three decisive metrics in
`METRICS.md` — returns zero forever while rows exist to compute it from.
**AC-B2.5** The want form never promises a time, a probability, or that the book
will arrive.
**Metric:** match rate (**request limb** — the one that exposes illiquidity,
because an unfulfilled want is a row); request fill rate. **Journey:** J4.

#### US-B3 · Be warned when the edition is not the one my course lists
**Problem.** The highest-value thirty seconds in the product. A buyer about to
pay Rs 200 for the 2nd edition when the course prescribes the 3rd has made the
one mistake BookHop exists to prevent, and no competitor can prevent it.
**Behaviour.** On a listing detail page, when `prescribed_texts` holds a
different `book_id` for the same work on this campus, say so — plainly, with
both editions named, and **without blocking the purchase.**
**AC-B3.1** Given a seeded `prescribed_texts` row for ISBN A on a course, a
listing for ISBN B of the same work shows a warning naming both editions and the
course code. QA seeds the pair and asserts the string.
**AC-B3.2** The warning does not block, does not require a dismissal, and does
not tell the student what to do. Sometimes the older edition is the right
purchase and the student knows more about their exam than we do.
**AC-B3.3** The absence of a warning is **never** presented as a positive
signal. No "edition match" tick, no green state, nothing. We have no idea
whether `prescribed_texts` is complete, and a tick would be a claim about the
syllabus we cannot support. Silence when there is nothing to say.
**AC-B3.4** This screen uses no forbidden string. It is the place where
"verified" is most tempting and most dangerous.
**Metric:** dispute rate, `EDITION_MISMATCH` category specifically — this
story's whole accountability is that that category stays near zero.
**Journey:** J3.

#### US-B4 · See a listing without seeing a person
**Problem.** A profile photo, a bio and a phone number are a harassment surface
and a PII surface, and they add nothing to the decision *should I buy this
book*. R-06 is a critical risk and the cheapest mitigation is having nothing to
leak.
**AC-B4.1** A listing response — L2 JSON and L3 HTML — contains exactly
`{display_name, campus_name, pseudonym}` for the seller and nothing else. No
email, no phone, no address, no coordinates, no settled price. QA asserts
against the **response schema**, not the database.
**AC-B4.2** `display_name` is first name plus initial by policy, and the profile
form cannot accept a value containing an `@`, a digit run of 6+, or a URL — the
three ways a student would route around us to put a contact detail in public.
**AC-B4.3** No listing page is indexable: `robots.txt` is `Disallow: /` and
every listing response carries `X-Robots-Tag: noindex`. QA asserts the header.
**Metric:** safety incidents (target zero, any incident is a founder
escalation). **Journey:** J3.

### 4.4 The transaction — offer to record

#### US-H1 · Make an offer and know immediately whether I have the book
**Problem.** Two students offering on the last copy is the normal case at
semester start. Ambiguity here produces two people walking to the library gate
for one book, and that is a support ticket and a lost user.
**AC-H1.1** Concurrent accepts on one listing produce exactly one success; every
other gets 409 `LISTING_ALREADY_RESERVED` and a page that says the book is taken
and offers the want form (US-B2) in the same view. QA fires N concurrent
accepts.
**AC-H1.2** Tapping "accept" twice on a flaky connection accepts once and both
taps see the same answer (`Idempotency-Key`).
**AC-H1.3** A reservation that expires at 48 hours relists the book and tells
**both** parties, in plain words, that it expired and why — not a silent state
change the buyer discovers by reloading.
**AC-H1.4** Every transfer screen states the current state in plain EN and TA,
not as an enum. QA asserts no raw state name (`AWAITING_CONFIRMATION`) is ever
rendered to a student.
**Metric:** match rate; time to match; cancellation rate by actor.
**Journey:** J3.

#### US-H2 · Agree a place and a time without exchanging contact details
**Problem.** R-06 plus the disintermediation evidence risk. The moment a phone
number crosses, the match leaves the platform and the record (§3.2) is gone, and
we also lose any ability to act on a safety report.
**AC-H2.1** Handover points are chosen from a staff-curated list for that
campus. There is no free-text location field anywhere in the product, for either
party, in any state.
**AC-H2.2** A transfer cannot reach `SCHEDULED` until the current
`HANDOVER_SAFETY` notice version has been shown to **both** parties and
acknowledged, recorded on the transfer's event log. QA asserts the guard by
attempting the transition without the acknowledgement.
**AC-H2.3** The safety copy is guidance and never a warranty: *check the book
before you hand over any money*; *meet at [named point] in daylight*. It
contains no forbidden string, and it does not say BookHop will help if something
goes wrong, because BookHop holds no money and cannot.
**AC-H2.4** Messages matching a phone, email or UPI-handle pattern are
**flagged, not blocked** (`DATA-MODEL.md` §8). The sender is not warned, accused
or stopped. Blocking is unenforceable and user-hostile; the flag feeds
harassment review.
**Metric:** no-show rate; completion rate; safety incidents. **Journey:** J3.

#### US-H3 · Change the time when life happens
**Problem.** The most ordinary thing in a campus handover is "can we make it
tomorrow instead". The frozen contract cannot express it: `SCHEDULED` exits only
to no-show (terminal) or cancel (terminal). Both destroy a match that both
parties still want, both relist a book that is not actually available, and both
generate the support minutes that are the one number most likely to sink the
unit economics.
**This story is BLOCKED on CG-1** and I am not designing around it. A
reschedule implemented as cancel-then-re-offer loses the transfer, loses the
`transfer_events` thread, double-counts a cancellation against T1b's 25% bar,
and corrupts time-to-match. That is not a workaround, it is data corruption with
a UI on top.
**AC-H3.1** (post-amendment) Either party may propose a new point or window
while `SCHEDULED` and before `handover_window_end`; the transfer returns to
`ACCEPTED` and re-enters `SCHEDULED` on the other party's agreement. A
`transfer_events` row records it with `reason_code='RESCHEDULE_REQUESTED'`.
**AC-H3.2** At most **2** reschedules per transfer, then the only options are
proceed or cancel. Unbounded rescheduling is a way for one party to hold a book
hostage indefinitely, and the cap is what stops it.
**AC-H3.3** A reschedule is **not** counted as a cancellation in any metric.
QA asserts the cancellation-rate query excludes it.
**Metric:** cancellation rate (must not be inflated by reschedules); no-show
rate (should fall); support minutes, `COORD` bucket (the number this story
exists to reduce). **Journey:** J5.

#### US-H4 · Confirm the book changed hands, and never be asked about money
**Problem.** This is the record (§3.2). It is the only asset the institutional
hypothesis has, and it is also the moment at which the student has the least
reason to do anything — they have the book, they are walking away.
**AC-H4.1** The confirm screen asks exactly one question: *did the book change
hands?* It has no amount field, no price field, no "how much did you pay", and
no optional note that could become one. QA asserts no numeric input exists on
the screen and no endpoint in §5.4 accepts an amount.
**AC-H4.2** **One side alone is never a completion.** `COMPLETED` requires both
`seller_confirmed_at` and `buyer_confirmed_at`. QA asserts a single confirmation
leaves the transfer in `AWAITING_CONFIRMATION`.
**AC-H4.3** The confirm action is reachable in **one tap from the notification**
and one tap from the transfer list, with no intermediate screen. Every
additional tap here is a lost record.
**AC-H4.4** The copy states why we are asking, in one short sentence, without
mentioning institutions, funding or metrics: *"This tells us the book actually
moved. It is the only way we know BookHop works."* No incentive, no credit, no
badge is offered for confirming — US-X7 explains why.
**Metric:** completion rate; leakage band; repeat transfer @90d.
**Journey:** J3.

#### US-H5 · Answer one question about an object, 72 hours later
**Problem.** Pairs settle and go dark. `TEST-1` §4.1's insight is that the one
trace a silent pair leaves which is **not** surveillance is that the book is no
longer where it was — and that is a question about a physical object, cheap to
answer honestly, saying nothing about money.
**AC-H5.1** At 72 hours after a handover window with no confirmation, each party
is asked **separately** — never in a shared thread — one question: the seller
*do you still have [title]?*, the buyer *did you end up getting [title]?*
**AC-H5.2** Three attempts (+0h, +24h, +48h after entering
`AWAITING_CONFIRMATION`), then silence. No fourth. QA asserts the attempt count
caps at 3 and `leakage_class='UNKNOWN_NO_REPLY'` is set.
**AC-H5.3** No follow-up question, in any locale, in any attempt, mentions
money, a fee, a price or a platform.
**AC-H5.4** The leakage figure is reported as a **band with K and U printed
beside it, never as a point**, and when the band exceeds 20 percentage points
the export states that this was not measured. There is no midpoint.
**Metric:** leakage band; completion rate. **Journey:** J3, J5.

#### US-H6 · Get help from inside the product when it goes wrong
**Problem.** Two problems in one. The student's: the seller has not replied for
three days and there is no one to ask, so they ask in the batch WhatsApp group
and never come back. The company's: **if support happens anywhere but in the
app, D-009's entire measurement mitigation fails silently** (`METRICS.md`;
`DATA-MODEL.md` §11.3). Support is therefore a product surface and a measurement
instrument at the same time, and the second is why the first cannot be skipped.
**This story is BLOCKED on CG-2.** There is no student-facing route into
`support_tickets`.
**AC-H6.1** (post-amendment) Every transfer, listing and account screen carries
one "Get help with this" action that opens a ticket **pre-bound** to that
`transfer_id` or `listing_id`. A generic help page alone is not acceptable:
unbound tickets land in `DAILY_UNALLOCATED` and are excluded from the
per-transfer median that decides the business. **Contextual entry is a
measurement requirement, not a convenience.**
**AC-H6.2** A ticket opened by a student is visible to that student with its
history, and a staff reply appears in the same place. The student is never asked
to check their email for the answer.
**AC-H6.3** The help entry asks one routing question, because the three doors
have different legal clocks and a misfiled item costs staff minutes to re-route:
*about a book that changed hands* → dispute (J6), *about someone's behaviour or
a listing that should not be here* → report (J7), *anything else* → support
ticket.
**AC-H6.4** **No phone number and no WhatsApp number appears anywhere** in the
product, the emails, the notices or the store listing. The statutory grievance
email (r.4(2)) is published because it must be, and every message arriving there
is opened as a ticket with `channel='EMAIL'` and timed like any other, so those
minutes are measured too.
**AC-H6.5** The help surface states what we can and cannot do before the student
types: we can help you reach the other student, re-list a book, or look at a
listing; **we cannot refund you, because we never hold the money.** Saying this
up front is cheaper than saying it in a reply, and it is the one expectation
that, left unmanaged, turns into the belief that BookHop vouches for the trade.
**AC-H6.6** A ticket cannot be closed with zero logged seconds. QA asserts
`close_ticket` fails on a ticket with no `support_work_log` row. **This is the
guard that stops the decisive number being silently zero.**
**Metric:** support load (minutes per completed transfer) — the D-009 reversal
trigger. **Journey:** J9, J9-staff.

### 4.5 Exit, and the things a student is owed

#### US-X1 · Delete my account and be told the truth about what remains
**Problem.** Deletion that quietly keeps everything is a lie, and deletion that
destroys the transaction record would break the legal retention floor and the
counterparty's dispute. The student is owed the actual answer, at the moment
they ask, not in a support ticket afterwards.
**AC-X1.1** Two-step confirmation, then `erase_account` runs as one transaction.
**AC-X1.2** Before the second step, the screen states plainly, in EN and TA:
what is deleted now; that the record of transfers already completed is kept
without their name for one year, and why (statutory retention); and **that chat
content is not deleted and is purged one year after the last message.** That
last one is the disclosure `COMPLIANCE.md` §7 row 11 requires, and the student
must learn it here, not from a support ticket.
**AC-X1.3** After deletion: the transfer record survives, is pseudonymous,
cannot be relinked to the deleted identity by any query available to a staff
account, and the §9.2 repeat-transfer query still returns their transfers under
their pseudonym. **That last assertion is the test that proves erasure and
measurement coexist** — the central claim of the data model, and the one QA
assertion I would keep if I could keep only one.
**AC-X1.4** A repeat-infringer record survives deletion and is never purged.
**Metric:** none. This is a right, not a feature, and it is not measured by
adoption.
**Journey:** J8.

#### US-X2 · Get a copy of my data, and name someone to act for me
**Problem.** Both are in the Act, both are cheap, and nobody builds the second.
**AC-X2.1** `GET /account/export` returns a JSON summary of personal data and
processing activities for the signed-in student, generated live, with no staff
step.
**AC-X2.2** Nomination (s14) exists as one field in privacy settings and is
**not** promoted as a feature, because a student who came to find a textbook
does not need a nominee flow in their way.
**Metric:** data-subject requests completed within 7 days (not 90 — the
tightest applicable clock governs). **Journey:** J8.

#### US-X3 · Report a listing or a person and get a ticket number
**Problem.** A report with no acknowledgement is indistinguishable from a void,
so people stop reporting — and reports are our only early signal on R-05 and
R-26.
**AC-X3.1** Every report returns a ticket number on screen and triggers an
acknowledgement within 24 hours **as a job, not a human remembering.**
**AC-X3.2** The response states the acknowledgement and disposal clocks in plain
words, with the right clock for the category (2h for NCII/impersonation, 36h for
copyright, 36h act and 7d disposal otherwise).
**AC-X3.3** Filing a report **never** auto-removes the target. QA asserts the
listing is still live immediately after a report.
**AC-X3.4** The copyright-notice and grievance forms are reachable
**unauthenticated**, because a rights holder, a parent or a college is not a
user. QA asserts both without a session.
**AC-X3.5** Report rate limits are per **reporter**, never per target. A low
limit on a target is itself an abuse vector.
**Metric:** reports per 1,000 listings; time to moderate; confirmed
counterfeit/misdescription rate. **Journey:** J7.

#### US-X4 · Block someone and stop existing to them
**AC-X4.1** A block is mutual invisibility in search, listings, threads and
offers, and is a guard on `→ OFFERED`. QA asserts the blocked user cannot see
the blocker's listings and cannot offer on them, and that the error is a 404,
not a 403 — a 403 would confirm the listing exists.
**Metric:** safety incidents. **Journey:** J7.

### 4.6 Staff — specified as a product, not as an afterthought

The admin is where the legal clocks are either met or missed, where the support
number is either measured or lost, and where one person has to do all of it. It
gets the same treatment as the consumer side. Journeys J2-staff through
J9-staff carry the detail; the stories are here.

#### US-M1 · Work the moderation queue without losing the clock
**Problem.** At pilot scale `LISTING_REVIEW_ALL=true`, so every listing is
reviewed by one person, and that cost lands directly on R-13 and the D-009
reversal trigger. A queue that does not show its own age is a queue that misses
a 3-hour clock.
**AC-M1.1** The queue is ordered by **time remaining on the shortest applicable
clock**, ascending, not by arrival. An item with 40 minutes left outranks one
that arrived first with 6 days left.
**AC-M1.2** Each row shows the remaining time against its own clock, and rows
inside 25% of their window are visually distinct in a way that does not rely on
colour alone (WCAG 2.2 AA).
**AC-M1.3** Opening an item starts a server timer; the elapsed time is
**visible** to the staff member while they work; saving writes
`moderation_actions` with `work_seconds` and an `audit_log` row.
**AC-M1.4** Every action requires a `legal_basis` and a non-empty `reason`. QA
asserts an action with an empty reason is refused.
**AC-M1.5** There is no bulk-approve. One listing, one decision, one logged
reason. At pilot volume the cost is affordable and the audit trail is the point.
**Metric:** time to moderate; `INTAKE` support minutes; reports per 1,000
listings. **Journey:** J7-staff.

#### US-M2 · See every legal clock running, in one place, as a working surface
**Problem.** Four different clocks (3h court order / government notification, 2h
NCII, 36h copyright with a 21-day hold, 7d grievance disposal, 24h
acknowledgement on everything) cannot be held in a person's head, and a missed
one is the loss of safe harbour.
**AC-M2.1** One screen lists every open `reports`, `legal_notices`,
`grievances` and `disputes` item with its own due time and the statutory basis
named. Nothing that has a clock is absent from it.
**AC-M2.2** The clocks are computed from the category at insert and are **data,
not a convention** — QA asserts the stored `act_due_at` for each category
against the table in `DATA-MODEL.md` §7 without reading any code.
**AC-M2.3** A `COPYRIGHT_R75` takedown sets `hold_expires_at = acted_at + 21
days`; at expiry, access is **restored automatically** unless a court order has
arrived, recording `restored_at` and the **named deciding human**. QA runs the
21-day clock forward on a fixture and asserts both the restoration and the named
decider.
**AC-M2.4** A removal under the Rules preserves the content 180 days for
investigation and the retention job does not purge it.
**AC-M2.5** A repeat-infringer record is written on every statute-based removal,
keyed to the pseudonym, and the retention job explicitly skips that table. QA
asserts the row survives both account deletion and a purge run.
**AC-M2.6** All times are rendered in `Asia/Kolkata` and stored UTC. Every SLA
depends on this and there are no naive datetimes.
**Metric:** time to moderate; zero missed statutory clocks (a missed clock is a
founder escalation, like a safety incident). **Journey:** J7-staff.

#### US-M3 · Resolve a dispute that has no money in it
**Problem.** BookHop holds no money and cannot refund. A dispute flow that looks
like a refund flow creates an expectation we cannot meet — and an unmet promise
of protection is itself a form of vouching, which is how R-16 bites.
**AC-M3.1** Before a student can file a condition dispute, the screen states
what a dispute **is**: a record and a look at the listing and the seller. It
states what it is **not**: a refund, a return, or a BookHop judgement on the
book. QA asserts the string is present and contains no forbidden word.
**AC-M3.2** `disputes` has no refund field and no screen offers one.
**AC-M3.3** **Product decision filling a hole in the contract:** `sla_due_at` is
`opened_at + 7 days` disposal with acknowledgement in 24 hours, matching the
grievance clock. `DATA-MODEL.md` carries the column with no value; this is the
value. A tighter clock than the statutory grievance channel would be a promise
one staff member cannot keep; a looser one would be worse than the channel the
student could have used instead.
**AC-M3.4** Resolution is one of the four enum values, with notes, by staff
only, and the student is told the outcome in-app with the reason in plain words.
**AC-M3.5** A `CONDITION` or `EDITION_MISMATCH` dispute always results in a look
at the listing, and a confirmed misdescription produces a `moderation_actions`
row — the dispute is the signal that feeds US-S3's accountability.
**Metric:** dispute rate; time to dispose; `AFTER` support minutes.
**Journey:** J6, J6-staff.

#### US-M4 · Decide a contact request without a second staff member, honestly
**Problem.** The CTO flagged that at one staff member, the two-person rule on
`contact_disclosures` blocks rather than reviews. **That is a product problem
before it is a technical one, and the product answer is that the common case
should never reach the queue.**

The r.5(3)(a) proviso is about a buyer being able to reach a seller after a
purchase. BookHop collects **no address and no phone**, so the only field that
could ever be disclosed is an email — a real personal-data disclosure, requested
by one student, about another, with no counterparty consent. Meanwhile the thing
the buyer actually wants is to *reach the person*, which does not require
disclosing anything.

**So the surface is a relay, and disclosure is the rare exception:**
**AC-M4.1** The student-facing action is **"ask BookHop to reach the other
student"**, not "request contact details". It reopens the listing thread and
notifies the counterparty. **No disclosure, no staff decision, no two-person
rule engaged, no `contact_disclosures` row.** QA asserts the relay path writes
no disclosure row.
**AC-M4.2** An actual field disclosure is only reachable when the relay has
failed — no reply after two notifications over 72 hours — and it goes to the
`contact_disclosures` queue with the justification the student wrote.
**AC-M4.3** The two-person rule stands. The second person is a **named human in
`legal_entities`** — the grievance officer or the nodal contact, who exists
because the law already requires them to. If the only staff member is that same
person, **the disclosure cannot be approved, and that is the correct
outcome**: there is nothing the relay has not already done, and a single
operator unilaterally handing one student another student's email is exactly the
insider action the rule exists to stop. The queue blocking is the rule working.
**AC-M4.4** `fields_disclosed` may never contain an address. There is none to
disclose because none is collected. QA asserts the enum of permissible fields.
**AC-M4.5** Every refusal tells the student plainly what was done instead, so a
refusal is never a silence.
**Metric:** `AFTER` support minutes; safety incidents. **Journey:** J5-staff.

#### US-M5 · Run the stopwatch so the number is real
**Problem.** The whole of D-009's mitigation is one number — support minutes per
completed transfer — and it is produced by a staff member remembering to start a
timer. A number that is easy to not record will not be recorded.
**AC-M5.1** The timer starts automatically when a staff member opens a ticket
and stops on save or navigation, with `source='SERVER_TIMER'`. Manual entry
exists for off-platform work and is **reported separately**, because a
hand-entered number is weaker evidence.
**AC-M5.2** The bucket names are exactly `TEST-1` §3.2's — `INTAKE`, `MATCH`,
`COORD`, `HANDOVER`, `AFTER`, `CHASE`, `UNALLOCATED` — so the app's numbers are
directly comparable to the thresholds set for the concierge design.
**AC-M5.3** Anything under six seconds records as 0.1 minutes, never 0.
**AC-M5.4** A batch matching run records one `batch_run_id` with its
`batch_match_count`, and the divisor is stored so the arithmetic is reproducible
by anyone who doubts it.
**AC-M5.5** The weekly export reports the figure **twice** — including chase
minutes, which is the pre-registered pass number, and excluding them, labelled
*"instrument cost removed, not the pass number"* — and prints the three
reference lines (4.00 min = Rs 11.36, 2.11 = Rs 6.00, 1.06 = Rs 3.00) plus the
sentence *"passing the 4-minute bar means not catastrophic, not viable."*
If the two figures straddle the threshold, it is a **fail, not a debate.**
**AC-M5.6** Opening a student's profile, chat or report detail writes
`personal_data_access_log` **and the screen says so to the staff member.** That
visibility is most of the control.
**Metric:** support load. **Journey:** J9-staff.

#### US-M6 · Open a campus only when the company exists
**Problem.** A browsable listing surface makes BookHop an e-commerce entity
under r.4(1)(a), which requires the company to exist (Gate B).
**AC-M6.1** `discovery_enabled_at` is NULL until opened by a management command
with the full evidence checklist, and a real (non-seed) student on a closed
campus sees a page explaining that listings open when the service launches,
**with no listing data on it.** QA runs this as a user journey, not a unit test.
**AC-M6.2** `open_discovery` refuses on a campus with no `legal_entity_id` and
no CoI. **No agent writes a `gate_authorisations` row.**
**AC-M6.3** Seed and real data never mix: `CHECK (seller_is_seed = buyer_is_seed)`,
and every metric view filters `is_seed = false` **and prints the excluded seed
count** so contamination is visible rather than silent.
**Metric:** none. This is a gate, and gates are not optimised.
**Journey:** J10-staff.

---

## 5. Exclusions

### 5.1 Deferred by a recorded decision — not mine to widen

| Excluded | Representable in the schema? | Reason | Returns when |
|---|---|---|---|
| Direct swap UI | **Yes** — `listings.intent='SWAP'` + `swap_wants`, flag off | Supply and demand peak in **antiphase**; direct swap needs two mutually matching needs at the same moment, and generates zero cash (D-007) | Evidence that swap-only users are the cheapest supply we can acquire. `JOURNEYS.md` §J-DEFERRED keeps the journey so reinstating it is not archaeology |
| General reading UI | **Yes** — `category='GENERAL_READING'`, flag off | Dilutes the only defensible wedge in a category where we hold no advantage (D-007) | D-007 reversal, **after** R-26 copyright exposure is reassessed |
| Any fee on the student side | No | 6% falsified at D-006: minimum take rate to cover support and payment cost alone is 16.7% at base, and O-10 makes leakage the compliant path. Free is not generosity — it deletes fee collection, the PPI question and most e-commerce exposure in one move | A funded, counsel-cleared second test. A fee-collection pass **reopens the question; it does not reinstate the fee** (D-008 Ruling 1) |
| Escrow, custody, wallet, credits, points, balance | **No, deliberately not** | D-004, D-003, ADR-003. Any instrument that holds money re-creates the refund obligation we structurally cannot discharge | Counsel C9, dormant, and a founder payment-activation decision |
| Settled transaction price, cash GMV | **No, and never** | P14 — s194-O's deeming provision has no consideration limb and its threshold is nil. Asking price fixed at intake is the only money in the system | Never |
| Browsable listings before incorporation | Gated by `discovery_enabled_at` | Gate B: r.4(1)(a) | CoI + INC-20A + grievance officer + takedown SOPs + counsel C1–C3 |
| Institutional / B2B features | No | The payer hypothesis rests on zero sources (O-12) | If the Rs 0 librarian probe succeeds **and** N2's compliance surface is reopened first |

### 5.2 Rejected by me, on product grounds — the useful list

Each of these was either implied by the contracts, named in the evidence base,
or is what a reader would expect to find. Each is rejected because it fails the
same two-part test: **a stated user problem and a measurable acceptance
criterion.** "Users expect it" and "competitors ship it" are not reasons and
appear nowhere below.

| # | Rejected | Why |
|---|---|---|
| EX-1 | **Ratings, reviews, reputation scores** | Two independent kills. O-11: a signal the platform disclaims is a form with a dropdown, and an *enforced* one is vouching (R-16). And at one campus with n in the tens, a 4.2-star average carries no statistical content while being a permanent, searchable, defamation-shaped claim about a named student. No problem it solves that inspect-before-pay does not solve better. |
| EX-2 | **A condition grade, badge, score or "BookHop-checked" marker** | R-16, O-11, and `DATA-MODEL.md` §11.4 routed it to me for exactly this answer. The schema cannot prevent bad copy; I can. US-S3 is the replacement: four descriptions, attributed to the seller, with no platform adjacent to them. |
| EX-3 | **Any price BookHop suggests** — "fair price", "similar books went for", a recommended range | Requires a settled-price history (P14 forbids storing one) and makes the operator a price-setter on its own marketplace. The seller's own number, fixed at intake, is the whole mechanism. |
| EX-4 | **Delivery, courier, pickup, lockers, a drop-off desk** | Three kills: it creates custody of goods; it removes the inspection moment, which is the only remedy we have for a return obligation we cannot discharge (`COMPLIANCE.md` §2.4(ii)); and O-5 shows courier-based national C2C is a ceiling, not an opportunity. A handover is not a limitation of v1, it is the remedy. |
| EX-5 | **Phone numbers, contact exchange, "reveal seller's number"** | Nothing to reveal — no phone column exists, by decision not oversight. The buyer's real need is to reach the person, which US-M4's relay serves without disclosing anything. |
| EX-6 | **Free-text meeting locations** | R-06. A curated point list is both the safety mitigation and the reason there is no address anywhere in the database. A free-text field would create the PII surface the entire schema was designed to avoid. |
| EX-7 | **SMS or WhatsApp notifications and support** | No SMS vendor, no DPA, and — decisively — **published WhatsApp support makes support minutes unmeasurable and voids D-009's mitigation** (`METRICS.md`; `DATA-MODEL.md` §11.3). This is the one exclusion that is load-bearing for the company's own evidence, not for the student. |
| EX-8 | **Onboarding tour, tutorial carousel, feature spotlight, streaks, badges, points, leaderboards** | No stated user problem. A student who came to find out whether a Rs 200 book exists is not short of motivation, they are short of patience and data allowance. Every one of these costs payload on a 3G budget and interaction count against US-S1's eight. |
| EX-9 | **Profile photos, bios, "about me", follower counts** | A photo is a person, not a book. Adds a harassment surface (R-06) and a PII surface for zero contribution to *should I buy this book*. `display_name` as first name plus initial is the entire identity surface. |
| EX-10 | **Wishlists, favourites, saved searches, "watch this book"** | A `book_request` **is** the saved search, and it is the one that produces a measurable row and triggers a notification (US-B2). A second, un-instrumented list would compete with it for the same intent and win, because it is easier — and then the request-side match rate, one of three decisive metrics, reads zero while students are quietly watching books. **Rejected to protect a measurement.** |
| EX-11 | **Chat before an offer, open DMs, user-to-user messaging outside a listing** | A harassment surface, and a pre-offer conversation produces no `transfer` row — so the match becomes unmeasurable at exactly the point we need to see it. A thread exists only between a buyer and a seller on a specific listing. |
| EX-12 | **Social login (Google, Apple)** | A new auth surface and a third-party processor relationship, for zero gain over a magic link to an institutional address — which is simultaneously the sign-in **and** the campus verification, with no artefact to store (`DATA-MODEL.md` §2, the cheapest compliance win in the schema). |
| EX-13 | **Recommendations, "students also bought", personalised ranking, promoted listings, sponsored placement** | r.4(12) and r.4(13) avoided entirely, and at pilot volume there is nothing to recommend. Ranking is documented and unpersonalised, and that is a feature. |
| EX-14 | **AI-written listing descriptions, AI photo enhancement, AI condition assessment** | IT Rules r.3(3) makes this a **compliance change, not a feature** (`DATA-MODEL.md` §12). And an enhanced photo of a damaged book is a misdescription we authored — moving the liability from the seller to us, which is R-16 in one tap. |
| EX-15 | **Public, SEO-indexed listing pages** | r.3(1)(b) trigger. `Disallow: /` and `X-Robots-Tag: noindex` are product requirements, not SEO neglect. |
| EX-16 | **A native app in an app store** | PWA (ADR-001). Store review is a release dependency on a founder-gated launch (G4), and an install prompt is a conversion step for a product that has not shown a student a single book yet. |
| EX-17 | **A `business_seller_flag` UI** | The mechanism is built because `COMPLIANCE.md` §2.4 requires it; the threshold is unset (`DATA-MODEL.md` §11.5). A UI for a flag that nothing computes would be a visible claim about a student with no rule behind it. Hidden boolean, no screen, until counsel C2. |
| EX-18 | **An in-app "how much did you pay?" field, anywhere, in any optional form** | P14. Including it "just for analytics" is how a settled price enters the database. Named explicitly because it is the single most likely well-intentioned breach of the constraint that most protects us. |
| EX-19 | **A reward, credit, badge or priority for confirming a handover** | The confirmation is the record (§3.2) and it is tempting to incentivise it. Any reward either costs money (there is none), or creates an instrument (D-003), or biases the one measurement the company is being built around. A measurement you have paid for is not a measurement. |
| EX-20 | **"Verified seller", "trusted student", a trust score of any shape** | Forbidden strings, R-16, and the only defensible version of the trust leg — campus-bounded identity and no contact exposure — is a statement about **our own process**, which carries no vouching liability (O-11). We say what we do, never what the seller is. |

---

## 6. Edge cases

Each has a decided behaviour. Where the decision fills a hole in the frozen
contract rather than contradicting it, it is marked **[fills a hole]**; where it
needs an amendment it points at §9.

| # | Case | Decided behaviour |
|---|---|---|
| EC-1 | Two buyers offer on the last copy; the second accept loses the race | Exactly one succeeds (partial unique index). The loser gets a page that says the book is taken **and offers the want form in the same view** — not a dead 409. AC-H1.1. |
| EC-2 | Seller withdraws the listing while an offer sits `OFFERED` | The withdrawal succeeds; the transfer goes to `CANCELLED` with `cancelled_by='SELLER'`; the buyer is told plainly, and is offered the want form. A silent disappearance is the worst available outcome. |
| EC-3 | Reservation expires (48h) while the buyer is mid-way through proposing a window | `422 RESERVATION_EXPIRED` rendered as a page that says the reservation ran out, the book is back up, and here is the link to offer again. Both parties are notified at expiry — not only the one who reloads. AC-H1.3. |
| EC-4 | A party deletes their account mid-transfer | **[fills a hole]** Erasure does **not** cancel the transfer, and nothing in the state machine lets SYSTEM cancel one. The counterparty sees "this student has deleted their account" (`display_name` is NULL after purge) and may cancel themselves; otherwise the existing timers resolve it — reservation expiry, window close, then 72h follow-up with no reply → `EXPIRED`. Chosen over adding a transition because the timers already produce a correct terminal state and a new transition would need a frozen-contract change for no gain. |
| EC-5 | Both confirm, then the buyer raises a condition dispute inside 7 days | `COMPLETED → DISPUTED` is already reachable and staff can resolve back to `COMPLETED`. The completion record is not retracted by a dispute; the dispute is a separate row. |
| EC-6 | The same physical book is listed twice by the same seller | Allowed — we cannot tell two copies from one, and refusing would block a seller with two genuine copies. If the first completes, the second stays live and the seller withdraws it. A duplicate-listing warning at publish time, never a block. |
| EC-7 | A student creates a duplicate `books` row for a book that already exists | `merge_books` resolves it with `merged_into_id` and **no row is deleted**, because listings point at it. A listing on a merged book resolves to the surviving book and renders normally. QA asserts the listing still loads after a merge. |
| EC-8 | The listing's edition differs from `prescribed_texts` | US-B3. Warn, name both editions, do not block, and never show a positive "matches your syllabus" marker. |
| EC-9 | Search finds the right book — on a different campus | **Never shown** (`visibility_scope='CAMPUS'`). The empty state must say *not on your campus yet*, which is true, and must not say *no results*, which teaches the student the book does not exist. AC-B2.2. |
| EC-10 | A real student signs up before the campus gate opens | They can sign in, confirm age, consent, and then do nothing — listing is also gated. The page says listings open when the service launches, names no date we cannot keep, and offers to email them. **[fills a hole]** The launch email is a one-off `notify()`; no new notification kind is needed. |
| EC-11 | `campuses.email_domains` is empty (no MoU yet) | `request_magic_link` cannot match a domain. The 202 page still names the accepted domains — and when there are none, it says the campus is not open for sign-ups yet. AC-A1.2 is what stops this being a silent void. |
| EC-12 | A 17-year-old declares an adult DOB | Admitted. We cannot detect it (R-28). On discovery: `REVOKED_MINOR_DISCOVERED`, suspend, erase, log, `safety_incidents` with `minor_involved=true`, POCSO duty surfaced as a required next step. **No copy implies a stronger check than a declaration.** |
| EC-13 | Photo upload fails at photo 3 of 4 on 3G | Listing stays `DRAFT` with photos 1–2 attached and is resumable. `create_listing` and `publish_listing` being separate calls is what makes this free. AC-S1.3. |
| EC-14 | A message contains a phone number or UPI handle | `contact_pattern_flag` is set. **Flagged, not blocked**; the sender is not warned or accused. Feeds harassment review and the leakage signal. The regex is trivially evaded and that is accepted — the signal is directional. |
| EC-15 | Staff member is the same human as the grievance officer, and a contact disclosure is requested | The disclosure cannot be approved. See US-M4: the relay has already done the useful thing, and a single operator disclosing one student's email to another is the insider action the rule exists to prevent. **The block is the rule working, and the student is told what was done instead.** |
| EC-16 | A Tamil-locale student lists an English-titled book | The title is never translated. Titles and ISBNs stay as printed; only interface strings switch locale. Translating a book title makes it harder to find, not easier. |
| EC-17 | A want is filed for a book whose ISBN we do not recognise | `book_requests.free_text_title` carries it (the CHECK permits book_id OR free text). It is a staff signal that the catalogue is missing a prescribed title — one of the few places the product tells us something about the syllabus we did not know. |
| EC-18 | Both parties say the book did not move, when it did | Undetectable by construction (`TEST-1` §4.2). The leakage lower bound is a **floor on leakage, not an estimate of it**, and the export says so. No proxy is offered. |
| EC-19 | A support ticket arrives in Tamil and the staff member reads English | Operational, not technical: the ticket is answered in the student's locale or not at all. Flagged to `marketplace-ops` — a support surface that silently answers only English speakers is an accessibility failure with a WCAG-adjacent shape and no test that catches it. |
| EC-20 | A report is filed against a listing that is already removed | Accepted, acknowledged, and disposed with the right outcome. A report that bounces because staff were faster teaches people not to report. |

---

## 7. Metric accountability — every feature answers to a number

A feature without a metric is a preference. The left column is from
`METRICS.md`; the right is which story is accountable for it. **Nothing in this
PRD requires holding money, storing a settled price, or vouching for a book's
condition**, which is why three rows read as they do.

| Metric | Denominator | Accountable stories |
|---|---|---|
| Verified students | — | US-A1, US-A2, US-A3 |
| Valid listings | all listings created | US-S1, US-S4 |
| Supply density | campuses with ≥1 active user | US-S1 |
| Search success rate | all searches | US-B1, US-B2 (empty state), US-M6 (seeding) |
| Match rate — search limb | distinct searching users/week | US-B1, US-H1 |
| Match rate — **request limb** | requests | US-B2 — **blocked on CG-3 and CG-4** |
| Time to match | matched listings | US-B1, US-H1 |
| Completion rate | accepted offers | US-H2, US-H3, US-H4 |
| No-show rate | scheduled handovers | US-H2, **US-H3** (the story that should reduce it) |
| Cancellation rate | accepted offers | US-H1, US-H3 (must not be inflated by reschedules) |
| Dispute rate | completed transfers | US-S3, US-B3, US-M3 |
| Repeat transfer @90d | first-time recipients cohort | US-H4, US-X1 (the pseudonym surviving deletion is what makes it computable) |
| Book value moved | — | US-S2. **Asking prices only.** |
| Cash GMV | — | **Not computable in v1 and never will be.** P14. Any v1 report quoting it is wrong. |
| Platform revenue | — | **Rs 0 by design.** |
| Support load (minutes/transfer) | completed transfers | **US-H6, US-M5** — the D-009 reversal trigger |
| Leakage band | known-moved + unknown | US-H5 |
| Reports per 1,000 listings · time to moderate | listings · reports | US-X3, US-M1, US-M2 |
| Safety incidents | — target zero | US-B4, US-H2, US-X4, US-M4 |
| WCAG 2.2 AA violations | — target zero | every story, both locales |
| p75 LCP on mid-range Android/3G · p95 search latency | — | US-S1, US-B1 |
| Data-subject requests inside 7 days | requests | US-X1, US-X2 |

---

## 8. Scope and dependency order

The build order in `TASKS.md` is **correct and I am not reordering it.** What
follows maps my stories onto it and names where a story is blocked.

| Slice | Stories | Product blockers |
|---|---|---|
| S0 | US-M6 (gate, seed separation) | none |
| S1 | US-A1, US-A2, US-A3, US-X1, US-X2 | none. Deletion before there is data to delete is the right call |
| S2 | US-S1, US-S2, US-S3, US-S4 | none |
| S3 | US-B1, US-B2 (partial), US-B4 | **US-B2 is half a feature until CG-3 + CG-4.** The want form ships; the answer does not |
| S4 | US-H1 | none |
| S5 | US-H2, US-H4, US-H5, US-M4 | **US-H3 blocked on CG-1.** I recommend CG-1 lands with S5, not after — a handover flow with no reschedule will generate the support minutes we are measuring, and the measurement will be of our own omission |
| S6 | US-X3, US-X4, US-M1, US-M2, US-M3, US-M5 | **US-H6 blocked on CG-2.** CG-2 should land in S5, one slice earlier than the support tables, because "they're not replying" is a handover problem |
| S7 | reporting for everything above | CG-3, CG-4 must have landed or the request-side match rate reports zero |
| S8 | — | founder spend approval |

---

## 9. Where this PRD and the frozen contracts disagree

The contracts came first. Each item below states the problem, the smallest
change that fixes it, what it touches, and my severity. **I am not silently
designing around any of them and I am not silently accepting any of them.**
All five are escalated to `cto`.

### CG-1 · A `SCHEDULED` handover cannot be rescheduled · **BLOCKING for S5**

**Problem.** `DATA-MODEL.md` §6.2 gives `SCHEDULED` three exits: forward to
`AWAITING_CONFIRMATION`, sideways to `NO_SHOW` (terminal), or out to `CANCELLED`
(terminal). There is no path back to `ACCEPTED`. The most ordinary event in a
campus handover — *can we make it tomorrow* — has no representation, so it is
expressed as a cancellation.

**Why a workaround is worse than the change.** Cancel-then-re-offer loses the
transfer row and its `transfer_events` thread, counts a cancellation against
T1b's pre-registered 25% bar, corrupts time-to-match, relists a book that is not
actually available, and pushes the coordination into chat where it becomes
`COORD` support minutes — the number D-009's reversal trigger reads.

**Smallest change.** One transition: `SCHEDULED → ACCEPTED`, actor buyer or
seller, guard `now() < handover_window_end` and fewer than 2 prior reschedules
on this transfer. One endpoint `POST /api/v1/transfers/{id}/reschedule` /
`POST /transfer/{id}/reschedule`. One L1 function
`reschedule_handover(actor, transfer, expected_version)`. **No schema change** —
`transfer_events` records it with `reason_code='RESCHEDULE_REQUESTED'`, and the
existing `propose_handover` / `agree_handover` pair takes it from there.
One analytics change: the cancellation-rate query must exclude it.

**Severity.** Blocking. **Recommendation:** amend before S5 begins.

### CG-2 · No student can open a support ticket · **BLOCKING for D-009's mitigation**

**Problem.** Every signature in `API-CONTRACT.md` §3 `apps/support/services.py`
takes `staff` first. §5 has no support endpoint at any level.
`support_tickets.channel` offers `'IN_APP'` and nothing can create such a row
from the student side. A student can file a `report` (abuse), a `grievance`
(complaint) or a `dispute` (transfer-bound) — and cannot ask a question. "The
seller hasn't replied in three days" is not any of those three, and it is the
most common thing a student will want to say.

The consequence is not a UX gap. **`METRICS.md` and `DATA-MODEL.md` §11.3 both
state that D-009's mitigation fails silently if support happens off-platform,
and the frozen contract leaves the student no on-platform place to go.**

**Smallest change.**
- One L1 function:
  `open_ticket_as_student(actor, *, kind, transfer=None, listing=None, body, channel='IN_APP') -> Ticket`,
  plus `reply_to_ticket(actor_or_staff, ticket, body)`.
- Two endpoints: `POST /api/v1/support/tickets` + `POST /api/v1/support/tickets/{id}/replies`,
  with L3 `POST /help/ask` and `POST /help/{id}/reply`, and `GET /help` for the
  student's own tickets.
- **One new table**, because `support_tickets` has nowhere to put what the
  student actually wrote:
  `support_messages (id, ticket_id FK, author_pseudonym uuid NULL, author_staff_id bigint NULL FK, body text, created_at, purge_due_at)`.
  Rejected alternative: reusing `threads`/`messages`, which §5.5 reserves for a
  buyer and a seller on a specific listing — overloading it would put staff
  inside a student-to-student thread.
- Rate limit `POST /support/tickets` at 10/day per user, mirroring reports.
- One `COMPLIANCE.md` §7 row for `support_messages`, retention 1 year.
- `close_ticket` gains a guard: refuse on a ticket with no `support_work_log`
  row (AC-H6.6).

**Severity.** Blocking. **Recommendation:** amend and schedule in S5, one slice
ahead of the support tables, because the need arises during handover.

### CG-3 · `book_requests.fulfilled_by_transfer_id` is never written · material

**Problem.** The column exists. The request-side match rate query in
`DATA-MODEL.md` §9.3 reads it. **No L1 function sets it** — `create_request` and
`close_request` are the only two. So one of the three decisive metrics in
`METRICS.md` returns zero permanently while the rows to compute it exist.

**Smallest change.** Inside `confirm_handover`, when a transfer reaches
`COMPLETED`: close any `OPEN` `book_requests` with the same `buyer_pseudonym`
and `book_id` on the same campus, setting `status='FULFILLED'` and
`fulfilled_by_transfer_id`. One query inside an existing transaction. No schema
change, no new endpoint.

**Severity.** Material. **Recommendation:** fold into S5 with the confirm flow.

### CG-4 · There is no `WANT_MATCHED` notification · material, and the most product-significant

**Problem.** The notification kinds in `DATA-MODEL.md` §8 cover offers,
handovers, follow-ups, reports, disputes and the quarterly rules reminder.
**None covers "the book you asked for is now available."** So the complete
designed journey for a student whose book is not there is: state a want, and
never hear anything. In an antiphase market where T4 says the gap between
disposal and need is 2–8 weeks, that is the journey most students will have.

**Smallest change.** One notification kind `WANT_MATCHED`. One job
`requests.match_scan`, enqueued by `publish_listing`, which finds `OPEN`
requests on the same `(campus_id, book_id)` and calls `notify()` with a
`dedupe_key` of `want:{request_id}:listing:{listing_id}` so a republish cannot
notify twice. `notifications.kind` is free text, so this may need no schema
change at all — `cto` to confirm.

**Severity.** Material, and I rate it the highest-value change of the five for
the student. **Recommendation:** S3 if possible, S5 at the latest.

### CG-5 · `age_check_pending` holds a DOB for up to 7 days on the happy path · clarification, not a change

**Problem, or possibly my misreading.** `DATA-MODEL.md` §2 says the
`age_check_pending` row is "deleted the moment staff review completes, and
unconditionally at `expires_at`" (declared_at + 7 days).
`age_verification_events.method` also permits
`SELF_DECLARED_DOB_SERVER_CHECKED`, which implies an instant-confirm path with
no staff review. If the instant path still writes an `age_check_pending` row,
then a declared DOB sits in the database for seven days on the **most common**
journey — which is more DOB retention than `COMPLIANCE.md` §7 row 7 intends, and
it also leaves the student's status ambiguous for a week if they look.

**My recommendation.** On the instant-confirm path, write **no**
`age_check_pending` row at all: check the date, set `adult_verified`, write the
`age_verification_events` row, discard the DOB in the same request. The pending
table then exists only for the cases genuinely routed to `STAFF_REVIEW`.

**Severity.** Clarification. May be exactly what is already intended, in which
case the answer is one sentence in the data model and no code changes.

### What I am accepting rather than contesting

Recorded so nobody reopens these thinking they were overlooked:

- **The eleven-state machine, the partial unique index, and dual confirmation.**
  Better than what I would have specified, particularly "one side alone is never
  a completion".
- **The 48-hour reservation and the 15-minute no-show definition.** Both are
  arbitrary and both are *fine*; arguing them without data would be taste.
- **Django admin for staff rather than a bespoke console.** It costs the staff
  experience some polish and buys the audit trail, the access log and the
  two-person rule for nothing. At one staff member that is the right trade, and
  US-M1/US-M2's requirements are achievable inside it.
- **Tombstone-plus-purge, the one-year floors, and the skip-list.** I would not
  have thought to assert that the repeat-transfer query still returns a deleted
  user's transfers under their pseudonym. It is the best test in the programme.
- **`condition` as four values.** I wanted to delete the field and specify
  photos only. The schema is right: a buyer walking across campus needs to know
  whether to expect a broken spine. US-S3 solves it with copy, which is where
  the problem actually was.

---

## 10. Open items this PRD does not close

1. **Zero students have been interviewed.** Every persona and problem statement
   here is a hypothesis. The instruments are written, pre-registered and funded;
   they are blocked on three named campus contacts and nothing in this document
   substitutes for them.
2. **The repeat-transfer threshold is deliberately unset** (§3.3). `ceo-planning`
   sets it on the first real 90-day cohort, then locks it.
3. **The search-success floor of 25% is weak** — a `[G]` derived from a `[G]`.
   It is a review trigger, not a kill, and Test 1's match rate would have been
   the cheap way to firm it up (`DISCOVERY.md` §8.1 item 7).
4. **`business_seller_flag` has no threshold** and therefore no UI (EX-17).
   Returns with counsel C2.
5. **Tamil support coverage** (EC-19) is an operating commitment nobody has
   made. To `marketplace-ops`.
6. **The institutional payer has zero sources** and this PRD builds nothing
   toward it. If the librarian probe succeeds, N2's compliance surface reopens
   before any feature does.
7. **Design system does not exist.** Every copy string specified here is
   behavioural intent, not final wording. `design-director` owns the words,
   including the approved-vocabulary list in §4, and the Tamil phrasing of the
   handover-safety and dispute-expectation copy is a **blocking** task — those
   are the two places where a literal translation changes the meaning into a
   promise.

---

## Amendment log

| Date | Change | Approved by |
|---|---|---|
| 2026-10-21 | v1.0 — first PRD. Written after contracts were frozen (§0). Five contract disagreements raised (§9) | product-manager |
