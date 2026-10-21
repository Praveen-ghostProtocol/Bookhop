# G1 Red Team Memo — Strategy Gate

**Owner:** `red-team` · **Version:** v1.0 · **Date:** 2026-10-21
**Reports to:** founder (human) and `ceo-planning`. Not to Product, not to Finance.
**Inputs reviewed in full:** `evidence/COMPETITORS.md`, `evidence/MARKET-SIZING.md`,
`evidence/COMPLIANCE.md`, `product/DISCOVERY.md`, `finance/MODEL.md`,
`finance/model.py`, `README.md`, `risks/RISK-REGISTER.md`, `decisions/DECISIONS.md`.

**Arithmetic I actually ran** (not reasoned about):
`python -I company/finance/model.py` unmodified, then a harness that imports
`model.py` and overrides one driver at a time. 14 tests. Every number in this memo
tagged `[ran]` is output I produced; the script is reproducible from the driver
overrides named inline. No driver values were invented — only the published
low/base/high values and explicit sweeps between them.

---

## 1. Verdict

**G1 PASSES WITH CONDITIONS.** The evidence is good enough to reject the current
*monetisation* thesis — a 6% transaction fee on a Rs 220 local handover is dead and
should be recorded as falsified — but it is **not** good enough to kill the company,
because Finance's "no breakeven at any volume" is a property of how the model is
constructed rather than a measured property of the business, and the two inputs that
decide the unit (`support_cost_per_transfer`, `cac_per_registered_user`) have never
been observed. Conditions in §3 and §6.

---

## 2. Objections

Twelve. Two are `critical`. Each carries a test with a threshold, a rupee cost and a
day count. Objections without a test were deleted during drafting.

**Map to the risk register**, so `ceo-planning` can file these without re-reading:

| Objection | Severity | Risk register |
|---|---|---|
| O-1 CAC-in-contribution and model linearity | **critical** | **R-22 (referred to red-team at G1 — this answers it)**, R-13 |
| O-2 "growth is the problem" misreported | material | R-22 |
| O-3 gift/swap share misidentified as decisive | material | R-03 |
| O-4 support cost is a design variable | material | **R-13** |
| O-5 Clankart is the wrong ceiling | material | R-07, R-21 |
| O-6 T2 screener contamination | material | R-15 |
| O-7 T3 cannot fail as written | material | **R-02** |
| O-8 T1/activation inconsistency; T4 denomination | minor | R-01, R-04 |
| O-9 antiphase overstated; cut direct swap | material | **R-04** |
| O-10 inspect-before-pay *is* disintermediation | **critical** | **R-02 + R-03 together** — a new finding, neither risk states it |
| O-11 verification liability vs the trust wedge | material | **R-16** |
| O-12 adjacent-market recommendation unevidenced | material | R-08 |

New risk to add: **the model has no mechanism by which the unit can improve with
density, automation or repeat use** (O-1(d)). This is not in the register and it is the
reason every scale conclusion in `MODEL.md` is pre-determined.

---

### O-1 — "There is no volume at which this reaches breakeven" is a construction, not a finding · **CRITICAL**

**The failure case.** Finance's §1 headline reads as a universal claim. It is not
one. Three separate things are collapsed into it, and unpicking them changes the
verdict.

*(a) CAC and infrastructure sit inside "contribution".* `model.py` line 128 puts
`cac_cost` and `infra_cost` — both charged **per registered user**, not per transfer
— inside the variable block. So the `contribution` line is not a marginal measure at
all. §6.1's own table shows the high case at **+Rs 15.03 marginal contribution per
transfer** `[ran]`, which flatly contradicts the §1 narrative read.

*(b) At HIGH drivers the verdict turns on CAC alone.* I swept CAC independently with
every other driver held at high `[ran]`:

| CAC per registered user | Contribution | Per transfer |
|---:|---:|---:|
| Rs 60 | −Rs 3,35,233 | −Rs 35.34 |
| Rs 25 (published high) | −Rs 89,288 | −Rs 9.41 |
| Rs 15 | −Rs 19,018 | −Rs 2.00 |
| **Rs 12.29 (breakeven)** | **Rs 0** | **Rs 0.00** |
| Rs 10 | +Rs 16,117 | +Rs 1.70 |
| Rs 0 | +Rs 86,386 | +Rs 9.11 |

**The high case has positive unit economics at any CAC at or below Rs 12.29 per
registered user** `[ran]`. On a campus — the one setting where organic acquisition
through a class group, a notice board and six ambassadors is genuinely plausible —
Rs 12 per registration is not an absurd number. It has never been measured.

*(c) But at BASE drivers the coordinator's hypothesis fails, and I am saying so.*
Breakeven CAC at base is **negative Rs 22.77** `[ran]` — i.e. even at CAC = 0 the
base case loses Rs 62,675 (−Rs 42.16/transfer). Setting CAC to zero does not rescue
base. So Finance is right that the base case is not a CAC artifact, and should say
that explicitly rather than leaving it implicit.

