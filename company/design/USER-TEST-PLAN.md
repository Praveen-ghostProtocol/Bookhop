# USER-TEST-PLAN.md — usability test of Direction A, ready to run

**Owner:** `design-director` · **Version:** v1.0 · **Date:** 2026-10-21
**Instrument for:** `DIRECTIONS.md` Direction A ("Catalogue Card") and
`SYSTEM.md`
**Handoff:** `product-manager` (recruiting overlap with `DISCOVERY.md` §4.1),
`test-qa` (accessibility arm, §6), `ceo-planning` (budget escalation, §7)

> ## STATUS: NOT RUN. ZERO PARTICIPANTS. ZERO RESULTS.
>
> This document is an **instrument**, per `README.md` §8. There is no results
> section and there will not be one until sessions have happened. Any agent
> that cites a finding from this file is citing something that does not exist.
>
> The thresholds in §5 are **pre-registered** and they become fixed **the
> moment the first session is booked**, for the same reason `DISCOVERY.md`
> locks its own: a threshold edited after data starts arriving is a
> rationalisation with a date on it.
>
> **Not funded.** See §7.

---

## 1. What this test is for, and what it is not for

**It tests whether Direction A works.** It does **not** test whether anyone
wants BookHop. That is `DISCOVERY.md`'s job (T1, T2a, T2b, T3, T4) and the
two must not be confused, because a student can complete every task here
flawlessly and still never use the product.

Concretely, this test exists to resolve the four things `DIRECTIONS.md` leaves
open:

| # | The open question | Where it comes from |
|---|---|---|
| **Q1** | Can a student find and verify the **exact edition** in a dense catalogue layout, on their own phone? | `DIRECTIONS.md` §4.1 item 2 — the core bet of Direction A |
| **Q2** | Does the trust-without-warranting copy produce confidence **without** producing a false belief that BookHop vouched for anything? | `DIRECTIONS.md` §4.2 — the hardest problem in the product |
| **Q3** | Does the dense record layout fail for students who are not app-fluent — the thing Direction B would have been better at? | `DIRECTIONS.md` §4.4 item 1, the biggest named risk of the recommendation |
| **Q4** | Does the Tamil interface perform as well as the English one? | `DIRECTIONS.md` §4.4 item 2, §4.5 third bullet |
| **Q5** *(new, v1.1)* | Does a student understand that the asking price is a starting point they negotiate, rather than the price? | `COMPLIANCE.md` §4.3.1 trap (1) — a **legal** limb that lives in copy and is currently asserted to counsel as a fact about the product with no evidence behind it |

A fifth question is deliberately **out of scope** and stated so nobody tries
to answer it here: *will a student pay ₹250 for a used book rather than
photocopy it.* That is T2a, it needs n≥120 on a survey, and a usability
session with 8 people cannot estimate a prevalence.

---

## 2. Method

**Moderated, task-based, in person, on the participant's own phone.**
8 participants, 45 minutes each, one moderator, one note-taker (or audio with
consent if only one person is available).

Six decisions about the method, each with its reason, because each one is a
place this kind of test usually goes wrong:

1. **Their phone, not ours.** The charter's target is a mid-range Android on
   3G. A test on a loaned flagship measures a product we are not building.
   Record make, model, Android version, screen width, free storage and
   whether system dark mode and a non-default font size are on — the last two
   bear directly on `SYSTEM.md` §3.6 and §7.2.
2. **Throttled network, on purpose, and disclosed.** The session runs against
   a 3G-throttled build. We tell the participant the connection is slowed on
   purpose so they do not spend the session apologising for their phone.
   Without this the test measures patience, not design.
3. **A real clickable build, not a Figma prototype.** The whole direction is
   an argument about htmx swaps, 3G behaviour and failure states
   (`SYSTEM.md` §5). A prototype cannot show any of them. **If no build
   exists when the test is ready, run the ₹0 variant in §7 instead, not a
   prototype test.**
4. **Seed data, obviously seeded.** Listings must include **the participant's
   own course's prescribed titles in two adjacent editions** — that pairing is
   what Task 1 is about and without it Q1 cannot be answered. Everything is
   `is_seed=true` (ADR-002 §4.1) and nothing points at a real student.
5. **Tasks, not opinions.** We watch what they do. "Do you like it" is not
   scored. `DISCOVERY.md` §4.9's discipline applies here too.
