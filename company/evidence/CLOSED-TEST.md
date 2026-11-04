# CLOSED-TEST.md — what a closed test among known adults actually requires

**Owner:** privacy-compliance · **Version:** v1.1 · **Written:** 2026-10-23
**Amended:** 2026-11-04 (§4.1, `completes_purchases` — see the amendment in that section)
**Question answered:** the founder wants to put BookHop in front of ~12 of
their own friends, not a campus. What binds, and how much of the ten-field
discovery gate is overkill for it?

**Separate file, not a new `COMPLIANCE.md` section, for one reason:** the ten
fields were reasoned for *"verified adults at 2–3 Chennai campuses"* and this
is a different scope with a different answer per field. Interleaving the two
would make the campus answers ambiguous. `COMPLIANCE.md` §11 now points here.

**This is not legal advice.** See `COMPLIANCE.md` §0, which applies in full.
Every rule below is cited with the source I read and the date I read it.

---

## 0. Verdict

**Yes, a closed test among twelve known adults can be run lawfully, and the
ten-field gate is substantially more than the law requires for it — but the
answer splits on one product decision the founder has not yet made, and the
gate they asked me about is not the gate their test crosses.** If no book is
actually bought or sold through the app (friends list, search, browse and
message; the test ends before any handover), the Consumer Protection
(E-Commerce) Rules 2020 have nothing to attach to, **incorporation is not
required**, and the honest requirement set is four items, not ten: a published
privacy policy, published terms and platform rules, a named and reachable
grievance officer, and the in-force takedown and incident clocks. If friends do
buy and sell real books through it, BookHop is a marketplace e-commerce entity
and **r.4(1)(a) requires a company at twelve users exactly as it does at two
thousand — I verified the instrument's scope rule from the Gazette and there is
no de minimis of any kind in it.** Overriding both of those: **the event the
founder is describing is Gate B — one real person holds an account — and Gate B
has no guard in the code and no evidence requirements in the database. The
elaborate gate is on the door after the one they are about to walk through.**
That finding is §1 and it outranks the field-by-field answer.

---

## 1. FINDING — the gate that governs this test does not exist

**This is the answer to Command 4 and it comes first because it changes the
question from "is the gate too big?" to "which gate?".**

`ops/INCORPORATION-AND-BLOCKERS.md` §3.3 already split the gates correctly on
2026-10-21. Gate C is *"a real student can see another real student's
listing"*. Gate B is *"one real student holds an account"*. Twelve friends
browsing each other's books is **Gate C by that definition** — but every one of
them crosses **Gate B first**, the moment they sign up, and Gate B is the gate
with nothing behind it.

**B9′ was specified and was not built.** §3.3 requires: *"A
`gate_authorisations` row with `gate='B'`, and real account creation refused
without it"*, and adds *"it is one function"*. Measured today:

- `apps/core/scoping.py:71` defines `assert_discovery_open`. `apps/listings/services.py:584` defines `assert_campus_write`. **There is no third guard.** `grep -rn "def assert_"` over `apps/` returns exactly those two.
- `apps/accounts/services.py` contains no reference to a gate on any account-creation path.
- So a real, non-seed account can be created with no authorisation row of any kind, and no named human anywhere in the chain.

**And the database floor exempts Gate B by design.**
`apps/core/migrations/0005_gate_evidence_complete.py` opens its trigger with

```
IF NEW.gate <> 'C' THEN
  RETURN NEW;
END IF;
```

and says so in its own docstring: *"`gate='B'` and `gate='D'` rows are
unconstrained: ADR-002 §4.1(b) specifies the checklist for Gate C, and
inventing one for the others would be scaffolding for a gate nothing opens."*

**That reasoning was right when it was written and is wrong now.** It was true
while nothing opened Gate B. The founder's question opens it. As the code
stands, a `gate='B'` row may be inserted with `evidence={}` and
`authorised_by_human=''` — the two things the whole design exists to prevent —
and nothing reads it anyway.

This is `CLAUDE.md` rule 9 in its exact shape: **a document names a control, the
control does not exist, and the existence check that would have failed by name
was never written because the gate had nothing to open.** It is also rule 10's
sixth disguise — *"a check that has not started"* — one level up: not a
forward-dated test, a forward-dated *gate*. From outside, "Gate B is clean" and
"Gate B is unguarded" look identical, because both produce no refusal.

