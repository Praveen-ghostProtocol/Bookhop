# BookHop Financial Model — TAM / SAM / SOM and Unit Economics

Owner: `market-finance` · Version: **v1.1 (corrected after Red Team G1 review)** · Date: 2026-10-21
v1.0 superseded. See §0 for exactly what was overstated and what now stands.
Denominator work: `company/evidence/MARKET-SIZING.md`
Editable driver sheet: `company/finance/model.csv`
Arithmetic script (reproducible): `company/finance/model.py` — every figure in
this document is printed by `python -I model.py`. Change a driver there or in the
CSV and re-run to regenerate the whole model.

Evidence standard: `company/README.md` §8. Every number is sourced with a URL and
date, or tagged `ASSUMPTION:` with reasoning and the test that would replace it.

---

## 0. Correction notice — what v1.0 overstated

Red Team re-ran `model.py` across 14 CAC sweeps (`evidence/RED-TEAM/G1-MEMO.md`
O-1, O-2, O-12) and found four defects in how v1.0 reported its own arithmetic.
All four are reporting defects, not arithmetic errors: **no driver value and no
output number has changed.** What changed is what this document claims they mean.
Required by `DECISIONS.md` D-006 condition 5.

| # | v1.0 said | Correct statement | Where fixed |
|---|---|---|---|
| **C-1** | "There is no volume at which this reaches breakeven" — stated universally | True of **low and base**. **Not** true of high: at high drivers the verdict turns entirely on CAC, with breakeven at **Rs 12.29 per registered user**, against a published high assumption of Rs 25. The claim was never tested at high and should not have been written as universal | §1, §6.2, §4 |
| **C-2** | "Contribution margin is negative at **every** case, including high" | Negative at all three **published CAC values**, which is a different and much weaker statement. CAC and infrastructure sit inside `contribution` (`model.py` line 128) and are charged **per registered user, not per transfer**, so `contribution` is not a marginal measure. At high drivers with CAC = 0, contribution is **+Rs 86,386 (+Rs 9.11/transfer)** | §1, §4, §6.1, §6.2 |
| **C-3** | §8 "growth is the problem"; "the driver that goes the wrong way" | A total, held at fixed `registered`. **Per transfer the same sweeps move the other way:** raising activation 0.30 → 0.90 improves the fully-loaded unit from −Rs 153.27 to −Rs 56.98, a **2.7× improvement**. The correct statement is "a negative marginal makes volume costly", not "growth is the problem" | §8 |
| **C-4** | −Rs 153.27 per transfer presented as the cost of a transaction | **94% of it is CAC + infrastructure per registered user divided by 0.54 transfers per registered user.** It measures acquiring **1.85 registrations per transaction**; it is not what a transaction costs | §6.1 |

**And one defect that is not a reporting defect.** The model is **strictly
linear** and contains no mechanism by which the unit improves with density,
automation, referral or repeat use. `model.py` now proves this in its own output:
contribution per transfer is **Rs 9.11 at one campus, Rs 9.11 at three campuses and
Rs 9.11 across all of Chennai metro** — identical to the paisa across a 49× range.
Every "growth makes it worse" and every "monopoly is profitable" conclusion in v1.0
is therefore an assumption restated as an output. **This model must not be used to
reject scale.** Filed as **R-23**; §12 states why no mechanism is being added yet.

**What stands, unchanged and now more narrowly stated.**

1. **The base case fails independently of CAC, and this is the robust finding.**
   Breakeven CAC at base is **negative Rs 22.77** — at CAC = 0 the base case still
   loses **Rs 62,675 (−Rs 42.16/transfer)**. No acquisition improvement rescues it.
   This is the one verdict in the document that survives every attack made on it.
2. **The 6% take rate is falsified** (D-006 condition 1). Minimum take rate to cover
   support and payment processing alone is 16.7% at base; Red Team pushed price to
   Rs 500 and marginal contribution moved only −Rs 8.83 → −Rs 4.79.
3. **Price is not the lever**, and the five-output-line discipline (§2) stands.
4. **§11's institutional/buyback recommendation is withdrawn as strategy**
   (D-006 condition 6). It carried zero sources. It survives as a hypothesis with a
   Rs 0 test attached: `evidence/INSTITUTIONAL-PROBE.md`.

---

## 1. The verdict, up front

**At base-case drivers, no. A student-only local used-book marketplace in Chennai
cannot be a sustainable business — and that conclusion does not depend on
acquisition cost.** At high drivers the question is open and turns on one
unmeasured number.

Three statements, in descending order of how well-evidenced they are.

**(1) The base case fails, and fails robustly.** One completed transfer produces
**Rs 4.94 of collectible revenue** against **Rs 13.77 of marginal cost** (support
Rs 12.00 + payment processing Rs 1.77): **marginal contribution −Rs 8.83 per
transfer.** Set acquisition cost to **zero** and the base case still loses
**Rs 62,675 a year at three campuses, −Rs 42.16 per transfer** `[ran]`. Breakeven
CAC at base is **negative Rs 22.77** — i.e. we would have to be *paid* Rs 22.77 to
register each user. **This is not a CAC artifact and no acquisition improvement
rescues it.** It is the strongest negative finding in Phase A.

**(2) The high case is a different question, and it turns on CAC alone.** At high
drivers marginal contribution is **+Rs 15.03 per transfer**, and the full
contribution line is negative only because CAC and infrastructure — both charged
**per registered user, not per transfer** — sit inside it. Breakeven is at
**Rs 12.29 of CAC per registered user** `[ran]`, against a published high
assumption of Rs 25:

| CAC per registered user | Contribution (3 campuses, high drivers) |
|---:|---:|
| Rs 25 (published high) | −Rs 89,288 |
| **Rs 12.29** | **Rs 0 — breakeven** |
| Rs 0 | +Rs 86,386 (+Rs 9.11/transfer) |

Rs 12.29 per registration on a single campus has **never been measured**. It is not
obviously achievable and not obviously absurd. Test 1 measures it.

**(3) The model cannot answer what happens with density, and must not be used to
try.** It is strictly linear: contribution per transfer is Rs 9.11 at one campus,
three campuses and all of Chennai metro alike `[ran]`. So the Rs 7.34 lakh
"Chennai monopoly" ceiling in §10 is Rs 9.11 × 1,35,533 transfers less Rs 9 lakh of
fixed cost — arithmetic, not evidence about whether a marketplace's unit improves
with density. **Read §10's ceiling as what this model assumes, not as what the
business would do.** See §12 and R-23.

