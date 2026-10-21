# BookHop — Discovery Package

Owner: `product-manager` · Version **v0.2** · Date: 2026-10-21 · Phase A
Handoff: `ceo-planning`, `red-team`
Supersedes v0.1 (same date). Revised after `evidence/RED-TEAM/G1-MEMO.md` and
D-006 / D-007.

---

> ## VALIDATION STATUS
> **ZERO interviews conducted. ZERO surveys fielded. ZERO students spoken to.**
> **Still zero after this revision — v0.2 changes the instruments, not the
> evidence.** Every statement in this document about what a student wants,
> feels, pays, or does is a **HYPOTHESIS**, not a finding. Nothing here may be
> cited as user evidence by any agent. The deliverables here are *instruments*
> (§4, §5, §6) and *falsifiable claims* (§3), per `company/README.md` §8.
>
> **Budget status:** D-007 approved Rs 16,500 total; Rs 4,500 of it is this
> document's fieldwork (18 interviews × Rs 200 + Rs 900 contingency).
> Rs 0 spent. Fieldwork is blocked only on the three named campus contacts.
>
> **Pre-registration lock.** The thresholds in §3 are final as of this
> revision. **The moment the first interview is booked they cannot be moved.**
> A threshold edited after data starts arriving is not a pre-registered
> threshold; it is a rationalisation with a date on it.

---

## 0. Changelog — what Red Team broke and what changed

v0.1 of this document was written for a product that no longer exists: one
with a 6% student transaction fee, direct swap, and general reading in v1.
D-006 falsified the fee, D-007 cut swap and general reading, and the Red Team
memo found four defects in the instruments themselves. Both sets of changes
are applied below. A reader who knows v0.1 should read §3, §4 and §5 again
from scratch — the numbers that look unchanged are measured on different
samples.

| # | What Red Team established | What changed here |
|---|---|---|
| **O-6** | T2's kill threshold (6 of 18 describing a past paid whole-book purchase) was measured on a sample whose screener admitted people **for having paid for a book**. Reachable by selection alone. | **Both ends fixed.** The pay-money limb is deleted from the §4.1 screener. T2 is **split**: the population claim (**T2a**) moves to the survey, where n is large enough to estimate a prevalence; the interview limb (**T2b**) is re-denominated onto the 12 cleanly-screened respondents only and demoted to a mechanism test. The counter-persona limb Red Team proposed as a kill condition is kept, but as a **contamination diagnostic** — see §3, where I say why I disagree with its original form. |
| **O-7** | T3 was *unprompted* AND conjunctive AND set at 50%, and measured a disposition rather than the moment. O-10 then established that inspect-before-pay **is** the disintermediation event. | **T3 rewritten from scratch.** It now names the thirty seconds at which the buyer is holding the book with UPI open, and it is measured **past-tense on a real second-hand transaction the respondent already completed** (new Q20a–Q20c in §4.5), not on an intention about BookHop. Prompted, single-limb, denominated on respondents who actually have such a transaction, with a minimum denominator stated. Because the student side is now free, T3's consequence also changed: disintermediation no longer costs revenue, it costs **the completion record the institutional-payer thesis needs in order to be sold anything**. |
| **O-8 (part 1)** | T1 at 40% listing vs Finance's 30% activation implies a 75% list-to-transfer conversion in a cold-start market. One of them is wrong. | **T1's bar raised to 60%**, with the arithmetic shown and the conditions on it stated. I resolved it on my side rather than asking Finance to drop activation, because listing is unambiguously the easier act and the bar I own is the one that was too low. Finance's alternative resolution is named in §3 so the two documents can be reconciled in one place. |
| **O-8 (part 2)** | T4 was denominated in handover **count** while the two halves of the catalogue differ in price by an order of magnitude. Restate in cash GMV. | **Declined, and T4 retired instead.** T4 measured whether *general reading* fills the seasonal trough. D-007 cut general reading from v1 after the memo was written, so restating its denomination would be polishing an instrument pointed at a feature that does not ship. See §3 for the reasoning. |
| **O-9** | The antiphase assumption is unsourced and, from its own cited calendar, is 2–8 weeks rather than months. Cut direct swap regardless. | **T4's slot reused for the timing claim.** Three past-tense timing questions added at §4.4 (Q17a–Q17c), and the kill threshold set at Red Team's 10-week median with the 6-week refutation bar recorded. Direct swap was already absent from the instruments; the scope cut is recorded in §1.2 and §3. |
| **O-3** | Gift share and swap share are called decisive in three documents. Across their **entire** range they move the unit by Rs 0.56 and Rs 0.79. | **Interview time reallocated.** Cut: Q14 (gift-to-junior narrative), Q22 and all of old §4.6 (general reading — out of scope per D-007), and the deep probe on Q24. Recovered ≈6 minutes spent on: the inspect-before-pay moment (§4.5), the institutional-provision probe (new §4.6), and the timing questions (§4.4). Survey Q7 is kept but re-pointed — its decision is *does supply exist*, not *what is gift share*. |
| **D-006 / D-007** | Student side is free permanently by design; the institution is the hypothesised payer; swap and general reading are out of v1. | Every question probing willingness to pay **a platform** is gone — that hypothesis is falsified and a stated-preference question cannot confirm a structural falsification anyway (§3, T-fee note). Willingness to pay **the other student** is kept and is now more important, not less: with no fee, the only price in the system is the one between the two students, and if the buyer's maximum is below the seller's minimum there is no trade for anyone to intermediate. New §4.6 tests the institutional payer **from the student side**; new §4.10 carries O-12's four librarian questions, rewritten past-tense-first. |
| — | Internal inconsistency found during this revision, not by Red Team. | §4.1 said recruit **5** counter-persona respondents; §6.2 said **6**. Both now say 6, and the counter-persona is recruited on a **positive profile** rather than on screener failure, because with the pay-money limb removed a Vignesh can pass the screener. |

**Not applied, with reasons, so the next reader does not assume they were
missed:** O-11's three-card concept test (outside my command, and a forced
choice between three cards we designed is the exact pattern §4.9 already
rejects); O-5, O-12's desk-research half, and all of Test 1 (not my
instruments — Test 1 is Red Team's and runs separately).

**Tag key used throughout.** Every assertion carries one:

| Tag | Meaning |
|---|---|
| `[S]` | **Sourced** — external source cited in §8, URL + date accessed. |
| `[R]` | **Reasoned assumption** — derived from a sourced fact or from arithmetic, stated with its reasoning. Could still be wrong. |
| `[G]` | **Pure guess** — invented by this agent, no basis. Needs a test. Any `[G]` that survives into the PRD unchanged is a defect. |

---

## 1. Persona hypothesis

### 1.1 Primary persona (HYPOTHESIS) — "The second-year who already paid once"

Not a demographic sketch. A specific person defined by a specific behaviour
we think exists.

| Attribute | Claim | Tag | Why / what would falsify |
|---|---|---|---|
| Year | 2nd or 3rd year undergraduate (not 1st, not final) | `[R]` | 1st years buy what the seniors/college tell them and have no books to sell yet; final years are the biggest *sellers* but are leaving. 2nd/3rd year is the only cohort that is both buyer and seller in the same term. Falsified if interviews show 1st years are the active buyers and nobody else transacts. |
| Course type | Engineering (Anna-University-affiliated syllabus) or commerce/science at an arts & science college; **not** medicine | `[R]` | Engineering has prescribed, edition-stable, expensive titles — Pearson lists Anna University Engineering Maths I at Rs 499 and Rs 689; Wiley lists first-sem Anna University titles at Rs 349 `[S]`. Medicine books are far costlier and the resale market there is already organised, which is a different product. |
| Income reality | Pays for books from a monthly allowance of roughly Rs 2,000–5,000, or asks a parent per purchase | `[G]` | **Pure guess. No source.** This is the single most load-bearing unknown in the persona — it sets whether Rs 150 vs Rs 400 is a real decision. Test: Q7 in the survey, Q9 in the interview. |
| Price sensitivity | A Rs 500 textbook is a deliberated purchase; a Rs 80 photocopy is not | `[R]` | Follows from the Rs 349–689 new price `[S]` against the Re 1–2/page photocopy rate `[S]`. The *shape* is reasoned; the threshold is a guess. |
| Phone | Android, mid-range or entry (Rs 8,000–15,000), 2–4 years old, storage near-full | `[G]` | No source found for Indian student handset mix. Matters for CTO/design (p75 LCP target already in `metrics/METRICS.md`). **No longer tested in Phase A** — survey Q11 carried this and was replaced in v0.2 by the institutional-provision question, because D-006 condition 3 forbids code until Test 1 reports and a payload budget cannot be spent. Re-add when Phase C opens. |
| Data | Prepaid daily-cap pack, roughly 1–2 GB/day; Jio's 1 GB/day 28-day pack is Rs 249, and a small Rs 100 top-up buys 5 GB (~Rs 20/GB) `[S]` | `[S]` for tariffs, `[R]` for "this is what students buy" | A daily cap means a student can browse but resents a heavy app; it does **not** mean they are offline. Falsified if students report Wi-Fi-first behaviour on campus. |
| Language | Reads technical content in English; switches to Tamil for negotiation, trust-building and informal chat | `[R]` | Instruction medium in engineering is English; Tamil is the ambient social language in Chennai. Reasoned, not measured. Drives the EN/TA copy decision owned by `design-director`. Test: interview Q4 and Q19 observe which language the respondent *uses*, not which they claim. |
| Where they get books today | Mixed: seniors, photocopy shop, PDF, college/department library, new purchase, Moore Market | `[R]` from §2 | The mix ratio is entirely unknown. Survey Q3 exists only to measure it. |
| End-of-semester behaviour | Books stay in a shelf/under the bed; a few go to a junior they know; none are sold | `[G]` | **Pure guess, and it is the guess the entire supply side rests on.** If students already sell efficiently, there is no supply gap. If they already give books free to juniors, our price is competing with zero. Interview Q12, Q13, Q15, Q16 and the new timing questions Q17a–Q17c target this directly; survey Q7 sizes it. |
| Trust posture | Will meet a stranger from the same campus in a public campus spot in daylight; will not go off-campus | `[G]` | Drives R-06 (physical safety) and the entire handover design. No evidence. Interview Q20 and Q21. |
| Payment | UPI, instantly, phone-to-phone at the handover | `[R]` | UPI is the default small-value rail in India. The reasoned part is that they will *not* want an in-app payment that adds a step — which is also what D-004 (no custody of funds) prefers. |

**What this persona is NOT claiming.** It does not claim the student is
frustrated, underserved, or looking for a solution. We have no evidence of
felt pain. §2 is deliberately written to argue the opposite.

### 1.2 Secondary persona — "The general reader with a shelf problem" · **DEFERRED, NOT MEASURED IN PHASE A**