**Consequence for the founder's question:** shrinking the Gate C field set
buys nothing until Gate B has a guard, because the first real friend's personal
data enters the system at Gate B regardless of what Gate C asserts. **Build the
small gate at B. Do not loosen the big gate at C.** They are different doors.

### 1.1 Second finding — one of the ten fields is unsatisfiable at this scope

`campus_mou_ref` asserts a signed MOU with an institution. **For a friends
test there is no institution and no counterparty.** The only ways past it are a
fabricated reference or a placeholder, and migration 0005's deny-list exists
precisely to reject the placeholder. So the field is not merely unnecessary —
it is a requirement that **cannot be satisfied**, which `CLAUDE.md` rule 10
names directly, and whose predictable resolution is someone widening
`_present()` or typing `"N/A"`.

Under rule 13's order of resort this is **rung 1, not rung 3**: the colliding
requirement is ours, not a frozen external contract, so the fix is a
scope-typed evidence set, costing one trigger and leaving Gate C at full
strength. It is not a reason to weaken the deny-list.

---

## 2. What actually binds for a closed circle of known adults

### 2.1 Are we an intermediary at this scale? — Yes, and scale is irrelevant

IT Act s2(1)(w) defines an intermediary by function — a person who on behalf of
another receives, stores or transmits a record. It has **no user threshold and
no company requirement**. One real friend's listing or message satisfies it.
`ops/INCORPORATION-AND-BLOCKERS.md` B1′ already reached this conclusion and
called it the key finding; nothing about twelve friends changes it.

**What that pulls in** (IT Rules 2021 as amended by G.S.R. 120(E), in force
20 Feb 2026; clocks tabled in `COMPLIANCE.md` §5.1, unchanged): published rules
and regulations, privacy policy and user agreement (r.3(1)(a)); a named
Grievance Officer with published contact (r.3(2)(a)); acknowledge in 24 hours,
dispose in 7 days; the 3-hour court/government takedown clock (r.3(1)(d)) and
the 2-hour NCII/impersonation clock (r.3(2)(b)); 180-day preservation
(r.3(1)(j)); the quarterly user reminder (r.3(1)(c)).

**The sanction is loss of safe harbour, not a fine, and this matters for
calibration.** Rule 7, read today: *"Where an intermediary fails to observe
these rules"*, the s79(1) exemption *"shall not be applicable to such
intermediary"* and it *"shall be liable for punishment under any law for the
time being in force including the provisions of the Act and the Indian Penal
Code"* — https://itlaw.in/bareact/it-rules-2021-intermediaries-guidelines-and-digital-media-ethics-code/page/4
(bare-act reproduction, accessed 2026-10-23; **near-primary — the eGazette copy
should be read before Gate C**, and this is the same caveat `COMPLIANCE.md` §5.1
already carries).

So the practical exposure at twelve friends is: **if one of them posts a
pirated PDF scan or a defamatory message and BookHop has no grievance officer,
BookHop (or the founder personally, pre-incorporation) answers for that content
instead of being exempt from it.** At twelve known friends the probability is
low. The cost of the control — publishing a name and an email — is also near
zero. **Keep it.**

### 2.2 DPDP, given the 13 May 2027 commencement

**Re-verified 2026-10-23: no notification advancing the dates was found.** I
searched for an October 2026 MeitY commencement amendment and found none; the
three-tranche schedule in G.S.R. 843(E) (13 Nov 2025 / 13 Nov 2026 / 13 May
2027) stands as recorded in `COMPLIANCE.md` §1.1. Commentary still reports an
unnotified proposal to shorten the 18-month tranche. **Days since last
re-verification of the commencement position: 0.** Keep the monthly re-check.

**Consequence for this test: essentially nothing binds under DPDP today.**
Notice, consent, rights, erasure and breach reporting all commence 13 May 2027.
That is the same unusual room `COMPLIANCE.md` §11 described, and the same
instruction applies — use it to build correctly, not to defer.

**Two things that are specific to this test and are not in §1 of
`COMPLIANCE.md`:**