**The one number that decides everything is a cost, not a revenue.**
`support_cost_per_transfer` at Rs 12 is the only driver in the model that can flip
the sign of the unit, and it has never been observed. At Rs 30,000/month fully
loaded it is **4.2 minutes of human time per completed handover including every
dispute and no-show**. Measure that before anything else.

§10 gives the full reasoning, §11 the adjacent markets (now hypotheses, not
recommendations) and §12 the standing limitation.

---

## 2. Model structure

Five output lines, kept strictly separate. They are different numbers and
conflating them is the most common way this category is oversold.

| Line | Definition |
|---|---|
| **Book value moved** | Σ stated book price across **all** completed transfers, including swaps and gifts. Measures activity. **Not revenue, not GMV.** |
| **Cash GMV** | Σ stated price across the subset where money actually changes hands. Swaps contribute **zero**. Gifts contribute **zero**. |
| **Platform revenue** | Fees **actually collected** = cash GMV × take rate × fee-collection rate. |
| **Contribution margin** | Revenue − variable cost (payment processing + support + infrastructure + CAC). |
| **Profit** | Contribution margin − fixed cost. |

One **transfer** = one book changing hands. A two-person direct swap is therefore
**two transfers**, both contributing to book value moved and neither to cash GMV.

### Funnel

```
students (sourced)
  × pct_adult × pct_book_active          → addressable
  × signup_rate_y1                        → registered
  × activation_rate                       → active participants
  × transfers_per_active_yr               → transfers
  × avg_book_price_inr                    → BOOK VALUE MOVED
  × (1 − swap_share) × (1 − gift_share)   → cash transfers → CASH GMV
  × take_rate × fee_collection_rate       → PLATFORM REVENUE
  − pg_cost − support − infra − CAC       → CONTRIBUTION MARGIN
  − fixed_cost                            → PROFIT
```

---

## 3. Drivers — every row with low / base / high

`ASSUMPTION:` tags carry the reasoning inline. The machine-readable version with the
replacement test for each row is `model.csv`.

### 3.1 Denominator

| Driver | Low | Base | High | Basis |
|---|---:|---:|---:|---|
| `students` — TAM | 3,96,64,479 | 3,96,64,479 | 3,96,64,479 | **Sourced.** AISHE 2023-24 Table 6(a), All-India regular mode |
| `students` — SAM | 3,20,000 | 4,60,000 | 6,50,000 | `ASSUMPTION:` Chennai metro regular-mode enrolment. No official figure exists — see `MARKET-SIZING.md` §4. Range spans 2.03× |
| `students` — SOM | 32,197 | 32,197 | 32,197 | **Sourced.** Anna University departments 11,940 + Loyola 9,347 + DG Vaishnav 10,910, all from NIRF filings |

### 3.2 Addressability

| Driver | Low | Base | High | Basis |
|---|---:|---:|---:|---|
| `pct_adult` | 0.90 | 0.95 | 0.97 | `ASSUMPTION:` Pilot is verified **adults** only. TN UG entry is typically 17–18, so a minority of first-years are under 18. **Test:** date-of-birth distribution from any one pilot campus registrar, or the age field at sign-up in week one |
| `pct_book_active` | 0.35 | 0.60 | 0.75 | `ASSUMPTION:` Share on courses where physical books actually change hands. Engineering and CS cohorts run substantially on PDFs and lab manuals; arts, law, medicine and commerce remain physical. The low case assumes the digital shift is further along than we think — a real risk, not a formality. **Test:** 100-student intercept survey across two course types, asking how many physical books they bought or were given this semester |

### 3.3 Participation

| Driver | Low | Base | High | Basis |
|---|---:|---:|---:|---|
| `signup_rate_y1` | 0.04 | 0.15 | 0.30 | `ASSUMPTION:` Replaces half of the founder's "20% participation". A concentrated on-campus push beats diffuse national signup. **Benchmark:** Clankart reached 25,000+ registered students across all of India ([Starter Story](https://www.starterstory.com/stories/clankart), accessed 2026-10-21) — the low case assumes we land nearer that diffuse rate. **Test:** registrations in the first 6 weeks of pilot, against the campus addressable base |
| `activation_rate` | 0.10 | 0.30 | 0.45 | `ASSUMPTION:` Registered → at least one completed transfer. This is the cold-start tax and it is where two-sided marketplaces die. **Test:** pilot cohort telemetry at 90 days |
| `transfers_per_active_yr` | 1.10 | 1.80 | 3.00 | `ASSUMPTION:` Replaces the founder's "2 per student per year" — note the **denominator change**: per *active participant*, not per enrolled student. Capped by the trading window (§7). **Test:** completed transfers per activated user over one full academic year |

### 3.4 Transaction mix

| Driver | Low | Base | High | Basis |
|---|---:|---:|---:|---|
| `swap_share` | 0.40 | 0.20 | 0.10 | `ASSUMPTION:` Share of transfers that are direct two-person swaps. **Swaps are revenue-poison** — full book value moved, zero cash GMV, full support cost. The low case assumes students strongly prefer barter, which is exactly what a cash-averse campus culture would produce. **Test:** transaction-type split in pilot |
| `gift_share_of_nonswap` | 0.30 | 0.15 | 0.08 | `ASSUMPTION:` **NO SOURCE EXISTS.** Share of non-swap transfers where the book is given away free. The competitor audit identifies this as one of the two numbers that decide the business: it suppresses cash GMV without suppressing book value moved. **Required Phase A measurement, not an estimate.** Instrument: survey question ("the last textbook you passed on — sold, swapped, or given away?") plus direct observation at one semester-end |
| `avg_book_price_inr` | 140 | 220 | 350 | `ASSUMPTION:` Replaces the founder's Rs 300. **Test (cheap, do it now):** scrape 200+ Chennai used-book listings on OLX and Clankart, and photograph price lists at Moore Market and Pondy Bazaar second-hand sellers |

### 3.5 Monetization

| Driver | Low | Base | High | Basis |
|---|---:|---:|---:|---|
| `take_rate` | 0.00 | 0.06 | 0.10 | `ASSUMPTION:` Low case is **zero**, and that is deliberate — on a Rs 200 book handed over in person, a fee is trivially avoided and may be refused outright. **Test:** A/B a 5% fee against free in the pilot and measure completion-rate delta |
| `fee_collection_rate` | 0.20 | 0.55 | 0.80 | `ASSUMPTION:` Share of nominally-chargeable transfers where the fee is actually collected. **This is the structural weakness of local handover:** buyer and seller meet in person, so settling in cash off-platform costs them nothing and saves them the fee. **Test:** reconcile in-app completions against listings marked sold-elsewhere or silently delisted |