*(d) The deeper problem: the model is strictly linear and therefore cannot represent
the thing it is being used to test.* At high drivers with CAC = 0, contribution per
transfer is **Rs 9.11 at one campus, Rs 9.11 at three campuses, and Rs 9.11 across
all of Chennai metro** `[ran]`. Identical to the paisa. There is no density effect,
no automation curve, no support-cost learning, no CAC decay with referral. A model in
which the unit cannot improve with scale will always print "growth makes it worse"
when the marginal is negative, and "monopoly is profitable" when it is positive —
and the Rs 7.34 lakh Chennai-monopoly figure in §10 is nothing more than
Rs 9.11 × 1,35,533 transfers less Rs 9 lakh of fixed cost. **That arithmetic is not
evidence about whether a marketplace's unit improves with density. It is the
assumption that it does not, restated as an output.**

**What would have to be true for the plan to work.** `support_cost_per_transfer`
below roughly Rs 6 and `cac_per_registered_user` below roughly Rs 12 at a single
campus, simultaneously. Neither has been observed once.

**Cheapest test — the zero-code concierge pilot.** One campus, one fortnight at a
semester boundary, no app. A Google Form takes listings, one human matches them by
hand, messages both parties, and asks for the fee at completion. Instrument three
things with a stopwatch and a spreadsheet: minutes of human time per completed
handover, total acquisition spend ÷ registrations, and fee-paid ÷ fee-asked.

**Pass/fail (all three must pass):** ≥ 30 completed handovers in 14 days at one
campus; median human time ≤ **4 minutes** per completed handover *including* disputes
and no-shows; acquisition cost ≤ **Rs 15** per registration.
**Cost:** Rs 2,000–12,000 (printing, incentives, and one person's time for 10 days;
Rs 0 cash if the founder runs it). **Days:** 14, plus campus access.
**Decision it changes:** build / don't build. Nothing should be coded before it
reports.

**Severity: CRITICAL.** Killing a business on two unmeasured inputs, using a model
that cannot represent improvement in either, is the expensive mistake this gate
exists to prevent.

---

### O-2 — "Growth is the problem" is reported in the one denomination that makes it true · material

**The failure case.** §8.2 and §8.3 show total contribution falling as activation and
transfers rise, and conclude "growth is the problem" and "the driver that goes the
wrong way". Both sensitivity tables hold `registered` fixed while adding transfers at
a negative marginal, so total contribution must fall — arithmetically, with no
information content. The per-transfer line, which Finance did not print, moves the
other way `[ran]`:

| `activation_rate` | Transfers | Contribution total | **Contribution per transfer** | Marginal/transfer |
|---:|---:|---:|---:|---:|
| 0.10 | 496 | −Rs 2,19,096 | **−Rs 442.16** | −Rs 8.83 |
| 0.30 (base) | 1,487 | −Rs 2,27,846 | **−Rs 153.27** | −Rs 8.83 |
| 0.50 | 2,478 | −Rs 2,36,595 | **−Rs 95.50** | −Rs 8.83 |
| 0.90 | 4,460 | −Rs 2,54,093 | **−Rs 56.98** | −Rs 8.83 |

Activation from 0.30 to 0.90 improves the fully-loaded unit by **2.7×**. This also
answers the coordinator's question about the −Rs 153.27 figure directly, and the
answer is not the one hypothesised: fixed cost is *excluded* from contribution, so
−153.27 is not a fixed-cost artifact. It decomposes as `[ran]`:

| Component | Per transfer | Note |
|---|---:|---|
| Revenue | +Rs 4.94 | |
| Payment processing | −Rs 1.77 | per transfer |
| Support | −Rs 12.00 | per transfer |
| Infrastructure | −Rs 33.33 | **per registered user ÷ 0.54 transfers per registered user** |
| CAC | −Rs 111.11 | **per registered user ÷ 0.54 transfers per registered user** |
| **Total** | **−Rs 153.27** | |

**94% of the negative is the per-registered-user block divided by a funnel ratio of
0.54 transfers per registered user.** It is a statement about acquiring 1.85
registrations per transaction, not about what a transaction costs.

**What would have to be true.** Nothing new — this is a reporting defect, not a
business claim.
**Test.** Finance re-runs the two sensitivity tables printing contribution *per
transfer* alongside the total, and restates §8's conclusion. **Pass/fail:** the
restated §8 says "a negative marginal makes volume costly" rather than "growth is the
problem". **Cost:** Rs 0, 1 day.
**Severity: material.** The current phrasing would, if carried into a founder
decision, argue against the single intervention (raising activation) that most
improves the unit.

---

### O-3 — The two drivers Finance names as decisive are nearly irrelevant to the unit · material

**The failure case.** `MODEL.md` §12 tells Red Team that `gift_share_of_nonswap`
"directly sets the cash GMV ceiling" and lists it as a top attack surface;
`COMPETITORS.md` §6.3 calls gifting share one of "the two numbers that decide it" and
Q1 "the highest leverage question in Phase A"; `MARKET-SIZING.md` §5 calls it a
required measurement. Product has accordingly built it into the survey and the
interview. I swept both across their entire published ranges `[ran]`:

| Driver moved across its whole range | Marginal contribution/transfer |
|---|---:|
| `gift_share` 15% → 0% | −Rs 8.83 → **−Rs 8.27** (Rs 0.56) |
| `swap_share` 20% → 0% | −Rs 8.83 → **−Rs 8.04** (Rs 0.79) |
| `avg_book_price` Rs 220 → Rs 500 | −Rs 8.83 → **−Rs 4.79** (Rs 4.04) |
| `fee_collection_rate` 55% → 100% | −Rs 8.83 → **−Rs 4.79** (Rs 4.04) |
| `support_cost` Rs 12 → Rs 3 | −Rs 8.83 → **+Rs 0.17** (Rs 11.83) |