6. **Two failure events are injected, and only two.** A photo upload failure
   (`SYSTEM.md` §4.5) and a connection drop at the confirm step
   (`SYSTEM.md` §5.4). These are the two states most likely to be wrong and
   least likely to appear by luck in a 45-minute session. **They are injected
   and logged as injected** — a failure state nobody saw is a failure state
   nobody tested.

### 2.1 Recruiting — 8 participants

Use `DISCOVERY.md` §4.1's screener so the samples are comparable, with two
changes and one addition:

| Group | n | Profile | Why |
|---|---|---|---|
| **Primary** | 4 | 2nd/3rd year, `S2 ≥ 2 AND S4 ≥ 1` (the `MAIN` rule) | The persona hypothesis (`DISCOVERY.md` §1.1) |
| **Counter-persona** | 2 | The `COUNTER` positive profile: last course book was a PDF or photocopy **and** never paid their own money for one | Q3. If Direction A only works for people who already think bibliographically, that is a finding, and Vignesh is the one who will show it |
| **Tamil-interface** | 2 | Same as Primary, but the whole session runs in the Tamil locale, moderated by a Tamil speaker | Q4. **A test of the Tamil UI moderated in English is not a test of the Tamil UI** |
| | **8** | | |

- **18+ only**, hard gate, same as `DISCOVERY.md` §4.1 S6.
- No design, product or engineering students who have built a marketplace.
- Nobody who has seen BookHop before.
- **The two Tamil sessions cannot run before `COPY-DECK.md` §2's B1/B2/B3
  sign-off exists.** Testing unreviewed Tamil would produce findings about my
  draft Tamil rather than about the design, and might expose a participant to
  a safety string that is wrong. If the sign-off is not in place, run 6
  sessions in English and record the Tamil arm as **not run**.

**Why 8 and not 5 or 18.** Five would not cover three groups. Eighteen is
`DISCOVERY.md`'s interview sample and this is not a prevalence study — a
usability test's job is to find the problems, and the fourth or fifth
participant in a group stops producing new ones. Eight buys three groups and
a spare.

---

## 3. Session script — 45 minutes

Read the bracketed instructions; do not improvise them.

### 3.0 Setup (before they arrive)
Device throttled to a 3G profile. Account pre-created and signed in **except**
for Task 0. Seed listings loaded including the two-adjacent-editions pair for
their course. Failure injections armed but not triggered. Screen recording
only with consent; **never record the participant's face or their phone's
notification shade.**

### 3.1 Opening — 3 min

> "Thanks for coming. I'm testing a thing we've built, not you — if something
> is confusing, that is information I need. Please think out loud: say what
> you are looking for and what you expect to happen. I'll mostly stay quiet.
> I've slowed the connection down on purpose, so if it feels slow that's us,
> not your phone. You can stop any time."

Record: device details, whether dark mode is on, whether their font size is
non-default.

### 3.2 Task 0 — first run and sign-in (5 min)

> "Here's a link someone sent you. Get yourself in."

Observe: do they understand what the college email is for? Do they expect a
password? Does the email field autocapitalise (a build bug —
`SYSTEM.md` §5.2 rule 1)? Do they go looking for the email in the right app?

### 3.3 Task 1 — find the exact edition (10 min) · **answers Q1**

Hand them a printed syllabus line, actually formatted the way Anna University
formats one (`COMPETITORS.md` §5.1):

> *"Stuart Russell and Peter Norvig, 'Artificial Intelligence – A Modern
> Approach', **Fourth Edition**, Pearson Education, **2021**"*

> "This is on your syllabus. Find a copy on BookHop and get as far as telling
> the seller you want it. Stop before you'd actually meet them."

The seed data contains the **3rd** and the **4th** edition of this title, at
different prices, with the 3rd edition cheaper. This is the core measurement
of the whole test.

Record:
- **Success** = they open or offer on the 4th edition. **Failure** = they
  offer on the 3rd, or cannot decide, or need a hint.
- **Time to first correct identification** (from search submit to opening the
  right listing).
- Where their eyes/thumb go first on a result row — title, price, or the
  edition line.
- Whether they say the edition number out loud at any point.
- Whether they notice the "This is the 3rd edition, not the 4th edition your
  syllabus names" line (`COPY-DECK.md` §6.2 `search.other_editions.warn`).
- Any hint given, verbatim, and at what time.

### 3.4 Probe P1 — the warranty probe (4 min) · **answers Q2**

**On the listing page, before they offer.** Ask exactly this, once, and then
be quiet:

> **"Looking at this screen — what has BookHop promised you here?"**

Then, after they finish:

> "If the book turns out to be in worse shape than it says, what happens?"
> "Who checked this book?"

**Added in v1.2 — the adjacency check.** Point at the seller block and ask:

> "What does this part tell you about Priya?"

`COMPLIANCE.md` §2.5a flagged that "Signed in with a college email address"
and the not-checked sentence could read as the product arguing with itself,
and that *a contradiction in trust copy is worse than either string alone*.
The fix is `COPY-DECK.md` §3.2's two labelled blocks with the qualifier
adjacent to the fact — **and that fix is untested.** Record, verbatim, whether
the participant reads the pair as **one coherent statement** ("they know she's
a student here, that's all"), as a **contradiction** ("so do they check her or
not?"), or as a **boast they then discount**. No separate threshold — U2
catches the dangerous failure — but a contradiction reading is reported in its
own right, because the fix for it is mine and compliance is relying on it.

Code the answer into exactly one bucket:

| Code | Answer shape | Meaning |
|---|---|---|
| **W0** | "Nothing / they haven't promised anything / nobody checked it, I have to check it myself" | **The design worked.** This is the target |
| **W1** | Uncertain, hedging, "I think the seller checked it?" | Partial. Note what they looked at |
| **W2** | **Any warranty belief** — "they checked it", "I'd get my money back", "BookHop guarantees it", "they verified the seller" | **Failure.** This is the single most important negative result the test can produce |

**Do not correct a W2 answer until the session is over.** Then do correct it,
clearly, before they leave — it would be wrong to send someone away with a
false belief about what we do.

### 3.4a Probe P3 — the negotiability probe (2 min) · **new in v1.1**

Added because `COMPLIANCE.md` §4.3.1 makes negotiability a **legal limb that
lives entirely in copy**, and Q9's statement of facts asserts to counsel that
*"Price is negotiable and the product says so."* That assertion is currently
untested. This probe is the only instrument that tests it.

**On the listing page, still before they offer.** Ask exactly this:

> **"It says ₹280 here. What do you think you'd actually end up paying?"**

Then: *"Who decides that?"*

Code into one bucket:

| Code | Answer shape | Meaning |
|---|---|---|
| **N0** | "Depends — I'd ask her / we'd talk / maybe less" and attributes the decision to the two students | **The limb is true in practice.** Target |
| **N1** | Uncertain, or "₹280 I suppose, unless she agrees less" | Partial. Note whether they had read the negotiability sentence |
| **N2** | "₹280, that's the price" / "that's what BookHop says it costs" | **Failure.** The copy has not made negotiability visible, and the fact asserted to counsel in Q9 is not true of the product |

This is also the **cheapest honest check available** on whether the whole
`COMPLIANCE.md` §4.3.1 control works, and it costs two minutes of a session we
are already running. Report the distribution to `privacy-compliance`
directly — they are relying on this being true and currently have only my
word for it.

### 3.5 Task 2 — list a book, with an injected photo failure (10 min)

> "Now the other side. You've finished with this book [hand them a real
> textbook]. Put it up for sale."

**Inject the photo-upload failure on the second photo** (`SYSTEM.md` §4.5
`error`).

Record:
- Do they find the ISBN on the physical book without help?
- Does the numeric-keypad ISBN field work on their keyboard
  (`SYSTEM.md` §5.2 rule 2)?
- **Do they answer "What's wrong with it?" with a real defect, or with
  "good condition"?** This is the measurement for
  `DIRECTIONS.md` §4.2(3) — specificity is the trust mechanism, so a field
  that produces "good condition" has failed.
- On the photo failure: do they understand the typed listing is not lost? Do
  they find Retry? Do they abandon?
- Do they notice `sell.price.hint` ("BookHop doesn't record it" — P14)? Does
  it confuse them?

### 3.6 Task 3 — the handover, with an injected connection drop (8 min)

> "The seller said yes. Sort out when and where you'll meet. Then afterwards,
> tell BookHop what happened."

**Inject the connection drop on the confirm submission**
(`SYSTEM.md` §5.4 last row).

Record:
- Do they read the handover guidance (`COPY-DECK.md` §7) or skip to the
  button? **Eye or thumb dwell time on the guidance block.**
- Does the button label "I've read this — agree 4:30 PM at Library steps"
  read as an acknowledgement, or do they look for a checkbox?
- On the drop: **do they believe the confirmation was recorded?** If yes, the
  offline copy has failed, and this is a correctness failure, not a polish
  one — it corrupts the completion metric D-009 depends on.
- Do they try again, wait, or give up?