**D-007 cut general reading from v1.** This persona is retained for the record
and for the data model (CTO constraint at Phase C), but **no interview or
survey question in §4–§5 measures it any more** — old Q22 and old §4.6 were
deleted in v0.2 and the four minutes went to the institutional probe. Do not
re-add questions for this persona without a scope reversal recorded in
`DECISIONS.md`.

It existed in the v0.1 thesis because of R-04 (seasonality): textbook demand
spikes twice a year and the trough had to be filled by something. R-04 is now
addressed directly by **T4 (timing)** in §3 instead — the question is whether
the trough is weeks or months, not what fills it.

- Reads fiction/non-fiction outside the syllabus, 6–20 books a year `[G]`.
- Buys at the Chennai Book Fair, from pavement sellers (reported Rs 20–70 a
  book `[S]`), from Moore Market, or new online `[R]`.
- Finishes a book and has no reason to keep it; does not want to throw it
  away `[G]`.
- **The risk inside this persona:** the general reader's transaction has no
  deadline. A textbook buyer needs the book before an exam; a fiction reader
  needs nothing by any date. Zero urgency may mean zero liquidity in the
  trough — which would *not* fix R-04, only disguise it. **No longer
  measured:** old interview Q22 was cut in v0.2 with the rest of general
  reading. R-04 is now addressed by T4 (timing) instead.

### 1.3 COUNTER-PERSONA (HYPOTHESIS) — "The student who will never use BookHop"

Required by the charter. If we cannot name who this is not for, we have not
scoped it.

**"Vignesh, 3rd-year CSE, WhatsApp-native, PDF-sufficient."**

- His class has a WhatsApp group of 60 people and a shared Google Drive with
  every PDF the batch has accumulated over three years `[G]`.
- For the two subjects where he needs paper, he walks to the shop outside the
  gate and photocopies the four chapters the exam covers for under Rs 100
  `[R]`, derived from Re 1–2/page `[S]`.
- He has never paid for a textbook with his own money.
- **Why he will not use us:** his acquisition cost is Rs 0–100 and his
  acquisition *time* is minutes, in a channel where he already knows everyone.
  Our product asks him to pay more money, wait longer, and meet a stranger.
  Every one of those is a downgrade for him.
- **Why this matters more than the primary persona:** if Vignesh is the
  *modal* student rather than an edge case, BookHop's addressable demand is a
  small residue, not a market. The survey's single most important job is to
  estimate what fraction of the campus is Vignesh. That is Q3 + Q4, and
  **since v0.2 it is the survey, not the interviews, that carries the T2
  population claim** — see §3.
- **How he is recruited (changed in v0.2).** Previously "anyone who fails the
  screener". That no longer works: the §4.1 screener's pay-money limb was
  deleted to fix O-6, and a Vignesh can now pass it. The 6 counter-persona
  respondents are therefore recruited on a **positive profile** — S3 shows
  their most recent course book was a PDF or a photocopy **and** S5 shows they
  have never paid their own money for a course book — and they are kept in a
  separate, separately-denominated bucket throughout §3.

**Second counter-persona:** the student with a well-stocked department
library or a reliable senior-handover tradition in their department. Their
marginal cost is zero and social, and we have nothing to add `[R]`.

---

## 2. Problem statement and current workarounds

### 2.1 The honest problem statement

Draft, stated so it can be attacked:

> A Chennai undergraduate who needs a specific prescribed book often cannot
> get a *physical copy* of the *right edition* quickly and cheaply, and a
> student who has finished with a book has no low-effort way to convert it
> into money — so books sit unused while other students pay for copies or
> read on a phone.

**Two things are wrong with this statement until proven otherwise:**

1. It assumes the student wants a *physical whole book*. The evidence in §2.2
   says the dominant behaviour may be acquiring *partial content*, not books.
2. It assumes the seller's inconvenience is a problem *to the seller*. An
   unused book costs the owner nothing per day. A problem with no running
   cost generates no urgency.

### 2.2 The workarounds, honestly

Costs below are per-book-equivalent. Money figures tagged `[S]` are sourced;
time and hassle figures are `[R]` or `[G]` and are flagged — we have measured
none of them.

#### (a) Partial photocopy / course pack — **the one we must beat**

- **Money.** Re 1–2 per B&W page at Indian college shops and libraries: a
  June 2025 college notice sets Xerox at Re 1/copy and print at Rs 2/copy;
  another institute library lists Rs 1/page photocopy and Rs 2/page print
  `[S]`. For the 60–100 pages an exam actually covers, that is **Rs 60–200**,
  plus binding `[R]`.
- **Time.** Minutes to an hour; the shop is usually at the campus gate `[R]`.
- **Hassle.** Near zero. Walk, hand over the book or the shop's own master
  copy, collect.
- **Legality.** This is settled law in India in the student's favour, more
  than most people assume. In *Oxford University Press & Ors v. Rameshwari
  Photocopy Service*, the Delhi High Court held in 2016 that reproducing
  portions of copyrighted books for course packs fell within the educational
  exception in s.52(1)(i) of the Copyright Act 1957; the publishers withdrew
  the suit in March 2017 and said they would not appeal to the Supreme Court
  `[S]`. A separate SLP was filed by the Indian Reprographic Rights
  Organisation in 2017 `[S]`; **we did not confirm its current status and do
  not claim one.**
- **Why it persists.** It is cheap, legal, instant, and sized to the actual
  need — the student does not want a book, they want the four chapters in the
  exam `[R]`.
- **Does BookHop beat it?** *On price, no.* A used textbook at Rs 150–250
  (hypothetical) costs more than a Rs 80 partial copy. We can only win where
  the student needs the **whole book, for a whole semester, repeatedly** —
  lab/drawing work, a core subject carried across semesters, or reading that
  is unbearable on a phone `[R]`. **This is a narrower wedge than the thesis
  in README §1 implies, and §3 restates the thesis to match.**

#### (b) Free PDF — WhatsApp group, Telegram channel, shared Drive

- **Money.** Rs 0 `[S]`, effectively — plus data. Telegram is heavily used in
  India for exam-prep material sharing and has an acknowledged piracy problem;
  reporting put India at roughly 40 million Telegram users and its largest
  market, though that figure is from 2019 and is dated `[S]`.
- **Time.** Seconds, if the batch group already has it `[R]`.
- **Hassle.** Low to acquire, high to *use*: reading a 400-page technical book
  on a 6-inch screen, no annotation, phone storage pressure `[R]`.
- **Legality.** Unauthorised reproduction/distribution of whole books is
  infringement under the Copyright Act 1957 — a Kerala news report cites up
  to three years and Rs 3 lakh `[S]`, which we have **not** verified against
  the statute and do not rely on. Enforcement against individual students in
  India appears effectively absent `[R]`.
- **Why it persists.** Free, instant, socially frictionless, zero risk felt.
- **Does BookHop beat it?** Only on the *reading experience* and only for
  people who actually read long-form. Never on price or speed. If the
  interviews find students are content reading textbooks on a phone, the
  physical-book premise is in serious trouble.

#### (c) Seniors' hand-me-downs

- **Money.** Rs 0 to a token amount `[G]`. **Time.** Depends entirely on
  knowing a senior `[R]`. **Hassle.** Social, not logistical.
- **Why it persists.** Free, trusted, and comes with the previous owner's
  notes and exam intelligence — a feature we cannot replicate `[R]`.
- **Does BookHop beat it?** No, and we should not try. We serve the student
  who *doesn't have* that senior — a first-generation student, a lateral
  entrant, a transfer, someone outside the dominant social group `[G]`. If
  that group is small, so are we.

#### (d) Department / college library and book bank

- **Money.** Rs 0 or a refundable deposit `[G]`.
- **Hassle.** Copy scarcity at exam time, return deadlines, fines `[R]`.
- **Why it persists.** Institutional and free.
- **Does BookHop beat it?** Only on availability at peak, which is exactly
  when our supply is also scarcest `[R]`. **Unresolved: we have not audited a
  single Chennai college library's holdings.**
- **Promoted in v0.2 from a workaround to the payer hypothesis.** With the
  student-side fee falsified (D-006), the institution in this row is no longer
  only a competitor — it is the only candidate payer left (§3.0). That makes
  this the one workaround we must understand from **both** sides: §4.6 asks
  students what the department actually did, §4.10 asks three budget-holders
  what they actually control, and survey Q11 sizes it at n ≥ 120. Red Team
  O-12 found **zero sources** in any Phase A document on Indian college book
  provision; these are the cheapest available first three.

#### (e) Buying new

- **Money.** Rs 349–689 for Anna-University-targeted titles from Wiley and
  Pearson `[S]`; a 2025 Veerarajan *Higher Engineering Mathematics* listed at
  Rs 335 `[S]`. Indian-market reprints of foreign textbooks are the cheap
  legitimate route and are marked for South Asia sale only `[S]`.
- **Why it persists.** Certainty of edition, condition, and availability.
- **Does BookHop beat it?** Yes, on price — this is our clearest win, and it
  is also the *smallest* segment, because few students buy new `[G]`.

#### (f) Existing resale channels — OLX, campus WhatsApp, Instagram stories

- Sourcing guides list OLX, WhatsApp and Telegram resale groups as where used
  books change hands `[S]`. A student-marketplace vendor describes the status
  quo as "scattered WhatsApp groups, Instagram stories, and word of mouth" —
  **that is a competitor's own marketing copy, not evidence** `[S]`.
- Earlier attempts at exactly our idea exist (Doosradeal for engineering
  second-hand textbooks; Cultext for used textbooks, rentals and buyback)
  `[S]`. **Their current status is unknown to us.** Assessing whether they
  died and why belongs to `market-finance` (R-07, `evidence/COMPETITORS.md`)
  — but Product flags it as the most informative single piece of research
  nobody has done yet.
- **Why it persists.** Free, already installed, already populated with people
  you can place socially.
- **Does BookHop beat it?** Only if trust + exact-edition matching +
  structured handover are worth more than a group chat you are already in.
  That is the README §1 thesis, and it is still unproven.

#### (g) Offline used-book trade — Moore Market, pavement sellers

- Moore Market is Chennai's used-book hub; sellers claim close to 150 shops
  and over 1 crore books, with academic reference books the main draw `[S]`.
  Pavement sellers report pricing between Rs 20 and Rs 70 `[S]`. Berkshire
  Books (Nungambakkam) sells at roughly Rs 250/kg; Murugan Old Book Stall
  (Mylapore) from about Rs 50 `[S]`. Reporting also describes the Moore Market
  trade as slumping, blamed on online bookstores — that piece's date is
  unclear `[S]`.
- **Money.** Cheap. **Time.** A cross-city trip `[R]`. **Hassle.** Finding
  *your* edition is luck.