### 3.6 Costs

| Driver | Low | Base | High | Basis |
|---|---:|---:|---:|---|
| `inapp_payment_share` | 0.20 | 0.50 | 0.75 | `ASSUMPTION:` Share of cash transfers paid inside the app rather than hand-to-hand. **Test:** pilot payment-method telemetry |
| `pg_cost_pct` | 0.0236 | 0.0236 | 0.0099 | **Sourced.** [Razorpay pricing](https://razorpay.com/pricing/), accessed 2026-10-21: UPI carries zero MDR by mandate but Razorpay charges a **2% platform fee**, plus 18% GST = **2.36%**. High case uses the **0.99% UPI QR** rate from the same page. Route (payment splitting), which a marketplace needs, adds **0.1% + platform fee** |
| `support_cost_per_transfer` | 30 | 12 | 6 | `ASSUMPTION:` Human minutes per transfer — disputes, no-shows, condition complaints, handover coordination. **Test:** support-ticket minutes per completed transfer in pilot. This is the cost that kills the unit; measure it first |
| `infra_cost_per_user_yr` | 40 | 18 | 8 | `ASSUMPTION:` Hosting, storage, image CDN, SMS/OTP, per registered user per year. **Test:** actual cloud bill ÷ registered users at month 3. CTO owns the real quote |
| `cac_per_registered_user` | 180 | 60 | 25 | `ASSUMPTION:` Campus activation — posters, ambassadors, stalls, referral incentives. **Test:** total acquisition spend ÷ registrations in the first pilot term |
| `fixed_cost_y1_inr` | 15,00,000 | 9,00,000 | 5,00,000 | `ASSUMPTION:` Year-one fixed cost at 2–3 campuses — part-time operations staff, tooling, compliance. **Test:** actual. Founder owns all spend |

---

## 4. TAM — India higher education, regular mode

Denominator: **3,96,64,479** (AISHE 2023-24, Table 6(a)).

**Why TAM is built bottom-up and not from a market report.** We found no credible
primary source for the Indian used-book market. The Credence Research "USD 781m"
figure is a vendor landing page with no published methodology and **is excluded
from this model**. Building TAM from AISHE enrolment with the same driver stack as
SAM and SOM is auditable and internally consistent; importing an unverifiable
number is not. The consequence is that TAM is *definitionally* the ceiling of this
business model, not the size of the used-book category.

| Line | Low | Base | High |
|---|---:|---:|---:|
| Students | 3,96,64,479 | 3,96,64,479 | 3,96,64,479 |
| Addressable | 1,24,94,311 | 2,26,08,753 | 2,88,55,908 |
| Registered | 4,99,772 | 33,91,313 | 86,56,773 |
| Active participants | 49,977 | 10,17,394 | 38,95,548 |
| Transfers | 54,975 | 18,31,309 | 1,16,86,643 |
| **Book value moved** | Rs 76,96,496 | **Rs 40,28,87,979** | Rs 4,09,03,25,026 |
| **Cash GMV** | Rs 32,32,528 | **Rs 27,39,63,826** | Rs 3,38,67,89,122 |
| **Platform revenue** | Rs 0 | **Rs 90,40,806** | Rs 27,09,43,130 |
| **Contribution margin** | −Rs 11,16,14,442 | **−Rs 28,06,90,085** | −Rs 10,99,97,131 |
| **Profit** | −Rs 11,31,14,442 | −Rs 28,15,90,085 | −Rs 11,04,97,131 |

**Read the base case carefully.** If this model were rolled out across every
regular-mode student in India, it would move **Rs 403 crore of book value**, carry
**Rs 274 crore of cash GMV**, and collect **Rs 9.04 crore of revenue** — on which it
would **lose Rs 281 crore**. The gap between the book-value headline and the revenue
line is the entire pitch risk in this category.

**Corrected (C-1, C-2).** v1.0 read this table as "contribution margin is negative
at every case, including high. That is the TAM telling you the unit is broken."
That is overstated. Contribution is negative at every case **at the published CAC
values**, and `contribution` includes CAC and infrastructure charged per registered
user. At high drivers the **marginal** unit is **+Rs 15.03 per transfer**, and the
high line turns negative only through the per-registered-user block. The honest
reading of this table is: at base the unit is broken; at high the TAM line is a
statement about acquisition cost, which is unmeasured.

---

## 5. SAM — Chennai metro higher education

Denominator: **3.2 / 4.6 / 6.5 lakh**. `ASSUMPTION:` — no official Chennai figure
exists (`MARKET-SIZING.md` §4). The low/base/high here move the *denominator as well
as* the drivers, so the spread is wider than driver sensitivity alone.

| Line | Low | Base | High |
|---|---:|---:|---:|
| Students | 3,20,000 | 4,60,000 | 6,50,000 |
| Addressable | 1,00,800 | 2,62,200 | 4,72,875 |
| Registered | 4,032 | 39,330 | 1,41,862 |
| Active participants | 403 | 11,799 | 63,838 |
| Transfers | 444 | 21,238 | 1,91,514 |
| **Book value moved** | Rs 62,093 | **Rs 46,72,404** | Rs 6,70,30,031 |
| **Cash GMV** | Rs 26,079 | **Rs 31,77,235** | Rs 5,55,00,866 |
| **Platform revenue** | Rs 0 | **Rs 1,04,849** | Rs 44,40,069 |
| **Contribution margin** | −Rs 9,00,469 | **−Rs 32,55,241** | −Rs 18,02,573 |
| **Profit** | −Rs 24,00,469 | −Rs 41,55,241 | −Rs 23,02,573 |

Owning **all** of Chennai student used-book trade, at base drivers, yields
**Rs 1.05 lakh of annual revenue**. One junior salary is Rs 3.6 lakh.

---

## 6. SOM — three pilot campuses, year one

Campuses, all individually sourced from NIRF filings:

| Campus | Enrolment | District |
|---|---:|---|
| Anna University (university departments) | 11,940 | Chennai |
| Loyola College | 9,347 | Chennai |
| D.G. Vaishnav College | 10,910 | Chennai |
| **Total** | **32,197** | |

Chosen because all three are in **Chennai district** (not Chengalpattu), are single
campuses, are large, and have unambiguous primary-sourced enrolment. MCC and SRM
Arts & Science were excluded for being in Chengalpattu; SRM IST and VIT for having
non-separable multi-campus filings.

| Line | Low | Base | High |
|---|---:|---:|---:|
| Students | 32,197 | 32,197 | 32,197 |
| Addressable | 10,142 | 18,352 | 23,423 |
| Registered | 406 | 2,753 | 7,027 |
| Active participants | 41 | 826 | 3,162 |
| Transfers | 45 | 1,487 | 9,486 |
| **Book value moved** | Rs 6,248 | **Rs 3,27,038** | Rs 33,20,255 |
| **Cash GMV** | Rs 2,624 | **Rs 2,22,386** | Rs 27,49,171 |
| **Platform revenue** | Rs 0 | **Rs 7,339** | Rs 2,19,934 |
| — payment processing | Rs 12 | Rs 2,624 | Rs 20,413 |
| — support | Rs 1,339 | Rs 17,838 | Rs 56,919 |
| — infrastructure | Rs 16,227 | Rs 49,551 | Rs 56,216 |
| — CAC | Rs 73,023 | Rs 1,65,171 | Rs 1,75,675 |
| — **total variable** | Rs 90,601 | Rs 2,35,184 | Rs 3,09,222 |
| **Contribution margin** | −Rs 90,601 | **−Rs 2,27,846** | −Rs 89,288 |
| **Profit** (after fixed) | −Rs 15,90,601 | **−Rs 11,27,846** | −Rs 5,89,288 |

### 6.1 Per-unit economics — the core finding

| Metric | Low | Base | High |
|---|---:|---:|---:|
| Revenue per transfer | Rs 0.00 | **Rs 4.94** | Rs 23.18 |
| Marginal cost per transfer (support + payment processing) | Rs 30.28 | **Rs 13.77** | Rs 8.15 |
| **Marginal contribution per transfer** | **−Rs 30.28** | **−Rs 8.83** | **+Rs 15.03** |
| Fully-loaded contribution per transfer (incl. CAC + infra) | −Rs 2,030.28 | **−Rs 153.27** | −Rs 9.41 |
| Revenue per registered user per year | Rs 0.00 | **Rs 2.67** | Rs 31.30 |
| **Breakeven CAC per registered user** | −Rs 43.33 | **−Rs 22.77** | **+Rs 12.29** |

**Read the last row first.** It is the row v1.0 omitted and it changes the verdict's
shape. At low and base the breakeven CAC is **negative**: those cases fail even if
acquisition is free, which is why the base verdict is robust. At high it is
**+Rs 12.29**, so the high case is a live question about one unmeasured input.

Base-case arithmetic, shown in full:

```
revenue per transfer
  = take_rate × (1 − swap_share) × (1 − gift_share) × price × fee_collection_rate
  = 0.06 × 0.80 × 0.85 × 220 × 0.55
  = Rs 4.94

marginal cost per transfer
  = price × (1 − swap) × (1 − gift) × inapp_share × pg_cost  +  support_cost
  = 220 × 0.80 × 0.85 × 0.50 × 0.0236  +  12.00
  = 1.77 + 12.00
  = Rs 13.77

marginal contribution = 4.94 − 13.77 = −Rs 8.83 per transfer
```

**A 6% take rate on a Rs 220 book is Rs 13.20 of gross fee. After the swap share,
the gifting share and realistic collection, Rs 4.94 of it arrives. Two minutes of
human support costs more than that.** That is the business, in one sentence.

### 6.1a What the −Rs 153.27 figure actually measures (correction C-4)

v1.0 printed the fully-loaded figure without decomposing it, and it was read as the
cost of a transaction. It is not. Decomposed `[ran]`:

| Component | Per transfer | Denominated in |
|---|---:|---|
| Revenue | +Rs 4.94 | per transfer |
| Payment processing | −Rs 1.77 | per transfer |
| Support | −Rs 12.00 | per transfer |
| Infrastructure | −Rs 33.33 | **per registered user ÷ 0.54 transfers per registered user** |
| CAC | −Rs 111.11 | **per registered user ÷ 0.54 transfers per registered user** |
| **Total** | **−Rs 153.27** | |

**94% of the negative is the per-registered-user block divided by a funnel ratio of
0.54 transfers per registered user** `[ran]`. At base we acquire **1.85
registrations for every transaction that happens**. −Rs 153.27 is a statement about
that ratio — the cold-start tax — not about what a handover costs. The handover
costs Rs 13.77. Raising activation is therefore the single largest improvement
available to the fully-loaded unit (§8.3), which is the opposite of what v1.0's §8
concluded.

### 6.2 Breakeven

**There is none at low or base drivers, at any CAC.** Contribution per transfer is
negative, so no volume covers fixed cost — the loss grows with the volume. Removing
CAC entirely (year two, same cohort returning): contribution is still
**−Rs 62,675**, or **−Rs 42.16 per transfer**. Breakeven CAC at base is **negative
Rs 22.77** `[ran]`. **This is the robust finding and it does not depend on
acquisition cost.**

**At high drivers breakeven exists and sits at CAC = Rs 12.29 per registered
user** `[ran]`. v1.0's universal "no breakeven at any volume" was wrong about the
high case and is withdrawn (C-1). Nothing in the model says Rs 12.29 is reachable;
nothing says it is not. It is one of the two numbers Test 1 exists to measure.

Minimum take rate for a base-case transfer to cover **only** support and payment
processing — ignoring infrastructure, acquisition and all fixed cost:

| If support cost per transfer were | Minimum viable take rate |
|---|---:|
| Rs 12.00 (base) | **16.7%** |
| Rs 6.00 | 9.4% |
| Rs 3.00 | 5.8% |
| Rs 1.00 | 3.4% |
| Rs 0.00 | 2.1% |

A 16.7% take rate on a student's Rs 200 textbook is not collectible from people who
are standing next to each other. **The only path to a positive unit is driving
support cost per transfer below roughly Rs 3 — which means near-total automation and
effectively no dispute handling**, in a category whose entire claimed wedge is trust.

---

## 7. The trading window — timing, not averages

The competitor audit finds supply and demand peak in **antiphase**: sellers release
books at semester end, buyers need them at semester start, leaving roughly **8
trading weeks a year**. Modelled explicitly rather than smoothed:

| Case | Transfers/year | Per week (8 weeks) | Per day, across 3 campuses |
|---|---:|---:|---:|
| Low | 45 | 6 | 0.8 |
| Base | 1,487 | 186 | 26.5 |
| High | 9,486 | 1,186 | 169.4 |

Two consequences the annual averages hide:

1. **Infrastructure and staff are sized for the peak and idle for 44 weeks.**
   `infra_cost_per_user_yr` and `fixed_cost_y1_inr` are therefore charged against
   8 weeks of revenue, not 52. This is already in the model but it is worth saying
   out loud: the effective cost per trading week is 6.5× the naive annual rate.
2. **Antiphase means inventory must be *held*, not matched.** A seller in May and a
   buyer in July do not meet in a pure matching marketplace. Closing that gap
   requires either storage (an inventory business with working capital and shrinkage)
   or a credit system (which `README.md` §1 defers pending payment-rules review).
   Direct swap — the model's third transaction type — is the one mechanism that
   *requires* both parties present simultaneously, so it is the **worst fit** for an
   antiphase market and also the one that generates zero cash.

---

## 8. Sensitivity on the three drivers that matter most

SOM year one, all other drivers at base. **Restated per D-006 condition 5 and
correction C-3.** v1.0 printed only the total contribution column, which falls
mechanically whenever transfers are added at a negative marginal while `registered`
is held fixed. That is arithmetic with no information in it. The per-transfer
columns below are the ones that carry the finding, and two of the three move the
*opposite* way to the totals.

Output pasted verbatim from `python -I model.py`:

```
fee_collection_rate:
     value   transfers      cash GMV     revenue  contribution  contrib/xfer  marginal/xfer      profit
      0.00       1,487       222,386           0      -235,184       -158.21         -13.77  -1,135,184
      0.20       1,487       222,386       2,669      -232,516       -156.41         -11.97  -1,132,516
      0.40       1,487       222,386       5,337      -229,847       -154.62         -10.17  -1,129,847
      0.55       1,487       222,386       7,339      -227,846       -153.27          -8.83  -1,127,846
      0.70       1,487       222,386       9,340      -225,844       -151.93          -7.48  -1,125,844
      0.90       1,487       222,386      12,009      -223,176       -150.13          -5.69  -1,123,176

transfers_per_active_yr:
     value   transfers      cash GMV     revenue  contribution  contrib/xfer  marginal/xfer      profit
      0.80         661        98,838       3,262      -220,555       -333.83          -8.83  -1,120,555
      1.10         908       135,902       4,485      -222,742       -245.19          -8.83  -1,122,742
      1.50       1,239       185,321       6,116      -225,658       -182.16          -8.83  -1,125,658
      1.80       1,487       222,386       7,339      -227,846       -153.27          -8.83  -1,127,846
      2.50       2,065       308,869      10,193      -232,949       -112.83          -8.83  -1,132,949
      3.50       2,890       432,417      14,270      -240,240        -83.11          -8.83  -1,140,240

activation_rate:
     value   transfers      cash GMV     revenue  contribution  contrib/xfer  marginal/xfer      profit
      0.05         248        37,064       1,223      -216,909       -875.50          -8.83  -1,116,909
      0.10         496        74,129       2,446      -219,096       -442.16          -8.83  -1,119,096
      0.20         991       148,257       4,892      -223,471       -225.50          -8.83  -1,123,471
      0.30       1,487       222,386       7,339      -227,846       -153.27          -8.83  -1,127,846
      0.40       1,982       296,514       9,785      -232,220       -117.16          -8.83  -1,132,220
      0.50       2,478       370,643      12,231      -236,595        -95.50          -8.83  -1,136,595
      0.90       4,460       667,157      22,016      -254,093        -56.98          -8.83  -1,154,093
```

### 8.1 `fee_collection_rate`

The only one of the three whose **marginal** column moves at all: 0.00 → 0.90 takes
the marginal unit from −Rs 13.77 to −Rs 5.69. It does not reach zero. Driving
collection to a perfect 90% moves annual profit by **Rs 12,009**. The
highest-leverage revenue driver in the model cannot flip the sign. (It is also the
driver D-006 condition 1 falsified outright; see O-10.)

### 8.2 `transfers_per_active_yr` — corrected

v1.0 called this "the driver that goes the wrong way" and read the falling profit
column as evidence. **Withdrawn.** The marginal column is flat at −Rs 8.83 by
construction: the sweep holds `registered` fixed and adds transfers at a fixed
negative marginal, so total contribution *must* fall. Meanwhile the fully-loaded
unit **improves 4.0×**, from −Rs 333.83 at 0.80 transfers to −Rs 83.11 at 3.50,
because the per-registered-user block is spread over more transactions.

**Correct statement: a negative marginal makes volume costly.** Not "growth is the
problem" — that phrasing would have argued against the intervention that most
improves the unit.

### 8.3 `activation_rate` — corrected

Same correction, larger effect. Raising activation **0.30 → 0.90 improves the
fully-loaded unit 2.7×, from −Rs 153.27 to −Rs 56.98** `[ran]`, while total
contribution falls by Rs 26,247. Both are true; only the first is about the
business. Activation is the direct inverse of the 1.85-registrations-per-transaction
ratio in §6.1a, and it is the largest lever on the fully-loaded figure anywhere in
this model.

**The conclusion from all three, restated.** No revenue-side driver can flip the
marginal sign; exactly one cost driver (`support_cost_per_transfer`) can. The
binding constraint is a cost denominated in human minutes against a revenue
denominated in a percentage of a cheap object. **But the fully-loaded figure is a
different problem with a different fix:** it is dominated by acquiring 1.85
registrations per transaction, and activation is what fixes that. v1.0 conflated
the two and concluded "growth is the problem" from the conflation.

---

## 9. Reality check against the only real revenue data in this category

Per the competitor audit, five comparable teams have hit the same ceiling. The one
with published numbers:

**Clankart** — student-to-student used books, pan-India, 25,000+ registered
students, roughly **USD 1,200/month**, founder describes it as "still a part-time
gig" ([Starter Story, 2023-01-02](https://www.starterstory.com/stories/clankart),
accessed 2026-10-21).