### 3.7 Probe P2 — the alternatives probe (3 min)

> "If you needed this book next week and BookHop wasn't there, what would you
> actually do?"

Not a design question. It is a cheap, honest check on
`DISCOVERY.md` §2.3's ranking (photocopy > PDF > WhatsApp), recorded verbatim
and reported to `product-manager` as **anecdote, n=8, not evidence**. It is in
the script because the moderator is already in the room and it costs 3
minutes.

### 3.8 Close — 2 min

Correct any W2 belief. Ask for anything they want to say. Thank them. Hand
over the incentive. Delete the recording within 90 days and tell them so.

---

## 4. What is measured

| Measure | How | Maps to charter metric |
|---|---|---|
| **Task success rate** per task, per group | Binary per the definitions in §3, scored by the note-taker during the session, not reconstructed afterwards | "Task success rate" |
| **Time on task** | Stopwatch from task statement to success or abandonment | "Time on test" |
| **Hints given** | Count + verbatim + timestamp. A task completed after a hint is **a failure**, recorded as "success-with-hint" separately | — |
| **Warranty code** (W0/W1/W2) | §3.4 | The `DIRECTIONS.md` §4.2 mechanism |
| **Negotiability code** (N0/N1/N2) | §3.4a | `COMPLIANCE.md` §4.3.1's copy control |
| **Doubt events** | Any moment the participant stops, scrolls back, re-reads, or says "I'm not sure" — timestamped, with what was on screen | The "adds a doubt" half of the brief |
| **Defect specificity** | Does the condition field get a real defect or an adjective? (§3.5) | `DIRECTIONS.md` §4.2(3) |
| **Failure-state comprehension** | Did they correctly understand what had and had not been saved, in both injected failures? | `SYSTEM.md` §4.5, §5.4 |
| **Device reality** | Make, model, Android version, width, dark mode, font size | Charter's 3G/mid-range target |

**Not measured, deliberately:** satisfaction scores, SUS, NPS, preference
between directions. An 8-person preference vote between two directions we
designed is exactly the pattern `DISCOVERY.md` §4.9 and the declined
three-card concept test (D-008) reject, and I am not reintroducing it here.

---

## 5. Pre-registered thresholds

These are the numbers that decide something. They match
`DIRECTIONS.md` §4.5's change-of-mind conditions exactly, so neither document
can drift from the other.

| # | Threshold | If it trips |
|---|---|---|
| **U1** | **≥3 of 8 fail Task 1** (offer on the wrong edition, or need a hint) | The density bet has failed. **Direction B's layout takes over the search and results surface** — not a repaint of A. `DIRECTIONS.md` §4.5 bullet 1 |
| **U2** | **≥2 of 8 code W2** on Probe P1 | The trust-without-warranting mechanism has failed. First fix: move `trust.not_checked` above the fold and into `--c-ink` at `--t-base`. Re-test before anything else changes. `DIRECTIONS.md` §4.5 bullet 2 |
| **U3** | **Either counter-persona participant fails Task 1 while all four Primary participants pass** | Direction A works only for the already-bibliographic student. Q3 answered against us. Adopt B's one-question-per-screen pattern for first run and search |
| **U4** | **Both Tamil participants take >1.5× the English median on Task 1, or either fails it** | The 15–19px Tamil body size is the problem. Raise the Tamil step above `1.06em` and re-test; if that does not close it, B's larger type wins on that axis. `DIRECTIONS.md` §4.5 bullet 3 |
| **U5** | **≥2 of 8 believe the confirmation was recorded** after the injected drop (§3.6) | A correctness failure in the offline copy, not a usability one. Blocks the slice: the completion metric is the thing D-009 traded the concierge pilot for |
| **U6** | **≥4 of 8 answer the condition field with an adjective rather than a defect** | `DIRECTIONS.md` §4.2(3)'s specificity mechanism does not survive contact with a real seller. The field needs to become structured prompts ("Any torn pages? Any writing? Is anything missing?") rather than one open box |
| **U7** | **Any participant abandons a task entirely** | Report it as its own finding regardless of the other numbers, with the full timeline. An abandonment at one campus is a churn event at twenty |
| **U8** *(v1.1; remedy pre-authorised v1.2)* | **≥3 of 8 code N2 on Probe P3** (the asking price reads as *the* price) | The `COMPLIANCE.md` §4.3.1 copy control is not working, and the fact asserted to counsel in Q9 — *"price is negotiable and the product says so"* — is not true of the product. Still reported to `privacy-compliance` and `ceo-planning` **as a compliance finding, not a design nit** — `COMPLIANCE.md` §4.3.3 endorses that escalation path by name. **But the first remedy no longer waits on a ruling:** the buyer-side figure prompt (`price.ask_in_messages`, `offer.message.hint`) together with `price.seller.hint` at intake is **pre-authorised**, and I may implement both immediately. If copy fails a second time, the next step is **not** to start recording prices — see §5.1 |