- **Does BookHop beat it?** On proximity and exact-edition search, plausibly
  yes. On breadth of inventory, not remotely — and the market sizing claim
  ("India second-hand books market USD 781.04m in 2023, 6.8% CAGR") comes from
  a commercial research firm's own report page and should **not** be used in
  any BookHop financial model without a primary source `[S]`, flagged for
  `market-finance`.

### 2.3 The workaround ranking we must act on

1. **Partial photocopy at Rs 60–200** — beats us on price and speed. Beatable
   only on "whole book, whole semester".
2. **Free PDF in the batch group** — beats us on everything except reading
   experience.
3. **Campus WhatsApp resale** — free, installed, already liquid.

Everything else is secondary. **A product plan that does not have an explicit
answer to #1 and #2 is not finished.**

---

## 3. Sharpened product thesis (falsifiable)

### 3.0 The thesis these instruments now test

v0.1 tested a product with a 6% student transaction fee. That is gone. The
thesis below is the one recorded at D-006 / D-007 and in the Red Team memo §5,
and **every threshold in §3.1 is pointed at it**:

> BookHop is a **syllabus-to-shelf matching layer for edition-locked
> prescribed textbooks on one Chennai campus**. The **student side is free,
> permanently and by design** — no transaction fee, no escrow, no custody of
> funds (D-004). The paying customer, *if one exists*, is the **institution**
> (a department, library or book bank that funds student book provision). v1
> scope is buy and sell only: direct swap and general reading are cut (D-007).

Three consequences for the instruments, each of which changed a question:

1. **Willingness to pay a platform is no longer a research question.** It is a
   falsified hypothesis (D-006 condition 1). See the T-fee note at §3.2 for
   why I am not spending a single question trying to confirm it.
2. **Willingness to pay the other student became *more* important, not less.**
   With no fee, the only price in the system is buyer-to-seller. If the
   buyer's maximum sits below the seller's minimum, there is no trade at all
   and no payer on any side. Survey Q9/Q10 and interview Q26/Q27 are retained
   for this and nothing else.
3. **Disintermediation stopped being a revenue risk and became an evidence
   risk.** If matched pairs settle silently, BookHop can see no completions;
   an institution cannot be asked to fund a service whose use cannot be shown.
   T3 is rewritten around that.

### 3.1 The four claims

The README §1 thesis — "find a relevant book nearby, trust the listing,
complete a convenient handover" — is directionally fine and **not falsifiable
as written**. It names no user, no behaviour, and no observable that would
prove it wrong. Below it is split into four claims that can each be killed.
T1 and T2 are load-bearing: **if either fails, BookHop as scoped does not
work.**

**Standard every threshold below must meet (new in v0.2).** Each one states
(a) the number, (b) *why that number and not a neighbouring one*, (c) the
denominator it is measured on and the minimum denominator below which the
test is void, and (d) **one sentence describing a realistic result that would
trip it.** A threshold without (d) is decoration — if no plausible world
fails it, it is not a test.

> ### T1 — SUPPLY (the easier claim) · *bar raised in v0.2 per O-8*
> We believe a **2nd/3rd-year Chennai undergraduate who owns 3+ books they
> have finished with** will **list at least one and complete an on-campus
> handover with a stranger from their own campus within 14 days**, because the
> book is dead weight they would otherwise keep or give away, and Rs 150–400
> for it is free money.
>
> **We will know we are wrong if ANY of the following:**
>
> **T1a — listing.** Fewer than **60%** of students who create an account in a
> seeded one-campus pilot list a book within 14 days.
> *Why 60% and not the 40% in v0.1.* O-8 is right that 40% was incoherent with
> Finance's base `activation_rate` of 0.30 (registered users completing at
> least one transfer): 0.30 ÷ 0.40 implies a **75%** list-to-completed-transfer
> conversion in a cold-start two-sided market with no inventory, which nobody
> would defend if the two numbers lived in the same document. At 60% the
> implied conversion is **50%**, still generous for a cold start but no longer
> absurd. I resolved it by raising my own bar rather than asking Finance to cut
> activation, because listing is unambiguously the easier act and the number I
> own is the one that was too low. **The alternative resolution, for Finance to
> take or reject in one place:** hold T1a at 40% and drop base activation to
> **0.18**, which yields the same 45–50% conversion. *These two documents cannot
> both keep their current numbers.*
> **This bar is conditional on the recruitment method.** 60% assumes *seeded*
> registration — a human asked this person, face to face, to list a book, and
> they said yes and created an account. For an open self-serve signup 60% would
> be indefensible; v1 has no self-serve signup, because D-006 condition 3
> forbids code until Test 1 reports.
> **Realistic result that trips it:** 50 students sign up at the library-gate
> table over a fortnight, 22 of them put up a listing, and the rest say they
> will do it "after the exam" — 44%, and T1a fails.
>
> **T1b — seller reliability.** More than **25%** of accepted offers are
> cancelled by the seller before handover. *Why 25%:* at the ≥30 matches Test 1
> requires, 25% is 7–8 cancellations, which is large enough to be distinguished
> from noise at that n and small enough that a product could not route around
> it. Below ~15% it would be indistinguishable from chance at n=30.
> **Realistic result that trips it:** of 30 accepted offers, 9 sellers stop
> replying once the buyer names a meeting time, because agreeing cost them
> nothing and showing up costs them a walk across campus.
>
> **T1c — the behaviour exists at all.** Fewer than **6 of 18** interview
> respondents can name a specific past occasion when they tried to **convert a
> book into money**, or deliberately routed one to **someone they did not
> already know**. *Why this wording and this number:* v0.1 said "tried to sell
> or pass one on", and "pass one on" includes giving a book to a junior you
> know — which almost everyone does, so that limb could not fail. The clause
> that matters for a stranger-matching product is the stranger clause, and it
> is now the only clause. 6 of 18 is one-third: below that, the stranger
> transfer is not a latent behaviour we are making easier, it is a behaviour we
> are asking students to start.
> **Realistic result that trips it:** 14 of 18 describe giving books to juniors
> and roommates, 3 have sold a phone or cycle to a stranger, and only 4 have
> ever tried to move a *book* to someone outside their own circle.

> ### T2 — DEMAND (the claim most likely to kill us) · *split in v0.2 per O-6*
> We believe a student who needs a prescribed textbook will **pay Rs 150–250
> for a used physical copy from another student on campus** rather than take a
> free PDF or a Rs 60–200 partial photocopy, **only when** they need the whole
> book across a whole semester (core subject, lab/drawing work, or long-form
> reading).
>
> **The O-6 problem, stated plainly.** In v0.1 this was one threshold — 6 of 18
> interviews — measured on a sample the §4.1 screener admitted if
> `S2 ≥ 2 AND (S4 ≥ 1 OR S3 involves paying money)`. One limb of that screener
> *is T2's numerator*. Up to 12 of 18 could be admitted for satisfying the
> thing being tested. Red Team is right, and it was the worst defect in v0.1.
>
> **What I changed, and why both ends rather than one.** The screener is fixed
> **and** the threshold moves. The screener fix alone is not enough: even a
> clean 18 is too small to carry a *population prevalence* claim, and T2 is a
> prevalence claim — it asks what fraction of a campus has the whole-book need.
> So the population claim moves to the survey, where n ≥ 120 can actually
> estimate a proportion, and the interviews keep the part they are good at:
> whether the behaviour exists in a concrete, describable form, and what
> triggers it. **The honest answer to Red Team's question is yes — T2's
> load-bearing limb must be measured on the survey, not the interviews.**
>
> **T2a — PREVALENCE (primary; survey, n ≥ 120).** T2 fails if fewer than
> **30%** of survey respondents report (Q3) that their **last** course-book
> acquisition was a whole physical copy they paid for — "bought new" or
> "bought used".
> *Why 30% and not v0.1's 25%.* The number is derived from the pilot's own pass
> bar rather than picked for plausibility. Test 1 must produce ≥ 30 completed
> handovers in 14 days at one campus. A seeded fortnight plausibly reaches
> ~300 registrations `[G]`, so ~10% of registrants must complete a paid
> whole-book transfer. But a transfer needs the *right title in the right
> edition held by someone on the same small campus in the same fortnight*; at
> best perhaps one wanted title in three is matchable under those constraints
> `[G]`. 10% ÷ (1/3) ≈ **30%** of the population needing a paid whole book.
> The 1-in-3 matching factor is a pure guess and I am tagging it as one — but
> note the decision does not turn on 25 vs 30. It turns on whether the answer
> is near 30% or near the 10–15% the counter-persona in §1.3 implies, and those
> two worlds are far apart.
> **Decision rule, pre-registered, because this is where studies cheat.** The
> comparison is against the **95% confidence interval**, not the point
> estimate. At n = 120 a point estimate of 30% carries a CI of roughly
> ±8pp. If the CI straddles 30%, the result is **INCONCLUSIVE and must be
> reported as inconclusive** — not rounded toward whichever side the company
> prefers that week. This is the R-15 failure mode and it is the most likely
> way this study produces a wrong answer.
> **Realistic result that trips it:** 142 responses come back, 19% say their
> last course book was one they bought, 44% say PDF, 26% say photocopy — CI
> runs 13–25%, entirely below the bar, and T2a fails cleanly.
>
> **T2b — MECHANISM (secondary; interviews, denominator 12).** T2's interview
> limb fails if fewer than **6 of the 12 screened-in respondents** describe a
> *specific past instance* in the last 12 months where they paid their own
> money for a whole physical book they could have photocopied or PDF'd.
> *Note the number did not change — 6. What changed is what it is measured on,
> and that is the entire point of O-6.* The 12 are now recruited on
> `S2 ≥ 2 AND S4 ≥ 1` with **no payment limb** (§4.1), so none of them is
> admitted for satisfying the numerator. The denominator is 12, not 18, because
> the other 6 are deliberately selected *against* the behaviour and including
> them would contaminate the measure in the opposite direction.
> *Why 6 of 12 (50%) when T2a is 30%.* They measure different things and are
> consistent. T2a asks whether the **last** acquisition was paid; T2b asks
> whether **any** of roughly 4–8 acquisitions in a year was. If acquisitions
> were independent draws at 30%, the any-in-a-year rate would be ~80%; because
> this behaviour is strongly person-clustered — Vignesh never pays, the buyer
> always does — the true rate sits somewhere between 30% and 80%. 50% is the
> midpoint. Below it, paid whole-book acquisition is the habit of a minority of
> students rather than a common event, which is the Vignesh world.
> **Minimum denominator:** the limb is void below 10 screened-in interviews.
> **Realistic result that trips it:** 12 clean interviews produce 4 students
> who bought a book with their own money in the last year; the other 8 describe
> a Drive folder, a senior, and the shop at the gate.
>
> **T2c — CONTAMINATION DIAGNOSTIC (the 6 counter-persona respondents).** If
> **3 or more of the 6** counter-persona respondents describe a specific past
> paid whole-book purchase, the screener is not separating the two personas and
> **both T2a and T2b must be re-read as contaminated** before anything is
> concluded from them.
> *Where I disagree with Red Team, and why.* O-6 proposed making the
> counter-persona a **kill limb** — "at least 2 of the 6 counter-persona
> respondents describe one" — as a required condition for T2 to pass. I am not
> adopting that form. The counter-persona is *defined* as the student who has
> never paid for a course book; requiring 2 of them to have paid is requiring
> the recruitment to have failed in order for the thesis to pass, which makes a
> recruitment defect look like a finding. The same observation is genuinely
> valuable, but it diagnoses the **instrument**, not the market, and it belongs
> above the thresholds rather than inside them. A second defect in the proposed
> form, and the reason I rebuilt the denominators rather than adopting the
> wording: O-6's limb (i) — "6 of the 12 where the pay-money limb was not what
> admitted them" — has a floating denominator. If 10 of 12 happened to be
> admitted via that limb, only 2 respondents are eligible for the numerator and
> "6 of 12" becomes arithmetically impossible, i.e. the test flips from
> unfailable to auto-failing. Deleting the limb from the screener removes the
> problem at the source.
> **Still logged either way:** §4.1 records which limb admitted each respondent
> at booking. It costs one field and it is the only way to audit this later.

