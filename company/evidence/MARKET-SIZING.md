# Market Sizing — The Chennai Denominator

Owner: `market-finance` · Version: v1.0 · Date: 2026-10-21
Evidence standard: `company/README.md` §8. Every number below carries a source
URL and access date, or is tagged `ASSUMPTION:` with reasoning and the test
that would replace it.

Companion: `company/finance/MODEL.md` (the TAM/SAM/SOM model) and
`company/finance/model.csv` (editable driver sheet).

---

## 0. Headline

| Layer | Number | Confidence |
|---|---|---|
| India higher education, regular mode | **3,96,64,479** | **Sourced** (AISHE 2023-24) |
| Tamil Nadu, all modes | **35,77,047** | **Sourced** (AISHE 2023-24) |
| Tamil Nadu, regular mode | **31,93,831** | **Sourced** (AISHE 2023-24) |
| Chennai metro (4 districts), regular mode | **3.2 – 6.5 lakh**, base 4.6 lakh | `ASSUMPTION:` — **no official source exists** |
| Chennai metro — sourced floor, 28 named campuses | **1,97,186** | **Sourced**, institution by institution |
| All 30 named campuses incl. 2 multi-campus filings | **3,12,085** UG+PG (+19,299 PhD) | **Sourced**, but 2 rows are not Chennai-only |
| 3 pilot campuses (Anna Univ depts + Loyola + DG Vaishnav) | **32,197** | **Sourced** |

**The single most important finding in this document:** there is no published
Chennai-district or Chennai-metro higher-education enrolment figure. It does not
exist in AISHE, in the NIRF corpus, or in any Tamil Nadu government release we
could reach. §4 states the gap, the proxies, their error bars, and the three
primary requests that would close it. We did not invent a denominator to fill it.

---

## 1. What replaced the four founder planning assumptions

The founder supplied four numbers and instructed that they be replaced. Each line
below says what replaced it and where that replacement lives.

### 1.1 "5 lakh Chennai students"

**Replaced by:** a three-layer denominator — a sourced national/state figure, a
sourced campus-by-campus floor, and an explicitly-tagged proxy range for the gap
between them.

- Sourced: Tamil Nadu regular-mode enrolment **31,93,831** (AISHE 2023-24, Table 6(a)).
- Sourced: **1,97,186** UG+PG across 28 named Chennai-metro campuses (§3), rising to
  **3,12,085** if the two non-separable multi-campus filings (SRM IST, VIT) are included.
- `ASSUMPTION:` Chennai metro (Chennai + Chengalpattu + Tiruvallur + Kancheepuram)
  regular-mode enrolment of **3.2 / 4.6 / 6.5 lakh** low/base/high. See §4 for the
  two proxies and why neither is good.

**Verdict on the founder's figure:** 5 lakh falls inside the plausible range, so it
was not wrong — but it was never the right number to build on, for two reasons.
First, it is a *metro* figure, not a Chennai-district figure, and the pilot is
Chennai district. Second, and more important, enrolment is not the addressable
base. After filtering for adults and for courses where physical books actually
change hands, the base case addressable population is **2,62,200**, not 5 lakh
(`MODEL.md` §3). The error was not the magnitude; it was using enrolment where
addressable population belongs.

### 1.2 "20% participation"

**Replaced by:** two separate drivers, because "participation" conflated two very
different things.

- `signup_rate_y1` — share of the addressable population that registers in year one.
  Base **15%**.
- `activation_rate` — share of registered users who complete at least one transfer.
  Base **30%**.