1. **A friends test creates a data tail that outlives the exemption.** Personal
   data collected in late 2026 is still personal data on 13 May 2027, with no
   transition period. At twelve people this is trivially managed — close the
   test and purge — but *only if the test has an end date*. An open-ended
   friends test is the version of this that goes wrong.
2. **s5(2) retro-notice — I could not resolve this and it is an honest gap.**
   DPDP s5(2) requires a fiduciary to give notice to a Data Principal who
   consented *"before the commencement of this Act"*. The Act partially
   commenced 13 Nov 2025, so data collected in October 2026 is after the Act's
   commencement but before s5's. Whether s5(2) therefore reaches this test's
   participants turns on how "commencement of this Act" is read against a
   tranched notification. **I could not reach the official section text**
   (indiacode.nic.in returned HTTP 403 on 2026-10-23, as it did on 2026-10-21);
   commentary reproduces the sub-section but splits on the wording
   (*"before the date of commencement"* vs *"before the commencement"*) —
   https://www.ahlawatassociates.com/blog/consent-requirements-under-the-digital-personal-data-protection-act-2023-and-digital-personal-data-protection-rules-2025
   (accessed 2026-10-23). **Impact at twelve friends: near zero — send the
   notice anyway, it is one email. Impact at 2,000 campus users: material.**
   Logged as an open item in §5.

**Not in force is not the same as not binding.** SPDI Rules 2011 r.4 is in
force today and is the subject of §2.4.

### 2.3 The Consumer Protection (E-Commerce) Rules — the decisive question

**Primary-verified from the Gazette text on 2026-10-23.** I extracted the
English text of G.S.R. 462(E) (Gazette No. 358, 23 July 2020) from the PDF
rather than reading a summary — source
https://prsindia.org/files/bills_acts/bills_parliament/2021/Consumer%20Protection%20(E-Commerce)%20Rules,%202020.pdf

**There is no de minimis.** r.2(1) applies the Rules to *"all goods and
services bought or sold over digital or electronic network"*, *"all models of
e-commerce"*, *"all e-commerce retail"* and *"all forms of unfair trade
practices across all models of e-commerce"*. **No turnover, user-count,
transaction-volume or size threshold appears anywhere in the instrument.** The
closed-circle framing earns nothing here: twelve is the same as twelve
thousand.

**The entity definition is person-shaped, not company-shaped.** r.3(1)(b):
an e-commerce entity is *"any person who owns, operates or manages digital or
electronic facility or platform for electronic commerce"*. So an unincorporated
founder operating the platform **is** an e-commerce entity — and r.4(1)(a) then
requires that entity to *"be a company incorporated under the Companies Act,
1956 ... or the Companies Act, 2013"*. The rule is breached by operating, not
by trading at some volume.

**The only textual hook for a closed test is the r.2(1) proviso, and I think it
fails.** Verbatim: *"Provided that these rules shall not apply to any activity
of a natural person carried out in a personal capacity not being part of any
professional or commercial activity undertaken on a regular or systematic
basis."* `COMPLIANCE.md` §2.1 already rules that this exempts the student
seller and not BookHop. The founder's framing raises a narrower version — is
the *founder's own* operation, among personal friends, pre-revenue, an activity
"in a personal capacity"? **My reading: no.** Building and operating a platform
you intend to commercialise is hard to characterise as personal capacity, and
twelve people transacting over weeks is "regular or systematic". But it is the
only hook that exists, it is a one-line question, and the thing it would buy is
a four-week incorporation lead time off the critical path. **It goes to counsel
as Q-CT1 (§5), not because I am unsure of the reading but because the founder
should not spend four weeks on my reading of a proviso.**

**The route that does work: no sale, no e-commerce.** The Rules attach to goods
*"bought or sold"* over the network (r.2(1)(a)) and to *"e-commerce"*, defined
at CPA 2019 s2(16) as *"buying or selling of goods or services including
digital products over digital or electronic network"* (definition corroborated
across commentary on 2026-10-23 — https://taxguru.in/corporate-law/inclusion-e-commerce-consumer-protection-act-2019.html
— **not read from the bare Act; indiacode 403**). **If the closed test completes
no purchase, there is nothing for r.2(1) to attach to**, and r.4(1)(a) does not
bite. Note that `COMPLIANCE.md` §2.1 already grades the no-shipping argument as
*"an argument, not a safe harbour"* — but that argument was about *where* a sale
concludes. **This one is about whether a sale happens at all, and it is a
stronger argument because it is a fact about the test rather than a
construction of the rule.**

