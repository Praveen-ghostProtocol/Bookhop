# COMPLIANCE.md — Regulatory review

**Owner:** privacy-compliance · **Version:** v1.4 · **All sources accessed:** 2026-10-21
(v1.4 adds no new source; it rules on two inventory gaps against rule text already verified above)
**Handoff:** ceo-planning, cto, red-team, human founder

---

## Changelog

### v1.5 — 2026-10-23 · a scope this document was never written for

The founder asked what a **closed test among ~12 personally-known adults**
requires, and how much of the ten-field discovery gate is overkill for it.
**That answer is in `company/evidence/CLOSED-TEST.md`, not here**, because
every field answer differs from the campus answer and interleaving the two
would make the campus rulings ambiguous.

**Three things from it that bind this document.** (i) The gate a friends test
crosses is **Gate B, and Gate B has no guard in the code and no evidence
requirement in the database** — `ops/INCORPORATION-AND-BLOCKERS.md` §3.3 B9′
was specified and never built, and migration 0005 exempts `gate='B'` by
design. (ii) `campus_mou_ref` is **unsatisfiable** at that scope, which is a
rule-10 defect, not an inconvenience. (iii) **SPDI Rule 4 is primary-verified
to cover "personal information including sensitive personal data or
information"** — not SPDI only — and "body corporate" under s43A Explanation (i)
reaches a sole proprietorship, so **a published privacy notice binds an
unincorporated founder today.** §1.1's statement that the current statutory
privacy floor "is thin" stands as to *content*; the **publication** duty is not
thin and applies pre-incorporation.

Nothing in this document is relaxed. **The condition set remains P1–P16.**

### v1.1 — 2026-10-21 · prompted by D-009 and three CTO escalations