> ### T3 — DISINTERMEDIATION AT THE INSPECTION MOMENT (R-02 + O-10) · *rewritten in v0.2*
> We believe that when a buyer and seller meet on campus and the buyer
> **inspects the book before paying**, they will still complete and record the
> transfer through BookHop rather than settling quietly and going dark,
> because the platform costs them nothing and the record is what earns them
> the next match.
>
> **Why this is a different claim from v0.1's.** O-10 established that
> inspect-before-pay *is* the disintermediation event: Compliance requires that
> moment to exist because BookHop holds no money and cannot refund; the revenue
> model required payment *not* to happen at that moment. v0.1's T3 asked about
> a general disposition ("would you just WhatsApp the same person next time") —
> the wrong object, and the wrong moment. The new T3 probes **those thirty
> seconds**: buyer holding the book, seller in front of them, UPI open.
>
> **Why the consequence changed too.** The student side is free now, so
> defection costs BookHop no revenue. What it costs is the **completion
> record** — and the institutional-payer hypothesis cannot survive without one.
> No department funds a service it cannot see being used.
>
> **The three leniencies in v0.1, each removed.** *Unprompted* — gone; the
> question is asked directly, because volunteering a specific behavioural
> intention rarely reaches any threshold and v0.1 effectively required it to
> reach 50%. *Conjunctive* — gone; the "cannot articulate why" limb let an
> articulate defector count as a pass. *Hypothetical* — gone, and this is the
> real fix: v0.1's T3 asked about a future intention, which §4.9 of this same
> document bans. The new limb is measured **past-tense on a second-hand
> transaction the respondent has already completed** (Q20a–Q20c, §4.5).
>
> **T3 kill threshold (interviews).** Among respondents who describe at least
> one in-person second-hand transaction that was **arranged through a platform,
> app, or group** — any platform, not BookHop — T3 is falsified if **more than
> 50%** report that the platform never learned the deal closed: numbers were
> exchanged and the conversation moved off it, or the listing was deleted,
> left live, or silently marked gone.
> *Why 50% is acceptable here when I argued against it above.* The v0.1 defect
> was never the number — it was three leniencies stacked under it, each of
> which independently drove the achievable maximum far below 50%. Stripped of
> all three, this is a plain majority-of-observed-behaviour bar on a past
> event, and my honest prior is that **it trips**. Pre-registering a threshold
> you expect to fail is the discipline, not a flaw in it.
> **Denominator:** respondents with such a transaction, expected 12–15 of 18.
> **The limb is void below 8** — if fewer than 8 of 18 have ever transacted
> second-hand with a stranger through any channel, that is itself the finding
> (report it against T1c) and T3 cannot be evaluated on this sample.
> **Realistic result that trips it:** of 13 respondents who bought or sold
> something on OLX or in a college group, 10 say the first message was "send
> your number", everything after happened on WhatsApp, and the listing is still
> sitting there marked available.
>
> **Behavioural confirmation, not ours to run.** The decisive measure is
> Test 1's: of matched pairs, how many report completion in-app within 72
> hours. **That bar should be ~60%, not Red Team's 40%** — O-7 set 40% for the
> *fee* arm, where defection saves the student money. In a free arm defection
> saves nothing, so 40% would be uninformative; if 4 in 10 pairs go dark even
> when reporting is costless, there is no observable completion to sell an
> institution. Flagged to `red-team` and `ceo-planning` as an amendment to
> Test 1; Test 1 is not my instrument and I am not editing it here.

> ### T4 — TIMING / ANTIPHASE (R-04) · *retired and replaced in v0.2 per O-8 and O-9*
>
> **What v0.1's T4 said, and why it is gone.** It claimed general
> (non-syllabus) reading would sustain ≥30% of off-peak handovers. O-8 part two
> asked for it to be restated in **cash GMV** rather than count, because
> engineering books fetch Rs 20–100 to a seller and novels Rs 5–20, so T4 could
> pass on volume while contributing nothing. **That objection is correct and I
> am declining the fix anyway.** D-007 — decided after the memo was written —
> cut general reading from v1 entirely. Re-denominating a threshold pointed at
> a feature that does not ship would be polishing an instrument nobody will
> read. The GMV-vs-count discipline itself is right and is recorded in §5 as a
> standing rule for any future seasonality metric.
>
> **What replaces it.** R-04 is still live, so T4's slot now carries the
> question that actually drives the revenue model: O-9's antiphase assumption,
> which `COMPETITORS.md` §5.2 flags as having **no source** while `MODEL.md`
> §7/§10 treats it as a structural kill requiring storage or credits.
>
> We believe the gap between the week a cohort **disposes of** last semester's
> books and the week the next cohort **needs** them is short enough that a
> listing survives it — a pre-order with a reminder, not an inventory business
> with working capital and shrinkage.
>
> **T4 kill threshold (interviews, Q17a–Q17c, denominator 18, void below 12).**
> Antiphase is confirmed as **structural**, and T4 fails, if the **median gap
> between a respondent's disposal week and the next cohort's acquisition week
> exceeds 10 weeks**; **or** if more than **half** of respondents report that
> the book they disposed of was already gone — sold, given, binned, lost —
> before the next need window opened, in which case the gap length is moot
> because nothing survives it.
> *Why 10 weeks.* Taken from O-9, and derived from `COMPETITORS.md` §5.2's own
> cited academic calendar rather than invented: even semester ends ~May/June
> and odd starts ~July/August, a gap of roughly **6–8 weeks**; odd ends
> ~December and even starts in January, roughly **2–4 weeks**. 10 weeks sits
> just outside the worst case the calendar itself produces, so exceeding it
> means the observed behaviour is worse than the calendar explains — which is
> the only thing that would justify `MODEL.md`'s storage-or-credits conclusion.
> **Refutation bar, also pre-registered:** a median under **6 weeks** refutes
> antiphase as a structural problem, and `MODEL.md`'s structural objection #3
> and its "8 trading weeks a year" compression must then be restated.
> **Realistic result that trips it:** respondents consistently clear their
> shelves in the week they finish final exams in May, the junior cohort does
> not start looking until the second or third week of August, and 11 of 18 say
> last year's books went to raddi or a cousin long before anyone asked.

### 3.2 The fee question, and why no instrument here tests it

D-006 condition 1 records the 6% transaction fee as **falsified**, on O-10 —
a structural contradiction that no driver value resolves. My command asked me
to keep only what is needed to confirm that falsification cheaply.

**My answer is: nothing in this document, and here is the reasoning.** A
stated-preference question cannot confirm or overturn a structural
falsification. Asking "would you have paid a small platform fee" invites the
agreeable answer §4.9 exists to prevent, and a yes would prove nothing while
a no would prove something already decided. The only instrument that can move
this is Test 1's fee-vs-free A/B, which measures `fee-paid ÷ fee-asked`
against real money at the real moment, and that is Red Team's to run.

**What this document contributes instead, at zero incremental minutes:** Q20c
in §4.5 records, past-tense, whether the respondent has **ever** paid a
platform any money on a second-hand transaction they completed in person, and
whether they knew about it before they met. That is a behavioural datapoint
about fee salience, folded into a story they are already telling. It is worth
one line. It is not worth a section.

### 3.3 Scoring map — which question produces which threshold

Pre-registered with the thresholds, because a threshold whose data source is
decided after the data arrives is not pre-registered either.

| Threshold | Instrument | Scored from | Denominator | Void below |
|---|---|---|---|---|
| **T1a** listing ≥60% | Test 1 (not this document) | pilot registration and listing log | account creators | 30 creators |
| **T1b** seller cancels ≤25% | Test 1 (not this document) | pilot match log | accepted offers | 20 offers |
| **T1c** stranger transfer ≥6 | Interview | Q15 (tried to sell) + Q18 (last second-hand transaction), coded for *book* and *outside own circle* | all 18 | 14 |
| **T2a** paid whole book ≥30% | **Survey (primary)** | Q3, options "Bought new" + "Bought used", against the 95% CI | all completed responses | 120 |
| **T2b** ≥6 of 12 | Interview | Q3–Q5 and Q9 — a named book, a rupee amount, and the respondent's own money, within 12 months | the 12 `MAIN` respondents | 10 |
| **T2c** contamination <3 of 6 | Interview | same coding as T2b | the 6 `COUNTER` respondents | 5 |
| **T3** platform-never-knew ≤50% | Interview | Q20a–Q20c, coded `PLATFORM KNEW` / `PLATFORM NEVER KNEW` | respondents with a platform- or group-arranged in-person transaction | 8 |
| **T3** behavioural confirmation | Test 1 (not this document) | in-app completion within 72h of a match | matched pairs | 30 |
| **T4** median gap ≤10 weeks | Interview | Q17a (disposal week) and Q17b (acquisition week) | all 18 | 12 |
| **§4.10** budget line ≥1 of 3 | Budget-holder probe | L2 and L3 — a named line **and** a named approver | 3 budget-holders | 3 |

**Thresholds above are `[G]`/`[R]`, not sourced.** They are deliberately
written as numbers so Red Team can argue them down or up *before* data
arrives, rather than after. **They are now locked** — see the VALIDATION
STATUS banner.

**Thesis revision this forces on README §1:** "find a relevant book nearby"
is wrong as a wedge. The wedge is narrower: **the whole-book, whole-semester
need, where the photocopy shop and the PDF both fail** — and the payer, if
any, is the institution rather than the student. Recommend `ceo-planning`
update §1 to the §3.0 wording.