`ASSUMPTION:` INR/USD = 88. Clankart annual revenue ≈ **Rs 12,67,200** across 25,000
registered users = **Rs 50.69 revenue per registered user per year.**

| | Revenue per registered user per year |
|---|---:|
| Clankart (actual) | **Rs 50.69** |
| BookHop SOM, low | Rs 0.00 |
| BookHop SOM, **base** | **Rs 2.67** |
| BookHop SOM, high | Rs 31.30 |

**Our base case is 19× below the only real revenue datapoint in the category, and
even our high case is below it.** This model does not out-forecast any real player —
it under-forecasts all of them. The pessimism is therefore not the model's
construction; it is what happens when the five output lines are kept separate and
fee collection is treated honestly.

Two caveats, stated so this comparison is not over-read:
- Clankart's revenue mechanism is **not confirmed to be commission**. The founder
  describes it as "a free platform". A 10% fee is attributed to it in the competitor
  audit but we could not verify it on Clankart's own site. If the USD 1,200 is
  advertising or listing-promotion revenue, the comparison is to a different
  business model and a commission marketplace would do *worse*, not better.
- Clankart ships nationally. BookHop's local handover removes shipping cost but
  **also removes the enforcement point for the fee** — which is precisely what
  `fee_collection_rate` captures.