| # | Change | Why |
|---|---|---|
| 1 | **§5.2 rewritten; new §5.2.1 — CERT-In data residency ANSWERED.** The CTO's reading (ADR-001 §5) is **CONFIRMED**, uncertainty downgraded MODERATE → **LOW**. A VM in an Indian region of a foreign-owned provider satisfies Direction (iv). Provider ownership, incorporation and foreign lawful-access exposure are **not** what Direction (iv) turns on. **Do not move providers and do not spend money on the hedge.** ADR-001 §8's reversal trigger is recorded NOT FIRED. | ADR-001 §5 and §7.2 routed this to me as an open question; INFRA.md §2 says nothing deploys until I answer. Answered from the primary direction **and** CERT-In's own FAQ Q35/Q36, both newly extracted. |
| 2 | **§4.3 substantially strengthened; s194-O regraded.** Found the authority the v1.0 review said it could not find: **CBDT Circular 20/2021** (e-auction) and **Circular 17/2020 para 4.3**. The asking-price-plus-completion construction **holds on the better view**. Uncertainty HIGH → **MODERATE**. Also two corrections to our own citations and one new uncertainty (the circulars' binding force after 1 Apr 2026). | CTO escalation: ADR-003 §5.3 asked whether asking price + completion is a determinable gross amount. It is the right question and it needed re-searching, not re-asserting. |
| 3 | **§4.3.1 new — what the forbidden-schema test must forbid.** Nine concrete requirements, including inverting the deny-list into a **whitelist** and freezing the column list of the four transaction tables. **Two of them are not in ADR-003 §2.3 today and my position does not hold without them.** | ADR-003 §5.2 asked for exactly this. |
| 4 | **§7 — four new data-inventory rows (21–24).** Includes one **refusal of the CTO's proposed lawful basis** (row 22 must not sit behind withdrawable consent) and one **recommended schema reduction** (row 21: drop `actor_pseudonym` from `search_events`; no metric needs it). Row 24 (the salt) corrects a premise in the request itself. | DATA-MODEL.md §11.1 and ADR-001 §7.4 routed four fields here. §7's own standing rule: a field without a row is a compliance defect. |
| 5 | **§9 Q9 re-drafted** around Circular 20/2021 so counsel is asked an answerable question rather than an open one. Cheaper to buy, better answer. | Consequence of change 2. |
| 6 | §10 open-items ledger updated: CERT-In **closed**; two new open items recorded; the s194-O item re-stated rather than closed. | The charter metric is days since rule text last re-verified. |
| 7 | **§11 verdict amended** for D-009 and for the gate resequencing in `ops/INCORPORATION-AND-BLOCKERS.md` §3. | D-009 voided the gate the verdict was written against. |

**Re-verified today and unchanged:** DPDP commencement **13 May 2027** (the January 2026 compression proposal is still unnotified). **New instrument found and assessed as immaterial:** the **DPDP (Removal of Difficulties) Order, 2026, S.O. 5458(E)**, 5 Oct 2026, which makes two purely textual corrections — "child or a person with disability" → "child or **of** a person with disability" in s9(1), and "audit" → "data audit" in s10(2)(c)(ii). **It changes nothing for BookHop's age gate or SDF position and it does not move any commencement date.** *(Commentary-sourced: https://ssrana.in/articles/dpdp-removal-of-difficulties-order-2026-what-has-been-changed-for-childrens-data-and-sdf-audits/ and https://www.scconline.com/blog/post/2026/10/15/dpdp-removal-of-difficulties-order-2026/, both accessed 2026-10-21. I did not reach the Gazette text. It is recorded here so that nobody discovers it later and assumes it mattered.)*

### v1.2 — 2026-10-21 · two blocking design rulings, both answered

Design escalated two strings to me and **correctly refused to treat v1.1's
silence as approval**. Both are now ruled on, concretely, with wording.

| # | Change | Why |
|---|---|---|
| 1 | **§2.5a new — RULING on `trust.campus_mail`: SHIP, with the domain removed.** Approved English: **"Signed in with a college email address."** The **vouching** concern is unfounded — it is a logged mechanical event, not a judgement, and Design's own reading was right. The **disclosure** concern is real: `campuses.email_domains` is a `text[]`, so showing *which* domain leaks student-versus-staff status, department or intake year, **while carrying zero trust value because the campus is already on the listing and in v1 the domain is identical on every listing.** Three conditions, of which the third is an engineering requirement nobody had noticed: **gate the string on `campus_verifications.method = 'EMAIL_DOMAIN'`, not on `users.campus_verified`** — ADR-001 §2.5's staff-assisted recovery path produces verified users who did **not** sign in with a college email, and rendering it for them is a false statement about a person. | `design/COPY-DECK.md` §12 item 1; `design/SYSTEM.md` §7.3a; `design/DIRECTIONS.md` §7.3. Design blocked the best non-vouching trust signal in the product rather than ship on an assumption. **That was the right call and the cost is now released.** |
| 2 | **§4.3.3 new — RULING: a rupee figure in a free-text message does NOT change the s194-O position, and BookHop's copy MAY invite a buyer to name a figure. §12 item 2 is released.** Design's conservative reading was reasonable but over-conservative, and the product was paying a usability cost for a risk that does not exist. **Decisive point: in Circular 20/2021 the e-auctioneer *conducts the auction itself* — a far more active role in price formation than a hint text — and CBDT still held s194-O does not apply.** **I go further than permitting it and recommend it:** copy that *asserts* negotiability is the weakest form of the limb; copy that *causes* negotiation produces evidence. Four conditions — invite a conversation, never capture a number. | `design/COPY-DECK.md` §12 item 2 and §3.1's closing note. Design declined to decide and logged it. |
| 3 | **§4.3.2 gains items 10 and 11.** **Item 10: `contact_pattern_flag`'s regex may never be extended to currency patterns** — a per-message boolean saying an amount was discussed converts the unstructured free text §4.3.3 relies on into a column we can group by, and someone will propose it as a leakage signal. **Item 11: no template may interpolate a campus email domain.** | Conditions of the two rulings, made mechanical. |
| 4 | **§7 rows 6 and 22 amended.** Row 6's purpose extends to the counterparty **disclosure** and must be notified under `listing_publication`; row 22 gains an explicit **never-money** purpose limitation. | Disclosure is a different processing operation from verification. |
| 5 | **§9 Q9's statement of facts CORRECTED.** It asserted to counsel that *"the product says so"* — true of a frozen specification since Design's v1.1, **but not of a built product.** Now says precisely what is specified, what is tested, and what has **not yet been observed in use**, and asks counsel to say if their answer depends on behaviour we have not measured. | Flagged by the coordinator. **Asserting a spec to counsel as a built fact is exactly the error this document warns others against**, and it was mine. |
| 6 | **Threshold U8 recorded as a named compliance instrument** (`design/USER-TEST-PLAN.md` §3.4a Probe P3), with its escalation path endorsed and a **pre-authorised remedy** so Design is not blocked waiting on me a second time. The control of last resort — a listing with **no asking price at all** — is named with its cost and explicitly **not** requested. | Negotiability is a legal limb carried entirely in copy. It needed an instrument and Design built one. |

**Still not legal advice, and neither D-009 nor these rulings changed that.**
See §0. Neither ruling was decided by reference to anyone's schedule, and §2.5a
tightens a constraint (the domain) while releasing a string.

---

### v1.3 — 2026-10-22 · one inventory gap, raised twice, and I am not signing off the proposed shape

Code Review (R-R6) and then the backend developer both raised the same thing:
`review_listings --photos` writes decrypted copies of a student's photographs
onto an operator's filesystem, and §7 had no row for them. Backend fixed the
code half it could fix and correctly refused to write my ruling for me.

| # | Change | Why |
|---|---|---|
| 1 | **§7 row 25 new — moderation working copies of listing photographs.** Backend's suggested retention — *"operator-deleted, no automated clock"* — is **refused**. Retention is **the review session, ceiling 24 hours**, enforced by a sweep. | A retention period that is a person's intention is not a retention period. See the ruling below the table. |
| 2 | **§6.1 gains P15** — the sweep is a **pilot blocker**, and the only one in this document whose subject is photographs of the inside of students' rooms. | Rows 1–24 all have a clock. Row 25 was the only field in the inventory without one. |
| 3 | **`tests/contract/test_the_review_copies_expire.py` added** — two `xfail(strict=True)` conformance tests that cannot pass silently and flip to failure the day the sweep ships. | Rule 9: the row is a claim until a test asserts it. Rule 10: a forward-dated check that merely skips can skip forever. |
| 4 | **Notice finding flagged, not edited** — `erase.*` in `COPY-DECK.md` enumerates what survives deletion and does not enumerate these. Conclusion below: **the copies must go, because the alternative sentence is one no student would accept.** | `tests/e2e/test_deletion.py::test_the_disclosure_does_not_claim_more_is_deleted_than_is` already forces the enumeration to be true. Copy is frontend's; the ruling is mine. |

---

### v1.4 — 2026-10-22 · the want box had no row, and the sentence that counted the boxes was the reason nobody noticed

The backend developer raised `book_requests.free_text_title` and
`book_requests.course_code`: two fields that have been in the schema since S2
with no §7 row, and a sentence in §7 claiming *"there are now two free-text
fields in the system"*. **Both halves of that sentence were wrong.** There were
three free-text columns a student types into, and **neither of the two the
sentence counted exists in the schema yet** — `search_events.query_norm` (row
21) and `support_work_log.note` (row 23) are both specified and unbuilt. The
sentence counted two fields that are not there and missed every field that is.

| # | Change | Why |
|---|---|---|
| 1 | **§7 rows 26 and 27 new** — `book_requests.free_text_title` and `book_requests.course_code`. Basis: **Contract → Consent (s6) under `account`**, and the ruling says why that differs from row 22's refusal. Rows 21 and 23's **truncation** condition **applies and is already breached on one of the two write paths**; their **access-logging** condition is **forward-dated and inverted** rather than asserted. | §7's own standing rule: a field without a row is a compliance defect. A-32 made `free_text_title` carry what the student typed on **every** want, not only the unresolvable ones, and A-32 also renders it back to them — so the box that earned rows 21 and 23 their conditions is now the most-written free-text column in the product. |
| 2 | **§7 row 28 new** — `data_subject_requests.stated_problem`, found by writing the test rather than by being told. A **fourth** student-typed free-text column with no row. It is the one that already has the control the other three lack (`MAX_STATED_PROBLEM = 2000`, with the reason written at the constant). | The charter metric is *"personal-data fields with no stated purpose or retention period"*. Three of four free-text columns in the live schema had no row. |
| 3 | **The count sentence is deleted, not corrected**, and replaced by **§7.1, a `table.column` registry** that `tests/contract/test_the_inventory_covers_the_schema.py` asserts **in both directions** against the live schema. | Rule 11. A hand-maintained count drifted the moment a field was added, and the drift is what hid the gap. A number in prose has no reader that can fail; a registry with a test has one. |
| 4 | **FINDING, and it outranks the rows: the wants survive `erase_account` and the deletion card does not enumerate them.** `_detach_listing_rows` NULLs the FK, keeps `requester_pseudonym`, and **leaves `free_text_title` and `course_code` byte-for-byte**. The eight `erase.retained.*` items name transfers, chat, reports, the email hash, the account, the age check, the audit line and the deletion record. **A want is none of those.** | Identical in shape to row 25's finding four hours earlier, and forced by the same test. Copy is frontend's: **flagged, not written.** |
| 5 | **SECOND FINDING: `book_requests.purge_due_at` is a retention clock that nothing reads.** `retention.purge` walks six tables; `listings.purge_media` walks `listing_photos`. `PURGE_SKIP_LIST` exists precisely so that an omission is *a decision with a reason* — **`book_requests` is on neither side of that split.** And nothing ever sets `status='EXPIRED'`, so an OPEN want that is never withdrawn has `purge_due_at IS NULL`: **no clock at all.** | Rule 12. Writing *"1 year"* into a row whose remedy does not exist would make this document the thing it warns others about. The row states what the system does; **P16** states what it must do. |
| 6 | **§6.1 gains P16** and §11's condition set becomes P1–P16. | A free-text box the student's own words go into, retained for ever, undisclosed, on the main journey of the pilot. |

**Not changed, and worth recording because the obvious reading is wrong.**
`create_request` calls `record_audit(after={"free_text_title": title})`, which
*looks* like a second copy of the typed text in a table §7 leaves untouched by
erasure. It is not: `record_audit` stores `after_hash`, never the payload. The
residual is row 22's shape rather than row 25's — an unsalted hash of a
low-entropy string stays *confirmable* against a candidate title after the row
it described is purged. Noted, not blocked; it adds nothing while the row
survives, which is the actual defect.

---

## 0. Standing disclaimer and how to read this

**This is not legal advice.** I am not a lawyer and cannot give legal sign-off.
This document is a primary-source review that tells you (a) what the rule text
actually says today, (b) where BookHop sits against it, and (c) the exact
questions a qualified Indian lawyer must answer. **A qualified Indian lawyer
must review BookHop's terms, privacy notice, seller arrangements and credit
design before public launch.** Tax positions in §4 additionally require an
Indian chartered accountant or tax counsel.

Where I quote rule text I have read the Gazette PDF itself, not a summary.
Where I could only reach commentary, I say so and the conclusion is weaker.

**Three things changed after the last widely-circulated summaries and are easy
to get wrong. All three are verified below from the Gazette:**

1. The DPDP Act's **operative obligations are not yet in force**. Notice,
   consent, breach notification, data principal rights and penalties commence
   **13 May 2027**. Today the binding privacy law is the IT Act s43A + SPDI
   Rules 2011, plus the CERT-In Directions 2022.
2. The **Consumer Protection (E-Commerce) (Amendment) Rules, 2026** were
   notified 9 Sept 2026 and come into force **1 January 2027**.
3. The **IT Intermediary Amendment Rules, 2026** are already in force
   (20 Feb 2026) and cut the takedown clock from 36 hours to **3 hours** and
   grievance disposal from 15 days to **7 days**.

**Re-verification:** every rule below must be re-checked before G3 (Pilot) and
again before G4 (Public). Two instruments are moving targets and must be
re-checked monthly: the **RBI draft PPI Master Direction 2026** (§3) and any
MeitY notification advancing the DPDP commencement (§1).

---

## 1. DPDP Act 2023 + Digital Personal Data Protection Rules 2025

### 1.1 In-force status — verified from the Gazette, not assumed

**Sources (read in full, not summarised):**
- Commencement notification **G.S.R. 843(E)**, MeitY, 13 November 2025 —
  https://egazette.gov.in/WriteReadData/2025/267647.pdf (accessed 2026-10-21)
- **DPDP Rules 2025, G.S.R. 846(E)**, MeitY, 13 November 2025 —
  https://egazette.gov.in/WriteReadData/2025/267650.pdf (accessed 2026-10-21)
- Corrigendum **G.S.R. 892(E)**, 10 December 2025, Gazette No. 806 of 11 Dec 2025 —
  https://egazette.gov.in/WriteReadData/2025/268455.pdf (accessed 2026-10-21)
- MeitY landing page for the Rules —
  https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa
  (accessed 2026-10-21; returned HTTP 403 to automated fetch, so the Gazette
  PDFs above are the sources of record)

G.S.R. 843(E) appoints commencement in three tranches, quoting the operative words:

| Tranche | Date | DPDP Act provisions | DPDP Rules (r.1(2)–(4)) |
|---|---|---|---|
| Immediate | **13 Nov 2025** | s1(2), s2, ss18–26, s35, ss38–43, s44(1) & (3) | rr.1, 2, 17–21 |
| +1 year | **13 Nov 2026** | s6(9), s27(1)(d) — Consent Managers only | r.4 |
| +18 months | **13 May 2027** | ss3–5, s6(1)–(8) & (10), ss7–10, ss11–17, s27 (except (1)(d)), ss28–34, 36, 37, s44(2) | rr.3, 5–16, 22, 23 |

The corrigendum G.S.R. 892(E) is **typographical only** — its two commencement
items replace "of this Gazette" with "in the Official Gazette" in r.1(3) and
r.1(4). It does not move any date. The Gazette PDFs are dated 13 Nov 2025 on
their face and digitally signed 14 Nov 2025; this is the source of the one-day
discrepancy across commentary. **Compute from 13 November 2025.**

**Status as at 21 October 2026:**
- Everything BookHop would actually have to *do* — notice (s5), consent (s6),
  data fiduciary obligations (s8), children's data (s9), data principal rights
  (ss11–14), and the s33 penalties — is **not in force** and commences
  13 May 2027.
- The Consent Manager provisions commence in roughly three weeks
  (13 Nov 2026). They impose nothing on BookHop (see §1.7).
- I found **no notification amending these dates**. A MeitY proposal to cut the
  18-month tranche to 12 months has circulated in commentary but is not
  notified as of 21 Oct 2026 (searched 2026-10-21; corroborated by
  https://dpdprules.org/blog/dpdp-act-rules-what-is-in-force-2026, last
  reviewed 21 Oct 2026). **Treat 13 May 2027 as current and re-check monthly.**
- The Data Protection Board is constituted on paper but, per commentary citing
  the Union's submission to the Kerala High Court on 7 Oct 2026, is not yet
  functional. I could not verify this from a primary source.

**What binds BookHop *today* instead.** Because s44(2) is in the 18-month
tranche, **IT Act s43A and the SPDI Rules 2011 are still in force** and remain
so until 13 May 2027. Their practical bite on BookHop is small: SPDI r.3
defines "sensitive personal data or information" as passwords, financial
instrument data, health, sexual orientation, biometrics and medical records.
**Name, phone, email, campus affiliation, approximate location, listing photos
and chat are not SPDI** — only the account password is. So the current
statutory privacy floor is thin, and the real near-term obligations are the
CERT-In Directions 2022 (§5.2) and the IT Rules 2021 (§5.1).

> **Do not read "not yet in force" as "do nothing."** Everything in §1 lands on
> 13 May 2027 with no transition period, and retrofitting consent and deletion
> into a live data model is expensive. Build to DPDP now; it costs little at
> this size.

### 1.2 Our role: Data Fiduciary — settled

BookHop determines the purpose and means of processing users' personal data, so
it is a **Data Fiduciary** under s2(i). Any hosting, analytics, SMS/OTP or
moderation vendor is a **Data Processor** under s2(k), and under Rule 6(1)(f)
BookHop must have a contract with each of them requiring reasonable security
safeguards. **Conclusion: Data Fiduciary, no uncertainty.**

### 1.3 Notice and consent (s5, s6, Rule 3 — from 13 May 2027)

Rule 3 requires the notice to:
- (a) be **presented and understandable independently** of any other document.
  A privacy clause buried in the Terms does not satisfy this. It must be its
  own artefact.
- (b) give, in clear and plain language, at minimum **(i) an itemised
  description of the personal data** and **(ii) the specified purpose or
  purposes**, with a specific description of the goods or services enabled.
  "We collect data to improve your experience" fails this twice over.
- (c) give the **communication link** by which the user can (i) withdraw
  consent, "with the ease of doing so being comparable to that with which such
  consent was given", (ii) exercise rights, and (iii) complain to the Board.

The itemisation requirement is why §7 of this document is a per-field
inventory and not a prose paragraph — the inventory *is* the notice content.

**Lawful bases available.** DPDP has only two: consent (s6) and the "certain
legitimate uses" in s7. **There is no general "legitimate interests" ground.**
s7(a) covers data the Data Principal has voluntarily provided for a specified
purpose and has not indicated she does not consent to. The remaining s7 grounds
(State functions, medical emergency, employment, disaster) do not apply to
BookHop. **Practical consequence: BookHop runs on consent for essentially
everything, with s7(a) as a narrow fallback for data a user types in herself
for an obvious purpose.** Design accordingly — no silent repurposing, no
bundled consent.

**Conclusion.** Clear and specific. Requirements are known; nothing is
ambiguous here.
**Uncertainty.** Low. The one open point is whether a single itemised notice
can cover the whole service or whether separate purposes (listing, chat,
handover coordination, safety/moderation) need separable consent. Rule 3's
"specific and informed consent" wording and s6(1)'s limitation of consent to
"the specified purpose" point towards **granular, per-purpose consent**. I
recommend granular from the start.
**Counsel: NO for the rule reading; YES for the final notice text** (see §9 Q1).

### 1.4 Children's data — the adults-only decision is CORRECT, and here is the trap

**The rule.** s9(1) requires verifiable parental consent before processing a
child's personal data; s9(3) prohibits tracking, behavioural monitoring and
targeted advertising directed at children. "Child" = under 18 (s2(f)).
Rule 10(2)(a) defines "adult" as "an individual who has completed the age of
eighteen years."

**What Rule 10 actually governs.** Rule 10 prescribes how to verify a *parent*
when you *do* process a child's data: by (a) reliable identity and age details
already held, or (b) identity and age details voluntarily provided by the
individual or via a virtual token from an authorised entity (including a
DigiLocker service provider). **Rule 10 does not prescribe a method for
verifying that your own users are adults.** There is no prescribed
adult-verification standard for a platform that simply excludes children.

**The hook that lets us age-gate at all.** Fourth Schedule, Part B, item 6
(read with Rule 12(2)) disapplies s9(1) and s9(3) for processing done "for
confirmation by the Data Fiduciary that the Data Principal is not a child and
observance of due diligence under rule 10", **restricted to the extent
necessary for such confirmation**. So BookHop may collect age evidence for the
sole purpose of age-gating, and that collection does not itself trip the
children's-data provisions. It may not be reused for anything else.

**Conclusion: adults-only is the right call, and for a sharper reason than
"it's simpler."** If a single under-18 completes signup, BookHop needs
verifiable parental consent under s9(1) and is barred from behavioural
monitoring and targeted ads to that user under s9(3) — and BookHop's
moderation, trust-scoring and recommendation systems are behavioural monitoring
on any ordinary reading. The cost of children's compliance is not a consent
screen; it is an architectural carve-out in the core product.

**The trap, stated plainly.** A Chennai campus population contains 17-year-olds.
First-year undergraduates are routinely 17 and sometimes 16. **An adults-only
campus marketplace will attract minors, and a tick-box "I am 18+" will not keep
them out.** Treat under-18 signups as a certainty to be engineered against, not
an edge case.

**What "verifiable adult" should mean in practice at pilot** (my
recommendation, not a prescribed standard):
1. Date of birth captured as a **date field, not a checkbox**, with a hard
   client- and server-side block below 18. A checkbox is not evidence; a stored
   DOB plus a server-side rejection is.
2. Campus verification (institutional email + enrolment evidence) as a second
   signal — but note it **proves affiliation, not age**, and must not be relied
   on as an age check.
3. For the pilot only, a **documented human review** of the age declaration at
   onboarding, with the reviewer, timestamp and outcome logged. At 2–3 campuses
   this is affordable and produces the audit trail that a self-declaration does
   not.
4. **Do not collect Aadhaar or any government ID at pilot.** DigiLocker-based
   age tokens (Rule 10(2)(b)/(c)) are the forward path if a stronger check is
   ever needed, because they return an age assertion rather than an identity
   document. Collecting ID scans creates a far larger breach liability than the
   risk it mitigates at this scale.
5. A standing instruction that any user discovered to be under 18 has their
   account suspended and their data erased, with the incident logged.

**Uncertainty: MODERATE, and this is the single least-settled point in §1.**
The Rules prescribe no adult-verification standard, no safe harbour for
good-faith age-gating, and no guidance on what diligence is "reasonable" for a
platform that excludes children. The Board has issued nothing and is not yet
functional. Our position is defensible but untested.
**Counsel: YES** (see §9 Q2).

### 1.5 Security safeguards (Rule 6 — from 13 May 2027) and the one-year log floor

Rule 6(1) sets a **minimum**, and it is specific enough to be a build list:
- (a) encryption, obfuscation, masking, or virtual tokens over personal data;
- (b) access control over the computer resources used;
- (c) **visibility on access to personal data, through logs, monitoring and
  review**, to detect, investigate and remediate unauthorised access;
- (d) continued-processing measures, e.g. backups;
- (e) **retain such logs and personal data for a period of one year** for
  detection, investigation, remediation and continuity, unless another law
  requires otherwise;
- (f) a **contract with every Data Processor** requiring these safeguards;
- (g) technical and organisational measures to make the above effective.

**Rule 6(1)(e) is a one-year retention *floor* on security logs.** It sits
alongside Rule 8(3) (§1.6) and together they mean a user's "delete my account"
cannot hard-delete everything.

### 1.6 Retention and erasure (s8(7), Rule 8 — from 13 May 2027)

**Rule 8(1) + Third Schedule does NOT apply to us.** The three-year
erasure-on-inactivity duty attaches only to an e-commerce entity with **not
less than two crore registered users in India**, an online gaming intermediary
with 50 lakh, or a social media intermediary with two crore. BookHop is
nowhere near, and will not be for the foreseeable future.

**Rule 8(3) DOES apply to us, and it binds every Data Fiduciary regardless of
size.** It requires retention of "such personal data, associated traffic data
and other logs of the processing for a **minimum period of one year** from the
date of such processing" for the Seventh Schedule purposes, after which it must
be erased unless another law requires longer.

The illustration to Rule 8 is, by coincidence, almost exactly our case: a user
buys an e-book on a platform; the platform **"must retain the order details,
personal data, and logs of the processing (such as order confirmation, payment,
and delivery events) for at least one year from the date of the transaction,
even if X deletes her account."**

**Conclusion — this is a hard design constraint, state it to the CTO in these
words:** account deletion must **erase the identity and contact layer** (name,
phone, email, photos, chat content, campus evidence) while **retaining the
transaction record and processing logs for one year**, in a form that is
pseudonymised and not re-identifiable from the retained record alone. A single
`DELETE FROM users` is both a compliance failure and a dispute-evidence
failure. Build deletion as **tombstone-plus-purge**, not as a cascade delete.

Rule 8(2) additionally requires the Data Fiduciary to **warn the Data Principal
at least 48 hours before** erasure under Rule 8(1). Since Rule 8(1) does not
apply to us, this is not a current obligation — but if we ever adopt an
inactivity-erasure policy voluntarily, the 48-hour warning is the pattern to
copy.

**Uncertainty.** Low on the rule, **moderate on the interaction between
Rule 8(3)'s one-year retention floor and s12(3)'s right to erasure.** s12(3)
permits erasure to be refused where retention is necessary for a specified
purpose or for compliance with law; Rule 8(3) is such a law. The honest
position is that a user's erasure request is **partially** satisfiable for
twelve months. That must be said in the notice, not discovered by the user.
**Counsel: YES, narrow** (see §9 Q3).

### 1.7 Breach notification (Rule 7 — from 13 May 2027) — and what binds today

Rule 7 is two separate clocks, and most summaries collapse them:

**To each affected Data Principal (Rule 7(1)) — "without delay".** No hour
figure. Via her user account or a registered communication mode, in concise,
clear and plain language, containing all five of: (a) nature, extent and timing
of the breach; (b) consequences relevant to her; (c) mitigation measures
implemented and being implemented; (d) safety measures she may take; (e)
business contact information of a person who can answer her queries.

**To the Board (Rule 7(2)) — two stages.**
- (a) **"without delay"**: nature, extent, timing, **location** of occurrence,
  and likely impact.
- (b) **within seventy-two hours** of becoming aware (extendable only on a
  written request the Board allows): updated detail, the broad facts and causes,
  mitigation measures, findings on who caused it, remedial measures to prevent
  recurrence, and **a report on the intimations given to affected Data
  Principals**.

**What binds BookHop today, before 13 May 2027.** The CERT-In Directions of
28 April 2022 under IT Act s70B(6) require reporting of specified cyber
incidents to CERT-In **within six hours** of noticing them, and retention of
ICT system logs for a **rolling 180 days within Indian jurisdiction**, with
clocks synchronised to NIC/NPL. This is the operative breach obligation at
pilot. **The six-hour clock is shorter than anything in DPDP** — build the
runbook to six hours and the DPDP timelines are satisfied automatically.
(Sources for CERT-In: secondary commentary only; I could not reach the CERT-In
primary circular on 2026-10-21 — **verify the current text at
https://www.cert-in.org.in before the pilot**, and treat the six-hour figure as
high-confidence but not primary-verified.)

**Conclusion.** Build one runbook with the tightest clock (6h CERT-In), and a
72-hour Board-report template ready for 13 May 2027.
**Uncertainty.** Low on DPDP Rule 7 (read from the Gazette). **Moderate on
CERT-In**, pending primary verification. Also genuinely open: "becoming aware"
is undefined in both instruments, and the moment the clock starts is the thing
that will be litigated. Log detection timestamps.
**Counsel: NO** for the rule; the open question is operational, not legal.

### 1.8 Data Principal rights (ss11–14, Rule 14 — from 13 May 2027)

Rights: access to a summary of personal data and processing activities (s11),
correction, completion and updating (s12(1)–(2)), **erasure** (s12(3)),
grievance redressal (s13), and **nomination** of another individual to exercise
rights on death or incapacity (s14).

Rule 14 requires BookHop to **prominently publish on its website or app**
(a) the means to make a request and (b) any identifier required to identify the
requester under its terms of service, and to operate a grievance redressal
system responding **within a reasonable period not exceeding ninety days**.

> **Note on the ninety-day figure.** The Gazette text of Rule 14(3) is
> syntactically garbled — it reads "shall prominently publish ... within a
> reasonable period not exceeding ninety days under its grievance redressal
> system for responding to the grievances of Data Principals". The corrigendum
> G.S.R. 892(E) does not fix it. The only sensible reading is that **ninety days
> is the outer limit for responding to a grievance**, not for publishing
> anything. I have read the Gazette and am reporting the defect rather than
> tidying it. **Do not plan to ninety days.** It is the statutory ceiling, and
> it is far longer than the IT Rules' 7-day disposal clock (§5.1) and the
> E-Commerce Rules' one-month clock (§2). **The operative number for BookHop is
> 7 days**, because the tightest applicable clock governs.

**Conclusion.** Rights must be self-service in the product, not an email
address. Nomination (s14) is the one right nobody builds and it is in the Act.
**Uncertainty.** Low on substance; noted textual defect in Rule 14(3).
**Counsel: NO.**

### 1.9 Significant Data Fiduciary — we are nowhere near, and there is no number

**There is no numeric threshold.** s10(1) empowers the Central Government to
notify a Data Fiduciary or class of them as Significant, "on the basis of an
assessment of such relevant factors as it may determine", including the volume
and sensitivity of personal data processed, risk to data principals' rights,
potential impact on India's sovereignty and integrity, risk to electoral
democracy, security of the State, and public order. Seventh Schedule item 3
assigns the assessment to a designated MeitY officer. **Designation is by
notification, not by crossing a line.**

If ever designated, Rule 13 would require: a **DPIA and an audit once every
twelve months** with significant observations reported to the Board; due
diligence that algorithmic software does not risk Data Principals' rights; and
**localisation** of personal data and traffic data specified by the Central
Government on a committee's recommendation. s10(2) additionally requires an
India-resident Data Protection Officer who reports to the board of directors.

**Conclusion: BookHop does not approach SDF status and will not at pilot or
early public scale.** No SDF designation has been notified to any entity as of
21 Oct 2026 (searched 2026-10-21; commentary only — no primary notification
found, and absence of a notification cannot be proven from a search).
**Uncertainty.** Low for us, because the factors are qualitative and
scale-driven and we are small. The residual risk is a **class-wide**
designation (e.g. "all e-commerce entities") rather than an entity-specific
one. Re-check before G4.
**Counsel: NO at current scale.**

### 1.10 Consent Managers (s6(9), s27(1)(d), Rule 4, First Schedule — from 13 Nov 2026)

A Consent Manager is a Board-registered intermediary through which a Data
Principal can give, manage, review and withdraw consent. **Registration
requires a company incorporated in India with net worth not less than two crore
rupees** (First Schedule, Part A, item 4), independent certification of an
interoperable platform, and the Part B obligations including seven-year record
retention and a bar on sub-contracting.

**Conclusion: this is not an obligation on BookHop.** A Data Fiduciary is not
required to onboard onto any Consent Manager. s6(7) gives the Data Principal
the *option* to withdraw consent through a Consent Manager; it does not compel
the Data Fiduciary to integrate with one. BookHop is nowhere near the ₹2 crore
net worth and has no reason to become one.
**Uncertainty.** Low, with one watch item: if MeitY later mandates Consent
Manager interoperability for classes of fiduciaries, that is a new instrument,
not a reading of the current one. Nothing of the kind is notified.
**Counsel: NO.**

---

## 2. Consumer Protection (E-Commerce) Rules 2020, as amended 2026

**Sources (both read from the Gazette PDF):**
- Principal rules **G.S.R. 462(E)**, Dept. of Consumer Affairs, 23 July 2020 —
  https://prsindia.org/files/bills_acts/bills_parliament/2021/Consumer%20Protection%20(E-Commerce)%20Rules,%202020.pdf
  (Gazette No. 358 of 23 July 2020; accessed 2026-10-21)
- **Consumer Protection (E-Commerce) (Amendment) Rules, 2026, G.S.R. 789(E)**,
  9 September 2026, **in force 1 January 2027** — Gazette ref.
  CG-DL-E-10092026-276125, https://egazette.gov.in/WriteReadData/2026/276125.pdf
  (accessed 2026-10-21; commencement clause verified by rendering the Gazette
  page, which reads "They shall come into force with effect from 1st January,
  2027")
- Department landing page https://consumeraffairs.nic.in/acts-and-rules/consumer-protection/consumer-protection
  (accessed 2026-10-21; connection refused, so the Gazette PDFs are the sources
  of record)

### 2.1 Is BookHop a "marketplace e-commerce entity"? — Yes

r.3(1)(g): a marketplace e-commerce entity is "an e-commerce entity which
provides an information technology platform on a digital or electronic network
to facilitate transactions between buyers and sellers." That is a description
of BookHop.

r.2(1) applies the Rules to all goods bought or sold over a digital or
electronic network and to **all models of e-commerce, including marketplace**.

**The proviso everyone misreads.** r.2(1) ends: "Provided that these rules
shall not apply to any activity of a **natural person** carried out in a
**personal capacity** not being part of any professional or commercial activity
undertaken on a **regular or systematic basis**."

**That proviso exempts the student seller. It does not exempt BookHop.** The
platform operator is a company carrying on commercial activity systematically;
the proviso has nothing to attach to in our case. Anyone arguing "we're C2C so
the Rules don't apply" has read the proviso backwards.

**Does "no shipping" take us out of scope?** No, or at least not safely.
r.2(1)(a) covers goods "bought or sold over digital or electronic network".
BookHop hosts the listing, the price and the negotiation; only the handover and
the cash are offline. The conservative and correct planning assumption is
**in scope**. A contrary argument exists (the contract is concluded in person)
but it is an argument, not a safe harbour, and it is not worth betting the
pilot on.

**Conclusion: BookHop is both an "e-commerce entity" (r.3(1)(b)) and a
"marketplace e-commerce entity" (r.3(1)(g)). Rules 4 and 5 apply in full.**
**Uncertainty.** Low on status. **Moderate** on whether the no-shipping,
cash-offline model attracts every sub-rule designed for shipped, paid-online
goods — see §2.4.
**Counsel: NO on status; YES on §2.4** (see §9 Q4).

### 2.2 r.4 duties on every e-commerce entity — including an incorporation requirement

**r.4(1)(a) requires the e-commerce entity to be a company incorporated under
the Companies Act 1956 or 2013** (or a qualifying foreign company or FEMA-
resident-controlled office). **A sole proprietorship or an LLP does not satisfy
r.4(1)(a).** If BookHop intends to run a pilot that is in scope of these Rules,
it must be incorporated as a company first. **This is a pilot blocker and it
has a lead time** (name approval, incorporation, PAN/TAN, bank account).

r.4(1)(b): appoint a **nodal person of contact or alternate senior designated
functionary resident in India** for compliance.

r.4(2) (substituted 1 Jan 2027): display prominently **at an appropriate
place** — legal name; principal geographic address of headquarters and all
branches; name and details of the website; contact details including email,
landline and mobile of **both customer care and the grievance officer**. (The
2026 version drops "fax" and adds "at an appropriate place".)

r.4(3): no unfair trade practice.
r.4(4): establish an **adequate grievance redressal mechanism** and appoint a
**grievance officer**, displaying name, contact details and designation.
r.4(5) (substituted 1 Jan 2027): the grievance officer must **acknowledge within
48 hours**, **provide the complainant with a copy of the complaint as recorded
by the grievance officer** (new), and **redress within one month**.
r.4(7) (substituted 1 Jan 2027): **"shall become a partner in the convergence
process of the National Consumer Helpline"** — the 2020 text said "shall
endeavour on a best effort basis". **This becomes mandatory on 1 Jan 2027.**
r.4(8): no cancellation charges on consumers unless the entity bears similar
charges when it cancels unilaterally.
r.4(9): consent for a purchase only by **explicit and affirmative action** —
**no pre-ticked checkboxes**.
r.4(10): refunds to be effected within a reasonable period.
r.4(11): no price manipulation for unreasonable profit; no discrimination
between consumers of the same class; **(c), new 1 Jan 2027: no misleading users
by manipulating search results or search indexes having regard to the user's
search query.**

**New sub-rules from 1 Jan 2027:**
- **(12)** sponsored listings must be **distinctly identified with clear and
  prominent disclosures**.
- **(13)** on any announced price reduction, display the **prior price**,
  defined as **the lowest price of that good in the thirty days before the
  reduction was announced**.
- **(14)** the **seller's name on the invoice in the same font size** as the
  e-commerce entity's name.
- **(15)** comply with the **Guidelines for Prevention and Regulation of Dark
  Patterns, 2023**, conduct a **yearly self-audit**, and **display a certificate
  prominently** confirming the platform is free of dark patterns.

**Direct product consequences, stated for the CTO:**
- Any "was ₹300, now ₹150" UI triggers r.4(13) and requires a 30-day price
  history per listing. **Easiest compliant answer: do not display struck-through
  prices at all.** A used-book marketplace does not need them.
- Any promoted or boosted listing triggers r.4(12). If the pilot has no
  promoted listings, say so and keep it that way.
- r.4(11)(c) means a ranking algorithm must be defensible against the user's
  query. Combined with r.5(3)(f) (below) it means **the ranking parameters must
  be written down before launch, not reverse-engineered afterwards**.
- The dark-patterns self-audit and certificate (r.4(15)) is a **public launch**
  item with a real artefact attached.

### 2.3 r.5 liabilities of a marketplace e-commerce entity

**r.5(1): safe harbour is conditional.** A marketplace seeking exemption from
liability under **IT Act s79(1)** must comply with s79(2) and (3) **including
the IT Intermediary Rules**. This is the hinge that makes §5.1 a consumer-law
obligation too, not just an IT-law one. **Failing the 3-hour takedown clock
costs us safe harbour under both regimes at once.**

**r.5(2): seller undertaking on listing accuracy.** Every marketplace "shall
require sellers **through an undertaking** to ensure that descriptions, images
and other content ... is accurate and corresponds directly with the appearance,
nature, quality, purpose and other general features" of the goods. **This is a
contractual artefact we must actually collect**, not a policy page. For
used-book condition grading this is the operative hook: our condition scale must
be the thing the seller undertakes to.

**r.5(3) disclosures** (clauses (a), (c) and (f) substituted 1 Jan 2027):
- **(a)** seller details: business name whether registered or not, **geographic
  address**, customer care number, website and email where available, rating or
  aggregated feedback, and anything else needed for an informed pre-purchase
  decision. Plus a proviso: on a **written request after purchase**, the
  marketplace must give the buyer the seller's principal geographic address and
  contact details **for effective dispute resolution**.
- **(b)** a **ticket number for every complaint**, trackable by the consumer.
- **(c)** return, refund, exchange, warranty and guarantee, best-before,
  delivery and shipment, payment modes and grievance redressal information.
- **(d)** payment methods, their security, fees, cancellation of regular
  payments, chargeback options, and the payment service provider's contact.
- **(e)** everything the seller provides under r.6(5).
- **(f)** an explanation of the main ranking parameters **in descending order of
  significance**, publicly available, in plain and intelligible language.

**r.5(4):** disclose in seller terms any **differentiated treatment** between
sellers or goods of the same category.
**r.5(5):** take reasonable efforts to **maintain a record identifying repeat
infringers** — sellers who have repeatedly offered goods removed or disabled
under the **Copyright Act 1957**, Trade Marks Act 1999 or IT Act 2000. No duty
to terminate, but the record is mandatory. **This is the compliance artefact
that makes §5.3 workable.**

**New from 1 Jan 2027:**
- **r.5(6):** no using collected information (a) for sale of goods under a brand
  common with the marketplace, or (b) to promote any seller as associated with
  the marketplace, **without express and affirmative consent from the consumers
  whose information it is**. If BookHop ever runs first-party inventory or a
  "BookHop Recommended" badge built from user data, this bites.
- **r.5(7):** no **bundled fees** for services unrelated to the platform, except
  under a loyalty or membership programme.

### 2.4 The genuinely hard part: r.5(3)(a) seller address, and returns for C2C used goods

**Two provisions collide with our model and with DPDP, and I am not going to
paper over it.**

**(i) r.5(3)(a) appears to require publishing a seller's geographic address.**
For BookHop that would mean publishing a student's home or hostel address to
every browsing user. That is unacceptable on safety grounds and sits badly
against DPDP data minimisation.

*The argument that it does not apply:* r.3(1)(k) defines "seller" as "the
product seller as defined in clause (37) of section 2 of the Act", and s2(37)
CPA 2019 requires a person who, **in the course of business**, imports, sells,
distributes or otherwise places the product in the commercial chain. A student
selling her own used textbook once a term is not acting in the course of
business. Read with the r.2(1) proviso, such a person is outside the Rules
entirely, so there is **no "seller"** whose address r.5(3)(a) could require.
The post-purchase proviso is the designed channel for dispute resolution, and
it is a disclosure **on written request to the buyer**, not a public listing.

*Why that argument is not safe on its own:* the obligation in r.5(3) is on the
**marketplace**, and nothing in r.5(3) is expressly conditioned on the seller
being in scope of r.2(1). A regulator could read r.5(3)(a) as a flat platform
duty.

**My position, and the design that follows:**
- Do **not** publish seller addresses. Publish business/display name, campus,
  aggregated rating, and a platform-mediated contact channel.
- Implement the post-purchase proviso as a **reviewed, logged disclosure
  request**, not an automatic reveal: buyer submits a written request, BookHop
  assesses it, discloses only what is necessary for dispute resolution, and logs
  the disclosure. This satisfies the proviso's purpose while keeping the
  disclosure controlled and auditable.
- Implement a **volume threshold** that flips a user from "personal capacity" to
  "business seller": past the threshold, the r.2(1) proviso stops protecting
  them, r.6 duties attach to them, and we must collect and display the fuller
  r.6(5) disclosure set — including **r.6(5)(j) (new 1 Jan 2027): any Central
  Government identification number including GSTIN or MSME registration
  number**. The threshold number is a product decision; the mechanism is a
  compliance requirement. **The CTO should build the flag now even if the
  threshold is set high.**

**(ii) Returns and refunds for C2C used goods.** r.6(3) prohibits a seller on a
marketplace from refusing to take back goods or refund consideration where the
goods are **defective, deficient or spurious, or not of the characteristics or
features as advertised or agreed**. On its face, a student who misdescribes a
book's condition must take it back and refund. r.5(3)(c) requires the
marketplace to display return/refund/exchange information.

- BookHop holds no money (D-004), so BookHop **cannot** process a refund. The
  refund obligation, if it exists, is the seller's.
- At pilot, cash changes hands in person. The practical remedy is a
  **pre-handover inspection** — the buyer sees the book before paying — which
  largely dissolves the "not as described" case before money moves. **Make
  inspect-before-pay an explicit, prominent step in the handover flow.** It is
  the single highest-leverage compliance and trust mechanism available to us,
  and it costs nothing.
- Publish a return/refund policy that states honestly: inspection at handover is
  the remedy; BookHop does not hold funds and cannot refund; misdescription is
  reportable and affects the seller's standing and continued access.

**r.6 duties on sellers** also include, awkwardly, **r.6(4)(b): every seller
must appoint a grievance officer** who acknowledges in 48 hours and redresses in
one month, and **r.6(4)(a): a prior written contract with the e-commerce
entity**. The written contract is satisfiable by accepting seller terms at
listing time and must be logged with version and timestamp. **A student
appointing a grievance officer is absurd on its face** and is the clearest
indicator that r.6 was not drafted with C2C in mind — which is precisely why
the r.2(1) proviso / s2(37) "course of business" reading matters, and why it
needs counsel.

**Conclusion.** BookHop is in scope and must build the r.4 and r.5 artefacts.
The seller-side provisions (r.6, and r.5(3)(a) as it bears on individual
sellers) are **genuinely unsettled** for a C2C used-goods platform.
**Uncertainty: HIGH on §2.4, LOW on §2.1–2.3.** I can tell you with confidence
what BookHop must do; I cannot tell you with confidence what the Rules require
us to demand of a student selling one book. I have found **no notification, no
clarification and no reported decision** addressing C2C used goods under these
Rules.
**Counsel: YES — this is the second-most-important counsel question after
PPI** (see §9 Q4 and Q5).

### 2.5 Country of origin, misdescription and counterfeits

**Country of origin.** r.4(6) (substituted 1 Jan 2027) requires origin
disclosure **where the entity offers imported goods or services for sale**, with
identification per the **Legal Metrology (Packaged Commodities) Rules, 2011**.
r.6(5)(d) (substituted 1 Jan 2027) requires the **seller** to provide country of
origin among pre-purchase details.

**Applicability to us: partial, and it is a real field.** Used books are not
"imported goods offered for sale by the entity" in the r.4(6) sense — BookHop
imports nothing. But r.6(5)(d) attaches to the seller's listing, and imported
editions (international student editions, imported paperbacks) are common in
Indian campus textbook markets. **Pragmatic resolution: capture origin as an
optional listing field pre-populated from the ISBN where derivable, and treat
"not stated" as acceptable for a second-hand private sale.** Note that Legal
Metrology packaged-commodity obligations attach to pre-packaged commodities;
a loose second-hand book is not one. **Uncertainty: moderate.** Counsel: fold
into Q4.

**Liability for misdescribed or counterfeit items.** Three distinct exposures,
which should not be conflated:
1. **Consumer Protection (E-Commerce) Rules:** r.5(2) makes the marketplace
   responsible for *obtaining the seller's accuracy undertaking*, not for the
   accuracy itself. Breach of the Rules is actionable under the CPA 2019 (r.8).
2. **IT Act s79 safe harbour:** available for third-party *information* if the
   IT Rules due diligence is met — and r.5(1) ties the two together. Safe
   harbour protects against liability for the listing. It does not protect
   against a failure to act on notice.
3. **CPA 2019 product liability (Ch. VI) and "deficiency in service":** the
   open question is whether a marketplace is a "product seller" (s2(37)) or a
   "product service provider". A platform that merely hosts is on strong
   ground; a platform that **grades condition, verifies editions, vouches for
   authenticity or brands handovers as "BookHop Verified" moves towards
   vouching**, and r.7(5) (for inventory entities) shows the drafters'
   instinct: whoever vouches for authenticity bears liability for it.

**This is a direct constraint on the product thesis.** BookHop's stated wedge is
"trust plus proximity plus exact-edition matching". **The more we verify, the
more we may own.** That is not a reason to abandon verification — it is a reason
to be deliberate about the *wording*: "seller-stated condition", "ISBN match
confirmed by the seller", **not** "BookHop verified", "guaranteed authentic",
"condition assured".

**Counterfeit/pirated textbooks are the specific high-probability case.** See
§5.3.
**Uncertainty: MODERATE-HIGH on where vouching tips into liability.** No
reported Indian decision I could locate settles it for a marketplace.
**Counsel: YES** (see §9 Q6).

### 2.5a RULING — `trust.campus_mail` · **SHIP, with the domain removed**

**The escalation** (`design/COPY-DECK.md` §12 item 1, `design/SYSTEM.md` §7.3a,
`design/DIRECTIONS.md` §7.3): may a listing show another student
**"Signed in with a @{domain} address."**? Design blocked it in both languages
pending this ruling, recorded the cost rather than softening it, and asked for a
yes/no plus a preferred wording. **v1.1 did not answer it. Design was right to
treat that silence as unanswered rather than as approval, and right not to ship
on an assumption.**

**Ruling: it ships, with changed wording and three conditions. The vouching
concern is unfounded; the disclosure concern is real but narrow and fixable.**

#### Limb 1 — vouching: **PASSES, and not narrowly**

The string describes a **logged mechanical event**: a magic link was sent to an
address at an institutional domain and consumed (ADR-001 §2.5). It makes no
claim about the person's honesty, reliability or the book. Under this section's
own test it is on the hosting side of the line: we are not grading, verifying
authenticity, or branding anything. Under `COPY-DECK.md` §1.2 it is the same
shape as that deck's own passing example *"Priya wrote this 3 days ago"* — a
person who is not us as the grammatical subject, with an **event** as the
predicate rather than a judgement. **"Verified student" would be a judgement.
"Signed in with a college email address" is a thing that happened.**

**Design's own position was correct and I am confirming it rather than
second-guessing it.** It is one word away from "verified student" — but one word
away is where this entire deck lives, and the deck's governing rule is the right
instrument for keeping it there.

#### Limb 2 — disclosure: **this is the real issue, and the coordinator identified it correctly**

It is a fact about **another identifiable person's account, disclosed to a
stranger**. That makes it a data-protection question, not a liability one, and it
needs two things the string as drafted does not have.

**(a) The literal domain must not be rendered.** `campuses.email_domains` is a
`text[]` — a campus may have **several** domains: `student.x.ac.in` versus
`x.ac.in`, per-department domains, or intake-year cohorts. **Showing *which*
domain a seller used can therefore disclose their status (student or staff),
their department, or their year of entry — none of which the seller chose to
publish, and none of which has a purpose in §7.** That is attribute disclosure
smuggled in as a trust badge, and it is not obvious from reading the string.

**And the domain carries no trust value to pay for that risk.** The listing
already shows the campus. In v1 — one campus — the domain is **identical on every
listing**, so it discriminates between nothing. At multi-campus the campus line
already does that work. **It is redundant in the UI and leaky in the data model,
which is the easiest trade in this document.**

**(b) The notice must say this disclosure happens.** §7 row 6 states the purpose
of campus-verification evidence as *"Prove eligibility; prevent impersonation"* —
proving it **to BookHop**. Showing the fact to a counterparty is a **different
processing operation**: disclosure. Under DPDP s5 the notice must state the
personal data and the purpose for which it is processed, so the disclosure has to
be notified before it is lawful. **Row 6 is amended accordingly** (see §7), and
the natural consent home is `listing_publication`, because publishing a listing
necessarily discloses facts about the seller to buyers.

#### The ruling, in the form Design asked for

| | |
|---|---|
| **Ship?** | **Yes.** |
| **Approved English string** | **"Signed in with a college email address."** |
| **`{domain}` interpolation** | **Forbidden.** No part of `campuses.email_domains` may reach any student-facing surface |
| **Wording latitude** | **"college" may be changed to "campus"** for voice consistency with `run.h1` — that is Design's call, not mine. **The compliance content is: the mechanism, named; no domain; no judgement.** Any wording meeting those three holds |
| **Tamil** | Still blocked on the B2 reviewer, as all trust strings are. This ruling unblocks the **English** and the **content**; it does not substitute for TR review |

#### Three conditions, and the third is an engineering requirement nobody has noticed

1. **Never render the domain.** Add to `tests/unit/test_forbidden_copy.py`: no
   template may interpolate `campuses.email_domains` or any element of it, and no
   `.po` string may contain an `@`-prefixed domain literal.
2. **Notify it.** §7 row 6's purpose extends to the disclosure; the privacy
   notice and the `listing_publication` consent text must say that publishing a
   listing shows other students that you signed in with a college email address.
   **One sentence. Without it the disclosure is outside the notified purpose.**
3. **Render it only when it is true.** ADR-001 §2.5 provides a recovery path for
   a student who loses institutional email access: *"a logged staff-assisted
   re-verification."* **Such a user did not sign in with a college email address.
   Rendering the string for them is a false statement about a person** — which
   fails `COPY-DECK.md` §1.2's own "name a fact" test and is precisely the kind
   of quiet untruth that makes a trust signal worthless. **Gate the string on
   `campus_verifications.method = 'EMAIL_DOMAIN'`, not on
   `users.campus_verified`.** Those are two different facts and the UI must not
   conflate them.

**One review point for Design, not a condition.** `trust.not_checked`
("Nothing here is checked by BookHop") and this string may read as contradictory
if they sit adjacent without their scopes being obvious — one is about the book,
the other about the account. **A contradiction in trust copy is worse than
either string alone.** Layout is Design's; I am flagging the adjacency.

**Uncertainty: LOW** on vouching, **LOW** on the disclosure once conditions 1–3
hold. **Counsel: NO** — but the string should be shown to counsel as part of C1's
notice review, because condition 2 changes the notice.

---

## 3. RBI — Prepaid Payment Instruments, and the three credit designs

**Sources:**
- **RBI Master Directions on Prepaid Payment Instruments (MD-PPIs, 2021)**,
  RBI/DPSS/2021-22/82, CO.DPSS.POLC.No.S-479/02.14.006/2021-22, issued
  27 August 2021, **page last updated 30 September 2026** —
  https://www.rbi.org.in/Scripts/NotificationUser.aspx/NotificationUser.aspx?Id=12156
  (accessed 2026-10-21). **This is the instrument currently in force.**
- **Draft Master Direction on Prepaid Payment Instruments, 2026**, released
  22 April 2026, comments closed 22 May 2026 —
  https://www.rbi.org.in/scripts/bs_viewcontent.aspx?Id=4987 ; press release
  No. 2026-2027/124, https://rbi.org.in/scripts/BS_PressReleaseDisplay.aspx?prid=62602
  (both accessed 2026-10-21). **Draft only. Not notified as of 21 Oct 2026**
  (searched 2026-10-21; no finalisation found). It would repeal and replace the
  2021 MD.

### 3.1 What actually makes a stored balance a PPI

**MD-PPI 2021, para 2.8 — definition:** PPIs are "Instruments that facilitate
purchase of goods and services, financial services, remittance facilities, etc.,
against the value stored therein." PPIs requiring RBI approval before issuance
are classified as **Small PPIs** and **Full-KYC PPIs**.

**MD-PPI 2021, para 2.1 — the closed-system carve-out, in full:** Closed System
PPIs are "issued by an entity for facilitating the purchase of goods and
services **from that entity only**" and "do not permit cash withdrawal". "These
instruments **cannot be used for payment or settlement for third party
services**." Their issuance or operation "is not classified as a payment system
requiring approval / authorisation by RBI and are, therefore, not regulated or
supervised by RBI."

**Para 1.3 — applicability:** "The provisions of MD-PPIs shall apply to all
Prepaid Payment Instrument (PPI) Issuers and System Participants."

**The statutory backstop.** The MD is issued under the Payment and Settlement
Systems Act 2007. **s4 PSS Act prohibits any person from operating a payment
system without RBI authorisation.** The closed-system carve-out is the reason a
coffee-shop stored-value card is lawful without a licence. **Falling outside the
carve-out is not a paperwork problem; it is operating an unauthorised payment
system.**

**So the test has three limbs, and all three must hold for the carve-out:**
1. **Issued by the entity for purchases from that entity only.**
2. **No cash withdrawal.**
3. **Not used for payment or settlement for third-party services.**

**Limb 1 and limb 3 are where a marketplace fails.** On BookHop, the book is
supplied by **another user**, not by BookHop. Redeeming a credit for that book
is settlement in favour of a third party. **BookHop can never satisfy "from that
entity only" for a peer-supplied book, because BookHop does not supply the
book.** No naming convention changes that: the carve-out turns on *who supplies
the goods*, and on our own marketplace thesis the answer is "not us".

### 3.2 The regulator's direction of travel — and why it matters now

The **draft 2026 MD** makes the point explicit. **Para 4.1, Explanation (ii):**
"Issuance of a prepaid instrument by an entity, **other than a marketplace**,
only for the purpose of facilitating purchase of goods or services from the
entity itself, is not considered as a payment system, and does not require
authorisation from RBI."

And **para 4.1(d)** defines "Marketplace" as: "An e-commerce entity which
provides an information technology platform on a digital or electronic network
to facilitate transactions between buyer(s) and seller(s)."

**That definition is word-for-word the Consumer Protection Rules' definition of
a marketplace e-commerce entity, which §2.1 concludes BookHop satisfies.** RBI
is proposing to remove marketplaces from the own-goods exemption **by name**.

**Para 4.1(f)** of the draft redefines a PPI as a "Payment instrument in which
**money is loaded** and which facilitates subsequent transactions utilising this
money" — narrower on the loading limb than 2021's "value stored therein", but
the marketplace exclusion in Explanation (ii) is a separate and adverse change.

**Status: draft, not law.** It does not bind. But it is the clearest available
statement of how the regulator reads a marketplace stored balance, and **it
would be reckless to design a credit system on the assumption that RBI will
reverse a position it has just published**.

### 3.3 Classification of the three candidate designs

#### (a) Credits bought with cash — **PPI. Do not build. Blocked.**

**Reasoning against the definitions, not against the label.**
- Money is loaded against the credit, and the credit is thereafter used to
  acquire goods. That is **para 2.8** ("facilitate purchase of goods and
  services ... against the value stored therein") and **draft para 4.1(f)**
  ("money is loaded ... facilitates subsequent transactions utilising this
  money") on any reading. Both limbs satisfied.
- The closed-system carve-out at **para 2.1 fails on limb 1** (the books are
  supplied by other users, not by BookHop) **and on limb 3** (redemption is
  payment or settlement for a third party).
- Under draft para 4.1 Explanation (ii) it fails again and expressly, because
  BookHop is a marketplace within para 4.1(d).
- Therefore it is a PPI requiring authorisation, and issuing it without
  authorisation is operating an unauthorised payment system under **s4 PSS
  Act**.

**It also breaks a decision we have already made.** Selling credit for cash
means holding user money against a future redemption obligation. **That is
custody of funds and a float, which D-004 prohibits outright.** This design is
dead on our own constraints before RBI is reached. There is a further
unexamined exposure: a guaranteed-redemption obligation funded by public money
raises questions under the **Banning of Unregulated Deposit Schemes Act 2019**.
I have not analysed BUDS and am flagging it, not concluding on it.

**Verdict: PPI. Blocked. Not a counsel question — a decision already taken.**

#### (b) Credits earned by giving a book; non-transferable; redeemable only for a book on BookHop — **not clearly a PPI, but NOT within the closed-system carve-out. Counsel required before shipping.**

**Reasoning, limb by limb:**
- **"Money is loaded"** — fails on the draft's narrower definition at para
  4.1(f): no money is loaded, the credit is earned by surrendering a book. This
  is the strongest point in the design's favour, **and it only exists under the
  draft, which is not in force.**
- **"Value stored therein"** — the 2021 definition at para 2.8 is wider and does
  not say "money". A credit that reliably obtains a book has stored value, and
  it facilitates the purchase of goods. **Under the instrument actually in force
  today, this limb is arguable against us.**
- **Closed system, limb 1 ("from that entity only")** — **fails.** The book
  comes from another user. BookHop does not supply it.
- **Closed system, limb 3 ("not for payment or settlement for third party
  services")** — **fails.** Redemption discharges a third-party user's claim.
- **Draft Explanation (ii)** — **fails expressly**, because BookHop is a
  marketplace under para 4.1(d).
- **No cash withdrawal, non-transferable** — satisfied, and these matter: they
  remove the remittance and value-transfer characteristics that make a PPI
  look like money.

**The honest conclusion.** This design is **not plainly a PPI** — nothing is
loaded with money, nothing can be withdrawn, nothing can be transferred — **but
it is also plainly not inside the closed-system carve-out**, and the carve-out
is the only route by which a stored balance escapes authorisation. It sits in a
gap, and RBI has just proposed drafting that gap shut for marketplaces
specifically. **That is not a gap to ship into without counsel.**

**Three design conditions that must hold, or it collapses into (a):**
1. **Never purchasable for money**, directly or as part of any bundle,
   subscription or top-up.
2. **Never transferable, giftable, poolable or assignable** between users.
3. **Never redeemable for money, refundable, or settled in cash** to the
   giving user — including on account closure. If an unredeemed credit can ever
   become cash, it was a stored monetary claim all along.

**A fourth, which is a judgement call and which I recommend:** give credits an
**expiry** and make redemption **discretionary and subject to availability**,
never a guaranteed entitlement to a book. A guaranteed, perpetual,
unit-denominated entitlement looks much more like an instrument than a
time-limited, best-efforts benefit does.

**Verdict: not clearly a PPI; not within the carve-out; COUNSEL REQUIRED BEFORE
SHIPPING.** Consistent with D-003, which already requires exactly this review
before release.

#### (c) Pure non-transferable reputation score, no redemption value — **not a PPI. Ship it.**

**Reasoning:**
- **Not an instrument.** Nothing is issued to the user that can be presented in
  exchange for anything.
- **No stored value.** The score obtains no goods or services. It fails para 2.8
  at the first limb.
- **No payment or settlement**, so para 2.1's third-party concern never arises,
  and the question whether the carve-out applies never has to be answered.
- **Not a payment system** under the PSS Act, so s4 is not engaged.

**Verdict: not a PPI. No RBI issue. No counsel needed.**

**The line that must not be crossed, and this is the whole point of §3:**
design (c) becomes design (b) the moment the score is **denominated and
redeemable**. "Trust level 3" is a reputation. "You have 5 credits; 5 credits
gets you a book" is a balance. **Keep the number ordinal, not exchangeable.**
If product or growth proposes a redemption mechanic on top of a reputation
score, that is a new design requiring a fresh review — not a tweak.

### 3.4 Conclusion, uncertainty and counsel for §3

**Conclusion.** (a) PPI — blocked, and independently barred by D-004.
(b) Not clearly a PPI but outside the closed-system carve-out — counsel before
shipping. (c) Not a PPI — ship.

**Uncertainty: MODERATE for (b), LOW for (a) and (c).** The specific
uncertainties, stated so they are not mistaken for hedging:
- The 2021 MD's "value stored therein" is wider than the draft's "money is
  loaded", and **the wider one is the one in force**. Design (b) is safer under
  the draft than under current law — an uncomfortable position.
- RBI's own position on marketplace closed-loop value has visibly hardened
  between 2021 and the April 2026 draft. The direction of regulatory travel is
  against us.
- I could not find an RBI clarification, FAQ or enforcement action addressing a
  **non-monetary, earned, non-transferable** marketplace credit. The question
  appears genuinely unaddressed.
- **Watch item: if the 2026 MD is notified in anything like its draft form,
  re-run this entire section.** Check monthly at
  https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx

**Counsel: YES for design (b), mandatory before any release** (see §9 Q7).

---

## 4. Tax

**Caveat specific to §4.** The official income-tax and CBIC portals returned
HTTP 403 to automated access on 2026-10-21. Statutory text below is from
reproductions (Indian Kanoon, advocatekhoj) and rates from current commentary.
**Every number in this section must be confirmed with a chartered accountant
before it is relied on.** The *structure* of the analysis is sound; the
*figures* are second-hand.

### 4.1 Is BookHop an e-commerce operator? Yes, under both regimes

- **CGST s2(45):** an "electronic commerce operator" is a person who owns,
  operates or manages a digital or electronic facility or platform for
  electronic commerce.
- **s194-O Explanation (Income-tax Act 1961):** "e-commerce operator means a
  person who owns, operates or manages digital or electronic facility or
  platform" for electronic commerce. "E-commerce participant" is a **person
  resident in India** selling goods or providing services through it.

BookHop satisfies both. **Being an e-commerce operator is a status, not a
trigger.** The obligations below each have their own trigger, and they are not
the same trigger.

### 4.2 GST — TCS under CGST s52 and registration

**s52(1)** (https://www.advocatekhoj.com/library/bareacts/centralgstact/52.php,
accessed 2026-10-21): "every electronic commerce operator ..., not being an
agent, shall collect an amount calculated at such rate not exceeding one per
cent., as may be notified by the Government, of the net value of taxable
supplies made through it by other suppliers **where the consideration with
respect to such supplies is to be collected by the operator**."

**Explanation to s52(1):** "net value of taxable supplies" = aggregate value of
taxable supplies of goods or services (other than s9(5) services) made during a
month **by all registered persons** through the operator, less supplies returned
in that month.

**Rate: 0.5% (0.25% CGST + 0.25% SGST intra-state, or 0.5% IGST), reduced from
1% with effect from 10 July 2024 by Notification 15/2024-Central Tax.**
*Commentary-sourced — confirm with the CA.*
**Compliance if it applies:** pay collected tax within ten days after the end of
the month (s52(3)); monthly statement **GSTR-8 within ten days** after month-end
(s52(4)); annual statement by **31 December** following the financial year
(s52(5)).

**Registration:** **s24(x)** requires compulsory registration, with **no
threshold**, for every e-commerce operator **who is required to collect tax at
source under s52**. **s24(ix)** requires compulsory registration for persons
supplying through an ECO that must collect TCS — relaxed for small goods
suppliers by **Notification 34/2023-Central Tax dated 31 July 2023** (effective
1 Oct 2023, conditional on intra-state supply only, a single state/UT, PAN, and
a validated enrolment number obtained **before the first supply**), and for
service suppliers below ₹20 lakh by **Notification 65/2017-Central Tax dated
15 Nov 2017**. Ordinary threshold under s22(1): **₹40 lakh for goods, ₹20 lakh
for services; Tamil Nadu is not a special-category state, so ₹10 lakh does not
apply.** *All figures commentary-sourced — confirm.*

**Applied to BookHop:**

| | Pilot (cash between users, no fee) | After we collect fees / payments |
|---|---|---|
| Does s52 trigger? | **No.** The operator collects no consideration. The condition in s52(1) is unmet. | **Yes if we collect the sale consideration** (even via a PA/PG settling to the seller). |
| s24(x) compulsory registration? | **No**, because it is conditioned on being required to collect TCS. | **Yes, from the first rupee**, if s52 triggers. |
| GSTR-8? | No. | **Monthly, by the 10th.** |
| BookHop's own GST registration? | Only on ordinary s22(1) grounds — **₹20 lakh aggregate turnover** (services). Not reached at pilot. | As above, unless s24(x) bites first. |
| GST on BookHop's commission | N/A — no fee charged. | **Commission is BookHop's own taxable supply of service — 18%.** This is separate from TCS and is owed regardless of what the sellers' status is. |

**The question that decides it, and which I cannot answer.** s52 collects on
"**net value of taxable supplies** ... by **all registered persons**". A student
selling her own used textbook is almost certainly **not making a supply at all**:
CGST s7 requires the activity to be "in the course or furtherance of business",
and disposing of one's own used possessions is not. If the underlying
transactions are not taxable supplies by registered persons, the net value is
nil, and arguably **BookHop is never "required to collect tax at source" at all**
— which would mean s24(x) never bites either, even after we start collecting
payments. That is a clean argument. It is also exactly the kind of argument that
is clean until the department disagrees. **Counsel/CA question (§9 Q8).**

**Conclusion.** No GST registration or TCS obligation triggers at the pilot as
designed. The trigger is **collecting consideration**, not charging a fee — the
two are commonly confused. A listing fee that does not involve collecting the
sale price does not engage s52; collecting the sale price does, even at zero
commission.
**Uncertainty: MODERATE**, concentrated on whether non-business individual
sellers generate any "taxable supplies" at all.
**Counsel: YES (CA), before any payment collection** (§9 Q8).

### 4.3 Income tax — TDS under s194-O / s393, and the trap in the Explanation

**s194-O(1)** (Income-tax Act 1961, text via
https://indiankanoon.org/doc/72905898/, accessed 2026-10-21): where an
e-commerce operator facilitates the sale of goods or provision of services of an
e-commerce participant through its platform, the operator shall, at the time of
credit of the amount to the participant's account or payment, whichever is
earlier, deduct income-tax on the **gross amount of such sales or services**.

**Current rate: 0.1%, reduced from 1% with effect from 1 October 2024
(Finance (No. 2) Act, 2024).** *Commentary-sourced.* The Indian Kanoon
reproduction still shows the original 1% and is therefore **out of date on the
rate** — I am reporting that discrepancy rather than hiding it.

**Renumbering — this matters for anyone drafting from a template.** The
**Income-tax Act, 2025 came into force on 1 April 2026** and the s194-O
obligation is now at **s393(1), Table Sl. No. 8(v)**; the no-PAN override
formerly at s206AA is at **s394A**. *Commentary-sourced; multiple independent
sources agree on the mapping but differ on the precise table entry for the nil
threshold. **Confirm with the CA.*** The substance below is unchanged by the
renumbering.

**THE TRAP — the Explanation.** "any payment made by a purchaser of goods or
recipient of services **directly** to an e-commerce participant for the sale of
goods or provision of services or both, **facilitated by an e-commerce
operator**, shall be deemed to be the amount credited or paid by the e-commerce
operator to the e-commerce participant."

**Read that against the pilot design.** Cash handed from buyer to seller at a
campus handover, for a sale facilitated by BookHop, is **deemed to be paid by
BookHop**. **"We never touch the money" does not take us out of s194-O.** This
is the single most commonly missed point in Indian marketplace tax, and it is
the opposite of the §4.2 GST answer — the GST trigger turns on who collects, the
income-tax trigger expressly does not.

**The exemption that saves us — s194-O(2).** No deduction where the participant
is an **individual or HUF**, the **gross amount through the platform in the
previous year does not exceed ₹5 lakh**, **and** the participant has **furnished
PAN or Aadhaar to the operator**. Without PAN/Aadhaar, the no-PAN rate applies
(reported as 5%).

**The practical problem, stated bluntly.** To rely on the ₹5 lakh exemption we
must (i) know the participant is a resident individual, (ii) **track the gross
amount per seller per financial year**, and (iii) **hold PAN or Aadhaar**. At
pilot, every student will be far under ₹5 lakh — but the exemption is conditional
on PAN/Aadhaar being furnished, and **collecting PAN or Aadhaar from every
student creates a data-protection liability out of all proportion to the tax at
stake** (0.1% of a ₹150 book is 15 paise). We would also be collecting
financial-identifier data that *is* "sensitive personal data" under SPDI r.3,
pulling the pilot into the SPDI security regime it currently sits outside.

**My position for the pilot:**
- **Do not collect PAN or Aadhaar.**
- **Do not facilitate a priced sale in a way that creates a determinable "gross
  amount" credited by BookHop.** A listing carries an **asking price**; the
  transaction price is agreed and settled between users off-platform and is not
  recorded by BookHop as a settled sale amount. If BookHop records no sale
  consideration, there is no "gross amount of such sales" on which to deduct.
- **Understand that this is an argument, not a safe harbour.** The deeming
  Explanation is drafted precisely to catch direct payments, and a determined
  reading could use the asking price as the gross amount. The counter is that
  BookHop does not know whether a sale occurred or at what price.
- **This must be resolved before any fee or in-app payment.** Once BookHop
  collects or settles money, there is a determinable gross amount, the
  Explanation is not even needed, and the PAN/Aadhaar and tracking obligations
  become unavoidable.

**Conclusion.** Nothing triggers at the pilot **if** BookHop does not record
settled sale amounts; the exposure is real and structural, not theoretical.
**Counsel: YES (tax counsel, not just a CA), before pilot if any price is
recorded, and mandatory before fees** (§9 Q9).

> **v1.0 said "Uncertainty: HIGH — I could find no circular, FAQ or decision
> addressing s194-O for a facilitated offline cash sale on a C2C platform where
> the operator records no consideration." That statement was wrong and §4.3.1
> replaces it.** A targeted re-search on 2026-10-21 found two CBDT circulars
> directly on the point. **Uncertainty is regraded MODERATE.** Recording the
> correction rather than quietly overwriting it, because "I searched and found
> nothing" is a claim this document makes often and it has to be falsifiable.

### 4.3.1 s194-O regraded — the authority exists, and it helps us

**This section answers the CTO's own concern, recorded at ADR-003 §5.3: that
`asking_price_paise` plus `state = 'COMPLETED'` is arguably a determinable gross
amount if a tax officer is willing to read "the asking price of a book that
demonstrably changed hands" as the consideration. It is the right question, it
was correctly graded GREY, and it deserves a better answer than "it is an
argument, not a safe harbour."**

#### Two corrections to our own citations, first

1. **The ₹5 lakh individual/HUF relief is not inside the charging entry.** Under
   the Income-tax Act 2025 it is a separate no-deduction entry at **s393(4)
   Table, Sl. No. 11** — conditioned on the payee being *"an individual or a
   Hindu undivided family"*, gross sales *"during the tax year"* not exceeding
   **₹5,00,000**, **and** the participant having *"furnished the Permanent
   Account Number or Aadhaar number to the e-commerce operator"*. The charging
   entry at **s393(1) Table Sl. No. 8(v)** is confirmed: deductor *"Any
   e-commerce operator"*, rate *"0.1% of gross amount of such sale or services or
   both"*, threshold **Nil**. §4.3 above and
   `INCORPORATION-AND-BLOCKERS.md` §0 both implied the exemption sat inside
   8(v); it does not. **The substance is unchanged — threshold nil, exemption
   conditional on PAN/Aadhaar, therefore unavailable to us by design — but a
   drafter citing 8(v) for the exemption would be citing the wrong provision.**
   (https://indiankanoon.org/doc/30529673/ and
   https://eztax.in/income-tax-act-2025/section-393, both accessed 2026-10-21.)
2. **The deeming provisions migrated into Note 3 to the s393(1) Table**, which
   carries forward the deeming of a direct purchaser-to-participant payment, the
   deeming of the operator as *"the person responsible for paying"*, and a
   precedence clause. **The trap in §4.3 above survives the renumbering intact.**
   Also noted: the 1961 Act is **repealed** w.e.f. 1 April 2026 (Income-tax Act
   2025 s536), so s194-O now governs only pre-April-2026 periods. We have none.

#### The authority that was missing

**CBDT Circular 20/2021, dated 25 November 2021 — e-auction services.** CBDT
held that **s194-O does not apply** where a cumulative set of facts holds. The
findings, in short verbatim fragments: the operator *"is responsible for the
price discovery only which is reported to the client"*; the discovered price
*"is not necessarily the price at which the transaction takes place"*; the
transaction *"takes place directly between the buyer and the seller party
outside the electronic portal"*; *"Payments for the transactions are carried out
directly between the buyer and the seller outside the electronic portal"*; the
operator *"does not have any information about the quantum and the schedule of
payment"*; and *"The e-auctioneer is not responsible for facilitating the
purchase and sale of goods"* beyond price discovery. The circular closes: *"This
clarification shall not apply if any of these facts are not satisfied."*
*(Reproductions: https://www.taxwink.com/blog/tds-on-eauction-services-cbdt-circular-20-2021,
https://www.lkslaw.com/insights/news/guidelines-under-section-194o-194q-and-206c-of-income-tax-act-1961,
both accessed 2026-10-21. **incometaxindia.gov.in returned HTTP 403 and the
official PDF was not reached — this is near-primary, not primary.**)*

**CBDT Circular 17/2020, dated 29 September 2020, para 4.3.** Where an insurance
agent or aggregator *"has no involvement in transactions between insurance
company and the buyer"* in later years, *"he would not be liable to deduct tax
under section 194-O of the Act for those subsequent years"*. **CBDT has
therefore accepted, in a different context, that absence of involvement in the
transaction defeats s194-O even where the platform originated the
relationship.** *(https://abcaus.in/income-tax/cbdt-guidelines-on-applicability-of-tds-us-194-o4-tcs-206c-1h.html,
accessed 2026-10-21.)*

**CBDT Circular 20/2023, dated 28 December 2023 — what "gross amount" means
when it *is* determinable.** It is the full amount the buyer pays: seller-charged
shipping, logistics, packaging and the operator's own commission and convenience
fees *"shall be a part of the gross amount on which tax is required to be
deducted"* (₹100 product + charges = ₹120 → deduct on ₹120). A seller-funded
discount reduces it; an operator-funded discount does not. GST is excluded only
if invoiced separately and deduction is at credit. **Every rule in it starts from
a known invoice value. There is no fallback rule — no "use the listed price", no
best-estimate rule, no deeming of an asking price.** *(Summary:
https://taxmann.com/post/blog/cbdt-releases-guidelines-for-deduction-of-tax-under-section-194-o,
accessed 2026-10-21.)*

**Mjunction Services Ltd. v. Union of India, Calcutta HC, WPO/441/2021,
25 August 2021** (https://indiankanoon.org/doc/103432152/, accessed 2026-10-21).
An e-commerce operator pleaded that *"sale consideration is not received by
MSL"* and that it *"does not have any business relationship with the buyers"*.
The Court directed CBDT to decide its representations and, **interim, that
*"the respondent concerned shall not treat the petitioner in default"***. **The
merits were never decided.** The sequence — a steel e-auction operator, a
six-week direction in August 2021, the e-auction circular in November 2021 —
fits, but no source confirms 20/2021 was the disposal of that representation.

#### Does the construction hold? — Yes, on the better view

**BookHop satisfies Circular 20/2021's facts almost exactly, and by design
rather than by accident:**

| Circular 20/2021 limb | BookHop |
|---|---|
| Platform does price discovery only | Yes — a listing with an asking price (ADR-003 §2.1) |
| Discovered price *"not necessarily the price at which the transaction takes place"* | Yes — **conditional on negotiation being real; see the trap below** |
| Transaction takes place directly between the parties outside the portal | Yes — a physical handover on campus |
| Payment carried out directly between the parties outside the portal | Yes — cash, hand to hand (D-004, ADR-003 §1) |
| Operator has *"no information about the quantum and the schedule of payment"* | Yes — and `transfer_followups` is forbidden from ever asking (DATA-MODEL §5) |
| The client deducts tax on the platform's own fee under another provision | **Not satisfied, and not capable of being satisfied — BookHop charges no fee.** |

**The sixth limb is the only weak one and it is weak in our favour.** It exists
to stop the auctioneer's *own fee income* escaping TDS. A platform with no fee
income has nothing for that limb to govern. But the circular says *"This
clarification shall not apply if any of these facts are not satisfied"*, which
hands a literalist officer a foothold. **My assessment: a condition that exists
to tax a fee cannot sensibly be failed by a platform that charges no fee, and
Circular 17/2020 para 4.3 reaches the same destination without that limb at
all.** Two independent routes to the same place is the reason I am willing to
move this off HIGH.

**The structural point, which is stronger than either circular.** The statute
deems the **payment**, not the **amount**. Note 3 to the s393(1) Table deems a
direct buyer-to-seller payment to be paid by the operator; it does not tell you
its quantum, and no instrument supplies a quantum where the operator does not
know one. Circular 20/2023's entire architecture presupposes an invoice.
**"Gross amount of such sales" presupposes a sale at a known price. BookHop
knows an asking price and a fact that a book moved. Those are two facts, and
neither of them is a price at which anything sold.** No circular, FAQ or
reported decision determines the gross amount for an operator in that position.
**That is a genuine gap, I state it as a negative finding after a real search,
and the gap runs in our favour because the charge cannot be computed.**

#### What breaks it — the three things, ranked

**(1) The negotiation trap, and it is the one nobody has noticed.** Circular
20/2021's second limb needs the asking price to be *"not necessarily the price at
which the transaction takes place"*. **P14's immutable asking price makes the
asking price a *better* proxy for the settled price, not a worse one.** ADR-003
§2.2 chose immutability to prevent reconstructing "the price at the moment of
handover" — correct for one reason, and mildly adverse for this one. If the
product presents an unchangeable asking price, forbids negotiation, or says
anything resembling *"pay the listed price"*, then **"the asking price of a book
that demonstrably changed hands" becomes a very good estimate of the
consideration, and the CTO's worry becomes the right answer.**

> **Instruction to product, design and the CTO — this is the cheapest control
> in the whole s194-O position and it is a copy change, not a schema change.**
> The product must make it visibly true that price is negotiated between the
> parties and that BookHop does not know the outcome. Concretely: the handover
> copy says *"agree the price between yourselves"*; the asking price is labelled
> **"seller's asking price"** everywhere it appears, never "price"; and
> **"pay the listed price", "fixed price", "non-negotiable" and "final price" are
> forbidden strings** in `tests/unit/test_forbidden_copy.py`. The schema cannot
> carry this limb. Only the copy can.

**(2) Any field from which the consideration can be reconstructed.** Not just a
`settled_price` column — see §4.3.1's test requirements below. The single most
likely proposal is a **structured offer/counter-offer amount**, because it is the
obvious next feature and because an accepted offer amount **is** a settled
consideration. It is not on ADR-003 §2.3's deny-list today.

**(3) A fee, a payment integration, or any money through BookHop.** Then the
Explanation is not even needed and §4.4 applies in full. Unchanged.

#### Exposure if the position is wrong

**The tax is trivial; the process is not.** At 30 handovers averaging ₹300 the
0.1% is about ₹9. At 3,000 it is about ₹900. The real cost is **s398 of the 2025
Act** (consolidating the old s201(1)/(1A)): a person required to deduct who
fails *"shall be deemed to be an assessee in default in respect of such tax"*,
plus interest *"at 1% for every month or part of a month"*, plus penalty where
the officer is satisfied the failure was *"without good and sufficient reasons"*,
with an order window of six years. **Nothing in s398 excuses a deductor who
received no money.** Relief routes exist — s398(2) where the payee paid the tax
and an accountant certifies it, and "good and sufficient reasons" — and
prosecution is likely off the table on the reasoning of **US Technologies
International Pvt Ltd v. CIT**, SC, 10 April 2023, which confined the
prosecution provision to failing to remit what was actually deducted
(https://api.sci.gov.in/supremecourt/2010/13647/13647_2010_4_1502_43314_Judgement_10-Apr-2023.pdf,
accessed 2026-10-21). **No court has decided whether an operator that receives
nothing can be an assessee-in-default for the full TDS. The statute reads as
though it can. The only protection anyone has obtained is the interim direction
in Mjunction.**

**So the shape of the risk is: trivial quantum, open law, retrospective reach
across every transfer ever recorded, and a defence that costs more than the
tax.** That is why the mitigation is worth holding absolutely and why the answer
to "can we just store the price?" is no, permanently.

#### A new uncertainty I am introducing, because it is real

All three circulars were issued under **s194-O(4)** and were binding on the
operator under **s194-O(5)**. I could not find a re-enacted equivalent of either
power attached to Sl. No. 8(v) in the 2025 Act. **s536(2)(j) carries forward
circulars made under the 1961 Act "so far as not inconsistent"**, which should
carry 20/2021 across — but if there is no corresponding guidelines power, the
provision under which they are *deemed* issued, and their statutory binding
force on an operator, are both unclear.
*(https://www.taxmann.com/post/blog/carry-over-provisions-under-income-tax-act-2025,
accessed 2026-10-21.)* **I could not resolve this and I am not going to guess.
It goes into §9 Q9 as a sub-question, and it is the reason this is MODERATE and
not LOW.**

#### Is counsel question C11 / Q9 now urgent?

**No — and the reason is precise rather than comfortable.**
`INCORPORATION-AND-BLOCKERS.md` §5 C11 made deferral conditional: *"This can wait
until Gate B if and only if P14 is enforced in the schema."* **The CTO has done
exactly that**, with a DB trigger, a CI deny-list test and an instruction that a
diff to that test is a founder escalation. The condition is met. And the new
authority makes the interim position **stronger** than when C11 was drafted, not
weaker — which is a reason to defer, not to accelerate.

**Three changes to C11's status, all of them real:**

1. **It moves from "deferrable" to "scheduled at Gate B, bundled."** By Gate B
   the founder is paying counsel for C1 and C3 anyway. **Add a tax-counsel limb
   to that engagement rather than buying C11 separately later.** Asking a
   drafted, narrow question alongside work already commissioned is the cheapest
   it will ever be.
2. **The question is re-drafted** (§9 Q9) to ask whether Circular 20/2021's
   e-auction clarification applies to BookHop's facts, and whether it survives
   the 2025 Act with binding force. **A yes/no on a named circular is far cheaper
   and far more useful than an open-ended "does s194-O catch us".**
3. **The tripwire stays, and gains three triggers.** C11 becomes urgent **that
   day** if anyone proposes (a) storing any settled, agreed, offered or accepted
   amount; (b) a fee, payment integration or any money through BookHop; or
   (c) **copy or UX that presents the asking price as the transaction price** —
   trigger (c) is new and comes from the negotiation trap above.

**Uncertainty: MODERATE.** Two near-primary circulars support us, the structural
argument is sound, no decision tests it, one of our three supports has an
unresolved binding-force question, and the whole position rests on a schema
constraint and a copy constraint both holding indefinitely.
**Counsel: YES — tax counsel, at Gate B, inside the C1–C3 engagement.**

### 4.3.2 What `tests/unit/test_forbidden_schema.py` must forbid

**ADR-003 §5.2 asked for this explicitly: "the counsel C11 tripwire is now
mechanical", and asked what the test must forbid for my position to hold. Here
it is. Nine requirements. ADR-003 §2.3's existing deny-list covers items 1–2 and
nothing else, so seven of these are additions.**

**My s194-O position in §4.3.1 does not hold without items 3, 4 and 9.** Items 3
and 4 close the reconstruction routes the statute's deeming provision needs;
item 9 is the negotiation limb of Circular 20/2021, which lives in copy and
cannot be carried by a schema test at all. I am saying which are load-bearing so
the CTO can prioritise rather than treat nine items as equal.

| # | Requirement | Why, tied to a limb of the argument |
|---|---|---|
| 1 | **Keep every pattern in ADR-003 §2.3 as it stands.** Nothing in this section relaxes anything. | They are correct. |
| 2 | **Keep the trigger test and the API-response-schema test.** | A price absent from storage but present in a response is still a record. |
| 3 | **Invert the money rule from a blacklist into a whitelist.** Assert that `listings.asking_price_paise` is the **only** column in the entire database carrying a monetary quantity — by asserting that no other column matches a money-ish name pattern **or** sits on a table that has no business holding money. A blacklist is defeated the first time a developer writes `transfers.value_x integer`. **A whitelist is less code and strictly stronger.** | §4.3.1's structural argument: the operator must know no amount. One column is auditable; a pattern list is not. |
| 4 | **Forbid offer, bid and negotiation amounts by name:** `%offer%amount%`, `%offered_price%`, `%counter%price%`, `%bid%`, `%negotiat%`, `%accepted_price%`, `%deal%`. | **An accepted offer amount IS a settled consideration.** This is the most likely next feature request and it is not on the deny-list today. |
| 5 | **Forbid price history in any shape:** `%price_history%`, `%price_change%`, `%previous_price%`, `%old_price%`, `%price_at%` — **and structurally assert there is no `(listing_id, price, valid_from)`-shaped child table of `listings`.** | ADR-003 §2.2 argues this in prose and the test does not check it. Reconstructing "the price at the moment of handover" is reconstructing a settled price. |
| 6 | **Forbid price-derivation fields:** `%discount%`, `%rebate%`, `%cashback%`, `%coupon%`, `%voucher%`, `%refund%`, `%adjust%amount%`. | Circular 20/2023's gross-amount arithmetic is built out of exactly these. A discount column is a price-derivation column. |
| 7 | **Forbid charge components:** `%shipping%`, `%delivery%charge%`, `%packaging%`, `%convenience%fee%`, `%commission%`, and `%fee%` **except** the two names ADR-003 §3 pre-authorises — `fee_asked_paise` and `fee_paid` — and **assert `fee_paid` is `boolean`, never numeric**, if either ever exists. | Circular 20/2023: these charges *"shall be a part of the gross amount"*. A charge column is a gross-amount component. ADR-003 §3 already specified the only permissible shape; the test should enforce it in advance. |
| 8 | **Freeze the full column list of the four transaction tables** — `transfers`, `transfer_events`, `messages`, `transfer_followups` — against an expected list, so **any** new column on them fails the build until the expected list is edited in the same commit. **And assert the two `transfer_followups` CHECK constraints by value set:** `question_key IN ('STILL_HAVE_BOOK','DID_YOU_GET_BOOK')` and `answer IN ('YES','NO','NO_REPLY')`. | A frozen column list beats any pattern list and is less code. The follow-up is where a money question would be most natural — *"did you pay?"* — and DATA-MODEL §5 promises *"no question about money, ever"*. **Promise it in the test. Widening an enum is the quietest way to break P14.** |
| 9 | **Extend `tests/unit/test_forbidden_copy.py`** to forbid, in every template and `.po` file: `"pay the listed price"`, `"fixed price"`, `"non-negotiable"`, `"final price"`, and the bare label `"Price"` for `asking_price_paise` where `"Asking price"` / `"Seller's asking price"` is required. **And require the metric label:** wherever **Book value moved** is rendered or exported it must carry *"sum of asking prices of books that changed hands — not a sale value and not revenue"*. | §4.3.1's negotiation trap. **And a point that matters more than it looks: the document a tax officer would actually read is the metrics export, not the schema.** A report headed "value of books sold" that sums asking prices over completed transfers is, in substance, BookHop asserting those books sold for those amounts. **`design/COPY-DECK.md` §1.6 rule 1 and §3.1 already implement this; the test makes it permanent.** |
| 10 | **Never extend `messages.contact_pattern_flag`'s regex to currency patterns** (`₹`, `Rs`, `INR`, `\d+/-`). Assert the pattern set in the test, not just the column | §4.3.3 condition 2. A per-message boolean saying "an amount was discussed" is a **structured, queryable signal about consideration** — it converts the unstructured free text that §4.3.3 relies on into a column we can group by. Row 22's purpose is contact-sharing and safety, never money |
| 11 | **No template may interpolate `campuses.email_domains` or any element of it, and no `.po` string may contain an `@`-prefixed domain literal** | §2.5a condition 1. A multi-domain campus leaks student-versus-staff status, department or intake year through a trust badge. Not a tax item — included here because this is the file that holds the copy assertions |

**One thing the test must NOT do.** It must not forbid `transfers.completed_at`,
`seller_confirmed_at` or `buyer_confirmed_at`. Not recording completion is the
only materially stronger s194-O position available, and it would destroy every
metric in `METRICS.md`, the institutional-payer thesis, and D-009's entire
measurement mitigation. **ADR-003 §5.3's recommendation — keep completion, keep
the asking price, buy C11 — is the right trade and I endorse it.** The
completion record is worth more than the marginal tax argument it costs.

**And one process point.** ADR-003 §2.3 says a change to this file requires a new
ADR plus privacy-compliance sign-off in the same commit. **Confirmed, and I am
adding a condition: a diff that widens a CHECK constraint or adds a column to one
of the four frozen tables is the same event as a diff to the deny-list, and
carries the same escalation.** Enum widening and column addition are how this
constraint will actually be broken, not by someone naming a column
`settled_price`.

### 4.3.3 RULING — may BookHop's copy invite a buyer to name a figure? · **Yes, and I recommend it**

**The escalation** (`design/COPY-DECK.md` §12 item 2 and §3.1's closing note):
Design declined to add a prompt inviting a buyer to state a number, reasoning
that *"a rupee figure typed into a stored message body is closer to a
reconstructable consideration than anything else in the product"* and that
§4.3.1 trap (2) is about reconstruction. Its strings point at the thread without
eliciting a figure. It asked two questions and logged the second as the one it
could not answer.

**Answering the direct question first, plainly, because the product is paying a
usability cost for it: a student-authored rupee figure in a free-text message
does NOT change my s194-O position. Not at the margin, not at all. Design's
conservative reading is reasonable but over-conservative, and the constraint is
released.**

#### (a) Is a student-authored figure in a message a problem? **No.**

Four reasons, in descending strength:

1. **A figure in a thread is a negotiating position, not a consideration.** It
   may be accepted, refused, ignored, superseded by nine later figures, or
   contradicted by whatever the two of them actually say to each other at the
   handover. **Nothing in the system links any figure to the outcome**, because
   there is no field in which acceptance of an *amount* can be recorded —
   `POST /offers` carries no amount, `transfers` has no money column, and
   `offer.accept` accepts **a buyer**, not a price.
2. **"Gross amount of such sales" presupposes a known consideration.** Circular
   20/2023's entire architecture starts from an invoice value and supplies no
   fallback measure. **A chat log of haggling is not an invoice and cannot be
   made into one.** An officer could read threads one by one and *construct* an
   estimate; that is materially different from a determinable amount, and the
   construction would be incomplete and unreliable by its nature.
3. **It is affirmative evidence for the limb we are weakest on.** Circular
   20/2021 needs the asking price to be *"not necessarily the price at which the
   transaction takes place"* and the operator to have *"no information about the
   quantum and the schedule of payment"*. **Unresolved, unstructured, unlinked
   candidate numbers are not information about the quantum — they are evidence
   that the quantum was settled somewhere we cannot see.** A thread full of
   haggling makes limb 2 *true* in a way a disclaimer never can.
4. **The risk exists either way.** Students will discuss price in messages
   whatever our copy says, and `offer.message.hint` already says *"Or ask about
   the price."* The marginal effect of a prompt is the **density** of figures in
   threads, not the existence of the mechanism.

#### (b) Does it become a problem because BookHop's copy invited it? **No — and this is the only part of the question that is actually about BookHop.**

What would hurt us is BookHop **recording or structuring** a consideration. It is
not BookHop **encouraging two people to negotiate**. There is no doctrine under
which inviting negotiation makes the operator more involved in the price; if
anything it is evidence the operator is not setting it.

**The decisive comparison, and it is directly on point.** In Circular 20/2021 the
e-auctioneer **conducts the auction itself** — it runs the entire price-discovery
process, which is a far more active role in price formation than a hint text —
and **CBDT still held s194-O does not apply**, because the transaction and the
payment happened outside the portal and the auctioneer did not know the quantum.
**If running an auction does not attract the charge, a sentence saying "you can
discuss the price with the seller" certainly does not.**

#### The ruling

| | |
|---|---|
| **Does a rupee figure in `messages.body` change the s194-O position?** | **No.** |
| **May BookHop's copy invite a buyer to name a figure?** | **Yes.** |
| **Do I require it?** | **No — but I recommend it**, for the reason below |
| **Is §12 item 2 released?** | **Yes.** Design may proceed without a further ruling |

**Why I recommend it rather than merely permitting it — this is the part that
reverses Design's instinct and it is the useful half of this ruling.** The
negotiability limb is carried entirely in copy, and **copy that asserts
negotiability is the weakest possible form of it.** Copy that *causes* negotiation
produces evidence. A student who has typed a number into a thread has personally
experienced that the price is not fixed; a student who has read a disclaimer has
not. **The strongest available version of "negotiability is real" is a corpus of
threads in which it demonstrably happened** — and that is also the version that
would survive being shown to a tax officer, which a disclaimer would not.
Design's §3.1 note already identifies `price.seller.hint` as *"where
negotiability becomes real rather than stated"* for the seller side. **This is
the same insight applied to the buyer side, and Design stopped one step short of
it for a risk that does not exist.**

#### Four conditions — the line is: invite a conversation, never capture a number

1. **No structured capture, ever.** No numeric input, no amount field, no parsing
   or extraction of figures out of `messages.body` into any column, no "detected
   price" annotation, no analytics or aggregate over amounts mentioned in
   messages. **This is the actual boundary.** §4.3.2 item 8 already enforces it by
   freezing the column list of `messages`; **I am recording here that it is
   load-bearing for this ruling too**, so nobody relaxes it thinking it only
   served a different argument.
2. **`contact_pattern_flag` must never be extended to currency patterns.** Row 22
   exists for phone, email and UPI-handle patterns, for contact-sharing and
   safety. **Someone will propose adding `₹\d+` to the regex as a leakage
   signal. That is forbidden**: it would create a derived, queryable, per-message
   indicator that an amount was discussed, which is a structured signal about
   consideration and converts exactly the unstructured free text this ruling
   relies on into a column we can group by. **Add it to the deny-list reasoning
   and to row 22's purpose limitation.**
3. **`price.not_recorded` must appear in the same view as any such prompt.** If
   we invite the figure, the same screen says we do not know or record what was
   paid. Inviting without that sentence is the one version of this I would not
   sign off.
4. **The prompt addresses the counterparty, never BookHop.** *"What would you
   pay?"* reads as BookHop collecting an answer. The permitted shape addresses
   the seller. A compliance-safe option, offered for Design to do the craft on:
   **"For example: is the CD still inside? Or tell {name} what you'd be willing
   to pay."** Any wording that invites the student to say a figure **to the
   seller** holds.

#### Pre-authorised remedy if threshold U8 fires

`design/USER-TEST-PLAN.md` §3.4a Probe P3 and threshold **U8** — *"≥3 of 8 code
N2 on Probe P3"*, i.e. the asking price reads as *the* price — exist because
negotiability is a legal limb asserted to counsel with nothing behind it but
copy. **I endorse that instrument and its escalation path**: it comes to
privacy-compliance and ceo-planning as a compliance finding before Design
iterates, on the grounds that we may want a stronger control than copy. That is
correct, and it is recorded here as a named compliance instrument rather than a
design nit.

**To save a round trip: if U8 fires, the buyer-side figure prompt above is the
PRE-AUTHORISED first remedy, together with `price.seller.hint` at intake.
Design may implement both without a fresh ruling from me.**

**And the control that exists if copy fails twice, named with its cost rather
than recommended.** `listings.asking_price_paise` is `NOT NULL` today. **A
listing with no asking price at all cannot be a determinable gross amount on any
reading** — it is the strongest control available and it does not depend on copy,
behaviour or a user test. It costs the price filter
(`API-CONTRACT.md` §5.3), a large amount of buyer utility, and probably
liquidity. **I am not asking for it now.** It is the escalation of last resort,
it would be a P14 amendment and an ADR, and it should be on the record so that if
copy fails repeatedly nobody concludes the only remaining option is to start
recording prices — **the available move is to record fewer, not more.**

**Uncertainty: LOW** that a free-text figure is harmless; **LOW** that inviting
one is harmless; **MODERATE** on the underlying s194-O position itself, which
§4.3.1 grades and this ruling does not change. **Counsel: covered by the existing
Q9** — no new question.

### 4.4 What changes the moment we charge a fee

In order of when it bites:
1. **BookHop's commission is its own taxable supply of services at 18% GST.**
   Register under s22(1) at ₹20 lakh aggregate turnover, or immediately if
   s24(x) is triggered.
2. **If we collect the sale consideration**, s52 TCS at 0.5% engages (subject to
   §4.2's open question), s24(x) forces registration from the first rupee, and
   GSTR-8 is due monthly by the 10th.
3. **s194-O / s393 becomes unavoidable**: determinable gross amounts, per-seller
   annual tracking, PAN/Aadhaar collection, quarterly TDS returns, certificates.
4. **r.5(3)(d) of the E-Commerce Rules** then requires disclosure of payment
   methods, their security, fees, chargeback options and the payment service
   provider's contact details.
5. **Income tax on BookHop's own revenue**, plus TDS as a deductor on its own
   vendor payments. Out of scope here; Finance owns it.

**Recommendation: the fee decision is a tax-compliance decision with a lead
time, not a pricing decision.** Involve the CA at least one quarter before
switching fees on.

---

## 5. Other exposures

### 5.1 IT Act s79 safe harbour and the IT Rules 2021 as amended in 2026

**Sources:**
- IT (Intermediary Guidelines and Digital Media Ethics Code) Rules 2021,
  **G.S.R. 139(E)**, 25 February 2021, amended by G.S.R. 794(E) (28 Oct 2022),
  G.S.R. 275(E) (6 Apr 2023), G.S.R. 775(E) (22 Oct 2025) and —
- **IT (Intermediary Guidelines and Digital Media Ethics Code) Amendment Rules,
  2026, G.S.R. 120(E), 10 February 2026, IN FORCE 20 FEBRUARY 2026** — text read
  in full from https://www.livelaw.in/pdf_upload/2026/02/10/it-rules-2026-amendment-655195.pdf
  (accessed 2026-10-21; this is a reproduction of the Gazette notification —
  **re-verify against the eGazette before the pilot**).

**BookHop is an "intermediary"** under IT Act s2(1)(w): it receives, stores and
transmits listings and messages on behalf of users. s79(1) gives it safe harbour
for third-party information, **conditional** on s79(2)–(3) and on the Rules'
due diligence — and **r.5(1) of the E-Commerce Rules ties that condition into
consumer law as well** (§2.3). Losing it costs us twice.

**Current obligations on an ordinary intermediary (BookHop is not a significant
social media intermediary — that threshold is 50 lakh registered users):**

| Obligation | Rule | Clock |
|---|---|---|
| Publish rules & regulations, privacy policy, user agreement | 3(1)(a) | standing |
| Inform users of prohibited content categories | 3(1)(b) | standing |
| **Inform users at least once every three months** of termination rights, user liability, and mandatory-reporting consequences | **3(1)(c), substituted 2026** | **quarterly** |
| Remove/disable access on a court order or government notification | **3(1)(d)** | **3 hours** (was 36) |
| Appoint a Grievance Officer; publish name and contact | 3(2)(a) | standing |
| Acknowledge a complaint | 3(2)(a)(i) | **24 hours** (unchanged) |
| **Dispose of a complaint** | **3(2)(a)(i)** | **7 days** (was 15) |
| First proviso to 3(2)(a)(i) | **3(2)(a)(i)** | **36 hours** (was 72) |
| **Remove non-consensual intimate imagery / impersonation content on complaint** | **3(2)(b)** | **2 hours** (was 24) |
| Retain information for 180 days after withdrawal/removal of registration | 3(1)(h) | 180 days |
| Preserve removed information for 180 days for investigation | 3(1)(j) | 180 days |

**The 3-hour and 2-hour clocks mean BookHop needs a staffed, round-the-clock
escalation path from day one of the pilot.** A grievance officer who reads email
on weekday mornings cannot meet a 2-hour clock. At pilot scale the honest
solution is a monitored channel with an on-call rota, not a 24/7 team — but it
must be **designed and rostered**, not assumed.

**Synthetically generated information — the forward-looking warning.** The 2026
amendment inserts **r.3(3)**, which applies where "an intermediary offers a
computer resource which may enable, permit, or facilitate the creation,
generation, modification, alteration, publication, transmission, sharing, or
dissemination of information as synthetically generated information". Such an
intermediary must deploy technical measures to block unlawful SGI and must
**prominently label** all other SGI and **embed permanent metadata or provenance
including a unique identifier**, and must not allow that label or metadata to be
removed.

**As designed, BookHop does not offer such a resource, so r.3(3) does not apply.**
Two things would change that, and both are plausible product ideas:
- **AI-generated listing photos or cover images** → r.3(3) applies in full.
- **AI-written listing descriptions** → arguably "synthetically generated
  information" only in respect of audio/visual content; r.2(1)(wa) defines SGI as
  **"audio, visual or audio-visual information"**, so text-only generation
  appears to fall outside the definition. *This is my reading; it is not
  settled.*
- **Plain photo enhancement is expressly carved out**: the proviso to r.2(1)(wa)
  excludes "routine or good-faith editing, formatting, enhancement, technical
  correction, colour adjustment, noise reduction, transcription, or compression
  that does not materially alter, distort, or misrepresent the substance,
  context, or meaning" of the underlying content. **Auto-cropping, brightening
  and denoising a listing photo is safe. Generating a book cover is not.**

**CTO instruction: any proposal to add generative AI to listing creation is a
compliance change, not a feature. Route it back to this review.**

Also note r.2(1B), inserted 2026: removing or disabling content in compliance
with these Rules, **including by automated tools**, does not itself breach the
s79(2)(a)/(b) conditions. This is helpful — it gives cover for proactive
moderation, which previously risked being characterised as editorial control
that forfeits safe harbour.

**Conclusion.** BookHop is an intermediary, the obligations are specific and
short-fused, and they are in force today.
**Uncertainty: LOW on the obligations** (read from the notification text).
**Moderate** on whether the 2026 amendment survives challenge — commentary
anticipates constitutional challenges to the 3-hour clock, and I found no
ruling. **Plan on compliance; a challenge is not a defence.**
**Counsel: NO on the obligations; the Grievance Officer appointment and the
published policies need legal drafting (§9 Q1).**

### 5.2 CERT-In Directions, 28 April 2022 — **now primary-verified in full**

**Source, read as extracted text from the PDF itself, not from commentary:**
No. 20(3)/2022-CERT-In, MeitY, Indian Computer Emergency Response Team,
Electronics Niketan, dated **28 April 2022**, *"Directions under sub-section (6)
of section 70B of the Information Technology Act, 2000 relating to information
security practices, procedure, prevention, response and reporting of cyber
incidents for Safe & Trusted Internet"* —
https://www.cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf
(accessed **2026-10-21**).

The three directions that bind BookHop, verbatim:

- **Direction (i) — clocks.** *"All service providers, intermediaries, data
  centres, body corporate and Government organisations shall connect to the
  Network Time Protocol (NTP) Server of National Informatics Centre (NIC) or
  National Physical Laboratory (NPL) or with NTP servers traceable to these NTP
  servers, for synchronisation of all their ICT systems clocks."*
- **Direction (ii) — six hours.** *"shall mandatorily report cyber incidents as
  mentioned in Annexure I to CERT-In within 6 hours of noticing such incidents
  or being brought to notice about such incidents"*, to
  `incident@cert-in.org.in`, 1800-11-4949, or fax 1800-11-6969.
- **Direction (iv) — logs.** *"shall mandatorily enable logs of all their ICT
  systems and maintain them securely for a rolling period of 180 days and the
  same shall be maintained within the Indian jurisdiction. These should be
  provided to CERT-In along with reporting of any incident or when ordered /
  directed by CERT-In."*

**In force:** *"This direction will become effective after 60 days from the date
on which it is issued"* → **27 June 2022**. Non-compliance *"may invite punitive
action under sub-section (7) of the section 70B of the IT Act, 2000 and other
laws as applicable."*

**This is the operative breach obligation at pilot**, since DPDP's Rule 7 does
not commence until 13 May 2027. Build the runbook to six hours.

**Direction (v) does not apply to BookHop.** It obliges *Data Centres, VPS
providers, Cloud Service providers and VPN Service providers* to register
subscriber details for five years. BookHop is a subscriber of such a provider,
not one of them. **Recorded as a negative finding so that nobody later builds a
five-year subscriber register we do not owe.** The flip side: whichever provider
BookHop rents from holds BookHop's own subscriber details for five years. That
is a fact, not a problem.

**Retention: plan on one year, not 180 days.** DPDP r.6(1)(e) (security logs)
and r.8(3) (personal data, traffic data and processing logs) each set a one-year
floor from 13 May 2027, and the longest applicable period governs. INFRA.md
§2.2 already does this.

**Uncertainty: LOW. Primary-verified. Counsel: NO.** Discharges the CERT-In
limb of P13.

### 5.2.1 "Within the Indian jurisdiction" — the CTO's question, answered

**The question routed to me (ADR-001 §5, §7.2; INFRA.md §2):** does a single
Linux VM in an Indian *region* of a **foreign-owned** cloud provider satisfy
Direction (iv)'s requirement that logs be *"maintained within the Indian
jurisdiction"*, when the provider is subject to foreign legal process? The CTO
graded its own reading MODERATE and deployed nothing pending my answer.

**Answer: YES. The CTO's reading is confirmed. Uncertainty: LOW.** I am saying
this without hedging because the charter warns that hedging everything is as
useless as hedging nothing, and because this one is not close.

**There are two independent reasons, and we win on either.**

**Reason 1 — the strict reading, which is the one we do not need any
clarification for.** On the strictest possible construction of Direction (iv),
the 180-day rolling log must sit physically inside India. ADR-001 §2.7 and
INFRA.md §2.2 put structured application logs, nginx logs, Postgres logs and the
journal on the local filesystem of a VM in an Indian region. **The bytes are in
India.** BookHop — an Indian-incorporated company from Gate B — enables them,
maintains them, and can produce them on requisition. Direction (iv)'s own
closing sentence states its purpose: *"These should be provided to CERT-In along
with reporting of any incident or when ordered / directed by CERT-In."*
**Direction (iv) is a retention-and-producibility obligation, not a sovereignty
or exclusivity obligation, and nothing in it mentions the ownership,
incorporation or nationality of the infrastructure supplier.**

**Reason 2 — CERT-In has stated the position, and it is more permissive than
the strict reading.** From *"FAQs on Cyber Security Directions of 28.04.2022"*,
CERT-In, **May 2022**,
https://www.cert-in.org.in/PDF/FAQs_on_CyberSecurityDirections_May2022.pdf
(accessed **2026-10-21**; extracted from the PDF, not read from commentary):

> **Q 35. Is it required to store copy of logs in India only?**
> **Ans.:** *"The logs may be stored outside India also as long as the
> obligation to produce logs to CERT-In is adhered to by the entities in a
> reasonable time."*

The issuing authority's own reading is therefore that **log location is
subordinate to producibility.** If logs may lawfully sit *entirely outside*
India subject to producibility, then logs sitting *inside* India on a
foreign-owned provider's hardware cannot possibly fail.

**On the specific worry — does provider ownership, incorporation, or exposure
to foreign lawful access bear on Direction (iv)? No, and here is what CERT-In
has actually said about nationality:**

> **Q 26. Do the Cyber Security Directions of 28.04.2022 apply only to Indian
> companies or also to foreign firms that serve Indian customers?**
> **Ans.:** *"These Cyber Security Directions of 28.04.2022 are applicable to any
> entity whatsoever, in the matter of cyber incidents and cyber security
> incidents."*

Nationality appears in the FAQ **only to widen who is bound, never to narrow
where data may sit.** The one place the FAQ does impose an India-location
requirement by reference to foreign providers is narrow and not ours:

> **Q 36. Do we need to store logs of Foreign Service providers and foreign part
> of financial transactions in India?**
> **Ans.:** *"Any service provider offering services to the users in the country
> needs to enable and maintain logs and records of financial transactions in
> Indian jurisdiction."*

That answer is about **records of financial transactions**. BookHop has none —
ADR-003 and P14 mean there is no financial transaction record in the system at
all. **The one FAQ answer that could have bitten is disarmed by a constraint we
already hold for a different reason.**

**The only reading on which BookHop would fail** is one where *"within the
Indian jurisdiction"* means *"beyond the reach of any foreign legal process"*.
No CERT-In text supports it, the FAQ contradicts it, and it would make
compliance impossible for any Indian company using any foreign-supplied
software or hardware. **I have not found that reading advanced by CERT-In, MeitY
or any court, and I am not going to invent it on BookHop's behalf.**

**What is genuinely unsettled, and why it does not reach us.** Commentary splits
on whether Q35's *"also"* means logs may be held *exclusively* abroad or only
*additionally* abroad with the primary copy in India. That ambiguity is real.
**It cannot bite BookHop on any reading, because our primary copy is in India
either way.** Separately, an FAQ is a clarification, not an amendment: it could
be withdrawn tomorrow and cannot cut down the direction's text. **That also does
not reach us, because Reason 1 does not rely on the FAQ.** We are compliant on
the text and compliant again on the issuer's gloss.

#### Decision, in the form the CTO asked for

| Question | Answer |
|---|---|
| Does an Indian region of a foreign-owned provider satisfy Direction (iv)? | **Yes.** |
| Must we move to an Indian-incorporated provider? | **No.** |
| Should we spend money or time on the hedge in ADR-001 §5? | **No.** |
| Is ADR-001 §8's reversal trigger *"privacy-compliance rejects §5"* fired? | **NOT FIRED.** Recorded here so the CTO can close it. |
| Is anything still blocked on me here? | **No.** INFRA.md §2's hold is released. Deployment is blocked only on founder spend approval (ADR-001 §7.1), which is not a compliance matter. |

**The reason our answer is clean is a design decision already taken, not the
region selector — and this is the part worth internalising.** Direction (iv)
binds *BookHop* to maintain *BookHop's* logs. Because ADR-001 §3 rejected Sentry,
hosted APM and third-party analytics, **every log we owe lives on a filesystem
we control.** The nationality of the landlord is immaterial when the filing
cabinet is ours. Had we shipped logs to a vendor's SaaS log product, the question
would be live and the answer would be harder — not because of ownership, but
because producibility *"in a reasonable time"* would depend on someone else's
support queue. **So ADR-001 §3's rejection of hosted error tracking turns out to
be the control that settles C1, and ADR-001 §3's rejection of BaaS was right for
a better reason than it gave: not that a region selector is untrustworthy, but
that we would not have been the entity in possession of the logs.**

#### Two residual reasons to prefer an Indian provider anyway — neither blocking

1. **The DPA (r.6(1)(f); Gate B item B15).** The hosting provider is a Data
   Processor and the founder must sign a contract with it. An Indian-incorporated
   provider is marginally easier: Indian governing law, Indian forum, and a
   counterparty that can be sued here. **This is a procurement preference, not a
   compliance requirement.** A foreign hyperscaler's standard DPA is signable and
   is signed by thousands of Indian companies.
2. **Foreign lawful access is a threat-model item, not a CERT-In item.** A
   foreign-headquartered provider may receive compulsory process in its home
   jurisdiction. That is a real confidentiality consideration and it belongs in
   `THREAT-MODEL.md`, where the CTO can weigh it. **It is not a Direction (iv)
   question and must not be smuggled in as one.** For a one-campus textbook
   pilot holding no financial data, no government identifiers and no precise
   location, the realistic exposure is low.

**Recommendation to the CTO, stated as an instruction so it is actionable:**
choose the provider on price, on whether it will actually sign a DPA, and on
whether its Indian region is a real region rather than an edge location. **Do not
re-architect, do not migrate, and do not treat this as a compliance blocker.**
If the founder prefers an Indian provider for sovereignty reasons, that is a
legitimate founder preference and costs nothing given the stack's portability —
but it is a preference, and this document will not pretend it is a requirement.

**Counsel: NO.** This is now closed. It does not need a lawyer and it should not
be put in the C1–C3 engagement.

### 5.3 Copyright — pirated textbooks are a when, not an if

**This is the highest-probability content risk BookHop faces** and it deserves
more attention than it usually gets. Photocopied course packs, scanned PDFs
bound as books, and unauthorised reprints of imported textbook editions are
endemic in Indian campus textbook markets. A used-textbook marketplace at a
Chennai campus **will** receive such listings.

**The safe-harbour-preserving process has two tracks, and they have different
clocks:**

**Track 1 — IT Act s79 + IT Rules 2021.** r.3(1)(b)(iv) requires the
intermediary's rules to prohibit information that **infringes any patent,
trademark, copyright or other proprietary rights**. A rights-holder complaint
goes through the Grievance Officer under r.3(2)(a): **acknowledge in 24 hours,
dispose in 7 days**. A court order or government notification triggers
**r.3(1)(d): 3 hours**.

**Track 2 — Copyright Act s52(1)(c) + Copyright Rules 2013, r.75.** On a
compliant written complaint from the rights owner, the person responsible for
the storage must **disable access within thirty-six hours** and **keep it
disabled for twenty-one days** or until a court order is produced, whichever is
earlier. The complainant must undertake to file an infringement suit within
21 days. If no court order arrives in 21 days, access may be restored and the
intermediary need not act on further notices from that complainant about the
same work at the same location.
*Sources: law-firm commentary only (searched 2026-10-21) — I could not reach the
Copyright Rules 2013 Gazette text. **The 36-hour figure and the r.75 mechanics
must be verified against the rule text before the takedown SOP is finalised.***
Note also that commentators dispute r.75's scope: its language tracks
s52(1)(b)–(c), which address **transient and incidental storage**, and whether
it reaches a marketplace hosting listings is contested. **r.75 has no
counter-notice mechanism**, which is a known gap.

**Track 3 — E-Commerce Rules r.5(5).** Maintain a record identifying sellers who
have **repeatedly** offered goods removed or disabled under the Copyright Act,
Trade Marks Act or IT Act. No obligation to terminate, but the record is
mandatory and it is the artefact that proves a takedown process exists.

**What a safe-harbour-preserving takedown process must have, concretely:**
1. A **published notice-and-takedown address and form** that captures what
   r.75 requires: the work, the infringing location, the complainant's
   authority, and the undertaking to sue within 21 days.
2. **Timestamped receipt** and acknowledgement within 24 hours.
3. **Disable within 36 hours** of a compliant copyright complaint; **3 hours**
   for a court/government order; **2 hours** for r.3(2)(b) categories.
4. **A 21-day hold** with automatic restoration if no court order is produced,
   and a record of the restoration decision.
5. **The r.5(5) repeat-infringer record**, keyed to the seller, surviving
   account deletion (see the retention carve-out in §7).
6. **Preserve removed content for 180 days** (r.3(1)(j)).
7. **A listing-time deterrent**: prohibit photocopied, scanned, spiral-bound and
   unauthorised-reprint listings in the seller undertaking under r.5(2); require
   an ISBN; and flag listings whose photographs show photocopy or spiral binding
   for human review. **Prevention is cheaper than 36-hour takedowns.**

**The s52(1)(a) fair-dealing / first-sale question.** Reselling a *legitimately
purchased physical copy* is not infringement — Indian copyright law exhausts the
distribution right in a lawfully made copy. **BookHop's exposure is not the
resale of genuine books; it is the listing of unauthorised reproductions.** Say
this in the seller policy, because it is also the honest framing for users.

**Conclusion.** Process required before pilot; artefacts listed above.
**Uncertainty: MODERATE on r.75's applicability to a marketplace, HIGH on the
practical question of how a platform distinguishes a legitimate used copy from
an unauthorised reprint from a photograph.** The second is a product problem as
much as a legal one.
**Counsel: YES, narrow — the takedown SOP and the seller undertaking wording
(§9 Q10).**

### 5.4 Campus and state-level requirements

**There is no state licence or permit for operating an online marketplace in
Tamil Nadu.** I searched for one on 2026-10-21 and found none; the regulatory
requirements are the central ones already covered (incorporation under
r.4(1)(a), GST when triggered, IT Rules compliance).

**What does apply:**
- **Tamil Nadu Shops and Establishments Act 1947** — compulsory **online
  registration** was introduced by amendment with rules notified **2 July 2024**.
  Sources conflict on whether registration applies to all establishments or only
  those employing ten or more workers, and on the filing window (30 days vs
  6 months). *Commentary-sourced; **verify on the TN Labour Department portal**.*
  This attaches to BookHop's **office as an employer**, not to the platform.
- **Campus access is contractual, not regulatory.** Operating on college
  premises — stalls, collection points, posters, orientation sessions, staffed
  handover desks — requires **written permission from each institution**, on that
  institution's own terms. Several Chennai institutions are autonomous or
  affiliated to Anna University / University of Madras and have their own
  rules on commercial activity, student data sharing and external vendors.
- **This is a founder-reserved matter.** Per README §2, campus agreements are
  **legal commitments** and only the founder may commit them. No agent may sign
  or promise campus terms.
- **Two things a campus MoU must address, and which are easy to forget:** (i)
  whether the institution will **share or confirm student enrolment data** for
  verification — that is a disclosure of personal data by the institution and
  needs its own basis and a written arrangement; and (ii) whether BookHop may
  use the institution's **name or logo**, which is a trademark and reputational
  question, not a data one.

**Conclusion.** No platform licence; incorporation and (probably) Shops &
Establishments registration; campus access by written MoU per institution.
**Uncertainty: LOW on the absence of a platform licence; MODERATE on Shops &
Establishments applicability pending verification; institution-specific and
unknowable in the abstract for campus rules.**
**Counsel: YES for the campus MoU template — this is a contract, and it is one
the founder will sign repeatedly (§9 Q11).**

### 5.5 Platform liability for physical-safety incidents at handovers

**This is the exposure with the least law and the most consequence.** A physical
meeting between two strangers, arranged by BookHop, at a place and time BookHop
helped choose, carries a risk of assault, theft, harassment or worse. If it
happens, it will be the defining event for the company.

**The legal position, as best I can state it:**
- **IT Act s79 does not help.** Safe harbour is for liability "in respect of any
  third party information, data, or communication link made available or hosted"
  by the intermediary. **A physical assault is not third-party information.**
  s79 is not a shield against offline harm.
- **Consumer Protection Act 2019** exposes BookHop to a "deficiency in service"
  claim if it has held out a service — safe handovers, verified users, vetted
  meeting points — and failed to provide it to the standard represented.
  **The exposure scales directly with what we claim**, exactly as in §2.5.
- **Tortious negligence** is the general-law route: a claim that BookHop owed a
  duty of care in designing the handover process and breached it. I am not aware
  of an Indian decision establishing such a duty for an online marketplace, and I
  could not find one on 2026-10-21. **The absence of precedent cuts both ways:
  it is not settled that we are liable, and it is not settled that we are not.**
- **Criminal liability** for the perpetrator is a matter for the police, and
  BookHop's obligation is to preserve and produce evidence (IT Rules r.3(1)(j),
  180 days) and to cooperate — not to investigate.

**What reduces the exposure, in order of effect:**
1. **Do not warrant safety.** Never say "safe", "secure", "verified safe" or
   "BookHop-protected" about a handover. Say what is true: "meet in a public
   place", "campus library forecourt is well-lit and staffed until 8pm".
   **Guidance is protective; a guarantee is an assumed duty.**
2. **Default to public, staffed, daylight locations.** Pre-set campus handover
   points rather than free-text addresses. This is a product decision with a
   legal effect.
3. **Never expose home or hostel addresses** (see §2.4(i)).
4. **In-app, retained messaging** so that pre-meeting conduct is evidenced.
   Chat retention is a safety control, not just a feature — and it is one reason
   the one-year retention floor in §1.6 is a feature rather than a burden.
5. **A reporting and blocking flow that works before an incident**, with a
   logged outcome for every report. The pattern a plaintiff looks for is a prior
   report that was ignored.
6. **An incident log and a written escalation procedure**, including when to
   advise a user to go to the police and when BookHop itself reports. Note the
   IT Rules r.3(1)(c)(iii) obligation (as substituted in 2026) to inform users
   about **mandatory reporting** of offences under laws such as the BNSS and
   POCSO — and note that POCSO reporting is **mandatory** and applies if a minor
   is involved, which §1.4 says is a live possibility.
7. **Insurance.** Public liability / professional indemnity. A commercial
   decision, and a founder spending decision, but it belongs on the pre-launch
   list.

**Conclusion.** No safe harbour applies. The exposure is managed by **not
over-claiming**, by **designing the handover**, and by **evidencing the
process** — not by terms and conditions, which will not exclude liability for
negligence in any event.
**Uncertainty: HIGH on legal outcome, LOW on what reduces risk.** This is the
clearest case in the document where the right answer is operational rather than
legal.
**Counsel: YES — specifically on the limitation-of-liability drafting and on
whether our handover design creates an assumed duty of care (§9 Q12).**

---

## 6. Blocker tables

**Two separate lists. The pilot list is what must be true before a verified
adult at a Chennai campus can list a book. The launch list is what must be true
before the public can sign up.** Conflating them is how a pilot slips a quarter.

### 6.1 Must be resolved BEFORE PILOT (G3)

| # | Blocker | Source | Owner | Why it is a pilot blocker |
|---|---|---|---|---|
| P1 | **Incorporate as a company** under the Companies Act | E-Com Rules r.4(1)(a) | founder | An e-commerce entity must be a company. Lead time measured in weeks. |
| P2 | **Appoint and publish a Grievance Officer** (name, designation, contact) and a **nodal contact resident in India** | IT Rules r.3(2)(a); E-Com r.4(1)(b), r.4(4) | founder + ops | Statutory, immediate, and a precondition of safe harbour. |
| P3 | **Takedown + grievance SOP meeting 3h / 2h / 24h / 7d clocks**, with an on-call rota | IT Rules r.3(1)(d), 3(2)(a), 3(2)(b) | marketplace-ops | In force since 20 Feb 2026. Missing it forfeits s79 **and** E-Com r.5(1) safe harbour. |
| P4 | **Published privacy notice, terms, and seller undertaking**, drafted by counsel | E-Com r.5(2); IT Rules r.3(1)(a); DPDP r.3 (design-ahead) | counsel + product | r.5(2) requires an actual collected undertaking, not a policy page. |
| P5 | **Age gate: DOB field, server-side 18+ block, logged human review, no ID collection** | DPDP s9 (design-ahead); 4th Sch. Pt B item 6 | cto + product | Minors on a campus platform are a certainty, not an edge case. |
| P6 | **Consent capture with per-purpose granularity and an audit trail** | DPDP s6, r.3 (design-ahead) | cto | Retrofitting consent into a live data model after 13 May 2027 is far more expensive. |
| P7 | **Deletion flow = tombstone + purge**, retaining transaction records and logs for 1 year | DPDP r.8(3), r.6(1)(e) | cto | A cascade delete is both a compliance and a dispute-evidence failure. |
| P8 | **Breach runbook on the 6-hour CERT-In clock**; 180-day logs in India, NTP-synced | CERT-In Directions 2022 | cto | Operative breach law today. DPDP r.7 does not commence until 2027. |
| P9 | **Copyright takedown SOP + repeat-infringer record + listing-time deterrents** | Copyright Rules r.75; E-Com r.5(5); IT Rules r.3(1)(b)(iv) | marketplace-ops + cto | Pirated textbooks will appear in week one. |
| P10 | **Handover safety design**: public pre-set points, no addresses published, reporting flow with logged outcomes, **no safety warranties in any copy** | §5.5 | product + design + ops | The highest-consequence risk. Copy review is part of this blocker. |
| P11 | **Written campus permission (MoU) per institution** — founder signs | README §2 | founder | Legal commitment; founder-reserved. |
| P12 | **CREDIT DESIGNS (a) AND (b) ARE BLOCKED FOR PILOT.** Only design (c), a non-redeemable ordinal reputation signal, may ship. | MD-PPI 2021 ¶2.1/2.8; Draft MD 2026 ¶4.1; D-003, D-004 | privacy-compliance | (a) is a PPI and breaches D-004. (b) needs counsel per D-003. |
| P13 | **Verify CERT-In primary text, Copyright Rules r.75 text, and TN Shops & Establishments applicability** · **v1.1: CERT-In limb CLOSED** (§5.2, §5.2.1 — direction and FAQ both extracted from the CERT-In PDFs on 2026-10-21). **r.75 and TN Shops still open.** | §5.2, §5.3, §5.4 | privacy-compliance | Two of three items remain commentary-sourced. The evidence standard requires closing them. |
| P14 | **Do NOT collect PAN or Aadhaar; do NOT record settled sale consideration** | s194-O Explanation; §4.3 | cto + product | A recorded settled price creates a determinable TDS gross amount. |
| P15 | **`review_listings --photos` copies must expire on a clock, ceiling 24h** — a sweep at the top of every run, covering `gettempdir()` and any `--photos DIR` | §7 row 25; DPDP s8(5), s8(7); r.6(1) | cto + backend | **At pilot every listing is reviewed, so this path runs on every student.** It is the only row in §7 with no retention period, and the data is photographs taken inside students' rooms. Gated by `tests/contract/test_the_review_copies_expire.py`. |
| P16 | **A want must have a retention that something honours, and the deletion card must say a want is kept.** Four parts, all small: (i) a purge limb that NULLs `book_requests.free_text_title` and `course_code` at `purge_due_at`, **or** `book_requests` named in `PURGE_SKIP_LIST` with a reason — not neither; (ii) a clock on a want that is never withdrawn (set `EXPIRED`, or set `purge_due_at` at creation); (iii) a **bound on `free_text_title` in `create_request`**, not only in `WantedForm` — the API path has none; (iv) a ninth `erase.retained.*` item for wants, in both languages | §7 rows 26–27; DPDP s8(7), r.8(3); **CP (E-Commerce) Rules r.4(3) — binds today** | cto + backend + frontend | **The want box is on the main journey of the pilot** (J4 step 2), A-32 made it store the student's own words on **every** want rather than only the unresolvable ones, and today those words survive account deletion **for ever**, undisclosed. (iv) alone is the r.4(3) exposure and does not wait for 2027. Gated by `tests/contract/test_the_inventory_covers_the_schema.py`. |

### 6.2 Must be resolved BEFORE PUBLIC LAUNCH (G4) — in addition to all of the above

| # | Blocker | Source | Owner | Trigger |
|---|---|---|---|---|
| L1 | **Qualified Indian lawyer reviews terms, privacy notice, seller terms, and liability limits** | README §7 | founder + counsel | Mandatory. Non-negotiable. |
| L2 | **CA / tax counsel signs off on GST and TDS position before any fee or payment collection** | §4.2, §4.3 | market-finance + CA | Fee activation is a tax decision with lead time. |
| L3 | **NCH convergence partnership** — mandatory from 1 Jan 2027 | E-Com r.4(7) as substituted | marketplace-ops | 1 Jan 2027. |
| L4 | **Dark Patterns 2023 compliance + yearly self-audit + displayed certificate** | E-Com r.4(15) new | design-director + ops | 1 Jan 2027. |
| L5 | **Ranking parameters published in descending order of significance** | E-Com r.5(3)(f) as substituted | product + cto | 1 Jan 2027; also r.4(11)(c). |
| L6 | **Sponsored listing disclosure**, if any promoted placement exists | E-Com r.4(12) new | product | 1 Jan 2027. |
| L7 | **Prior-price (30-day lowest) display**, if any price-reduction UI exists. *Recommendation: remove struck-through prices instead.* | E-Com r.4(13) new | design-director | 1 Jan 2027. |
| L8 | **Post-purchase seller-detail disclosure flow** — reviewed, logged, minimal | E-Com r.5(3)(a) proviso | cto + ops | At launch. |
| L9 | **Business-seller threshold flag** with the fuller r.6(5) disclosure set incl. GSTIN/MSME | E-Com r.6(5)(j) new; r.2(1) proviso | cto + product | 1 Jan 2027. |
| L10 | **Full DPDP readiness for 13 May 2027**: notice, granular consent, rights self-service incl. **nomination (s14)**, 72-hour Board breach report, Data Processor contracts under r.6(1)(f) | DPDP ss5–14; rr.3, 6, 7, 14 | cto + privacy-compliance | **13 May 2027 — no transition period.** |
| L11 | **Credit design (b) cleared by counsel, or dropped** | §3.3(b); D-003 | founder + counsel | Before any credit release. |
| L12 | **Payment provider selected with direct settlement; no escrow, no float** | D-004 | cto + founder | Before payment activation. |
| L13 | **Public liability / professional indemnity insurance** | §5.5 | founder | Before public scale. |
| L14 | **Re-verify every rule in this document; re-check the RBI 2026 MD and DPDP commencement** | §0 | privacy-compliance | At G4. |

---

## 7. Data inventory

**Lawful basis column reads: current basis (to 12 May 2027) → DPDP basis (from
13 May 2027).** Under DPDP the only bases are **consent (s6)** and the **s7
legitimate uses** — s7(a) covers data the Data Principal voluntarily provided
for a specified purpose. **There is no "legitimate interests" ground in Indian
law.** Where a field is marked **s7(a)**, that is a narrow reading and consent
should be captured anyway.

**Retention column reads from the point the purpose is served.** Two floors
override any shorter period: **DPDP r.8(3)** (personal data, traffic data and
processing logs, minimum **1 year**) and **r.6(1)(e)** (security logs,
**1 year**). CERT-In requires 180 days, which is subsumed.

| # | Field | Purpose | Lawful basis | Retention | Deletion mechanism |
|---|---|---|---|---|---|
| 1 | **Name / display name** | Identify the counterparty at handover; accountability | Contract → **Consent (s6)** | Until deletion request, then **purge**; pseudonymous seller ID survives in the transaction record for 1 yr | Hard-delete from profile; replace with `deleted-user-<pseudo-id>` in retained records |
| 2 | **Phone number** | Account recovery; OTP; handover coordination | Contract → **Consent (s6)** | Until deletion, then purge. **Salted hash retained 1 yr** for ban evasion and dispute linkage | Hard-delete plaintext; retain one-way hash only |
| 3 | **Email address** | Account identity; notices; rights requests | Contract → **Consent (s6)** | Same as phone | Same as phone |
| 4 | **Password / credential** | Authentication | Contract (**SPDI r.3 sensitive — applies today**) → Consent | Until deletion, then immediate purge | Hard-delete. Stored only as a salted hash (argon2/bcrypt); never recoverable |
| 5 | **Campus affiliation** | Eligibility; proximity matching; trust signal | Contract → **Consent (s6)** | Until deletion, then purge; coarse campus code retained 1 yr in the transaction record | Purge the affiliation record; retain campus code only |
| 6 | **Campus verification evidence** (institutional email confirmation, enrolment evidence) | Prove eligibility; prevent impersonation; **and — amended v1.2 — disclose to a counterparty on a listing that the seller signed in with a college email address** (§2.5a) | Contract → **Consent (s6)**; the **disclosure** limb sits under `listing_publication` and **must be in the notice** | **Purge the evidence immediately on successful verification.** Retain only a boolean + method + timestamp | Delete the artefact at verification time by design — do not store it pending deletion. **The displayed string is gated on `campus_verifications.method = 'EMAIL_DOMAIN'`, never on `users.campus_verified`, and never renders the domain itself** |
| 7 | **Date of birth / adult status** | **Age-gate only** — confirm the user is not a child | Contract → **4th Sch. Pt B item 6** (exempt from s9(1)/(3)) + **Consent** | DOB purged after verification; retain **adult-status boolean + verification method + reviewer + timestamp** for the account's life + 1 yr | Purge DOB post-verification; boolean survives as the audit trail. **Never reused for any other purpose.** |
| 8 | **Approximate location** (campus / locality, **not precise GPS**) | Proximity search; handover point suggestion | Contract → **Consent (s6)**, separately captured | Until deletion, then purge. **Do not store a location history.** | Hard-delete; current value only, overwritten on change |
| 9 | **Listing photographs** | Show condition and edition; deter misdescription | Contract → **Consent (s6)** | Until listing closes + **1 yr** (r.8(3) — the listing is part of the transaction record) | Delete originals and derivatives from object store and CDN after 1 yr; purge EXIF **at upload** |
| 10 | **Listing metadata** (title, ISBN, condition, asking price, origin) | The core service; exact-edition matching | Contract → **Consent (s6)** / s7(a) | Transaction record + **1 yr** | Retained pseudonymously for 1 yr, then erased |
| 11 | **Chat messages between users** | Negotiation; handover coordination; **dispute and safety evidence** | Contract → **Consent (s6)** | **1 yr** from last message (r.8(3)); **180 days minimum if removed under IT Rules r.3(1)(j)** | Content purged at 1 yr; thread existence + participants pseudonymised. **Not deleted on account deletion** — disclose this in the notice |
| 12 | **Handover meeting point and time** | Coordinate the handover; **safety evidence if an incident occurs** | Contract → **Consent (s6)** | **1 yr** (r.8(3)) | Pseudonymised at account deletion; erased at 1 yr |
| 13 | **Reports and disputes** (incl. safety reports) | Trust and safety; moderation; **evidence of process** | Contract → **Consent (s6)** / legal obligation | **1 yr minimum**; longer where an incident is open or referred to police | Not deletable while open. Closed reports pseudonymised, erased at 1 yr unless preserved |
| 14 | **Repeat-infringer record** (copyright/trademark) | **Mandatory** under E-Com r.5(5) | Legal obligation (r.5(5)) | For as long as r.5(5) requires — **survives account deletion** | Not user-deletable. Keyed to a pseudonymous identifier, minimum content |
| 15 | **Reputation / trust signal (design (c))** | Trust; counterparty assessment | Contract → **Consent (s6)** | Life of account; pseudonymised for 1 yr after deletion | Purged with the account; aggregate not reconstructable to the individual |
| 16 | **Security and access logs** | Detect, investigate and remediate unauthorised access | Legal obligation — **r.6(1)(c)/(e)**; CERT-In | **1 yr**, in India, NTP-synced | **Not user-deletable.** Rotated and erased at 1 yr. Access to logs itself logged |
| 17 | **Processing / traffic logs** | r.8(3) Seventh Schedule purposes | Legal obligation — **r.8(3)** | **Minimum 1 yr** | Not user-deletable; automatic erasure at 1 yr unless another law requires longer |
| 18 | **Consent records** (purpose, version, timestamp, withdrawal) | Prove consent; evidence for the Board | Legal obligation | Life of account + **1 yr** after the last processing | Not user-deletable — it is the record that the deletion itself was lawful |
| 19 | ~~PAN / Aadhaar~~ | — | — | — | **NOT COLLECTED AT PILOT.** See P14 and §4.3 |
| 20 | ~~Precise GPS, contact-list, device identifiers beyond session~~ | — | — | — | **NOT COLLECTED.** No purpose stated → under the charter's own metric, a field with no stated purpose is a defect |
| 21 | **Search queries** — `search_events.query_norm` (free text), `isbn_query`, `session_key`, `filters`, `result_count` | **Search success rate** (`METRICS.md`) and **R-01**: what students look for that we do not have. **Not** ranking, personalisation, profiling or advertising | Contract / **s7(a)** — **and see the recommendation below: with no actor key this is not personal data at all and needs no consent** | **1 yr** from `occurred_at`, then purge (r.8(3) floor on processing logs) | Nightly `retention.purge` on `purge_due_at`. **Not touched by account deletion — there is nothing linked to delete.** `query_norm` truncated at upload; rendered to staff in aggregate only |
| 22 | **`messages.contact_pattern_flag`** — a boolean **derived** from message content (phone / email / UPI-handle pattern **only — never a currency pattern, §4.3.3 condition 2**) | Harassment and safety review; the O-7/O-10 leakage indicator. **It flags, it does not block.** **Purpose limitation, v1.2: never money.** A per-message boolean saying an amount was discussed would be a structured signal about consideration | **NOT consent.** Contract / **s7(a)** + **legal obligation** (IT Rules r.3(1)(b) duty to cause users not to host unlawful information). **I am refusing the CTO's proposed `safety_moderation` consent basis — see below** | **Lives and dies with the message**: 1 yr from the thread's last message. **Exceptions:** survives while linked to an open `report`/`safety_incident` (row 13's rule), and 180 days if the message was removed under r.3(1)(j) | **Reset to `false` in the same statement that sets `messages.body_purged_at`** unless a report preserves it. **Not deleted on account deletion** (follows row 11) — and that must be in the notice |
| 23 | **Support instrumentation** — `support_tickets` (`user_pseudonym`, links, channel, timestamps) and `support_work_log` (`staff_id`, `seconds`, `bucket`, `source`, `batch_*`, **`note` free text**) | **D-009's mitigation**: support minutes per transfer (R-13, R-25, D-009's reversal trigger); operating support | **Two data subjects, two bases.** Student limb: Contract / **s7(a)** + consent under `account`. **Staff limb: employment** — this is worker monitoring and is a new category in this inventory | **Identifiers 1 yr; measurement indefinitely.** At 1 yr purge `note` and NULL `user_pseudonym`; **keep `seconds`, `bucket`, `source`, `batch_run_id`, `batch_match_count` indefinitely** — pseudonymous, and the evidence D-009 exists to produce | Purge job for `note` and `user_pseudonym`. **`note` must be manually reviewed on any erasure or access request** — a free-text staff note may name the subject and the purge job cannot see that |
| 24 | **`PSEUDONYM_SALT`** — the server-side secret outside the database that salts `user_tombstones.email_hash` | **The control that makes row 3's "one-way hash" claim true.** Without it, a sha256 of a predictable institutional email is enumerable from a roll list | Not personal data. A **security safeguard under r.6(1)**, and the precondition of row 3's lawfulness | **As long as any un-purged `email_hash` references its version, and no longer.** Version it; keep at most two versions; retire a version when no live tombstone references it | `shred` the retired version from `/etc/bookhop/env`; log the rotation in `audit_log`. **On confirmed compromise: rotate immediately AND purge every `email_hash` under the compromised version ahead of `purge_due_at`** |
| 25 | **Moderation working copies of listing photographs** — plaintext files written by `review_listings --photos` to an operator's filesystem, outside the object store | Let the one human control in the pilot queue **see** what it is judging (F50 / R-R6). Nothing else: not archival, not evidence, not training | **s7(a)** + the IT Rules r.3(1)(b) trust-and-safety limb — **the same basis as row 22, and like row 22 it is not a withdrawable consent purpose.** The copy is a *rendering step* within row 9's already-notified purpose, **not a new purpose**, and it stays that way only because it is transient | **The review session. Hard ceiling 24 hours from creation**, whether or not a decision was reached. **Not** "until the operator deletes it" — see the ruling. Row 9's one-year clock does **not** apply: it is the retention of the *record*, and a working copy is not the record | **Automatic.** A sweep of `bookhop-review-*` directories older than 24h, in `tempfile.gettempdir()` and in any `--photos DIR`, run at the top of every `review_listings` invocation. The printed `rm -rf` stays as the fast path, **not as the mechanism.** Erasure reaches these only through the clock, which is why the clock has to be short |
| 26 | **`book_requests.free_text_title`** — **the student's own words**, typed into the want box. Since **A-32** it is stored whenever the student typed a title, book FK or not, and **rendered back to that student** on `/wanted` in place of a withheld catalogue title | Record what book a student is looking for; match it against supply (`METRICS.md` match rate, R-01); **EC-17** — the staff signal that the catalogue is missing a prescribed title; **and, since A-32, show the student their own want** | Contract → **Consent (s6) under `account`** / s7(a). **Withdrawable — and, unlike row 22, that is correct:** see the ruling below | **`closed_at` + 1 yr** (r.8(3)) once the want is closed. **An OPEN want has no clock** — nothing sets `EXPIRED` — and **nothing reads `purge_due_at` on this table at all.** Stated as the system is, not as it should be: **P16** | **Today: none.** `erase_account` → `_detach_listing_rows` NULLs `requester`, keeps `requester_pseudonym`, sets `purge_due_at` on OPEN rows **and leaves the text byte-for-byte**. No purge handler walks this table and it is not in `PURGE_SKIP_LIST`. **Required: NULL the text at `purge_due_at`, and enumerate the want on the deletion card** |
| 27 | **`book_requests.course_code`** — free text, whitespace-collapsed and upper-cased, cap 40 **on the form path only**. Load-bearing: **A-33** puts it in the request idempotency key | Which syllabus is driving demand — the product thesis's only direct evidence; part of request identity (A-33), so two wants for two courses are two rows | Same as row 26 | Same as row 26 | Same as row 26. **A-33 does not block purging it:** the idempotency filter only ever matches `status='OPEN'`, and an erased or closed want is never OPEN |
| 28 | **`data_subject_requests.stated_problem`** — the student's own words about what BookHop holds wrongly about them (**A-29**, s12(1)–(2) correction). Found by writing §7.1's test, not by being reported | Exercise the correction right; evidence that it was exercised and answered inside the 7-day clock | **Legal obligation** (DPDP s12 from 13 May 2027; SPDI r.5(6) today) + s7(a). **Not a consent purpose** — the exercise of a right is not something the subject can be asked to consent to | **1 yr with the row** (row 18's family) | Not user-deletable: it is the record that a right was exercised and answered. **The one free-text column that already has its bound** — `MAX_STATED_PROBLEM = 2000` in `apps/accounts/services.py`, with the reason written at the constant. **That constant is the control rows 26 and 27 are missing** |

#### Row 21 — the recommendation is to collect *less*, and no metric suffers

`search_events` as specified carries `actor_pseudonym`. **No metric in
`METRICS.md` needs it.** Search success rate is *"searches returning ≥1 result
the user then opens"* — that is a join from `search_events` to
`search_result_opens.search_event_id`, per event, not per person. R-01 is "what
is searched and not found" — also per event.

> **Instruction: drop `actor_pseudonym` from `search_events`. Keep
> `session_key`, and make it a random per-session value generated for this
> purpose, held in the session, written only to `search_events`, and **never
> joinable to `users` or to the Django session table**.** Session scoping is a
> real measurement need — it distinguishes one student refining a query five
> times from five students searching once — and it is the whole of the need.

**That removes a consent purpose, a deletion obligation and an erasure-request
limb, and keeps every number.** It also means `query_norm` being free text
stops mattering much: it is a defect, not a disaster.

**Treat `query_norm` as personal data regardless of its intended content.** It
is a free-text field a student types into. A book title is not personal data; a
free-text box will eventually contain a name, a phone number or a hostel room,
because free-text boxes always do. **The real risk here is not the regulator; it
is a staff member reading what an identifiable student searched for.** Hence:
truncate on write, and surface it to staff only in aggregate.

**If the CTO keeps `actor_pseudonym`** — which is a legitimate choice I am not
vetoing — then this needs a **new consent purpose key `service_improvement`**,
separately withdrawable, and withdrawal must degrade search logging to anonymous
rather than break it. The existing key set (`account`, `listing_publication`,
`location_proximity`, `chat`, `safety_moderation`, `notifications`) has no home
for it, and putting it under `safety_moderation` would be purpose creep.
**Dropping the column is cheaper than the consent machinery.**

#### Row 22 — I am refusing the proposed lawful basis, and the field stays

`DATA-MODEL.md` §8 states `contact_pattern_flag` is *"Covered by the
`safety_moderation` consent purpose."* **That is the wrong home and I am not
signing it off.**

**The reason is a one-line thought experiment.** If the basis is withdrawable
consent, then a user who withdraws `safety_moderation` consent must have their
messages stop being flagged. **That makes consent withdrawal a tool for a
harasser** — the person with the strongest incentive to withdraw is the person
the flag exists to detect. A safety control whose operation the subject can
switch off is not a safety control.

**The correct basis** is the same family as rows 13, 16 and 17: processing
necessary to BookHop's trust-and-safety function and to its IT Rules r.3(1)(b)
duty, disclosed in the notice, **not withdrawable**. Under DPDP that is a narrow
**s7(a)** reading plus a legal-obligation limb, which is exactly the hedge this
table's header already flags — *"Where a field is marked s7(a), that is a narrow
reading and consent should be captured anyway."* So: **capture consent for
messaging under `chat`, disclose the flagging in the notice, and do not make the
flag itself contingent on a withdrawable purpose key.**

**The flag stays. The regex stays. The "flags, does not block" design is
correct** — blocking contact-sharing is unenforceable and user-hostile, and the
CTO's own `# ponytail` note that the signal is directional is honest.

**One catch worth a line of code.** `messages.body` is purged at 1 year;
`contact_pattern_flag` as specified is not. **That leaves a permanent marker
saying "this pseudonym shared contact details" against a message whose content
no longer exists — a profile with the evidence deleted and the conclusion
retained.** Reset the flag in the same statement that purges the body, unless an
open report preserves it.

#### Row 23 — two subjects, and the riskiest field is the free-text note

**`support_work_log` is worker-monitoring data.** A per-task stopwatch against a
named staff member is personal data about that person, and it is a category this
inventory has not had before. At pilot the staff member is the founder, which is
why the rule is cheap to write now and expensive to retrofit:

> **The staff member must be told the timer runs and what the data is for, and
> the data must not be used for any purpose other than the D-009 cost
> measurement without a fresh notice.** It is a cost instrument, not a
> performance-management instrument. Writing that down now is what stops it
> becoming one when there are three staff.

**`support_work_log.note` is the highest-risk field in this set** — free text
typed in a hurry by staff about an identifiable student, retained a year,
readable by any staff account. Three requirements:

1. **`note` is for work description, never a characterisation of a person**, and
   the admin form must say so at the field. A hint text is the whole control and
   it costs one line.
2. **`note` is in scope for a §1.8 access request.** Staff notes about a data
   subject are the subject's personal data. People are routinely surprised by
   this; do not be.
3. **`personal_data_access_log` must fire when a staff member opens a support
   ticket**, not only on a profile or chat view. `DATA-MODEL.md` §8 requires it
   for profiles and chat; **extend it to tickets explicitly.**

**The honest limitation, stated rather than hidden:** `erase_account` is
specified as one transactional service function, and **free-text notes are the
one place that model breaks.** A purge job cannot tell whether a note names the
subject. An erasure or access request therefore requires a human to read the
notes. **Put that step in the runbook rather than pretending the job covers it.**

**And one instruction on `MANUAL_ENTRY`.** A staff member logging off-platform
minutes may be recording that a WhatsApp conversation happened. **Record
`channel='OTHER'` and the seconds. Never the handle, never the content.**

**The retention split is deliberate and mirrors how I treated the paper pilot.**
`INCORPORATION-AND-BLOCKERS.md` §4.5 set identifiers at 30 days and measurement
data indefinitely, pseudonymised. **Row 23 is the same rule at a one-year floor,
because the floor now applies.** Consistency here is not tidiness — it is what
makes the two datasets comparable, which `DATA-MODEL.md` §8 says is the point of
keeping `TEST-1`'s bucket names.

#### Row 24 — the salt, and a correction to the premise

**I was asked to confirm that the salt "is what makes the pseudonym survive
deletion and therefore what makes repeat-transfer-at-90-days measurable."
It is not, and the distinction is the whole compliance answer.**

What makes the pseudonym survive deletion is **`users.pseudonym`**, a uuid
copied onto `listings.seller_pseudonym`, `transfers.{seller,buyer}_pseudonym` and
the rest. Repeat-transfer-@90d (`DATA-MODEL.md` §9.2) groups by those columns and
works with no salt and no email hash at all. The salt serves **`email_hash`,
whose only permitted purposes under row 3 are ban-evasion detection and dispute
linkage.** `DATA-MODEL.md` §2 says so itself and is right.

**Why the distinction matters enough to correct the question.** The known
consequence is that repeat-transfer-@90d **undercounts users who delete and
rejoin**. Someone will eventually propose fixing that by matching `email_hash`
to re-link a rejoiner to their old pseudonym. That would:

1. be **purpose creep** against row 3, which permits exactly two purposes;
2. **defeat the one-way pseudonymisation** §10.1 promises and that
   `tests/e2e/test_deletion.py` limb (c) exists to prove; and
3. make *"delete my account"* a false statement in the privacy notice.

> **The undercount is the price of honest deletion. It is not a bug and it must
> not be fixed. Report it as a known undercount wherever the metric appears** —
> `DATA-MODEL.md` §9.2 already says it out loud, and `METRICS.md` should carry
> the same caveat. **Anyone who closes the gap has broken the deletion
> guarantee, not improved the metric.**

**Does a server-side secret outside the database satisfy row 3's intent? Yes —
and it is not a nice-to-have, it is the only thing that makes row 3 true.**
Institutional emails are low-entropy and predictably formatted
(`firstname.lastname.rollno@campus.ac.in`). An unsalted hash, or one salted with
a value stored in the same database, is **enumerable from a published roll list
in seconds**. So the hash is only "one-way" because the salt is elsewhere.
**This upgrades the salt from an implementation detail to a named control, and it
should be listed as one in `THREAT-MODEL.md`.**

**What its compromise would mean.** Either half alone is close to harmless: the
salt without the database hashes nothing; the database without the salt yields
unusable hashes. **With both**, an attacker enumerates the campus email list and
**re-identifies every tombstoned account from the preceding year — undoing every
deletion BookHop performed, for exactly the users who asked to be forgotten.**
Note the shape of that: it adds nothing against *live* users, whose emails are in
the database in plaintext anyway. **The salt is a deletion-integrity control, not
a confidentiality control, and its loss harms only the deleted.**

Three operational consequences, all cheap and none currently written down:

1. **Add it to the breach runbook's T+1h scoping list by name:** *"was
   `PSEUDONYM_SALT` exposed?"* — because the answer changes who must be
   notified. **And here is the nasty part: if the salt leaks, the people you owe
   notice to are the people whose contact details you purged.** You cannot reach
   them. The only available response is the CERT-In report (Annexure I item (xii)
   Data Leak), the Board report from 13 May 2027, and a published notice. Decide
   that now, not at T+2h.
2. **Version the salt; do not rotate on a schedule.** Naive rotation silently
   breaks ban-evasion matching against older tombstones. Add
   `user_tombstones.salt_version smallint NOT NULL`, hash a candidate under every
   live version, keep at most two, retire a version when no un-purged tombstone
   references it — which happens automatically a year after rotation, and
   `purge_log` proves it. **One smallint and a two-iteration loop**, and it is
   the cheap fix for the rotation gap INFRA.md §2 already declares as an ASVS V13
   shortfall.
3. **On confirmed compromise, purge the affected hashes early.** A hash that is
   no longer one-way has **no lawful basis for retention** — row 3 permits a
   one-way hash, not a reversible one. So: rotate, then delete every `email_hash`
   under the compromised version immediately, ahead of `purge_due_at`, and accept
   the loss of ban-evasion matching. That is the correct trade and it should be
   in the runbook rather than improvised.

**And one thing that will otherwise be discovered the hard way.** INFRA.md
correctly keeps the salt out of every dump. **Therefore a restore to a fresh VM
produces a database whose `email_hash` values cannot be verified against
anything.** That is expected behaviour, not a restore failure, and §3.3's
assertion set should say so. It also means **the salt must exist somewhere other
than one unbacked-up VM** — the founder's password manager, written down at
provisioning. A secret that exists in exactly one place is a secret you will
lose, and losing it costs the ban-evasion control permanently.

---

#### Row 25 — RULING: "operator-deleted, no automated clock" is **not defensible**, and the reason is a sentence nobody would write

**The proposed shape, stated plainly, is: indefinite retention of photographs
of the inside of a student's room, on an unspecified number of laptops, with
no inventory of where they are and no event that ends it.** The reminder is
printed, the operator is conscientious, and neither of those is a retention
period. A retention period is a *property of the system*; an intention is a
property of a person, and the charter metric this document is measured on is
"personal-data fields with no stated purpose or **retention period**". Row 25
as proposed would be the first row to fail that metric by design.

**Three grounds, in descending order of how much they bind us today.**

1. **The notice, which binds now and is not a DPDP question at all.**
   `COPY-DECK.md` v1.4 withdrew *"Everything else goes now"* because it was
   false, and replaced it with an **enumeration** of what survives — forced by
   `tests/e2e/test_deletion.py::test_the_disclosure_does_not_claim_more_is_deleted_than_is`.
   That enumeration is a representation to the student. These copies are not
   in it. So there are exactly two lawful states: the copies die on a clock, or
   the card gains a line. **Write that line and the answer falls out of it** —
   *"A staff member may still have copies of your photographs on their own
   computer. We don't know how many, or where, and nothing deletes them."* No
   one would ship that sentence, and a thing you cannot disclose is a thing you
   should not be doing. Under CP (E-Commerce) Rules r.4(3) an inaccurate
   representation about the service is an unfair trade practice **today**,
   without waiting for 13 May 2027.
2. **DPDP s8(5) and r.6(1) — possession, not location.** A file on an
   operator's laptop is personal data in the Data Fiduciary's possession; the
   operator is us. r.6(1) requires reasonable security safeguards *for data we
   hold*, and §7's own standard — access logged, retention bounded, deletion
   mechanical — does not stop at the object-store boundary. The access log
   (r.6(1)(c)) shipped. It is the half that tells you the copy exists; it does
   nothing about how long it lives.
3. **DPDP s8(7) — the purpose is served the moment the decision is logged.**
   Erasure is owed when the purpose is no longer served. The purpose here is
   one person looking at one listing once. There is no r.8(3) floor to point
   at: r.8(3) preserves the *record and the logs*, and the record is row 9's
   object plus the `audit_log` row, both of which survive untouched. **A
   working copy is not the record and cannot borrow its retention.** Citing
   row 9's one year for these would be the error rule 12 warns about — a
   control that guarantees a *state* (the record is kept) does not thereby
   license a *copy*.

**Uncertainty: LOW on the conclusion, and it does not turn on a contested
reading.** DPDP Rules 6 and 8 commence 13 May 2027, so ground 2 and ground 3
are design-ahead; ground 1 binds today. **Counsel: NO.** This is not a question
to buy an opinion on. If counsel is ever asked about it, the question is
whether photographs of a domestic interior supplied for one purpose are
sensitive enough to warrant more than a 24-hour ceiling — i.e. whether my
answer is strict *enough*.

**The cheapest control that actually works**, and it is cheaper than the
conversation about it: a sweep of `bookhop-review-*` directories older than
24 hours, run **at the top of every `review_listings` invocation**, covering
`tempfile.gettempdir()` and any directory passed to `--photos`. No daemon, no
cron, no state file, no new table. The person who makes the copies is the only
person who runs this command, and they run it again tomorrow. `--photos DIR`
therefore writes into `DIR/bookhop-review-<random>/`, so **one** name rule
covers both modes (rule 11: one definition, not many copies).

**Residual, named rather than hidden** (rule 12: name the other layer). An
operator who uses `--photos DIR` once and never runs the command again is not
swept. The layer that catches *that* is the `personal_data_access_log` row —
we know which operator, which listing and when — so it is answerable on an
erasure request by asking one named person, rather than unanswerable. That is
a worse layer than a clock and it is the one case the clock does not reach.

**The upgrade that deletes this row rather than governing it.** Backend has
already named it: a moderation screen that streams the bytes to the reviewer's
browser. Then there is no second copy, no sweep, no row 25, and no residual.
**That is the real fix and this is the bridge to it.** Row 25 should be deleted
from this table, not amended, when that screen ships.

**Conformance (rule 9): `tests/contract/test_the_review_copies_expire.py`.**
Two tests, each asserting the control **exists** (`sweep_review_copies` is
importable — it fails by name, so you know which guard went missing) and that
its property **holds** (a 25-hour-old directory is gone after a run). Both
sides are rows: each test also asserts **a one-minute-old directory survives**,
because a sweep that satisfied only the first assertion is `rm -rf` on the
directory the moderator is working in. Both are `xfail(strict=True)` on **one
subject each**, not on the module, so a second defect cannot hide inside the
first — and strict means they **cannot pass silently**: the day the sweep
ships they turn XPASS-as-failure and force the marks off in the same commit.

**That day was the same day, and the mechanism did exactly what it was built
to do** (updated by cto, 2026-10-22). Backend built `sweep_review_copies`
within the hour; both tests turned XPASS-as-failure on their first run against
it and the marks came off in that commit. The surviving assertion is the one
that mattered: the 60-second-old directory lives, so the sweep is an **age**
and not a **name**.

**Status: built and asserted. P15 is closed.** The residual is unchanged and
is not closed — an operator who runs `--photos DIR` once and never runs the
command again is never swept, and the `personal_data_access_log` row naming
that operator and that listing is the layer that makes an erasure request
answerable rather than unanswerable.

*This paragraph previously read "specified and gated, and is not built", which
was true when written and false four commits later. It is corrected here
rather than left to be read as current — a status line is a claim with a
timestamp, and this document's own rule is that a claim contradicted by a
measurement is deleted, not footnoted.*

---

#### Rows 26–27 — RULING: the basis is consent, the conditions do apply, and **the erasure story is the blocker**

**Three questions were asked. The third answer outranks the first two, so it
goes first.**

##### (c) Erasure — a want survives deletion, nothing ever purges it, and the card does not say so

Measured, not inferred. `erase_account` → `_detach_listing_rows`:

- `requester` → `NULL`; **`requester_pseudonym` survives**, as it must — the
  transaction record has to keep referring to someone;
- an OPEN want → `status='WITHDRAWN'`, `closed_at=now`,
  `purge_due_at = now + 1 yr`;
- **`free_text_title` and `course_code` are not touched.**

So after a student deletes their account, BookHop still holds **the sentence
they typed** and **the course they typed it for**, under a pseudonym, with a
clock. Two things are then wrong with that, and they compound.

**First, nothing reads the clock.** `apps.accounts.services.purge_expired`
walks `email_login_tokens`, `idempotency_keys`, `personal_data_access_log`,
`jobs`, `django_session` and `user_tombstones`. `apps.listings.jobs.purge_media`
walks `listing_photos`. **No handler walks `book_requests`.** And
`PURGE_SKIP_LIST` is explicitly *"the explicit skip-list, as data. A table here
is one the purge job must never touch, **with the reason**, so a reviewer can
see that the omission is a decision."* `book_requests` is not in it either.
**The design splits every clocked table into purged-or-deliberately-skipped,
and this table is on neither side** — which is rule 10's corollary almost
word for word: where a rule splits a set, both sides are rows.

Worse, the clock is only *started* by withdrawal or erasure. **Nothing in the
product ever sets `status='EXPIRED'`** — the value is in the CHECK, in
`DATA-MODEL.md` §3 and in `REQUEST_STATUSES`, and no code path reaches it. An
OPEN want from a student who neither withdraws it nor deletes their account has
`purge_due_at IS NULL`: **not a long retention, no retention.** That is the
charter metric — *"personal-data fields with no stated purpose or retention
period"* — failing on the main journey of the pilot, and it is the same defect
row 25 was refused for four hours ago. I refused *"the operator will delete
it"*; I am not now accepting *"the student will withdraw it"*.

**Second, the deletion card does not enumerate it.** `COPY-DECK.md` v1.4
withdrew *"Everything else goes now."* and replaced it with an enumeration,
because `tests/e2e/test_deletion.py::test_the_disclosure_does_not_claim_more_is_deleted_than_is`
forces the enumeration to be true. `templates/delete_confirm.html` lists eight
items: transfers, chat, reports, the email hash, the account, the age check,
the audit line, the deletion record. **A want is none of them.** *"Books that
changed hands"* is `transfers`; a want is a book that did **not** change hands.

The v1.4 amendment's own words are the test: *"The card asserts only what it
enumerates, and the list is the assertion."* An enumeration that omits a
category is not a weaker claim than a totality claim — **it is the same false
statement, made by omission**, and under CP (E-Commerce) Rules r.4(3) an
inaccurate representation about the service is an unfair trade practice
**today**, without waiting for 13 May 2027.

**Two lawful states, exactly as with row 25: the text goes on a clock that
something actually honours, or the card gains a line.** Unlike row 25, here I
want **both** — because the want is genuinely useful to us for a year (R-01
is the measurement that tells us a campus is illiquid) and because there is no
sentence problem: *"Books you asked for, kept for a year without your name"*
is a line a student accepts when told. Row 25's test — would you ship the
disclosing sentence? — passes here, which is exactly why row 25's answer
(delete the data) is not this row's answer.

> **Copy flagged to design and frontend, not written here.** A ninth
> `erase.retained.*` item for wants, in both languages. **The §1.2 shape is
> already set by the existing eight:** mechanism, period, purpose, no
> reassurance. Mine is a finding about truth, not a draft.

##### (a) Lawful basis — **Consent (s6) under `account`**, and the difference from row 22 is the whole point

**Contract → Consent (s6) under the existing `account` purpose key** / s7(a) as
the narrow reading. **No new consent key.** A want is created by the student
asking for a thing; it is the service, not a secondary use of it.

I refused a withdrawable-consent basis for row 22 (`contact_pattern_flag`) on a
one-line thought experiment: *"the person with the strongest incentive to
withdraw is the person the flag exists to detect. A safety control whose
operation the subject can switch off is not a safety control."* **Rows 26 and 27
are the mirror image and that is why the answer flips.**

- Row 22 is data **about** the student, held **against** their interest, for our
  r.3(1)(b) duty. Withdrawal would defeat the purpose.
- Rows 26 and 27 are data **from** the student, held **for** their benefit.
  Withdrawal defeats nothing — it is the feature. **It is already built:**
  `DELETE /api/v1/requests/{id}` sets `WITHDRAWN` and starts the clock.

So the test is not "is it free text" or "is it sensitive"; it is **whose
interest the processing serves, and what breaks if the subject says stop.**
Nothing breaks here. Consent is the correct basis, it is withdrawable, and the
withdrawal mechanism shipped before the basis was written down — which is the
right order to be wrong in.

*Not consistent with row 28, deliberately.* Row 28 is a **right being
exercised**, and a right is not a purpose the subject can be asked to consent
to or withdraw from — the record of the correction request must outlive the
request. Three columns, three bases, and the splitting question is the same one
each time.

##### (b) Conditions — **truncation applies and is already breached. Access logging applies and has no reader yet, so it is inverted rather than asserted.**

Rows 21 and 23 carry *"truncation, access logging and aggregate-only display"*
because of a sentence in row 21 I still stand behind: *"a free-text box will
eventually contain a name, a phone number or a hostel room, because free-text
boxes always do."* `free_text_title` is a free-text box, it is now written on
**every** want rather than only the unresolvable ones (A-32), and it is the
**only** one of the four that is rendered back out of the database to a human.
The conditions apply. Taken one at a time, because they are not one condition:

**1. Truncation — APPLIES, and it is missing on one of two write paths.** This
is the finding I did not expect to make. `WantedForm` caps `title` at 300 and
`course_code` at 40. **`create_request` caps neither**, and
`POST /api/v1/requests` passes `body.get("free_text_title")` straight through:
the column is `TextField`, so the only bound on the API path is the request body
limit. **Two writers, one bound** — rule 11's failure mode exactly, and the
cheap fix is rule 11's answer: **the bound belongs in `create_request`, which
both writers already route through, not in the form that only one of them
uses.** The pattern to copy is twelve lines away in another app and was written
for this reason: `MAX_STATED_PROBLEM = 2000`, *"a free-text box with no bound is
a free-text box somebody pastes a database into."* Same sentence, same control,
same codebase, applied to the correction box and not to the want box.

**2. Access logging — APPLIES, and today there is nothing to log.** The
condition is about **staff** reading an identifiable student's words; the
`/wanted` render is the student reading their own, which owes no
`personal_data_access_log` row and would be noise if it wrote one. **I checked
for the staff reader and there is none:** `apps/listings/staff.py` does not
import `BookRequest`, and the EC-17 *"staff signal"* purpose that both `PRD.md`
and `JOURNEYS.md` claim for this column **is not yet implemented by anything.**

That makes the condition forward-dated, and rule 10 is explicit about what
happens next: *"a forward-dated test can skip **forever**. From outside, 'not
yet running' and 'running and passing trivially' are indistinguishable.
**Invert it.**"* So the condition is written as a **ruled path that must not
resolve**:

> **No staff or operator code path may read `book_requests.free_text_title` or
> `course_code` without writing a `personal_data_access_log` row and
> displaying in aggregate.** The guard is not "the log fires" — there is
> nothing to fire. The guard is **"`apps/listings/staff.py` does not touch
> `BookRequest`"**, and it is a *failure* the day that stops being true, which
> forces the log into the same commit as the first reader.

**3. Aggregate-only display — APPLIES to the staff reader, and NOT to the
student.** Row 21's aggregate rule exists because *"the real risk here is not
the regulator; it is a staff member reading what an identifiable student
searched for."* A-32 is the opposite operation: the student reading their own
words. **A-32 is right and I am not qualifying it** — *"the gate was never
meant to stop a student seeing their own words"* is correct, the row is scoped
to the requester's own pseudonym, and subject access is a **right** (s11), not
a leak. The condition binds the EC-17 staff view when it is built.

**Conformance (rule 9): `tests/contract/test_the_inventory_covers_the_schema.py`.**
Five tests, each asserting a control **exists** (so it fails by name) and that
its property **holds**:

| Test | Asserts | Today |
|---|---|---|
| `test_every_free_text_column_has_an_inventory_entry` | §7.1's registry covers the live schema **in both directions** — a column with no entry fails, and an entry for a column that no longer exists fails too, so the registry cannot rot. **Asserts its own reach:** the measured column set is non-empty and every entry resolved | **green** (it is why row 28 exists) |
| `test_an_erased_want_is_purged_when_its_clock_runs_out` | A due `book_requests` row's text is NULL after both purge handlers run — **and** a not-yet-due row's text survives, because a sweep that only satisfies the first assertion is `DELETE FROM book_requests` | `xfail(strict=True)` |
| `test_the_want_is_on_one_side_of_the_purge_split` | `book_requests` is either walked by a purge handler or named in `PURGE_SKIP_LIST` **with a reason** | `xfail(strict=True)` |
| `test_the_deletion_card_enumerates_the_want` | A ninth `erase.retained.*` key for wants exists in the shipped template. Keyed on **a named msgctxt, not a keyword**, so it cannot go green on a reword | `xfail(strict=True)` |
| `test_the_want_box_has_a_bound_on_every_path` | `create_request` refuses an over-long title — **the service, not the form**, because the form is only one of two writers | `xfail(strict=True)` |
| `test_no_staff_path_reads_the_want_text` | **Inverted guard.** `apps/listings/staff.py` does not touch `BookRequest`. Green today and **designed to go red** the day the EC-17 staff view lands without its access log | **green** |

Every `xfail` is `strict=True` and on **one subject each**, never on the
module, so a second defect cannot hide inside the first — and strict means they
flip to failure the day the fix ships and force their own marks off, which is
what happened to row 25's pair within the hour.

**Uncertainty: LOW on all three answers.** The basis question is settled by
whose interest the processing serves. The disclosure ground binds **today**
under r.4(3) and does not wait for DPDP. The retention grounds (s8(7), r.8(3))
commence 13 May 2027 and are design-ahead, but the clock has to exist before
then or the data it would have bounded is already a year old. **Counsel: NO on
all three.** This is not a question to buy an opinion on.

---

**Standing rules for the CTO, derived from the table:**
- **Every new personal-data field needs a row here before it ships.** The charter
  metric is "personal-data fields with no stated purpose or retention period".
  A field without a row is a compliance defect by definition. **And a *copy* of
  a field is a field** — row 25 exists because a rendering step put a student's
  photographs somewhere no row covered. **Rows 21–24 close
  the four fields routed by `DATA-MODEL.md` §11.1 and ADR-001 §7.4.**
- **"Delete my account" never means `DELETE FROM users`.** It means: purge rows
  1–9 and 15, pseudonymise 10–13, and leave 14 and 16–18 alone. Build it once,
  correctly. **Rows 21–24 under D-009:** row 21 is untouched by deletion (no
  actor key); row 22 follows row 11 (pseudonymised, not deleted, **and disclosed
  in the notice**); row 23 purges `note` and NULLs `user_pseudonym`, keeps the
  timings, **and needs a human to read the notes**; row 24 is a secret, not
  subject data. **Rows 26–28, added v1.4:** rows 26 and 27 are pseudonymised
  here and **then purged at `purge_due_at`** — that purge is **P16** and does
  not exist yet — and they **must be enumerated on the deletion card**, because
  a want is not a transfer, a message or a report; row 28 survives untouched,
  because it is the record that a right was exercised.
- **A free-text field is personal data whatever you intended to put in it**, and
  every one of them needs a **bound in the service that writes it**, an
  **access log on the first staff reader**, and **aggregate-only display to
  staff**. **There is no count of them in this document and there must not be
  one.** v1.3 of this section said *"there are now two free-text fields in the
  system"*; it was a hand-maintained number, it drifted the moment S2 added a
  field, and **both fields it counted are specified and unbuilt while three
  built ones had no row**. The question *"how many are there"* is answered by
  **§7.1 against the live schema**, not by a sentence. Rule 11: ask the
  property, do not enumerate the cases.

---

### 7.1 Field registry — the inventory's completeness, asserted against the schema

**This block is data, and
`tests/contract/test_the_inventory_covers_the_schema.py` is its reader.** The
test measures every free-text column in the live schema and asserts this
registry covers it **in both directions**: a column with no entry fails by
name, and an entry naming a column that no longer exists fails too. So the
registry cannot silently rot, and it cannot be satisfied by being longer than
the schema.

**Declared ceiling, in the same place as the list** (rule 11). The measured set
is *"a `TextField` that is nullable and has no `choices`"* — the shape of a box
something writes prose into. **It does not catch** a non-null `CharField`, a
`jsonb` column (`data_subject_requests.nominee` is personal data about a third
party and is governed by A-29, not by this test), a file's contents (row 25),
or a column that holds personal data in a structured type (`users.campus_id`).
**The layer that generalises is this table itself** — the standing rule is that
*every* new personal-data field needs a row, whatever its type; §7.1 mechanises
only the slice a schema read can see, and a green §7.1 is **not** a claim that
the inventory is complete, only that no free-text column is missing from it.

Each entry carries its own reason, so that fixing one never silently removes
the coverage of another.

```inventory
# column                                  -> row | NOT-PD: reason
book_requests.free_text_title             -> 26
book_requests.course_code                 -> 27
data_subject_requests.stated_problem      -> 28
users.email                               -> 3
users.display_name                        -> 1
users.password                            -> 4
user_tombstones.email_hash                -> 3
user_tombstones.salt_version              -> 24
campus_verifications.email_domain         -> 6
age_verification_events.note              -> 7
consents.user_agent                       -> 18
email_login_tokens.user_agent_family      -> 16
audit_log.object_id                       -> 17
audit_log.before_hash                     -> 17
audit_log.after_hash                      -> 17
audit_log.request_id                      -> 17
audit_log.user_agent                      -> 16
personal_data_access_log.request_id       -> 16
data_subject_requests.outcome             -> NOT-PD: a CHECK-constrained outcome code, text only by column type; the row it sits on is row 18's family
jobs.locked_by                            -> NOT-PD: a worker identifier generated by `new_worker_id`, never a person
jobs.last_error                           -> NOT-PD: a traceback, scrubbed of every payload value by `apps.core.jobs._scrub` before it is stored. If a subject's data reaches it that is a defect in the scrubber, not a missing row here — and the layer that catches it is `retention.purge`'s `jobs` limb
purge_log.job_run_id                      -> NOT-PD: a job run identifier. Its `purge_due_at` column records the *purged row's* due date, not this row's own clock, so this table is not a subject of §7's retention split
gate_authorisations.revoked_reason        -> NOT-PD: operational text about a campus gate written by staff, naming a decision and not a person
legal_entities.*                          -> NOT-PD-SUBJECT: BookHop's own registration data and the contact details of its officers in their statutory capacity, which E-Com r.4(1)(b) and IT Rules r.3(2)(a) require us to **publish**
books.isbn13                              -> NOT-PD: bibliographic data about a published work, shared by every copy of it
books.edition_label                       -> NOT-PD: bibliographic; an edition is a property of the book, never of the student holding it
books.publisher                           -> NOT-PD: bibliographic; the publisher is a company, and not a data principal
books.origin_country                      -> NOT-PD: bibliographic, and the r.4(10) country-of-origin evidence we are required to show
prescribed_texts.source_ref               -> NOT-PD: catalogue provenance, a syllabus citation
listing_photos.storage_key                -> NOT-PD: the locator for row 9's bytes, not the bytes. Row 9 governs the object; this column is what `purge_media` NULLs to prove it purged one
listing_photos.storage_token              -> NOT-PD: same as `storage_key`
```

---

## 8. What we must build — CTO-implementable list

Ordered so that each item is a discrete piece of work with a definition of done.

**8.1 Consent capture**
- A `consents` table: `user_id`, `purpose_key`, `notice_version`, `granted_at`,
  `withdrawn_at`, `mechanism`, `ip`, `user_agent`. Append-only; never update in
  place.
- Separate purpose keys at minimum: `account`, `listing_publication`,
  `location_proximity`, `chat`, `safety_moderation`, `notifications`.
  **No bundled "I agree to everything" checkbox.**
- **No pre-ticked boxes anywhere** (E-Com r.4(9) — in force now, not 2027).
- **Withdrawal must be as easy as granting** (DPDP r.3(c)(i)): a settings toggle
  per purpose, not an email request. Withdrawal writes `withdrawn_at` and
  triggers the downstream stop.
- Notice version is immutable and archived, so we can show what a user agreed to
  on a given date.

**8.2 Notice copy — content requirements (counsel drafts the words)**
- A **standalone** privacy notice, separately presented and independently
  understandable (DPDP r.3(a)). Not a section of the Terms.
- **Itemised** list of personal data — §7's table is the source of truth
  (r.3(b)(i)).
- Specific purposes per item (r.3(b)(ii)).
- Links for: **withdraw consent**, **exercise rights**, **complain to the Data
  Protection Board** (r.3(c)).
- **Must state plainly:** transaction records, chat and logs are retained for one
  year after deletion because the law requires it (r.8(3)). Users should learn
  this from the notice, not from a support ticket.
- English plus Tamil. (DPDP's Eighth Schedule language right commences 13 May
  2027, but a Chennai campus product should be bilingual regardless, and
  design-director already owns EN/TA copy.)
- A **separate, short handover-safety notice** in the handover flow — guidance,
  never a warranty (§5.5).

**8.3 Deletion flow**
- Self-service, in-product, no email required.
- Implement as **tombstone + purge**, per §7: purge rows 1–9, 15; pseudonymise
  10–13; preserve 14, 16–18.
- Pseudonymisation must be **one-way** — the retained record must not be
  re-identifiable from itself.
- A scheduled job that **erases the 1-year-retained data on schedule**. Retaining
  beyond the purpose without a legal basis is its own breach. Build the expiry
  job at the same time as the retention, not later.
- Deletion requests and outcomes are logged in the consent/audit trail.
- **Acceptance test:** delete a test account; confirm the transaction record
  survives, is pseudonymous, and cannot be re-linked to the deleted identity.

**8.4 Grievance and takedown**
- Publish **Grievance Officer** name, designation, email and phone, and a
  physical address (IT Rules r.3(2)(a); E-Com r.4(2), r.4(4)).
- In-product complaint form issuing a **ticket number** (E-Com r.5(3)(b)) and an
  **acknowledgement within 24 hours** (IT Rules r.3(2)(a)(i)).
- SLA timers enforced in the system, not in a spreadsheet:
  **2 hours** (r.3(2)(b)), **3 hours** (r.3(1)(d)), **24 hours** acknowledge,
  **36 hours** (copyright r.75; IT Rules first proviso), **7 days** dispose
  (r.3(2)(a)(i)), **one month** redress (E-Com r.4(5)).
- From 1 Jan 2027: **give the complainant a copy of the complaint as recorded**
  (E-Com r.4(5) as substituted).
- An **on-call rota** covering the 2- and 3-hour clocks. This is an ops
  commitment, and it must exist before the pilot opens.
- A **copyright notice form** capturing r.75's requirements, with the 21-day hold
  and automatic restoration if no court order arrives.
- The **r.5(5) repeat-infringer record**, surviving account deletion.
- **Quarterly user reminder** of termination rights and user liability
  (IT Rules r.3(1)(c), substituted 2026) — a scheduled job, not a manual task.

**8.5 Audit trail**
- Append-only, tamper-evident log of: consent grants and withdrawals; age
  verification decisions (reviewer, method, timestamp); moderation actions;
  takedowns and restorations; disclosure of seller details under the r.5(3)(a)
  proviso; data access by staff; deletion executions.
- **Logs retained one year in India, NTP-synced to NIC/NPL** (r.6(1)(e);
  r.8(3); CERT-In).
- **Access to personal data must itself be logged** — r.6(1)(c) requires
  "visibility on the accessing of such personal data".
- Encryption, masking or tokenisation of personal data at rest (r.6(1)(a)).
- **A signed data-processing contract with every vendor** that touches personal
  data (r.6(1)(f)). Hosting, SMS/OTP, analytics, object storage, error tracking.
  **Each one is a Data Processor.** No vendor goes live without it.

**8.6 Breach runbook**
- **T+0** detect → log the detection timestamp. "Becoming aware" is the clock
  start and it will be scrutinised.
- **T+6h: report to CERT-In** (the binding clock today).
- **T+immediate: notify each affected Data Principal** with all five Rule 7(1)
  elements (nature/extent/timing; consequences for her; mitigation done and in
  progress; safety steps she can take; a named contact).
- **T+immediate: initial Board intimation** — nature, extent, timing,
  **location**, likely impact (r.7(2)(a)). *From 13 May 2027.*
- **T+72h: detailed Board report** — causes, mitigation, findings on who caused
  it, remedial measures, **and a report on the intimations given to Data
  Principals** (r.7(2)(b)). *From 13 May 2027.*
- Pre-written templates for all four communications, held in the repo.
- **Rehearse it once before the pilot opens.** An unrehearsed runbook is a
  document, not a capability.

**8.7 Age gate**
- DOB as a date field; **server-side** rejection under 18; never a checkbox.
- Logged human review of the age declaration at pilot scale (reviewer, outcome,
  timestamp).
- **No PAN, no Aadhaar, no ID document uploads.**
- Store the adult-status boolean + method + timestamp; **purge the DOB after
  verification**.
- A documented procedure for a discovered minor: suspend, erase, log.
- **Note the POCSO mandatory-reporting duty** if a minor is involved in a safety
  incident (IT Rules r.3(1)(c)(iii)).

**8.8 Product guardrails that are compliance controls**
- **No struck-through "was/now" prices** (avoids E-Com r.4(13) entirely).
- **No promoted or boosted listings** at pilot (avoids r.4(12)).
- **Ranking parameters documented in descending order of significance** before
  launch (r.5(3)(f), r.4(11)(c)).
- **Pre-set public handover points**; no free-text addresses; **no seller
  address displayed** (§2.4, §5.5).
- **Inspect-before-pay as an explicit step** in the handover flow (§2.4(ii)).
- **Copy review for safety and verification language**: "seller-stated
  condition", not "BookHop verified"; "meet in a public place", not "safe
  handover" (§2.5, §5.5).
- **Business-seller volume flag** built now, threshold set later (§2.4).
- **No generative AI in listing creation without re-review** (§5.1).
- **Credit design (c) only**: an ordinal trust level, never a denominated
  redeemable balance (§3.3).

---

## 9. Counsel questions — ask exactly these

**Indian technology / consumer / payments counsel:**

**Q1 (pilot).** Draft and review: the standalone privacy notice (DPDP r.3
compliant), user terms, seller terms including the **r.5(2) accuracy
undertaking**, the limitation-of-liability clause, and the Grievance Officer
appointment. *Constraints: no fund custody (D-004); no safety warranties; no
seller addresses published.*

**Q2 (pilot).** For an adults-only platform that processes **no** children's
data, what standard of diligence satisfies DPDP s9 and Rule 10 in establishing
that a user is 18+, given that Rule 10 prescribes a method only for verifying a
**parent**? Is a stored date of birth with a server-side block plus a logged
human review defensible? Does Fourth Schedule Part B item 6 cover that
processing? What is our exposure if a 17-year-old defeats the gate — and does
that change if we knew the campus population includes minors?

**Q3 (before G4).** How do we reconcile a Data Principal's **s12(3) erasure
right** with the **Rule 8(3)** one-year minimum retention of personal data,
traffic data and processing logs? Is a tombstone-plus-pseudonymisation model
compliant, and what must the notice say about it?

**Q4 (pilot — HIGH PRIORITY).** Do the Consumer Protection (E-Commerce) Rules
2020 (as amended by **G.S.R. 789(E)**, in force 1 Jan 2027) apply to a C2C
used-goods marketplace where (i) the seller is a natural person acting in a
personal capacity within the **r.2(1) proviso**, (ii) no shipping occurs, and
(iii) payment is in cash between users offline? Specifically: **does r.5(3)(a)
oblige us to publish an individual seller's geographic address**, given that
r.3(1)(k) defines "seller" by reference to **s2(37) CPA 2019 ("in the course of
business")**? Is a reviewed, logged, post-purchase disclosure under the
r.5(3)(a) proviso sufficient? And at what volume does an individual seller
become "regular or systematic" and lose the proviso?

**Q5 (pilot).** Does **r.6(3)** (no refusal to take back defective or
misdescribed goods) apply to an individual C2C seller of a used book, and if so
how is it discharged when the platform holds no funds? Is a documented
inspect-before-pay handover an adequate return/refund policy under
**r.5(3)(c)**?

**Q6 (before G4).** At what point does BookHop's condition grading, edition
matching or trust badging make it a **"product seller" under s2(37) CPA 2019**,
or a "product service provider", so that **product liability under Chapter VI**
attaches? What specific wording keeps us on the hosting side of that line?

**Q7 (before any credit release — HIGHEST PRIORITY).** Credit design (b):
earned by surrendering a book, **never purchasable for money, never
transferable, never redeemable for cash**, redeemable only for a book listed by
another user on BookHop. (i) Is it a **PPI** under **MD-PPI 2021 ¶2.8**? (ii)
Can it be a **Closed System PPI** under **¶2.1** given that the book is supplied
by a third-party user and not by BookHop? (iii) What weight should we give the
**draft MD 2026 ¶4.1 Explanation (ii)**, which excludes "marketplace" (defined
at ¶4.1(d) in terms that describe BookHop) from the own-goods carve-out? (iv)
Does issuing it without authorisation risk **s4 PSS Act 2007**? (v) Does a
redemption obligation raise any issue under the **Banning of Unregulated Deposit
Schemes Act 2019**? (vi) Would an **expiry** and a **discretionary,
availability-subject** redemption materially improve the position? *We are not
asking whether we can call it points. We are asking whether this instrument
falls inside or outside ¶2.1 and ¶2.8.*

**Q11 (pilot).** A campus MoU template covering: permission to operate on
premises; any sharing or confirmation of student enrolment data by the
institution and its lawful basis; use of the institution's name and marks;
liability allocation for incidents on premises; and termination.

**Q12 (before G4).** Does BookHop's handover design — suggesting meeting points,
times and counterparties — create an **assumed duty of care** for physical
safety? What limitation-of-liability drafting is enforceable under Indian law
(noting that negligence liability generally cannot be excluded), and what
product or copy changes most reduce the exposure?

**Indian chartered accountant / tax counsel:**

**Q8 (before any payment collection).** (i) Is BookHop "required to collect tax
at source" under **CGST s52** if the underlying sellers are non-business
individuals whose disposals are not **"supplies" under s7** (not in the course
or furtherance of business)? (ii) If not, does **s24(x)** compulsory
registration ever bite, even after we collect sale consideration through a
payment aggregator? (iii) At what point does our own commission income require
registration under **s22(1)** — ₹20 lakh, Tamil Nadu? (iv) Confirm the current
TCS rate (0.5% per Notification 15/2024-CT, 10 July 2024) and GSTR-8 mechanics.

**Q9 (= C11 in `INCORPORATION-AND-BLOCKERS.md` §5; at Gate B, inside the C1–C3
engagement — re-drafted v1.1).** *Ask tax counsel, not only a CA. Re-drafted
around a named circular so this is a narrow opinion rather than an open
question — see §4.3.1.*

Facts: BookHop will operate a free matching service for used prescribed
textbooks between students on one campus. It records a **seller's asking price
fixed at intake and immutable**, and a **completion boolean** (two
confirmation timestamps). It records **no settled, agreed, offered or accepted
amount anywhere**, enforced by a database trigger and a CI schema test. Buyer
and seller agree price between themselves and settle in **cash, hand to hand**.
BookHop receives nothing from anyone.

**On negotiability, stated precisely, because this limb matters and we must not
overstate it to you** *(corrected v1.2 — the earlier draft of this paragraph
asserted it as a fact about a built product, which it was not)*: price is
negotiated between the two students, and **the specification requires the
product to say so** — the number is labelled *"Seller's asking price"*
throughout and never *"Price"*; the copy states that the two students agree the
actual price between themselves and that **BookHop does not know and does not
record what is actually paid**; there is **no numeric offer, counter-offer or
bid control anywhere in the interface**, and negotiation happens in the
students' own words in a message thread. **This is a frozen design
specification** (`design/COPY-DECK.md` §1.6 and §3.1, `design/SYSTEM.md` §4.15)
**enforced by a copy test in the build pipeline. At the date of this brief it is
specified and tested, not yet observed in use by students** — a user test with a
pre-committed failure threshold is scheduled, and if it shows students read the
asking price as the price, we will tell you. **Please opine on the specification
as described, and tell us if your answer depends on behaviour we have not yet
measured.**

(i) **Does CBDT Circular 20/2021 (25 Nov 2021, e-auction services) apply to
these facts**, such that **s393(1) Table Sl. No. 8(v)** (and s194-O for
pre-April-2026 periods) does not attach at all? We satisfy five of its six
limbs on their face; the sixth — *"the client deducts tax under the relevant
provisions… other than Section 194-O"* on the operator's own fee — we cannot
satisfy because **we charge no fee**. Is that fatal given the circular's closing
sentence, or is a limb directed at fee income inapplicable to a platform with
none? (ii) Does **Circular 17/2020 para 4.3** — no liability where the platform
*"has no involvement in transactions"* — reach the same result independently?
(iii) **Does Note 3 to the s393(1) Table, deeming a direct buyer-to-seller
payment to be paid by the operator, supply a *quantum* as well as a payment?**
Our reading is that it deems the payment only, and that **"gross amount of such
sale"** presupposes a known consideration that we do not have; **Circular
20/2023 supplies no fallback measure** where the operator does not know the
price. (iv) **Could an asking price plus a completion boolean be read as a
determinable gross amount**, and what specifically would make that reading
available — immutability of the asking price? UX that implies a fixed price?
Volume? **This is the question we are most worried about.** (v) If a deduction
obligation does arise, how is it discharged by an operator that receives no
money, and can we be an **assessee-in-default under s398** for tax we had
nothing to deduct from? (vi) Can we rely on the **₹5 lakh individual/HUF relief
at s393(4) Table Sl. No. 11** **without** holding PAN or Aadhaar, given it is
expressly conditional on PAN or Aadhaar being furnished? We will not collect
either. (vii) **Do Circulars 17/2020, 20/2021 and 20/2023 retain binding force
after 1 April 2026?** They were issued under **s194-O(4)** and bound the operator
under **s194-O(5)**; we could not locate a re-enacted guidelines power attached
to Sl. No. 8(v). **s536(2)(j)** carries circulars forward *"so far as not
inconsistent"* — but under which corresponding provision, and with what binding
effect? (viii) Confirm the rate (0.1%) and the provision mapping.
(ix) **What is the minimum data we must hold to be compliant, given that we are
actively trying not to hold PAN or Aadhaar?**

**Q10 (pilot).** *(Technology counsel, narrow.)* Confirm the current text and
timelines of **Copyright Rules 2013 r.75**, whether it applies to a marketplace
hosting listings (as opposed to transient/incidental storage under
**s52(1)(b)–(c)**), and review our notice-and-takedown SOP and seller
undertaking for safe-harbour preservation under **IT Act s79**.

---

## 10. Open items in this document — honest ledger

Per the evidence standard, these are claims I could not close from a primary
source on 2026-10-21. **They are P13.**

**v1.1: one item closed, one item re-stated, three items added.** The table below
is the current state.

| Item | What is unverified | Impact if wrong |
|---|---|---|
| ~~CERT-In Directions 2022~~ | **CLOSED 2026-10-21.** Direction text and the FAQ both extracted from the CERT-In PDFs. §5.2, §5.2.1 | — |
| **CERT-In FAQ Q35 scope** *(new)* | Whether *"may be stored outside India **also**"* permits exclusively-foreign storage or only an additional copy. **Commentary splits.** | **None for BookHop** — our primary copy is in India on either reading. Recorded because someone will cite Q35 for a broader proposition later |
| **Circulars' binding force post-1-Apr-2026** *(new)* | Whether Circulars 17/2020, 20/2021, 20/2023 — issued under s194-O(4), binding under s194-O(5) — retain binding force under the 2025 Act, which appears to have no re-enacted guidelines power at Sl. No. 8(v). s536(2)(j) carries them *"so far as not inconsistent"* | **Material.** It is the reason §4.3.1 is MODERATE and not LOW, and it is Q9(vii) |
| **Circular 20/2021 and 17/2020 text** *(new)* | Read from near-primary reproductions (taxwink, lkslaw, abcaus). **incometaxindia.gov.in returned HTTP 403.** Official PDFs not reached | The §4.3.1 upgrade rests on them. Counsel reads the official text as part of Q9 |
| s194-O construction *(re-stated, not closed)* | **No circular, FAQ or decision determines the gross amount for an operator that records only an asking price.** This remains a genuine gap after a real search. **It runs in our favour** — the charge cannot be computed — but it is unsettled | §4.3.1; Q9(iii)–(v) |
| Copyright Rules 2013 r.75 | 36-hour takedown, 21-day hold, scope — commentary only | Takedown SOP timings |
| GST rates and thresholds | 0.5% TCS; ₹20L/₹40L; Notifications 15/2024, 34/2023, 65/2017 — commentary only; CBIC not reached | Tax position (CA closes this) |
| s194-O rate and 2025-Act mapping | 0.1%; s393(1) Sl. 8(v) **confirmed 2026-10-21**; **corrected: the ₹5 lakh relief is at s393(4) Sl. No. 11, not inside 8(v)** (§4.3.1). Rate still commentary-only; incometaxindia.gov.in returned 403 again | Tax position (CA closes this) |
| IT Amendment Rules 2026 | Read from a reproduction of G.S.R. 120(E), not the eGazette | Grievance and takedown clocks |
| TN Shops & Establishments | Applicability threshold and filing window — conflicting commentary | Registration obligation |
| SDF designations | "None notified" rests on absence of search results, which cannot prove a negative | Low — we are far below any plausible threshold |
| DPDP commencement advancement | A proposal to cut 18 months to 12 is reported but not notified | **High if notified — would move core obligations to 13 Nov 2026** |

---

## 11. Verdict

> **Scope note (v1.5).** This verdict is for the **campus pilot**: verified
> adults at 2–3 Chennai campuses. It is **not** the verdict for a closed test
> among personally-known adults, which is a different scope with a different
> per-field answer — see `company/evidence/CLOSED-TEST.md`. Do not read
> P1–P16 as the requirement set for twelve friends, and do not read
> CLOSED-TEST.md as relaxing anything here.

### v1.1 amendment — what D-009 changed, stated plainly

**D-009 is within the founder's authority and I am not re-litigating it.** It
did, however, void the gate this verdict was written against: Gate A was a
14-day paper concierge pilot with a human operator and no software, and it no
longer exists as designed. **The revised gate sequence is in
`ops/INCORPORATION-AND-BLOCKERS.md` §3, rewritten in the same pass as this
document.** The headline: the gates are now **build → first real user →
discovery opens → public**, and the pivotal legal event moved from *"when can a
student browse"* to *two* events, because collecting a real student's personal
data and letting students see each other's listings are different triggers with
different obligations.

**D-009 created three new exposures. The charter requires me to say so rather
than soften them, and to say which are mitigated.**

1. **A durable personal-data estate under a regime that changes on a fixed
   date.** A 14-day spreadsheet purged at day 30 had essentially no DPDP tail;
   it would have been finished long before 13 May 2027. **An app that goes live
   in 2026 and is still running on 13 May 2027 must be compliant on that date,
   with no transition period, carrying whatever it has accumulated.** This is
   the largest new exposure. **It is also the best-mitigated**: the CTO has
   specified consent capture, tombstone-plus-purge, the expiry job and the
   access log in the first slices rather than as retrofits, which is exactly the
   right response and is why L10 is a build item rather than a crisis.
2. **Intermediary status and safe-harbour exposure arrive earlier, and the
   copyright control got weaker.** The paper pilot had a human operator who saw
   every book before anyone else did. **An app has a moderation queue, which is a
   strictly weaker control than a person holding the only list.** §5.3 already
   rates pirated textbooks as the highest-probability content risk and D-008
   recorded that the scope cut concentrated it; **D-009 weakens the control as
   well.** Therefore: `listings.suspect_reproduction_flag` routing to
   `PENDING_REVIEW` must be **on by default and must not be a flag anyone turns
   off for throughput**, and the r.5(5) repeat-infringer record must exist before
   the first real listing, not before the first takedown.
3. **The s194-O evidence improved — for whoever disagrees with us.** D-009 did
   not change the §4.3.1 argument. It did change the quality of the record: a
   30-row spreadsheet pseudonymised at day 30 is a poor basis for a reassessment;
   **a Postgres database with `transfers.completed_at` and
   `listings.asking_price_paise`, retained a year, joinable by a documented
   metric query in a frozen architecture document, is an excellent one.** That is
   a genuine new exposure, it is the honest answer to "did D-009 create any",
   and it is a reason to buy Q9/C11 at Gate B rather than drift past it.

**And one exposure D-009 removed, recorded because rigour runs both ways.** The
paper pilot's single highest-probability incident was a shared spreadsheet of
student names and phone numbers, held in one person's account, outside any
logging or retention regime, with a 6-hour CERT-In clock attached and no
technical means of honouring a deletion request. **Personal data in one Postgres
with an access log, a purge job and a tested restore is better on that axis than
the spreadsheet was.** D-009 is not uniformly worse for privacy, and saying
otherwise would be dishonest.

**Nothing in D-009 relaxes a single constraint in this document.** No constraint
below has been loosened because the founder is in a hurry, and P14 in particular
is now enforced more strongly than v1.0 contemplated (§4.3.2).

### The verdict itself

**v1.3: the condition set is P1–P15.** P15 is new and it is the cheapest item
on the list — a sweep, no new table, no counsel. It is nonetheless a **pilot**
blocker and not a launch one, because at pilot `LISTING_REVIEW_ALL=true` means
the path runs on every listing from day one. Everything below reads P1–P15.

**v1.4: the condition set is P1–P16.** P16 is four small parts and no counsel,
and it is a pilot blocker for the same reason P15 was: the path runs on every
student from day one. **Part (iv) — one line on the deletion card — is the
only part that binds *today*,** under CP (E-Commerce) Rules r.4(3); the other
three are design-ahead for 13 May 2027 and must exist before then, because a
clock added later does not bound the data it would have bounded. Everything
below reads P1–P16.

**Pilot: NOT BLOCKED, conditional on P1–P14.** None of P1–P14 is a research
problem; all are build or appoint or verify tasks with known definitions of
done. The regulatory position for a cash-settled, adults-only, no-shipping,
no-credit campus pilot is **workable**, and it is workable largely because the
DPDP operative provisions do not commence until 13 May 2027, which gives us an
unusual and temporary amount of room. **Use it to build correctly rather than to
defer.**

**Public launch: BLOCKED until L1–L14**, and L1 (counsel review) is
non-negotiable under README §7 and under this charter.

**Credit designs:** **(a) blocked** — it is a PPI and it breaches D-004
independently. **(b) blocked pending counsel** per D-003, and it is outside the
closed-system carve-out even though it is not plainly a PPI. **(c) cleared** —
an ordinal, non-redeemable reputation signal is not a PPI and raises no RBI
issue.

**This is not legal advice. A qualified Indian lawyer must review BookHop's
terms, privacy notice, seller arrangements and credit design before public
launch, and a qualified Indian tax adviser must review §4 before any fee or
payment is collected.**