---

## 4. Interview script — 45 minutes, ready to run

**Use as written.** Behavioural, past-tense. Do not add questions. Do not
improve the wording in the room.

**Materials:** phone voice recorder (only with consent), printed consent slip,
notepad. **No BookHop branding, no mockups, no logo in the room.** The
respondent must not know what we want to hear until §4.7.

**Time budget — 45 minutes, unchanged in total, reallocated inside.**

| § | Block | v0.1 | v0.2 |
|---|---|---:|---:|
| 4.2 | Opening | 3 | 3 |
| 4.3 | Acquisition — the last time | 12 | 12 |
| 4.4 | Disposal **and timing (O-9)** | 8 | **10** |
| 4.5 | Channels, trust **and the inspection moment (O-7/O-10)** | 8 | **10** |
| 4.6 | ~~General reading~~ → **Institutional provision** | 4 | **4** |
| 4.7 | ~~WTP and disintermediation~~ → **The price between the two students** | 6 | **4** |
| 4.8 | Close | 2 | 2 |
| | **Total** | **43** | **45** |

**Interviewer rules**
- Ask about the **last time**, never about "usually" or "would you".
- After any answer, ask "what happened next?" until the story ends.
- Silence is a tool. Count to five before filling it.
- Never explain the product before Q26 (§4.7).
- If the respondent asks "are you building an app?" — "I'll tell you at the
  end, I don't want to bias your answers." Then actually tell them.
- Record **behaviour and amounts**, not opinions. "It's expensive" is not
  data; "I paid Rs 480 in July" is data.

---

#### 4.1 Screener (ask before booking — 2 minutes, by phone or in person)

- S1. What course and which year are you in?
- S2. In the last 12 months, how many times have you got hold of a book for
  your course — any way at all, bought, borrowed, copied, downloaded?
- S3. How did you get the most recent one?
- S4. Do you have any books at home from last semester that you have finished
  with? Roughly how many?
- S5. Who pays for your course books — you, from your own money, or someone
  else?
- S6. Are you 18 or over? *(Hard gate — see §6.5. Under 18, thank and stop.)*

> **CHANGED IN v0.2 — do not restore the old rule.** The previous inclusion
> rule was `S2 ≥ 2 AND (S4 ≥ 1 OR S3 involves paying money)`. The second limb
> admitted respondents *for having paid for a book*, which is the exact
> behaviour T2 measures, so T2 was reachable by selection alone (Red Team O-6).
> **The pay-money limb is deleted.**

**MAIN SAMPLE — include 12 if:** `S2 ≥ 2` **AND** `S4 ≥ 1`.
Both limbs are now about *handling* and *holding* books. Neither is about
paying for one. S3 and S5 are still **asked and recorded**, but they do
**not** decide admission.

**COUNTER-PERSONA SAMPLE — recruit 6 separately, on a positive profile:**
`S3` shows their most recent course book was a **PDF or a photocopy**, **AND**
`S5` shows they have **never paid their own money** for a course book. This
is Vignesh (§1.3), recruited deliberately rather than by screener failure —
with the pay-money limb gone, a Vignesh can pass the main screener, so
"whoever fails" is no longer a definition.

**Booking log — one field, mandatory, fill it at booking, not after.**
For every respondent record: `MAIN` or `COUNTER`; the value of S3 and S5; and
which limb(s) they satisfied. Without this field the T2c contamination
diagnostic in §3 cannot be computed and neither T2b nor T2a can be audited.
A sample of only people who already buy and hoard books will tell us we are
right. See §6.4.

---

#### 4.2 Opening (3 min)

Read aloud:

> Thanks for the time. I'm doing research on how students at your college get
> hold of books. There are no right answers and I'm not selling anything
> today. I'd like to record audio so I don't have to write while you talk —
> only I will hear it, it will be deleted within 90 days, and I will not use
> your name anywhere. You can stop or skip anything, and you can ask me to
> delete the recording afterwards. Is recording OK?

- Q1. Tell me what you're studying and what a normal week looks like for you.
- Q2. Which subjects this semester need a book?

---

#### 4.3 Acquisition — the last time (12 min)

- Q3. Think about the most recent book you needed for your course. What was
  the book?
- Q4. Walk me through how you got it — start from the moment you found out you
  needed it.
  *(Probe at every step: who did you ask, where did you go, how long did it
  take, what did it cost?)*
- Q5. What did that cost you in rupees, exactly?
- Q6. How long was it between realising you needed it and actually having it?
- Q7. What else did you consider before that, and why didn't you do it?
- Q8. Was there a point in that where you nearly gave up? What happened?
- Q9. Whose money paid for it, and did you have to ask anyone?
- Q10. Now think of a time you needed a book and **never got it.** What
  happened instead — how did you manage the subject?
- Q11. In the last year, how many of your course books have you got as a
  photocopy, and how many as a PDF? What did each of those cost you?

---

#### 4.4 Disposal and timing — the last semester end (10 min)

*v0.2: old Q14 (the gift-to-a-junior narrative) is **cut**. Gift share moves
the unit economics by Rs 0.56 across its entire range (Red Team O-3), and the
one thing we still need from it — does disposal happen at all — is covered by
Q13, Q15 and survey Q7. The recovered minutes fund Q17a–Q17c below, which
carry T4.*

- Q12. Where are last semester's books right now? Physically, where?
- Q13. What happened to the books from the semester before that?
- Q15. Have you ever tried to sell a book? What happened?
  *(If never: "What stopped you?" — then stop, do not sell them the idea.)*
- Q16. If I came to your room right now, roughly how many books would be
  sitting there that you're done with?

**Timing — added in v0.2, carries T4 (§3). Ask all three. Get months and
weeks, not "around then".**

- Q17a. The books from last year you no longer have — **when** did you get rid
  of them? Which month, and what was going on at the time — exams, moving
  rooms, going home?
  *(Push for a week if you can get one. "Right after last paper" is a usable
  answer; "sometime in the summer" is not — ask what else was happening that
  week.)*
- Q17b. The books you needed for **this** semester — when did you actually get
  each one? Which week of term? Was that before classes started, in the first
  week, or later?
- Q17c. Think about the last book you got rid of. How long had it been sitting
  there since the last time you actually opened it?

> **Why these three and not a question about seasonality.** T4 needs two
> dated events per respondent — a disposal week and an acquisition week — so
> the gap can be computed across the sample. Asking "is there a gap between
> when students sell and when students buy?" would get a theory. Q17a and Q17b
> get two dates. Q17c tests whether a listing could have survived the gap at
> all, which is the half of T4 that `MODEL.md`'s storage-or-credits conclusion
> actually turns on.

---

#### 4.5 Channels, trust, and the inspection moment (10 min)

- Q18. Tell me about the last thing you bought or sold second-hand — anything,
  not just a book. Phone, cycle, calculator, anything.
- Q19. How did you find the other person, and how did you decide they were
  OK to deal with?
- Q20. Where did you meet them and what time of day?

**The inspection moment — added in v0.2, carries T3 (§3).** Red Team O-10
established that inspect-before-pay *is* the disintermediation event. These
three questions walk the respondent through those thirty seconds of a
transaction they have **already completed**. No hypothetical, no BookHop.

> **Interviewer note — this is the most important block in the script and the
> easiest to fumble.** Do not summarise. Make them narrate it in real time. If
> they jump to the end ("yeah I bought it"), go back: *"wait — take me back to
> the moment you first had it in your hand."*
> **Skip this block only if Q18 produced no in-person second-hand
> transaction.** Record the skip — the T3 denominator depends on it.

- Q20a. Go back to the moment you two actually met. You've got the [item] in
  your hand. Walk me through what happened from then until the money moved —
  what did you look at, what did you say, who paid first?
- Q20b. You said you found them through [whatever they said at Q19]. After
  that very first message, where did the rest of the conversation happen —
  did it stay there, or move somewhere else?
  *(Probe, neutrally, without naming the behaviour: "So once you had their
  number, did you go back to the app at all?" Do not say "disintermediation",
  "cut out" or "avoid" — those words supply the frame.)*
- Q20c. After it was done — did you do anything on that app or in that group?
  Did you delete the post, mark it sold, leave it up, anything? *(Then:)* Did
  that app or site take any money from you for it? Did you know whether it
  would, before you met?

> **What to record against T3, verbatim where possible.** For each respondent
> with a platform- or group-arranged in-person transaction, one of:
> `PLATFORM KNEW` (marked sold, completed in-app, or the platform otherwise
> registered the outcome) / `PLATFORM NEVER KNEW` (numbers exchanged and the
> conversation moved off, or the listing was deleted, left live, or silently
> abandoned) / `NO SUCH TRANSACTION`.
> Q20c's second half also answers §3.2 — whether a platform fee is even
> salient to a student at the moment of paying.

- Q21. Was there a moment in that where you felt uncomfortable? What was it?
- Q22. Which WhatsApp or Telegram groups do you have for your class or
  college? What actually gets posted in them?
  *(Ask to see the group list on their phone if they offer. Do not ask to see
  message contents.)*

---

#### 4.6 Institutional provision — does anyone already do this job? (4 min)

*v0.2 replaces the old general-reading question here (old Q22, cut). General
reading is out of v1 (D-007), so measuring it would be measuring a feature
that does not ship. The four minutes go to the hypothesis that replaced the
transaction fee: **the institution as payer.** These questions test it from
the student side; §4.10 tests it from the budget-holder's side. Both are
needed — a librarian will describe the book bank that exists on paper, a
student will describe the one that works.*

- Q23. Has your department, or the college library, ever given you a book,
  lent you one for a whole semester, or arranged one for you? Tell me about
  the last time.
  *(Probe: which book, which semester, how long did you keep it, did you pay
  a deposit, did you get the edition you actually needed?)*
- Q24. Is there a book bank, or a set of department books, in your
  department? Have you used it? Walk me through the last time — what did you
  have to do, who did you ask, and did you get the book?
  *(If they have never used it: "How do you know about it?" — a book bank
  everyone has heard of and nobody has used is a finding.)*
- Q25. Has anyone at your college — a department, a club, a staff member, a
  senior batch — ever collected books from students at the end of a year?
  What happened to them?

> **Why these three.** The institutional-payer hypothesis (§3.0) is currently
> supported by nothing — Red Team O-12 found zero sources in any Phase A
> document about Indian college book provision. The cheapest student-side test
> is whether the institution is **already** in this loop, and with what
> result. Two outcomes are both informative: if departments already lend books
> effectively, BookHop is competing with a free incumbent (§2.2(d)); if the
> book bank is a cupboard nobody can open, there is a job going undone and
> possibly a budget line already attached to it.
> **All three are past-tense and about a specific occasion.** None asks
> whether the respondent *thinks* the college should buy books — that gets a
> yes from everyone and is banned under §4.9.