**Shape 1 is also probably the better experiment.** Twelve friends cannot tell
you whether campus handovers work, whether strangers trust each other, or
whether supply shows up at semester end — those need a campus. What they can
tell you is whether the matching layer finds the right edition and whether the
flow is usable, and neither requires money to change hands. **That is Product's
call, not mine, but the compliance cost of the two shapes differs by a company
registration and I would be failing the charter not to say which side of that
line the cheap experiment sits on.**

**Contravention routes through the parent Act, not an automatic penalty.**
r.8, verbatim: *"Contravention of rules. — The provisions of the Consumer
Protection Act, 2019 (35 of 2019) shall apply for any violation of the
provisions of these rules."* So the consequence of operating unincorporated is
CCPA investigation and direction, and liability for non-compliance with such a
direction — **not a self-executing fine**. I did **not** verify the CPA penalty
sections from primary text and am not quantifying them (§5, Q-CT4).

### 2.4 Does anything turn on incorporation when no money flows through us?

Four separate answers, because they come apart:

| | Binds without a company? | Source |
|---|---|---|
| **Intermediary duties** (grievance officer, clocks, published policies) | **Yes.** s2(1)(w) is functional; r.3 has no entity requirement. The Grievance Officer may be the founder in their own name (already B2′) | IT Act s2(1)(w); IT Rules r.3, r.7 |
| **SPDI privacy policy** | **Yes — and this is the one most likely to be missed.** See below | SPDI Rules r.4 |
| **CERT-In** (6h reporting, NTP, 180-day India logs) | **Yes.** Direction (i)/(ii)/(iv) bind *"service providers, intermediaries, data centres, body corporate"* | CERT-In Directions 2022, `COMPLIANCE.md` §5.2 |
| **E-Commerce Rules r.4(1)(a)** | **No — it is the rule that requires the company.** It bites only if the Rules apply at all (§2.3) | E-Com r.3(1)(b), r.4(1)(a) |

**SPDI Rule 4, primary-verified 2026-10-23** —
https://www.wipo.int/wipolex/edocs/lexdocs/laws/en/in/in098en.pdf — requires a
body corporate to *"provide a privacy policy for handling of or dealing in
**personal information including** sensitive personal data or information"*,
*"published on website"*. **It is not limited to SPDI**, which is the part most
summaries get wrong, and it says so on its face.

And **"body corporate" reaches an unincorporated founder.** Rule 2(1)(c) points
to IT Act s43A Explanation (i): *"'body corporate' means any company and
includes a firm, sole proprietorship or other association of individuals
engaged in commercial or professional activities"* (corroborated across
commentary on 2026-10-23 — https://courtbook.in/information-technology-act-2000/section-43A
— **not read from the bare Act; indiacode 403, same as 2026-10-21**).

**So: a published privacy notice is required today, at twelve friends, with or
without a company, and remains so until s43A is omitted on 13 May 2027.** This
does not add a blocker — `notice_version_ids` already covers it — but it
converts one of the ten fields from *"good practice at this scale"* to
*"required at this scale"*, which is exactly the distinction the founder asked
for.

**What incorporation buys that is not a legal requirement:** limited liability.
Operating unincorporated means the founder is personally the body corporate,
personally the intermediary, and personally the defendant. That is a founder
decision, not a compliance ruling, and it is the strongest reason to start the
filing now even under shape 1 — `ops/INCORPORATION-AND-BLOCKERS.md` §1.4 puts
the lead time at about four weeks, and §3.3 already warns that Gate B *"is a
holding position and not a destination"*.

### 2.5 Grievance-officer obligations at twelve people

**Required. Unambiguously, at both shapes, pre-incorporation.** IT Rules
r.3(2)(a) imposes it on every intermediary; E-Com r.4(4) imposes it again if
the Rules apply. Neither has a threshold.