Eliminating gifting entirely — a perfect, impossible outcome — moves the unit by 56
paise. **No revenue-side driver in this model can flip the sign. Exactly one cost
driver can.** Gifting share is a real and important question *for the product thesis*
(if everyone gifts, there is nothing to intermediate), but it is not a question about
the unit, and three documents have told Product it is.

**What would have to be true for the current research plan to be well-aimed.** That
gifting share has leverage over the verdict. It does not.
**Test.** Already run — the sweep above. The corrective action is a reallocation:
interview minutes currently assigned to Q1/Q7 willingness-to-pay should move to
observing what a completed handover actually costs in human attention (O-1's test).
**Pass/fail:** the Phase A research plan allocates at least as much instrumentation to
support minutes as to gifting share. **Cost:** Rs 0, 1 day of re-planning.
**Severity: material.** This misdirects the scarcest Phase A resource — access to real
students.

---

### O-4 — `support_cost_per_transfer` is treated as a market fact; it is a design variable · material

**The failure case.** Rs 12 is the input the whole verdict rests on, and it is stated
as a cost assumption awaiting measurement. Converted to the unit it is actually
denominated in `[ran]`: at Rs 30,000/month fully loaded (Rs 2.84/minute), **Rs 12 is
4.2 minutes, Rs 6 is 2.1 minutes, and Rs 3 is 1.1 minutes of human time per completed
transfer, inclusive of every dispute and no-show.** Finance's conclusion — "the only
path to a positive unit is driving support cost below roughly Rs 3, which means
near-total automation and effectively no dispute handling" — is true only if you move
one variable at a time. I ran a blend of five changes each of which is individually
defensible and none of which is at its published high: support Rs 6, CAC Rs 15,
infra Rs 8, take rate 10%, collection 70%, everything else at base. Result: **marginal
contribution +Rs 2.71 per transfer** `[ran]`, with no driver pushed to an extreme and
no support target below Rs 6. (Fully-loaded is still −Rs 39.89 at base activation,
which is O-1(d) and O-2 again, not a new problem.)

**What would have to be true.** That a handover with inspect-before-pay, a
pre-set meeting point and no money held by the platform generates under ~2 minutes of
human attention per completed transfer. Plausible; unmeasured.
**Test.** Folded into O-1's concierge pilot — a stopwatch on every interaction.
**Pass/fail:** median ≤ 4 minutes, p90 ≤ 12 minutes, over ≥ 30 handovers.
**Cost:** Rs 0 incremental. **Days:** 0 incremental.
**Severity: material.**

---

### O-5 — "Clankart's actual revenue" is a ceiling on courier-based national C2C, not on this · material

**The failure case.** §9 sets Clankart's Rs 50.69 revenue per registered user per year
as the benchmark and instructs reviewers to reject any model that beats it without
naming a mechanism. That discipline is good. The benchmark is mis-specified. Finance's
own competitor audit verifies three things about Clankart that make it a poor ceiling:
it is **courier-only** by its own FAQ, it has **no city filter, no location field and
no geography layer at all** (verified directly at `clankart.com/used-books-in-chennai`),
and the revenue figure is from **January 2023** with no later figure found. A company
that ships a Rs 200 book across India, where delivery is 52% of item price, is
standing at a different wall. Separately, §9's own caveat concedes the revenue
mechanism was never confirmed to be commission — so the Rs 50.69 may not be a take-rate
number at all, which would make the comparison a category error rather than a
conservative one.

Note the symmetric point, because it cuts against me: NearBook *did* test proximity
(~6 lakh downloads, hyperlocal by design, zero commission) and was **pre-revenue at
pitch with 0 organic visitors/month**. That is the better ceiling, and it is worse
news than Clankart.

**What would have to be true.** That BookHop has a mechanism neither Clankart nor
NearBook has. The only candidates verified in the audit are campus-bounded identity
and edition-to-syllabus matching, neither of which any player has shipped.
**Test.** Count actual Chennai supply depth on the three live geography-aware
competitors — Bookaao, NearBook, BookFlow — by searching Chennai PIN codes, and open
OLX Chennai books manually (the audit was domain-blocked and the count is unverified).
**Pass/fail:** if the best-funded competitor has **fewer than 100 live Chennai
used-book listings**, the category ceiling is execution, not demand, and the
"five teams hit the same ceiling" reading weakens. If it has **more than 1,000**, the
channel exists and nobody monetises it, which strengthens the pessimistic reading.
**Cost:** Rs 0. **Days:** 1.
**Severity: material.**

---

### O-6 — T2's kill threshold is measured on a sample whose screener selects on the thing being measured · material

**The failure case.** T2 fails if "in 18 interviews, fewer than **6** students can
describe a specific past instance in the last 12 months where they paid their own
money for a whole physical book." But §4.1's screener admits a respondent if
`S2 ≥ 2 AND (S4 ≥ 1 OR S3 involves paying money)`. Twelve of the eighteen are recruited
through that screener, one limb of which is *having paid money for a book*. So up to
12 respondents can be admitted partly because they satisfy T2's numerator. **A
threshold of 6 is then reachable by selection alone.** The six deliberately-recruited
counter-persona respondents are the only unbiased part of the sample, and they are
excluded from the screener precisely because they do not buy books.

This is the single most consequential methodological defect in `DISCOVERY.md`, and it
is in the one test Product itself calls "the claim most likely to kill us".

**What would have to be true.** That paid whole-book purchase is common enough to
appear at a meaningful rate in a sample *not* selected on it.
**Test (a rewrite, not new fieldwork).** Restate T2 as two conditions, both required:
(i) at least **6 of the 12 screened-in** respondents describe a specific past paid
whole-book purchase **where the pay-money limb of the screener was not what admitted
them** (log which limb admitted each respondent at booking — a single field), and
(ii) at least **2 of the 6 counter-persona** respondents describe one.
**Pass/fail:** as stated. **Cost:** Rs 0. **Days:** 1 (edit the screener form and the
threshold before any interview is booked — after the first interview this fix is no
longer available).
**Severity: material.**

---

### O-7 — T3 cannot fail as written · material

**The failure case.** T3 (disintermediation) fails only if "more than **50%** of users
who complete a handover say, **unprompted**, that they would just WhatsApp the same
person next time **AND** cannot articulate why a new counterparty needs the platform."
Three compounding leniencies: *unprompted* volunteering of a specific behavioural
intention rarely reaches 50% for anything; the two limbs are conjunctive, so an
articulate respondent who nonetheless intends to defect counts as a pass; and the
question (Q25) follows Q23/Q24, which have just primed the respondent with the concept
and a price. The fallback limb — repeat-transfer-at-90-days below 15% — requires a
90-day pilot, i.e. it cannot gate G1 or G2 at all.

Separately, the verbal test is measuring the wrong object. The observable for
disintermediation is not what a student says; it is `fee_collection_rate`, which is
directly countable.

**What would have to be true.** That stated intention predicts off-platform
settlement. It does not, and §4.9 of the same document correctly bans hypothetical
questions for exactly this reason — T3 reintroduces one.
**Test.** Replace the verbal limb with a behavioural one inside O-1's concierge
pilot: of handovers the platform matched, count how many report completion in-app
versus how many listings are silently delisted or marked sold-elsewhere within 72
hours of a match. **Pass/fail:** T3 is falsified if **fewer than 40%** of matched
handovers are reported as completed in-app when a fee is attached, measured over
≥ 30 matches. **Cost:** Rs 0 incremental to O-1. **Days:** 0 incremental.
**Severity: material.**

---

### O-8 — T1 and Finance's activation base are mutually inconsistent; T4 is denominated in the wrong unit · minor

**The failure case, part one.** T1 fails if fewer than **40%** of account creators list
a book within 14 days. Finance's base `activation_rate` — registered users completing
at least one transfer — is **30%**. Those two numbers imply a 75% list-to-completed-
transfer conversion in a cold-start two-sided market with no inventory. One of them is
wrong, and nobody has noticed because they live in different documents. Either T1's
bar should be materially higher than 40% (listing is far easier than transacting), or
Finance's 30% activation is optimistic by roughly the same factor.

**Part two.** T4 fails if off-peak handovers fall below 30% of peak **by count**. But
`COMPETITORS.md` §5.3 prices the two halves of the catalogue an order of magnitude
apart — engineering books fetch Rs 20–100 to a seller, novels Rs 5–20. T4 can
therefore pass on volume while contributing almost nothing, which is the exact failure
mode the five-output-line discipline in `MODEL.md` §2 exists to prevent.

**Test.** Reconcile in writing before G2: either raise T1's bar or lower Finance's
activation base, and restate T4's threshold as **30% of peak-month cash GMV**, not
30% of peak-month handover count. **Pass/fail:** both restatements recorded in
`DECISIONS.md` with the chosen number and its reasoning. **Cost:** Rs 0. **Days:** 1.
**Severity: minor** — both are correctable on paper today, but both become expensive
after data collection starts, because a pre-registered threshold cannot be moved
afterwards without destroying the point of pre-registering it.

---

### O-9 — The antiphase assumption is unsourced and, derived from its own cited calendar, overstated · material

**The failure case.** `MODEL.md` §7 and §10 treat antiphase as a structural kill — "a
seller in May and a buyer in July do not meet in a pure matching marketplace",
requiring storage or credits. `COMPETITORS.md` §5.2 flags the same assumption as
having **no source** and says it "drives the entire revenue model and is currently
unsupported". Working it through §5.2's own cited academic calendar: the even semester
ends ~May/June and the odd semester starts ~July/August — a gap of roughly **6–8
weeks**. The odd semester ends ~December and the even starts in January — roughly
**2–4 weeks**. A seller holding her own book on her own shelf for four to eight weeks
is not an inventory business with working capital and shrinkage. It is a pre-order
with a reminder notification. The "8 trading weeks a year" figure that compresses the
entire revenue model is derived from the same unsourced assumption and inherits its
error.

This cuts both ways, and I am reporting both. If the gap is weeks, Finance's
structural objection #3 is substantially weaker than stated. If the trading window is
genuinely 8 weeks, then `fixed_cost_y1_inr` and `infra_cost_per_user_yr` are being
charged against 8 weeks of revenue and the effective cost per trading week is 6.5× the
naive rate, which Finance states correctly.

**What would have to be true for the pessimistic reading.** That supply and demand
peaks are separated by months rather than weeks, and that no listing survives the gap.

**Test.** Pure desk work: count new used-book listings per week on Clankart's and
BookFlow's India pages across 12 months of archived listing dates, and plot them.
Second, a three-question addition to the existing interview (§4.4): *when exactly did
you get rid of last year's books, when exactly did you need this year's, and how long
did the book sit before you acted?*
**Pass/fail:** antiphase is confirmed as structural if the median gap between a
cohort's disposal week and the next cohort's acquisition week exceeds **10 weeks**; it
is refuted if it is under **6 weeks**. **Cost:** Rs 0 (desk) + Rs 0 incremental
(interview). **Days:** 2.
**Action regardless of outcome:** cut **direct swap** from v1. It is one of three
headline features in `README.md` §1, it generates zero cash by construction, it incurs
full support cost on two transfers, and it is the only mechanism that requires both
parties present simultaneously in a market whose timing is the open question. Nothing
in any Phase A document argues for keeping it in the first release. **Cost of cutting:
negative** — it removes build scope.
**Severity: material.**

---

### O-10 — Inspect-before-pay *is* the disintermediation event. The trust mechanism and the revenue mechanism are the same moment · **CRITICAL**

**The failure case.** This objection comes from putting two documents side by side,
which neither agent did because each stayed in its lane.

`COMPLIANCE.md` §2.4(ii) concludes that for C2C used goods, where BookHop holds no
money (D-004) and therefore cannot process a refund, the practical remedy to r.6(3)
return obligations is **pre-handover inspection — the buyer sees the book before
paying** — and calls it "the single highest-leverage compliance and trust mechanism
available to us, and it costs nothing."

`MODEL.md` §10(2) concludes that the structural hole in the revenue model is that
"buyer and seller meet in person, so settling in cash off-platform costs them nothing
and saves them the fee."

**These describe the identical thirty seconds.** The buyer is standing in front of the
seller, holding the book, with UPI open. Compliance requires that this moment exist —
it is the designed remedy for a refund obligation BookHop structurally cannot
discharge. The revenue model requires that payment *not* happen at this moment. There
is no design that satisfies both: any escrow or in-app payment that captures the fee
moves the money before inspection and re-creates the refund obligation that BookHop
cannot meet; any inspect-before-pay flow hands both parties a free, frictionless,
socially normal way to settle outside the platform.

This is not a driver that could go either way. It is a contradiction in the product as
specified, and it is **independent of every number in the model**. No value of
`fee_collection_rate`, `support_cost_per_transfer` or `avg_book_price_inr` resolves it.
It is also why `fee_collection_rate` is the wrong name for the problem: the model
treats leakage as a percentage to be optimised, when the architecture makes leakage
the compliant path.

**What would have to be true for a transaction fee to survive.** Either BookHop holds
the goods (buyback — a different business, and D-004-adjacent), or it holds the money
(escrow — which contradicts D-004 and re-creates the refund liability Compliance says
it cannot discharge), or the fee is not attached to the transaction at all (listing
fee, subscription, or an institutional payer).

**Cheapest test.** The behavioural measurement in O-7, run twice as an A/B inside
O-1's concierge pilot: half the matches are asked for a 6% fee at completion, half are
asked for nothing. Measure (i) fee-paid ÷ fee-asked, and (ii) the delta in reported
completions between the two arms.
**Pass/fail:** the transaction-fee model survives only if fee-paid ÷ fee-asked
exceeds **40%** *and* the fee arm's reported-completion rate is within **10 percentage
points** of the free arm. Below either bar, record the transaction fee as falsified
and stop designing around it. **Cost:** Rs 0 incremental to O-1. **Days:** 0
incremental.
**Severity: CRITICAL.** It invalidates one of the three transaction types, the entire
revenue line, and — because the fee is what the escrow and dispute machinery exists to
protect — a large share of the planned build.

---

### O-11 — If verification is the wedge, the affordable form of it is not a trust signal · material

**The failure case.** `COMPLIANCE.md` §2.5 is the sharpest single finding in the Phase
A set: a platform that "grades condition, verifies editions, vouches for authenticity
or brands handovers as *BookHop Verified* moves towards vouching", and whoever vouches
for authenticity bears liability for it. Its recommended mitigation is wording:
"seller-stated condition", "ISBN match confirmed by the seller", **never** "BookHop
verified". Compliance is right about the law. The product consequence is the one
nobody stated: **a seller-attested condition grade is exactly what a WhatsApp group
already provides.** The audit's §5.5 finding that "no Indian platform publishes a
defined grading scale" and that this is "genuinely unoccupied ground" only holds if
the scale is *enforced*; a published scale that the platform explicitly does not stand
behind is a form with a dropdown. `README.md` §1's wedge is "trust plus proximity plus
exact-edition matching", and the affordable version of the trust leg is a disclaimer.

Note what is *not* affected: campus-bounded identity and no-phone-number-exposure
carry no vouching liability at all, because they are statements about BookHop's own
process, not about a third party's goods. That part of the trust leg survives intact
and is the part with the only real-world corroboration in the audit (the Telegram
migration anecdote at §3.5).

**What would have to be true.** That a seller-attested, photo-backed, platform-defined
grade changes buyer behaviour even when the platform disclaims it.
**Test.** A concept test with seeded mock inventory, run during the interviews at the
point the concept is revealed (§4.7). Three listing cards for the same book: bare
title and price; seller-attested grade with photos and an explicit "seller-stated,
not verified by BookHop" line; and campus-verified seller identity with no grade.
Ask which the respondent would act on and why.
**Pass/fail:** the disclaimed-grade card is chosen first by **fewer than 40%** of 18
respondents → the condition-grading feature is not carrying the trust leg and should
not be built in v1. **Cost:** Rs 300 (printing). **Days:** 0 incremental to the
interviews.
**Severity: material.**

---

### O-12 — The adjacent-market recommendation is the nearest escape hatch, and its own file contradicts part of it · material

**The failure case.** `MODEL.md` §11 ranks eight adjacent markets and recommends
**institutional/library channel first, then buyback**. Reviewing it with the suspicion
the command asks for:

1. **It rests on zero evidence.** §11's table scores institutional supply as "Low trust
   cost / Medium ops / Medium compliance" and calls it "Strongest. Pursue first."
   There is **not one source** in `COMPETITORS.md`, `MARKET-SIZING.md`,
   `COMPLIANCE.md` or `DISCOVERY.md` about Indian college library acquisition budgets,
   departmental book-bank practice, what happens to hostel clear-out stock, or whether
   any Chennai institution has ever transacted this way. Under `README.md` §8 the
   entire row should carry `ASSUMPTION:` tags. It carries none. The same document that
   correctly refused to import the Credence Research TAM figure for want of methodology
   has proposed a strategic pivot with no sources at all.
2. **Buyback is contradicted by evidence already in the file.** §11 scores buyback
   "Low trust cost — one counterparty, you" and "structurally the real fix". But
   `COMPETITORS.md` §3.2 establishes that **Bookchor's consumer buyback arm, "Dump", is
   "currently available in Delhi only"** after the company has operated since 2015 —
   and draws exactly the right conclusion there: "collecting used books from
   individuals does not scale cheaply." And §3.7 establishes that ChennaiUsedBooks
   already runs a free van, a published rate card and on-the-spot cash in Chennai
   specifically. Buyback is not an unoccupied escape hatch; it is a business with an
   incumbent in the pilot city and a ten-year negative datapoint on scaling.
3. **It changes the buyer, which invalidates the research instrument.** Eighteen
   student interviews and a 120-response student survey answer nothing about a
   librarian's budget line or an HoD's procurement authority. If the institutional
   channel is the strategy, Phase A is measuring the wrong population.
4. **Both recommendations require founder-reserved authorities** (campus legal
   agreements and spend, `README.md` §2), i.e. neither can be tested by an agent and
   both are escalations. A recommendation that cannot be cheaply falsified is the
   opposite of what this gate wants.
5. **It contradicts the same document's §10.** §10 concludes "the monetization thesis
   is dead, not the product thesis… Phase A should therefore test whether the utility
   is real, while treating 'we will take 6%' as already falsified." §11 then proposes
   two monetisation strategies requiring founder spend. These are different
   recommendations and the CEO cannot act on both.

**What would have to be true.** That a Chennai college department or library holds a
discretionary budget line for student book provision, has decision authority over it
below the Principal, and currently disposes of or acquires used stock in a way a
platform could serve.

**Cheapest test, and it is nearly free because it already exists.**
`DISCOVERY.md` §6.2 already requires recruiting **one college librarian per campus**.
Add four questions to that conversation: (i) what happens to departmental and library
stock that is superseded by an edition change; (ii) is there a book bank, who funds it,
and from what line; (iii) who signs off a Rs 50,000 purchase of used books, and has it
ever happened; (iv) would you take 200 used copies of a prescribed title at 40% of MRP.
**Pass/fail:** if **zero of three** librarians can name a budget line and an approver
for student book provision, the institutional recommendation is dead and §11 must be
withdrawn or re-evidenced before it reaches the founder.
**Cost:** Rs 0. **Days:** 5 (runs inside the existing recruitment).
**Severity: material.**

---

## 3. The three tests worth running before anything is built

Ranked by decision value per rupee. All three run inside the campus access that
`DISCOVERY.md` §7 is already asking the founder for; none requires a line of code.

### Test 1 — The zero-code concierge pilot · Rs 2,000–12,000 · 14 days

One campus, one semester-boundary fortnight. A form, a spreadsheet, one human matching
by hand, and a stopwatch. Instruments **five** things that no document in the Phase A
set has ever observed: support minutes per completed handover (O-1, O-4), acquisition
cost per registration (O-1), fee-paid ÷ fee-asked under a 6%-vs-free A/B (O-10),
in-app completion versus silent delisting (O-7), and whether anyone lists at all
(T1).

**Pass:** ≥ 30 completed handovers in 14 days; median human time ≤ 4 min; CAC ≤ Rs 15;
fee-paid ÷ fee-asked ≥ 40%; fee-arm completion within 10pp of the free arm.
**Decision it changes:** build / don't build, and whether a transaction fee exists in
the product at all. **This is the only test that can move the G1 verdict in either
direction**, because it measures the only two inputs that control the sign of the unit
and the one contradiction (O-10) that no number can resolve.

### Test 2 — The 18 interviews and 120 surveys, with the four threshold fixes applied first · Rs 4,500 · 21 days

`DISCOVERY.md` §4–§6 is good work and should run close to as written. It must not run
until the fixes in **O-6** (T2 screener contamination — log which screener limb
admitted each respondent, and restate the threshold), **O-7** (T3 replaced by a
behavioural measure), **O-8** (T1/activation reconciliation; T4 restated in cash GMV)
and **O-9** (three timing questions added to §4.4) are in the document. All four are
paper edits costing Rs 0 and one day, and **none of them is available after the first
interview is booked**, because a pre-registered threshold edited post hoc is not a
pre-registered threshold.

**Pass:** the amended T1, T2, T3 and T4 thresholds.
**Decision it changes:** whether the whole-book, whole-semester need exists at a
population scale that supports anything — and, via O-6's counter-persona limb, whether
Vignesh is the modal student or the edge case.

### Test 3 — The Rs 0 desk day plus the librarian questions · Rs 300 · 5 days

Three things, none of which needs a student or a budget: (a) count live Chennai
used-book listings on Bookaao, NearBook, BookFlow and OLX, and record the ten most
recent post dates on each (O-5 — the audit was domain-blocked on OLX and this number
is still unverified for a *named competitor*); (b) count new listings per week across
12 archived months to test the antiphase assumption that drives the whole revenue
model (O-9); (c) the four librarian questions inside Product's existing recruitment
(O-12).

**Pass:** per the thresholds in O-5, O-9 and O-12.
**Decision it changes:** whether the "five teams hit the same ceiling" reading is about
demand or about execution; whether the 8-trading-week compression is real; and whether
Finance's recommended pivot survives contact with three librarians.

**Sequencing note.** Tests 2 and 3 share the campus access that Test 1 needs, and all
three are blocked on the founder decision due 2026-10-28. Test 3's parts (a) and (b)
are not blocked on anything and should run this week.

---

## 4. What I am not objecting to

A red team that objects to everything is useless. The following survived scrutiny and
should be treated as settled at G1.

**The denominators are sound and honestly bounded.** AISHE 2023-24 figures are read
from the Gazette PDF with table references; the 30 campus figures are each traced to a
named NIRF filing with the academic-year convention independently verified from the
PhD header. More importantly, `MARKET-SIZING.md` §4 states plainly that **no Chennai
district or metro enrolment figure exists in any public source**, gives both proxies,
explains why each is wrong and in which direction, and declines to invent a number. The
2.03× error bar is carried through every SAM line. This is the standard the rest of the
company should be held to.

**Finance is right that price is not the lever, and I tested it.** I pushed
`avg_book_price_inr` to Rs 500 — well above the published high of Rs 350 and above
almost every observed Chennai price band — and marginal contribution moves only from
−Rs 8.83 to −Rs 4.79 `[ran]`. It does not flip. The "cheap object cannot carry a human"
argument survives my attack on it.

**The five-output-line discipline is the most valuable thing Finance built.** Keeping
book value moved, cash GMV, platform revenue, contribution and profit strictly separate
is exactly how this category gets oversold, and the Rs 403 crore / Rs 9.04 crore gap in
the TAM table makes the point better than any argument. Keep it, and keep §9's rule
that any future model beating Clankart must name its mechanism.

**The competitor audit's register of what it could not verify (§8) is exemplary.**
Twenty-two rows of BLOCKED / NOT FOUND / CONTRADICTED, each with the reason. Three
competitors' self-reported user counts are contradicted by their own on-page counters,
and the audit says so rather than repeating the marketing number. Doosradeal and
Cultext are reported as confirmed-dead-with-no-known-cause rather than fitted to a
narrative.

**"This category does not kill companies, it strands them" is the most useful sentence
in the Phase A set** and I have no attack on it. Five independent teams at the same
ceiling, two silent deaths with no post-mortem, a 600k-download hyperlocal app with
zero revenue, a 50,000-student claim against 291 listings. The specific danger it
names — a business that consumes years without producing a stop signal — is the
failure mode this programme should be designed against, and the concierge pilot in §3
is my answer to it.

**NearBook is the correct refutation of the proximity thesis and should be weighted
above Clankart.** 6 lakh downloads of the exact hyperlocal promise, pre-revenue, 0
organic visitors. I attacked the Clankart benchmark in O-5; I cannot attack this one.

**Compliance is the strongest document in the set.** The three DPDP commencement
tranches are read from the Gazette and computed from 13 November 2025 with the
corrigendum correctly identified as typographical. The **r.4(1)(a) incorporation
requirement** is a genuine pilot blocker with a lead time that nobody would have
guessed and that would otherwise have been discovered the week before launch. The PPI
analysis of the three credit designs works limb by limb against the instrument actually
in force rather than against the draft, identifies that design (b) is *safer under the
draft than under current law*, and names the exact line that turns a reputation score
into an instrument. The §2.5 vouching-liability finding is the sharpest constraint on
the product thesis anyone produced, and O-11 builds on it rather than disputing it.

**Product's methodology is better than its thresholds.** §4.9 (the nine questions
deliberately not asked, with reasons) and §6.4 (quota the sceptics, Q28 recruits
adversaries by name, no friends, a third recruited off-channel, concept never revealed
before Q23, thresholds pre-registered) are a genuinely well-designed defence against
the failure mode that kills founder research. My objections O-6 to O-8 are about four
numbers, not about the instrument.