---

#### 4.7 The price between the two students (4 min)

*v0.2: this section was "willingness to pay and disintermediation" and ran 6
minutes. Disintermediation moved to §4.5, where it is measured past-tense on
a real transaction instead of as an intention. What is left here is the one
thing that still matters: **the price between the two students.** The student
pays BookHop nothing (§3.0), so the only price in the system is buyer-to-
seller, and if the buyer's maximum sits below the seller's minimum there is no
trade for anyone to intermediate. Old Q24's deep probe is cut per O-3 —
ask it once, write the number, move on.*

Only now describe the concept, in one neutral sentence:

> Some students are putting their finished books on a notice board where
> another student at the same college can see what's available and arrange to
> meet on campus and hand it over. It's free to use.

*(Say "it's free to use" exactly as written and do not elaborate. It is now a
fact about the product, and leaving it out would make Q26 price a product we
are not building. Do not mention fees, apps, or BookHop.)*

- Q26. You just told me about [the book from Q3]. If another student on your
  campus had that exact book, same edition, used, and you could collect it at
  the library gate tomorrow — what would you have paid for it?
  *(Write the number. Then:)* How did you arrive at that number?
- Q27. And for [a book from Q12] that you're done with — what's the smallest
  amount that would make it worth handing it to a stranger on campus?
  *(One number. Do not probe further — O-3.)*
- Q28. What would make you not do it at all?

> **Q26 is the one hypothetical this script retains, and it is deliberate.**
> §4.9 bans hypotheticals because they invite agreeable answers. Q26 survives
> because it is anchored on a **specific book the respondent already told us
> they needed and already told us what they paid for** (Q3–Q5), which makes it
> a counterfactual about a real event rather than a fantasy about a product.
> Its number is still weaker evidence than Q5's and must be reported
> separately, never averaged with it.
> **The spread between Q26 and Q27 is the market.** If Q27 > Q26 across the
> sample, there is no trade. Survey Q9/Q10 measure the same spread at n ≥ 120
> and are the primary read; these two are the texture.

---

#### 4.8 Close (2 min)

- Q29. Is there anything about getting books I should have asked and didn't?
- Q30. Who else at your college should I talk to, especially anyone who'd
  think this is a bad idea?

Thank them, hand the incentive (§6.3), confirm the consent slip is signed,
confirm they know how to ask for deletion.

---

#### 4.9 Questions we deliberately DO NOT ask — and why

These were drafted, **flagged as leading, and removed**. They must not be
reinstated.

| Rejected question | Why it is removed |
|---|---|
| "Would you use an app that helps you buy used books on campus?" | Hypothetical and agreeable. Everyone says yes. Predicts nothing. |
| "Don't you find it frustrating that textbooks are so expensive?" | Supplies the emotion we want to hear. Leading. |
| "How important is trust when buying from a stranger?" | Nobody answers "not important". Zero information. |
| "Would you prefer swapping a book to paying cash?" | Forces a preference between two things we invented. |
| "Would you pay Rs 200 for a used textbook?" | A price we name becomes the anchor. Q26 makes *them* say the number first. |
| "How often do you usually buy books?" | "Usually" invites a self-flattering average. Q3 asks about one real event. |
| "What features would you want in a book app?" | Users do not design products, and the answer is always a feature list we then feel obliged to build. |
| "Is piracy a problem for students?" | Moralising frame; invites the socially correct answer. Q11 asks what they actually did. |
| "Would you feel safe meeting on campus?" | Leads to "yes". Q20/Q21 get the real behaviour from a past meeting. |

**Added in v0.2.** Every question introduced in this revision was run against
the same three tests — behavioural, past-tense, non-leading. Four drafts
failed and were removed before they reached the script. Recorded here so they
are not re-added by someone who thinks they were overlooked:

| Rejected in v0.2 | Why it is removed |
|---|---|
| "Would you still use it if the platform took a small cut?" | The thing it tests is already falsified (D-006, §3.2), and a stated-preference answer cannot confirm a structural falsification. Q20c instead records, past-tense, whether they have ever actually paid a platform anything. |
| "Do you think your college should provide textbooks?" | Universally agreeable, zero information, and it hands the institutional-payer hypothesis the answer it wants. §4.6's Q23/Q24/Q25 ask what the college has actually done instead. |
| "Would you report the sale in the app, or just deal directly?" | A hypothetical about future honesty, which is the exact defect O-7 found in v0.1's T3. Q20a–Q20c get the same behaviour from a transaction they already completed. |
| "How long do you think there is between students selling and students buying?" | Asks the respondent to theorise about a population. Q17a/Q17b get two dates from one person and let us compute the gap ourselves. |

---

#### 4.10 Librarian / budget-holder probe — 20 minutes, separate conversation

**New in v0.2.** §6.2 already requires one college librarian per campus. Red
Team O-12 asks for four questions to be added to that conversation, because
the institutional-payer hypothesis — now the only payer hypothesis in the
thesis (§3.0) — rests on **zero sources** across the entire Phase A set. This
is a Rs 0 test inside recruitment that already exists.

**Who.** The person who actually controls, or can name who controls, book
spending: a college librarian, a departmental HoD, or a book-bank custodian.
One per campus, three total. Not a student.

**Framing, read aloud.** *"I'm researching how students at Chennai colleges
get hold of their textbooks. I'd like to understand it from your side — what
the library and the department actually do. I'm not selling anything."*

- L1. When an edition changes and the prescribed book is superseded — what
  happens to the copies you're holding of the old edition? Tell me about the
  last time that happened.
- L2. Is there a book bank here, or any scheme that puts books in students'
  hands for a semester? Who funds it, and from which line in the budget?
  *(If yes: how many students used it last year, and how do you know?)*
- L3. When was the last time this department or library bought used books
  rather than new? What happened — who proposed it, who signed it off?
  *(If never: who would have to sign it off if someone proposed it?)*
- L4. If someone offered you 200 used copies of a prescribed title at 40% of
  MRP, what would happen next — who do you go to, and how long would it take?

> **L4 is a hypothetical and I am keeping it anyway, with the reason stated.**
> §4.9 bans hypotheticals because they produce agreeable answers from people
> with nothing at stake. L4 is different in one respect that matters: it is
> not asking whether the respondent *likes* the idea, it is asking them to
> **trace an approval chain**, and the chain either exists or it does not.
> L3 asks the past-tense version first, deliberately, so that L4's answer can
> be read against a real precedent. **Record L4's answer as stated intent,
> never as evidence of demand**, and report the approval chain separately
> from the willingness.

> **Pre-registered threshold (O-12, adopted as written).** If **zero of three**
> budget-holders can name both a **budget line** and an **approver** for
> student book provision, the institutional-payer hypothesis in §3.0 is dead
> and must be withdrawn or re-evidenced before it reaches the founder again.
> **Realistic result that trips it:** all three say books come out of a
> general library grant they do not control, the Principal signs everything,
> and no one has bought a used book in living memory.

---

## 5. Survey — 12 questions, under 4 minutes on a phone

**Format:** one question per screen, radio buttons except where noted, every
question skippable except Q1. No open text except Q12 (optional). Mobile-first.

**Decision mapping is mandatory.** Any question that does not name a decision
below is deleted. None were kept on "nice to know".

> **CHANGED IN v0.2.** The survey is now the **primary** instrument for T2 —
> O-6 showed the interview sample cannot carry a population claim, and n ≥ 120
> can. Q3 is no longer "the single most important question in the study"
> informally; it **is** the T2a kill threshold (§3), and its result is read
> against a confidence interval, not a point estimate. Q11 was swapped: the
> phone/data question informed a CTO performance budget, and D-006 condition 3
> forbids code until Test 1 reports, so it is premature. Its slot now tests
> the institutional-payer hypothesis. Survey length is unchanged at 12.

| # | Question | Options | Decision it informs |
|---|---|---|---|
| **Q1** | Which college are you at? | *[list of the 3 pilot campuses]* / Other | Screen-out; campus-level liquidity (R-01) |
| **Q2** | Which year are you in? | 1 / 2 / 3 / 4 / PG | Validates the 2nd–3rd-year persona (§1.1). If buyers are 1st years, the persona changes. |
| **Q3** | The last book you needed for your course — how did you get it? | Bought new / Bought used / Borrowed from a senior or friend / Library or department / Photocopied part of it / Photocopied all of it / Got a PDF / Never got it | **The single most important question in the study, and since v0.2 it carries a kill threshold.** "Bought new" + "Bought used" is the T2a numerator; the bar is **30%**, read against the 95% CI (§3). Also sizes the counter-persona (§1.3). Single-select — do not let this become choose-all, or the denominator for T2a is destroyed. |
| **Q4** | What did that cost you, in rupees? | Rs 0 / under 100 / 100–250 / 250–500 / over 500 | The price BookHop must beat. Feeds R-03 with `market-finance`. |
| **Q5** | How long from "I need this book" to actually having it? | Same day / 2–3 days / about a week / more than a week / never got it | Sets the time-to-match bar in `metrics/METRICS.md`. If the status quo is same-day, our match time must be too. |
| **Q6** | How many finished course books are at your place right now? | 0 / 1–2 / 3–5 / 6–10 / more than 10 | Supply density (R-01). Multiply by campus population for a seeding estimate. |
| **Q7** | What happened to your books from last year? *(choose all)* | Still with me / Gave to a junior or friend / Sold them / Threw away or raddi / Don't know | **Re-pointed in v0.2.** Its decision is now **does disposable supply exist and is it still in reach** (the "Still with me" share), not *what is gift share*. Gift share moves the unit by Rs 0.56 across its entire range (O-3) and is no longer treated as decisive anywhere. Also still tests the §1.1 end-of-semester guess: if "sold" is already high, our supply pitch is weaker than assumed. |
| **Q8** | In the last year, have you bought or sold anything second-hand with someone you didn't already know? | Yes, in person / Yes, delivered / No | Stranger-transaction baseline. Drives handover design and R-06. |
| **Q9** | If a classmate at your campus had the exact book you needed, used and in good condition, what's the most you'd pay **them**? | Nothing, I'd use a PDF / up to Rs 100 / Rs 100–200 / Rs 200–350 / over Rs 350 | **Re-pointed in v0.2 — this is no longer fee research.** The student pays BookHop nothing (§3.0), so this is the **buyer's maximum in the only price that exists**, the one paid to the other student. Feeds R-03 as a trade-existence test, not a take-rate input. Stem reworded to "pay **them**" so the respondent is not pricing a platform. |
| **Q10** | What's the lowest amount that would make it worth handing one of your finished books to a stranger on campus? | I'd give it free / Rs 50 / Rs 100 / Rs 200 / Rs 300+ / I wouldn't | Seller reservation price. **The spread between Q9 and Q10 IS the market, and with no fee it is the whole market.** If the Q10 distribution sits above the Q9 distribution, there is no trade — and no payer on any side, institutional or otherwise. This is the primary read; interview Q26/Q27 are the texture. |
| **Q11** | This semester, did your department or the college library give you, lend you, or arrange any of your books? | No / Borrowed from the library and got it / Tried the library, couldn't get it / Department or book bank lent it / A senior-batch handover the department organised / Don't know | **New in v0.2, replacing the phone/data question.** Sizes the institutional channel from the student side at n ≥ 120 — the hypothesis in §3.0 that currently rests on zero sources (O-12). Pairs with interview §4.6 and the librarian probe §4.10. *Replaced:* "How do you mostly use the internet on your phone?", which informed a CTO payload budget. No code is being written (D-006 condition 3), so that question was premature; re-add it when Phase C opens. |
| **Q12** | *(Optional)* Anything about getting books at your college you'd want to tell us? | Free text, 200 char | Qualitative leads and recruitment for interviews. |