What *is* scale-sensitive is the staffing, not the appointment. A 2-hour clock
does not lengthen because there are twelve users — but at twelve users, **one
named person with notifications enabled is a defensible way to meet it**,
whereas at 500 it is not. That distinction drives the `oncall_rota_ref` answer
in §3.

### 2.6 Negative findings, recorded so nobody builds them

- **No SMS vendor exists** (`apps/accounts/models.py:111`: *"there is no SMS vendor and handover coordination happens in-app"*), so TRAI's TCCCPR 2018 / DLT sender registration — which in practice requires a registered entity — **is not on the critical path.** It would become one the day anyone adds OTP-by-SMS, and that is a change to this analysis, not a feature.
- **No money flows through BookHop**, so GST s52 TCS and s24(x) registration are not engaged (`COMPLIANCE.md` §4.2 reasoning unchanged; nothing about a friends test alters it), and no PPI question arises because no credit exists in the build (P12/C16).
- **IT Rules r.3(1)(h)'s 180-day retention after account withdrawal is already satisfied**, not by accident: `apps/accounts/services.py:143` sets `RETENTION_FLOOR = timedelta(days=365)` and `apps/listings/services.py:82` imports it rather than retyping it. 365 > 180. I checked this specifically because a deletion flow is the obvious place for that floor to be breached.
- **`legal_entities` already accommodates a pre-incorporation gate row.** `apps/core/models.py:85`: *"Every column is nullable because the row exists before the company does."* So the smaller gate needs no schema change on that table.
- **`GATES = ("B","C","D")` and `SCOPE_TYPES = ("GLOBAL","CAMPUS")`** (`apps/core/models.py:21–22`), so a `gate='B'`, `scope_type='GLOBAL'` row is **already expressible today**. The smaller gate needs no CHECK-constraint change and no enum widening.

---

## 3. The ten evidence fields, one at a time

**Columns.** *Shape 1* = closed test, no completed purchase. *Shape 2* = friends
actually buy and sell books through the app. **"Required"** means a rule I can
cite compels it. **"Wanted"** means I am not claiming the law requires it and I
still want it, with the reason stated — that line is the point of this table.

| # | Field | Shape 1 | Shape 2 | Why, and what I want regardless |
|---|---|---|---|---|
| 1 | `cin` | **Not required** | **REQUIRED** | E-Com r.4(1)(a), primary-verified, no de minimis. Shape 1 escapes it only because no sale occurs. **Wanted regardless:** start the filing now — 4-week lead time, and unincorporated means personally liable. |
| 2 | `incorporation_date` | Not required | Required *(derivative)* | Not an independent obligation. It is a consistency check on `cin` (must parse, not future, must precede INC-20A). Falls and stands with field 1. |
| 3 | `inc20a_filed_at` | **N/A** | Required *(conditional)* | Companies Act s10A bars a company from commencing business before the declaration — **but only once a company exists.** With no company there is no INC-20A and no s10A bar on a natural person. This field is conditional on field 1, not parallel to it. |
| 4 | Grievance officer (name / email / phone) | **REQUIRED** | **REQUIRED** | IT Rules r.3(2)(a) — functional test, no threshold, no company requirement; E-Com r.4(4) adds it again at shape 2. **The clearest "binds at any scale" item on this list.** May be the founder in their own name (B2′). |
| 5 | `notice_version_ids` — PRIVACY / TERMS / SELLER_TERMS | **PRIVACY + TERMS required; SELLER_TERMS not** | **All three REQUIRED** | PRIVACY: SPDI r.4, in force, binds a sole proprietorship (§2.4). TERMS/rules: IT Rules r.3(1)(a). SELLER_TERMS carries the r.5(2) seller undertaking, which is an E-Commerce Rules artefact and so shape-2 only. **Wanted regardless:** the seller undertaking is the only thing that makes a condition grade mean anything. **Keep this field exactly as it is — README §7 records it as the one item verifiable end-to-end in the database, and shrinking the gate must not cost that.** |
| 6 | `breach_rehearsal_at` | **Not required** | **Not required** | **No instrument requires a rehearsal.** What binds — today, at any scale, incorporated or not — is CERT-In's 6-hour reporting capability, NTP sync to NIC/NPL, and 180-day logs held in India. The gate asserts a drill and never asserts the capability; `breach_rehearsal_at`'s only validation is that a date parses. **Replace, do not drop:** a named CERT-In PoC plus a written runbook is the obligation; the drill is how you find out the runbook is wrong, and it is worth doing before a campus, not before twelve friends. |
| 7 | `counsel_engagement_ref` | **Not required** | **Not required** | No rule requires engaging counsel. **And it is the field I would fight hardest to keep.** Everything else here is me reading rule text; the founder is about to put real people's data in a database and publish terms that allocate liability. See §6. |
| 8 | `takedown_sop_ref` | **REQUIRED in substance** | **REQUIRED in substance** | The 3h (r.3(1)(d)), 2h (r.3(2)(b)), 24h-acknowledge and 7-day-dispose clocks are in force since 20 Feb 2026 and are not scale-gated. **A twelve-person test does not make a 2-hour clock longer.** The SOP can be one page. |
| 9 | `oncall_rota_ref` | **Required in substance, not in form** | Required | The obligation is the *clock*, not the *rota*. At twelve known friends, one named person with notifications on is a defensible way to meet 2 hours; at 500 it is not. **Keep the field and let a rota of one satisfy it** — that is still a rota, and it is honest. Do not drop it: dropping it is how the clock becomes nobody's job. |
| 10 | `campus_mou_ref` | **Not required — and not satisfiable** | Not required *(no campus)* | There is no institution and no counterparty, so the only ways past it are a false reference or a placeholder the deny-list exists to reject. See §1.1. The obligation it proxies — permission to run activity on someone's premises — has no analogue when a handover happens in a café. |