**Minimum denominator:** the whole test is void below **6 completed
sessions**, and U3 is void if the counter-persona group is not recruited, and
U4 is void if the Tamil arm is not run. **A void limb is reported as void, not
dropped silently.**

**Honest prior, recorded before the data exists:** I expect **U2 to be the
one that trips**. Every instinct a student has been trained with by this
category says a marketplace vouches for its listings
(`COMPETITORS.md` §3.9 — Bookaao ships exactly that), and one line of
honest copy against years of that is not obviously enough. Pre-registering a
threshold I expect to fail is the discipline, not a flaw in it.

### 5.1 If U8 fires twice — the direction the remedy must travel

Recorded here because this is the document someone will read when a threshold
fires, and the wrong conclusion is both available and plausible.

The pre-authorised first remedy is more copy that *causes* negotiation rather
than asserting it. If that also fails, `COMPLIANCE.md` §4.3.3 names — and
explicitly does **not** request — a listing with **no asking price at all**,
which cannot be a determinable gross amount on any reading. It would cost the
price filter, a large amount of buyer utility and probably liquidity, and it
would be a P14 amendment and an ADR.

**It is written down for one reason: so that nobody reading a failed copy
control concludes the only remaining option is to start recording prices. The
available move is to record fewer, not more.** Recording a settled price is
closed permanently (D-004, ADR-003, P14), and a failing usability threshold is
not a reason to reopen it.

---

## 6. The accessibility arm — separate, and not a substitute

Usability with 8 sighted touch users does not test accessibility, and running
axe-core does not test it either. Both are needed and neither replaces the
other.

**6a — automated and manual, owned by `test-qa`.** `SYSTEM.md` §6's thirteen
criteria. Runs on every route, in both locales, before any session.
**If criterion 1, 2, 3 or 4 fails, the sessions do not run** — testing a
layout with a contrast failure or a 32px button wastes eight students'
afternoons measuring a bug we already know about.

**6b — one session with a screen-reader user, if we can find one.** TalkBack
on Android, their own device and their own settings, same tasks. The things
only this session can find:

- Whether focus survives every htmx swap (`SYSTEM.md` §5.3 rule 5) — the most
  likely defect in the whole build.
- Whether the state banner being second in reading order
  (`SYSTEM.md` §5.5) actually helps.
- Whether `confirm.yes`'s long accessible name is useful or just long.
- Whether the Tamil `lang` attribute makes TalkBack switch voice correctly.

**Recruiting honesty:** we have no route to a TalkBack-using Chennai student
and I am not going to pretend otherwise. If we cannot find one, the arm is
recorded as **not run**, 6a still runs in full, and the gap is logged. A
manual keyboard + TalkBack pass by `test-qa` is a weaker but real substitute
and should be done either way.

---

## 7. Cost, and the escalation

| Line | Cost | Note |
|---|---|---|
| 8 participant incentives @ ₹300 | ₹2,400 | `DISCOVERY.md` pays ₹200 for a 45-min interview; this is also 45 min but on their own device with recording, so ₹300 is the honest rate. `ASSUMPTION:` not benchmarked |
| Tamil-speaking moderator for 2 sessions | ₹0–1,200 | ₹0 if the founder or a Tamil-speaking team member moderates. **Not optional to have one** (§2.1) |
| Travel, printing, water | ₹300 | — |
| **Total** | **₹2,700–3,900** | |

**Against the ledger (D-008): ₹16,500 approved, ₹0 spent, ₹5,000 ring-fenced
for `DISCOVERY.md` interviews, ₹9,100 for Test 1, ₹2,600 unallocated.** This
test does not fit in ₹2,600 at the full rate. **Escalated to
`ceo-planning` → founder. No spend is committed by this document.**

### 7.1 The ₹0 variant, if no money is authorised

Run **4 sessions, unpaid, recruited by the founder from people who already
know them**, English only, Tasks 0–1–2 and Probes P1 and P3 only.