**Deleted during drafting** (recorded so they are not re-added): gender, age,
hostel vs day-scholar, branch, favourite genre, "how satisfied are you with…",
"rate the importance of…". None mapped to a decision we face at G1.
**Deleted in v0.2:** the phone/data question (premature — no code until Test 1
reports) and every framing that asked the respondent to price a platform
rather than price a book.

> **Standing rule adopted from Red Team O-8 part two, even though T4 was
> retired rather than restated.** Any future metric that compares volumes
> across categories of book must be denominated in **cash GMV, not handover
> count**. `COMPETITORS.md` §5.3 prices the two halves of the catalogue an
> order of magnitude apart — engineering books fetch Rs 20–100 to a seller,
> novels Rs 5–20 — so a count-based metric can show health while contributing
> nothing. This rule binds the PRD and `metrics/METRICS.md`, not just this
> document.

**Tamil translation — where it is needed.** The survey ships bilingual, EN and
TA, on the same screen (`design-director` owns the EN/TA copy standard).

- **Must be translated:** every question stem and every option label in Q3,
  Q7, Q8, Q10, Q11, Q12 — these describe informal, social, domestic and
  institutional behaviour where the natural word is Tamil and the English
  phrasing risks a wrong read (notably "raddi" in Q7, which should carry its
  local equivalent; "stranger" in Q8/Q10, where English understates and Tamil
  must not overstate; and **"book bank" in the new Q11, which must carry
  whatever the local institution actually calls it — if the respondent's
  college calls it something else, the English term will read as a thing that
  does not exist there and Q11 will undercount**).
- **Keep English, no translation:** "PDF", college names, and rupee figures —
  translating these makes them *harder* to read for the target respondent
  `[R]`. *(v0.2: "Wi-Fi" and "data pack" dropped from this list with the old
  Q11.)*
- **Needs a native speaker, not machine translation:** Q10's framing of
  "worth your while" has no clean Tamil equivalent and will change meaning if
  translated literally. **Flag to `design-director` as a blocking copy task
  before the survey fields.**

---

## 6. Recruitment plan

### 6.1 Campuses

Three, chosen for *difference*, not convenience — a sample of three similar
colleges measures one college three times.

| Slot | Profile wanted | Why |
|---|---|---|
| A | A large Anna-University-affiliated private engineering college | The core T2 textbook case; Tamil Nadu's college base is heavily private-unaided `[S]` |
| B | An arts & science / commerce college, co-ed, mixed income | Tests whether the thesis survives outside engineering |
| C | A high-selectivity campus (IIT-M, or a top autonomous college) | The *hostile* case: best library, strongest PDF culture, most organised seniors. If BookHop has no value here, we learn the ceiling early. |

Named campuses are the founder's call (§7) — Product specifies the profile,
not the institution.

### 6.2 Sample size — what is actually enough to act on

- **Interviews: 18 total, 6 per campus.** Rationale: thematic saturation in
  behavioural interviews typically arrives in the low teens for a single
  homogeneous segment; three segments need three bites. **Composition:** 12
  recruited on the §4.1 **main** screener (`S2 ≥ 2 AND S4 ≥ 1` — no payment
  limb), **plus 6 recruited on the §4.1 counter-persona profile** (most recent
  course book was a PDF or photocopy, and has never paid their own money for
  a course book). `[R]` — a reasoned research convention, not a sourced rule.
  **The two groups are denominated separately throughout §3** and must not be
  pooled: T2b is measured on the 12, T2c on the 6. Pooling them reintroduces
  O-6 from the other direction.
  *(v0.2 also fixes an internal inconsistency not raised by Red Team: §4.1
  previously said recruit 5 counter-persona respondents while this section
  said 6. It is 6.)*
- **Survey: minimum 120 completed responses, target 180.** Rationale: for a
  single proportion (Q3 — "what fraction of students are the counter-persona")
  at 95% confidence with a ±10 percentage-point margin, the worst-case
  requirement is n ≈ 96; 120 absorbs partial completions, and 180 allows one
  cut by campus at a wider margin `[R]` (standard proportion arithmetic, shown
  so it can be checked).
- **Explicitly NOT enough to act on:** fewer than 60 responses, or responses
  from one campus only. **A result below that bar must be reported as
  inconclusive, not as a signal.** This is the exact failure mode R-15 warns
  about.
- **Also recruit: 3 non-students per the original plan, plus the budget-holder
  upgrade.** One campus-gate photocopy shop owner and one Moore Market /
  used-book seller — they know the volumes we are guessing at, and the
  photocopy shop owner is the best single informant on how much of our
  "market" is already served at Rs 80. **Changed in v0.2: the single
  "librarian" slot becomes three — one budget-holder per campus — and runs the
  §4.10 script.** The institutional payer is now the only payer hypothesis in
  the thesis (§3.0) and it rests on zero sources (O-12); one conversation
  cannot carry it, and three is the minimum at which the pre-registered
  "zero of three" threshold in §4.10 means anything. Cost: Rs 0 — these are
  the same campus visits.

### 6.3 Incentive

- Interview (45 min): **Rs 200** in the respondent's preferred form, handed at
  the end, unconditional on what they said. `[R]` — roughly a canteen meal
  plus travel; low enough not to buy agreement, high enough to respect the
  time. **APPROVED — D-007. Rs 4,500 allocated (18 × Rs 200 + Rs 900
  contingency), Rs 0 spent, inside the Rs 16,500 envelope. No agent may
  exceed it.** The budget-holder conversations (§4.10) carry **no incentive**
  — paying a librarian or an HoD to answer questions about their own budget
  changes what they say, and may not be a thing we can do at all.
- Survey (4 min): **no cash.** A single raffle, or nothing, stated up front.
  Per-response cash on a 4-minute survey buys completions, not truth `[R]`.
- **Never:** free credits, early access, or any BookHop-linked reward. That
  selects for people predisposed to like us and poisons the sample.

### 6.4 Avoiding the only-friendly-respondents trap

The default failure of founder-adjacent research is interviewing people who
want you to succeed. Counter-measures, all mandatory:

1. **Quota the sceptics.** 6 of 18 interviews must be counter-persona
   respondents recruited on the positive profile in §4.1 — most recent course
   book was a PDF or a photocopy, never paid their own money for one.
   *(v0.2: this used to say "people who failed the screener". With the
   pay-money limb deleted to fix O-6, a sceptic can now pass the screener, so
   failure is no longer a usable definition.)*
2. **Q30 recruits adversaries by name** ("who'd think this is a bad idea").
   Those referrals get priority over friendly ones.
3. **No friends, no friends-of-friends, no one from the founder's own
   department or batch.** If a respondent knows anyone on the BookHop side,
   record it and weight the response down in analysis.
4. **Recruit at least a third through a non-social channel** — a table at the
   library entrance or canteen, intercepting people who did not opt in to a
   group post. A WhatsApp-group-only recruit skews the sample toward exactly
   the students who are already well served by WhatsApp groups `[R]`.
5. **The concept is never described before Q26 (§4.7).** Anyone told what we
   are building before that point is excluded from the sample.
6. **Pre-register the kill thresholds.** §3's numbers are written down
   *before* data collection, so they cannot be moved afterwards. **v0.2 is
   the last revision in which they can change at all** — see the VALIDATION
   STATUS banner. Red Team's O-6 to O-9 fixes were available only because no
   interview had been booked; that window closes with the first booking.
7. **Report inconclusive results as inconclusive.** T2a is read against a
   confidence interval (§3). A CI that straddles the bar is not a weak pass.
   This is the R-15 failure mode and it is how an honest study still produces
   a wrong answer.

### 6.5 Consent and data handling

**Status: still BLOCKED pending `privacy-compliance` sign-off, but no longer
for the original reason.** v0.1 said `evidence/COMPLIANCE.md` did not exist.
**It exists now** and Red Team §4 rates it the strongest document in the Phase
A set. What has still not happened is a review *of this section* against it.
The following remains Product's *proposal*, and must be reviewed and signed
off by `privacy-compliance` against DPDP 2025 (R-10) before a single interview
is booked. Two items in v0.2 add new personal-data surface and need explicit
sign-off: the **booking log** in §4.1 (which limb admitted each respondent)
and the **§4.10 budget-holder conversations**, which involve a named
professional rather than an anonymised student.

- Participants must be **18+**, confirmed at the screener (S6). No minors, no
  exceptions.
- **Written consent slip**, one page, EN + TA, signed before recording:
  purpose, what is collected, retention period, deletion right, contact point.
- **Collect:** course, year, campus, behavioural answers, audio (consent only).
  **Do not collect:** full name, roll number, phone number beyond a single
  recontact field, address, photographs, screenshots of their chats.
- **Recontact field is optional and separately ticked**, stored apart from the
  responses.
- **Retention:** audio deleted within 90 days; transcripts anonymised at
  intake (respondent = "A-03"); the name↔code key held in one place and
  destroyed when the study closes.
- **Deletion on request**, honoured within 7 days, with a named contact on the
  consent slip.
- Survey tool must not be one that harvests respondent identity by default.
  Tool choice goes to `privacy-compliance` before the survey fields.

---

## 7. THE FOUNDER ASK — **ANSWERED (D-007), ONE ITEM OUTSTANDING**