**If a future version of this model produces revenue materially above Clankart's
actual, the reviewer should reject it unless it names a specific mechanism BookHop
has that Clankart does not.** We could not name one.

---

## 10. The frank answer

### Can a student-only local used-book marketplace be a sustainable business?

**No.** Four structural reasons, in order of severity:

**1. The object is too cheap to carry a human.** A used campus textbook is Rs 140–350.
Any defensible take rate yields Rs 8–35 of gross fee. A single support interaction —
a no-show, a condition dispute, a "he never paid me" — costs more than the fee on
several books. Marketplaces in cheap physical goods survive only by eliminating human
cost per transaction, which requires either scale we cannot reach in this segment or
an abandonment of the trust mediation that is the stated wedge.

**2. Local handover destroys the fee enforcement point.** The product's core
advantage — buyer and seller meet in person — is also the mechanism by which they
settle in cash and route around the platform at zero cost to themselves. Shipping
marketplaces can charge because they hold the goods. Payment marketplaces can charge
because they hold the money. A local-handover marketplace holds neither, and
`fee_collection_rate` is the model's name for that structural hole.

**3. Antiphase demand compresses the business into 8 weeks.** Supply peaks when
demand is absent. Fixed and infrastructure costs are annual; revenue is not. Closing
the gap requires holding inventory (a different business, with working capital and
shrinkage) or issuing credits (deferred by `README.md` §1 pending payment-rules
review). Direct swap, one of the three launch transaction types, requires both
parties present at once, making it the worst-fitted mechanism in an antiphase market
and the one that produces zero cash.