What this buys: **U1, U2 and U8** are still answerable at n=4 — the two that
decide the direction, plus the one that is a compliance finding. P3 costs two
minutes on a page the participant is already on, so there is no version of
this test cheap enough to justify dropping it. What it loses, stated so nobody
treats the cheap version as the real one:

- **U3 is void** — no counter-persona group, which is Q3 unanswered and Q3 is
  the named risk of the recommendation.
- **U4 is void** — no Tamil arm.
- **U5 and U6 are void** — Task 3 and the injected failures are cut.
- **Selection bias is severe and must be stated in the write-up.** People who
  already know the founder are not a sample; they are a courtesy.

### 7.2 What blocks this test from running today

1. **No build.** `DIRECTIONS.md` and `SYSTEM.md` are Phase B; the frontend
   does not exist yet. The test needs a clickable build with seed data. §2
   decision 3 forbids substituting a prototype. **Earliest honest window:
   after slice S3** (`TASKS.md`) — S1 gives sign-in and the legal pages, S2
   the sell flow and listing detail, and **S3 is where search and the empty
   state land, which Task 1 cannot run without.**
2. **Campus contacts.** Still the single blocker on all fieldwork (D-008).
3. **Tamil sign-off** for the Tamil arm (`COPY-DECK.md` §2). Note that
   `feature_flags['i18n.ta_enabled']` is seeded **false** (`TASKS.md` A-9), so
   **the Tamil arm is not merely unreviewed — it is unservable until a named
   native speaker signs `locale/ta/REVIEWED.toml`.** If that has not happened,
   run 6 sessions in English and record the Tamil arm as **not run**; do not
   flip the flag to make a test possible.
4. **Budget** (§7).
5. **`SYSTEM.md` §6 criteria 1–4 green** (§6a).

---

## 8. Reporting template — what the write-up must contain

So that a pass cannot be reported as more than it is, which is the mistake
D-008 explicitly wrote into Test 1's template and the same discipline applies
here.

1. **n, per group, and every void limb named as void.**
2. **Device table** — every participant's actual phone.
3. **Per-task: success / success-with-hint / failure / abandoned**, with times.
4. **Every hint given, verbatim, with its timestamp.**
5. **The W0/W1/W2 distribution**, with the exact words of every W2, **and the
   N0/N1/N2 distribution**, with the exact words of every N2. **Plus the
   seller-block adjacency reading** (coherent / contradiction / discounted
   boast) for every participant, verbatim — reported to
   `privacy-compliance` because §2.5a's flagged risk is relying on this fix.
6. **Each of U1–U8: tripped / not tripped / void**, stated before any
   interpretation.
7. **Every injected failure, labelled as injected.**
8. **The sentence that must appear if the test passes:**
   > *"Passing this test means 8 students could use Direction A. It does not
   > mean they would. Whether anyone wants BookHop is T1, T2a, T2b, T3 and
   > T4 in `DISCOVERY.md`, and those are unrun."*
9. **What I would change**, ranked, with the threshold or observation each
   change answers to.
10. **No quotes invented, no results estimated, no averages over fewer than
    the stated minimum denominator.**

---

## Amendment log

| Version | Date | Change |
|---|---|---|
| v1.0 | 2026-10-21 | First plan. 8 participants in three groups, Tasks 0–3, Probes P1–P2, thresholds U1–U7, accessibility arm, ₹0 variant, reporting template |
| **v1.3** | **2026-10-21** | §7.2 blockers sharpened against `TASKS.md`: the earliest honest window is **after slice S3**, because Task 1 needs search and the empty state. The Tamil arm is recorded as **unservable, not merely unreviewed**, while `i18n.ta_enabled` is false — with an explicit instruction not to flip the flag to make a test possible. **Still not run, zero participants, unfunded** |
| **v1.2** | **2026-10-21** | **Both compliance rulings reflected.** U8's first remedy is now **pre-authorised** (`COMPLIANCE.md` §4.3.3) so it no longer waits on a ruling; new **§5.1** records the direction a second failure must travel — record fewer prices, never more — so a failed copy control is never read as a reason to start recording them. **P1 gains the adjacency check** on the seller block, because §2.5a's flagged contradiction risk rests on a fix of mine that is untested. Reporting template extended |
| **v1.1** | **2026-10-21** | **Probe P3 (negotiability) and threshold U8 added**, because `COMPLIANCE.md` §4.3.1 made negotiability a legal limb carried entirely in copy and Q9 already asserts it to counsel as a fact about the product. New question Q5. P3 is retained even in the ₹0 variant. **Still not run, still zero participants, still unfunded** |