**Totals.** Of the ten: **four are required at shape 1** (grievance officer,
PRIVACY notice, TERMS notice, takedown SOP), **one more is required in
substance but not in the form the field demands** (`oncall_rota_ref`), **three
are required only at shape 2** (`cin`, `incorporation_date`, `inc20a_filed_at` —
and the second and third are derivative of the first), **one is wanted and not
required** (`counsel_engagement_ref`), and **two should be replaced rather than
kept or dropped** (`breach_rehearsal_at` → CERT-In capability; `campus_mou_ref`
→ nothing).

---

## 4. The smaller gate, specified

**Ruling: a reduced gate is lawful for a closed test, at Gate B, with an
expiry.** Below is what the row should assert. **I have changed no code — §4.2
describes what engineering would have to do and it needs a CTO contract
amendment, not an edit.**

### 4.1 What a closed-test `gate_authorisations` row should assert

`gate='B'`, `scope_type='GLOBAL'`, `scope_id=NULL` — **already expressible;
no enum or CHECK change needed** (§2.6).

| Item | Where it lives | Note |
|---|---|---|
| `authorised_by_human` | column | **Unchanged, same deny-list, non-negotiable.** A smaller gate is still a named human's signature. |
| `notice_version_ids` | evidence | PRIVACY + TERMS. SELLER_TERMS **required if any book changes hands** (shape 2). Same FK resolution — the one end-to-end verifiable item stays verifiable. |
| `grievance_officer_name` / `_email` / `_phone` | `legal_entities` | Required. Read from the same typed columns, with `cin` / `incorporation_date` / `inc20a_filed_at` **not** read. The table already allows this. |
| `takedown_sop_ref` | evidence | Required. |
| `escalation_contact_ref` | evidence | **Replaces `oncall_rota_ref`.** One named reachable human. |
| `cert_in_poc_name` / `_email` / `_phone` | `legal_entities` *(columns already exist)* | **Replaces `breach_rehearsal_at`.** The obligation is the 6-hour capability. |
| `incident_runbook_ref` | evidence | With the above. A written runbook, not a rehearsal. |
| `participant_ceiling` | evidence | **New, and one of the two that make this defensible rather than merely smaller.** An integer. |
| `closed_test_expires_at` | evidence | **New, and the more important of the two.** |
| `completes_purchases` | evidence | **Added by A-37 after v1.0 of this file; see the amendment below.** Boolean. §2.3's route out of the E-Commerce Rules is the factual one — *no sale, no e-commerce* — so the shape has to be a value a named human signed, not a property of what has not been built yet. `false` is a **value**, so the gate tests presence and never truthiness. |
| **Not asserted** | — | `cin`, `incorporation_date`, `inc20a_filed_at`, `campus_mou_ref`. `counsel_engagement_ref` **recommended, not required**. |

