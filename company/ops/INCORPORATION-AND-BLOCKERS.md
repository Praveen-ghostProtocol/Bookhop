# INCORPORATION-AND-BLOCKERS.md — execution checklist and re-scoped blocker list

**Owner:** privacy-compliance · **Version:** v1.1 · **Date:** 2026-10-21
**`evidence/COMPLIANCE.md` remains the standing legal review.** Both documents
were updated in the same pass for v1.1; where they differ, this one is the gate
and sequencing authority and `COMPLIANCE.md` is the rule authority.
**Handoff:** cto, ceo-planning, marketplace-ops, human founder.

---

## Changelog

### v1.1 — 2026-10-21 · D-009 voided Gate A as designed

| # | Change | Why |
|---|---|---|
| 1 | **§3 rewritten — the three gates are re-cut.** They are now **A = build (open now) · B = first real user · C = discovery opens · D = public**. The old Gate A (14-day paper concierge pilot, premised on a human holding the list) **no longer exists**; the old Gate B's definition — *"any code may ship"* — was wrong under D-009 and has been replaced. **The gate letters are kept deliberately**, because D-009, ADR-001, ADR-002 §4, `gate_authorisations` and `TASKS.md` all reference them and renaming would invalidate four frozen documents. | D-009 made the first student-visible surface software. Gate A's hinge was A0, *"BookHop must operate no browsable listing surface"*, enforced by operator discipline. |
| 2 | **The single most consequential finding: IT Rules 2021 intermediary status attaches at the FIRST REAL USER, not at the first browsable listing.** §4.6 held BookHop is not an intermediary *"conditional on A0"* because *"no computer resource of ours receives, stores or transmits records on users' behalf."* **The moment a real student's listing or message is stored on our server, that condition fails.** Grievance officer, published rules, the 2h/3h/24h/7d clocks and r.3(1)(j) 180-day preservation all move to **Gate B**. **This moves blockers strictly earlier and it is the main increase in urgency.** | Intermediary status under IT Act s2(1)(w) does not require a browsable surface. |
| 3 | **Blockers that became LESS urgent, stated as plainly as the ones that got worse.** **A1/P11 campus permission now blocks nothing until Gate C** — D-008's *"still blocked on exactly one thing: three named campus contacts"* is **no longer true**, and campus contacts are off the critical path. **N3 (fee A/B rules) is CLOSED/void.** **A8 (spreadsheet custody) is void.** C9 and C10 stay dormant. | The command asked for rigour in both directions. The discovery gate means code can exist before the company does. |
| 4 | **P14's gate moves to A** (it was A and B): the schema is created at slices S0–S2, long before Gate B. **The CTO already did this and it is confirmed, not requested.** §4.3.2 of `COMPLIANCE.md` adds seven requirements to the test. | A price column added in slice 2 and removed in slice 7 has existed in a real database. |
| 5 | **New §6 — the founder's one real choice**, framed rather than decided: do real users arrive **before** discovery opens (a separate Gate B: earlier counsel, earlier infrastructure spend, instrumented closed beta) **or with it** (B and C collapse: simpler and cheaper, but no instrumented data before the company exists). **This is a founder decision and D-009's whole mitigation depends on it.** | Nobody has priced it. INFRA.md assumes real data from Gate C; under this resequencing it can arrive at Gate B. |
| 6 | **§0 re-verification table updated:** CERT-In **data-residency question answered** (CTO's reading confirmed, do not move providers); the **DPDP (Removal of Difficulties) Order, 2026** found and assessed as immaterial; the **s393 ₹5 lakh mapping corrected**. | ADR-001 §5 and §7.2 routed the residency question here; INFRA.md §2 held deployment on it. |
| 7 | **§5 C11 re-drafted and re-ranked** — still deferrable to Gate B, now **scheduled and bundled** into the C1–C3 engagement, with a **third tripwire** added (copy that presents the asking price as the transaction price). **C1 is more urgent in wall-clock terms than v1.0 implied.** | `COMPLIANCE.md` §4.3.1 found the authority v1.0 said did not exist. |
| 8 | **§4 retained, not deleted, and re-headed** as the source of three artefacts the app inherits: §4.1 → the forbidden-copy test fixture; §4.2 → the schema deny-list; §4.5 → row 23's retention split. | The paper pilot is cancelled; the thinking in its envelope is not wasted. |

**This is not legal advice.** See §0. **A qualified Indian lawyer must review
BookHop's terms, privacy notice and seller arrangements before public launch**,
and the incorporation filing still cannot be self-filed.

---

## 0. Standing disclaimer, and what changed

**This is not legal advice. I am not a lawyer and cannot give legal sign-off.**
This is a primary-source review that tells you what the rule text says, where
BookHop sits against it, and what to ask a lawyer. **A qualified Indian lawyer
must review BookHop's terms, privacy notice and seller arrangements before
public launch**, and a qualified Indian chartered accountant or company
secretary must handle the incorporation filing itself (§1.6). Nothing below
removes those requirements.

### What changed since COMPLIANCE.md v1.0

Two decisions landed after that review, and I was asked to test whether they
shrink my own blocker list. They do — unevenly. The honest summary:

| Change | What it genuinely removes | What it does not touch |
|---|---|---|
| **Student side free in v1** (D-006, D-007) | **GST, entirely.** No TCS under CGST s52, no s24(x) compulsory registration, no GSTR-8, no 18% GST on commission, no r.5(3)(d) payment disclosures. §4.4 of COMPLIANCE.md is dead for v1. | **s194-O / s393 TDS. Unchanged.** The trigger is facilitation, not fee income. See §2, P14. |
| **Student side free in v1** | **CPA "consumer of BookHop's service" status.** s2(7) requires consideration on both limbs; a student who pays BookHop nothing is not BookHop's consumer. | **E-Commerce Rules duties.** They attach to an "e-commerce entity", a status with no consideration limb. Breach is still actionable (r.8). |
| **Swap and general reading cut** (D-007) | **The reason credits existed.** Credits were invented to solve the swap double-coincidence problem. With swap out of v1, there is nothing for them to solve. Counsel question on PPI goes dormant. | **The PPI analysis itself.** Still correct, still binding the day anyone proposes a balance. |
| **Free + no fee** | **Red Team O-10.** Inspect-before-pay was "the disintermediation event" only because it destroyed fee revenue. With no fee, compliance's mandated inspect-before-pay costs nothing. **O-10 is resolved by the free decision, not deferred by it.** | Nothing. This is a clean win. |

### The one place the founder's hypothesis was wrong

The brief suggested that because the operator earns nothing, s194-O's deeming
Explanation might not reach us. **It does. I re-read the section and the
answer is no.**

- s194-O Explanation (b) defines "e-commerce operator" as **"a person who owns,
  operates or manages digital or electronic facility or platform for electronic
  commerce."** There is no payment limb and no consideration limb in the
  definition. The "responsible for paying" language sits separately in
  **sub-section (6)**, which *deems* the operator to be the person responsible
  for paying — it is a deeming provision that catches us, not a condition that
  releases us.
  (https://indiankanoon.org/doc/72905898/, accessed 2026-10-21.)
- Under the **Income-tax Act 2025**, the same obligation sits at **s393, Table
  Sl. 8(v)**: deductor "any e-commerce operator", rate **0.1% of gross amount**,
  **threshold nil**.
  (https://indiankanoon.org/doc/30529673/, accessed 2026-10-21.)

**What BookHop earns is nowhere in the trigger.** P14 therefore stands at full
force and is arguably the single most important technical constraint in v1.

### Re-verified today, 2026-10-21

| Item | Status now |
|---|---|
| **CERT-In Directions** | **CLOSED — now primary-verified.** No. 20(3)/2022-CERT-In, MeitY, dated 28 April 2022, PDF text extracted from https://www.cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf (accessed 2026-10-21). Direction (ii): report Annexure I incidents **"within 6 hours of noticing such incidents or being brought to notice"**. Direction (iv): **"enable logs of all their ICT systems and maintain them securely for a rolling period of 180 days ... maintained within the Indian jurisdiction"**. Direction (i): NTP sync to NIC or NPL. **"This direction will become effective after 60 days from the date on which it is issued"** → in force 27 June 2022. Discharges one third of P13. |
| **E-Commerce Rules r.4(1)(a)** | **Re-verified verbatim from the Gazette**, text extracted from https://prsindia.org/files/bills_acts/bills_parliament/2021/Consumer%20Protection%20(E-Commerce)%20Rules,%202020.pdf (Gazette No. 358, 23 July 2020; accessed 2026-10-21): an e-commerce entity shall **"be a company incorporated under the Companies Act, 1956 (1 of 1956) or the Companies Act, 2013 (18 of 2013)"** or a qualifying foreign company or FEMA-resident-controlled office. *Gazette defect noted: both clauses of r.4(1) are printed as "(a)"; the second is plainly (b).* |
| **r.3(1)(b) "e-commerce entity"** | **"any person who owns, operates or manages digital or electronic facility or platform for electronic commerce, but does not include a seller offering his goods or services for sale on a marketplace e-commerce entity"** — same source. **No consideration limb. Being free does not take us out.** |
| **r.4(11)(b)** | **"No e-commerce entity shall ... discriminate between consumers of the same class or make any arbitrary classification of consumers affecting their rights under the Act."** Same source. Newly relevant — see §4.3. |
| **DPDP commencement** | **Unchanged. 13 May 2027 stands.** Re-searched 2026-10-21: no MeitY notification advancing the 18-month tranche has been gazetted. The compression proposal circulated in January 2026 remains unnotified (commentary: https://www.amsshardul.com/insight/enforcement-of-the-dpdp-act-and-notification-of-the-dpdp-rules/, https://consentos.in/learn/dpdp-rules-notification-status/, both accessed 2026-10-21). **Re-check monthly.** |
| **Copyright Rules r.75; TN Shops & Establishments** | **Still open.** P13 remains live on these two. |
| **CERT-In data residency — the CTO's question (ADR-001 §5)** | **ANSWERED 2026-10-21. The CTO's reading is CONFIRMED. Uncertainty MODERATE → LOW.** A VM in an Indian region of a **foreign-owned** provider satisfies Direction (iv). Direction (iv) is a **retention-and-producibility** obligation — its own closing words are *"These should be provided to CERT-In along with reporting of any incident or when ordered / directed by CERT-In"* — and it says nothing about the ownership, incorporation or nationality of the infrastructure supplier. CERT-In's own FAQ is **more permissive than we need**: *"Q 35. Is it required to store copy of logs in India only? Ans.: The logs may be stored outside India also as long as the obligation to produce logs to CERT-In is adhered to by the entities in a reasonable time."* (FAQs on Cyber Security Directions of 28.04.2022, CERT-In, May 2022, https://www.cert-in.org.in/PDF/FAQs_on_CyberSecurityDirections_May2022.pdf, accessed 2026-10-21, extracted from the PDF). Nationality appears in the FAQ **only to widen who is bound** (Q 26: *"applicable to any entity whatsoever"*), never to narrow where data may sit. The one India-location answer tied to foreign providers, **Q 36**, is about *"logs and records of financial transactions"* — **of which BookHop has none, because of P14.** **Do not move providers. Do not spend on the hedge. ADR-001 §8's reversal trigger is NOT FIRED.** Full reasoning: `COMPLIANCE.md` §5.2.1. |
| **CERT-In Direction (v)** | **Does not apply to BookHop.** It binds *Data Centres, VPS providers, Cloud Service providers and VPN Service providers* to register subscriber details for 5 years. **We are a subscriber, not one of them.** Recorded as a negative finding so nobody builds a register we do not owe. Primary text verified 2026-10-21 from https://www.cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf. |
| **DPDP (Removal of Difficulties) Order, 2026 — S.O. 5458(E)** | **New instrument, found and assessed: IMMATERIAL.** Dated **5 October 2026**, in force on Gazette publication (sources differ between 6 and 7 Oct). Two purely textual corrections to the DPDP Act: *"child or a person with disability"* → *"child or **of** a person with disability"* in **s9(1)**, and *"audit"* → *"data audit"* in **s10(2)(c)(ii)**. **It does not move any commencement date and it changes nothing for our age gate (P5, C3) or our SDF position (`COMPLIANCE.md` §1.9).** *Commentary-sourced — https://ssrana.in/articles/dpdp-removal-of-difficulties-order-2026-what-has-been-changed-for-childrens-data-and-sdf-audits/ and https://www.scconline.com/blog/post/2026/10/15/dpdp-removal-of-difficulties-order-2026/, both accessed 2026-10-21; Gazette text not reached.* Recorded so nobody finds it later and assumes it mattered. |
| **s393 mapping — CORRECTION to §0 below** | The charging entry **s393(1) Table Sl. No. 8(v)** is confirmed: deductor *"Any e-commerce operator"*, rate *"0.1% of gross amount"*, threshold **Nil**. **But the ₹5 lakh individual/HUF relief is NOT inside 8(v)** — it is a separate no-deduction entry at **s393(4) Table, Sl. No. 11**, conditional on PAN or Aadhaar being furnished. The substance is unchanged; a drafter citing 8(v) for the exemption would cite the wrong provision. (https://indiankanoon.org/doc/30529673/ and https://eztax.in/income-tax-act-2025/section-393, accessed 2026-10-21.) |
| **s194-O / s393 construction** | **Materially strengthened, and P14 is unchanged.** `COMPLIANCE.md` §4.3.1 found the authority v1.0 said did not exist — **CBDT Circular 20/2021** (e-auction: price discovery only, *"not necessarily the price at which the transaction takes place"*, transaction and payment both outside the portal, operator *"does not have any information about the quantum and the schedule of payment"* → **s194-O does not apply**) and **Circular 17/2020 para 4.3** (*"no involvement in transactions"* → *"would not be liable to deduct"*). Uncertainty **HIGH → MODERATE**. **§4.6's GREY grading below is superseded by `COMPLIANCE.md` §4.3.1.** |

---

## 1. Incorporation checklist

### 1.1 Entity type — private limited is right. Here is the reasoning and the one fallback.

**The requirement.** E-Commerce Rules r.4(1)(a), quoted verbatim above,
requires the e-commerce entity to **be a company incorporated under the
Companies Act 1956 or 2013**. That is the whole requirement. Four candidates:

| Form | Satisfies r.4(1)(a)? | Verdict |
|---|---|---|
| **Sole proprietorship** | **No.** Not a company. | Rejected. |
| **LLP** | **No.** An LLP is incorporated under the **Limited Liability Partnership Act 2008**, not the Companies Act. It fails r.4(1)(a) on the face of the text. | Rejected. This is the most common mistake and it is unambiguous. |
| **Section 8 company** | Yes — it is a company under the 2013 Act. | Rejected. Non-profit licence, no distribution of profit, materially longer process. Wrong shape for a company that intends to be funded. |
| **One Person Company (OPC)** | **Yes.** An OPC is a company incorporated under the 2013 Act and satisfies r.4(1)(a). | **Fallback only — see below.** |
| **Private limited** | **Yes.** | **RECOMMENDED.** |

**Why private limited and not OPC.** OPC would satisfy the rule, and it is
genuinely faster if the founder is alone. But s2(62) of the Companies Act 2013
defines an OPC as a company with **only one member**. Admitting any second
shareholder — a co-founder, an angel, an ESOP holder — breaks the definition
and forces conversion. The mandatory conversion thresholds (₹50 lakh paid-up /
₹2 crore turnover) were removed by the **Companies (Incorporation) Second
Amendment Rules, 2021**, effective 1 April 2021, and voluntary conversion is
now available at any time under Rule 6(1) — so the OPC route is **reversible**
(https://vinodkothari.com/?p=32872, accessed 2026-10-21; commentary-sourced,
confirm with the CS). **Recommendation: private limited. Use OPC only if the
founder cannot produce a second shareholder this week and the pilot timeline
matters more than one later conversion filing.** Say so to the CS up front if
you take that path.

**Uncertainty: LOW.** r.4(1)(a) is unambiguous and I have read it in the
Gazette. The only judgement here is private limited vs OPC, and that is a
commercial judgement, not a legal one.

### 1.2 The thing most likely to stall you, stated first

**A private limited company needs two members and two directors.** s3(1)(b)
(minimum two persons for a private company) and s149(1)(a) (minimum two
directors). At least one director must have **stayed in India for 182 days or
more in the financial year** (s149(3)).

**If the founder is solo, the filing stops here until a second person agrees to
hold one share and be a director.** This is usually a spouse, sibling or parent
holding a single ₹10 share. It is a real legal position with real duties — that
person signs filings, is an "officer in default" for penalties, and must obtain
a DSC. **Decide who this is before you open the portal.** Everything else in
this checklist is paperwork; this is a conversation.

*Sources for the Companies Act thresholds: these are long-settled provisions
unchanged since 2013/2018 and I have not re-verified them from the Gazette.
indiacode.nic.in and mca.gov.in both returned HTTP 403 to automated access on
2026-10-21. Commentary corroborating s149(3):
https://thelegalschool.in/blog/section-149-3-companies-act-2013 (accessed
2026-10-21). **The CS confirms these as part of the filing.***

### 1.3 Documents the founder must have in hand

For **each** director and subscriber (so, both people):

1. **PAN card** — mandatory for Indian nationals, no substitute.
2. **Aadhaar** — for identity and mobile/email OTP verification.
3. **One identity proof**: passport, voter ID or driving licence.
4. **One address proof not older than two months**: bank statement, electricity
   bill, telephone bill or mobile bill **in that person's own name**.
5. **Passport-size photograph**, digital.
6. **Personal mobile number and email**, each unique per person on the portal.
7. **Digital Signature Certificate (DSC)** — Class 3, individual, with video
   KYC. Needed before anything can be filed.

For the **registered office** (can be a residence):

8. **Utility bill for the premises not older than two months** (electricity or
   gas or water or telephone).
9. **No Objection Certificate from the owner**, signed, if the premises are not
   the subscriber's own.
10. **Rent agreement**, if rented.

For the **company**:

11. **Two proposed names**, in order of preference. Check both against the MCA
    name search *and* the trade mark register before filing — a name that
    collides with an existing mark is the commonest rejection.
12. **Object clause** — what the company will do, in the MoA. Have the CS draft
    this. Write it broad enough to cover a marketplace platform, campus
    services, and an institutional B2B revenue line, because narrowing it later
    costs an EGM and a filing.
13. **Authorised and paid-up capital.** **Recommendation: authorised ₹1,00,000,
    paid-up ₹1,00,000 or less.** Keeping authorised capital at or under ₹15 lakh
    keeps the MCA registration fee at nil (§1.4), and keeping it low keeps Tamil
    Nadu stamp duty at the bottom of the slab.

### 1.4 Fees and realistic elapsed time

**Sourcing caveat, stated plainly: mca.gov.in returned HTTP 403 to automated
access on 2026-10-21, as did indiacode.nic.in. Every figure in this table is
commentary-sourced. Treat the structure as reliable and the numbers as
indicative. The CA or CS confirms them on the MCA fee calculator at filing
time.**

| Item | Approx. cost | Notes |
|---|---|---|
| DSC, Class 3, two individuals | ₹2,000 – ₹4,000 | ₹1,000–₹2,000 each. 1–2 days with video KYC. |
| SPICe+ Part A name reservation | ₹1,000 per attempt | Two names per attempt. Approval valid **20 days**. A rejection costs another ₹1,000. |
| MCA registration fee (SPICe+ Part B) | **₹0** | Nil for authorised capital **up to ₹15 lakh**, per notification **G.S.R. 329(E)**. *Commentary-sourced:* https://www.corplawupdates.in/tools/fee-calculator/companies/spice-plus (accessed 2026-10-21). |
| Tamil Nadu stamp duty on MoA + AoA | ₹1,000 – ₹2,500 at minimum capital | **Sources conflict sharply** — one calculator gives ₹1,000 (MoA) + ₹300 (AoA); another describes a rate scaling to 1% of authorised capital capped at ₹25,000. Collected inside the SPICe+ filing. **Keep authorised capital low and this stays small.** Confirm on the fee calculator. |
| PAN + TAN | ~₹150 total | Issued automatically with the Certificate of Incorporation. |
| INC-20A (commencement declaration) | ₹200 | Post-incorporation. See §1.5. |
| CA / CS professional fee | ₹3,000 – ₹15,000 | Not optional — see §1.6. |
| **Realistic all-in** | **₹8,000 – ₹20,000** | Against the ₹16,500 approved under D-007. **This is a conflict: see the warning below.** |

> **Budget warning for the founder and ceo-planning.** D-007 approved ₹16,500
> covering 18 interviews, the concierge pilot and contingency. **Incorporation
> at ₹8,000–₹20,000 was not inside that envelope.** It is a separate founder
> spending decision under README §2. Do not let an agent book it against the
> Test 1 budget.

**Elapsed time.**

| Stage | Working days |
|---|---|
| DSC issuance (both people) | 1 – 2 |
| SPICe+ Part A name approval | 1 – 3 |
| SPICe+ Part B + eMoA + eAoA + AGILE-PRO-S preparation and signing | 1 – 3 |
| ROC processing to Certificate of Incorporation | 3 – 10 |
| **One resubmission, if the ROC raises a query** | **+3 – 7** |
| Company bank account opened after CoI | 3 – 10 |

**Optimistic: 10 working days to the certificate. Plan for four weeks to an
operational company with a bank account. Do not plan for under three.**
Resubmissions are common and you generally get one chance to resubmit before
the filing is rejected and fees are forfeited.
*Sources, all commercial and conflicting on the exact ranges:*
https://www.incorpx.io/blog/spice-plus-form-company-incorporation-guide-2026,
https://buildwright.co.in/blog/spice-plus-company-registration-complete-process,
https://batchwise.ai/guides/private-limited-company-incorporation-india/
*(all accessed 2026-10-21).*

### 1.5 The sequence — what runs in parallel, what is blocked

**Phase 0 — before anything is filed. All parallel, all founder-doable today.**
- Agree who the second shareholder/director is. *(Gate on everything.)*
- Collect the eleven documents in §1.3 for both people.
- Run the name search and the trade mark search on both proposed names.
- Engage a CS or CA (§1.6) and get a quote.
- Procure both DSCs.

**Phase 1 — filing. Sequential.**
1. SPICe+ **Part A** → name reserved, valid 20 days.
2. SPICe+ **Part B** with linked forms, filed as one transaction:
   **eMoA (INC-33)**, **eAoA (INC-34)**, **INC-9** declaration, and
   **AGILE-PRO-S (INC-35)** — which carries EPFO and ESIC registration,
   professional tax, a bank account application, and optionally GSTIN.
   **Do not tick GSTIN.** BookHop has no GST obligation in v1 (§2, P-GST) and
   a voluntary registration creates monthly return obligations with no benefit.
3. Pay fee + stamp duty.
4. **Certificate of Incorporation** issues, carrying **CIN, PAN and TAN**. DIN
   is allotted inside the same filing for up to three first directors.

**Phase 2 — post-incorporation. Sequential, and the one people forget.**
5. Open the company bank account.
6. Pay the subscription money **into that account** from each subscriber.
7. **File INC-20A** — the s10A declaration of commencement of business, due
   **within 180 days** of incorporation. Needs professional certification.
8. Appoint the **first auditor within 30 days** of incorporation (s139(6)).

> **This is the dependency most likely to bite BookHop.** **s10A bars a company
> from commencing any business or exercising borrowing powers until the INC-20A
> declaration is filed.** If the campus pilot runs in the company's name before
> INC-20A, the company has commenced business without the declaration. Penalties
> reported at ₹50,000 on the company and ₹1,000 per day on officers in default,
> and the ROC may initiate strike-off under s248. *Commentary-sourced:*
> https://www.incorpx.io/guide/how-to-file-inc-20a-commencement-of-business
> *(accessed 2026-10-21); confirm with the CS.* **Sequence it: CoI → bank →
> subscription money → INC-20A → then the platform pilot.**

**Blocked until the Certificate of Incorporation exists:**
- Opening a bank account in the company's name.
- Signing any campus MoU as "BookHop Private Limited".
- Displaying a legal name, CIN or registered address under E-Com r.4(2).
- Any GST registration, if one is ever needed.
- Appointing a grievance officer *of the company*.
- Issuing shares, ESOPs or a term sheet.

**Explicitly NOT blocked on incorporation:**
- **The concierge pilot (Test 1).** See §3, Gate A. This is the headline:
  **you do not need the company to run the paper pilot**, provided it is run
  within the envelope in §4.
- The 18 interviews and the ₹0 librarian probe.
- Drafting, counsel engagement, campus conversations.

### 1.6 What needs a CA or CS rather than the founder

**Not optional:**
- **SPICe+ Part B must be digitally signed and certified by a practising
  professional** — a Chartered Accountant, Company Secretary, Cost Accountant
  or Advocate. The founder cannot self-file a company incorporation in India.
- **INC-20A** likewise requires professional certification.
- **MoA object clause drafting.** A founder-drafted object clause is the
  commonest cause of a later amendment filing.
- **Capital structure and stamp duty slab** — getting the authorised capital
  wrong costs money at filing and again at every increase.
- **First auditor appointment, statutory registers, board minutes, AOC-4 and
  MGT-7A annual filings, DIR-3 KYC.** These start the day the company exists
  and recur annually.

> **What the founder is actually approving.** Incorporation is not a one-off
> ₹15,000. It starts a permanent annual compliance obligation — audited
> accounts, two annual MCA filings, a company ITR, director KYC — that runs
> whether or not BookHop trades. Budget roughly ₹15,000–₹30,000 a year in
> professional fees from here on. That is the real cost of r.4(1)(a), and it is
> worth knowing before the certificate rather than after.

---

## 2. P1–P14 re-scoped for the free-to-student v1

**Key:** **STILL REQUIRED** · **REDUCED** (narrower, not gone) ·
**NO LONGER APPLICABLE** · **NEWLY APPLICABLE**.

I have tried to be as willing to keep a blocker as to drop one. Three dropped,
four reduced, seven unchanged, three new. The gate column is the important
addition: the old list collapsed "before the pilot" and "before code", which
is the specific defect this document fixes.

| # | Blocker | Status under free-to-student v1 | Gate | Reasoning |
|---|---|---|---|---|
| **P1** | Incorporate as a company | **STILL REQUIRED — unchanged** | **B** | r.3(1)(b) defines "e-commerce entity" with **no consideration limb**: "any person who owns, operates or manages digital or electronic facility or platform for electronic commerce". Charging nothing does not take us out. The *gate moves* — it blocks code, not the paper pilot. |
| **P2** | Grievance Officer + India-resident nodal contact | **STILL REQUIRED — unchanged** | **B** = first real user *(v1.1)* | IT Rules r.3(2)(a) attaches to an "intermediary"; E-Com r.4(1)(b) and r.4(4) to the e-commerce entity. **v1.1: intermediary status arrives at the first real user, not at the first browsable listing — see §3.3 B1′. The officer may be the founder in their own name pre-incorporation**; re-published as a company officer at Gate C. |
| **P3** | Takedown + grievance SOP, 3h / 2h / 24h / 7d, on-call rota | **STILL REQUIRED — and MORE URGENT under D-009** | **B** = first real user (capability), **C** (rostered and tested) | In force since 20 Feb 2026. Nothing about fees touches it. Failing it forfeits s79 safe harbour **and** E-Com r.5(1) at once. **v1.1: the clocks must be live from the first real user (§3.3 B1′), because s79 is what protects us from a user's pirated listing and it is conditional on observing them.** |
| **P4** | Counsel-drafted privacy notice, terms, seller undertaking | **REDUCED** | **B** | The r.5(2) accuracy undertaking is untouched. **Removed from scope: all payment, fee, chargeback and payment-service-provider disclosure under r.5(3)(d), and the refund-processing provisions.** The returns policy simplifies to inspect-before-pay plus "BookHop holds no money and cannot refund". Roughly a third less to draft. |
| **P5** | Age gate: DOB field, server-side 18+ block, logged review, no ID | **STILL REQUIRED — unchanged** | **A** (manual), **B** (built) | Entirely unaffected by money. A free platform attracts more 17-year-olds, not fewer. |
| **P6** | Per-purpose consent capture with audit trail | **REDUCED** | **B** | Purpose keys drop `payments` and `fee_billing`. Remaining set: `account`, `listing_publication`, `location_proximity`, `chat`, `safety_moderation`, `notifications`. The mechanism is unchanged; the surface is smaller. |
| **P7** | Deletion = tombstone + purge, 1-year retention | **STILL REQUIRED — unchanged** | **B** | DPDP r.8(3) attaches to "personal data, associated traffic data and other logs of the processing" — not to payments. The listing, chat and handover records are the processing. The floor applies in full. |
| **P8** | Breach runbook on the 6-hour CERT-In clock; 180-day logs in India, NTP-synced | **STILL REQUIRED — and now primary-verified** | **A** (thin), **B** (full), **C** (rehearsed) | Verified today from No. 20(3)/2022-CERT-In. Applies to any "body corporate", which under the IT Act s43A Explanation includes a sole proprietorship — **so a thin version of this applies to the concierge pilot too** (§4.6). |
| **P9** | Copyright takedown SOP, repeat-infringer record, listing-time deterrents | **STILL REQUIRED — and the risk went UP, not down** | **B** | Cutting general reading does not dilute copyright risk, it **concentrates** it. v1 is edition-locked prescribed textbooks only — precisely the category where photocopied course packs, scanned PDFs and unauthorised reprints live. We removed the low-risk inventory and kept the high-risk inventory. Say this to anyone who reads the scope cut as a risk reduction. |
| **P10** | Handover safety design; no safety warranties in any copy | **STILL REQUIRED — and the conflict inside it is RESOLVED** | **A** (manual), **B** (built) | Tortious negligence exposure is unchanged by fees. **But Red Team O-10 is resolved:** inspect-before-pay was "the disintermediation event" only because in-person settlement destroyed fee revenue. There is no fee revenue. Compliance's mandated control now costs the business nothing. **Mark O-10 closed by D-007, not deferred.** CPA deficiency-in-service exposure also drops, because s2(7) requires consideration — but that was always the smaller of the two exposures. |
| **P11** | Written campus permission per institution | **STILL REQUIRED — but v1.1: NO LONGER THE EARLIEST BLOCKER.** D-009 removed the 14-day study it gated. **It now blocks nothing until Gate C**, and D-008's "still blocked on exactly one thing: three named campus contacts" is no longer true (§3.5) | **C** (full MoU) *(v1.1: the Gate A letter limb is void — there is no 14-day study)* | **Split it.** Gate A needs a one-page written permission for a 14-day study — the founder can obtain that without counsel. Gate C needs the full MoU covering enrolment-data sharing, name and logo use, liability allocation and termination — that needs counsel (§5, C5). Founder-reserved either way. |
| **P12** | Credit designs (a) and (b) blocked; only (c) may ship | **STILL REQUIRED — but now MOOT for v1** | **B** | Unchanged as a rule. But credits existed to solve the swap double-coincidence problem, and **D-007 cut swap from v1**, so nothing in v1 wants a credit. The rule binds; the pressure on it is zero. **Consequence: counsel question Q7 goes dormant and should not be paid for now** (§5, Tier 4). |
| **P13** | Verify CERT-In, Copyright r.75, TN Shops & Establishments | **REDUCED — one third discharged today** | **C** | **CERT-In: CLOSED**, primary text extracted and quoted in §0. **v1.1: the CERT-In *data-residency* question is also now closed — see §0 and `COMPLIANCE.md` §5.2.1.** **Copyright r.75: still open.** **TN Shops & Establishments: still open**, and note it attaches to BookHop as an *employer* at its registered office, not to the platform — with no employees it may not bite at all, which is itself worth confirming. |
| **P14** | Do not collect PAN or Aadhaar; do not record settled sale consideration | **STILL REQUIRED — AND MORE IMPORTANT THAN BEFORE** | **A** *(v1.1: was A and B; the schema is created at S0–S2, so it is a Gate A item in full — see §3.2 A1′ and `COMPLIANCE.md` §4.3.2)* | **This is the one the free-to-student change does not help.** s194-O's definition of "e-commerce operator" has no payment or consideration limb; sub-section (6) deems us the payer; the Explanation deems direct cash to be paid by us; s393 Table Sl. 8(v) sets the threshold at **nil**. Earning nothing is irrelevant. The only mitigation remains the one in P14: **no PAN, no Aadhaar, no settled price recorded anywhere.** Enforce it in the schema at Gate B and in the spreadsheet at Gate A. |

### Blockers that fall away entirely

| Dropped | Was | Why it is gone |
|---|---|---|
| **GST registration and TCS readiness** | COMPLIANCE.md §4.2, §4.4, L2 | **NO LONGER APPLICABLE for v1.** CGST s52 requires consideration "to be collected by the operator" — none is. s24(x) is conditioned on being required to collect TCS — we are not. BookHop makes **no outward supply at all**, so aggregate turnover is nil and s22(1)'s ₹20 lakh threshold is not approached. No registration, no GSTR-8, no 18% commission GST. **Stated without hedging: there is no GST obligation in free-to-student v1.** It returns the day institutional revenue or any fee arrives. |
| **r.5(3)(d) payment disclosures** | COMPLIANCE.md §2.3 | **NO LONGER APPLICABLE.** There are no payment methods, fees, chargebacks or payment service providers to disclose. |
| **L12 payment provider selection** | COMPLIANCE.md §6.2 | **NO LONGER APPLICABLE for v1.** D-004 stands as a standing rule; there is simply nothing to select. |

### Newly applicable

| # | New blocker | Gate | Why it is new |
|---|---|---|---|
| **N1** | **Post-incorporation statutory maintenance**: first auditor within 30 days (s139(6)); **INC-20A within 180 days before commencing business** (s10A); AOC-4, MGT-7A, DIR-3 KYC annually | **B** | Created *by* executing P1. The s10A bar on commencing business before the declaration is filed is a sequencing trap, not a formality (§1.5). Owner: founder + CS. |
| **N2** | **Institutional-payer compliance surface** — before any money from a college is accepted | **D (pre-launch)**, but **assess before the ₹0 librarian probe produces a signed anything** | D-007 item 4 authorised testing the institutional-payer hypothesis. If it succeeds it **reverses most of what free-to-student just removed**: BookHop acquires revenue (GST on its own supply of services once over ₹20 lakh), a B2B contract, probably a public-institution procurement process — **and, non-obviously, it puts students back inside CPA s2(7)**, whose services limb extends to "any beneficiary of such service" where the service is availed with the approval of the person who paid. **A college paying for the students makes the students BookHop's consumers again.** The probe is a conversation and needs no clearance; a signed institutional contract needs counsel. |
| **N3** | ~~**Fee A/B rules for Test 1**~~ | ~~A~~ | **CLOSED / VOID at v1.1.** D-009 cancelled the paper pilot, so there is no fee arm, no cash fee and no founder personal income to declare. **The r.4(11)(b) warning in §4.3(iv) survives and is now architectural** — ADR-003 §3 records that the architecture offers no mechanism for a price A/B, and one must not be built after Gate C without counsel. |

---

## 3. Dependency-ordered sequence — re-cut for D-009 (v1.1)

> **§3 was rewritten on 2026-10-21. The version below supersedes it. The
> superseded text is kept at §3.9 because A0's reasoning is still load-bearing
> and because deleting the analysis would hide why the gates moved.**

### 3.0 What D-009 did to the gates

Gate A existed because there was a student-visible surface — a human operator
with a spreadsheet — that was **not a platform**. Its hinge was **A0**:
*"BookHop must operate no browsable listing surface."* D-009 made the first
student-visible surface software, so **Gate A as designed is void.**

**But A0 did not die; it was reimplemented, and better.** ADR-002 §4 is A0 in
code: `campuses.discovery_enabled_at` defaulting to NULL, a server-side
`assert_discovery_open` guard returning 403 `GATE_CLOSED`, a seed-only discovery
predicate, an append-only `gate_authorisations` row with a named human on it, and
`tests/unit/test_gate.py`. **That is strictly stronger than the original.** A0
was a MODERATE-uncertainty reading of *"manages a facility"* resting on an
operator not sharing a spreadsheet; the replacement rests on a `WHERE` clause and
an HTTP 403. **Credit where it is due: the discovery gate is the design that
makes D-009 workable, and it is the reason some blockers got *less* urgent.**

**The error in the old sequence, now fixed.** Old Gate B was defined as *"any
code may ship, even to a closed test group."* **Shipping code to a box is not a
legal event.** Two things are:

1. **A real person's personal data enters the system.** That triggers
   intermediary status, consent, deletion, logs, breach duties — none of which
   depend on anyone being able to browse.
2. **A real student can see another real student's listing.** *That* is when
   r.4(1)(a) attaches and the company must exist.

**These are different events, weeks apart, with different blockers. Collapsing
them was the same defect v1.0 fixed between A and B, one level down.** Hence
four gates.

### 3.1 The four gates in one table

| Gate | The event that opens it | Incorporation? | Counsel? | Legal spend |
|---|---|---|---|---|
| **A — build** | Code is written and run against **seed data only** | **No** | **No** | **Zero** |
| **B — first real user** | **One real student holds an account**, with discovery still closed | **No** *(conditional — §3.3)* | **C1, C3** | First legal spend |
| **C — discovery opens** | A real student can see **another real student's** listing | **Yes — r.4(1)(a)** | **C2, C4, C5** | — |
| **D — public launch** | Public signup | Yes | L1 | — |

**This maps onto the frozen architecture without a single change.**
`gate_authorisations.gate` is already `CHECK IN ('B','C','D')`, and ADR-002
§4.1(b)'s `open_discovery` command already demands the CoI, INC-20A, the
grievance officer, published notices, `counsel_engagement_ref`,
`takedown_sop_ref`, `oncall_rota_ref`, `breach_rehearsal_at` and
`campus_mou_ref` before discovery opens. **Gate C below is that command's
checklist. The CTO has to change nothing to adopt this.**

### 3.2 Gate A — code may be written and run against seed data · **OPEN NOW**

**This is no longer a student-facing gate. It is a developer gate, and D-009
opened it.** Preconditions are few, and three of them moved *earlier*:

| | Must be true | Owner | Note |
|---|---|---|---|
| **A0′** | **The discovery gate exists before the first discovery query does** — `discovery_enabled_at` NULL by default, server-side guard, `is_seed` predicate, `test_gate.py` green | cto | **Replaces A0.** Must be in the first discovery query ever written. Retrofitted, it will be retrofitted wrong |
| **A1′** | **P14 enforced in the schema** — the price trigger plus `test_forbidden_schema.py` with the additions in `COMPLIANCE.md` §4.3.2 | cto | **Was B13. Moved to A**, because the schema is created at S0–S2. **Already done by the CTO; confirmed, not requested** |
| **A2′** | **The forbidden-copy test exists as a fixture, not a review** — §4.1's may/may-not-say list, plus `COMPLIANCE.md` §4.3.2 item 9 | cto + design-director | **Was A7 (a design review at Gate B).** The test is built in S2, so the list must be a fixture by S2 |
| **A3′** | **No real personal data on any machine, including the founder's laptop.** Seed and fixtures only | cto + QA | New. The honest statement of what "Tier 0" means legally |
| **A4′** | **`seller_is_seed = buyer_is_seed` and all metric views filter `is_seed = false`** | cto | ADR-002 §4.1(c). Already specified |

**Not required at Gate A:** incorporation, grievance officer, IT Rules clocks,
takedown SOP, consent infrastructure, deletion flow, counsel-drafted terms, any
DPDP artefact, GST, insurance, campus permission, infrastructure spend, **or a
single campus contact.**

**Legal spend at Gate A: zero.** Unchanged from v1.0, and it is still the most
useful sentence in this document.

**Fallen away entirely at Gate A:** A1 (campus permission letter) → Gate C.
A3 (participant notice) → B8. A4 (18+ at intake) → B7. A6/N3 (fee A/B) →
**closed, void.** A8 (spreadsheet custody) → **void, no spreadsheet exists.**
A9 (CERT-In PoC) → B10. A10 (handover points) → B12.

### 3.3 Gate B — the first real student may hold an account · **the new gate, and the one nobody had**

**The event: one real student signs up and creates a listing that only they and
staff can see. Discovery is still closed.**

**Does this require incorporation? Arguably not — and I am going to be careful
rather than convenient about it.** A0's reasoning transfers by parity: a web app
where a student's listing is reachable by nobody else is the mechanised form of
*"a private intake form feeding a private spreadsheet that only the operator
reads"*, and `is_seed` scoping means no buyer encounters any real seller's goods.
**But I will not extend A0 to carry this indefinitely**, for three reasons v1.0
itself supplies: (i) A0 was graded **MODERATE uncertainty**; (ii) it was scoped
to *"30 handovers over 14 days"* and *"not a position I would hold at 300"*; and
(iii) a permanent web application is manifestly a *"digital or electronic
facility"* in a way a spreadsheet arguably was not.

> **So: incorporation is not a hard Gate B blocker, but Gate B is a holding
> position and not a destination. If real accounts exist for more than a few
> weeks without the company, the A0 reading is being asked to carry weight it
> was never graded for. Start the filing at Gate A — it has a four-week lead
> time (§1.4) and nothing about it is urgent until it is.**

**What Gate B does require unconditionally — and this is the increase in
urgency D-009 caused:**

| | Must be true | Owner | Why it is now Gate B |
|---|---|---|---|
| **B1′** | **IT Rules 2021 intermediary artefacts live**: published rules and privacy policy and user agreement (r.3(1)(a)); a **named, published Grievance Officer** with a working channel (r.3(2)(a)); **24h acknowledge / 7d dispose** capability; the **2h** (r.3(2)(b)) and **3h** (r.3(1)(d)) clocks; **180-day preservation of removed content** (r.3(1)(j)); the **quarterly user reminder** (r.3(1)(c)) as a job | founder + ops + cto | **THE KEY FINDING. §4.6 said BookHop is not an intermediary *"conditional on A0"* because *"no computer resource of ours receives, stores or transmits records on users' behalf."* One real listing and one real message break that condition.** Intermediary status under IT Act s2(1)(w) does **not** require a browsable surface. **s79 safe harbour — the thing that protects us from a user's pirated listing — is conditional on observing these.** |
| **B2′** | **The Grievance Officer may be the founder in their own name, pre-incorporation** | founder | Intermediary status has **no company requirement**. This is why B1′ does not drag incorporation earlier. Published as an individual; re-published as an officer of the company at Gate C |
| **B3′** | Per-purpose consent capture, append-only, no pre-ticked boxes (P6) | cto | Was B8. Gate B is now much earlier in wall-clock time, so this is urgent in a way it was not |
| **B4′** | Age gate built: DOB field, server-side 18+ rejection, DOB purged post-verification, no ID upload (P5) | cto | Was B7. Needs **counsel C3** |
| **B5′** | Deletion = tombstone + purge, **with the expiry job built in the same slice** (P7) | cto | Was B9 |
| **B6′** | **Breach runbook to 6 hours; CERT-In PoC named; logs in India with a 1-year retention; NTP to NIC/NPL** (P8) | cto + founder | Was B10. **Residency is settled — see §0. Any Indian region, any provider.** |
| **B7′** | **Signed DPA with both processors** — hosting and transactional email (r.6(1)(f), design-ahead) | founder + cto | Was B15. INFRA.md §9: **two blocking signatures, and that is the whole third-party surface** |
| **B8′** | **Counsel C1 delivered** — privacy notice, user terms, seller terms with the r.5(2) undertaking, liability clause | counsel | **More urgent in wall-clock terms than v1.0 implied.** "Before the first line of code" meant *after a 14-day paper pilot*; it now means *before the first real signup* |
| **B9′** | **A `gate_authorisations` row with `gate='B'`, and real account creation refused without it** | founder (signs) + cto | **New, and it is one function.** Reuse `assert_discovery_open`'s exact pattern for `users.is_seed = false` creation. Same guard, same audit row, same named human. **Do not invent a second mechanism** |
| **B10′** | Rows 21–24 of `COMPLIANCE.md` §7 implemented as written, including the row 22 basis change and the row 21 reduction | cto | New. They ship in S3/S5/S6 |

**Not required at Gate B:** incorporation *(see the caution above)*, INC-20A,
first auditor, the full campus MoU, counsel C2/C4/C5, insurance, the on-call
rota, the rehearsed breach drill.

### 3.4 Gate C — discovery opens · the e-commerce-entity gate

**The event: a real student can see another real student's listing.** This is
where r.4(1)(a) bites and therefore where the company must exist. **This is
exactly the checklist ADR-002 §4.1(b)'s `open_discovery` command already
enforces**, which is the right place for it.

Everything at Gate B, plus:

| | Must be true | Owner |
|---|---|---|
| C1 | **Certificate of Incorporation issued** (P1) | founder + CS |
| C2 | **Subscription money paid and INC-20A filed** (N1) — **s10A bars commencing business before this, and operating a platform is commencing business** | founder + CS |
| C3 | **First auditor appointed** within 30 days of C1 (N1) | founder + CA |
| C4 | **Grievance Officer and India-resident nodal contact re-published as officers of the company**; legal name, CIN and registered address displayed (E-Com r.4(2), r.4(4); P2) | founder + ops |
| C5 | **Counsel C2 delivered — the C2C scope question** (r.5(3)(a) seller address; r.2(1) proviso; r.6(3)) | counsel |
| C6 | **Takedown + grievance SOP with SLA timers in the system** (P3) | ops + cto |
| C7 | **Copyright takedown SOP + r.5(5) repeat-infringer record + ISBN requirement + photocopy/spiral-binding flag ON BY DEFAULT** (P9) | ops + cto |
| C8 | **Full campus MoU signed** (P11) — needs counsel C5 | founder + counsel |
| C9 | **P13 closed**: Copyright Rules r.75 text and scope; TN Shops & Establishments applicability | privacy-compliance |
| C10 | **Breach runbook rehearsed once end to end, logged** | cto + ops |
| C11 | **On-call rota rostered with named people** covering the 2h and 3h clocks | ops |
| C12 | **Grievance ticketing tested end to end** — a real complaint acknowledged inside 24h with a ticket number | ops |
| C13 | **Age-review queue staffed**, written procedure for a discovered minor: suspend, erase, log; **POCSO duty understood** | ops |
| C14 | **Every rule re-verified**; DPDP commencement and the RBI 2026 PPI Master Direction re-checked | privacy-compliance |
| C15 | **Insurance decision taken**, or a recorded decision not to | founder |
| C16 | **No credit of any design in the build** (P12); **no struck-through prices, no promoted listings, no generative AI in listing creation** | cto + product |
| C17 | **Handover safety design in the product; full copy review; no safety warranty anywhere** (P10) | product + design-director |

**Gate D (public launch)** remains L1–L14 in `COMPLIANCE.md` §6.2, **less L2 and
L12 while v1 is free**, plus **N2** if the institutional payer materialises.

### 3.5 What moved, in one table — both directions

| Item | Was | Now | Direction |
|---|---|---|---|
| **IT Rules clocks, grievance officer, published rules** (P2, P3) | Gate B *(built)* / C *(tested)*, and explicitly **not applicable at Gate A** | **Gate B = first real user** | **MORE urgent** |
| **P14 in the schema** (B13) | Gate B | **Gate A** | **MORE urgent** — already done |
| **Discovery gate** (A0) | Operator discipline at Gate A | **Gate A, in code, in the first query** | **MORE urgent** |
| **Counsel C1** | "before the first line of code" | **Before the first real signup** | **MORE urgent in wall-clock** |
| **Consent + deletion + purge job** (P6, P7) | Gate B | Gate B — **but Gate B arrives much sooner** | **MORE urgent** |
| **DPAs with processors** (B15) | Gate B | Gate B = first real user | **MORE urgent** |
| **Infrastructure spend** | INFRA.md assumes real data from Gate C | **Can arrive at Gate B** | **MORE urgent — see §6** |
| **Campus permission** (A1, P11) | **The single remaining blocker** (D-008) | **Nothing until Gate C** | **LESS urgent** |
| **Fee A/B rules** (N3) | Gate A, needed before ops built the instrument | **CLOSED — void.** No fee arm, no cash fee, no founder personal income. ADR-003 §3 already forbids a platform price A/B under r.4(11)(b) | **CLOSED** |
| **Spreadsheet custody** (A8) | Gate A | **Void.** No spreadsheet | **CLOSED** |
| **Participant consent paragraph** (A3, §4.4) | Gate A | Absorbed into B3′ consent capture | Moved |
| **CERT-In thin version for a paper pilot** (§4.6) | Gate A | **Void as described; replaced by B6′ in full** | Moved |
| **Counsel C9 (PPI), C10 (GST)** | Dormant | **Dormant. D-009 changes nothing.** Paying for them now remains the cheapest sequencing mistake available | Unchanged |
| **Counsel C11 (s194-O)** | Deferrable to Gate B if P14 is in the schema | **Scheduled at Gate B, bundled into C1–C3.** P14 is in the schema, and the position got stronger | Unchanged, sharpened |
| **P13 TN Shops & Establishments** | Gate C | Gate C. With no employees it may not bite at all | Unchanged |

**The one in that table that deserves saying out loud: D-008 recorded that the
programme was *"still blocked on exactly one thing: three named campus
contacts."* That is no longer true.** Under D-009 the build runs to Gate B
without a campus, and campus access is a Gate C dependency. **That is a real and
underappreciated consequence of the override, and it is in the founder's
favour.**

### 3.6 Superseded text — the original §3, retained

The original Gate A table is retained below because **A0's reasoning is still
the reasoning**, now carried by ADR-002 §4 instead of by an operator, and
because §4's envelope is cross-referenced by `COMPLIANCE.md`, ADR-003 and
`TEST-1-CONCIERGE-PILOT.md`.

### Gate A *(SUPERSEDED — see §3.2)* — the concierge pilot may run (no code, no platform, 14 days)

**Hard precondition, and the whole gate turns on it:**

> **A0. BookHop must operate no browsable listing surface.** The human operator
> holds the list. Participants never see each other's listings in a shared
> sheet, a group, a channel or a published document. Matches are made by a
> person and communicated one-to-one.
>
> **Why this is the hinge.** r.3(1)(b) makes an "e-commerce entity" anyone who
> "owns, operates or manages digital or electronic facility or platform for
> electronic commerce". A private intake form feeding a private spreadsheet
> that only the operator reads is a record, not a platform — there is no
> facility on which buyers encounter sellers' goods. **The moment participants
> can browse each other's listings, BookHop is operating a platform, and
> r.4(1)(a) (be a company), r.4(2) (display legal name and address) and r.4(4)
> (grievance officer) attach immediately — before the company exists.** This is
> a bright line and marketplace-ops should treat it as one.
>
> **Uncertainty: MODERATE.** This is my reading of "manages a facility", not a
> settled position, and I found no clarification on it. It is defensible and
> the exposure at 30 handovers over 14 days is small. It is not a position I
> would hold at 300 handovers.

Then, in order:

| | Must be true | Owner | Blocks on |
|---|---|---|---|
| A1 | **Written campus permission for a 14-day study**, one page, from each institution | founder | — |
| A2 | A0 confirmed in the pilot design: no browsable surface | marketplace-ops | — |
| A3 | **Participant notice + recorded consent**, EN and TA (§4.4) | marketplace-ops | — |
| A4 | **18+ confirmed at intake**, under-18s declined and the decline logged | marketplace-ops | — |
| A5 | **Collection list frozen** to §4.2. No PAN, no Aadhaar, no UPI handle, no address, **no settled price** | marketplace-ops | — |
| A6 | **Fee A/B built to §4.3** — fee computed on the *asking* price, cash only | marketplace-ops | A5 |
| A7 | **Copy reviewed** against the may/may-not-say list in §4.1 | marketplace-ops + design-director | — |
| A8 | **Spreadsheet custody**: one named holder, one account, 2FA on, audit log on, retention rule in §4.5 written at the top of the sheet | marketplace-ops | — |
| A9 | **CERT-In point of contact named** and the 6-hour rule understood (§4.6) | founder | A8 |
| A10 | Pre-set public handover points; inspect-before-pay scripted into the operator's messages | marketplace-ops | A7 |

**Not required at Gate A:** incorporation, grievance officer, IT Rules clocks,
takedown SOP, consent infrastructure, deletion flow, counsel-drafted terms,
any DPDP artefact, GST, insurance.
**Legal spend required at Gate A: zero.**

### Gate B *(SUPERSEDED — its items split between §3.3 and §3.4)* — any code may ship, even to a closed test group

> **Why this definition was wrong.** *"Any code may ship"* treats a deployment
> as the legal event. It is not. The legal events are a real person's data
> entering the system (§3.3) and a real student seeing another's listing
> (§3.4), and B1–B16 below divide between them. **B13 moved earlier still, to
> Gate A.**

Everything at Gate A that persists, plus — and this is where the real work is:

| | Must be true | Owner | Blocks on |
|---|---|---|---|
| B1 | **Certificate of Incorporation issued** (P1) | founder + CS | §1 |
| B2 | **Subscription money paid and INC-20A filed** (N1) — the company may not commence business before this | founder + CS | B1 |
| B3 | **First auditor appointed** within 30 days of B1 (N1) | founder + CA | B1 |
| B4 | **Grievance Officer and India-resident nodal contact appointed and published** (P2) | founder + ops | B1 |
| B5 | **Counsel-drafted terms, standalone privacy notice, r.5(2) seller undertaking, liability clause** (P4) | counsel | §5 C1, C2 |
| B6 | **Takedown + grievance SOP implemented with SLA timers in the system** (P3) | marketplace-ops + cto | B4, B5 |
| B7 | **Age gate built**: DOB date field, server-side 18+ rejection, DOB purged post-verification, no ID upload (P5) | cto | §5 C3 |
| B8 | **Per-purpose consent capture, append-only, no pre-ticked boxes** (P6) | cto | B5 |
| B9 | **Deletion = tombstone + purge, with the expiry job built at the same time** (P7) | cto | B8 |
| B10 | **Breach runbook written to 6 hours; logs in India, 180-day rolling minimum, NTP-synced to NIC/NPL** (P8) | cto | — |
| B11 | **Copyright takedown SOP + r.5(5) repeat-infringer record + ISBN requirement + photocopy/spiral-binding flag** (P9) | marketplace-ops + cto | B6 |
| B12 | **Handover safety design in the product; full copy review; no safety warranty anywhere** (P10) | product + design-director | — |
| B13 | **P14 enforced in the schema**: no `pan`, no `aadhaar`, **no `settled_price`** column; asking price only | cto | — |
| B14 | **No credit of any design in the build** (P12); reputation signal ordinal only if present at all | cto | — |
| B15 | **Signed data-processing contract with every vendor** touching personal data — hosting, SMS/OTP, object storage, error tracking (r.6(1)(f), design-ahead) | cto + founder | B1 |
| B16 | **No struck-through prices, no promoted listings, no generative AI in listing creation** | product + design-director | — |

### Gate C *(SUPERSEDED — see §3.4, which absorbs all of it)* — the closed campus pilot may run on the platform

Everything at Gate B, plus:

| | Must be true | Owner |
|---|---|---|
| C1 | **Full campus MoU signed**, covering the platform and not just a study: enrolment-data sharing and its basis, name and logo use, liability on premises, termination (P11) | founder + counsel (§5 C5) |
| C2 | **P13 closed**: Copyright Rules r.75 text and scope verified; TN Shops & Establishments applicability verified | privacy-compliance |
| C3 | **Breach runbook rehearsed once, end to end**, with the rehearsal logged | cto + ops |
| C4 | **On-call rota rostered with named people** covering the 2-hour and 3-hour clocks | marketplace-ops |
| C5 | **Grievance ticketing tested end to end** — a real complaint acknowledged inside 24 hours with a ticket number | marketplace-ops |
| C6 | **Age-review queue staffed**, with a written procedure for a discovered minor: suspend, erase, log; POCSO reporting duty understood | marketplace-ops |
| C7 | **Every rule re-verified**; DPDP commencement and the RBI 2026 PPI Master Direction re-checked | privacy-compliance |
| C8 | **Insurance decision taken** — public liability / professional indemnity, or a recorded decision not to | founder |

**Gate D (public launch)** remains L1–L14 in COMPLIANCE.md §6.2, less L2 and
L12 while v1 is free, plus N2 if the institutional payer materialises.

---

## 4. The concierge pilot's compliance envelope — **retained as the app's inheritance**

> **v1.1 status.** D-009 cancelled the paper pilot, so this section is no longer
> an operating brief for marketplace-ops. **It is retained, not deleted, because
> three of its parts become artefacts in the app and because the reasoning is
> what the gates in §3 rest on:**
>
> | This section | Becomes |
> |---|---|
> | **§4.1** may/may-not-say list | **The fixture for `tests/unit/test_forbidden_copy.py`** (Gate A item A2′). Every forbidden string there is still forbidden, now mechanically. Add `COMPLIANCE.md` §4.3.2 item 9's strings to it |
> | **§4.2** collection list | **The schema deny-list** (ADR-003 §2.3 + `COMPLIANCE.md` §4.3.2). *"MAY NOT collect"* became `information_schema` assertions |
> | **§4.5** retention rule | **The pattern for `COMPLIANCE.md` §7 row 23** — identifiers expire, measurement data survives pseudonymised. Same rule, now at the one-year statutory floor |
> | **§4.3(iv)** r.4(11)(b) warning | **Still live and now architectural.** ADR-003 §3 records that the architecture offers no mechanism for a price A/B. **N3 is closed; the warning is not** |
> | **§4.4** participant consent | Absorbed into Gate B item B3′ (per-purpose consent capture) |
> | **§4.6** applicability analysis | **Superseded in two places.** The *"not an intermediary, conditional on A0"* holding **fails at the first real user** — see §3.3 B1′. The **GREY s194-O grading is superseded by `COMPLIANCE.md` §4.3.1** |
>
> **One sentence in §4.5 survives verbatim and still binds:** *"if this dataset
> is later migrated into the product, that is a new purpose and needs fresh
> consent."* There is no pilot dataset to migrate now — but the same rule applies
> to **seed data**: a seed account must never be converted into a real one.

**For marketplace-ops. Build to this.** Short answers, no hedging. Everything
here assumes **A0 holds: no browsable listing surface** (§3). If that changes,
this entire section is void and Gate B applies instead.

### 4.1 What the operator may and may not say

**MAY say:**
- "Condition as stated by the seller." / "Edition and ISBN as stated by the seller."
- "Check the book before you hand over any money."
- "Meet at [named public campus point] between [daylight hours]."
- "This is a 14-day study run by [founder's own name]. It is not a company yet
  and there is no app."
- "You can stop at any point and we will delete your details."
- "If something goes wrong, tell us and tell campus security; we will keep a
  record."

**MAY NOT say — any of these creates a liability we cannot carry:**
- "BookHop verified", "verified seller", "guaranteed authentic", "condition
  assured", "quality checked".
- "Safe handover", "safe meetup", "BookHop-protected", "secure".
  **Guidance is protective. A guarantee is an assumed duty of care.**
- "We will refund you", "money-back", "buyer protection". BookHop holds no
  money and cannot refund.
- "BookHop Private Limited", any CIN, "registered company" — **none of this is
  true yet and saying it is a misrepresentation.**
- Any promise of future credits, discounts, priority or points. **D-007 ships
  no credit of any design, and a promise of one is a promise of a redeemable
  balance.**
- Any claim the service continues after the 14 days.
- Any implication the college endorses or runs it, unless the A1 permission
  letter expressly allows name use.

### 4.2 What may and may not be collected

**MAY collect:**
first name + initial · one contact number *or* messaging handle · campus ·
course and year (optional) · book title, ISBN, edition · **seller's asking
price** · seller-stated condition · handover point and time · handover
completed yes/no · support minutes (the operator's own stopwatch) · fee asked
yes/no and fee paid yes/no · how the participant heard about the pilot (for
CAC) · one free-text comment.

**MAY NOT collect — each for a stated reason:**
- **PAN. Aadhaar. Any government ID. Any photograph of an ID.** (P14; and these
  are "sensitive personal data" under SPDI r.3, which would pull a 14-day paper
  pilot into a security regime it currently sits outside.)
- **The settled sale price.** (P14 — a recorded settled price creates a
  determinable "gross amount of such sales" under s194-O / s393. Record the
  *asking* price only, and record completion as a boolean.)
- **Bank account numbers or UPI handles.** A UPI handle is arguably
  financial-instrument data and therefore SPDI r.3 sensitive personal data.
  **Take the A/B fee in cash. This is the cheapest compliance decision in the
  whole pilot.**
- **Home or hostel address. Precise location.** (§5.5 of COMPLIANCE.md; and it
  is the specific disclosure that turns a handover into a risk.)
- **Date of birth.** Record **"18+ confirmed by [operator] on [date]"** — the
  outcome, not the input.
- **Photographs of people. Chat screenshots**, except where a safety report
  requires one.
- Anything about health, caste, religion, politics or sexual orientation.

### 4.3 Does the fee A/B create a tax or e-commerce obligation? — **No. Here are the four answers separately.**

**(i) Tax on the fee itself: no.** At the Test 1 pass bar — 30 handovers, roughly
half in the fee arm, ~₹300 average book, 6% ≈ ₹18 — total receipts land in the
low hundreds of rupees. Nothing triggers:
- **GST: no.** BookHop collects no sale consideration, so CGST s52 TCS never
  engages and s24(x) compulsory registration (which is conditioned on being
  *required* to collect TCS) never bites. The fee is BookHop's own supply of
  service, but aggregate turnover is nowhere near the s22(1) ₹20 lakh threshold.
- **Income tax: no new obligation.** Pre-incorporation this is the **founder's
  personal income**, declarable in the founder's own ITR. It is not company
  revenue, must not be invoiced as such, and must be entered in the D-007 budget
  ledger as a receipt.

**(ii) s194-O / s393: unchanged by the fee, and unchanged by being free.** The
obligation is triggered by **facilitating the sale**, not by earning from it
(§0). The mitigation is P14 and nothing else.

**(iii) The collision ops must design around, and the fix.** A fee of "6% of the
sale" requires knowing the sale price — **which P14 forbids recording.**

> **Build rule: compute the fee as 6% of the seller's stated asking price,
> fixed at the time the listing is taken, rounded to the rupee, and recorded as
> `fee_asked: ₹18 (6% of asking price ₹300)`. Never ask, and never record, what
> the book actually sold for.** The A/B still measures fee-paid ÷ fee-asked
> exactly as designed, and P14 survives intact.

**(iv) E-Commerce Rules: no — but there is one provision ops should know about.**
Charging a fee does not create e-commerce-entity status; **operating a platform
does**, and A0 is what keeps us out. However:

> **E-Com r.4(11)(b), verified today from the Gazette: "No e-commerce entity
> shall ... discriminate between consumers of the same class or make any
> arbitrary classification of consumers affecting their rights under the Act."**
>
> **A randomised 6%-vs-free split is, on its face, an arbitrary classification
> of consumers of the same class.** It does not bite at Gate A, because BookHop
> is not an e-commerce entity (A0) and because participants are consenting
> research subjects who have been told they are in a study. **It would bite on
> the live platform.** Two consequences: the participant consent in §4.4 must
> say the pricing differs between participants, and **a price A/B must not be
> repeated on the platform after Gate B without counsel.** Flag this now rather
> than when product proposes the obvious follow-up experiment.

### 4.4 Consent needed from participants

**DPDP does not bind — its operative provisions commence 13 May 2027.** This
consent is not a DPDP artefact. Take it anyway: it costs one paragraph, it is
the thing that makes the fee A/B defensible under §4.3(iv), and it is the
pattern you will need in 2027.

A **one-paragraph notice, in English and Tamil**, given at intake and recorded
with a tick or a verbal yes plus the date, saying:
1. **Who** is running this — the founder, by name, as an individual, not a
   company.
2. **What is recorded** — the §4.2 list, itemised, not summarised.
3. **What is not recorded** — no ID, no bank details, no address, no sale price.
4. **How long** — §4.5, stated in days.
5. **That this is a 14-day study**, that participation is voluntary, and that
   they can withdraw and have their details deleted by messaging one named
   contact.
6. **That some participants are asked for a fee and others are not**, and that
   this is part of the study. *(This sentence is what defuses §4.3(iv) and the
   dark-patterns concern. Do not drop it to improve the response rate — dropping
   it is the dark pattern.)*
7. **A named contact** with a phone number or email.

A **separate explicit yes for the fee arm** at the moment the fee is asked,
recorded in the sheet.

### 4.5 Retention rule for the pilot spreadsheet

**No statutory floor applies.** DPDP r.8(3)'s and r.6(1)(e)'s one-year minimums
are not in force until 13 May 2027. CERT-In's 180-day rule covers ICT **system
logs**, not a research dataset. **So this is a judgement call, and here is the
rule — write it at the top of the sheet:**

| Data | Rule |
|---|---|
| **Identifiers** — name, contact number or handle, campus, course | **Delete 30 days after the last handover, or immediately on request.** Replace with a pseudonym `P-001`…`P-0nn`. |
| **Measurement data** — support minutes, fee asked/paid, handover completed, acquisition source, asking price, ISBN | **Keep indefinitely, pseudonymised** after the 30-day mark. This is the evidence Test 1 exists to produce. |
| **Safety reports and incidents** | **Keep one year**, with identifiers, in a separate access-controlled file. An incident can surface late, and the record of a report that was handled is the thing that matters if one was not. |
| **Consent records** | Keep as long as the pseudonymised dataset exists. It is the record that collection was lawful. |
| **Custody** | One named holder. One account. 2FA on. Sheet audit log on. No copies, no exports to personal devices, no sharing links. |

> **One rule that is easy to get wrong:** if this dataset is later migrated into
> the product, **that is a new purpose and needs fresh consent.** Pilot
> participants consented to a 14-day study, not to being seeded as users.

### 4.6 Which rules actually apply to a 14-day paper pilot

**APPLY:**
- **CERT-In Directions 2022** — thinly but genuinely. They bind any "body
  corporate", and the IT Act s43A Explanation defines that to include a sole
  proprietorship engaged in commercial activity. Practical effect: **if the
  sheet is breached or leaked, that is Annexure I item (xi) "Data Breach" or
  (xii) "Data Leak" and must be reported to CERT-In within 6 hours** at
  incident@cert-in.org.in or 1800-11-4949. Name a point of contact (A9). Keep
  the sheet's audit log on. NTP synchronisation is not meaningfully applicable
  to a hosted spreadsheet.
- **IT Act s43A + SPDI Rules 2011** — but only if sensitive personal data is
  collected. **Follow §4.2 and they are effectively inert.** This is the entire
  reason for the no-UPI-handle rule.
- **General law** — contract, tort, criminal law. **POCSO mandatory reporting
  if a minor turns out to be involved in any incident.**

**DO NOT APPLY:**
- **DPDP Act and Rules.** Operative provisions commence **13 May 2027**. Notice,
  consent, breach notification, data-principal rights and penalties do not bind
  a pilot running in 2026.
- **IT Rules 2021 intermediary obligations** — the 3-hour, 2-hour, 24-hour and
  7-day clocks, the grievance officer, the quarterly user reminder. BookHop is
  not an intermediary at Gate A: no computer resource of ours receives, stores
  or transmits records on users' behalf. **Conditional on A0.**
- **Consumer Protection (E-Commerce) Rules r.4 and r.5** — no e-commerce
  entity. **Conditional on A0.**
- **GST, CGST s52 TCS, RBI PPI.** Nothing to attach to.

**GREY, and mitigated rather than avoided:**
- **s194-O / s393.** Facilitation alone is enough, and the deeming Explanation
  is drafted to catch exactly a direct cash handover. We do not clear it; we
  make it indeterminable by never recording a settled price (P14). **That is an
  argument, not a safe harbour. It holds at 30 handovers. It will need counsel
  before it holds at 3,000.**

---

## 5. Counsel brief — one page, quotable for a fee

> **To Indian technology / consumer counsel.** Below are the facts and the
> questions. We are a pre-incorporation, pre-revenue campus project and we are
> asking you to scope and quote. We have ranked the questions by what blocks us
> soonest and marked what we believe can wait. **Nothing before item C1 requires
> your time: our 14-day paper pilot runs without you.**

### The facts you need

1. **What it is.** A matching service for **used prescribed textbooks** between
   students on a single Chennai campus. Buyer and seller meet in person on
   campus and hand over the book.
2. **Money.** **The service is free to students, permanently by design.** Cash
   passes **directly from buyer to seller** in person. **BookHop never touches,
   holds, escrows or settles any money.** There is no payment integration, no
   wallet, no credit, no points, no stored balance of any kind.
3. **Revenue.** None in v1. A hypothesised future institutional payer (a college
   paying for the service) is being tested but is not committed.
4. **Entity.** Not yet incorporated. A private limited company is being formed
   now specifically because **Consumer Protection (E-Commerce) Rules r.4(1)(a)**
   requires an e-commerce entity to be a company.
5. **Users.** **Adults only (18+).** We know a Chennai campus population includes
   17-year-olds and we treat under-18 signups as a certainty to engineer
   against. **We collect no PAN, no Aadhaar and no identity documents.**
6. **Sellers.** Individual students disposing of their own used textbooks, not
   acting in the course of business. We believe they fall within the **r.2(1)
   proviso** (natural person in a personal capacity, not regular or systematic).
7. **What we do not do.** No shipping. No inventory. No first-party sales. No
   promoted or sponsored listings. No struck-through prices. No generative AI in
   listing creation. No safety warranties in any copy.
8. **Scale.** A 14-day paper pilot of roughly 30 handovers, then a closed
   single-campus pilot. Not public.
9. **Timing.** A 14-day operator-run paper pilot runs first, with no software.
   Software ships only after your advice on C1–C3.
10. **Our own reading** is in `COMPLIANCE.md`; we are not asking you to repeat
    it. We are asking you to settle the four things we could not.

### The questions, ranked by what blocks soonest

**TIER 1 — blocks the first line of code. These three are one engagement.**

> **v1.1 re-ranking, because D-009 moved the wall clock and the tier label is
> now misleading.** *"Blocks the first line of code"* is no longer the right
> test — code is being written today under D-009 and the discovery gate
> (§3.2). The right test is **which gate each question blocks**:
>
> | | Blocks | Changed? | Why |
> |---|---|---|---|
> | **C1** documents | **Gate B** = first real signup | **MORE urgent in wall-clock terms** | "Before the first line of code" used to mean *after a 14-day paper pilot*. It now means *before the first real student account*, which under D-009 could be weeks away. **This is the one to buy first.** |
> | **C3** adult verification | **Gate B** | Unchanged, and still the cheapest of the three | The age gate is built once and is painful to change |
> | **C2** C2C scope | **Gate C** *(moved from Gate B)* | **LESS urgent** | It determines the **seller-profile UI and the address question** — and a seller profile is only visible to another student once discovery opens. **The schema is already built on the maximally conservative answer: no addresses collected anywhere, with the r.5(3)(a) proviso served by `contact_disclosures` (a reviewed, logged disclosure).** If counsel says we must publish more, that is an *additive* migration under INFRA.md's expand-then-contract rule — cheap. We are not building the wrong listing model; we are building the smallest one. |
>
> **Consequence: buy C1 and C3 first and C2 with the Gate C work**, or buy all
> three together if the quote is better as one engagement — which §5's closing
> paragraph still says it will be, and that reasoning is unchanged.
> **Add the C11 tax limb (above) to whichever engagement is bought at Gate B.**

**C1. Documents.** Draft and review: a **standalone** privacy notice
(structured for DPDP Rule 3 compliance from 13 May 2027, but operative now),
user terms, seller terms containing the **r.5(2) accuracy undertaking**, the
limitation-of-liability clause, and the Grievance Officer appointment.
*Constraints we will not move on: no custody of funds; no safety warranties; no
seller addresses published; no PAN or Aadhaar collected.*
**Needed by:** Gate B. **Can it wait?** **No.** Nothing ships without it.

**C2. C2C scope — the question we most need settled.** Do the Consumer
Protection (E-Commerce) Rules 2020 (as amended by **G.S.R. 789(E)**, in force
1 Jan 2027) apply to a C2C used-goods marketplace where the seller is a natural
person inside the **r.2(1) proviso**, nothing is shipped, and payment is in cash
between individuals offline? Specifically: **does r.5(3)(a) oblige us to publish
an individual student seller's geographic address**, given that r.3(1)(k) defines
"seller" by reference to **s2(37) CPA 2019 ("in the course of business")**? Is a
**reviewed, logged, post-purchase disclosure** under the r.5(3)(a) proviso
sufficient instead? At what transaction volume does an individual student become
"regular or systematic" and lose the proviso? And does **r.6(3)** (no refusal to
take back misdescribed goods) attach to such a seller, given the platform holds
no funds and the remedy we have designed is inspect-before-pay?
**Needed by:** Gate B — it determines the listing schema and the seller-profile
UI, not just the policy page. **Can it wait?** **No.** Building the wrong
listing model and rebuilding it is more expensive than the opinion.

**C3. Adult verification.** For an adults-only platform that processes **no**
children's data, what diligence satisfies **DPDP s9 and Rule 10** in establishing
that a user is 18+, given that **Rule 10 prescribes a method only for verifying a
parent** and prescribes none for verifying an adult? Is a stored date of birth
with a server-side block, plus a logged human review, defensible? Does **Fourth
Schedule Part B item 6** cover that processing? What is our exposure if a
17-year-old defeats the gate — and does it worsen because we have written down
that the campus population includes minors?
**Needed by:** Gate B. **Can it wait?** **No** — the age gate is built once and
is painful to change afterwards. This is the cheapest of the three to answer.

**TIER 2 — before the closed campus pilot (Gate C).**

**C4. Copyright takedown.** Confirm the current text and timelines of **Copyright
Rules 2013 r.75**, whether it reaches a marketplace hosting listings as opposed
to the transient and incidental storage addressed by **s52(1)(b)–(c)**, and
review our notice-and-takedown SOP and seller undertaking for **IT Act s79**
safe-harbour preservation. *Context: v1 is prescribed textbooks only, which is
precisely where photocopied and pirated copies concentrate.*
**Can it wait?** **Yes, until Gate C** — but not past it. Pirated listings will
appear in week one.

**C5. Campus MoU template.** A template the founder will sign repeatedly,
covering: permission to operate on premises; whether and how the institution
shares or confirms **student enrolment data** and on what lawful basis; use of
the institution's **name and marks**; liability allocation for incidents on
premises; and termination.
**Can it wait?** **Yes for the paper pilot** — a one-page written permission for
a 14-day study is something the founder can obtain unaided. **No for Gate C.**

**TIER 3 — before public launch.**

**C6. Where hosting becomes vouching.** At what point does condition grading,
edition matching or trust badging make BookHop a **"product seller" under s2(37)
CPA 2019** or a product service provider, so that **Chapter VI product liability**
attaches? What specific wording keeps us on the hosting side?

**C7. Duty of care on handovers.** Does suggesting meeting points, times and
counterparties create an **assumed duty of care** for physical safety? What
limitation-of-liability drafting is enforceable in India, noting that negligence
liability generally cannot be excluded? Which product or copy changes most reduce
the exposure?

**C8. Erasure versus retention.** How do we reconcile the **s12(3)** erasure right
with the **Rule 8(3)** one-year minimum retention of personal data, traffic data
and processing logs? Is tombstone-plus-pseudonymisation compliant, and what must
the notice say about it? **Needed before 13 May 2027.**

**TIER 4 — dormant. Do not pay for these now.**

**C9. (was Q7) PPI / credit design.** **Dormant.** D-007 cut direct swap from v1,
which removed the only problem credits existed to solve, and no credit of any
design ships. Reactivate the moment anyone proposes a denominated redeemable
balance — the analysis in COMPLIANCE.md §3 stands unchanged and the question is
already drafted.

**C10. (was Q8) GST and TCS.** **Dormant.** No consideration is collected and
BookHop makes no outward supply. Reactivate before any fee or any institutional
revenue — and note the institutional-payer test (N2) is the thing most likely to
reactivate it.

**C11. (was Q9) s194-O / s393 TDS — the judgement call. · RE-RANKED AND
RE-DRAFTED AT v1.1.**

**Verdict: still not urgent. Now SCHEDULED at Gate B and BUNDLED into the C1–C3
engagement rather than merely deferred.**

v1.0 made deferral conditional: *"This can wait until Gate B if and only if P14
is enforced in the schema."* **The condition is met.** ADR-003 implements it with
a database trigger, a CI deny-list test, and an instruction that a diff to that
test is a founder escalation rather than a review comment. **And the position
got stronger, not weaker:** `COMPLIANCE.md` §4.3.1 found **CBDT Circular
20/2021** (e-auction — price discovery only, price *"not necessarily the price
at which the transaction takes place"*, transaction and payment both outside the
portal, operator *"does not have any information about the quantum and the
schedule of payment"* → **s194-O does not apply**) and **Circular 17/2020 para
4.3** (*"no involvement in transactions"* → *"would not be liable to deduct"*).
Uncertainty moved **HIGH → MODERATE**. Stronger interim positions are a reason
to defer, not to accelerate.

**Three changes:**

1. **Bundle it.** By Gate B the founder is already paying counsel for C1 and C3.
   **Add a tax-counsel limb to that engagement.** A drafted, narrow question
   alongside work already commissioned is the cheapest this will ever be. Buying
   it separately later is the second-cheapest sequencing mistake available (the
   cheapest remains paying for C9 and C10 now).
2. **Ask a narrower question.** The full text is at `COMPLIANCE.md` §9 Q9,
   re-drafted to ask **whether Circular 20/2021 applies to our facts** and
   **whether the circulars retain binding force after 1 April 2026** (they were
   issued under s194-O(4) and bound under s194-O(5); the 2025 Act appears to have
   no re-enacted guidelines power at Sl. No. 8(v), and s536(2)(j) carries them
   only *"so far as not inconsistent"*). **A yes/no on a named circular is far
   cheaper, and far more useful, than an open-ended "does s194-O catch us".**
3. **The tripwire gains a third trigger.** C11 becomes urgent **that day** if
   anyone proposes:
   - **(a)** storing any settled, agreed, offered or **accepted** amount — note
     that an **accepted offer amount is a settled consideration**, and it is the
     most likely next feature request;
   - **(b)** a fee, a payment integration, or any money through BookHop; or
   - **(c)** **NEW — copy or UX that presents the asking price as the
     transaction price.** Circular 20/2021's second limb needs the asking price
     to be *"not necessarily the price at which the transaction takes place"*.
     **P14's immutability makes the asking price a *better* proxy for the settled
     price, not a worse one**, so the negotiability has to be real and the copy
     has to say so. `"pay the listed price"`, `"fixed price"`,
     `"non-negotiable"` and `"final price"` are forbidden strings.
     **This limb lives in copy. The schema cannot carry it.**

**Also correct the citation when you brief counsel:** the ₹5 lakh individual/HUF
relief is at **s393(4) Table Sl. No. 11**, not inside the charging entry at
s393(1) Table Sl. No. 8(v).

### My honest estimate, given that legal spend is not approved

**v1.1: zero legal spend is still required to BUILD.** Gate A (§3.2) needs no
counsel, no campus letter, no incorporation and no infrastructure. **What
changed is that the thing Gate A used to sit in front of — a 14-day paper pilot
— is gone, so the next thing after Gate A is a real student account, and that
needs C1.**

**Three questions genuinely cannot wait, and they are C1, C2 and C3.** They
should be bought as **one scoped engagement** — "review a pre-launch C2C campus
marketplace's documents and data model" — because they are the same reading of
the same rules and a lawyer quoting them separately is quoting the same work
three times. **v1.1: C1 and C3 block Gate B; C2 blocks Gate C (see the Tier 1
re-ranking above); and the C11 tax limb should ride along with whichever
engagement is bought at Gate B.**

**The cheapest sequencing mistake available to BookHop is to pay for C9 and C10
now.** Both are dormant under D-007 and D-009 changes nothing about that. The
second-cheapest is to defer C2 until after the **seller-profile UI** is built —
note the correction: v1.0 said "after the schema is built", and on reflection the
schema is not the exposure, because it is built on the conservative answer.

---

## 6. The founder's one real decision under D-009 · **new at v1.1**

**This is framed, not decided. It is a founder authority and nobody else's.**

D-009's mitigation for building before measuring is that *"the app is
instrumented to measure support time, match rate, time to match, completion and
leakage directly, so the product becomes the measurement instrument."* **That
mitigation needs real users.** The resequencing in §3 exposes a choice nobody has
priced:

| | **Option 1 — real users before discovery** *(Gate B as a separate, earlier event)* | **Option 2 — real users with discovery** *(Gate B and C collapse)* |
|---|---|---|
| **What it is** | A closed beta: real students hold accounts and create listings only they and staff can see. Discovery opens later | Nothing real happens until the company exists, the MoU is signed and discovery opens |
| **Counsel** | **C1 and C3 needed sooner** | C1, C2, C3 all at once, later |
| **Infrastructure** | **Spend starts at Gate B.** INFRA.md §1 assumes *"real student data from Gate C"*; under Option 1 it arrives earlier, so the box, the one-year logs, the NTP sync, the backups and a **tested restore** are all needed earlier. **Rs 630–1,750/month starts sooner than ADR-001 §7.1's packet assumes** | Spend starts at Gate C, as currently assumed |
| **Incorporation** | Not a hard blocker, **but Gate B is a holding position and not a destination** (§3.3). The A0 reading was graded MODERATE and scoped to 30 handovers | Required anyway |
| **What D-009 gets** | **Instrumented real-usage data before the company exists** — support minutes, intake time, listing-creation drop-off. **Not** match rate, time to match, completion or leakage, because those all need two students who can find each other | **No instrumented data until Gate C.** D-009's reversal trigger — *"support time per transfer exceeds 4.00 minutes once there are 30 real handovers"* — cannot fire until then |
| **Risk** | A longer period relying on the A0 reading; earlier spend; more surface before counsel | The founder waits longer for the number D-009 exists to obtain |

**The honest asymmetry, and it is the thing worth knowing.** Option 1 buys
*some* instrumentation early, but **the four metrics that decide the business —
match rate, time to match, completion and leakage — are all two-sided and none
of them is measurable before discovery opens.** So Option 1 buys support-minutes
data and little else, at the cost of earlier spend and a longer reliance on a
MODERATE-uncertainty reading.

> **My recommendation, offered as a compliance view and not as a product
> decision: collapse Gate B into Gate C unless the founder specifically wants
> support-minutes data early.** It is less exposure, less spend, and a shorter
> time holding a reading I have graded MODERATE. If the founder does want Option
> 1, it is **available and defensible** — it just needs B1′–B10′ in full, and
> the grievance officer published in the founder's own name from the first real
> signup.

**Either way, §3.2's Gate A is open and the build is not blocked by this
decision.** It only has to be made before the first real account is created.

---

**This is not legal advice. I am not a lawyer and cannot give legal sign-off.
A qualified Indian lawyer must review BookHop's terms, privacy notice and seller
arrangements before public launch, and a qualified Indian chartered accountant or
tax counsel must review the s194-O position (§5 C11) before volume grows.
Nothing in D-009, and nothing in this v1.1 revision, removes either
requirement.** The incorporation filing itself requires a practising Chartered
Accountant or Company Secretary and cannot be self-filed. Every figure in §1.4
is commentary-sourced because mca.gov.in returned HTTP 403 on 2026-10-21 and
must be confirmed at filing time.