Product: **4.5%** of the addressable population completes a transfer in year one,
against the founder's implied 20%. A registration is not a transaction, and in a
cold-start two-sided marketplace the gap between them is the whole problem.
Clankart's own numbers support the split: 25,000+ registered students pan-India
against roughly USD 1,200/month of revenue
([Starter Story, 2023-01-02](https://www.starterstory.com/stories/clankart),
accessed 2026-10-21) — that is a registration base with very little transacting
behind it.

### 1.3 "2 book transfers per student per year"

**Replaced by:** `transfers_per_active_yr`, base **1.8 transfers per *active
participant* per year** — not per enrolled student.

The unit matters more than the value. Carried through the funnel, 1.8 per active
participant equals **0.046 transfers per enrolled student per year**. The founder's
figure, read as 20% × 2, implies **0.4 per enrolled student per year** — roughly
**9× higher**.

The driver is also capped by timing, not by willingness. Per the competitor audit,
campus supply and demand peak in **antiphase** — sellers release books at semester
end, buyers need them at semester start — leaving roughly **8 trading weeks a
year**. At the base case that is 1,487 transfers compressed into 8 weeks across
three campuses, or about 27 a day. This is modelled explicitly in `MODEL.md` §7
rather than smoothed into an annual average.

### 1.4 "Rs 300 average used-book value"

**Replaced by:** `avg_book_price_inr`, base **Rs 220** (band Rs 140 / 220 / 350),
tagged `ASSUMPTION:` — *and*, more consequentially, by the separation of book value
from cash value.

Rs 300 was being used as if it were revenue-bearing. It is not. After a 20% direct-swap
share (zero cash by construction) and a 15% gifting share within the remainder, only
**68%** of book value moved carries any cash at all. The model therefore reports
**book value moved** and **cash GMV** as two different lines that never meet
(`MODEL.md` §5). Platform revenue is a fraction of the second, not the first.

---

## 2. AISHE 2023-24 — what the report actually supports

Source: *All India Survey on Higher Education 2023-24*, Ministry of Education,
Government of India.
URL: https://cdnbbsr.s3waas.gov.in/s392049debbe566ca5782a3045cf300a3c/uploads/2026/07/202607131602421770.pdf
Accessed 2026-10-21. Text extracted locally with `pdftotext -layout`; table and
line references below are to that extraction.

| Figure | Value | Where in the report |
|---|---|---|
| All-India total enrolment, all modes | 4,50,01,123 | Table 6, "All India" row |
| All-India enrolment, **regular mode** | 3,96,64,479 | Table 6(a), "All India" row |
| Tamil Nadu total enrolment, all modes | **35,77,047** (M 18,16,574 / F 17,60,473) | Table 6, row 30 |
| Tamil Nadu, **regular mode** | **31,93,831** | Table 6(a), row 30 |
| Tamil Nadu, by institution type | Universities 8,69,323 · Colleges 25,02,003 · Standalone 2,05,721 | Table 6, row 30 (sums to 35,77,047) |
| Tamil Nadu, UG level, all modes | 27,51,939 | Table 6, row 30 |
| Tamil Nadu colleges | **2,983** (2,933 responded) | Table 4, row 30 |
| Tamil Nadu college density | 44 per lakh population aged 18–23 (narrative text says 43) | Table 4, row 30 / §2.1.2.2 |
| Tamil Nadu GER | 52.3 — among the highest in India | §2.1.2.2 narrative |
| Tamil Nadu rank by enrolment | 3rd (after Uttar Pradesh 72.7 lakh, Maharashtra 46.5 lakh) | §2.2 narrative |
| Tamil Nadu share of India regular-mode enrolment | **8.1%** | Derived: 31,93,831 ÷ 3,96,64,479 |

### 2.1 Why regular mode is the correct base

Distance, private and online enrolment — **3,83,216 students in Tamil Nadu**, the
difference between the two totals — are not on a campus and cannot participate in
a local handover. Every denominator in this document and in `MODEL.md` uses
**regular mode**. Using the 35.77 lakh headline instead would overstate the
addressable base by 12%.

### 2.2 What AISHE does NOT support

**AISHE 2023-24 contains no district-level enrolment table and no Chennai figure.**
This is a property of the report, not a gap in our search.

- The only district-level content is §2.1.2.1 and Box 2, "Top 10 Districts having
  Maximum Number of Colleges". Chennai is **not** in it. The tenth entry is Bhopal
  at 327 colleges.
- Box 3 gives a distribution of districts by college-count band but names no districts.
- Table 3 gives, per state, the count of districts with at least one institution —
  not enrolment per district.

**One genuinely useful bound comes out of this:** since Chennai does not appear in
the top-10 districts, **Chennai district has fewer than 327 colleges**. That is a
sourced ceiling, and it is consistent with the DCE directory count in §4.

---

## 3. Campus-by-campus enrolment (primary sources)

Method and caveats:

- Figures are the **"Total Students"** column of each institution's NIRF Data
  Capturing System submission, the same document whether served from
  `nirfindia.org` or the institution's own domain.
- **Academic-year convention, verified:** NIRF filings print no year on the strength
  table. The Ph.D header in the same PDF reads `Ph.D (Student pursuing doctoral
  program till 2023-24)` in NIRF'2025 filings and `...till 2024-25` in NIRF'2026
  filings. So **NIRF'2025 = AY 2023-24** and **NIRF'2026 = AY 2024-25**.
- **UG+PG columns are literal printed values. The UG+PG sums are our arithmetic**,
  not figures printed in the source.
- PhD headcount is listed separately and is **excluded** from the addressable base
  in `MODEL.md` (doctoral scholars are a negligible used-textbook cohort).
- All URLs accessed **2026-10-21**.

### 3.1 Technical and professional institutions

| Institution | UG+PG | PhD | AY | District | Source | Scope caveat |
|---|---:|---:|---|---|---|---|
| IIT Madras | 7,512 | 2,711 | 2023-24 | Chennai | [NIRF Overall IR-O-U-0456](https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Overall/IR-O-U-0456.pdf) | Single campus, all disciplines |
| Anna University (university departments) | 11,940 | 1,809 | 2023-24 | Chennai | [NIRF Overall IR-O-U-0439](https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Overall/IR-O-U-0439.pdf) | **Affiliated colleges excluded.** Filing does not state whether the 13 constituent colleges and 3 regional campuses are inside |
| SRM IST | 60,645 | 2,641 | 2023-24 | Chengalpattu + | [NIRF Overall IR-O-U-0473](https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Overall/IR-O-U-0473.pdf) | **Multi-campus, not separable.** Includes Ramapuram, Vadapalani, Tiruchirappalli, Delhi-NCR |
| VIT | 54,254 | 5,142 | 2023-24 | Vellore + Chennai | [NIRF University IR-O-U-0490](https://www.nirfindia.org/nirfpdfcdn/2025/pdf/University/IR-O-U-0490.pdf) | **Vellore + Chennai combined, not separable.** VIT Chennai files no separate NIRF submission |
| Sathyabama IST | 16,658 | 914 | 2023-24 | Chennai | [NIRF Overall IR-O-U-0474](https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Overall/IR-O-U-0474.pdf) | Single campus |
| SIMATS (Saveetha) | 13,987 | 1,507 | 2023-24 | Chennai | [NIRF Overall IR-O-I-1441](https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Overall/IR-O-I-1441.pdf) | All disciplines; UG[5y] 2,810 is the MBBS/BDS cohort |
| Panimalar Engineering College | 10,722 | 90 | 2024-25 | Tiruvallur | [NIRF'2026, own domain](https://www.panimalar.ac.in/assets/pdf/academics/nirf/PEC-NIRF_2026-Engineering.pdf) | Not Panimalar Institute of Technology |
| Vel Tech R&D Institute | 9,678 | 586 | 2023-24 | Tiruvallur | [NIRF Engineering IR-E-U-0489](https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/IR-E-U-0489.pdf) | **Engineering only** — no Overall filing exists |
| Dr. M.G.R. E&RI | 8,352 | 552 | 2023-24 | Chennai | Eng [IR-E-U-0461](https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/IR-E-U-0461.pdf) · Arch [IR-A-U-0461](https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Architecture/IR-A-U-0461.pdf) · Dental [IR-N-U-0461](https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Dental/IR-N-U-0461.pdf) | **Partial.** Three separate filings summed; misses pharmacy, allied health, arts & science |
| Rajalakshmi Engineering College | 8,177 | 374 | 2023-24 | Tiruvallur | [NIRF Engineering IR-E-C-16626](https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/IR-E-C-16626.pdf) | AY 2024-25 figure (9,345) exists but was read from an image render — not used |
| Saveetha Engineering College | 5,961 | 204 | 2024-25 | Kancheepuram | [NIRF'2026, own domain](https://saveetha.ac.in/wp-content/uploads/2026/02/SAVEETHA-ENGINEERING-COLLEGE20260216-.pdf) | Distinct institution from SIMATS |
| St. Joseph's College of Engineering | 5,868 | 185 | 2024-25 | Chennai | [NIRF'2026, own domain](https://www.stjosephs.ac.in/NIRF/NIRF2026/NIRF2026.pdf) | Not St Joseph's Institute of Technology |
| HITS (Hindustan) | 4,283 | 429 | 2023-24 | Chengalpattu | [NIRF Engineering IR-E-U-0454](https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/IR-E-U-0454.pdf) | **Engineering only** — institution-wide figure not found |
| BSA Crescent IST | 4,070 | 180 | 2023-24 | Chengalpattu | [NIRF Engineering IR-E-U-0445](https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/IR-E-U-0445.pdf) | **Engineering only.** Architecture adds 326 (AY 2022-23) |
| SSN College of Engineering | 3,877 | 489 | 2023-24 | Chengalpattu | [NIRF Overall IR-O-C-16604](https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Overall/IR-O-C-16604.pdf) | |
| **Subtotal** | **2,25,984** | **17,813** | | | | |

### 3.2 Arts and science colleges

| Institution | UG+PG | PhD | AY | District | Source |
|---|---:|---:|---|---|---|
| D.G. Vaishnav College | 10,910 | — | 2023-24 | Chennai | [NIRF College IR-C-C-43968](https://www.nirfindia.org/nirfpdfcdn/2025/pdf/College/IR-C-C-43968.pdf) |
| Loyola College | 9,347 | — | 2023-24 | Chennai | [NIRF College IR-C-C-44006](https://www.nirfindia.org/nirfpdfcdn/2025/pdf/College/IR-C-C-44006.pdf) |
| Ethiraj College for Women | 7,749 | — | 2023-24 | Chennai | [NIRF College IR-C-C-43902](https://www.nirfindia.org/nirfpdfcdn/2025/pdf/College/IR-C-C-43902.pdf) |
| Guru Nanak College | 7,227 | — | **2022-23** | Chennai | [NIRF College IR-C-C-43998](https://www.nirfindia.org/nirfpdfcdn/2024/pdf/College/IR-C-C-43998.pdf) |
| Madras Christian College | 6,898 | — | 2023-24 | **Chengalpattu** | [NIRF College IR-C-C-43965](https://www.nirfindia.org/nirfpdfcdn/2025/pdf/College/IR-C-C-43965.pdf) |
| The New College | 6,460 | — | 2024-25 | Chennai | [NIRF'2026, own domain](https://thenewcollege.edu.in/pdf/NIRF2026.pdf) |
| Stella Maris College | 5,681 | — | 2023-24 | Chennai | [NIRF College IR-C-C-43931](https://www.nirfindia.org/nirfpdfcdn/2025/pdf/College/IR-C-C-43931.pdf) |
| Queen Mary's College | 5,021 | — | 2024-25 | Chennai | [NIRF'2026, own domain](https://queenmaryscollege.edu.in/images/notifications/files/12:22:17pmNIRF_2026_DCS_Report.pdf) |
| Presidency College | 4,858 | — | 2023-24 | Chennai | [NIRF College IR-C-C-43921](https://www.nirfindia.org/nirfpdfcdn/2025/pdf/College/IR-C-C-43921.pdf) |
| Women's Christian College | 4,315 | — | **2022-23** | Chennai | [NIRF College IR-C-C-43946](https://www.nirfindia.org/nirfpdfcdn/2024/pdf/College/IR-C-C-43946.pdf) |
| MOP Vaishnav College for Women | 3,988 | — | 2024-25 | Chennai | [NIRF'2026, own domain](https://mopvc.edu.in/wp-content/uploads/2026/04/1.-COLLEGE-M.O.P.-Vaishnav-College-for-Women.pdf) |
| RKM Vivekananda College, Mylapore | 3,512 | — | 2024-25 | Chennai | [NIRF'2026, own domain](https://rkmvc.ac.in/wp-content/uploads/2026/04/NIRF-DCS-2026.pdf) |
| Pachaiyappa's College | 3,475 | — | 2023-24 | Chennai | [NIRF'2025, own domain](https://pachaiyappascollege.edu.in/assets/pdf/nirf/NIRF-2025_compressed.pdf) |
| University of Madras (departments) | 3,384 | 1,486 | 2023-24 | Chennai | [NIRF University IR-O-I-1357](https://www.nirfindia.org/nirfpdfcdn/2025/pdf/University/IR-O-I-1357.pdf) |
| SRM Arts and Science College | 3,276 | — | 2024-25 | **Chengalpattu** | [NIRF'2026, own domain](https://www.srmasc.ac.in/wp-content/uploads/2026/04/SRM-ARTS-AND-SCIENCE-COLLEGE20260402-1-1.pdf) |
| **Subtotal** | **86,101** | **1,486** | | | |

Notes on individual rows:
- **University of Madras**: the 3,384 is **PG only** — the university departments offer
  no UG programmes in the NIRF form. This is university-department enrolment, entirely
  separate from the 131 colleges affiliated to it.
- **Stella Maris**: the UG[3yr] row prints Male 0 / Female 4,600 / Total 4,603. The
  submission is internally inconsistent by 3 students; we report the printed total.
- **Pachaiyappa's** and **The New College** are men's colleges (Female column prints 0).
  Relevant to a trust/handover model with mixed-gender matching.
- **MCC and SRM A&S sit in Chengalpattu district**, not Chennai district — confirmed
  against the DCE directory. This matters for a pilot scoped to "Chennai campuses".

### 3.3 Affiliating-university structure (the part not in §3.1–3.2)

The campus tables above cover **single institutions**. Most Chennai students are in
*affiliated colleges*, which file no NIRF submission unless they rank.

| Figure | Value | Source | Caveat |
|---|---|---|---|
| Colleges affiliated to Anna University, **Chennai region** | **142** | [Anna University CAI, College Statistics 2023-24](https://annauniv.edu/cai/College%20Statistics-2023-24.pdf) | "Chennai region" = **10 districts** (Chennai, Chengalpattu, Kancheepuram, Tiruvallur, Vellore, Ranipet, Tirupathur, Tiruvannamalai, Kallakurichi, Villupuram) per [CAI Head Quarters](https://annauniv.edu/cai/Head%20Quarters.php) — far wider than Chennai metro |
| Colleges affiliated to Anna University, statewide | **488** | Same | |
| Colleges affiliated to Anna University (alternative) | **593** | [Anna University Profile PDF](https://annauniv.edu/Anna%20University%20Profile.pdf) | **Conflicts with 488.** Undated; prefer the dated 2023-24 figure |
| Students in Anna University affiliated institutions | "about **7,21,276**" | Same profile PDF | **Undated** (latest internal reference is 2019), statewide, prefixed "about". Do not treat as current |
| Colleges affiliated to University of Madras | **131** | [UNOM NAAC SSR 4th cycle, p.11](https://www.unom.ac.in/webportal/uploads/naac/ssr_report.pdf) | Jan 2023. Jurisdiction = Chennai, Tiruvallur, Kancheepuram |
| Colleges in Chennai district (DCE-administered types) | **67** (46 arts & science) | [TN Directorate of Collegiate Education directory](https://tndce.tn.gov.in/Colleges) | **Excludes engineering, medical, dental, law, agriculture, polytechnic.** Count tallied from the list; the page prints no total |
| Colleges in Chennai + Chengalpattu + Tiruvallur + Kancheepuram (DCE types) | **191** | Same | Same exclusions |
| Colleges in Tamil Nadu (DCE types) | **1,566** | Same | Against AISHE's 2,983 all-type TN colleges — the difference is the non-DCE directorates |

---

## 4. The Chennai denominator gap — stated, not papered over

**There is no published figure for higher-education enrolment in Chennai district
or Chennai metro.** We confirmed this against AISHE 2023-24 (§2.2), the NIRF corpus,
the TN Directorate of Collegiate Education directory, and both affiliating
universities' own publications. This is risk **R-08** and it remains open.

### 4.1 What we can defend without assumption

- **Floor, 28 named Chennai-metro campuses: 1,97,186 UG+PG.** Every component is a
  printed figure in a cited institutional filing. Excludes the SRM IST and VIT rows
  because those filings mix in non-Chennai campuses.
- **Including those two rows: 3,12,085 UG+PG** — but this over-counts Chennai by an
  unknown amount (VIT's Vellore campus and SRM's Trichy/Delhi campuses are inside it).
- **Ceiling on Chennai district colleges: fewer than 327**, from AISHE Box 2 (§2.2).

The floor covers only 30 institutions. Chennai metro has at least 191 DCE-listed
colleges plus the Anna-affiliated engineering network plus medical, dental, law and
polytechnic institutions. **The floor is therefore a genuine floor — the true number
is materially higher, and we cannot say by how much from public data.**

### 4.2 The two proxies, and why neither is good

**Proxy A — college-count share.** 191 of 1,566 DCE-listed TN colleges are in the
four metro districts = **12.2%**. Applied to TN regular-mode enrolment: **3,89,541**.
*Why it understates:* metro colleges are systematically larger than the TN average
(DG Vaishnav alone is 10,910 students), and the DCE list excludes the engineering
sector, which is both huge and metro-concentrated.

**Proxy B — Anna University region share.** 142 of 488 affiliated colleges are in the
Chennai region = **29.1%**. *Why it overstates:* that region spans ten districts
reaching to Villupuram and Tiruvannamalai. The four-district subset is lower, and a
direct count of the CAI district pages is unusable — the Chengalpattu and
Kancheepuram lists share 36 identical college names (a legacy of the 2019 district
split), and the union of four district pages (135) contradicts the printed
ten-district regional total (142).

### 4.3 The range we use, and its error bars

`ASSUMPTION:` **Chennai metro (4 districts) regular-mode higher-education enrolment
= 3.2 lakh (low) / 4.6 lakh (base) / 6.5 lakh (high).**

*Reasoning.* The low bound is set just above the 28-campus sourced floor of 1.97 lakh
plus a conservative allowance for the unnamed affiliated-college tail — it assumes
the floor already captures most of the volume, which it almost certainly does not,
and is therefore a true pessimistic bound. The base sits between Proxy A's 3.90 lakh
and the midpoint of the two proxies, weighted up because Proxy A's exclusion of
engineering is a known, large, one-directional error. The high bound takes Proxy B's
direction seriously while discounting it for the ten-district span.

*Error bars.* The range spans **2.03×** from low to high. Any SAM figure derived from
it inherits that factor. We state SAM as a range throughout and never as a point.

*Test that would replace it.* Any one of the three requests in §4.4.

### 4.4 The three primary requests that would close the gap

Ranked by cost to obtain:

1. **AISHE institutional returns, filtered by district** (cheapest, highest quality).
   Every institution files an AISHE return carrying its district code and total
   enrolment. The district aggregation exists inside the AISHE portal but the public
   dashboards at `aishe.gov.in` require an authenticated session. **Request:** a data
   request to the AISHE cell, Department of Higher Education, MoE, for district-wise
   enrolment for Chennai, Chengalpattu, Tiruvallur and Kancheepuram, AY 2023-24. This
   is routine statistical data, not an RTI matter.

2. **Anna University Centre for Affiliation of Institutions**, for a district-wise
   affiliated-college summary *with printed totals and enrolment*, AY 2024-25. The
   CAI publishes district pages already; the summary table is a small ask.
   Contact point: the CAI index at https://annauniv.edu/cai/.

3. **RTI to the Tamil Nadu Directorate of Collegiate Education** for district-wise
   student strength across all directorates (collegiate, technical, medical), AY
   2024-25. Slowest, but the only route that captures all sectors in one answer.

**Until one of these returns, the Chennai denominator is an assumption with a 2×
range, and every SAM number in `MODEL.md` must be read as such.** The pilot does not
depend on it — SOM is built from three campuses whose enrolment is individually
sourced — so this gap blocks fundraising narrative, not Phase A execution.

---

## 5. What else we could not find

| Missing | Why it matters | How to get it |
|---|---|---|
| **Chennai district / metro enrolment** | The SAM denominator. §4 | §4.4 |
| **VIT Chennai campus-only enrolment** | VIT Chennai is a plausible pilot campus; we cannot size it | VIT files one NIRF submission for Vellore + Chennai combined, and chennai.vit.ac.in publishes no count. **Request:** VIT's UGC Public Self-Disclosure or NAAC Cycle-4 SSR with campus-wise strength, or its AISHE return (off-campus centres normally file separately) |
| **Anna University CEG / MIT / ACT / SAP split** | The 11,940 is "Anna University" with no campus breakdown, and the university also runs 13 constituent colleges and 3 regional campuses that may or may not be inside it | Anna University annual report or NAAC SSR extended profile metric 2.1, campus-wise; or the AISHE institution return |
| **Anna-affiliated college count for the 4 metro districts specifically** | Sizing the affiliated-college tail, which is most of the market | CAI district-wise summary with printed totals, or the AICTE approved-institutions dataset filtered by district |
| **HITS, Dr. M.G.R. E&RI, Crescent — institution-wide totals** | Three sizeable institutions are in §3.1 at partial (engineering-only) scope, so the floor understates | AQAR extended-profile metric 2.1 on each institution's IQAC page, or the AISHE institution return |
| **Women's Christian College, Guru Nanak College — post-2022-23 figures** | Both dropped out of NIRF's published band, so our figures are two years stale | The colleges' own AQAR, or a direct request for their NIRF'2025/'2026 DCS submission |
| **Average used-book transaction price in Chennai** | `avg_book_price_inr` is the fourth founder assumption and is still an assumption | **Measurable now at zero cost:** scrape 200+ Chennai used-book listings from OLX and Clankart, and photograph the price lists of the Moore Market / Pondy Bazaar second-hand sellers. This is the cheapest high-value measurement available and should be in Phase A |
| **Gifting share — what fraction of campus book transfer is given away free** | Suppresses cash GMV without suppressing book value moved. Identified by the competitor audit as one of the two numbers that decide this business. **No source exists** | **Phase A primary research, required.** Instrument: a question in the student survey ("the last textbook you passed on — did you sell it, swap it, or give it away?") plus observation at one semester-end. Flagged in `MODEL.md` as a required measurement, not an estimate |
| **India used-book market value** | TAM anchor | **No credible primary source found.** The Credence Research "USD 781m India second-hand books" figure is a vendor report landing page with no visible methodology — **it is not used in this model and must not enter it.** `MODEL.md` therefore builds TAM bottom-up from AISHE enrolment using the same driver stack as SAM and SOM, which is internally consistent and auditable, rather than importing an unverifiable number |

---

## 6. Sources

| Source | URL | Accessed |
|---|---|---|
| AISHE 2023-24, Ministry of Education | https://cdnbbsr.s3waas.gov.in/s392049debbe566ca5782a3045cf300a3c/uploads/2026/07/202607131602421770.pdf | 2026-10-21 |
| NIRF data submissions (per institution) | https://www.nirfindia.org/ — individual PDF URLs in §3 | 2026-10-21 |
| Anna University, College Statistics 2023-24 | https://annauniv.edu/cai/College%20Statistics-2023-24.pdf | 2026-10-21 |
| Anna University, Centre for Affiliation — Head Quarters | https://annauniv.edu/cai/Head%20Quarters.php | 2026-10-21 |
| Anna University Profile (undated) | https://annauniv.edu/Anna%20University%20Profile.pdf | 2026-10-21 |
| University of Madras NAAC SSR, 4th cycle | https://www.unom.ac.in/webportal/uploads/naac/ssr_report.pdf | 2026-10-21 |
| TN Directorate of Collegiate Education, college directory | https://tndce.tn.gov.in/Colleges | 2026-10-21 |
| Starter Story — Clankart founder interview | https://www.starterstory.com/stories/clankart | 2026-10-21 |
| Razorpay pricing | https://razorpay.com/pricing/ | 2026-10-21 |

**Not used, and why:** Credence Research India second-hand books market size — vendor
landing page, no methodology. Collegedunia / Careers360 / Shiksha / Wikipedia
enrolment figures — secondary, mutually inconsistent, and in at least one checked case
(Pachaiyappa's) wrong against the institution's own filing.
