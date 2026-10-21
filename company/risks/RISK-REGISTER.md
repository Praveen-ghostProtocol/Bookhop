# Risk Register

Owner: CEO / Planning Agent. Reviewed every weekly loop.
Severity: Critical (can kill the company) / Material / Minor.
A risk without a **test** is a worry, not a managed risk.

**v0.2 — updated 2026-10-21 after Phase A.** Status values: `open` (no
evidence yet), `evidenced` (research has moved it, test still unrun),
`confirmed` (the bad case is now the base case), `closed` (test run, result
recorded). **No risk may be closed without the test actually having been run.**

---

## Original register, updated with Phase A evidence

| # | Risk | Sev | Owner | Test that would resolve it | Status |
|---|---|---|---|---|---|
| R-01 | Cold-start liquidity: too few books per campus for a first search to succeed | Critical | marketplace-ops | Seed one department's reading list manually; measure search-success rate before any demand spend | open |
| R-02 | Disintermediation: users meet once, then transact off-platform forever | Critical | product-manager | Interview probe Q25 + repeat-transfer @90d. Threshold T3: >50% saying they would just WhatsApp next time = thesis wrong | **evidenced** — competitor audit calls this an unexamined existential risk to the revenue model on a local-handover design; model assumes only 55% fee collection |
| R-03 | Fee viability: a transaction fee on a Rs 100-300 item cannot cover variable cost | Critical | market-finance | Bottom-up contribution margin at observed price points | **confirmed** — min take rate to cover support+PG alone is 16.7% at base; revenue/transfer Rs 4.94 vs Rs 13.77 marginal cost. See MODEL.md |
| R-04 | Seasonality: textbook demand spikes twice yearly, flat between | Material | market-finance | Month-by-month demand model; check whether general reading fills the trough | **confirmed and worse than stated** — supply and demand peak in ANTIPHASE (sellers at semester end, buyers at semester start), ~8 trading weeks/yr. Direct swap is the worst-fitted mechanism in an antiphase market and generates zero cash |
| R-05 | Counterfeit / pirated / misdescribed books | Material | marketplace-ops | Sample audit of seeded listings against physical copies | **evidenced** — compliance: pirated textbooks are a when, not an if; three takedown tracks with different clocks (IT Rules 3h, Copyright r.75 36h + 21-day hold). Prevention at listing time is far cheaper |
| R-06 | Physical safety at stranger handovers | Critical | marketplace-ops | Designated on-campus handover points only in pilot; track incidents (target zero) | **evidenced** — s79 safe harbour covers third-party information, not offline harm. Never write "safe" or "verified" in any copy |
| R-07 | Free incumbents already work (campus WhatsApp/Telegram, OLX) | Critical | market-finance | Competitor audit + a stated switching reason a student confirms in interview | **partially evidenced, gap remains** — audit could not establish how campus WhatsApp groups actually operate after 5 searches, and OLX blocked it at domain level. Named as the single biggest hole in the programme |
| R-08 | Market too small: verified students at 2-3 campuses may not be a business | Critical | market-finance | Defensible bottom-up Chennai denominator; adjacent-market analysis | **confirmed** — sourced floor 1,97,186 across 28 named campuses, but SAM remains a 2.03x range. Best realistic case across ALL of Chennai metro funds 8.7 salaries |
| R-09 | Credit system is a regulated payment instrument (RBI PPI) | Material | privacy-compliance | Primary-source review before any credit ships | **evidenced** — design (a) cash-bought = PPI, blocked. Design (b) earned/non-transferable = counsel required. Design (c) ordinal reputation = clean |
| R-10 | DPDP 2025 obligations not met | Material | privacy-compliance | Data inventory + retention schedule + deletion flow verified by QA | **evidenced** — operative provisions NOT in force until 13 May 2027. What binds today is IT Act s43A, SPDI Rules, IT Rules 2021, CERT-In 6h clock |
| R-11 | E-commerce rules / GST-TCS obligations apply once we take fees | Material | privacy-compliance | Primary-source review; identify where counsel is required | **evidenced, and it bifurcates** — GST TCS does NOT trigger on cash between users, but s194-O's Explanation deems direct payment to be paid by the operator. Opposite triggers, same transaction |
| R-12 | Campus access denied, blocking the pilot entirely | Material | marketplace-ops | Written permission request to founder before Phase D spend | **open — founder ask issued, due 2026-10-28** |
| R-13 | Support load per transfer makes the model unprofitable at scale | Material | marketplace-ops | Measure support minutes per transfer during pilot | **open and decisive** — Rs 12/transfer is UNMEASURED and is the single input that could flip the sustainability verdict |
| R-14 | We build an AI-template-looking product nobody trusts with a cash handover | Material | design-director | Two distinct directions, tested with real students | open |
| R-15 | Agents produce volume, not validated progress | Material | ceo-planning | Weekly loop compares against baseline; retire workflows that do not help | open |

---

## New risks surfaced by Phase A