**4. Swaps and gifts strip the cash out of the activity.** At base, 32% of book value
moved carries no money at all, and the model's own product thesis actively encourages
one of those two (swap). The headline "book value moved" can look impressive while
cash GMV, and therefore revenue, stays small. This is the specific way this category
gets oversold, and it is why the five output lines are kept separate here.

### What the ceiling actually looks like

Best honest case — **every** driver at high, acquisition entirely organic (CAC = 0),
infrastructure at Rs 8/user/year:

| Scope | Transfers | Book value moved | Cash GMV | Revenue | Contribution | Profit |
|---|---:|---:|---:|---:|---:|---:|
| 3 pilot campuses | 9,486 | Rs 33,20,255 | Rs 27,49,171 | Rs 2,19,934 | +Rs 86,386 | −Rs 4,13,614 |
| **All Chennai metro** | 1,35,533 | Rs 4,74,36,638 | Rs 3,92,77,536 | **Rs 31,42,203** | **+Rs 12,34,208** | **+Rs 7,34,208** |

At three campuses, the best case still loses Rs 4.1 lakh and would need **31
campuses** to cover Rs 9 lakh of fixed cost at that contribution rate.

> **Linearity warning (R-23) — read before quoting the Rs 7.34 lakh figure.**
> The two rows above differ only in the number of students. Contribution per
> transfer is **Rs 9.11 in both**, and Rs 9.11 at a single campus too `[ran]` —
> identical to the paisa across a 49× range. The Chennai-metro row is therefore
> **Rs 9.11 × 1,35,533 transfers − Rs 9,00,000 fixed**, nothing more. It is the
> model's *assumption* that the unit does not improve with density, restated as an
> output. It is **not** evidence that a monopoly would earn Rs 7.34 lakh, and it is
> **not** evidence that scale cannot help. The model is silent on density. See §12.

At total Chennai monopoly with every assumption favourable **and no density effect
of any kind**, the business produces **Rs 7.3 lakh of annual profit** and funds
**8.7 salaries**. That is the ceiling *of this model*, at a driver set we have no
evidence for. Whether it is the ceiling of the business is a question this model
cannot answer.

### What this does not say

It does **not** say stop. It says the **monetization thesis** is dead, not the
**product thesis**. BookHop may still be the best way for a Chennai student to find a
nearby book and trust the handover — `README.md` §1's thesis is about utility, and
nothing here contradicts it. What the model shows is that **this utility cannot be
charged for at this scope.** Phase A should therefore test whether the utility is
real, while treating "we will take 6%" as already falsified.

The three cheapest measurements that would change this verdict, in order:

1. **`support_cost_per_transfer`.** If it is genuinely under Rs 3 — fully automated,
   near-zero disputes — the unit turns positive at a 6% take rate. Measure it in the
   first 50 transfers.
2. **`gift_share_of_nonswap`.** Unsourced, and it sets the ceiling on cash GMV.
   Required Phase A primary research (§3.4).
3. **`avg_book_price_inr`.** If the real Chennai figure is Rs 400+ rather than Rs 220
   — plausible for medical and law texts specifically — the fee per transfer nearly
   doubles. Scrapeable this week at zero cost.

---

## 11. Adjacent markets — hypotheses, not recommendations

> **WITHDRAWN AS STRATEGY.** `DECISIONS.md` **D-006 condition 6** rejected v1.0's
> "institutional channel first, then buyback" recommendation. Two reasons, both
> correct and both mine to own:
> 1. **It carried zero sources.** No figure in `COMPETITORS.md`,
>    `MARKET-SIZING.md`, `COMPLIANCE.md` or `DISCOVERY.md` establishes that any
>    Indian college library or department holds a discretionary budget line for
>    student book provision, who approves it, or that any Chennai institution has
>    ever transacted this way. The same document that refused the Credence Research
>    TAM figure for want of methodology proposed a pivot with no methodology at all.
>    That is an inconsistency in my own evidence standard, not a close call.
> 2. **Buyback is contradicted by evidence in my own file.** `COMPETITORS.md` §3.2:
>    Bookchor's consumer buyback arm "Dump" is **Delhi-only after operating since
>    2015**, and §3.7: ChennaiUsedBooks already runs a free van, a published rate
>    card and on-the-spot cash in Chennai. Buyback is not an unoccupied escape
>    hatch; it has an incumbent in the pilot city and a ten-year negative datapoint
>    on scaling.
>
> **Every row below is now tagged `ASSUMPTION:` and none is a recommendation.**
> Row 1 has a Rs 0 falsification test attached and approved by the founder (D-007
> item 4): `company/evidence/INSTITUTIONAL-PROBE.md`. **If three librarians cannot
> name a budget line and an approver, row 1 is dead and this section is deleted
> rather than re-argued.** No other row has a test and none should be acted on.
>
> **Declared interest.** I proposed this direction. The probe was therefore built
> against my own incentive to confirm it — its negative-result criteria are stated
> before its questions and are not mine to revise after the answers arrive.