> ### Status as of this revision
>
> **D-007 approved all four items.** Budget: **Rs 16,500 total**, of which
> **Rs 4,500** is this document's fieldwork (18 × Rs 200 + Rs 900
> contingency); the remainder funds Test 1 and contingency. **Rs 0 spent.**
> No agent may exceed the envelope or commit further funds.
> Also approved: start incorporation; cut direct swap and general reading from
> v1; run the Rs 0 librarian probe (now §4.10) as a **test only** — the
> institutional direction is not committed.
>
> **STILL OUTSTANDING AND BLOCKING: the three named campus contacts** (item 1
> below). Everything else in §4–§6 is ready to run the day they arrive.
>
> **The expiry that matters.** Red Team's O-6 to O-9 fixes were paper edits
> worth Rs 0, and they were available only because no interview had been
> booked. They are now applied (§0). **No further threshold change is
> available after the first booking.** If any agent or the founder wants to
> argue a number in §3 down or up, now is the only time.
>
> **What this does NOT authorise** (D-007): no code until Test 1 reports, no
> payment provider, no public launch, no campus agreement signed by an agent.

<details>
<summary><strong>Original ask, retained for the record (v0.1)</strong></summary>

> **DECISION NEEDED FROM THE FOUNDER — Phase A research access and budget**
>
> **1. Campus access — 3 named introductions.** I need one named human contact
> at each of three Chennai campuses matching the profiles in §6.1 (A: large
> private engineering college; B: arts & science college; C: a
> high-selectivity campus). A contact is: a department HoD, a librarian, a
> student-club office-bearer, or a placement cell staffer who can (a) permit
> us to approach students on campus and (b) forward a survey link to a batch
> group. **Email intro or a phone number is enough — we do not need a formal
> agreement.**
>
> **2. Permission posture.** Confirm which of these you authorise: (i) formal
> written permission from each college, (ii) informal department-level nod,
> or (iii) approach students off-campus only, at the gate. Each changes the
> plan. Note that any *written* campus agreement is a legal commitment and is
> a reserved founder authority (README §2) — Product cannot sign one.
>
> **3. Incentive budget — Rs 4,500.** 18 interviews × Rs 200, plus Rs 900
> contingency for no-shows and travel. Spending is a reserved founder
> authority. **Approve, reduce, or decline.** If declined, say so explicitly
> and I will run unincentivised recruitment.
>
> **4. Who conducts the interviews.** These must be done by a human with a
> real student. Confirm: you do them, you delegate to a named person, or you
> fund a research assistant. **No agent can do this, and no amount of agent
> output substitutes for it.**
>
> **BY WHEN: 2026-10-28** (7 days).
>
> **WHAT IT UNBLOCKS:** the interviews and survey in §4–§5, which produce the
> only evidence that can resolve T1 and T2 (§3) and the open critical risks
> R-01, R-02, R-03 and R-07. G1 (Strategy gate) cannot pass on hypotheses.
>
> **IF IT DOES NOT ARRIVE BY 2026-10-28:** Phase A stalls on the user-evidence
> half. Product will not fabricate substitutes. Two options, both bad, and I
> recommend the first: **(a)** proceed to G1 with market, competitor and
> compliance evidence only, with the thesis formally recorded as
> **UNVALIDATED**, and the PRD explicitly blocked until interviews run; or
> **(b)** run the survey alone through public student channels, accepting an
> unrepresentative self-selected sample, which answers Q3 weakly and T2 not at
> all. **Under no circumstance do we start Phase B/C build on this document.**

</details>

---

## 8. Sources

All accessed **2026-10-21**. Sources are cited for what they actually say.
Where a source is a vendor page, a research firm's own report page, or dated
reporting, it is marked — those are **not** usable as BookHop facts.

| # | Claim it supports | Source | Caveat |
|---|---|---|---|
| 1 | DU photocopy case, s.52(1)(i) educational exception, 2016 single-judge ruling | https://blog.ipleaders.in/oxford-v-rameshwari-photocopy-service-case-study/ ; https://blog.ipleaders.in/delhi-university-photocopy-case/ | Legal commentary blog, not the judgment text |
| 2 | Publishers withdrew the suit March 2017, said they would not go to the Supreme Court | https://spicyip.com/2017/03/publishers-release-public-statement-on-withdrawal-of-du-photocopy-case.html ; https://ipkitten.blogspot.com/2017/03/the-delhi-university-photocopy-case.html ; https://www.huffingtonpost.in/2017/03/09/delhi-university-photocopy-case-publishers-withdraw-copyright-s_a_21878943/ | — |
| 3 | IRRO filed an SLP in the Supreme Court challenging the Division Bench judgment (reported 2017) | https://ssrana.in/articles/du-photo-copy-case-irro-challenges-delhi-high-court-judgment-before-the-supreme-court/ | **Current status NOT confirmed.** Do not state the law as finally settled without re-checking. |
| 4 | Photocopy Re 1/copy, print Rs 2/copy (June 2025 college notice) | https://www.domkalgirlscollege.ac.in/admin/file/noti/196%20dt%2013-06-2025-%20Xerox%20print%20photo%20form%20fillup.pdf | West Bengal college; subsidised student rate, not a Chennai market rate |
| 5 | Library photocopy Rs 1/page, print Rs 2/page | https://library.fcrit.ac.in/photocopy-print-service | Mumbai institute library |
| 6 | Library photocopy Rs 1 per exposure A4, min Rs 2 | https://sgbaukrc.ac.in/index.php/services/reprographic-services | Amravati university library |
| 7 | Telegram piracy of textbooks/exam material; ~40m India users, largest market | https://archive.factordaily.com/telegram-turns-go-to-platform-for-test-prep-in-india-but-has-a-piracy-problem/ | **2019, dated.** User number must not be used as current. |
| 8 | Telegram channels distributing pirated textbooks generally | https://www.redpoints.com/blog/telegram-book-piracy/ | Anti-piracy vendor blog; not India-specific |
| 9 | Copyright Act 1957 penalties cited as up to 3 years / Rs 3 lakh | https://keralakaumudi.com/web-news/en/2023/10/NMAN0445257/1.html | News article, **not verified against the statute**; we do not rely on the figures |
| 10 | Pearson Anna University Engineering Maths titles at Rs 689 and Rs 499 | https://www.pearsoned.co.in/web/books/9789354497674_Engineering-Maths-I-Anna-Univ_C-Vijayakumari.aspx ; https://pearsoned.co.in/web/books/9789353062958_Engineering-Mathematics-I_K-S-Ramasami.aspx | Publisher list price, not street price |
| 11 | Wiley India first-semester Anna University titles at Rs 349 | https://www.wileyindia.com/books-for-anna-university-first-sem | Publisher list price |
| 12 | Veerarajan *Higher Engineering Mathematics* 2025 at Rs 335 (from Rs 395) | https://bharatlawhouse.in/?p=21923 | Retailer listing |
| 13 | Indian-market reprints of foreign textbooks are South-Asia-sale-only | https://forums.appleinsider.com/discussion/29608 | Forum post, old; treat as context only |
| 14 | Moore Market ~150 shops, >1 crore books, academic reference the main draw | https://www.t5eiitm.org/beyond-the-gates-a-book-lovers-delight/ ; https://theculturetrip.com/asia/india/articles/the-best-second-hand-bookshops-in-chennai | Figures are "according to sellers" |
| 15 | Moore Market used-book trade slumping, blamed on online stores | https://citizenmatters.in/photos-moore-market-and-death-of-used-book-business-12480 | **Date unclear**, possibly dated |
| 16 | Pavement sellers price Rs 20–70; old books cheaper | https://www.dtnext.in/news/chennai/sales-always-high-for-old-books-say-pavement-sellers-760802 | — |
| 17 | Berkshire Books ~Rs 250/kg; Murugan Old Book Stall from ~Rs 50 | https://lbb.in/delhi/best-second-hand-bookstores-in-chennai | City-guide listicle |
| 18 | OLX / WhatsApp / Telegram resale groups as used-book channels | https://cashkaro.com/blog/how-to-save-money-on-books/250942 | Affiliate/coupon site; weak |
| 19 | "Scattered WhatsApp groups, Instagram stories, word of mouth" framing | https://www.hunted.space/product/campuskart | **Competitor's own marketing copy. Not evidence.** |
| 20 | Prior attempts: Doosradeal (engineering second-hand textbooks), Cultext | https://gust.com/companies/doosradeal ; https://solve.mit.edu/solutions/53707 | **Current status unknown.** Flagged to `market-finance` (R-07). |
| 21 | India second-hand books market USD 781.04m (2023), 6.80% CAGR | https://www.credenceresearch.com/report/india-second-hand-books-market | **Commercial research firm's own report page. Do not use in the financial model without a primary source.** |
| 22 | Jio prepaid: Rs 249 for 1 GB/day 28 days; Rs 100 for 5 GB/30 days | https://www.digit.in/news/telecom/jio-prepaid-recharge-plans-for-2025-best-offers-data-validity-prices-and-other-details.html/amp/ ; https://www.cashify.in/best-jio-prepaid-recharge-plans-under-rs-300 | Prices change; re-check before quoting |
| 23 | Tamil Nadu GER highest among large states (46.9%); 76% private-unaided colleges (2014-15) | https://www.deccanchronicle.com/amp/nation/current-affairs/060118/tamil-nadu-tops-in-country-with-469-per-cent-gross-enrollment-ratio.html ; https://dhte.py.gov.in/sites/default/files/aishe-final-report-2014-15.pdf | State-level only. **No Chennai district enrolment figure was found** — that gap belongs to `market-finance` (R-08). |

### 8.1 Research gaps this document could not close

1. **No Chennai-district student denominator found.** → `market-finance`,
   `evidence/MARKET-SIZING.md`, R-08.
2. **No study of Indian students' actual textbook-acquisition mix.** It may
   not exist. This is precisely why §4 and §5 are the deliverable.
3. **Fate of Doosradeal, Cultext and similar prior attempts is unknown.**
   Highest-value unresearched item in the whole programme → `market-finance`,
   R-07.
4. **No Chennai college library holdings audit.** → **addressed in v0.2**: one
   budget-holder per campus, three total, running the §4.10 script (§6.2).
5. **Current status of the IRRO Supreme Court SLP** on the photocopy
   judgment → `privacy-compliance`, as it affects how we talk about
   photocopying as a competitor.
6. **New, and now the largest gap in the programme: zero sources on Indian
   college book provision.** Red Team O-12 searched `COMPETITORS.md`,
   `MARKET-SIZING.md`, `COMPLIANCE.md` and this document and found nothing on
   college library acquisition budgets, departmental book-bank practice, what
   happens to hostel clear-out stock, or whether any Chennai institution has
   ever transacted this way. **The thesis now names the institution as the
   payer (§3.0), so the payer side of the business rests on no evidence at
   all.** §4.6, §4.10 and survey Q11 are the first three probes; none of them
   is a substitute for desk research that nobody has done. → `market-finance`.
7. **The 1-in-3 matching factor used to derive T2a's 30% bar is a pure guess
   (§3).** It is the weakest link in the only threshold that can kill the
   demand claim. Anything that converts it into a measurement — Test 1's match
   rate, most cheaply — should be routed back here.