| # | Risk | Sev | Owner | Test that would resolve it | Status |
|---|---|---|---|---|---|
| R-16 | **Verification liability paradox**: the more we verify, the more we may own. Trust is the proposed wedge, and every trust feature increases exposure for offline harm and for product-seller liability under the e-commerce rules | Critical | privacy-compliance + product-manager | Counsel opinion on whether condition-grading tips us into product-seller liability, and whether the handover design creates an assumed duty of care. Until answered, cap verification at identity + campus, never condition warranty | **new, evidenced** |
| R-17 | **s194-O TDS applies even though we never touch the money.** The Rs 5 lakh exemption is conditional on holding PAN/Aadhaar, which creates data liability out of all proportion to the tax | Material | privacy-compliance | CA opinion before any fee is charged. Interim position: record an asking price, not a settled consideration — an argument, not a safe harbour | **new, evidenced** |
| R-18 | **First-year Chennai undergraduates are routinely 17.** One under-18 signup bars behavioural monitoring, and our moderation and trust-scoring ARE behavioural monitoring. The cost is architectural, not a consent screen | Material | cto + privacy-compliance | Server-side 18+ gate with logged review; no Aadhaar/PAN. Counsel on what "verifiable adult" means — no prescribed standard exists | **new, evidenced** |
| R-19 | **Pilot requires incorporation as a company** (E-Com r.4(1)(a) — sole prop and LLP fail). Registration has weeks of lead time and is a founder-reserved authority | Material | ceo-planning | Founder decision. Blocks the pilot, not the research | **new — escalated to founder** |
| R-20 | **Draft RBI Master Direction 2026 removes "marketplace" from the own-goods exemption by name**, and defines marketplace in words BookHop satisfies. If notified, credit design (b) collapses into design (a) | Material | privacy-compliance | Monthly re-check of the draft MD's status. If notified, re-run the whole PPI analysis | **new, monitoring** |
| R-21 | **The category strands rather than kills.** Five comparable players hit the same ceiling; two prior attempts at this exact idea died silently with no post-mortem and no warning signal before the money was spent | Critical | ceo-planning | Pre-register the kill thresholds BEFORE spending, and honour them. The failure mode is a slow bleed that always looks one feature away from working | **new, evidenced** |
| R-22 | **The model's pessimism may be an artifact of treating CAC as variable.** PARTLY RESOLVED: red-team swept CAC over 14 runs - at HIGH drivers breakeven CAC is Rs 12.29/registered user, but at BASE the verdict holds independent of CAC. Finance is right about base | Headline says negative contribution in all three cases; the script shows the high case positive at Rs 15.03/transfer marginal and Rs 86,386 contribution when CAC is zero | Material | market-finance + red-team | Re-run model.py varying CAC independently; establish whether CAC decays with campus density | **closed - test run, result recorded in G1-MEMO.md** |
| R-23 | **The financial model has no mechanism by which the unit can improve with density.** Contribution/transfer is Rs 9.11 at one campus, three campuses and all Chennai metro - identical to the paisa. "Growth makes it worse" is therefore tautological, not a finding | Material | market-finance | Add a density/automation/CAC-decay mechanism, or state in MODEL.md that the model cannot represent improvement and must not be used to reject scale | **new - raised by red-team at G1** |
| R-24 | **O-10 re-scoped from revenue risk to EVIDENCE risk.** The real observable is repeat transfer at 90 days; a 14-day pilot structurally cannot see it. With no fee, disintermediation costs the completion record the institutional-payer thesis depends on | Critical | product-manager | Repeat transfer at 90d, which requires a cohort followed beyond any test now funded. Test 1's leakage band is an indicator, not a resolution | **new, open - ruled in D-008** |
| R-25 | **Passing Test 1's support threshold confirms the Rs 12 assumption rather than refuting it.** 4.00 min implies Rs 11.36/transfer; the model needs Rs 6, i.e. 2.11 min. A pass risks being misread as viability | Critical | ceo-planning | Already computed and verified. Mitigation is documentary: "not catastrophic is not viable" is written into the Test 1 result template | **new, mitigated not closed** |
| R-26 | **Copyright exposure ROSE when general reading was cut**, concentrating v1 onto prescribed textbooks where photocopies and pirated reprints live | Material | privacy-compliance | Listing-time prevention: ISBN required, photocopy/spiral-binding flags, explicit prohibition in the seller undertaking. Kill condition K7 stops the pilot at 3+ pirated books | **new, evidenced** |
| R-27 | **Test 1 cannot measure search-success rate (R-01)** because the no-browsable-surface constraint means there is no search. Human match rate is an upper bound only | Material | marketplace-ops | Deferred to the first build with a real search surface. Do not report match rate as search success | **new, accepted limitation** |
| R-28 | **Adult verification in Test 1 is a declaration plus a logged in-person check** - weaker than R-18 demands and it does not transfer to the product | Material | cto | Server-side gate at build time; counsel question C3 on what diligence is required. Second under-18 encountered is a pilot kill condition | **new, flagged by marketplace-ops** |
| R-29 | **The forbidden-word test greps English only.** A Tamil string that warrants something passes the control clean, while the vouching liability (R-16) is exactly what the control exists to prevent. Tamil equivalents are genuinely ambiguous, not merely untranslated | Critical | cto + design-director | Extend enforcement across scripts AND native-speaker sign-off of the three blocking classes before any Tamil string ships. Tamil locale gated until both done (D-011) | **new, open** |
| R-30 | **Design performance figures are estimates, not measurements.** Nothing has been built or profiled; the ~30 KB / 3G numbers are modelled | Minor | frontend-developer | Profile the real build on a throttled connection before any figure is quoted as a result | **new, open** |

---

## Decisive unknowns

Three numbers decide this business and **none of them is known**:

1. **Transactions per student per year** — the model uses 1.8 per *active participant*, which is 9x below the founder's implied figure.
2. **What share of campus book transfer is gifting rather than selling** — no source exists anywhere. Gifting suppresses cash GMV without suppressing book value moved.
3. **Support cost per transfer** — Rs 12 assumed, unmeasured, and the single input that could flip the verdict.

All three are cheap to measure and expensive to assume. None requires building the product.