**Product is right that the photocopy shop is the competitor to beat, and the rest of
the company has under-weighted it.** Rs 60–200 for the chapters an exam actually
covers, legal under *Rameshwari*, instant, at the campus gate. It does not appear in
`COMPETITORS.md`'s twelve-player table at all. §2.3's ranking — photocopy, then free
PDF, then campus WhatsApp — is the correct ranking and the thesis has to answer #1 and
#2 or it is not finished.

**D-004 (no custody of funds) is the right call and is load-bearing.** It independently
blocks the PPI design, it is what makes inspect-before-pay the compliant remedy, and —
per O-10 — it is also what makes a transaction fee uncollectible. All three
consequences follow from one decision, which is a sign it is a real constraint rather
than a preference.

---

## 5. Revised thesis

`README.md` §1's thesis names the right nouns and the wrong payer. The revision below
is concrete enough to be killed by Test 1 and Test 3.

**Current:** *"The value is: find a relevant book nearby, trust the listing, complete a
convenient handover. The wedge is trust plus proximity plus exact-edition matching."*
Revenue: 6% of the transaction.

**What the evidence actually supports.** Of the three wedge legs, the evidence rates
them very differently and the current thesis weights them equally:

- **Edition-exact matching is the only leg with hard commercial corroboration.** Anna
  University prescribes named editions and years in the syllabus; ChennaiUsedBooks, a
  Chennai operator with cash at risk, **refuses academic stock older than two years
  because editions change**; outdated editions crash to 10–20% of MRP; and no audited
  platform matches an edition to a syllabus requirement. A business refusing revenue
  over an edition rule is stronger evidence than any platform's claim about itself.
  What is missing is any **student-side** evidence that this is felt as pain (§5.1:
  "zero evidence of student-side pain") — which is precisely Q4 in Test 2.