`ASSUMPTION:` **every cell in the table below.** Ranked by judgement of revenue
potential ÷ cost of entry, where "cost" means trust, operations and compliance.
**No cell carries a source. The ranking is reasoning, not evidence**, and the
reasoning is only as good as the structural problems it claims to fix — which are
themselves drawn from a model §12 says cannot represent density.

| # | Market | What it fixes | Trust cost | Ops cost | Compliance cost | Verdict |
|---|---|---|---|---|---|---|
| **1** | **Institutional / library channel** — bulk buy-in from departments, libraries, hostel clear-outs; supply to junior cohorts | Solves **antiphase** (institution holds between terms) and **cheap-object** (one transaction, hundreds of books) | **Low** — the institution is the trust anchor; no stranger-matching | **Medium** — needs storage and cataloguing | **Medium** — campus agreements are a founder-reserved legal commitment (`README.md` §2); GST on institutional sales | **Strongest. Pursue first.** Highest revenue per transaction, lowest trust cost, and it uses the campus relationship the pilot is already building |
| **2** | **Non-student public in the same city** | Multiplies the denominator ~10× without new ops | **High** — verified-adult campus identity is the pilot's entire safety model; public handover loses it | **Medium** — moderation volume rises sharply | **High** — DPDP obligations widen; consumer-protection e-commerce rules bind harder without a campus intermediary | Viable but it **trades away the wedge**. Do not do it before trust mechanics are proven on campus |
| **3** | **Buyback (platform buys, platform resells)** | Fixes **fee enforcement** (platform owns the goods) and **antiphase** (platform holds) — the two deepest structural problems | **Low** — one counterparty, you | **High** — working capital, storage, pricing, shrinkage, dead stock. A different business | **Medium** — inventory, GST, returns | **Structurally the real fix**, and the honest answer to "how does this make money". But it is an inventory business, not a marketplace, and needs founder-reserved spend |
| **4** | **Notes, question banks, lab records, course materials** | Near-zero marginal cost; no antiphase; digital delivery removes support cost | Low | **Low** — the best ops profile of any option | **High** — copyright on institutional material is a serious exposure; needs `privacy-compliance` review before any test | High margin, but the compliance question is genuinely unresolved and must be answered first |
| **5** | **Rentals** | Raises revenue per book (multiple cycles from one object) | Medium — deposits and damage disputes | **High** — recovery, condition grading, deposit handling | **High** — deposits may constitute a payment-system activity; same review gate as the deferred credit system | Attractive economics, heavy ops. Not a Phase A candidate |
| **6** | **Other cities** | Multiplies the denominator | Low — same model | **High** — every city is a fresh cold start, and the antiphase window is simultaneous nationally, so staff cannot be shared across cities | Low | **Does not fix the unit.** Multiplying a negative contribution margin by eight cities makes it eight times worse. **Only after the unit is positive** |
| **7** | **Shipping / pan-India delivery** | Removes geographic matching constraint | Medium | **High** — Rs 40–80 of logistics on a Rs 220 object | Medium | **Rejected.** Shipping cost exceeds the entire fee. This is the specific wall Clankart is already standing at |
| **8** | **New books** | Larger denominator, higher price point | Low | Medium | Medium | **Rejected.** Amazon and Flipkart own it, publisher margins are 10–25% and already competed away. No wedge |

### Sequence — withdrawn

v1.0 recommended "institutional/library channel (1) first, then buyback (3)".
**That recommendation is withdrawn** per D-006 condition 6 and is replaced by one
sentence: **row 1 is a hypothesis under test and nothing else here is actionable.**
The test is `evidence/INSTITUTIONAL-PROBE.md`, costs Rs 0 and reports in 5 days.

Two statements survive from v1.0 and are kept because neither is a pivot:

- **Rows 2–8 require founder-reserved authorities** (campus legal agreements and
  spend, `README.md` §2). None can be tested by an agent.
- **Do not pursue other cities (6) or shipping (7) until contribution margin per
  transfer is positive and measured.** Note the narrowing forced by §12: this is a
  statement about the *marginal* unit, which is measurable, not about whether
  density helps, which this model cannot represent. The mistake to avoid is scaling
  a unit whose sign is unknown — not scaling as such.

---

## 12. Standing limitation — the model is linear, and I am not fixing that yet (R-23)

**Decision: no density, automation or CAC-decay mechanism is being added to
`model.py` before Test 1 reports. This section is the written statement D-006 and
the R-23 filing require.**

**The defect, stated plainly.** Every cost driver in the model is a constant per
transfer or per registered user. Nothing varies with cumulative volume, local
density, elapsed time or repeat use. `model.py` now proves this in its own output
and asserts on it:

```
LINEARITY SELF-CHECK - the model has NO density mechanism
  1 campus (Loyola 9,347)            transfers     2,754  contribution/transfer Rs    9.11
  3 pilot campuses                   transfers     9,486  contribution/transfer Rs    9.11
  all Chennai metro (base denom.)    transfers   135,533  contribution/transfer Rs    9.11
  -> IDENTICAL to the paisa across a 49x range. STRICTLY LINEAR (R-23 open).
```

**Why I am not adding a curve.** Any mechanism I could write today would be a shape
I chose, and I would be choosing it knowing which answer it produces. A learning
curve on support cost, a referral term on CAC, a match-rate term on liquidity —
each is defensible in the abstract and each has a free parameter (how fast) that
nothing in the evidence base constrains. Fitting that parameter to nothing is how a
model stops being auditable. The charter requires a source or a tagged assumption
with the test that replaces it; a curve shape is an assumption whose test does not
exist yet. **A visible, asserted, loudly-warned linear model is more honest than a
curved one with an invented exponent**, and it fails in a direction a reader can
see rather than one the arithmetic hides.