> **AMENDMENT 2026-11-04 — `completes_purchases` joins the table, and v1.0 of
> this section could not have named it.**
>
> §4 was written on 2026-10-23 with the founder's choice between shape 1 and
> shape 2 **still open**: §2.3 analysed both and said explicitly that picking
> one was *"Product's call, not mine"*. The founder picked shape 1 the same day
> (`decisions/DECISIONS.md` D-072), and `API-CONTRACT.md` A-37 made it a
> control rather than an intention — *"an absence is not a control"* — adding
> the boolean to the authorisation row beside the two bounds above.
>
> **So this is not a correction of v1.0; it is the row v1.0 deliberately left
> undecided, filled in.** It is recorded here rather than only in the contract
> because `tests/unit/test_gate_b_evidence_set.py` derives the required set
> from **this table** and compares it with the code: an item the gate reads and
> this table does not list was carried in a test-side allow-list, which is one
> more hand-made copy of a rule that already has two homes (`CLAUDE.md`
> rule 11). That allow-list is now empty.
>
> **Accepted.** No other row changes, and nothing here widens the gate: the
> boolean was already being read.

**Why the last two items are not optional.** `ops/INCORPORATION-AND-BLOCKERS.md`
§3.3 already warns that Gate B *"is a holding position and not a destination"*
and that the A0 reading *"was scoped to 30 handovers over 14 days"* and is *"not
a position I would hold at 300"*. **A reduced gate justified by the words
"twelve known adults for six weeks" must be bounded by those words in the row,
or it is a permanent downgrade wearing a temporary label.** The expiry and the
ceiling are what turn that caution from prose into something a guard can
enforce. **Without them I do not endorse the reduced gate.**

### 4.2 What engineering would have to change — described, not done

Four items, none large, all behind frozen contracts (ADR-002 §4.1(b)):

1. **A `gate='B'` evidence trigger**, in a new migration **beside** migration
   0005's, keyed on gate with its own key set. 0005's `IF NEW.gate <> 'C' THEN
   RETURN NEW` becomes a per-gate lookup. **Rule 12: the C key set does not
   move and does not shrink.** The new trigger goes in alongside; nothing is
   removed.
2. **`assert_real_account_allowed(...)`** on the non-seed account-creation
   path — B9′'s one function, mirroring `assert_discovery_open`'s exact shape
   (refuse with a named code, log the reason, same audit row). This is the
   §1 finding and it is needed whatever the founder decides about field count.
3. **`open_discovery.EVIDENCE_KEYS` / `LEGAL_ENTITY_FIELDS` become per-gate.**
   Today they are module constants shaped for Gate C. **Rule 11 applies: one
   definition shared by the command and the trigger, not two hand-copied key
   lists** — the existing pair already carries a comment explaining why the
   command keeps its own ordered copy, and that reasoning should survive the
   change rather than be used to justify a third copy.
4. **An expiry that does something.** `closed_test_expires_at` is a date in a
   JSON blob unless something reads it. Rule 10: a clock nothing reads is a
   check that cannot fail. The guard in (2) must refuse after the date, **and
   there must be a test that exercises the refusal and asserts the message
   text, not the exit status** — rule 10's sixth disguise names exactly this.

**For the test-writer, since rule 9 requires the control be asserted at the
boundary the document claims:** the claim here is *"a real account cannot be
created without a live, unexpired, named-human Gate B row"*. The set that claim
quantifies over is **every path that creates a `users` row with
`is_seed = false`** — the signup view, the API, any management command, any
staff-created account, and any fixture path reachable outside tests. **That set
must be enumerated in the test file**, not implied, because `CLAUDE.md` rule 9's
four-gates-deep lesson is that the layer was real and the set was never written
down.

---

## 5. What I could not determine, and what it costs to close