- **Proximity has been publicly tested and produced nothing** (NearBook).
- **Trust, in the affordable form Compliance permits, is a disclaimer** (O-11) —
  except for campus-bounded identity and no-phone-number exposure, which carry no
  vouching liability and which is the one trust element with any real-world
  corroboration.

**Proposed revised thesis, for the CEO to accept, amend or reject:**

> BookHop is a **syllabus-to-shelf matching layer for edition-locked prescribed
> textbooks on a Chennai campus**: it answers "which students near me hold the exact
> prescribed edition of the book HS3152 requires, in a stated condition, this
> fortnight." The student side is **free, permanently and by design** — there is no
> transaction fee, no escrow and no custody of funds. The paying customer, if there is
> one, is the **institution** (a department, library or book bank that funds student
> book provision), not the pair of students doing the handover.

**Why this specific revision, and not a general retreat.** It is not optimism and it is
not surrender. Every clause is forced by a finding:

- Dropping the transaction fee is forced by **O-10**, which is a contradiction no
  driver value can resolve, and it is what Finance's own §10 concludes before §11
  reverses it. Dropping it also removes, in one move: the `fee_collection_rate`
  problem, the disintermediation risk to revenue (defection is free, so make it free),
  the PPI question, the escrow build, and most of the CP(E-Commerce) r.5/r.6 exposure.