**What would license a mechanism, named in advance so I cannot choose it later.**
Exactly one parameter, measured by the concierge pilot (Test 1), which already
instruments it:

> **`support_minutes_per_completed_handover`, recorded per handover with a sequence
> number, over ≥ 30 handovers at one campus.**

Test 1 already requires a stopwatch on every interaction (G1-MEMO O-1, O-4). The
only addition needed is that each reading is **logged in order** — handover #1,
#2, … #30 — rather than only as a median. That is one extra column in the
spreadsheet and costs Rs 0.

**The rule I am binding myself to, before the data exists:**

| Test 1 result | What goes into the model |
|---|---|
| Regress minutes on handover sequence number. **Slope not distinguishable from zero** over ≥ 30 handovers | **Nothing.** The model stays linear and §10's ceiling stands as written |
| **Slope significantly negative** | A learning term on `support_cost_per_transfer` **fitted to the observed slope**, with the fit and its residuals published in this file. No extrapolation beyond 3× the observed handover count |
| Fewer than 30 handovers completed | **Nothing**, and the sample is reported as too small. A curve fitted to 12 points is not a mechanism |

**Two mechanisms I will not add even if asked.** (a) A CAC-decay term from
referral: Test 1 measures total spend ÷ registrations once, which gives a level and
not a slope, so there is nothing to fit. (b) A liquidity or match-rate term: it
requires two cohorts at different densities and Test 1 runs one campus. Both stay
on R-23 until an instrument exists that could falsify them.

**What a reader must take from this section.** The base-case verdict (§1) is
unaffected — it is a marginal finding and marginal arithmetic is linear whether or
not density exists. **The scale conclusions are affected and are downgraded
accordingly.** Do not use this model to reject scale.

---

## 13. Handoff notes

**To `ceo-planning` (corrected).** The gate should treat **"a student-only local
marketplace can be a business *at base-case drivers*" as falsified**, and that
falsification is robust — it holds at CAC = 0. It should **not** treat the high
case as falsified: that verdict turns on a single unmeasured number (CAC ≤ Rs 12.29
per registered user) and on `support_cost_per_transfer`, and both are measured by
Test 1. The scale conclusions in §10 are downgraded to arithmetic (§12). §11's
pivot is withdrawn; its one testable row has a Rs 0 probe attached.

**To `red-team`.** Attack surfaces, re-ranked after your memo:
(a) **`support_cost_per_transfer`** — still the only driver that can flip the
marginal sign, still unmeasured; (b) **the linearity itself** (§12, R-23) — I have
declined to add a mechanism and stated the one parameter that would license one;
attack that rule, not just the model; (c) the Chennai denominator's 2.03× range
(`MARKET-SIZING.md` §4); (d) the Clankart comparison in §9, whose revenue mechanism
is unverified — your O-5 is accepted and NearBook is the better ceiling;
(e) `gift_share_of_nonswap` — **downgraded** on your O-3 sweep: it moves the unit by
Rs 0.56 across its entire range and I was wrong to call it decisive for the unit.
It remains decisive for the *product* thesis and that distinction is now explicit.
One thing I did not concede: your O-9 weakens the antiphase case, and the model's
8-week trading window (`model.csv` `trading_weeks_per_year`) still rests on it with
no source. The 12-month listing-date series in `INSTITUTIONAL-PROBE.md` §4 is my
attempt to source it.

**To `marketplace-ops`:** §6.1 says the business lives or dies on support minutes per
transfer. Real handover and dispute-handling costs are your input and they are the
highest-value number you can produce.

**To `cto`:** `infra_cost_per_user_yr` (Rs 18 base) is an assumption awaiting a real
quote. Note from §7 that infrastructure is sized for an 8-week peak and idle for 44
weeks — architecture that cannot scale down will fail this model badly.

---

## Appendix A — `python -I model.py`, new diagnostic sections, verbatim

Added in v1.1. No driver changed; these sections report what the model already
contained. The linearity check carries an `assert`, so the script fails loudly if a
density mechanism is ever added without updating §12.

```
LINEARITY SELF-CHECK - the model has NO density mechanism
==============================================================================
Same drivers (high, CAC=0), three scales 50x apart. If contribution per transfer
is identical, the model cannot represent ANY improvement from density, automation,
referral or repeat use - so it must not be used to argue for or against scale.
  1 campus (Loyola 9,347)            transfers     2,754  contribution/transfer Rs    9.11
  3 pilot campuses                   transfers     9,486  contribution/transfer Rs    9.11
  all Chennai metro (base denom.)    transfers   135,533  contribution/transfer Rs    9.11
  -> IDENTICAL to the paisa across a 49x range. STRICTLY LINEAR (R-23 open).
  -> The Chennai-monopoly profit figure is therefore Rs 9.11 x 135,533 transfers less fixed cost,
     i.e. an assumption of no density effect restated as an output, not evidence about one.

==============================================================================
BREAKEVEN CAC per registered user (all other drivers held at the named case)
==============================================================================
  low : contribution before CAC Rs     -17,578 over       406 registered -> breakeven CAC Rs  -43.33  [IMPOSSIBLE - negative, so CAC=0 does not rescue this case]
  base: contribution before CAC Rs     -62,675 over     2,753 registered -> breakeven CAC Rs  -22.77  [IMPOSSIBLE - negative, so CAC=0 does not rescue this case]
  high: contribution before CAC Rs      86,386 over     7,027 registered -> breakeven CAC Rs   12.29  [ACHIEVABLE - verdict turns on CAC]
  published CAC assumptions: low Rs 180 / base Rs 60 / high Rs 25

==============================================================================
WHERE THE FULLY-LOADED PER-TRANSFER FIGURE COMES FROM (base)
==============================================================================
  transfers per registered user: 0.54  (i.e. 1.85 registrations acquired per transaction)
  revenue              Rs      4.94   per transfer
  payment processing   Rs     -1.77   per transfer
  support              Rs    -12.00   per transfer
  infrastructure       Rs    -33.33   per REGISTERED USER / 0.54 transfers per registered user
  CAC                  Rs   -111.11   per REGISTERED USER / 0.54 transfers per registered user
  TOTAL                Rs   -153.27
  share of the negative that is CAC+infra: 94%
```

The full run (TAM/SAM/SOM tables, sensitivities, breakeven, Clankart check,
trading window) is reproduced by `python -I model.py` from this directory and is
unchanged from v1.0 except for the two new columns in §8.