| # | Open question | Why it is open | Cost to close |
|---|---|---|---|
| **Q-CT1** | Does the r.2(1) proviso (*"natural person ... personal capacity"*) reach a founder operating a platform for personal friends? | My reading is **no**, and it is the only textual hook that would take incorporation off the critical path. It is a reading, not a ruling. | **One question in the existing counsel C2 brief.** No new engagement. This is the cheapest high-value question on the list. |
| **Q-CT2** | Does a closed test in which **no purchase completes** avoid the E-Commerce Rules entirely? | §2.3 argues yes on the Gazette text. It decides whether a company is on the critical path for the next month. | Same brief as Q-CT1. **These two together are the whole incorporation question.** |
| **Q-CT3** | DPDP s5(2): is data collected in Oct 2026 *"before the commencement of this Act"*, given the Act commenced in tranches from 13 Nov 2025? | **indiacode.nic.in returned HTTP 403 on 2026-10-23 and on 2026-10-21.** Commentary reproduces the sub-section with two different wordings. | **Free if the Gazette PDF of the Act can be reached** — this is a reading task, not a counsel question. Near-zero impact at twelve friends (send the notice); material at campus scale. |
| **Q-CT4** | What CPA 2019 actually imposes for an r.4(1)(a) breach. | r.8 is verified and routes to the parent Act; **I did not verify the CPA penalty sections from primary text and am not quantifying the exposure.** | A read of CPA 2019 ss18–22 and s88 from a reachable primary copy. Do it before shape 2, not before shape 1. |
| **Q-CT5** | IT Rules 2021 r.7 and the 2026 amendment read from reproductions, not the eGazette. | Same caveat `COMPLIANCE.md` §5.1 and §10 already carry. Unchanged by this analysis. | Already tracked as P13 / C14. Not new. |
| **Q-CT6** | Whether the quarterly r.3(1)(c) reminder job is **implemented**, not just specified. | It is specified in `ADR-001` and `DATA-MODEL` §1267 as `QUARTERLY_RULES_REMINDER`. **I did not verify it runs.** The obligation attaches from the first real user. | One grep by the CTO. I am flagging it rather than claiming either way. |

**Nothing in this document is a verified claim about a rule I did not read.**
Where I read a reproduction rather than the Gazette I said so in the sentence.

---

## 6. Does this need a lawyer before launching to anyone?

**Shape 1: no, and I will say that plainly rather than hedge.** Every
obligation I have named for a no-sale closed test is one I read from rule text
I have cited: a published privacy policy, published terms and platform rules, a
named grievance officer, and the in-force clocks. None of it requires drafting
judgement that a careful non-lawyer cannot execute with a template.

**One caveat that is not a hedge:** a liability clause written by a non-lawyer
is worth less than nothing, because it reads as protection and is not. If the
terms published for shape 1 contain any limitation of liability, any safety
warranty, or any indemnity, **that specific text needs counsel** — and
`COMPLIANCE.md` P10 already forbids safety warranties in any copy, which is the
cheapest way to stay on the right side of this.

**Shape 2: yes, before the first completed sale.** Incorporation, a seller
undertaking, and the C2C seller-address question (`COMPLIANCE.md` §2.4, counsel
C2) are decisions with money and personal liability attached. **The founder
should not take them on my reading of a proviso.**

**And one thing that needs no lawyer and is the actual blocker:** §1. Until
real account creation refuses without a named human's Gate B row, the size of
the Gate C field list is not the live question.

---

## 7. Recommendation to the founder, in four lines

1. **Decide shape 1 or shape 2 first.** It is the only decision that changes the answer, and shape 1 is both cheaper and probably the better experiment with twelve friends.
2. **Build the Gate B guard** (B9′, one function) and the Gate B evidence trigger. This is required at either shape and is the §1 finding.
3. **Start the incorporation filing now anyway** — four-week lead time, off the critical path at shape 1, personal liability either way.
4. **Buy Q-CT1 and Q-CT2 as two lines in the counsel C1/C2 brief.** They are the cheapest legal spend available and they decide whether step 3 is a blocker or a background task.

**Founder authority is unchanged.** Legal commitments and public launch remain
reserved (README §2). This document advises; it decides nothing.