- Naming the institution as payer is forced by **O-12** — but, unlike Finance's §11, it
  is proposed **as a hypothesis with a Rs 0 test attached** (Test 3), not as a
  recommendation. If three librarians cannot name a budget line, this revision dies in
  five days for nothing, which is the point.
- Narrowing to edition-locked prescribed textbooks is forced by **DISCOVERY §2.3** —
  the photocopy shop wins everywhere except whole-book, whole-semester need — and by
  **§5.1**, the only leg with commercial corroboration. It also implies cutting general
  reading from v1, which O-8 shows T4 was measuring in the wrong unit anyway.
- Cutting direct swap is forced by **O-9**.

**What would kill this revision, stated before the data arrives:** three librarians
with no budget line (Test 3); or fewer than 30 completed handovers in a seeded
fortnight at one campus with the fee removed entirely (Test 1) — because if nobody
transacts when it is *free*, the utility is not real and no payer exists on either
side.

**What I am explicitly not recommending.** I am not recommending a kill. The case for
killing rests on a model that cannot represent the thing it measures (O-1), two
unmeasured inputs, and a competitive record about other people's execution of a product
that combined none of campus identity, same-day handover and edition matching. That is
not enough to stop. It is more than enough to refuse to write code.

---

## 6. Conditions on the G1 pass

Recommended to `ceo-planning` for `DECISIONS.md`:

1. **No code before Test 1 reports.** G2 entry is blocked on the concierge pilot, not
   on a PRD.
2. **Record the 6% transaction fee as falsified** on the strength of O-10, and remove
   it from every downstream document, including the PRD and the model's base case.
   Re-open only if Test 1's fee arm clears both bars.
3. **Finance to restate §1, §8 and §11.** §1 must say which case "no breakeven" applies
   to and that CAC sits inside contribution; §8 must print contribution per transfer
   alongside the total; §11 must carry `ASSUMPTION:` tags or be withdrawn pending
   Test 3.
4. **Product to apply the four threshold fixes (O-6 to O-9) before any interview is
   booked.** This expires the moment fieldwork starts.
5. **Cut direct swap and general reading from v1 scope.** Both are negative-cost
   decisions.
6. **Both CRITICAL objections (O-1, O-10) escalate to the founder** per charter, and
   neither is resolved by this memo — O-1 is resolved by Test 1 and O-10 by Test 1's
   A/B arm.
7. **Compliance's P1–P14 pilot blockers stand unchallenged**, and `r.4(1)(a)`
   (incorporation as a company) has a lead time that should start now if any in-scope
   pilot is intended.

---

*Prepared by the Red Team agent. Every objection carries a test with a threshold.
No evidence was invented; where a number is needed and does not exist, it appears above
as a test rather than as an assumption. All model figures marked `[ran]` are output
from `company/finance/model.py`, unmodified, with the named driver overridden.*
