# Decision Log

One entry per consequential decision. Owner: CEO / Planning Agent.
A decision without evidence and a reversal trigger is not recorded as decided.

Format: Context · Options · Evidence · Red Team · Decision · Reversal trigger.

---

## D-001 — Agent organization created as persistent definitions
**Date:** 2026-10-21 · **Decider:** ceo-planning

**Context.** The program needs distinct agents with separate charters and
working contexts, not one agent role-playing eight hats.

**Options.** (a) Role-play in a single context. (b) Persistent agent
definitions on disk, invoked as distinct subagents. (c) Ad-hoc subagents with
no written charter.

**Evidence.** Working directory was empty; no prior project or instructions.

**Decision.** (b). Eight standing charters written to `.claude/agents/`:
ceo-planning, product-manager, design-director, cto, market-finance,
marketplace-ops, privacy-compliance, red-team. Specialist agents are created
by their owner immediately before their work begins, per charter — not
up front.

**Reversal trigger.** If charters go unread by the agents that own them for
two consecutive weekly reviews, collapse the org and re-scope.

---

## D-002 — Phase A runs before any product or code work
**Date:** 2026-10-21 · **Decider:** ceo-planning

**Context.** The brief supplies a plausible thesis and four planning numbers
(5 lakh Chennai students, 20% participation, 2 transfers/year, Rs 300 book
value) that are explicitly unverified.

**Options.** (a) Build the obvious MVP now, validate later. (b) Evidence
first, build after G1.

**Evidence.** The riskiest assumptions — liquidity, disintermediation, fee
viability on a Rs 100-300 item, seasonality — are all cheap to test and
expensive to discover after building.

**Decision.** (b). No schema, no UI, no stack choice until Phase A evidence
is in and Red Team has reviewed it at G1.

**Reversal trigger.** If Phase A research cannot reach a defensible Chennai
denominator within one working cycle, escalate to founder rather than
proceeding on assumptions.

---

## D-003 — Credit-based exchange is designed, not released
**Date:** 2026-10-21 · **Decider:** ceo-planning + privacy-compliance

**Context.** A credit system removes the need for a perfect two-person swap
match, which is the core weakness of direct exchange.

**Decision.** Design it in the data model. Do **not** release any credit that
is cash-purchasable, transferable, or redeemable before privacy-compliance has
reviewed it against RBI PPI rules and the unit economics are modelled. A
non-cash, non-transferable, auditable pilot may be proposed after that review.

**Reversal trigger.** Compliance review concludes the mechanism is a PPI and
we are unwilling to meet the obligations — then direct swap only.

---

## D-004 — No custody of funds, ever
**Date:** 2026-10-21 · **Decider:** cto + privacy-compliance

**Decision.** BookHop will not build escrow and will not hold seller funds.
Any in-app payment uses an approved provider that settles directly, and only
once provider, economics, and compliance prerequisites are satisfied and the
founder has authorized activation.

**Reversal trigger.** None at pilot scale. Revisit only with counsel.

---

## D-005 — Agent registry constraint and the fallback actually used
**Date:** 2026-10-21 · **Decider:** ceo-planning

**Context.** The eight charters were written to `.claude/agents/`, but the
Agent tool's registry is loaded at session start. Invoking `market-finance`,
`privacy-compliance` and `product-manager` as subagent types returned
"Agent type not found" — the definitions exist on disk but are not selectable
until a new session.

**Decision.** Use the fallback the founder's brief specifies: keep the
charters as the persistent, reusable definitions, and invoke each agent as a
distinct subagent with a separate working context, pointed at its own charter
file path and required to read it before acting. Each agent still has one
charter, one owner, one set of deliverables, and its own context window.

**Recorded honestly:** Phase A agents ran as distinct subagents reading their
charters, NOT as registry-registered agent types. From the next session the
charters should be directly selectable; `CLAUDE.md` tells future sessions to
try the charter name first and fall back the same way if needed.

**Reversal trigger.** If the registry picks the charters up, drop the fallback
and invoke by name.

---

## D-006 — G1 (Strategy gate): PASS WITH CONDITIONS
**Date:** 2026-10-21 · **Decider:** ceo-planning, after red-team review
**Evidence:** `evidence/COMPETITORS.md`, `evidence/MARKET-SIZING.md`,
`evidence/COMPLIANCE.md`, `product/DISCOVERY.md`, `finance/MODEL.md`,
`evidence/RED-TEAM/G1-MEMO.md`

**Context.** Four agents produced Phase A evidence. Finance concluded the
business is unsustainable with no breakeven at any volume. Red Team was asked
to attack that conclusion as hard as the optimistic one.

**What Red Team established by re-running the model (14 CAC sweeps).**
"No breakeven at any volume" is a property of model construction, not a
measured property of the business. The model is strictly linear: contribution
per transfer is Rs 9.11 at one campus, at three campuses, and across all of
Chennai metro — identical to the paisa. It contains no mechanism by which the
unit can improve with density, automation, or CAC decay, so "growth makes it
worse" is tautological rather than a finding. At HIGH drivers the verdict does
turn on CAC (breakeven Rs 12.29/registered user); at BASE it does not, and
Finance is right about base.

**Decision — recorded by the CEO agent within its authority:**

1. **The 6% transaction-fee monetisation thesis is FALSIFIED.** Minimum take
   rate to cover support and payment processing alone is 16.7% at base. Red
   Team tried and failed to break this: pushing average price to Rs 500 moves
   marginal contribution only from −Rs 8.83 to −Rs 4.79. This is the most
   solid negative finding in Phase A.
2. **The company thesis is NOT killed.** The evidence kills a revenue model,
   not the product. Killing the company on two never-observed inputs, using a
   model that cannot represent improvement in either, is precisely the mistake
   this gate exists to prevent.
3. **No code is written before Test 1 (concierge pilot) returns.** No schema,
   no stack choice, no UI. Phase B and C stay closed.
4. **Product applies Red Team objections O-6 to O-9 before booking any
   interview.** T2's kill threshold can pass by selection because the screener
   admits people for having paid for a book; T3 cannot fail as written
   (unprompted, conjunctive, 50% threshold). Research into gift share and swap
   share is misallocated — across their entire range they move the unit by
   Rs 0.56 and Rs 0.79. Fixes expire the moment fieldwork starts.
5. **Finance restates MODEL.md §1, §8 and §11** to say explicitly that the
   base-case verdict holds independent of CAC, that the model is linear with
   no density mechanism, and that §8's "growth is the problem" is a total, not
   a unit — per transfer, raising activation 0.30 to 0.90 improves the unit
   2.7x.
6. **Finance's institutional/buyback recommendation is NOT adopted as
   strategy.** It carries zero sources and buyback is contradicted by the same
   file's finding that Bookchor's Dump arm is Delhi-only after ten years. It
   survives only as a hypothesis with a test attached.

**Escalated to the founder — not decided here.** See `G1-FOUNDER-PACKET.md`.
Four items require founder authority or founder information: incorporation,
campus access and interview budget, the scope cut, and the monetisation
direction.

**Critical objections recorded (per Red Team charter, both escalate):**
- **O-1** — "No breakeven at any volume" is a construction, not a finding.
  *Status: accepted. Resolved by conditions 1, 2 and 5.*
- **O-10** — **Inspect-before-pay IS the disintermediation event.** Compliance
  mandates inspect-before-pay because BookHop holds no money and therefore
  cannot refund; Finance identifies in-person settlement as the revenue hole.
  They are the same thirty seconds. No driver value resolves this.
  *Status: accepted and unresolved. This is new — neither R-02 nor R-03 states
  it. It is the single strongest argument against ever charging the student
  side, and it is why condition 1 is a falsification rather than a repricing.*

**Reversal trigger.** If Test 1 returns fee collection >=40% with the fee arm
completing within 10 percentage points of the free arm, O-10 is weaker than
stated and student-side monetisation returns to the table.

---

## D-007 — Founder approves all four G1 packet items
**Date:** 2026-10-21 · **Decider:** HUMAN FOUNDER (reserved authorities exercised)

**Context.** `G1-FOUNDER-PACKET.md` put four items to the founder. All four
approved as recommended, in writing, in session.

**Approved:**
1. **Start incorporation.** Private limited company, per E-Com r.4(1)(a).
   Unblocks the pilot. Founder owns the filing; agents produce the checklist
   and the dependency sequence only.
2. **Campus access plus Rs 16,500.** Covers 18 interviews at Rs 200, the
   concierge pilot (Test 1), and contingency. **This is the first approved
   spend in the programme.** No agent may exceed it or commit further funds.
3. **Cut direct swap and general reading from v1.** This REVERSES the scope in
   the founder's original brief, on the founder's own authority after seeing
   the antiphase evidence. Both remain in the data model; neither ships in v1.
4. **Run the Rs 0 librarian probe** testing the institutional-payer
   hypothesis. Authorised as a test only — the direction is not committed.

**What this does NOT authorise.** No code (D-006 condition 3 stands until
Test 1 returns). No payment provider. No public launch. No campus agreement
signed by an agent. No credit of any design.

**Consequences recorded:**
- v1 scope is now **buy and sell, edition-locked prescribed textbooks, one
  campus**. Swap and general reading are deferred, not deleted — the data
  model must still accommodate them (CTO constraint at Phase C).
- Red Team objection O-10 (inspect-before-pay IS the disintermediation event)
  remains open and unresolved. Test 1's fee A/B is the instrument that
  addresses it.
- Budget ledger opens at Rs 16,500 approved, Rs 0 spent.

**Reversal trigger.** Test 1 returning fee collection >=40% with the fee arm
completing within 10pp of the free arm reopens student-side monetisation.
Swap returns to scope if Test 1 shows swap-only users are the cheapest supply.

---

## D-008 — Test 1 kit accepted; three agent deviations ruled on
**Date:** 2026-10-21 · **Decider:** ceo-planning
**Evidence:** `ops/TEST-1-CONCIERGE-PILOT.md`, `ops/INCORPORATION-AND-BLOCKERS.md`,
`product/DISCOVERY.md` v0.2, `finance/MODEL.md` v1.1, `evidence/INSTITUTIONAL-PROBE.md`

All four D-007 workstreams delivered. Three agents raised deviations needing a
CEO ruling rather than acting unilaterally. All three rulings below.

**Ruling 1 — Operations' §2.4 narrowing of the reversal trigger: ACCEPTED.**
D-006 and D-007 set a reversal trigger that would reinstate student-side
monetisation on fee collection >=40%. Operations points out that under the
Compliance-mandated cash-only design, fee-paid ÷ fee-asked is two unverifiable
self-reports, money kept inside the pair is a transfer rather than a fee, and
the high side always has an advocate. Its rule — **a low number is credible, a
high one is not** — is correct. The trigger is amended: a fee-collection pass
**reopens the question and justifies a second, funded, counsel-cleared test.
It does not reinstate the fee.** A fee-collection *failure* remains fully
informative and confirms D-006 condition 1.

**Ruling 2 — Red Team O-10 is NOT resolved. Operations' framing stands.**
Compliance argued O-10 dissolves because inspect-before-pay only mattered as a
revenue leak and there is no fee revenue. Product argued the cost shifted to
the completion record the institutional-payer thesis depends on. Operations
settled it on measurement grounds, which beats both: **the real O-10
observable is repeat transfer at 90 days, and a 14-day pilot structurally
cannot see it.** O-10 therefore stays OPEN, re-scoped from a revenue risk to
an evidence risk, and Test 1's leakage band is an indicator, not a resolution.
Recorded as risk R-24.

**Ruling 3 — Finance's refusal to add a density mechanism (R-23): UPHELD.**
Any curve specifiable today has a free parameter no evidence constrains, and
Finance would be choosing the shape knowing the answer it produces. The model
stays linear, now with a self-asserting linearity check in `model.py`, and
R-23 is licensed to close only on the pre-committed rule: support minutes per
handover by sequence number over >=30 Test 1 handovers.

**The finding that most changes the picture, and it is bad news.**
Operations calculated that passing its own support threshold of 4.00 minutes
implies roughly **Rs 11.36 per transfer — which confirms Finance's Rs 12
assumption rather than refuting it.** The model needs Rs 6, i.e. 2.11 minutes.
CEO verification: Rs 11.36 / 4.00 min = Rs 2.84/min, so Rs 6.00 = 2.11 min.
Arithmetic confirmed independently.

**Consequence, recorded so nobody misreads a pass later: passing Test 1 does
not make this viable.** It establishes that support cost is not catastrophic.
Viability needs roughly half the passing time. "Not catastrophic" is not
"viable", and that sentence is written into the result template.

**Other items accepted without amendment:**
- Gate A (concierge pilot) needs **neither incorporation nor legal spend** —
  Test 1 is unblocked and waits only on campus contacts.
- Incorporation at Rs 8,000-20,000 is **outside** the D-007 Rs 16,500 envelope
  and is a separate founder spend. Escalated, not absorbed.
- Private limited confirmed; needs **two members and two directors**. OPC is a
  reversible fallback. s10A bars commencing business until INC-20A is filed.
- **s194-O survives the free-to-student change.** The CEO agent's hypothesis
  that it might fall away was wrong; the deeming provision has no consideration
  limb and the threshold is nil. **Not storing a settled transaction price is
  now the most important schema constraint in v1** (P14, binding on CTO).
- **Copyright risk rose** because cutting general reading concentrated v1 onto
  prescribed textbooks. The scope cut was not a risk reduction.
- Product retired threshold T4, declined Red Team's counter-persona kill limb
  (floating denominator) and the three-card concept test (forced choice between
  cards we designed). All three declines accepted.
- Counsel C1-C3 to be bought as **one** scoped engagement. C9 (PPI) and C10
  (GST) are dormant — paying for them now is the cheapest sequencing mistake
  available. **No legal spend is authorised; this is a recommendation for the
  founder, not a commitment.**

**Budget ledger:** Rs 16,500 approved · Rs 0 spent · Test 1 costed at Rs 9,100
(Rs 2,500 if the founder operates) · Rs 5,000 ring-fenced for interviews ·
Rs 2,600 unallocated. Incorporation separate and unapproved in amount.

**Still blocked on exactly one thing: three named campus contacts.**

---

## D-009 — Founder overrides the code gate; Phase C opens
**Date:** 2026-10-21 · **Decider:** HUMAN FOUNDER (overriding D-006 condition 3)

**Context.** D-006 condition 3 blocked all code until Test 1 returned. The
founder has directed that the app be built and that launch happen with the app
itself rather than with a paper concierge pilot.

**Decision.** Build. Phase C opens now. D-006 condition 3 is **superseded by
founder decision**, which is within the founder's authority.

**The CEO agent's concern, stated once and recorded, not re-argued.**
Support cost per transfer (Rs 12 assumed) remains unmeasured and is the single
input most likely to sink the unit economics: Operations' own 4.00-minute pass
bar implies Rs 11.36, confirming the assumption rather than refuting it, and
the model needs Rs 6 (2.11 minutes). We are therefore building before knowing
whether a transfer can be supported profitably.

**Mitigation adopted instead of delay.** The app is instrumented to measure
support time, match rate, time to match, completion and leakage directly, so
the product becomes the measurement instrument and Test 1's questions get
answered by real usage rather than by a spreadsheet. This is strictly better
data than the concierge pilot would have produced, provided the instrumentation
ships in the first slice rather than being retrofitted.

**What this does NOT change.**
- **G4 public launch remains a founder gate** requiring the go/no-go packet
  (security, privacy, accessibility, legal and tax review, payment readiness,
  terms, support, backups with tested restore, operating costs, unresolved Red
  Team objections). Building does not pre-authorise launching.
- **Gate B still binds before listings are shown to real students**:
  certificate of incorporation, INC-20A, grievance officer, takedown SOPs, and
  counsel C1-C3. A browsable listing surface makes BookHop an e-commerce
  entity under r.4(1)(a), which requires the company to exist. Code may be
  written and tested against seed data meanwhile.
- **P14 is binding on the schema: never store a settled transaction price.**
  Record an asking price fixed at intake. s194-O survives the free-to-student
  change and its threshold is nil.
- v1 scope stands at buy and sell, prescribed textbooks, one campus (D-007).
  Swap and general reading stay in the data model, out of the UI.
- Student side free. No fee, no escrow, no custody, no credits.
- Test 1's instruments are NOT discarded. The interviews, the survey and the
  institutional probe are independent of the build and still unrun.

**Reversal trigger.** If instrumented support time per transfer exceeds 4.00
minutes once there are 30 real handovers, the unit economics are confirmed
broken and the monetisation question returns to the founder before any
spend on growth.

---

## D-010 — CTO contracts accepted and frozen; two escalations
**Date:** 2026-10-21 · **Decider:** ceo-planning
**Evidence:** `company/architecture/` (9 documents), `.claude/agents/` (5 new charters)

**Accepted and frozen.** Django 5.2 LTS + PostgreSQL 16 + server-rendered HTML
with htmx, one modular monolith on one Linux VM in an Indian region.
Postgres-backed job queue; no Redis, no Celery, no SPA build, no SMS vendor.
Magic-link auth against the campus email domain, which collapses account
identity, campus verification and "no password to steal" into one mechanism.
Runner-up was Rails 8, rejected on Windows developer experience and the admin.

The reason accepted as decisive: every artefact Gate B blocks on — consent
ledger, age-gate audit trail, tombstone-plus-purge deletion, the takedown
clocks, repeat-infringer record, personal-data access log, moderation queue,
support stopwatch — is a back-office CRUD-and-audit problem, and Django gives
us that console for free where every rejected stack puts it on the critical
path as bespoke work.

**Five specialist agents created** before their work began, per the CTO
charter: backend-developer, frontend-developer, code-review, test-qa,
platform-sre (dormant until S8). Code Review writes no application code and
must refuse any diff it authored. Test & QA writes tests from specification
without reading the implementation and never fixes production code.

**Design properties recorded as load-bearing:**
- **Double-booking is prevented by a database constraint**, a partial unique
  index on `transfers(listing_id)` over the active states — not application
  locking. Second accept gets 409.
- **The discovery gate is data**, not a settings flag: `discovery_enabled_at`
  defaulting NULL, an evidence-gated command, append-only `gate_authorisations`,
  and a CHECK constraint making seed-to-real transactions impossible. This is
  what makes building before incorporation lawful.
- **P14 is enforced mechanically** — a CI deny-list test plus a database
  immutability trigger, not a policy note.

### Escalation 1 — infrastructure cost exceeds the entire programme budget
Rs 0 to build and test every slice locally. Pilot hosting is Rs ~630/month
minimum, Rs ~1,750/month recommended (the difference is off-site backup, so
that a restore survives the founder's laptop dying). That is **Rs ~20,580/yr
against a total approved budget of Rs 16,500.**

**CEO position, aligned with the CTO's: approve nothing now.** Cost of delay
is zero until Gate C, because the discovery gate means every slice can be
built and tested locally for free. Choose the tier when Gate B's legal
preconditions are close. Recorded as an escalation so it is not discovered
later as a surprise.

### Escalation 2 — Phase B was skipped and the sequencing is wrong
The CTO froze contracts with **no PRD, no journeys and no design system in
existence**, and flagged that G2's entry criteria are therefore not met by its
work alone. This is a direct consequence of D-009 opening Phase C early.

**Action taken rather than deferred:** product-manager is writing the PRD and
journeys and design-director is producing two visual directions plus the design
system, both concurrently with backend slice S0, which is backend-only and has
no design dependency. Frontend work does not start until the design system
exists. The cost of the wrong order is that the contracts came first and the
PRD must now either fit them or escalate a contract change — the PRD is
required to say explicitly where it disagrees.

**Local environment constraint discovered:** this machine has Python 3.11.9
only. **No PostgreSQL, no Docker.** Installing system software is the
founder's decision, not an agent's. Backend is building a SQLite dev/test path
with Postgres as the production target, and must produce
`architecture/ENGINE-DIVERGENCE.md` stating for every divergence whether a
property is genuinely verified locally or merely assumed — the double-booking
guard in particular, because verifying it on the wrong engine would be worse
than admitting it is unverified.

**Unresolved and carried:** s194-O (asking price plus completion boolean may
still be a determinable gross amount — routed to compliance); CERT-In log
residency on a foreign-owned Indian region (CTO's own reading, moderate
uncertainty, routed to compliance); ASVS L2 not fully achievable solo, V15 and
key management declared as gaps for the G4 packet; admin insider risk accepted
as A1, since at one staff member the two-person disclosure rule blocks rather
than reviews.

---

## D-011 — Design direction chosen; Tamil locale gated
**Date:** 2026-10-21 · **Decider:** ceo-planning, on design-director's recommendation
**Evidence:** `company/design/` (DIRECTIONS, SYSTEM, COPY-DECK, USER-TEST-PLAN, tokens.css)

**Direction A "Catalogue Card" adopted.** The interface is a bibliographic
record: the book's exact identity is the hero, and every human claim about it
appears as an attributed quotation rather than a platform fact.

**The deciding reason is not aesthetic and is recorded as such.** Direction B's
whole-screen institutional colour field reads as the platform asserting
something, and asserting is the one thing we may not do. A's grammar — a record
stating who said what and when — is the visual form of not vouching. It also
makes edition evidence scannable, which is the only wedge that survived Phase A,
and costs ~30 KB for 30 text results over 3G.

Taken from B anyway: one decision per screen for the whole handover flow, and
the transfer docket pinned above the home search field while a handover is live.

**Trust without warranting — solved, and this is the answer to the programme's
worst asymmetry (R-16, the more we verify the more we own).** Four mechanisms,
no badge: condition rendered only inside the seller's quoted sentence;
checkable facts instead of adjectives ("Signed in with a @___.ac.in address");
a required "what's wrong with it?" field, because a listing that volunteers a
defect is more believable than one that boasts; and the disclosure "Nothing
here is checked by BookHop. Look at the book before you hand over any money"
at the same type size as the offer button.

**Governing rule, adopted project-wide and testable in review:** *BookHop's
voice may describe a mechanism, name a fact, or give an instruction — never a
prediction or a judgement.* "Worth your while" was deleted rather than
translated, because it is a prediction and failed the rule in English too.

**Verified, not claimed:** all 27 Direction A colour pairs computed with the
WCAG relative-luminance formula, zero failures, lightest text 5.28:1, control
borders 3.55:1. No touch target under 44px. All ~27 components specified
across eight states plus `gate-closed`. Direction B's one contrast failure was
reported and fixed rather than hidden.

**No Tamil webfont.** The device's own Noto Sans Tamil via the system stack —
on 3G a Tamil webfont is 40-90 KB buying nothing perceptible at 17px. Tamil
gets its own line-height and tracking rules via `:lang(ta)`.

### GATE: the Tamil locale is not offered to students until native-speaker sign-off
Three blocking classes: handover guidance (a mistranslation here is a safety
and liability problem), every no-warranty string, and the legal and rights
flows. **Recorded as risk R-29.** The reason this is a gate and not a to-do is
TR-8: the forbidden-word test greps English only, so a Tamil string that
warrants would pass clean — the control reports green while the exposure
exists. Routed to the CTO to make mechanical.

### Escalation — user test is Rs 2,700-3,900 against Rs 2,600 unallocated
Over budget by Rs 100-1,300. **No spend committed.** A Rs 0 four-session
variant is specified with its voided limbs named. Founder decision.

**Recorded because it is unusual and good practice:** the Design Director
wrote down, before running anything, that it **expects** its own central probe
to trip — P1, "what has BookHop promised you here?", coded W0/W1/W2. A
pre-registered expectation of failure is worth more than a passed test.

**Also noted:** the DIRECTIONS §5.1 performance figures are marked estimates,
not measurements. Nothing has been built or profiled. They must not be quoted
as results.

---

## D-012 — Gates re-cut to four; two CEO statements corrected
**Date:** 2026-10-21 · **Decider:** ceo-planning, on privacy-compliance v1.1
**Evidence:** `evidence/COMPLIANCE.md` v1.1, `ops/INCORPORATION-AND-BLOCKERS.md` v1.1

**Gates re-cut, letters kept** (renaming would invalidate D-009, ADR-001,
ADR-002 §4, `gate_authorisations` and TASKS.md):

| Gate | Event | Status |
|---|---|---|
| **A** | Build | **OPEN NOW** |
| **B** | First real user's data enters the system | pending |
| **C** | Discovery opens — a real student sees another's listing | pending |
| **D** | Public | pending |

The old Gate B definition "any code may ship" was wrong: **shipping to a box is
not a legal event.** A real person's data entering the system and a real
student seeing another's listing are two different events, weeks apart.

### The key finding, and it moves work EARLIER
**IT Rules 2021 intermediary status attaches at the FIRST REAL USER, not the
first browsable listing.** One real listing or message breaks the condition
under which we were not an intermediary; s2(1)(w) needs no browsable surface.
So published rules, a **named Grievance Officer**, the 2h/3h/24h/7d clocks,
r.3(1)(j) 180-day preservation and the quarterly reminder all move to Gate B.
**s79 safe harbour — the thing that protects us from a user's pirated listing
— is conditional on them.**

It does **not** drag incorporation earlier: the founder may be that officer in
their own name. Counsel C1 moves to before the first real signup, and
infrastructure spend becomes possible at Gate B, earlier than INFRA.md assumed.

### Two CEO agent statements corrected — recorded, not quietly fixed
1. **D-008 said "still blocked on exactly one thing: three named campus
   contacts." That is no longer true.** Campus permission (A1/P11) blocks
   nothing until Gate C. The build is not waiting on it.
2. The brief issued to compliance asserted the tombstone salt is what makes
   repeat-transfer-at-90-days measurable. **Wrong.** `users.pseudonym` does
   that; the salt serves `email_hash` for ban-evasion only.

### Rulings accepted
- **CERT-In: the CTO was right.** An Indian region of a foreign-owned provider
  satisfies Direction (iv), on two independent grounds including CERT-In's own
  FAQ Q35. Uncertainty MODERATE → LOW. **Do not move providers, do not spend
  the hedge.** Clean because ADR-001 §3 rejected hosted error tracking and
  analytics — every log we owe sits on a filesystem we control.
- **s194-O: the construction HOLDS**, HIGH → MODERATE, on CBDT Circular
  20/2021 (e-auction): five of six limbs satisfied by design, the sixth
  concerning a fee we do not charge. Compliance recorded that its own v1.0
  claim that no circular addressed this was wrong.
- **The asking price must be genuinely negotiable, and the copy must say so** —
  P14's immutability makes it a better settled-price proxy, which weakens the
  circular's second limb. **This limb lives in copy; the schema cannot carry
  it.** Routed to design-director.
- **The P14 money rule inverts from a blacklist to a whitelist**: assert
  `listings.asking_price_paise` is the only monetary column in the database.
  Nine test requirements in COMPLIANCE.md §4.3.2; items 3, 4 and 9 are
  load-bearing. Routed to the CTO. Item 4 — forbid offer, bid and negotiation
  amounts, because **an accepted offer amount IS a settled consideration and
  is the most likely next feature** — is the one the CEO agent would have
  missed.
- `messages.contact_pattern_flag` basis is legal obligation, **not** consent:
  if withdrawable, withdrawal becomes a tool for a harasser.
- **The repeat-transfer-@90d undercount of delete-and-rejoin users is the
  price of honest deletion and must be reported, never fixed.** Closing it
  would be purpose creep and would make "delete my account" false.

### D-009 created three new exposures, stated plainly
(a) A durable personal-data estate that must be DPDP-compliant on 13 May 2027
with no transition — best mitigated, since consent, purge and access-log are
in the first slices. (b) Intermediary and copyright exposure arrive earlier
**and the control got weaker** — an operator who saw every book beats a
moderation queue, so `suspect_reproduction_flag` must default to review and
not be disableable for throughput. (c) The s194-O argument is unchanged but
the **evidence available to anyone who disagrees is now excellent** — a
joinable Postgres beats a 30-row sheet.
D-009 also **removed** one: the paper pilot's likeliest incident was a shared
spreadsheet of student names and numbers with no logging, retention or
deletion capability. Rigour runs both ways.

### FOUNDER DECISION FRAMED — not decided here
**Do real users arrive before discovery opens (separate Gate B) or with it
(B and C collapse)?** Compliance recommends collapsing unless the founder
specifically wants support-minutes data early, because **match rate, time to
match, completion and leakage are all two-sided and none is measurable before
discovery opens** — a closed beta buys support minutes and little else. A
separate Gate B means earlier counsel, earlier spend, and a longer reliance on
a MODERATE reading. Gate A is open either way; the build is not blocked.

---

## D-013 — CTO triage: all 16 amendments accepted; two CEO corrections
**Date:** 2026-10-21 · **Decider:** ceo-planning, recording cto's triage
**Evidence:** amended `company/architecture/`

Twelve amendments from three agents, all landing **before** the code that
implements them. "Contracts before parallel work" held under load. Net effect
on the critical path: **none** — S3 and S5 gained work, S7 lost it, S1 lost a
table, S0 gained four assertions.

**Accepted with consequences the proposers had not seen** — recorded because
each was a silent corruption, not a style point:
- **Reschedule (CG-1)** also requires `reservation_expires_at` to reset to
  +48h, or the expiry job kills the transfer within the minute; `accepted_at`
  must be write-once, or every rescheduled transfer looks like it matched days
  late; and every "ever reached state X" denominator needs
  `COUNT(DISTINCT transfer_id)` with match rate on **first** ACCEPTED.
- **CG-2 was a contradiction inside the CTO's own contract**: METRICS and
  §11.3 both say the mitigation fails if support goes off-platform, while the
  contract shipped no on-platform door and a `channel='IN_APP'` nothing could
  produce. Moved S6 → S5. Reply cap set at 60/hour rather than 10/day,
  because a daily cap breaks a conversation mid-problem — the exact failure
  being prevented.
- **CG-4 exposed a flaw in the slice order**: notifications move S7 → S3,
  because S4/S5/S6 all generated events with nowhere to notify. Two guards the
  PRD lacked: **`match_scan` no-ops on a closed gate**, since notifying a
  student that a listing exists *is* showing them a listing — CG-4 was a
  notification-shaped hole in the legal gate.
- **CG-5 taken further: `age_check_pending` is deleted.** No DOB is persisted
  in any state. With no ID collected, a reviewer cannot verify a date against
  anything, so storing it buys no information and costs a week of retention.
  The logged review reviews the account, not the date.
- **CG-6, which nobody routed and the CTO found in its own gap**: the relay
  had no function, no endpoint and no kind — and the relay is the mitigation
  for the CTO's own accepted risk A1.

**TR-8 resolved as two controls for two different threats**, after
establishing that a word list cannot work: morphology defeats stems, a ban
broad enough to work breaks the privacy notice's legally required vocabulary,
and the concept is subject-dependent. **English stays a whole-word deny-list;
Tamil becomes an allow-list** of reviewer-signed strings keyed by hash, because
the Tamil vocabulary is closed and the real threat is an unreviewed string
shipping, not a developer typing a bad word. The gate is mechanical:
`i18n.ta_enabled` defaults false and a test keeps it false while any
blocking-class string is unreviewed — the same shape as the campus gate,
default closed, named human on the record. **What stays human and must not be
read as covered: the grammatical rule is ungreppable in any language** —
"Trusted seller" contains no banned word. Now a Code Review checklist item.

**P14 inverted to a whitelist**, and the CTO judged compliance's design better
than its own. `asking_price_paise` is the only money column; every other
numeric column must carry a declared non-monetary suffix. **Book value moved
is renamed `asking_price_sum_paise`** and never renders without its
disclaimer, because a report headed "value of books sold" *is* BookHop
asserting those books sold for those amounts.

**The negotiability paradox resolved:** immutability stays, because a mutable
price with no history literally records the price at transfer time and is
worse. **Refusing to store a negotiation is what makes it real** — a
counter-offer field would make negotiation visible to us and destroy the
structural argument that we know no amount.

### CEO correction 1 — the CTO's Rs 0 Postgres route does not exist yet
The CTO ruled SQLite acceptable for S0/S1 only, gating **S2 on a reachable
PostgreSQL 16**, and directed that this is "a CI service container at Rs 0 —
not a founder spend escalation and must not be routed as one."

**Verified by the CEO agent: this project is not a git repository, has no
remote, and has no CI configuration of any kind.** The git binary exists
(2.56.0). So the free CI route is not available today; it presupposes
infrastructure nobody has set up. The ruling's *substance* stands — this is
not a spend question — but it is a **founder decision about their machine and
their accounts**, not a no-op. Options: install PostgreSQL 16 natively on
Windows (free, local, no third party), or initialise git plus a remote with CI
(free, but puts the code with a third party and needs their account).

### CEO correction 2 — the work has no version control
**Roughly 500 KB of evidence, contracts, PRD, design system and code exists
with no history and no recoverable prior state.** Not a git repo. An agent
overwriting a file is currently unrecoverable. `.gitignore` exists, which
means the backend agent assumed a repo that is not there. Flagged to the
founder; `git init` is local, free and involves no third party, but creating
the repository is the founder's call.

**Recorded as good practice:** the CTO credited the backend agent for finding a
hole in the CTO's own audit design — Postgres row triggers do not fire on
TRUNCATE, a gap SQLite could never have revealed — and adopted a standing
rule: **a guard test runs on both engines or skips with a reason naming the
engine, because a silently-passing guard is worse than no guard, since it is
reported as coverage.**

**OQ-1 recorded so swap is not archaeology:** a swap reserves two listings
against a per-listing unique index. Two designs costed; the CTO leans to one
transfer plus `counter_listing_id`, because two linked transfers would
double-count every swap in completion, leakage and repeat transfer. Not
designed — the trigger is a D-007 reversal.

**G2's entry criteria are now satisfiable:** the PRD and design system exist.

---

## D-014 — Negotiability limb closed in copy; one escalation already satisfied
**Date:** 2026-10-21 · **Decider:** ceo-planning, recording design-director v1.1

**The limb the schema could not carry is now carried by copy**, worked through
all four design documents. The string doing the real work is shown to the
**seller at intake**, not the buyer: a buyer-side disclaimer makes
negotiability *claimed*, whereas telling the seller their number is a starting
point is what makes it *true*. The price label became a question — "What are
you asking for it?" — so the grammar does the work before any hint text.

**Recorded because it reverses an ordinary assumption:** refusing to store a
negotiation is what makes the negotiation real. A counter-offer field would
make negotiation visible to us and destroy the structural argument that we
know no amount.

**Two rules design added unprompted and the CEO agent endorses:** no rupee
figure in any notification or email, because a number without context reads as
an amount due; and the confirmation copy extended to "we don't ask what you
paid, **and we don't record it**", placed at the one moment a student most
expects to be asked for a figure.

**Design's escalation to the CTO is already satisfied** — it recommended
`offer_amount`, `counter_offer_amount`, `bid_amount` and `agreed_price` go on
the forbidden-schema whitelist, which is exactly compliance item 4, already
accepted by the CTO in D-013. Closed, not open. Its reasoning stands as the
better justification of the control: **copy cannot defend a column that
exists**, and a UI rule is the weakest possible place for the limb, because
the next agent to read the PRD and not the design files will propose the
column in good faith.

**TR-8 now carries two legal exposures, not one.** The forbidden-copy test
greps English only, so a Tamil string that warrants passes it **and** a Tamil
string reading as a fixed price passes it — one blind spot, a liability
exposure and a tax exposure. Tamil blocking class B4 added. Design notes
`விலை` cannot be banned: it is the ordinary word for price and appears in
every approved string. Risk R-29 updated in scope.

**Deliberately separated:** the handover-guidance copy (liability artefact) and
the price copy (tax artefact) are kept in different blocks so one reviewer
does not sign off both.

**Open, routed to privacy-compliance, not decided by design:**
1. `trust.campus_mail` — "Signed in with a @___.ac.in address". Blocked in
   English and Tamil pending a ruling. **Compliance's silence is explicitly
   not treated as approval.** Cost recorded rather than softened: without it a
   listing shows only display name and campus, removing the best non-vouching
   trust signal we have.
2. **May BookHop's own copy invite a buyer to name a figure?** Design declined
   to decide. Inviting a figure makes negotiation more visible and strengthens
   the limb; it also creates reconstructable amounts in stored message bodies,
   which is the reconstruction trap. The product is currently paying a
   usability cost for a risk that may not exist.

**Pre-registered against its own work:** design added a probe asking a
participant looking at a Rs 280 listing what they think they would actually
pay, and committed that if 3 of 8 answer "Rs 280, that's the price", it comes
to compliance and the CEO agent as a compliance finding **before** design
iterates — on the grounds that we may then need a stronger control than copy.
Endorsed.

---

## D-015 — Both blocked strings ruled on; compliance corrects its own counsel brief
**Date:** 2026-10-21 · **Decider:** ceo-planning, recording privacy-compliance v1.2

**Ruling 1 — `trust.campus_mail` SHIPS as "Signed in with a college email
address", domain removed.** The vouching limb passes and not narrowly: it
describes a logged mechanical event, not a judgement — the same shape as the
deck's own passing example "Priya wrote this 3 days ago". Design's reading was
confirmed rather than second-guessed. Three conditions:

1. **Never render the literal domain.** A campus may run `student.x.ac.in`
   alongside `x.ac.in`, or per-department or per-intake domains, so showing
   *which* domain can disclose student-versus-staff status, department or
   intake year — attribute disclosure smuggled in as a trust badge. And it
   buys nothing: the campus is already on the listing and in v1 the domain is
   identical everywhere, so it discriminates between nothing.
2. **Notify it.** Showing the fact to a counterparty is a different processing
   operation from verifying it.
3. **Render only when true — the condition nobody had noticed.** There is a
   staff-assisted re-verification path for a student who loses institutional
   email access. That user did **not** sign in with a college email address,
   so rendering the string for them is a false statement about a person and
   fails the deck's own "name a fact" test. **Gate on the verification method,
   never on the verified flag** — two different facts, and the UI must not
   conflate them.

**Ruling 2 — a student-typed rupee figure in a free-text message does not
change the s194-O position at all, and compliance recommends the buyer-side
prompt it was asked merely to permit.** This reverses design's instinct.

The decisive comparison: in Circular 20/2021 the e-auctioneer **conducts the
auction itself** — far more active in price formation than a hint text — and
CBDT still held s194-O does not apply, because the transaction and payment
occurred outside the portal and the operator did not know the quantum.
Nothing in our system links a figure to an outcome: offers carry no amount,
`transfers` has no money column, and accepting an offer accepts **a buyer, not
a price**. Unresolved, unstructured, unlinked numbers are affirmative evidence
for the limb we are weakest on. The risk exists either way — students haggle
regardless.

**The argument the CEO agent endorses:** copy that *asserts* negotiability is
the weakest form of the limb; copy that *causes* negotiation produces
evidence. A student who has typed a number has experienced that the price is
not fixed; one who has read a disclaimer has not.

**The line: invite a conversation, never capture a number.** Four conditions,
of which one is a trap worth naming — **the `contact_pattern_flag` regex may
never be extended to currency patterns.** Someone will propose `₹\d+` as a
leakage signal; that would convert the unstructured free text this ruling
depends on into a queryable per-message indicator that an amount was
discussed. The frozen `messages` column list is now load-bearing for **two**
independent arguments, recorded so nobody relaxes it thinking it served only
one.

**Remedy pre-authorised** if design's probe P3 trips threshold U8: the
buyer-side prompt plus the seller-intake string, implementable without a fresh
ruling. Compliance also named, and explicitly did **not** request, the control
of last resort — a listing with no asking price at all, which cannot be a
determinable gross amount on any reading — recording it so that if copy fails
repeatedly nobody concludes the only option left is to start recording prices.
**The available move is to record fewer, not more.**

### Compliance corrected its own counsel brief, unprompted
Q9's statement of facts asserted to counsel that "the product says so" —
**true of a frozen specification, not of a built product.** It now states
separately what is specified, what the copy test enforces, and what has **not
been observed in use by students**, and asks counsel whether their answer
depends on behaviour we have not measured. Recorded because it is the exact
error the document warns other agents against, caught and owned by the agent
that made it.

**Net:** §2.5a tightens a constraint (the domain prohibition, now mechanised
in the copy test) while releasing a string. Neither ruling referenced anyone's
schedule.

---

## D-016 — S0 fails review: the legal gate does not hold in code
**Date:** 2026-10-21 · **Decider:** ceo-planning, recording code-review
**Evidence:** `company/architecture/REVIEW-S0.md`

**Verdict: CHANGES REQUIRED.** S0 does not integrate. Six must-fixes, then
re-review of those six only. The reviewer's assessment of the architecture:
right, small, plain, nothing over-built — but M0 blocks on its own.

### M0 — the discovery gate does not hold, and this one is legal, not technical
`campuses.discovery_enabled_at` has **no write guard**. Verified by probe: a
plain `Campus.objects.update(...)` or `.save()` opens the gate on a campus with
no authorisation row and no legal entity, writes **zero** audit rows, and
`assert_discovery_open` then passes. ADR-002 §4.1(b) states this cannot
happen. It can.

**Consequence recorded plainly: the claim that the discovery gate makes
building before incorporation lawful is, as of now, false in code rather than
merely unproven.** The authorisation machinery around it is excellent and well
tested — 21 green tests, 14 driving the command — but not one asked whether
the column itself was writable.

**Found by test-qa, not by code-review.** The reviewer enumerated existing
bypass paths and never tested the column's writability, and recorded it as its
own escaped defect. This is exactly why both agents exist and why neither may
be collapsed into the other.

The reviewer further recommends the gated read become the **default manager**
on `is_seed` models rather than opt-in per call site, since opt-in means every
future reader must remember. Routed to the CTO as a proposal (touches
ADR-002 §2), not landed unilaterally.

### The other five
- **M1** the P14 deny-list still carries the withdrawn `age_check_pending` DOB
  exception, so `date_of_birth` passes the whole deny-list today.
- **M2** the deny-list fails on `listings.price_fixed_at`, a column ADR-003
  mandates — S2 would meet a red guard and the tempting fix is editing a
  founder-escalation file. **CEO reading: M2 should largely dissolve under the
  whitelist the CTO already accepted, since a timestamp is not a monetary
  column.** Backend instructed to implement the whitelist and report whether
  M2 survives; if it does, stop and escalate rather than widening an
  allowance.
- **M3** an idempotency key replays **across endpoints** — `endpoint` is
  stored and never compared.
- **M4** a job locked by a worker that dies is never retried, breaking
  at-least-once; the existing test asserts the losing behaviour.
- **M5** `ENGINE-DIVERGENCE` §7.1 contradicts its own §3.6 — Django's Postgres
  `sql_flush` emits TRUNCATE, so the new TRUNCATE guard breaks every
  `transactional_db` teardown, landing on S4's double-booking test.

### The three legally load-bearing controls, assessed
1. **Discovery gate — DOES NOT HOLD** (M0).
2. **Audit trail — holds on SQLite, unverified on Postgres.** The reviewer
   read the plpgsql as text and found no syntax error and no wrong OLD/NEW
   reference, and noted the trigger checks `TG_OP` *before* touching
   `NEW`/`OLD`, which is what stops the statement-level TRUNCATE trigger
   failing on an unassigned record. Chain cannot fork, tamper is detected.
   M5 is the one proven hole.
3. **P14 — real but name-shaped.** Verified escapes:
   `settlements.amount_minor`, `settlement_records.consideration`,
   `receipts.total_inr`, plus jsonb and free text. The compensating control
   `test_forbidden_response.py` is a named control with **no owning slice**.

### Six tests that pass for the wrong reason
Recorded in full in the review. The pattern across all six is the defect class
this project has now named three times: `test_gate.py` is 21 green tests none
of which asks whether the column is writable; a deny-list test is green while
permitting a deleted table; a hostile-input test checks a mid-string newline
while the trailing one is what gets through; the job test asserts M4; a scoping
test asserts against a FakeQuerySet and so proves nothing about any caller; and
one assertion is the tautology `assert checked >= 0`.

**Deviations ruled:** jsonb `email_domains` acceptable (amend DATA-MODEL);
conditional-UPDATE job claiming acceptable **conditional on M4**, with the
trade named — `SKIP LOCKED` releases a lock when a connection dies and a
`locked_at` column does not; Python 3.11.9 acceptable, pin prod to 3.12;
`/readyz` acceptable with a docstring correction; the urls `try/except`
replaced now rather than later.

**One current failure is a verified false positive** —
`test_only_the_gate_commands_write_discovery_enabled_at` matches a
`stdout.write` f-string label in `seed_demo.py:47`, and `seed_demo` leaves the
column NULL. `seed_demo.py` must not be changed.

**Three TASKS defects escalated to the CTO:** S0 scopes ruff/mypy/CI while §1
makes CI dormant; S0's `seed_demo` "done when" is unmeetable before S1/S2; and
CSP plus `test_forbidden_response.py` have no owning slice.

---

## D-017 — S0 fails QA independently; the gate is weaker than its tests suggest
**Date:** 2026-10-21 · **Decider:** ceo-planning, recording test-qa
**Evidence:** `company/architecture/QA-S0.md`

**Verdict: S0 does not pass QA.** 169 tests added, written from the contracts
**before** the backend's own test files were opened — the method constraint
held, and it is why QA found what review did not.

Suite now: **3 failed, 235 passed, 44 skipped** on SQLite 3.45.1. The
backend's claim of 92 passing reproduces exactly, though it omitted the 21
skips when reporting.

### Independently confirmed (so these are now evidence, not assertion)
The gate's authorisation machinery survived 33 tests: closed by default;
refuses on each of six evidence keys and five legal-entity facts individually;
refuses a blank human name, the wrong gate letter, GLOBAL scope, another
campus's row, a revoked row, and a campus with no legal entity; `seed_demo`
leaves it closed; close revokes and re-opening needs fresh authorisation.
Route enumeration confirms the entire HTTP surface is `/healthz` and `/readyz`,
neither leaking tenant data, with no admin installed. The audit chain detects
a rewritten row, a deleted middle row, a forged append and a half-fixed hash,
and rolls back with its transaction.

### Three failures, three findings
- **F2, the serious one and the worst gap in the existing suite.** The DOB
  exemption that amendment CG-5 **explicitly withdrew** is still enforced. QA
  created `age_check_pending(date_of_birth date)` and ran the shipped guard's
  own functions over it: **they pass.** The one shape the amendment forbade is
  the one still allowed — in the slice before S1 builds age verification.
  QA's verdict on the file: `test_forbidden_schema.py` is "the file whose
  green is most load-bearing and least earned."
- **F3** confirms review's M0 independently: `Campus.objects.filter(...)
  .update(discovery_enabled_at=now())` opens the gate with zero authorisation
  rows and zero audit rows.
- **F1** P14 cannot be guaranteed by naming.

### P14's ceiling, now bounded concretely rather than feared
Escapes QA demonstrated: `transfers.cash_handed_over` (no cash word in
`MONEY_WORDS`), `transfer_settlements.cash_total`, **`asking_price_paise`
declared `real` — because names carry no types**, and a Python
`@property settled_price`, which changes zero columns. **The whitelist must
therefore assert the permitted money column's TYPE, not only its uniqueness**,
and the residual exposure belongs in ADR-003 as a stated limit. The
compensating control the review named, `test_forbidden_response.py`, is
load-bearing and has **no owning slice** — assigning it is a contract
decision, now with the CTO.

### Specification silences — routed to the CTO
1. **Gate C checks evidence *presence*, not *truth*:**
   `breach_rehearsal_at="not yet"` opens discovery. Thirty-three tests guard a
   structure that a human can satisfy by typing anything.
2. An `active=false` campus can still have an open gate.
3. The audit row holds hashes, so the named human who opened a campus
   survives only in `gate_authorisations` — a different guarantee from the
   chain.

### Blocking S1
**Anonymous idempotency: the key is `(user_id, key)` and a NULL user never
dedupes**, so S1 ships two anonymous POSTs the moment magic-link signup
exists. Routed to backend with instruction to choose the semantics
deliberately.

### 23 skips, each naming engine and slice
Including the double-booking race — a green on SQLite would mean nothing,
since one writer serialises the losers on the write lock rather than the index
— `expected_version` under a real race, concurrent chain appenders,
multi-worker job claiming, the plpgsql body, and the `BEFORE TRUNCATE` guard
which ENGINE-DIVERGENCE calls the most important thing for a Postgres box and
which has verified **nothing**.

### Accessibility harness
Stood up dependency-free (no Node or Playwright on this machine), nine
objective WCAG 2.2 structural rules including `lang` matching the served
locale, with 15 tests proving the harness itself works and a page runner that
discovers routes from the live URLconf and needs no edit when S1 lands.
**Explicitly not a WCAG pass** — four criteria including the magic-link flow
need a browser or a human.

**Recorded because it is the fourth instance of one defect class:** QA named
two more tests that pass for the wrong reason — one asserting against a
hand-written `FakeQuerySet`, touching no database, and one ending in
`assert checked >= 0` with `checked == 0` today. Both to be replaced, not
patched.

---

## D-018 — Design v1.2 implements both rulings; two stale items closed
**Date:** 2026-10-21 · **Decider:** ceo-planning, recording design-director v1.2

**Both compliance rulings implemented** across all four design documents, with
contrast assertions re-run and all pairs still passing.

**Condition 3 is the one that earned the round trip**, and it is recorded in
three documents as the standing case for not reading silence as approval:
neither design nor compliance v1.1 had seen it. Un-gated, the product would
have **published a false statement about a person, in production, for exactly
the users least able to notice, while passing every happy-path review.** The
string now gates on the verification *method* and the component **fails closed**
on an unknown method.

**What a staff-re-verified seller's listing shows: nothing.** No substitute
string — "Verified by BookHop staff" was considered and rejected immediately as
the worst string that could exist in this deck. **Residual risk named, not
solved:** at one campus almost every seller is email-verified, so a rare
absence is *more* conspicuous than a common one and may read as a negative
signal. Every alternative is worse; accepted with a revisit trigger.

**The adjacency fix made the copy better, and the reasoning generalises.**
Design's first instinct was to separate the contradictory sentences across the
page, and it rejected its own instinct: far apart they still contradict, just
less visibly, leaving the reader to reconcile them alone. Instead, two labelled
blocks, "Nothing here is checked by BookHop" rescoped to the book, and a new
line placed *immediately after* the positive fact — "That's all BookHop knows
about them. We haven't checked who they are."
**Rule adopted: a trust signal that states its own ceiling is the only kind we
may ship, and against this category's background noise it is also the
believable kind.** No trust sentence may appear outside the block whose scope
it names.

**"College" for the institution and the account, "campus" for the place** —
adopted as a project rule beyond copy, since in this product the institution
that issued an email and the place a stranger is met are separate facts doing
separate jobs.

**Design recorded being wrong, plainly and in its own file**, on the buyer
prompt. The framing is kept because it generalises beyond the string:
**an over-conservative call that costs the product utility is still a wrong
call.** It had already identified where negotiability becomes real for the
seller, then stopped one step short of the buyer for a risk that was not there.

### Two items design listed as open are closed — verified in the contracts
- The schema guard for offer, counter-offer, bid and agreed-price columns
  **exists**: ADR-003 §2.3 item 4, accepted by the CTO before design's
  escalation arrived, with THREAT-MODEL recording the control as a whitelist.
  Copy is not defending a column that exists; the column cannot exist.
- The slug is renamed: **Amendment A-7**, `handover-safety` →
  `handover-guidance`, across API-CONTRACT, DATA-MODEL and TASKS.

### Genuinely open
Four blocking Tamil classes and twelve translation items — **the Tamil locale
is not offered to students until signed off, and the reviewer is a human the
founder has not yet provided.** The user test remains unrun, unfunded,
zero participants.

**Pre-authorised remedy written where it will be read:** USER-TEST-PLAN §5.1
records the direction a second copy failure must travel, in the document
someone will have open when a threshold fires — **the available move is to
record fewer prices, not more.** A failed copy control is never a reason to
reopen recording a settled price.

---

## D-019 — CTO closes every S0 finding into a contract
**Date:** 2026-10-21 · **Decider:** ceo-planning, recording cto
**Evidence:** amended `company/architecture/`

**Every QA and review finding is now traceable into a contract document.** The
CTO ruled on all four routed items plus three it judged its own, including the
blocking M0.

**The CTO's own summary, recorded verbatim in substance because it is the
lesson of the slice:** the gate held against 33 tests on the authorisation
machinery and failed on the column, *"which is the half I described as a
constraint and implemented as a convention."* Both QA and review found it
independently. **The machinery was fine; the claim about it was ahead of the
code.**

### Rulings
1. **Gate C evidence — the answer is "both", stated per field.** The real fix
   was structural: half of QA's attack worked because the command read free
   text where a typed fact sat one table away. CIN, incorporation date, INC-20A
   and grievance-officer fields now read from typed columns; dates must parse
   and must not be in the future; notice IDs became **real foreign keys**, the
   one item verifiable end-to-end. `breach_rehearsal_at` is a date, so QA's
   `"not yet"` no longer parses. **`authorised_by_human` now rejects every
   name an agent would type, including all thirteen charter names — QA
   defeated it with `"agent"`.** Uploaded certificates rejected: nothing
   validates a PDF of a certificate either.
2. **Deactivation closes discovery, but must not clear the authorisation** — a
   term-break pause would otherwise destroy it and force a fresh gate. `active`
   is operational; `discovery_enabled_at` is legal; the two are independent.
3. **The audit row holds hashes: accepted deliberately, and §4's own sentence
   corrected.** Two artefacts, two different guarantees — the row gives
   immutability of content, the chain gives tamper-evidence over fact and time.
   The audit entry now points at the row, so the chain reaches the named human
   in one hop **without ever storing a person's name.**
4. **Default manager accepted as a correction to the CTO's own §2**, which said
   "one helper, used everywhere" and then relied on everyone choosing to use
   it — **a convention wearing a constraint's clothes, exactly what the gate
   column turned out to be.** Two Django footguns stated: `base_manager_name`
   must be set or cascade deletes and `refresh_from_db` break silently, and
   reverse relations are not covered, so this is defence in depth and not a
   replacement for the service-layer discipline.
5. **M0 fixed by constraint, not convention** — a `BEFORE UPDATE` trigger
   refusing NULL→non-NULL without a live unrevoked authorisation. The CTO's
   sharpening: §4.2 conceded we cannot stop direct SQL, **but this was the
   application's own ORM, reachable from the Django admin S2 introduces, which
   makes every field editable by default. A grep catches three spellings and
   misses an admin form.**
6. **P14 residual bounded, with the root cause named.** The type is now
   asserted (`real` passed a name-based control); the money-token set widened
   to 21 tokens over every table; a source-level grep added because a Python
   property is invisible to any schema control. **The one that matters most:
   the token sets move into code as data the tests import — because QA found
   the shipped control had been retyped from the ADR's prose table and had
   diverged from it, still carrying the withdrawn DOB exemption.** The CTO
   owns that as a defect its own document caused: **a rule that must be copied
   by hand into code will eventually differ from its spec, and the difference
   will be silent.**
   **Stated for G4 and red-team: P14 is enforced, not guaranteed.** A number in
   free text or jsonb is not closable by any schema control. New accepted
   risks A11–A13.
7. **Four ownerless controls assigned to S1**, including CSP middleware — an
   ASVS L2 control that must exist *before the first HTML ships* — and
   `test_forbidden_response.py`, now the named compensating control for P14's
   free-text limb. **A named control with no owner is never written.**
8. **TRUNCATE guard stays; the test harness yields.** A session GUC set by a
   teardown fixture, rather than disabling the trigger, which would need
   ownership and leave the guard off for the whole session. **The rule that
   keeps the escape honest: a test asserts the GUC is unset under production
   settings, so it cannot exist on a deployed box.** The CTO flagged that the
   tempting fix at that moment was to delete the guard, and that this is **the
   first live instance of the failure mode the charters' last hard rule
   names.**
9. **Anonymous idempotency is a compliance problem, not a cosmetic one.**
   Ruled sentinel key rather than exemption, because `/grievances` and the
   public copyright-notice form are how a rights holder or a distressed
   non-user reaches us, a safety path may not require an account, and **a
   double-submitted grievance creates two tickets with two separate 24-hour
   acknowledgement clocks running on one complaint.** Must close before S1
   wires magic-link.

### CEO action taken
`README.md` §7 now carries the A11 distinction next to the gate row: **a
`gate_authorisations` row is a named person asserting things on a date, not
verification** — with a per-field table of what the system genuinely checks
and what it cannot, and the note that shape is not existence and a placeholder
deny-list cannot catch a field filled in falsely.

**Standing:** S2 remains gated on a reachable PostgreSQL 16. Three guards now
sit on the must-confirm-on-Postgres list — P14's immutability trigger, the
TRUNCATE guard, and now the gate write-guard.

---

## D-020 — Design v1.3: closures verified at source, two improvements adopted
**Date:** 2026-10-21 · **Decider:** ceo-planning, recording design-director v1.3

**Design verified both closures by reading the contracts itself** rather than
accepting the CEO agent's report, citing the project's own evidence standard:
no agent may cite another agent as the origin of a fact. Correct, and applied
to the CEO agent without exception.

**It took a correction rather than just the closure.** It had asked for four
column names on a deny-list; the contracts hold patterns inside a whitelist.
Its own words: *patterns beat a name list and a whitelist beats both.* The line
in the design files is now inverted — copy is not defending a column that
exists; **the column cannot exist.**

It also quoted ADR-003's resolution of the apparent contradiction into two
design files for the next reader who thinks the rules conflict: *"The
prohibition on offer amounts and the requirement that negotiation be real are
the same design: BookHop must not know."*

**A third item closed that nobody had flagged** — design found while reading
TASKS.md that `/dev/states` is scoped to S2, which closes its own earlier
escalation.

### Two improvements the CEO agent adopts
- **The condition-1 scope note became a failable positive assertion** rather
  than prose: *the link-sent page DOES render the address the student just
  submitted.* Design's reasoning, which generalises and is adopted as
  practice: **a prose note is read once; a failing test is read every time
  someone over-complies with the ban and strips the echo believing they are
  tightening a control.**
- **The college/campus rule is recorded as owned beyond the deck and not
  design's to relax**, with the test an author should apply: *does this name
  the institution that issued an email, or the place two people walk to?*

### The Tamil gate became mechanical without design building it
TASKS.md amendments seed the locale flag false, create the exceptions,
blocking-classes and reviewed manifests in S1, and the release checklist
requires a reviewer-signed entry per string. Design adopted the contract's own
wording over its prose: **"That is the gate, and it is a test, not a promise."**

**So what is open there is a person, not a control** — and design recorded the
guard that matters: until a named reviewer exists, **"Tamil is supported" is
not a true statement about this product, and nobody should make it on the
strength of the deck existing.** The test plan's Tamil arm is marked
**unservable**, with an explicit instruction not to flip the flag to make a
session possible.

### Schedule correction
**The earliest honest window for the user test is after slice S3**, not after
S1: the first task needs search and the empty state, and S1–S2 only reach
sign-in, the sell flow and listing detail. The user test now has three
dependencies — money, campus contacts, and S3.

**Open list is exactly two, and neither is a design decision:** a named native
Tamil speaker, and the user test — unrun, unfunded, zero participants.

---

## D-021 — S0 rework delivered; one live disagreement sent back to measurement
**Date:** 2026-10-21 · **Decider:** ceo-planning
**Evidence:** ENGINE-DIVERGENCE v1.1, suite at 6 failed / 298 passed / 51 skipped

**All six must-fixes reworked, plus the QA findings.** CEO agent verified the
suite independently. Five of the six remaining failures are QA's
characterisation tests now failing **because the defect is fixed** — the gate
column raises, the inactive campus raises `GateClosed`, the DOB column is
refused, both idempotency findings raise. Backend correctly did not edit QA's
trees.

**M0 is now true by constraint.** A trigger on `campuses` requiring a live
unrevoked Gate C authorisation scoped to that campus plus `active=true`;
closing is always permitted, on the reasoning that **a campus that cannot be
closed is the worse failure.** Eleven assertions: queryset `update()`,
`save(update_fields=…)` and `create()` all refused with zero audit rows, a
neighbouring campus's authorisation refused, wrong gate letter and GLOBAL
scope refused. **No contract change — this makes ADR-002 §4.1(b) true rather
than renegotiating it.**

**M2 dissolved exactly as predicted, with no allowance widened**, and 17
contract-mandated columns are now pinned so no future tightening re-breaks S2.

**Float money closed engine-neutrally**: the whitelist asserts **types, not
only names**, read through model meta *and* `connection.introspection`, so a
raw-SQL column is covered, and **failing closed** when a declared type cannot
be classified.

### The disagreement, sent back to measurement rather than adjudicated
`test_p14_is_not_guaranteed_by_naming` reports that float money and a related
settlement table still escape. Backend says its rewrite catches both — 20 of
QA's own 22 attack cases — and that QA's test measures **QA's own
transcription** of the deny-list rather than the shipped control.

**If backend is right, QA's test has precisely the defect QA found in
backend's: a control checked against a hand-copied rule instead of the real
one.** QA has been instructed to re-point the test at the shipped control,
re-run, and state plainly which of them was correct. The CEO agent has not
picked a side; both claims are testable and one measurement settles it.

### Recorded as the strongest evidence for a decision already taken
Backend's guard-of-the-guard **caught a real narrowing while the guard was
being strengthened** — `rupees_exchanged` escaped every layer until `rupee`
and `paise` were restored to the word list. A control briefly weaker than its
predecessor *during a rewrite to strengthen it* is the best available argument
for the CTO's W1d ruling that token sets must be data the tests import rather
than prose to be retyped.

### Backend overruled the CTO twice, with reasons accepted
- **Anonymous idempotency: partial unique index on the key alone where
  `user_id IS NULL`**, rejecting the CTO's sentinel because `user_id = 0`
  breaks the foreign key S1 adds, and rejecting IP because that breaks the
  retry it exists to serve the moment a phone changes network.
- **The default manager deliberately not landed**, with S2 argued as the right
  slice — the first `is_seed` model exists then, so it costs one Manager class
  and no rework. Routed to review for the timing call and the CTO for the slice.

**Both vacuous tests replaced rather than patched.** The `FakeQuerySet` test
now runs against real querysets and asserts the property that protects us —
applying the gate filter to a model with no `is_seed` column raises
`FieldError` rather than silently returning everything. `assert checked >= 0`
is gone, replaced by a verdict function tested over six input combinations, so
**the file says something today instead of in S1.**

**Not done, deliberately and correctly:** CSP and the lint/CI items, as
ownerless or contradictory in TASKS at the time. The CTO has since assigned
CSP to S1.

**Unchanged and now larger: nothing has run on PostgreSQL.** Both append-only
trigger bodies, the new `campuses` guard, the TRUNCATE escape, `ENABLE ALWAYS`
and every race are unexecuted text. `sqlmigrate` still fails at connect, so
**no Postgres DDL for this schema has been generated, let alone run.**

---

## D-022 — CTO closes its own spec bug; the P14 duplication is still live in triplicate
**Date:** 2026-10-21 · **Decider:** ceo-planning, recording cto
**Evidence:** amended `company/architecture/`, plus CEO verification below

**The CTO's summary, recorded because the direction is unusual:** *"Backend was
right on substance on every item, and twice it was right against me."*

### Rulings
1. **The suffix list is a CLARIFICATION, not a widening — with a decision
   procedure instead of an adjective**, which is what a reviewer will need in
   six months: *can this word denote a quantity that could be a
   consideration?* `id, count, seconds, attempts, bytes, width, height, year,
   position, version, status` cannot. **If a proposed word could denote money —
   `total, value, sum, amount, balance, rate` — it is a widening, it is
   refused, and it goes to founder escalation.** Those six are already deny
   tokens.
   **The non-obvious part that actually makes it safe, verified mechanically
   rather than asserted: the allow-list and the token deny-list are AND-ed, not
   OR-ed.** `payment_status` passes the new `status` word and is still
   rejected, because `payment` is a deny token. Without that interaction this
   would have been a widening.
   **The CTO owns it as its own spec bug:** it wrote a suffix list while its own
   data model mandates bare names, so **its whitelist rejected six columns its
   own schema requires.**
2. **Anonymous idempotency: the CTO's sentinel is withdrawn**, backend's
   partial unique index becomes the specification, and the question backend
   actually asked is answered — **yes, anonymous POSTs require a key**, because
   a double-submitted grievance starts two 24-hour clocks on one complaint and
   a safety path may not require an account. One precise exemption: a
   single-use magic-link token **is idempotent by construction.**
3. **Default manager confirmed at S2, with backend's premise corrected.**
   `users.is_seed` actually lands in S1 — but **nothing in S1 reads users
   through a gate**, so a gated manager there would gate nothing. Stated so
   nobody later reads S1 as an oversight.
4. **The two escalations merged into one chain in ADR-003 §5.3**, ending with
   the sentence for the G4 packet: *P14 is enforced by a whitelist, frozen
   tables, a source grep and a response-schema test, and guaranteed by none of
   them — the residual is a number in free text, and the control for it is a
   product rule plus a human reviewing diffs.*
   **The CTO also deleted its own duplicate** of the residual table, on the
   grounds that duplicating a statement is how two copies come to disagree —
   *"it would have been hypocritical to leave it."*

### CEO verification — and the finding it produced
Checking the CTO's AND-ing claim, the CEO agent established that
**`apps/core/p14.py` does not exist.** It is assigned to S1. So the W1d fix —
token sets as data the tests import — **is not yet implemented, and the
duplication that caused the DOB divergence is still live.**

It is in fact live in **triplicate**: the ADR's prose, backend's
`tests/unit/test_forbidden_schema.py`, and **QA's own
`tests/contract/denylist.py`**, which QA wrote itself, derived independently
from the ADR.

**That settles the backend-versus-QA disagreement on mechanism: backend is
right.** QA's failing test measures QA's own derivation, not the shipped
control.

**And the reason is not carelessness — it is QA's correct method.** Its
charter requires it to write tests from the specification without reading the
implementation, which is exactly why it re-derived the deny-list. **So the
right method produced a test that cannot answer this particular question.**
Both agents were right about their own work and wrong about each other's.

**Consequence recorded: the current disagreement is not incidental. It is the
predicted symptom of the root cause the CTO has already diagnosed and
scheduled for S1.** Until `apps/core/p14.py` exists, any test of P14 is a test
of somebody's copy. QA has been asked to re-point and confirm independently;
its answer is expected to agree with this.

### The `rupees_exchanged` incident is now in the ADR as evidence
The CTO's framing, kept: it was not carelessness and review would not have
caught it — **the diff looked like an improvement, and it was one everywhere
except the single place it silently regressed. Only a test comparing the
control against its specification catches that.** Recorded so the next person
tempted to inline the token sets has the incident rather than the principle.

### Also ruled
`campuses.email_domains` → `jsonb` (membership is the only operation, and one
migration serves both engines). Job claiming stays a compare-and-swap, because
`SKIP LOCKED` is **silently a no-op on SQLite** and would have been an
undocumented divergence; it returns as a Postgres optimisation if a second
worker is ever run.

**Standing, and the CTO is right to correct the drift: PostgreSQL 16 installs
natively on Windows without Docker, so S2's gate is an installation decision
at Rs 0 — not a spend decision.** It had been drifting toward the founder's
spend queue.

---

## D-023 — S0 APPROVED. First slice integrates; first-pass rate baseline is 0/1
**Date:** 2026-10-21 · **Decider:** ceo-planning, recording code-review PART TWO
**Evidence:** `company/architecture/REVIEW-S0.md` §9-§15

**Verdict: APPROVED. S0 integrates.** All six must-fixes verified **by
execution**, not by reading backend's account. The reviewer appended rather
than replaced Part One, so the found-then-fixed history reads straight through.

**M0 confirmed blocked on all four write paths** — `queryset.update()`,
`instance.save()`, `objects.create()` **and raw SQL via cursor** — on a campus
with no authorisation, and allowed with a live Gate C row. Wrong-campus scope,
wrong gate letter and GLOBAL scope each refused. **ADR-002 §4.2's concession
that direct SQL is unprotected is no longer true of this column.**

**The close-always asymmetry was checked as the kind of exception that is
occasionally wrong, and it is load-bearing rather than merely harmless:**
`close_discovery` revokes the authorisation in the same transaction as the
close, so a symmetric guard would have made **the one operation that must
never fail depend on the row it is revoking.**

**M2 was fixed better than specified** — dissolved by the whitelist rather
than allow-listed, which addresses the defect class instead of the instance.

### Two new findings, both scheduled to S2
- **R1 is a genuine P14 hole, and the reviewer's framing is the one to keep:
  the vocabulary change was not the money widening, but there IS a money
  widening, and they are not the same decision.** The table-wide `listings`
  exemption composed with the non-monetary suffix allowance lets a **second**
  money column onto `listings` — `paise_count`, `rupees_count`,
  `cash_total_count` all verified passing, while the same names on `transfers`
  are caught. The contract says exactly one money column in the database.
  **CEO verification: `listings` does not exist yet, so this is not currently
  exploitable and S2 is the correct slice.**
- **R2 inverts W1c's stated purpose** — model meta overrides introspection for
  types, so a `real` column is masked whenever a model declares it. Union, not
  override.

**The reviewer's likely resolution of the backend-versus-QA disagreement:
backend right on the related settlement table, QA right on float money but for
the wrong reason — and R2's fix makes both true.** It declined to settle it,
as instructed, and noted the suite's red is not evidence either way.

### The design point recorded as more important than the timing
**The default manager sits underneath `assert_discovery_open`, never instead
of it.** A filtered manager returns *no rows*; the contract requires
`403 GATE_CLOSED`. **Substituting one for the other makes the legal gate
invisible to the person it applies to** — a worse outcome than the convention
it replaces, and exactly the substitution a future developer would make
believing it a simplification.

### Quiet-narrowing hunt: clean
The reviewer diffed the old vocabulary against the new and found nothing else
lost — `fee` moved to the deny-list with an explicit allowed pair, Django's
pluralisation now caught, `vpa` and `pan_card` fixed. Its verdict on the
guard-of-the-guard: **the best addition in this rework**, and the reason the
one narrowing was caught during the rewrite rather than after.

### Delivery baseline recorded, unflattering and useful
**First-pass rate: 0 of 1.** S0 did not pass review or QA on its first
submission. Both gates found real defects, one of them legally load-bearing,
and each found something the other missed. **This is the baseline the weekly
loop measures against, and it is recorded rather than smoothed.**

**Approval does not imply Postgres.** Four plpgsql bodies across migrations
0002 and 0003 have never been parsed by a server, and **three of the six
must-fixes live in code only a Postgres box can verify.** The reviewer's
assessment, which the CEO agent endorses: **getting one before S2 is the
highest-value zero-rupee action available.**

---

## D-024 — R1/R2 closed; S2 entry conditions written down; one CEO correction repeated
**Date:** 2026-10-21 · **Decider:** ceo-planning, recording cto
**Evidence:** amended `company/architecture/`

**R1 accepted as a genuine P14 hole, and the CTO owns it as its own.** Each
rule was defensible alone; **composed, they left the one table allowed to hold
money as the one table where a *second* money column was unguarded.** Fixed by
column-scoping the exemption — backend's own pattern, the same move it made
rescoping `address` after QA found `legal_entities.pincode`. The CTO's phrase,
kept: ***a table-wide exemption is a hole shaped like a convenience.***

It verified the fix mechanically rather than accepting the argument: all six
attack shapes now reject, both permitted columns and all seven
contract-mandated columns still accept. **§2.1 already said "exactly one money
column in the entire database", so the contract was right and the control
disagreed with it** — the fix makes the control say what the contract already
said. **The two decisions are kept separate on the record** so ratifying the
clarification does not depend on fixing the hole, and vice versa.

**R2 resolved as an asymmetry worth stating as one: names override, types
UNION.** Model meta winning is right for names — a declared field is the
stronger fact about intent — and backwards for types, because the whole reason
the check exists is to see what the database actually holds. The CTO's rule:
***never trust the declaration about the thing the declaration is suspected of
misrepresenting.***
**This resolves the backend-versus-QA disagreement with both agents coming out
right** — backend on the related settlement table, QA on float money for the
wrong reason — and the union makes both true without either having to be wrong.

**The design point is in ADR-002 §2.3 and is the item the CTO says it would
least want lost.** The manager sits underneath the gate check, never instead
of it. **Substituting one for the other silently renders an empty search page
and makes the legal gate invisible to the person it applies to — strictly
worse than the convention it replaces, because the convention could be
forgotten whereas this would *look* like it was working.** The two controls do
not do the same thing: **one filters rows, the other tells a student why there
are none.** Deleting the helper because the manager exists is now a Code Review
escalation, not a cleanup.

**The binding condition is discharged properly: the deferral is in TASKS S2's
scope AND its definition of done, as four checkable boxes rather than prose.**

**The CTO withdrew its own reasoning on the reverse-relation gap**, having
asserted flatly that reverse relations are uncovered: *"that was reasoning
where a measurement was available."* S2 measures it and records the result
either way — **fine, but known rather than assumed.**

**W1 ratified with the provenance the bar depends on.** The reviewer's reason
adopted verbatim: *the escalation bar is only credible if the provenance is in
the ADR — the next person to add a name cannot face a real bar if the list's
authority is a comment in a test written by the developer the bar exists to
constrain.* **A control whose authority lives in its own implementation is
self-certifying, which is the thing W1d existed to prevent.** The CTO also
corrected its own count from six to seven.

**ADR-002 §4.2's concession corrected, and the direction matters:** leaving it
would have **understated** the control to anyone reading it for the go/no-go
packet. A `psql` session now gets the same refusal as the ORM. What remains is
someone who drops the trigger first — **so the gate can no longer be opened by
accident or by ordinary code, only by a deliberate act that removes a guard,
and a dropped trigger is itself visible.**

### CEO corrections
1. **Repeated, and this is the second time: the CTO again states that Postgres
   is reached "via the CI service container at Rs 0, Docker not required."
   There is no CI.** This project is still not a git repository, has no remote
   and has no CI configuration — verified again. The CTO is right that it is
   **not a spend decision**; it is wrong that a route currently exists. The
   real options remain a native Windows install or setting up git plus a
   remote. **Recorded twice now because a contract document asserting a
   capability we do not have is how S2 gets started on an assumption.**
2. **R4 fixed by the CEO agent directly** — `ENGINE-DIVERGENCE.md`'s header
   read v1.0 while its own changelog recorded v1.1. One line, backend idle, not
   worth an agent. Worth fixing at all because **that document is the one a
   developer is told to trust before trusting a green test run.**

**R3 carried into S6 as a condition** rather than left as a note: no anonymous
endpoint may store anything in `response_body` that its reference does not
already reveal to the filer. Guessing a UUIDv4 is not a feasible attack,
**but it is a property we should choose rather than inherit.**

**S2's entry conditions are now fully written down. The standing gate is
unchanged and remains the critical path: S2 needs a reachable PostgreSQL 16.**

---

## D-025 — S0 approval SUSPENDED. QA finds a live disclosure and two phantom controls
**Date:** 2026-10-21 · **Decider:** ceo-planning
**Evidence:** `company/architecture/QA-S0.md` v2.0; suite 10 failed / 304 passed / 54 skipped

**S0 does NOT integrate.** Code review approved; QA did not pass. The CTO
charter requires both, so the approval in D-023 is suspended rather than
overridden. All ten failures are in one file and trace to two root causes.

### Who was right about the P14 disagreement: backend, on both shapes
QA re-pointed its attack at the shipped control over real DDL and confirmed
float money and the related settlement table are both **caught**. v1.0 had
measured QA's own transcription, exactly as backend said.

**QA wrote the irony up at its own expense rather than glossing it, and it is
the strongest possible evidence for a ruling already taken:** its v1.0
headline was that a legal control had been retyped from prose and silently
diverged — *and it then judged that control against its own retyped copy,
while the guard's attack test checks a third inline copy.* **Three hand-made
copies of one legal rule.** QA notes its error surfaced only because a human
read two reports side by side. It also fixed two of its own harness bugs
first, either of which would have misreported results.

### A fourth shape class, and it is worse than R1
- **F6**: ADR-003 states 22 money tokens; **the guard enforces 15.** `amt`,
  `paid`, `payment` and `due` are caught by nothing — and because the type
  rule inspects only **numeric** columns, a **TEXT** column slips entirely.
  `receipts.amt text`, `receipts.paid text`, `handover_log.payment_received
  text` all store a settled price silently.
- **F7**: the exemption is still `table != "listings"`. **The softest target
  in the schema is now the money table** — `listings.cash_received text`
  escapes. The CTO ruled the column-scoped fix, but it **amended the contract,
  not the code**; landing it is backend's.
- **Both fixes are tightenings, so by the CTO's own decision procedure neither
  is a founder escalation** — recorded so the bar is seen to have been
  considered rather than bypassed.

### F10 — a demonstrated disclosure, not a hole in a guard
The anonymous idempotency key format is unchecked, so `Idempotency-Key: 1` is
legal, and **QA demonstrated a same-body replay returning another caller's
grievance reference.** API-CONTRACT §4.1's claim that a collision requires
guessing a UUIDv4 is false on both halves. This is live in S0 code, on the
endpoint through which a distressed non-user or a rights holder reaches us.

### Two controls the documents rely on do not exist
- **F5: ADR-003 W1c's source grep is unimplemented** — no test reads source at
  all. It is the **only** compensating control for the `@property` residual,
  and with `test_forbidden_response.py` also unowned in code, **two of W5's
  three controls are unwritten.** So the sentence written for the G4 packet —
  *P14 is enforced by a whitelist, frozen tables, a source grep and a
  response-schema test* — **is true of the specification and false of the
  repository.** Either both get scheduled or the sentence changes. **The
  packet must understate us, never overstate us.**
- **F9, and a CEO correction: a claim I passed to the founder did not hold.**
  Backend reported that a test asserts the flush GUC cannot be set under
  production settings, and I repeated it. QA found the GUC appears in exactly
  **one** file — the migration — so the session fixture ENGINE-DIVERGENCE
  calls mandatory **does not exist**, and the first Postgres run of S4's
  transactional double-booking test will fail in teardown, at precisely the
  moment the tempting fix is deleting the guard. QA's structural point, which
  settles it: **no mechanism can make production refuse that SET, because a
  custom GUC is settable by any session.** The control is privilege
  separation, not a test, and §7.1 must say so.
  **The default-deny construction itself was independently verified and
  holds.** It was the claim *about* the claim that was wrong.

**F4 confirms the CEO agent's own finding and sharpens it:** `apps/core/p14.py`
still does not exist, and **F6/F7 are its predicted divergence, already
present.** W1d is therefore no longer a design improvement; **it is a fix for
an active defect.**

**F8**: the gate trigger checks an authorisation *exists*, not that it is
*complete* — an empty evidence blob with a blank human name still opens the
gate. Smaller than the original hole, but §4.1(b) reads stronger than the
floor it guarantees.

### Verified and sound
The `campuses` trigger refuses an INSERT arriving already open, always permits
closing even with the authorisation revoked, permits unrelated updates, and
**refuses a reopen after close with no new authorisation — the strongest
property it buys.** Five regressions converted and confirmed fixed. **QA
corrected itself in backend's favour on the cross-endpoint idempotency
semantics: it was a bug, and code review was right.**

**The engine position got worse, not better.** The rework added three guards
that exist **only** on PostgreSQL, so unexecuted security-relevant SQL went
**up**. Not advisable any more — overdue, at zero rupees.

---

## D-026 — Conformance testing adopted as a standing rule, now rather than later
**Date:** 2026-10-21 · **Decider:** ceo-planning
**Evidence:** cto's F4-F9 rulings; QA-S0.md v2.0; REVIEW-S0.md

**The CTO identified the real finding of this phase, and it is about its own
documents.** Every defect this pass was a place where **its specification was
stronger than its implementation and no test existed for the gap**:
- W1b named 22 money tokens; **15 were enforced.**
- §5.3 named four controls; **two did not exist.**
- The GUC test it specified **cannot be written at all.**
- §4.1(b) **read stronger than the floor it guaranteed.**

Its own diagnosis: *the document was the thing that was wrong, because it
asserted a property instead of requiring a check for it.*

**The CTO proposed making conformance testing a standing rule "if the pattern
recurs once more." CEO ruling: it has already recurred four times in a single
pass. That is not a trend to confirm; it is a confirmed trend.** Adopted now,
and written into `CLAUDE.md` so future sessions inherit it rather than
rediscovering it:

> **Every control a document names must have a conformance test asserting that
> control exists in code.** A document may not assert a property; it must
> require a check for it. No claim about a control may be quoted in a launch
> packet, an ADR or a report until its conformance test passes.

Three further rules promoted alongside it, each earned by a specific incident
rather than invented: **never hand-copy a rule into code**; **a list that
cannot express its own exceptions gets edited instead of extended**; and **a
guard test that passes vacuously is worse than no guard, because it is
reported as coverage** — found five times now.

### The CTO's structural fix for F5, which the CEO agent endorses
**The G4 sentence now exists in two versions, and nobody may quote the second
until a conformance test proves every control §5.3 names is present.** It
adopted QA's detectors as the gate on its own section. **The claim and the
check become one artefact** — W1d's principle applied to the ADR's own prose,
and cheaper than remembering.

The honest position it recorded: **as of today the `@property`, jsonb and
free-text P14 residuals have NO automated control**, bounded only by the
frozen-table escalation and a product rule. Both missing controls are assigned
to S1's first commit.

### F6's root cause, and the lesson is reusable
W1b was a flat list with **no way to express an exception.** `rs_` as a
substring genuinely collides with `members_count`, so the only available fix
was to drop it — **and three other tokens went with it, leaving four
enforcing nothing.** The documented reason was locally correct and silently
cost coverage. Fixed by giving each token a match rule: substring for 21,
prefix for `rs_`. Verified mechanically — all six attacks reject, `rs_total`
rejects, `members_count` passes, nothing mandated breaks. **No token had to be
dropped and coverage was not traded for a false-positive fix.**

### F9 — a specified test withdrawn as unwritable
The CTO withdrew its own claim and the reasoning under it: **a custom GUC is
settable by any role in any session, and Django settings have no say in it.**
The guard stops Django's own flush and an accidental TRUNCATE; **it does not
stop a determined session and was never going to.** Replaced with what is
testable, all of which QA verified by reading the migration.

### F8 — floor raised rather than wording lowered
A CHECK requiring all six evidence keys and a non-blank human name on any
Gate C row. **A CHECK cannot reference another table**, so the typed facts and
FK resolution stay in the command, and §4.1(b) now states which layer enforces
what — chosen over plpgsql reading three tables, which would be **unexecuted
text until a Postgres box exists**, the very problem that worsened this pass.
Residual named honestly: a forged authorisation is still possible from
application code, **but it is an INSERT plus an UPDATE into a table whose rows
can afterwards be neither deleted nor rewritten, so a forgery is permanent,
attributable evidence of itself.**

### The number to put in front of the founder — accepted risk A14
**The rework added three PostgreSQL-only guards, so unexecuted
security-relevant SQL went UP across a rework whose entire purpose was to make
the controls real.** Six security controls now exist as plpgsql no server has
parsed. Two agents reviewing the text did catch a real ordering bug, which is
worth something — **but text review is not execution, and the honest statement
until that run is that six controls are specified, reviewed, and unexecuted.**
The first PostgreSQL run is now a named deliverable with a six-item checklist,
not a side effect of S2 starting.

**S0 re-approval: four conditions, all backend's, all small** — `p14.py` plus
the F6/F7 fixes in one commit, the flush fixture, and the completeness CHECK.
**Not conditions:** the two missing P14 controls are S1's first commit; the
Postgres run is the S2 gate. Scheduled, not suspended.

---

## D-027 — Backend closes all ten findings plus the disclosure; one allowance escalated
**Date:** 2026-10-21 · **Decider:** ceo-planning
**Evidence:** ENGINE-DIVERGENCE v1.2 §9 items 9-11

`tests/contract/test_p14.py` is fully green. Backend's own trees are 214
passed / 28 skipped. **It edited nothing in QA's trees**, correctly.

### F10 — the disclosure closed with two changes, not one
An anonymous key **must parse as a UUID**, which makes API-CONTRACT §4.1's own
"a collision requires guessing a UUIDv4" argument true rather than assumed.
**And an anonymous replay now returns the status and never the stored body** —
the retry still gets the right code and is still not re-executed, it just does
not get a body it has no claim on. **There is now no path on which one
anonymous caller receives another's grievance reference.** Authenticated
replay is pinned by a test, because the narrowing must not break the mechanism
it protects.

### F6/F7 — all 22 tokens enforced, and the type gap closed
The rule now reads **every column in any type**, not only numeric — which was
what let `receipts.amt text` through — and the exemption is the two named
columns, with the table-wide exemption set to `None`, which is what QA
asserted it should be. Both changes are **tightenings, so by the CTO's own
procedure neither is a founder escalation** — stated in the commit message and
the module header so the bar is seen to have been considered.

### The one thing backend did NOT decide, and was right not to
Enforcing the bare tokens collides with names three frozen contracts mandate:
`due` appears in roughly fifteen SLA-clock columns, and `sum` sits inside
`consume_magic_link`, which API-CONTRACT freezes. Backend exempted three
shapes and **escalated rather than ruling, because an allowance is not a
tightening.** It also established the better order of resort: **where the
colliding name was its own, it renamed instead of exempting** —
`run_due_jobs` became `run_pending_jobs`. Routed to the CTO to ratify or send
onward; the CEO reading is that a timestamp, a state and a verb cannot denote
a consideration, so this is the `status` class.

### F4/F5 — both phantom controls now exist
`apps/core/p14.py` is the single expression of the rule in code and the guard
**imports** every list rather than retyping it. The source grep exists, **with
its own guard proving each declaration shape is visible and recognised,
because a grep that silently matches nothing is this project's recurring
defect.** It found two real collisions on its first run.

### F9 — backend withdrew its own claim in its own file
The fixture now exists, and §7.1 states in terms that **no such test exists and
none could**: a custom GUC is settable by any role in any session and Django
settings have no say in it. **What the guard actually buys is narrower than it
read — it stops Django's own flush and an accidental TRUNCATE, not a
determined session.** Backend apologised for the claim the CEO agent repeated
to the founder.

### F8 — the floor is in the database, and its bound is asserted
Migration 0005 enforces six evidence keys and a named human on both engines,
13 assertions. **Found while writing it: both engines' bare trim functions
strip spaces only, so a single tab passed as a named human.** Both bodies now
pass an explicit whitespace set.
**And the bound is a test, not a sentence:**
`test_the_database_floor_does_not_check_whether_the_evidence_is_true` shows a
placeholder reference still opens the gate. **"Every box filled" is not "every
box true", and the go/no-go packet must not read it as such.**

### An incident that supports D-026's conformance rule
The float check backend replaced **had gone quadratic**, taking the suite from
9 seconds to 72 under QA's attack suite, because it re-read the schema per
column. **A control nobody had executed was both incomplete and slow, and
neither was visible from the specification.**

**Unchanged and larger: every Postgres-side body is unexecuted text** — two
append-only triggers, the `campuses` write guard, the new evidence trigger,
the TRUNCATE escape, `ENABLE ALWAYS` — plus every race.

---

## D-028 — Exemptions ratified on an argument neither agent had made
**Date:** 2026-10-21 · **Decider:** ceo-planning, recording cto ratification

**All three shapes ratified, no split.** The CTO checked the CEO reading
rather than accepting it, and agreed: a deadline, a state and a verb, none of
which can denote a consideration.

### The decisive argument was one neither of us made
**The other layer independently rejects all three as numeric columns.**
`due_at`, `overdue` and `purge_due_at` end in no permitted non-monetary word,
so **a numeric column with any of these names fails regardless of what the
token layer exempts.** The exemptions can therefore only ever admit
**timestamps, booleans and function names — never a number.**

**That is the property that makes an exemption in one layer affordable: the
two layers cover each other.** Verified mechanically — all eight mandated
names pass; `amount_due`, `due_paise`, `total_due`, `sum_paise`, `cash_sum`
and also `payment_due_at` and `balance_due_at` all still fail, the last two
because **an exempt shape only excuses its own token, never the rest of the
name.**

**Promoted to `CLAUDE.md` rule 14:** prefer two independent layers over one
strict layer; before granting any exemption, state which other layer still
catches it — **and if none does, it is a widening, not a clarification.**

### The pattern, named on its third appearance, and promoted
> ***A guard that fires on the contracts it protects will be edited, not
> obeyed.***

M2, then `status`, now this. **The alternative to ratifying is never a
stricter control — it is a red test on mandated names and an edit to a
founder-escalating file under schedule pressure.** Promoted to `CLAUDE.md`
rule 13 together with backend's order of resort, now written down:
**rename ours → exempt a mandated shape, ratified → widen, founder
escalation.** Nothing has yet needed the third.

### The standing rule is now standing in the CTO's own documents too
THREAT-MODEL §6.2: any control named in the architecture must have a
conformance test asserting **(a) that it exists in the repository and (b) that
it executes within the suite's budget.**

**Limb (b) exists because of the quadratic incident.** The CTO's reasoning,
which is the clearest statement of why D-026 was adopted early: *a
specification can say what a control should do; it cannot tell you the control
is absent, wrong, or slow enough that someone will eventually delete it to get
the suite green. Only execution can.* **Which is also the sharpest argument
for why the first PostgreSQL run is a named deliverable and not a formality,
given six security controls are currently database code no server has
parsed.**

### F8's bound preserved as a test that must not be "fixed"
Recorded next to the layer table under the heading **"Every box filled" is not
"every box true"**, with the note that a placeholder passes because the
deny-list lives in the command, not the constraint — **and even the command
catches only a box nobody filled in, never one filled in falsely.** The CTO's
reasoning for preferring a test over a sentence: **the test is what gets read
by whoever changes the constraint next.**

### Also
`test_forbidden_response.py`'s gap was **propagation, not ownership** — it is
assigned in three of the CTO's documents and absent only from backend's file,
which the CTO cannot write to. **While checking, the CTO found and removed a
stale duplicate row in its own threat model that would have made two
statements of that control's scope diverge — the same transcription failure in
miniature, in the document that had just ruled against transcription.**

---

## D-029 — Code review APPROVES S0 (final). Two items carried to S1
**Date:** 2026-10-21 · **Decider:** ceo-planning, recording code-review PART THREE

**Verdict: APPROVED. S0 integrates. Nothing blocks.** All four conditions
verified by execution: backend trees 214 passed / 28 skipped in 0.94s,
migrations from empty through 0005 and back, the real command path refusing
and succeeding, five fresh probes. Suite back to 9.00s — **the quadratic float
check is gone.**

### C1 — the sibling hunt found exactly what it was sent for
**A trim-based blank check is a whitespace deny-list, and backend closed four
characters of it.** Verified: vertical tab, form feed, **NBSP — what a paste
from Word produces** — figure space and ogham space all pass the database
floor while Python's `strip()` catches them, so **for five of twelve forms the
floor is weaker than the command above it** — the F8 complaint recurring one
level down *inside the fix for F8*.

**And two characters pass both layers: zero-width space and BOM.** So
`authorised_by_human = "\u200b"` opens the gate **and renders as an empty name
in the audit row and the go/no-go packet.** Not a bypass — every other
conjunct holds — but the one field carrying the whole "a named human signed
this" rule can be satisfied by something invisible.

**Routed to backend now rather than deferred**, with the instruction to assert
the invariant and not the characters: a blank check must require **at least one
visible character**, not the absence of the whitespace we remembered. **This is
the second instance of `CLAUDE.md` rule 11** — a deny-list of characters is the
same shape as the token list that enforced 15 of 22.

### C2 — M5 inverted, in the document the packet rests on
Migration 0005 refuses an incomplete Gate C row at INSERT, so a saved row is
always complete — **but ADR-002 §4.1(b) still describes the opposite
workflow**, which can now never happen. The complete-or-absent invariant is
**not ratified anywhere.** A contract describing an operator workflow the code
has removed is the same defect as §7.1 asserting the opposite of the truth.
One paragraph from the CTO; QA re-points eight tests. **Must resolve before
S1.**

### The key-scope ruling, framed better than the CEO's question
Backend is right on the merits, and the boundary belongs in API-CONTRACT —
**but state the invariant, not the conclusion**: *`user_id` partitions the key
namespace, one principal per partition.* **The conclusion rots silently; the
invariant stays checkable.** Three reachable breaks named: a staff tool
writing a key under a student's id in S5 or S6, any impersonation or
service-account path, and **id reuse after purge** — SQLite is already recorded
as reusing a max rowid, S1 adds purge, and the replay window is 24 hours.

### Why the same gap is acceptable now and was blocking a round ago
The reviewer closed its own N2 objection with a distinction worth keeping
verbatim:

> **An absent control correctly reported as absent is a known gap; an absent
> control a compliance document claims is a false statement to a regulator.
> S0 ships the first.**

It accepted integration without `test_forbidden_response.py` **specifically
because ADR-003 §5.3.1 now understates** — and because a conformance test
asserts §5.3 cannot name a control the repository lacks. **That is the CTO's
structural fix doing exactly the work it was built for.**

### Checked last and most carefully, which is the right paranoia
Whether the performance fix had quietly reverted the union-versus-override
semantics — because **a collapsed union would look identical in every green
test, would remove the only part of P14 that can be *checked* rather than
named, and would do it in a commit whose stated purpose was speed.** It had
not. Verified by adding a raw-DDL `real` column to a table that *has* a model:
caught.

### The standing caveat, in the reviewer's strongest terms
**Six plpgsql bodies across migrations 0002, 0003 and 0005 have never been
parsed by a server** — both append-only guards, the truncate escape, the gate
write guard and the evidence-completeness guard — **and five are the security
controls three review passes have been spent on. Reviewed as text by two
agents, verified by neither.** A local PostgreSQL 16 costs Rs 0 and **is now
the only thing between "argued to work" and "known to work."**

---

## D-030 — Contract items closed; nothing blocks S1
**Date:** 2026-10-21 · **Decider:** ceo-planning, recording cto

**C2 ratified, and the offending sentence deleted rather than annotated.** A
Gate C row is written **complete or not at all**; the per-item checklist is a
pre-flight affordance on an **unsaved candidate row**, not a report on a
stored draft, so the useful half survives.

**The workflow cost is named honestly rather than buried:** an operator
assembling evidence over days holds it outside the database until every item is
in hand. The CTO's reason for calling that the right trade is the one to keep —
**a half-filled authorisation sitting in the table for a week is exactly the
artefact someone later mistakes for an authorisation.**

**Key scope: the CTO took the reviewer's framing over its own.** API-CONTRACT
§4.1 now states **the invariant as normative and the rule as its
consequence** — *`user_id` partitions the key namespace, and every key in a
partition is written by that one principal* — because **the conclusion rots
silently while the invariant stays checkable against a future design.** All
three reachable breaks are tabled with where they arrive.

**Flagged forward, and the CEO agent is carrying it:** before backend builds
S5 or S6, the first break arrives — **the moment a staff tool writes an
idempotency key under a student's `user_id`, the UUID rule extends to the
authenticated namespace.** Cheaper to design around now than to discover when
the partition already has two principals in it.

**The N2 distinction is in ADR-003 §5.3.1 verbatim**, with the CTO recording
**why the same gap blocked a round ago and is acceptable now: nothing about
either missing control changed — both are still unwritten. What changed is
that the document understates rather than overstates, and a conformance test
makes it unable to do otherwise.**

**The flush-GUC wording was already correct and the CTO checked rather than
assumed** — *"No mechanism can make production refuse the SET"* — with nothing
resembling the withdrawn claim surviving outside the block that quotes and
withdraws it.

### The standing item, now in both agents' words
**Six plpgsql function bodies across migrations 0002, 0003 and 0005 have never
been parsed by a server**, and five are the security controls three review
passes have been spent on: the audit append-only and no-TRUNCATE guards, the
`gate_authorisations` append-only guard, the `campuses` discovery write guard,
the Gate C completeness guard, and the price-immutability trigger.
**Each rework that strengthened the controls raised this count.**

**The counterpoint is kept because it cuts both ways:** text review caught a
real ordering bug — `TG_OP` tested before `NEW`/`OLD` are touched, which would
have made a guard deploy and protect nothing. **It shows text review is worth
doing and simultaneously proves it is not execution.**

**Nothing blocks S1.** C2 was the must-resolve and it is resolved.

---

## D-031 — Suite fully green for the first time; C1 closed with an invariant
**Date:** 2026-10-21 · **Decider:** ceo-planning
**CEO-verified:** `481 passed, 54 skipped, 0 failed` on SQLite 3.45.1

**C1 closed with the invariant, not the characters** — which was the actual
ask. `has_visible_character()` asks Python's Unicode database **per
character** whether anything printable, non-whitespace and non-format is
present, so **it consults no list and can gain no entries.**

**Why the original fix missed two characters, and it is worth knowing:
zero-width space and byte-order mark are *format* characters, not whitespace.
They survived a strip and rendered as nothing.** A whitespace deny-list could
never have caught them, however long it grew.

**Backend was plain about where it could NOT apply the invariant** rather than
claiming it had: SQLite has no regex at all, and Postgres's character-class
behaviour is libc- and locale-dependent, so a category test in SQL would be
**less** predictable than an enumeration. The migration therefore keeps an
explicit eleven-codepoint set, **declares its own ceiling** — an invisible
character not on the list passes the floor — and points at the layer that
generalises. Each entry is written with the reason it is there so the set can
be **extended rather than edited** (rule 11).

**The resulting relationship is the right one for a floor:** it no longer sits
above the command for any measured form, and the command is strictly stronger
for the forms nobody has measured. Measured across twelve whitespace and
format shapes on two fields, with 29 new assertions.

**The bound test now covers shape as well as content**, with the honest claim
in its own docstring: *"every box holds something visible that nobody checked
the truth of."* A placeholder still opens the gate, and **the go/no-go packet
must know the difference between an invisible name, which is now blocked, and
a plausible fake name, which is not.**

**`test_forbidden_response.py` written, picked up from TASKS rather than
waited for** — the control the launch-packet sentence depends on. Recursive on
purpose, **because the jsonb limb is a nested document and a top-level-only
walker would miss the one shape the control exists for.** With only two
endpoints in the slice, the live half could have passed while matching
nothing, so ten payloads prove the walker fires and six prove it does not flag
a legitimate response. Tokens **imported** from `apps/core/p14.py`, never
retyped.

### Judgement recorded because the instinct was right
TASKS.md names the source grep one thing; the repository another. **Backend
renamed it, then reverted — because QA imports it by name in three green
tests.** It judged that turning three of QA's passing tests red to match a
filename was the wrong direction for a one-line correction, and escalated.
**CEO position: change the contract to match the repository, not the
reverse** — resolving it the other way is three agents' work to make a
document right that could be right in one line.

**Backend also left the union-versus-override asymmetry spelled out in the
guard's docstring specifically so the next performance pass must read why
before collapsing it** — the correct response to the reviewer's near-miss,
since that regression is invisible in a green suite.

**Unchanged: every Postgres-side body is still unexecuted text**, now
including migration 0005's codepoint set and evidence loop.

---

## D-032 — Founder authorises local tooling; version control exists at last
**Date:** 2026-10-21 · **Decider:** HUMAN FOUNDER

**Approved:** `git init` locally and a native PostgreSQL 16 install on Windows.
No third-party remote.

**Version control is in place.** Initial commit `fd57a07` — 130 files, 37,531
lines, suite green at 481 passed / 54 skipped / 0 failed. **For this entire
project until now, an agent overwriting a file was unrecoverable.** The risk
the CEO agent raised in D-013 and repeated at every checkpoint is closed.

**PostgreSQL install — reported honestly, because the first attempt lied.**
The first `winget install` **exited 0 without installing anything**: its source
index could not update, so no package was found and the command still returned
success. No binaries, no service, nothing listening on 5432 — verified three
ways rather than trusted. **This is the same defect class the project has now
hit repeatedly: a green result that proves nothing.** After a source update the
package resolved and the install is running.

**Local superuser password generated, not chosen** — 24 random characters,
written outside the repository, never stated in conversation. `.env` is
gitignored and `.env.example` carries a placeholder only.

### What this unblocks, and it is the largest item on the board
**Six plpgsql function bodies across migrations 0002, 0003 and 0005 have never
been parsed by a server** — both `audit_log` guards, the `gate_authorisations`
append-only guard, the `campuses` discovery write guard, the Gate C
completeness guard, and the price-immutability trigger. **Five are the security
controls three review passes have been spent on, and each rework that
strengthened them raised that count.**

They were reviewed as text by two agents and verified by neither. The CTO is
writing the first-run execution checklist as a named deliverable, ordered by
what would be most expensive to discover late, and required to state **what the
run would not prove** — since that is the half a go/no-go packet gets wrong.

**Also recorded: text review is not worthless and not sufficient.** It caught a
real ordering bug — `TG_OP` tested before `NEW`/`OLD` are touched, which would
have deployed a guard that silently protected nothing. The checklist must treat
text review as having **reduced** the risk, not eliminated it, and name the
items it cannot have covered at all.

**Both agents stopped mid-task when the previous session ended** — the CTO on
three amendments, QA before its S0 verdict. Both resumed with their context
intact. **The thirteen charters are now registered as real agent types**, so
the D-005 fallback is retired and agents are invoked by charter name.

---

## D-033 — S0 INTEGRATES. Both gates pass
**Date:** 2026-10-21 · **Decider:** ceo-planning
**Evidence:** REVIEW-S0.md (APPROVED, Part Three) + QA-S0.md v4.0 (PASS)
**CEO-verified:** `570 passed, 55 skipped, 0 failed`

**Code review approved and QA passes. Per the CTO charter and `CLAUDE.md`
rule 5, S0 is integrated.** QA's tree across four passes: 169 → 182 → 246 →
336 tests, 3 → 10 → 0 → 0 failures.

**QA verified the twelve conversions rather than assuming them, and
strengthened them.** The eight gate tests now assert a `DatabaseError`
**carrying "4.1(b)"** rather than merely that something raised — an unrelated
error would have satisfied the weaker form. Each conversion gained a
**positive counterpart, so a guard cannot have replaced a hole with an
outage**: a complete authorisation still saves and still opens the gate, the
other gate letters stay unconstrained, authenticated replay still returns its
body. It also closed a launder route — save as one gate letter, update to
another.

**The Unicode invariant is genuinely a property, not a list in disguise.** QA
derived 26 invisible forms **independently** rather than re-running backend's
list; all 26 refused, **including six no list in this repository has ever
named** — NUL, DEL, soft hyphen, word joiner, Mongolian vowel separator, ogham
space mark. And the other half holds: a real name *containing* a zero-width
space still passes, so **"at least one visible character" has not become "no
invisible characters anywhere"**, which would have refused anything pasted out
of a document.

**The two layers are independently verified as independent.** U+200C is not on
the database's eleven-codepoint list, the database accepts it, and the command
refuses it — **two different mechanisms, not two copies of one list.** And
checked in the direction that can hurt an operator: for all 26 forms the
command refuses, so **there is no value an operator is told is complete that
the database then rejects.**

### F15 — the control written to close a gap does not cover the gap
`test_forbidden_response.py` **matches forbidden keys but not values.**
`{"handover_note": "Paid Rs 300"}` passes. A phone number in a message passes.
A double-encoded JSON string passes.

**This is the limb that matters: ADR-003 §5.3 names this control as the
compensating control for the free-text residual, and the free-text residual is
a value, not a key.** Assigned to S1, where §5.3.1 already places it.

**And the conformance mechanism caught it.** QA wrote the third detector: a
test now asserts §5.3.1's table cannot claim this control implemented while
two limbs are absent, **so the stronger launch-packet sentence cannot be
quoted and a test says so rather than a person remembering.** This is D-026
working on the control that was itself written to close a documented gap.

**F14, recorded not fixed:** three blank-rendering **printable** codepoints
pass the invariant — braille blank and two Hangul fillers — because Unicode
calls them printable. Closing it needs a list, which is what the invariant was
adopted to avoid. Exposure requires someone with write access obscuring their
own name in an append-only audited row.

**Two audits widened from lists to properties**, which is rule 11 applied
without being asked: the migration text audit now spans **every** migration —
it covered two, so the sixth guard was escaping it — and the trigger check is
now *every* Postgres trigger must be ALWAYS, rather than a list of five,
**because a fixed list is how the seventh goes unnoticed.**

**Open, none blocking:** F15 and F11 and F13 at S1, F12 at S2/S4, F14 record
only, and evidence-presence-not-truth open by agreement before Gate C.

---

## D-034 — First PostgreSQL contact: the migrations do not apply
**Date:** 2026-10-21 · **Decider:** ceo-planning
**CEO-verified directly:** PostgreSQL 16.15 installed, service running, port
5432 listening, role and database created, `.env` written and gitignored.

**Item 0 of QA's checklist — `migrate` from empty — FAILS.**

```
psycopg.ProgrammingError: incomplete placeholder: '%';
if you want to use '%' as an operator you can double it up, i.e. use '%%'
```

Four `%` characters inside plpgsql `RAISE` format strings are parsed by psycopg
as parameter placeholders **before Postgres ever sees the statement**:
`0002_append_only_triggers.py:23` and `:44`,
`0003_gate_column_write_guard.py:111`, `0005_gate_evidence_complete.py:112`.

### Why this entry matters more than the bug
**This is the exact class of defect four agents predicted and none could
find.** Three review passes, two independent agents reading the plpgsql as
text, a conformance-test regime, and a project rule about unexecuted code —
and the finding was still waiting at first contact with a server. **Not one of
the six guards had ever been parsed; it turns out the migration containing
them could not even be applied.**

So the standing caveat was not conservative. It was correct, and understated:
the position was "six controls are specified, reviewed, and unexecuted", when
the truth was that **the schema carrying them did not install.**

**Recorded as vindication of a decision, not of an agent:** the CTO, code
review, QA and backend all independently refused to call these controls
verified, and every one of them named execution as the only thing that would
settle it. **Had any of them accepted text review as sufficient, this would
have been discovered on a pilot box.**

### The fix is a two-layer escaping problem and is not trivial
plpgsql needs a single `%` to interpolate; psycopg needs it doubled to pass one
through. So doubling is right — **but the message a developer actually reads
must be verified by triggering each exception on Postgres**, because a guard
with a mangled message still protects while the next person debugging it reads
a broken string. **This project has twice been bitten by a control whose text
said something other than what it did**, so the fix is not complete until the
text is read off a live server.

**Routed to backend**, which owns the migrations, together with QA's full §7
checklist. **QA will re-verify independently on Postgres afterwards** — the
author of a fix does not grade it.

### Also recorded: the installer lied first
The first `winget install` **exited 0 having installed nothing** — its source
index could not update, so no package was found and the command returned
success anyway. Caught only because the result was checked three ways
(binaries, service, listening port) instead of trusting the exit code.
**A green result that proves nothing is now the fifth distinct instance of
this project's recurring defect, and this one came from outside the project.**

---

## D-035 — Postgres checklist written; a CEO miscount corrected
**Date:** 2026-10-21 · **Decider:** ceo-planning, recording cto
**Evidence:** `company/architecture/POSTGRES-FIRST-RUN.md`

### CEO correction — I was repeating a wrong number
**There are FIVE plpgsql bodies, not six.** CEO-verified by counting them:
`audit_log_is_append_only`, `gate_authorisations_is_append_only`,
`campuses_gate_is_authorised`, `bookhop_truncate_guard`,
`gate_authorisations_evidence_complete`. **The price-immutability trigger does
not exist** — `listings` is an S2 table.

"Six" was stated to the founder repeatedly and appeared in three of the CTO's
documents. The CTO found it by reading the migrations rather than taking the
brief, and corrected A14, the S2 gate and the checklist. Its reason is the one
that matters: **a checklist listing a control nobody can run is how an unrun
control gets reported as run.**

### The checklist's item 1 is a shape nobody had named, including me
**`check_function_bodies` validates plpgsql *syntax* at creation, but plpgsql
resolves identifiers and operators at the first execution of each branch.** So
a guard can be created cleanly, pass every happy-path test, and fail the first
time someone does the forbidden thing — **and the worst form of that failure
still blocks the operation, so it looks exactly like the guard working while
proving nothing about the guard.**

Hence the instruction, forwarded to backend mid-run and promoted to
`CLAUDE.md` rule 16: **exercise every refusal path and assert the message
text, not the exit status.** A raised error is not evidence the guard fired for
the reason you think. This is the same shape as the token list that enforced 15
of 22 while reporting green — one layer deeper and considerably harder to see.

### Two traps where a control could protect the wrong thing silently
`chr(n)` above 127 requires the database encoding to be UTF8, so the
eleven-codepoint set could be **silently protecting against the wrong
characters**. And a bare `btrim(NULL, …)` is NULL while **a CHECK constraint is
satisfied by NULL** — the trigger form avoids this and the CHECK form does not,
so which one actually runs must be confirmed.

**Credit recorded because it says what to preserve:** backend built the
whitespace set as `chr(32) || chr(9) || …`, which sidesteps
`standard_conforming_strings` entirely. A literal would have been six literal
characters, and the guard would have stripped backslashes while letting
zero-width space through. **That was the trap the CTO expected to find and
backend had already avoided it.**

### A Django trap that cannot exist on SQLite
An `IntegrityError` inside `atomic()` **poisons the transaction**, so whatever
converts it to a 409 must sit in a nested atomic or savepoint, or **the error
response itself fails.** On SQLite the loser gets a lock error instead, so this
has never been exercised — and it lands on offer acceptance in S4 if it is not
designed for now.

### §2 of the checklist is what the run will NOT prove
It tests **existence and behaviour, not fitness** — a guard that faithfully
refuses the wrong thing passes every item. Nothing about `listings` or
`transfers`. Nothing about the two still-unwritten application-layer P14
controls. **Nothing about evidence being true** — a placeholder reference and a
plausible fake human still open the gate. **The reporting section requires
`NOT APPLICABLE` with a reason and forbids recording it as PASS**, and requires
§2 to be filed with the completed checklist, because §2 is what stops the run
being read as more than it is. **A14 is narrowed by this run, not closed.**

### Why run controls three agents have already reviewed — answered as a ratio
Of the nine items, **text review cannot have touched seven at all** (runtime
resolution, replica role, encoding, operator resolution against real column
types, GUC semantics, concurrency, migrate and reverse), partially covered two,
and meaningfully established two. **That ratio is the argument for the run**,
and text review did earn its keep: reading caught the ordering bug that would
have deployed a guard protecting nothing.

**Promoted to `CLAUDE.md` rule 15, on its second occurrence: an invariant
beats a list** — with the honest rider that where an invariant cannot be
expressed, a list must **declare its ceiling in the same place** and point at
the layer that generalises.

**Also settled:** the filename stays as the repository has it, and the CTO
found a better reason than incumbency — it is consistent with its three
siblings, and **a guard family named by one convention is easier to notice a
gap in.**

---

## D-036 — First PostgreSQL run PASSES. Two real defects found that SQLite could never reach
**Date:** 2026-10-21 · **Decider:** ceo-planning
**CEO-verified:** Postgres `571 passed, 60 skipped` · SQLite `573 passed,
58 skipped` · six triggers live, every one `tgenabled='A'`

**All nine checklist items PASS**, each asserting SQLSTATE **P0001** alongside
the message text — a non-P0001 refusal was counted as a failure, which is
`CLAUDE.md` rule 16 applied on its first outing. Each paired with a permitted
counterpart, and **the two riskiest given negative controls**: downgrading a
trigger off `ENABLE ALWAYS` shows the write *does* get through under the
replica role, and removing the nested `atomic()` shows the transaction *is*
poisoned.

### The fix was better than the one I proposed
I suggested doubling the `%`. Backend instead passed **`params=None`**, which
**removes the escaping layer rather than escaping for it** — no SQL text was
touched, so the plpgsql still reads exactly as it would in `psql`. Its reason
for rejecting my suggestion is the right one: **doubling works but puts two
layers under one message and fails silently**, because a mis-doubled specifier
still refuses the operation, so only the text breaks.

### Three predictions were WRONG — which is the point of running it
- The exception class is **`ProgrammingError`**, not `InternalError`. psycopg 3
  maps it differently from psycopg 2, which is where the prediction came from.
  **The hazard was real and the named class was wrong — and "catch
  `DatabaseError`" is the only reason it cost nothing.** No caller needed
  fixing.
- **A boolean CHECK probe was passing on SQLite for the wrong reason**, and
  ENGINE-DIVERGENCE had recorded the wrong reason **as deliberate**.
- A float into an integer column is **silently rounded**, not rejected — so
  detection belongs to the service layer and never to the database.

### Two defects in shipped S0 code, both unreachable from SQLite
- **The audit chain dropped a row under concurrency and reported it as
  tamper.** A four-attempt retry with no backoff lost an append at 12
  concurrent appenders and raised `AuditChainBroken` — **a tamper-shaped
  error during a load spike**, which is the worst possible false alarm in this
  system. Measured tail: 5 attempts at 8 appenders, 7 at 24. Now a budget of
  12 with jittered backoff and a distinct contention error that is deliberately
  **not** a subclass.
- **The flush escape bound a per-connection setting to a pytest session**, so
  one threaded test closing connections killed the next transactional test in
  teardown. **That is exactly the S4 collision the earlier finding was written
  to prevent**, and the double-booking test triggers both halves. Now bound to
  Django's `connection_created` signal.

### The teardown item could not be measured, and why that is the familiar shape
**No test in the repository used `transactional_db`. All three mentions of it
were prose.** The fixture the architecture called mandatory was guarding
nothing, because nothing exercised it. Backend wrote the test and a negative
control. **This is the project's recurring defect once more: a document
describing a mechanism that had no instance.**

### Findings against the checklists themselves
QA's "skip becomes run" **cannot happen** — those tests have no body; 25 are a
bare skip and 8 now print a reason naming SQLite while running on Postgres.
And **`sqlmigrate` never generates this DDL on either engine**, because the
operations are `RunPython`; the catalog is the route, and is better evidence.

**Recorded because it is rule 13 obeyed without prompting:** one of QA's guards
fired twice on backend's new tests, and **both times backend renamed its own
test rather than widening QA's allowlist** — rung 1 of the order of resort.

### Still unverified, explicitly
**Double-booking is implemented nowhere and verified nowhere** — the index is
on `transfers`, which is S4; item 8 was a *rehearsal* of the same mechanism on
the anonymous idempotency index, not the thing itself. Nothing about
`listings`. `expected_version`'s failure mode, the reservation-expiry race, and
multi-worker job claiming are **unverified on both engines**. **Evidence truth
is unchanged: a placeholder reference still opens the gate.** And nothing about
scale — the retry budget comes from 40 appenders on a near-empty table.

**A14 is narrowed, not closed**, exactly as the checklist required.

---

## D-037 — Audit chain stays global on a threat-model argument; two rules promoted
**Date:** 2026-10-21 · **Decider:** ceo-planning, recording cto

### The chain stays GLOBAL, and the argument inverts the obvious answer
Per-scope chains look like a free throughput win. They are not. **A single
global chain makes the whole audit log one tamper-evident sequence, so no row
anywhere can be removed without breaking it. Split it per campus and an
insider can delete one campus's entire audit history while every other chain
still verifies clean** — an invisible gap, because nothing links the scopes any
more.

That is a direct regression against the insider risk the chain exists to
address. **At pilot write rates we would be paying a threat-model cost for a
throughput problem we do not have:** 40 concurrent appenders measured against
single-digit appends per minute at peak. Checkpoint anchoring is the right
upgrade when one is needed and **does not carry that weakness**; it buys
nothing now.

### The watcher, because splitting an error class without one just moves the silence
**The CEO agent's objection was accepted:** splitting contention out of the
tamper error converts a false alarm into a silent failure unless something
watches it. Specified: `AuditChainBroken` stays a founder escalation and must
keep meaning tampering; `AuditAppendContention` **pages on-call if greater
than zero in an hour**; and — the part that matters — **attempts-to-win p50/p99
goes into the daily digest as a counter, so contention is visible as a
*leading* indicator** rather than only once it has broken something.

**The honest limit is written down:** the budget is sized from data, but **the
data is about the mechanism, not a campus under load.** 40 appenders on a
near-empty table establishes that contention is survivable, not where the
ceiling is — the head read is trivial on an empty table, while a year of
retained rows contends on a hot rightmost index page with the nightly purge
running against the same table. **So re-measurement is triggered
unconditionally by the first month of real traffic**, not only by thresholds.

### Escalation 16 was sharper than a wording fix
PostgreSQL enforces integer storage **by silently rounding, not by raising**.
So the claim splits: *no float is ever stored* is the database's guarantee;
*a float being passed is detected and reported* belongs to the service layer
**and nothing else.** **A silent round is worse than a rejection, because a
rounded money value is a wrong value that looks right.** The service must
reject a non-integer, never round it.

**And the required test is not the obvious one:** "the column is of integer
type" passes while the bug ships. The assertion that matters is that creating a
listing with a fractional price is **refused.**

### Two rules promoted to `CLAUDE.md`
**Rule 17, which the CTO proposed and which closes a real gap in rule 9:**
label every cross-engine or cross-library claim `VERIFIED HERE` or
`ASSUMED THERE`. **Rule 9 asks whether a control exists; it does not ask
whether a document's explanation of that control is true** — and three
predictions were wrong inside documents that had passing conformance tests.
The worst was **green on both engines for two different wrong reasons**: on one
it compared untyped integers, on the other it never reached the constraint,
and the document recorded the wrong reason as deliberate.

**Rule 18, the third instance of a pattern the CTO named: a control that
guarantees a state does not thereby detect a bad input.** The gate's
constraint proves every box is filled, not that any is true; the guard proves
a column cannot hold a float, not that none was passed; the database proves no
float is stored, not that none was sent. **In all three the schema is the
floor, detection lives above it, and the obvious test passes while the defect
ships.**

**Generalised from the wrong exception class:** when a document predicts a
specific identifier across an engine or library boundary, **mitigate at the
parent, not at the prediction** — defending against a class costs the same as
defending against a guess and survives being wrong.

### Status
`POSTGRES-FIRST-RUN.md` marked **RUN AND PASSED** and retained as the G4
artefact **with its "what this does not prove" section attached**. A14 is
**narrowed by execution, not closed**, with the residue split out: four
properties remain unexecuted because their tables do not exist — price
immutability at S2, double-booking and MVCC at S4, metric SQL at S7 — **each
with its test shape pre-written so none is re-derived.** The S2 gate reads
**OPEN**.

### What the run was actually worth, in the CTO's words and the CEO agent's view
**It passed nine of nine, and that is not where the value was. The value was
the two defects SQLite could not have shown** — an audit row dropped under
contention and reported as tamper, and a session-scoped fixture binding a
per-connection setting — **and both would have landed on S4's double-booking
test, which needs transactional mode *and* multiple real connections, so it
would have tripped both at once.** Both sat in the seven of nine items text
review could not reach. **The pre-run framing — that review had meaningfully
touched two of nine — turned out to be the right way to describe the risk.**

---

## D-038 — S0 CLEARS on both engines. A CEO-repeated claim corrected
**Date:** 2026-10-21 · **Decider:** ceo-planning
**CEO-verified:** PostgreSQL 16.15 `617 passed, 49 skipped` · SQLite
`579 passed, 87 skipped` · three consecutive Postgres runs, no flakes

**QA passes on both engines. S0 is verified, not merely integrated.** 371 QA
tests, zero failures on either engine. **The install converted 35 skips into
assertions.**

### CEO correction — I repeated a claim that did not land in the repository
I told the founder backend had asserted the SQL error code alongside every
message. **QA measured it: `P0001` appears in backend's trees exactly once, in
a comment.** CEO-verified. The message half is enforced and is a good
engine-neutral test; **the SQLSTATE half was in the report and not in the
code**, so a guard that began refusing via a CHECK constraint while keeping its
text would pass tomorrow. QA has now encoded it for all five bodies in its own
trees. Severity low — the hazard rule 16 names changes the text too — but
**this is rule 17 on its first day: a claim about a control that was true of
the run and false of the repository.**

### The assertion nobody's checklist asked for, and it mattered most
**QA's five tamper-DETECTION tests were skipping off SQLite**, because the
helper used a SQLite-only catalog table. So backend's run verified
**prevention** on Postgres while **detection — QA's actual charter question —
had only ever run on the dev engine.** Two different claims. The helper now
branches, and asserts afterwards that no guard was left enabled, **or the
tamper is blocked and the detection assertions pass for the wrong reason.**
All five now run on both engines.

### Both defects verified, including the direction that would have been worse
Contention raises the contention error and the chain still verifies — **and a
real tamper still raises the tamper error, naming the row id.** QA tested that
explicitly, because **a fix that made a real tamper look like contention is the
obvious way to get this wrong.** It also checked the property an on-call rota
depends on: the two classes share a parent and neither is in the other's MRO,
so a monitor on tamper is not woken by a load spike. The flush escape was
verified by running the exact sequence that broke it, and in four threads.

### Negative controls: one verified, one honestly out of reach
The nested-`atomic()` control **genuinely fails** without the savepoint. The
replica-role control **needs a superuser**, so QA verified its *premise* (the
app role is refused that setting, SQLSTATE 42501), its *state* (all six
triggers `ALWAYS` from the catalog), and that the test role is not a superuser
**so the finding is what it appears to be.** The control itself rests on
backend's run and belongs in S8's restore rehearsal — **which is also where
`ENABLE ALWAYS` earns its place, since the bypass is unreachable from the
application.**

### Sibling hunt: four unmeasured claims found, none a defect
Including one where **QA's own P14 attacks depend on an unmeasured premise** —
every attack creates a real table with raw DDL and relies on DDL rollback. And
one where **the reasoning was the risky part**, not the claim. QA's framing:
**unmeasured is not the same as wrong, and the difference is only visible once
someone runs them.** It added the regression for the probe that had been green
for two wrong reasons.

### Weaker than it looks, in QA's own section
The anonymous-index contention test is a **rehearsal** of double-booking, not a
proof — *a pass there predicts a pass there.* Three correct predictions
produced no failure only because S0 has no subject matter for them. **The one
that will bite is `LIKE` becoming case-sensitive: every S2 search test written
on SQLite can pass locally and fail here**, so the standing S2 rule is **run on
PostgreSQL before asking for review.** And the metric views unlock nothing
until S1–S4 create rows — **the engine stopped being the blocker and the
tables became it**, which is what that skip now says.

**F16 — what the retry budget does not cover**, and it is sharper than the
threshold: production appenders are **asymmetric**. One long mutation holding
its transaction open races many short ones, **and the long one can least afford
to lose.** The bench had no such profile. Exhaustion is at least diagnosable
now, so whatever the right budget is, exceeding it is not misreported.

### The process note, recorded because it is the most useful thing in the report
**Three of QA's five passes found a defect in something QA itself had
written** — the P14 transcription, a contract misreading, and now its own
bodyless skips. **Each was caught by someone reading its output against
theirs.** QA's conclusion, which the CEO agent adopts: **keep both reports side
by side at every gate rather than treating either as settled.**

**Seven open items, all owned, none blocking.** Double-booking remains out of
scope and implemented nowhere.

---

## D-039 — Founder defers the audit; S1 proceeds
**Date:** 2026-10-22 · **Decider:** HUMAN FOUNDER

**Decision.** Skip the weekly audit and the Red Team pass for now. Build S1:
accounts, age eligibility, campus verification, profiles, consent, deletion
and the purge job.

**The CEO agent's concern, raised once and not re-argued.** Thirty-eight
decisions are now logged with **no adversarial review since G1**, and the
weekly audit → delegate → measure → improve loop has never run. Red Team's
last word was that the monetisation thesis was falsified and the product
thesis survived only as a hypothesis — **and that hypothesis is now carrying a
schema.** Risk R-15, logged on day one, is exactly this: *agents produce
volume, not validated progress.* Rigour about how we build is not evidence
that we should be building this.

**Founder has decided; proceeding at full effort.** Recorded so the question
is not lost rather than to reopen it. **R-15 and the deferred audit stay open
in the register**, and the next natural forcing point is Gate B — the first
real user — where Red Team review is already required and cannot be deferred,
because that is when real personal data enters the system.

**What S1 does not need and must not acquire:** no infrastructure spend, no
campus access, no counsel engagement. All of those arrive at Gate B. S1 is
buildable and testable entirely locally at zero cost.

**Sequencing.** Backend and frontend run in parallel against the ten frozen
account signatures — that is what the honest stubs were for — on disjoint file
trees, so "contracts before parallel work" holds. The five pre-assigned
control fixes land in S1's first commit, because `CLAUDE.md` rule 9 means a
control named in a compliance document with no code behind it is a false
statement, and two of ours currently are.

**The standing engine rule now applies to every slice: run on PostgreSQL
before asking for review.** `LIKE` is case-sensitive there and insensitive on
SQLite, so a search test written locally can pass and fail for real.

---

## D-040 — Scope narrowed: engineering only. Build and deliver the app
**Date:** 2026-10-22 · **Decider:** HUMAN FOUNDER

**Decision.** The founder is solo and wants **CTO work only**: develop the
application and deliver it. Everything else is out of scope until they say
otherwise.

**Stood down — do not raise these again unprompted:** incorporation and the
second-shareholder question, campus contacts and access, interviews, the
survey, the user test, the institutional probe, the Tamil reviewer, acquisition
budget, counsel engagement, and the weekly business audit. The Market &
Finance, Marketplace Operations, Product and Red Team agents are **dormant**
for this phase. Privacy & Compliance is dormant **as an advisory function**.

**What does NOT change, because it is architecture rather than admin.** These
are already frozen in the contracts, already implemented or scheduled, and are
simply how the code works. They are not decisions to be re-litigated and they
cost nothing to keep:
- **P14** — no settled transaction price, ever. The whitelist, frozen tables,
  source grep and response-boundary control stay.
- **No date of birth persisted in any state.** Adults-only, server-side.
- **Tombstone-plus-purge deletion** with a one-year retention floor and the
  pseudonym surviving.
- **No escrow, no custody of funds, no credits.**
- **The discovery gate**, which is also what makes the app safe to build and
  demo before anything is public.
- CSP, the audit chain, idempotency, the takedown clocks as schema.
- **WCAG 2.2 AA and the mid-range-Android-on-3G target**, which are product
  quality, not compliance.
- **The Tamil locale stays gated off.** No reviewer exists, so the flag stays
  false and English ships. This needs nothing from the founder.

**Retained engineering practice**, because all eighteen rules in `CLAUDE.md`
were earned by defects found in this project and dropping them would cost more
than it saves: code review and QA before integration, both engines green,
conformance tests for named controls, and no claim quoted that the repository
does not support.

**Delivery target.** A working, tested application the founder can run, with
the remaining slices in the frozen order: S1 accounts and deletion (in
flight), S2 listings, S3 discovery and notifications, S4 offers and the
transaction state machine, S5 handover coordination, S6 reports, moderation
and support, S7 analytics. Each slice goes through code review and QA and is
committed. The founder gets a run command and a browser preview once there is
a UI worth looking at.

**Recorded once and then dropped:** the thesis remains unvalidated and zero
students have been interviewed. That is now the founder's risk to carry
knowingly, not an open question for any agent to re-raise.

---

## D-041 — Red Team on engineering: the apparatus produces quality inside files and consumes it at the seams
**Date:** 2026-10-22 · **Decider:** ceo-planning
**Evidence:** `company/evidence/RED-TEAM/ENGINEERING-MEMO.md`

**The verdict, and it is the most useful sentence produced in this project:**

> Every defect the apparatus caught was **within-artefact** — a list enforcing
> 15 of 22, a trigger not reading `active`, a column stored and never
> compared. Every defect Red Team found is a **boundary defect**. All 18 rules
> are about claims and controls; **none is about end-to-end behaviour — which
> is why 835 tests pass and nobody has been served a page.**
> It earns its keep; the ceremony does not, and they separate cleanly.

### CRITICAL 1 — verified by the CEO agent directly
The app role holds `INSERT, UPDATE, DELETE, TRUNCATE` on **both**
`audit_log` and `gate_authorisations` (checked in
`information_schema.table_privileges`), and **can set the flush GUC** — I ran
it. So the TRUNCATE guard is defeated in two statements while the suite proves
the *other* bypass shut. And the gate's enforced floor sits three statements
below ADR-002 §4.1(b): placeholder evidence values that are **on §4.1(b)'s own
deny-list**, a mismatched legal entity, and a plain `update()` open discovery
with **zero audit rows**.
**The conformance test rule 9 demanded exists and passes — it tests the floor
the floor has, not the control the ADR specifies.** Root cause: the app role
holds the privileges the control withholds.

### CRITICAL 2 — verified by the CEO agent directly
`apps/accounts/services.py:259` enqueues `{"token_id": …, "token": raw, …}`.
`jobs.py` licenses that with "the row is deleted on completion". **Nothing in
the codebase deletes a Job row and `purge_expired` does not touch `jobs`** —
I checked both. So **every magic link ever issued persists in plaintext for
ever, failed jobs retain live tokens, and a nightly `pg_dump` is a file of
working sign-in links for named students.** Rule 9 broken in the credential
path, by a docstring nobody checked.

### The finding that invalidates part of this session's evidence
The autouse cache fixture gives ~99 tests undeclared database access — **and
pytest-django's blocker cannot block an already-connected PostgreSQL alias**,
because the flush fixture leaves one open. **So the isolation mechanism was
vacuous for the whole session and 99 tests were counted as coverage.**
Introduced by the fix for an earlier finding, and it would have presented as
"SQLite is broken."

### Scale, measured
3,778 lines of code, 71% of it comment prose, under **11,776 lines of
architecture markdown and 2,640 of decision log — 3.8 document lines per line
of code.**

### Accepted: the three ranked changes
1. **Move the gate and the audit log from a trigger to a privilege.** One
   migration revoking the privileges from the app role plus a second role for
   `open_discovery`. Closes both criticals at the root and **gives rule 14 its
   first genuinely independent second layer**, which trigger-plus-trigger
   never was.
2. **Stop persisting the raw token**, delete the job row on success, add
   `jobs` to the purge, scrub the payload before `last_error`, make the
   docstring true.
3. **One deploy, one backup, one restore with chain verification, one student
   journey end to end, and a ~15-line CI running both engines** — the only
   thing that would have caught the 99-test hole, and the one thing 835 tests
   structurally cannot tell you.

### Accepted: what to delete
The ten `test_finding_*` tests, which assert a gap **still exists** — one is
red right now *because it was fixed*, which trains the next reader to reopen
it. Review passes 2 and 3 as a standing gate, replaced by **one mandatory
adversarial execution pass**, which is what found everything. Rules 11 and 13
folded into 15 — **eighteen rules that are really twelve will be obeyed.**
The two review transcripts reduced to their findings tables. The 31 pinned
columns for tables that do not exist.
**Not touched:** rules 9, 10, 15, 17; `p14.py` as one importable definition;
the ceiling notes; the both-engines run.

### Survived scrutiny — do not touch
The audit chain (it tried hard to make id order diverge from chain order under
concurrency; `prev_hash UNIQUE` makes them equal by construction), the
contention/tamper split with its measured budget, the job runner's
compare-and-swap with lock timeout, single-use token enforcement by
conditional UPDATE, `has_visible_character`, the close-always asymmetry, **the
stack — no objection**, and multi-campus from day one.

### The method finding, adopted into rule 9 today
> "QA writes from specification without reading implementation" is sound and
> has a named blind spot: **it cannot test a seam, because a seam is not
> specified anywhere.**

Rule 9 now requires a conformance test to **assert the control at the boundary
the document claims, not the boundary the implementation chose.**

---

## D-042 — Four contract defects ruled; three were requirements that could not be satisfied
**Date:** 2026-10-22 · **Decider:** ceo-planning, recording cto rulings

**1 · `campus_verifications.method` ratified as `INSTITUTIONAL_EMAIL`.** The
schema CHECK and the running code always said so; **`EMAIL_DOMAIN` was never a
value**, so criterion 7h could only ever pass vacuously with the gate spelled
two ways across three documents and the code — rule 12 and rule 10 in one
defect. **Ratified reasoning, not incumbency: `INSTITUTIONAL_EMAIL` names the
thing verified rather than the mechanism used**, which is how its sibling
`STAFF_MANUAL` is named and which stays correct when a second method arrives
that still matches a domain. **CEO agent corrected the three design documents
directly** — spawning an agent for a find-and-replace is the ceremony Red Team
just flagged. Frontend's both-spellings tolerance is to be dropped: **a
tolerance that outlives its divergence is how the divergence returns.**

**2 · Criterion 7f narrowed to *another person's* domain, second limb kept.**
The rationale was entirely about a seller's domain on a listing, where it is
attribute disclosure dressed as a trust badge. **The accepted-domain list is
campus configuration — identical for every visitor, about nobody, already on
the institution's own website. There is no data subject.** As written, **the
primary journey could only work by violating a failable criterion.**

**The pattern, on its third appearance, and the fix is structural: a criterion
written from a rationale, without the rationale travelling with it, drifts
wider than the risk it was written for — and the widening is invisible because
the criterion still reads protective.** So 7f's narrowed form now carries its
rationale in the same place, and the CEO agent wrote that requirement into
`SYSTEM.md` rather than leaving it as advice.

**3 · The grievance page composes rather than stores, and the reasoning
generalises.** `RANKING` and `GRIEVANCE_PROCEDURE` added as notice kinds — but
the officer's contact details are **already columns on `legal_entities`**, and
versioning them would create **a second copy of a fact that changes without
the notice changing, and a stale grievance-officer contact is a direct
regulatory failure rather than a cosmetic one.** So: versioned prose from the
notice table, officer fields interpolated at render time. **That is the same
rule as 7f's second limb — the value arrives from the service, never baked
into stored text — and noticing they are the same rule is why the composition
is right rather than fussy.** Frontend's loud "not published yet" stays, and
not inventing an officer was correct.

**4 · The locale gate moves to middleware, and the finding is the placement
rather than the leak.** Frontend found a real leak and closed it in its own
page helper. But **a helper in `web/` covers only the pages that call it, and
`Accept-Language` also selects the locale for the JSON API**, whose handlers
never call it. So the gate was **closed on six pages and open on every JSON
endpoint, now and in every later slice.** `LocaleGateMiddleware` goes in after
`LocaleMiddleware`: ten lines, one place, every request. The required test is
the half a helper could never cover — Tamil yields English **on a page and on
an endpoint.**

**Third instance of a pattern now worth stating: a control enforced where it
was noticed covers only the paths that layer sees.** Frontend's placement was
local and its escalation was exactly what should have happened.

### The observation the CEO agent is acting on rather than promoting
All three document defects were **rule-12 shaped in a way rule 12 does not
quite catch** — rule 12 is about a *test* that passes vacuously; these were a
criterion that can only match a value that does not exist, a criterion broader
than its rationale, and a route whose storage kind was never allowed. **Same
failure, different artefact: a requirement that cannot be satisfied, or cannot
be violated, reads as a control and is not one.**

**All three were found by frontend trying to build against them, which is the
only way they surface.** The CTO declined to add a rule on three instances;
**the CEO agent will fold this into rule 12's wording rather than add a
nineteenth rule, because Red Team's finding stands: eighteen rules that are
really twelve will be obeyed, and nineteen will not.**

---

## D-043 — QA on S1: the deletion screen lies to the student
**Date:** 2026-10-22 · **Decider:** ceo-planning
**CEO-verified:** 3 consecutive runs with `--create-db`: `2 failed, 930
passed, 53 skipped, 2 xfailed` — identical each time

### The finding that matters most, and it is a product-honesty defect
**The point-of-no-return deletion screen says "Everything else goes now".
It is false.** QA ran a real erasure and enumerated the survivors: the `users`
row (campus, city, pseudonym, verification flags), `user_tombstones.email_hash`
— a salted email kept one year for ban evasion — `age_verification_events`,
and **six `audit_log` rows carrying the student's IP address and user agent.**

**Every retention is lawful; the sentence is not.** Reproduced directly. The
fix is the copy, not the retention: drop "Everything", and name the salted
hash with its purpose — a sentence a reasonable person accepts when told and
resents when discovered. Routed to frontend, which owns the correction now
that design-director is stood down.

This is the one irreversible action a student can take, and the claim sat on
the screen where they decide. No rule caught it; **a test written from the
specification against real behaviour did.**

### Two CEO corrections, on the same finding, in opposite directions
**1. The isolation leak is REAL and still open.** Backend concluded no test
had undeclared database access and I repeated that to the founder. QA found
the other half **by trying rather than reading**: a test with no marker and no
fixture executes `SELECT 1`. Backend was right that pytest-django patches
`ensure_connection` — I verified that — **but the blocker cannot close a
connection it did not open**, and two session-scoped autouse fixtures open one
at setup and never close it. Measured fix: close the connection at fixture
end. Routed.

**2. But the 0-to-14 variance was NOT the leak.** QA reported five runs on an
unchanged tree giving 0, 1, 4, 13, 14 failures. **I ran it three times with
`--create-db` and got an identical result every time.** So the spread was
dominated by QA's own second cause — a stale test database missing a table
from a recent migration — not by the connection leak. QA separated the two
causes honestly and said both produce the same signature; the measurement says
which one was doing the work. **The leak is a real defect that has not been
silently rewriting this session's results.**

### The privilege layer was verified structurally and by nothing behavioural
Because the harness re-grants everything for the session — for documented and
correct reasons — **every guard test exercised the trigger layer on a database
with one layer where production has two.** QA restored the production state
inside a single transaction and proved independence: escape granted so the
trigger permits, privilege revoked, refused with **42501**. That is the first
behavioural evidence that rule 14's second layer exists, and Red Team's
finding was exactly that the gate had one layer twice.

### Lists replaced by invariants, unprompted, three times
The locale parameter became *no page may claim a locale it does not serve*.
`NOT_PAGES` became a content-type invariant — **and it subsumed the whole
list, including the two endpoints it was written for**, so the list is gone
rather than shortened, with its own guard because a content-type skip is
silent. The route count became three invariants, the load-bearing one being
**no route serves campus-scoped data while the gate is closed** — which
extends to listings by adding one needle in S2 rather than eighteen routes.

**And the structural proof that frontend's claim holds as pages are added:**
`web/**` contains zero querysets, zero model imports and no HTTP clients, so a
view cannot reach a listing except through a service that begins with the gate
assertion.

### QA found a fourth defect in its own work
**Its accessibility harness was reaching four pages out of eleven** — seven
redirect without a session, and a non-200 counted as a skip. **Rule 12 inside
the harness itself, reported as coverage for a whole slice.** It signs in now
and asserts the property. Fourth time in six passes a defect was found in
something QA wrote, each caught by someone reading its output against theirs.
**The S0 accessibility result was weaker than it read.**

### F21 — an ownership gap that was the CEO agent's error
Eight adversarial probe files appeared in QA's tree, one broken, **because I
briefed Red Team without giving it a tree.** A broken file there presents as a
QA failure in QA's own report, which is what rule 6 exists to prevent. QA
reported rather than deleted them — correct. **Ruling: `tests/redteam/**`
added to the ownership table, owned by red-team, excluded from the default
run.**

**Closed and converted to regressions:** the UUID version check, three
declaration shapes the source grep missed, the response control's value and
contact-detail limbs, and rule 16's SQLSTATE half.

---

## D-044 — Append-only becomes a row predicate: there is nothing to impersonate
**Date:** 2026-10-22 · **Decider:** ceo-planning, recording cto

### The retention contradiction, resolved by refusing all three options offered
The CTO required a table to be **append-only** *and* to have a **finite
retention period**, which together are unsatisfiable. It owns the defect.
Backend put both tables in a purge skip list, tested the skip, and escalated —
**the right handling of a contract defect, and quietly picking one is how the
inventory would have become false.**

Why each obvious option fails: **retain indefinitely** breaches the rule that
retaining beyond the purpose without a basis is itself a breach — the one-year
floor is a minimum, not a licence. **Move the rows to a mutable table** is
worse: these are the two tables whose entire value is being evidence, and
removing tamper protection from the evidence to satisfy a retention job is the
wrong way round. **A privileged purge actor** is the right direction and the
wrong mechanism — it would put the key to deleting consent evidence in a
production path that runs **every night**, and it is already established that
no mechanism can make production refuse a session setting.

**Ruling: append-only becomes a predicate on the ROW, with no privileged
caller at all.** UPDATE only to set the purge date from NULL; DELETE only once
that date has passed; TRUNCATE never. The date is NULL for the life of the
account, **so a live consent or age record is undeletable by anyone, including
the expiry job.**

**Why this beats any actor rule, in the CTO's words: there is nothing to
impersonate.** The job holds no privilege an attacker lacks; **the row's own
retention state is the whole authorisation**, so an early delete fails
identically for the expiry job and for a compromised session. And it is less
new machinery than it sounds — an existing migration already uses this exact
trigger shape on both engines.

### The trigger-loss hazard now has a structural control
On SQLite any `ALTER TABLE` rebuilds the table and silently drops its
triggers; PostgreSQL's does not — **so one migration can leave a guard live on
one engine and gone on the other.** Four tables now, five more from S2. **A
behavioural test only catches it if someone wrote one for that table on that
engine**, so the control asserts the exact expected trigger set per table per
engine, failing by name. Otherwise it surfaces as a surprise red in an
unrelated assertion, **where the tempting fix is to skip the test.**

### The CTO found a wrong premise under one of its own correct conclusions
It had rejected a sentinel value partly because "it breaks the foreign key to
`users` that S1 adds" — **and S1 added no such key.** The conclusion stands on
its other leg. Recorded because **a conclusion propped up by a wrong premise
is one someone re-opens the moment they find the premise.**

### A rule I had written as a proxy would have blocked every later slice
"`bookhop/urls.py` is included once in S0 and never touched again" was a proxy
for the real invariant: **frontend never edits it and only ever edits its own
URL file; backend may add includes.** Also confirmed: an applied migration is
history, so **editing its text changes what a fresh migrate produces without
changing any deployed database — the two diverge and the grep is satisfied by
a lie.**

### Rule 12 rewritten rather than a nineteenth rule added
QA has found four defects in its own work across six passes, and the CTO's
observation is the useful one: **three were the same shape — a check that
could not fail.** QA keeps finding it because QA is the only agent whose job
is to ask *did this actually run*.

Rule 12 now covers four disguises: a test that passes vacuously; **a
requirement that cannot be satisfied or cannot be violated**; **a guard whose
fixture cannot produce the condition**; and **a measuring instrument that does
not assert it measured.** The last is the most consequential because
everything downstream trusts the instrument — **a harness that silently covers
a third of its target exists without being a control**, and any number it
produces must now be quoted with the count of subjects actually reached.

**No figure needs retracting** — nothing in the architecture ever quoted a
numeric accessibility result. The correction is to the standard, not to a
claim.

**F21 closed:** `tests/redteam/**` added, owned by red-team, excluded from the
default run, with one rule attached — **a probe is not a regression test.**
When a probe finds something real, the finding goes to the owning agent and
the regression is written in *that* agent's tree.

---

## D-045 — Five false claims, one cause: a journey's tense is future, a template's is now
**Date:** 2026-10-22 · **Decider:** ceo-planning, recording frontend-developer
**CEO-verified:** `1005 passed, 57 skipped, 2 xfailed, 1 failed` — the single
red is backend's isolation blocker

**I named three false claims. Frontend found five**, and diagnosed the class.

### The cause, and it explains every instance at once
**Three of the five were lifted from the journeys document, which describes
the FINISHED product and labels its own copy "behavioural intent".** A journey
is the right artefact for designing a product and **the wrong source for a
slice's copy, because its tense is future and a template's tense is now.**
The deck now records which slice a string becomes true in — the structural
fix, and it must extend as later slices lift copy from the same place.

**And all five were green under the banned-word test the entire time, because
not one contains a banned word.** The control worked perfectly on what it
checks — vocabulary — while the defect was in **commitment**.

### The two I missed
`help.scope` promised to reach the other student, re-list a book and look at a
listing — **three promises and one fact**, with the relay, listings and the
channel all in later slices. **Only the fact survives**, and it was the half
carrying the weight. And two FAQ answers — taking a listing down, stripping
photo metadata — are **approved, correct, unchanged deck strings that were
wrong on that page in this slice.** **The words were not the defect; the
placement was.**

### The deletion screen: the claim withdrawn in both directions
"Everything else goes now" is gone **with no replacement** — *"nothing else is
kept" would have been the same unfalsifiable claim mirrored, and wrong the
moment a ninth retention lands.* The card now asserts **only what it
enumerates**, four items added, led by the salted email hash with its
mechanism, period and purpose — **stated about accounts, never about the
reader, so it cannot read as an accusation.**

**Two judgements worth keeping.** The repeat-infringer table is **deliberately
not listed** despite surviving deletion, because naming it on every student's
screen reads as an accusation about a person. And it **refused to collapse the
list behind a disclosure widget** — the obvious next idea — because the
requirement is that the student learns this *before the button*, and a
collapsed disclosure means most never open it, **re-creating the defect with
the words technically present.** The reasoning is in the template so nobody
"improves" it later.

### CEO ruling on the one item it refused to decide alone
It flagged a trust sentence whose "this" has no referent on a page with no
book, and declined to invent a generically-scoped variant of a no-warranty
string without instruction. Correct instinct. **Ruling: answer the question
with a plain fact rather than minting a second no-warranty string** — which
sidesteps the scoping problem instead of solving it, and applies its own rule
from this pass: **prefer the absence to the softening.**

### The standing rule adopted into the deck
**When a string tells a student what *we* will do rather than what the product
does, it needs a mechanism behind it or it does not ship** — with three checks:
name the function that does it, and **if the answer is a slice number rather
than a file, the string waits**; a deck string is approved for a meaning, not
for a page; and prefer the absence to the softening, **because a hedged
promise is still a promise and is harder to test.**

`/help` ships, on frontend's reasoning: the footer link is on every page by
design, the alternative is a 404, **a true page is not improved by deleting
it**, and what must not ship is a page implying a channel — removed rather
than reworded. The page got shorter and truer: 3,028 bytes to 2,669.

---

## D-046 — QA passes S1. The erasure guarantee rests on a layer nobody specified
**Date:** 2026-10-22 · **Decider:** ceo-planning, recording test-qa v2.0
**Verified:** PostgreSQL `1 failed, 1005 passed, 57 skipped, 2 xfailed`;
SQLite `1 failed, 952 passed, 120 skipped, 1 xfailed`. The single red on each
is the isolation blocker, pre-existing and backend's.

### The erasure attack: yes-and-no, and the "no" is the finding
QA made the session scan match nothing **three ways** — a signing-key rotation
without fallback, a changed serialiser, and a cookie-backed session store
where there are no rows to scan at all. In two of those **a session row
survives carrying the erased student's user id, decodable again if the key or
serialiser returns.** Erasure reports success each time.

**And yet no live session results — because a second, independent layer
refuses a tombstoned user at request time.** QA proved it by planting a
brand-new session *after* erasure.

**That layer is the real guarantee. It is named in no document and was
asserted by no test.** It is also narrow: only tombstoned accounts, while
suspended ones are served. Routed to the CTO to specify, because a guarantee
that exists by accident of implementation is one a later refactor deletes
without noticing.

**Sound parts, measured:** the swallow is per-row rather than per-scan, the
scan does not over-delete an unattributable row, rotation-with-fallback is
handled, and erasure reaches every device.

### The rights question I am not letting pass
QA escalated that **§2.5 read literally refuses a suspended student their own
data rights.** Backend correctly wired the missing check — but if it gates
export and erasure as well as mutation, **we will have fixed an authorization
bypass by making an account we suspended unable to get its data out or delete
itself.** Those are statutory rights; suspension is our own moderation action,
not a forfeiture. **Correct in the diff, wrong in the product.** Routed: the
precondition must separate marketplace actions from self-service rights.

### A control passing while the hazard it guards is live
**On PostgreSQL the append-only *existence* control is satisfied by a
surviving sibling trigger while the audit table is freely updatable.** It
asserts a trigger exists, not that the table is immutable — so a partial
trigger loss reads green. **This is the control written to catch the SQLite
rebuild hazard, passing while that hazard is live on the other engine.** Fix:
assert the property, not the presence, keeping existence as the cheap first
layer.

### Both xfails confirmed honest
Under `--runxfail` each fails on its **first named** assertion — the gate
genuinely opens, the TRUNCATE genuinely succeeds. Neither reports the inverse
of the truth, which was the specific risk.

### No-DOB holds under independent attack
Verified across the HTML and JSON paths, both outcomes, the idempotency
replay, the session store, the job payload, the security log, the refusal page
and the export. **The staff-review note is refused with a message naming the
rule** — detection rather than the code-review item the specification settles
for, which is rule 18 satisfied properly.

### The gap QA calls most serious
**No student has completed a journey, and five of the seven erasure
assertions — including the one product called the most important of all — have
no subject until S4.** They are parametrised skips naming model and slice that
**turn red the day the model appears**, which is the right shape.

**Also unverified and stated:** the keyboard walkthrough and four WCAG
criteria, Tamil (gate correctly closed and asserted closed, **never reported
as verified**), performance percentiles, and the restore test.

### A process cost I own
Agents were editing application files while QA ran, and one mid-edit syntax
error produced seven spurious failures in a run it discarded. **That is my
sequencing, not theirs.** Its counter-observation is fair: two of its findings
were fixed within the hour, each citing its test by path.

---

## D-047 — A student journey has now been completed end to end, for the first time
**Date:** 2026-10-22 · **Decider:** ceo-planning (walked personally)

**The gap QA named as most serious is closed.** Landing page → sign in →
email delivered → magic link followed → age gate → consent ledger → account
page → deletion screen. Every step on a real server in a real browser.

### Two defects that only running it could find
1. **The app 500s on the first POST a user makes.** `no such table:
   rate_limit_counters` — the development database had not been migrated past
   `core/0007`, and **the dev server defaults to SQLite while all our verified
   runs were on PostgreSQL.** 1,017 passing tests did not catch it, because
   none of them runs the app the way a person does. This is the same stale-DB
   cause QA identified in the *test* database, present in the *dev* one.
2. **`HEAD /` returns 405**, and `/favicon.ico` 404s on every page load. Both
   minor; both invisible to the suite.

### What was verified working, in production conditions rather than in a test
- **The credential fix holds in the real flow.** The delivered job's payload
  reads `_redacted_keys` — the raw token is gone after send, exactly as
  specified. I could not retrieve a used token from the database even trying.
- **The magic-link email renders a real absolute URL** and **carries no name**
  — the enumeration protection frontend argued for, working.
- **The trust string renders correctly**: "Signed in with a college email
  address", gated on the verification method, on a student who actually signed
  in that way.
- **The age gate takes a date and keeps none** — the screen says so and the
  schema makes it true.
- **The consent page is granular and factual**, including
  *"BookHop stores it, and staff can read it if a problem is reported"* — an
  unflattering truth stated plainly rather than softened.

### The deletion screen, which is the one that had the false claim
It now enumerates **eight** retentions and asserts nothing beyond them. The
salted email hash reads: *"A scrambled code made from your email address,
kept for one year so that a banned account cannot sign up again. It is a code,
not an address."* And the age line: *"The date of birth you typed was never
kept."*

**That screen is the best argument in this project for the process that
produced it.** It is honest in a way nobody would have noticed was missing,
and it got there because a test written from the specification enumerated what
actually survived and compared it against what the page claimed.

### The standing lesson
**1,017 green tests did not tell us the first POST 500s.** Every rule in
`CLAUDE.md` is about claims and controls; none is about a person using the
product. Red Team said this in the engineering memo — *every defect the
apparatus caught was within-artefact* — and the first ten minutes of running
the app proved it again. **Running it is a different instrument, and it must
become part of a slice's definition of done rather than something done once.**

---

## D-048 — Running the app found two defects, and the fixes are better than the bugs
**Date:** 2026-10-22 · **Decider:** ceo-planning
**CEO-verified:** every web route answers `HEAD`; three API routes still refuse it

**`HEAD` fixed across ten read routes using Django's `require_safe`** rather
than spelling out the method pair — **so the two cannot be split by someone
later editing one of the names.** Frontend verified by **probing every route
in the resolver with both methods**, not by reading its own diff, **which is
how it found the same omission in three of backend's JSON routes.** I
confirmed independently: `/api/v1/account`, `/consents` and `/export` answer
`GET` with 401 and refuse `HEAD` with 405. Routed.

**The favicon fix is the declaration, not the route**, and that is the right
call: a browser rendering a BookHop page now never requests `/favicon.ico` at
all, **which removes the round trip rather than redirecting it.** The route
exists anyway for clients that ask regardless, as a permanent redirect with a
week's cache, so the cost is one round trip ever rather than one per
navigation.

**The accounting was shown rather than claimed:** +33 bytes per page against
one saved round trip per page — and on 3G a round trip is hundreds of
milliseconds while 33 bytes is not. **Inlining the icon as a data URI was
considered and rejected**, because base64 would cost ~700 bytes on *every*
page against one cached request, which loses for any repeat visitor. A
`ponytail:` note records the missing iOS icon with its ceiling and the
condition for adding it.

### The observation that matters more than either fix
Frontend's framing, which I am adopting: **both defects are the same shape as
the comment bug that made its first accessibility run red — a defect that only
exists when something real asks for something real.** One is a method nobody
sends in a test; the other is a request only a browser makes.

**Neither would ever have been caught by adding more tests of the kind we
already have.** That is now twice in two hours that running the application
beat testing it — the 500 on the first POST, and these two. The instrument
found two defects on its first walk.

**Standing change: walking a real journey in a real browser is part of a
slice's definition of done**, not a milestone to be celebrated once. Red
Team's verdict was that the apparatus catches defects inside artefacts and
misses them at the seams; a browser is the only instrument we have that works
at a seam.

---

## D-049 — The blocker was one line, and three of us reasoned our way to three wrong answers
**Date:** 2026-10-22 · **Decider:** ceo-planning
**CEO-verified:** the marker is at line 25; the test it contradicts is at line 377

### The diagnosis
`tests/contract/test_s0_surface.py` declares `pytestmark =
pytest.mark.django_db` at **module level**, which applies to every test in the
module — **including the one asserting that a test without the marker cannot
reach the database.** That test has database access *by its own file's
declaration*, so **its premise is false and it cannot pass.**

Backend's decisive measurement: it copied the test body **verbatim** into a
module with no marker and ran both in one invocation — `1 failed, 1 passed`.
**Identical code, one line of difference.**

### Three claims about the mechanism were wrong. Two were mine.
1. *"The blocker cannot block an already-connected alias."* **False** — it
   patches `ensure_connection`, which every query calls regardless. **I passed
   this to the founder as fact.**
2. *"The session fixtures leave a connection open and closing it is the fix."*
   **Half right** — they did, they now close it, and that is correct hygiene,
   but **closing changed nothing about blocking.**
3. *"The cause is in session setup."* **No** — session setup is identical for a
   contained and an uncontained test. **That narrowing was mine too, and I
   reported it as having gone further than QA did.**

**Backend pinned the measurement as a test so the next reader measures instead
of reasoning**, which is the correct response to three agents reasoning their
way to three different wrong answers about one line.

**The variance story is now fully closed: zero spread across five runs on each
engine**, identical counts and identical single failure. It was the stale test
database, and nothing else. Verdict delta from the entire isolation episode:
**zero**, measured two independent ways.

### What else closed
- **B3** — `require_actor` wired through one function on every write. It
  gained a named-check argument **because §2.5's order deadlocks on the two
  endpoints that satisfy it**: the age endpoint cannot require age, the
  consent endpoint cannot require consent, or no student ever reaches ACTIVE.
  **Narrowing by named check is the honest way to say that; skipping the call
  is how the bypass looked reasonable.**
- **B4** — the Tamil gate was **three copies of one rule**: the middleware,
  the notices handler re-deriving from the raw header, and the consents
  handler using the stored preference. Now one definition with the others as
  readers, and **a test that fails on any app file deciding for itself what
  `ta` means.** The fixture that could not produce the condition now can, and
  the tests assert **the body served** rather than a locale field.
- **A-1** — backend states plainly that **its implementation drifted from the
  CTO's specification**: the spec said the exact trigger set failing by name,
  it wrote an at-least-one existence check. Now three layers, and **the one
  that holds is the property measured** — a trigger whose body is replaced
  with `RETURN NEW` passes the first two and fails the third.
- **The xfail tripwires now work**, and the assertion no implementation could
  satisfy is dropped.
- **The startup check refuses a half-migrated database**, deliberately **not**
  tagged as a database check, because `runserver` skips those — which would
  have made it absent from exactly the situation it was written for.
- **HEAD derived once from the declared methods**, and the route probe asserts
  HEAD and GET agree on **status** — because a route answering 401 on GET and
  200 on HEAD would be a bypass nobody would look for.

### Backend kept the SQLite default, with a reason I accept
The defect was **unapplied migrations, not the engine**, and the startup check
closes that on either database. Flipping the default mid-slice would re-point
three agents' plain `pytest` at PostgreSQL and a shared test database — the
collision it had just worked around.

### The thing it most wants checked, routed away from it
**`_may_write`'s narrowed precondition lists.** Its own framing: it chose
those lists by reasoning about the contract and wrote its tests from the same
reasoning, so **a list one entry too short grants a write to an actor who
should not have it, and every test it wrote would still pass.** That is the
shape of the bypass this fix closes. Routed to code review — **an agent cannot
independently check a list it derived and then tested from the same
derivation.**

---

## D-050 — The check backend could not do on itself found a real divergence
**Date:** 2026-10-22 · **Decider:** ceo-planning
**CEO-verified:** API-CONTRACT §2.5 line 176 lists `POST /account/nominee`
(s14) in the Stack S row

### F23, and why only an outside derivation could find it
Backend asked for its narrowed precondition lists to be checked by someone
else, on the grounds that it derived them by reasoning and wrote its tests
from the same reasoning. **It was right, and the finding is exactly that
shape.**

**The nomination endpoint is Stack S in the contract and Stack M in the
code.** A suspended, under-age-verified, campus-unverified or unconsented
student is refused a statutory nomination, with four different refusal codes.

**QA found it by deriving endpoint membership from the contract's table.
Backend's tests enumerate the code's stacks, so they agree with the code by
construction.** The lists *within* each stack are correct; the assignment of
one endpoint to a stack is not.

**And backend had already "corrected" itself in the wrong direction**, moving
nomination from S to M by reading the ruling's prose summary — which named
five examples — rather than the normative table, which lists it. Its instinct
was sound: *"extending a list of exemptions by resemblance is how a stack
stops meaning anything."* The resemblance argument was simply never needed.
**It raised the question rather than re-deciding, which is why this cost one
word instead of a slice.**

Ruling: the code follows the table. If nomination belongs in M, that is a
contract amendment, not a code decision.

### What passed, each a plausible place to fail
The profile endpoint is split **by field** — locale under S, display name
under M — and a body containing both correctly takes the stricter stack, **so
a suspended student cannot rename themselves by sending a locale alongside.**
That is the placement most likely to have been done as "whichever stack the
endpoint is in". A tombstoned actor gets **401 rather than 403**. And a fresh
student walks age then consent unrefused — the **one-entry-too-long**
direction, which no enumeration of lists can catch, because the lists would
agree with each other.

41 of 45 cells pass; the 4 failures are one cause.

### QA recorded two mistakes of its own, and the second is the reusable warning
Its first draft reported four extra findings, **all of them its own**: it
treated an endpoint as single-stack when the code splits it by *direction*,
and it **reused one test client across actors — so every actor after the first
was anonymous and every endpoint answered 401.** Its phrase: **four cells of
confident, uniform nonsense that looked exactly like a finding.**

**For whoever extends this matrix at S2 and S4: a precondition matrix with a
shared session fixture produces results indistinguishable from a bypass.**

### F19 withdrawn by its author
QA withdrew its own isolation finding, agreed the marker diagnosis, and moved
its blocker test to a module declaring no marker — **with two guards: one
asserting the module never acquires a module-level marker**, because the
defect was invisible by construction and a marker added later would make the
test pass for the wrong reason; and a positive control so the two cannot both
be green for an unrelated reason. **Verdict delta from the whole episode:
zero, now agreed from both sides.**

**F21 has resolved itself** — the stray probe files are gone; only QA's own
helper remains. **F20 and F18 stay open and non-blocking.**

---

## D-051 — S1 green on both engines, zero spread. Committed 2540d0e
**Date:** 2026-10-22 · **Decider:** ceo-planning
**CEO-verified:** PostgreSQL `1144 passed, 57 skipped, 2 xfailed` twice
identical; SQLite `1079 passed, 123 skipped, 1 xfailed`. Zero failures.

### Backend closed the nominee finding by building QA's method into its own tree
It rewrote the comment that had recorded the correction in the wrong
direction — **which would have misled the next reader harder than no comment
at all** — and then wrote a test that **parses §2.5's Stack table out of the
markdown** and asserts each listed endpoint calls the Stack S gate, with a
vacuity guard on the parser.

Its own statement of the lesson, which is the durable part: **"A test written
from the implementation cannot discover that the implementation read the wrong
document."** Its tests had agreed with the code through **both** wrong
placements — the original inference and the over-correction.

**Fixing it surfaced a second defect:** `inspect.getsource` on a decorated
handler returned the **decorator's wrapper**, so a body-reading test had been
comparing the decorator against itself for every endpoint.

### Reading the table properly found two more things it had not done
**Logout had no gate at all** — and refusing it would leave a suspended
student holding a live session they cannot end, **the opposite of every reason
suspension exists.** And the suspended response said only "no", which the
contract calls *the failure this amendment exists to prevent*; it now names
the four open doors, **derived from stack membership rather than retyped, so a
route moving between stacks cannot leave the sentence describing the old
one** — and asserted end to end, because a message living in a constant and
never reaching a response is the exact shape the missing authorization check
had.

### Both splits are data, not branches
Profile by field, consent by direction — **because an authorization decision
behind a boolean is the shape this slice has been bitten by twice.** And the
reading of "as easy as granting" is mechanism parity, not shared
authorization: **the other reading would make the easier direction the one
that unlocks things.**

### Two defects in backend's own code that QA's matrix found
An age guard that **conflated "already declared" with "not new"**, so a
student who reached active status by another route could **never become
adult-verified at all**. And an invalid enum reaching the database as a 500 —
rule 18, the constraint guaranteeing the stored state while nothing detected
the bad input.

### The forward-looking item, acted on now rather than in four slices
**Three ruled placements cannot be implemented yet** — safety reports, ticket
reply versus ticket open, and display name — because their tables are S5 and
S6. Backend's framing: *by S5 the comment will be four slices old and the
person implementing it will be reading the table, not the reasoning. That is
the same gap that produced the nominee error, one slice later and with a
safety report on the other end of it.*

**Routed to QA to pre-register as parametrised skips derived from the contract
table, which turn red the day the model appears** — the pattern it already
uses for the erasure assertions, and the one shape that survives four slices
of forgetting.

**Still open and non-blocking:** the privilege layer is necessary and not
sufficient (needs a superuser), the append-only-versus-retention contradiction
awaits its migration, and nothing is deployed, no backup restored, no CI.

---

## D-052 — A right cited as satisfied has no endpoint; the guard found it on day one
**Date:** 2026-10-22 · **Decider:** ceo-planning, recording test-qa
**Suite:** `2 failed, 1147 passed, 65 skipped, 2 xfailed`, identical twice.
**Both failures are the new finding and should stay red.**

### F24 — rule 9 one level up
**`POST /account/correction` is named twice in §2.5 and does not exist.** The
Stack S table lists it. And §2.5 then uses it a second time as **the
justification for putting `display_name` in Stack M** — *"the right is
satisfied by `POST /account/correction`, which is in S, staff-reviewed and
logged."* No route, no handler, no slice.

So a suspended student cannot change their display name — **correctly** — and
**cannot use the correction route either, so that right has no path at all.**
**A document naming a control as the reason another control is acceptable,
with nothing asserting the first exists.** The restriction is right; its
justification is unbuilt. Routed to the CTO for a slice, with the standing
instruction that **§2.5's display-name reasoning must not be quoted as
satisfied until the endpoint exists**, including in a go/no-go packet.

### The forward-dated assertions, and the guard that makes them honest
Seven rows, each skipping while its app is absent — **naming app, slice, and
the contract's own words for why, because the why is what decides the next
ambiguous case** — and running the day the route is mounted.

**Both sides of every split are rows, and a test enforces that**, because the
reports endpoint splits by **category** — the same field-dependent shape that
already went wrong once, and **checking one side only is the nominee error
again.**

**The failure mode QA named and guarded:** a forward-dated skip can skip
**forever** — the endpoint ships at an unpredicted path, nothing runs, it
ships in the wrong stack, and the guard was **theatre with a four-slice
fuse.** So it inverted the test: once the owning app is installed, a ruled
path that does not resolve is a **failure**.

**That guard earned itself immediately by catching a bug in QA's own helper:**
`resolve()` matches everything, because the web urlconf ends in a catch-all
for the 404 page — so **every assertion in the file would have passed
vacuously the moment its app was installed.**

### Two preconditions forward-dated for the same reason
Scope-to-404 and gate-to-403, which S1 cannot exercise at all since every S1
endpoint concerns the caller's own account. QA's reason for choosing those
two: **the most likely to be forgotten by the first endpoint that needs them,
and the two with the largest consequences — one leaks the catalogue, one is
the gate.** The placeholder **fails rather than skips** once the listings app
exists, **with a test asserting that failure branch still exists so nobody
converts it into a permanent skip.**

### Closed and noted
**F21 has resolved itself** — the stray probe files are gone; only QA's own
helper remains, now tracked. Code review asked to keep probes out of QA's
tree, with its own row available for adversarial work. F23 closed, with
backend's contract-parsing control now a permanent fixture in its tree —
which QA judged **strictly better than its own version**, since it makes
derivation-from-contract a control rather than something done once.

**Still open and non-blocking:** the stale-test-database phantom failures, the
privilege layer re-granted session-wide so the suite's default state is the
weaker of the two layers, and §5.1's `needs` listing a campus step that cannot
occur.

---

## D-053 — The correction endpoint gets S2; deleting a dead value found a live gap
**Date:** 2026-10-22 · **Decider:** ceo-planning, recording cto

### F24 — the gap closed in the right direction
**The CTO did not close it by moving `display_name` to Stack S**, which would
have traded a missing endpoint for **a live evasion vector — changing the name
counterparties recognise after a safety report.** Its framing: **the placement
is right, its justification is unbuilt, and those need different fixes.**

Scheduled to S2 **on the merits rather than for convenience: a display name is
visible to nobody but its owner until listings exist, so the restriction only
starts costing a student anything in S2 — which is exactly when its
justification has to be real.**

One design note worth keeping: the correction request is **free text, not an
enum of correctable fields**, because **an enum there would be a list where a
judgement belongs.**

**And the quoting prohibition is written into the contract itself rather than
left to memory:** until the conformance test is green, the display-name
reasoning may not be quoted as satisfied in a packet, an ADR or a report.
QA's two red tests are marked **must-not-skip**.

### F22 — deleting a dead value exposed something better than the finding
The unreachable precondition is gone: a magic link is never sent to an
unrecognised domain, **so consuming one proves the domain matched — the magic
link *is* the campus evidence.**

**The gap underneath it is the real result: a campus with empty
`email_domains` has no student sign-in path at all.** The data model says such
a campus means no self-service signup, with users staff-created — **but
`request_magic_link` refuses their address too, so a staff-created user cannot
sign in either.** The unreachable value was the only thing in the contract
that looked like it addressed this.

**Recorded, not fixed** — v1 is one campus with a working domain, and the
trigger for reopening it is already named. **The point of writing it down is
that the next person reading the staff-created path will otherwise assume a
sign-in path exists for it.**

### A fifth disguise added to rule 12, because it is one the rule did not reach
Rule 12 covered a check that passes vacuously **now**. QA's pattern exposed a
check that **has not started**, where *"not yet running"* and *"running and
passing trivially"* are **indistinguishable from outside** — so a forward-dated
skip can skip forever, **reading as coverage for the entire window in which the
decision it encodes gets forgotten.**

Adopted: **once the owning app exists, a ruled path that does not resolve is a
failure, not a skip**, with a further test asserting that failure branch still
exists.

**And it earned itself on its first run by catching its own author's bug** — a
path check that matched everything because the URL config ends in a catch-all,
**which would have made every assertion in that file pass vacuously the moment
its app was installed.** The CTO's observation, which I have put in the rule
rather than the citation: **a guard-for-a-guard whose first catch is its own
is the strongest evidence the construction is right.**

Two rules promoted alongside it: **where a rule splits a set, both sides are
rows and a test enforces it** — checking only the permitted side passes, and
is how a wrong placement survives review. And **a guard for a guard is worth
writing when the guard is forward-dated or silent.**

### What carries into S2, with justifications already written
The two-stack split, the correction endpoint, and a behavioural partner for
every existing structural assertion. **The CTO's observation on the first two:
they are the same defect seen from opposite ends — one was authorization
applied too widely, the other a right with no route — and both were found by
someone trying to build against the contract rather than by reading it.**

---

## D-054 — The guard against the bypass was itself vacuous, and already hiding a mismatch
**Date:** 2026-10-22 · **Decider:** ceo-planning, recording code-review
**Verified by review:** ten runs on `2540d0e`, **zero spread** — PostgreSQL
1144 five times identical, SQLite 1079 five times identical.

### B7 — three characters, and what they guard
`assert expected in body or expected in source`, where `source` is the whole
module — **so every expected token is present by definition and the
per-handler check can never fail.** CEO-verified: the map says one gate for
the age endpoint while the code calls the other. **The guard built to stop the
authorization bypass recurring is silent, and is already silent about a live
mismatch.**

### The contract parser is sound; its enumeration is the same defect one level up
The regex is correct, it fails loudly on a reformat, and the vacuity guard is
real. **But the membership assertion is parametrized over a four-element
literal typed into the test file** — validating four names the author chose
rather than enumerating the table. **A fifth Stack S endpoint goes unnoticed,
which is exactly the failure the file exists to prevent.**

### A rebuke I am recording against myself
Review marked four items **Required** in round one; they are neither fixed nor
recorded as carried. Its words, passed on undiluted: ***"Required" means in
this slice, and four of them quietly becoming notes is how a Required list
stops being read.***

That is an integrator failure, not a developer one. Two of the four matter on
their own terms: **the session table has no retention row, no retention rule
and no purge path**, and **the jobs purge selects only on completion
timestamps, so a never-claimed row is never redacted — making the "second
layer" comment in backend's own file false for exactly that row.**

### R13 — the two reds become strict xfail
The findings are right and the mechanism is wrong. **A permanently-failing
suite means every run carries known failures, and the only way to tell a new
one is to read the names** — which is how a real failure gets waved through,
and this project has already paid for failures landing on tests that did not
cause them. **Strict xfail is green while the gap is open and red the day it
closes**, which is the semantics wanted.

### The asymmetric assertion, sharpened
**For Stack S the claim is about the gate — any non-gate response proves the
actor got through. For Stack M it is about the outcome, where only the stated
code proves the stated reason.** But the exclusion also accepted 405 (never
routed), 5xx (**masking a crash inside the gate itself**) and 429 — **which
contradicts the file's own cited reasoning that no safety path is rate-limited
to zero.**

### Three agents carried one wrong mechanism
Review withdrew its B1 cause — *the blocker cannot block an already-connected
alias* — which it had taken from QA and I had taken from both. **False.** Its
disposition is the right one: the observation was correct, the cause was the
stale test database, and **the fix is better than either, because the question
now lives in a module that can honestly ask it, with a guard on the guard.**

### A class this project had not named
Review on the correction-endpoint finding: **a control that is load-bearing
for a second control's acceptability.** Rule 9 at one remove. Already
scheduled.

**Re-review is B7 plus the R13 decision: one pass, five runs per engine, and
review expects to approve.** S1 still has **no WCAG 2.2 AA pass** — the
keyboard walkthrough and the performance percentile skip with a stated reason.

---

## D-055 — A mark must be as narrow as the gap it marks
**Date:** 2026-10-22 · **Decider:** ceo-planning
**CEO-verified:** PostgreSQL `1173 passed, 65 skipped, 3 xfailed`; SQLite
`1109 passed, 131 skipped, 2 xfailed`. Zero failures on either.

### B7 closed, verified line by line
The vacuous `or` is gone, the map entry is corrected to the gate the code
actually calls, and **the contract-table membership is now extracted into a
set rather than parametrized over a typed literal** — so a fifth endpoint
added to the contract is no longer invisible.

### The design point that generalises past this file
Converting the two reds to strict xfail, QA did **not** xfail the inversion
guard itself. It **excludes rows with an open finding instead** — because had
the known gap stayed inside the guard, **the whole guard would be an expected
failure, and a second row going unreachable later would be absorbed into it.**

Its framing, adopted: **a known failure buying silence for the next one is the
exact thing the conversion was meant to prevent.** The general rule — **any
time a known gap is marked, the mark must be as narrow as the gap, or it
becomes a blanket.** Routed to review to confirm, because it is the part most
likely to be copied without its reasoning.

### A caveat that expired between being written and being read
Review warned that the decorator's closure made every handler report the same
module, so tightening a check would break every row. **Measured: false** — the
`functools.wraps` that fixed the `getsource` defect also copies `__module__`,
so **one change retired two caveats.** True when review read the code, false
by the time it arrived.

**QA declined to tighten the check anyway, for a better reason than the
caveat**: `apps.*` is exactly the question being asked, and tightening adds a
second thing to keep in step per row for no extra discrimination. It pinned
which fact is current, so **one test now guards both.**

### The assertion, as four assertions
Each with its own message, so a cell reports which family it hit: refusal,
never-reached-the-gate, **a crash masked as a pass**, or rate-limited. QA's
note on the last: it was **its own cited reasoning arguing against its own
assertion**, since the safety row quotes the rule that no safety path is
rate-limited to zero.

### F21 closed by measurement
**There are no probe files in QA's tree.** I listed it: ten files, every one
QA's own, all tracked. Transient during earlier passes; review's probes were
never there. **QA can drop the ignore-glob its numbers have been carrying.**

### The sentence this round is worth remembering for
Three agents carried the wrong blocker mechanism, and **what settled it was
not better reasoning but running the same test body twice with one line
different.** QA counts **five instances this round where measuring beat
reasoning** — which is the argument for pinning mechanism **tests** rather
than mechanism **explanations**, and is now how this project resolves a
disputed cause.

**Carried and not fixed:** four Required items with backend, recorded as my
failure in D-054. **S1 still has no WCAG 2.2 AA pass.** Final review pass
running.

---

## D-056 — The deletion test's independence is lost; recorded, not papered over
**Date:** 2026-10-22 · **Decider:** ceo-planning
**Suite:** PostgreSQL `1178 passed, 65 skipped, 3 xfailed` twice identical;
SQLite `1113 passed, 131 skipped, 2 xfailed`. Zero failures.

### CEO correction — I inferred authorship from a directory listing
Closing F21 I told QA all ten files in its tree were its own. **Five are not.**
I read a listing, saw tracked files, and inferred who wrote them — **which a
listing cannot tell you.** The same move I have spent the day correcting in
others, made while closing a finding about that exact tree. F21 remains
correctly closed; the claim attached to it was wrong.

### The finding underneath it
**DATA-MODEL §10.3 assigns the deletion end-to-end test to test-qa "and
written independently". The implementer wrote it.** QA read it rather than
objecting: the content is sound, the properties that need later tables are
**skipped rather than silently absent**, and **no rework is needed.**
**What is lost is independence, not coverage.**

**Ruling: recorded as not met; not rewritten today.** Changing the author of a
sound test buys nothing now, and the deferred properties land in S4 — at which
point that file is written properly, by QA, from the specification, **and the
independence arrives with the coverage rather than as a separate exercise.**
Carried to S4 with its reason and **named explicitly in the go/no-go packet**,
because QA's framing is right: **the agent that wrote the deletion code wrote
the test that says deletion works, and that is the assertion a regulator would
read.**

QA has been invited to argue the ruling down — **better to be argued out of a
convenient decision than to discover later that the agent whose charter owns
the property disagreed quietly.**

### Why instrumenting the stale database was worth more than fixing it
**A stale database does not fail where it is stale.** Teardown flushes a table
it lacks, leaves rows committed, and the failures surface on whichever test
next reads global state — **which in this schema is always the audit chain,
because it is one linked list across the whole table.** Three checks now fail
by name with the fix in the message. **One named failure replaces a scatter of
unrelated ones.**

### Two formulations adopted verbatim
**On marks:** *a mark that is wider than the gap it marks is a blanket, and a
blanket absorbs the next failure.* With the reason the wrong version is
tempting — **the wide mark reads as "we know about this" while the narrow one
reads as special-casing, and the narrow one is right precisely because the
guard's value is in what it catches next.** The parametrised case is the trap:
marking the function rather than the row.

**On disputes:** when an explanation and a measurement disagree, **the
explanation is the thing to delete, even when it is in a document whose job is
to explain.** Five disputes this round were settled by measurement over
reasoning — the blocker mechanism, the boolean probe, the escaping, the
privilege state, the module attribution.

---

## D-057 — All four Required items closed; the second layer had the same hole as the first
**Date:** 2026-10-22 · **Decider:** ceo-planning
**CEO-verified:** PostgreSQL `1178 passed, 65 skipped, 3 xfailed`; SQLite
`1113 passed, 131 skipped, 2 xfailed`. Zero failures. Backend ran five each.

### B7 was worse than three characters, and backend checked the contract rather than my word
I told it the map was wrong and the code right. **It verified against §2.5
instead of taking that** — the age endpoint does not appear in the Stack S
row, and the M row is "everything else" — and reached the same conclusion
from the source. Each handler's **own body** is now read with no module-wide
fallback, plus two guards the map never had: one failing if a routed handler
has no entry, and one proving the predicate **can** reject a wrong gate, which
is what the `or` made impossible.

### Turning on the real enumeration found three things immediately
Two Stack S entries the four-element literal had never covered — the profile
endpoint qualified *"for locale only"*, and the consent toggle, which reaches
Stack S **through the direction map rather than by calling the gate**, so it
is asserted as a property rather than a token, **since a token match would
pass on a handler that merely mentioned the gate.**

And a latent defect: the extractor's regex held **a literal backspace byte
where a word boundary was intended**, so it returned zero tokens on its first
run. **The count floor caught it** — the guard-for-the-guard working again.

### R5 is the one that mattered, and it is the critical we thought we had closed
A job **never claimed at all** had neither timestamp, was never redacted on
finish, and was never purged. **So the one row the first layer provably missed
was the one row the second layer also missed — and the comment called it the
second layer.** For the sign-in job that is **a live token retained
indefinitely.**

The new branch is deliberately narrow, because a broader rule **would delete
the retention job's own reschedule and stop retention permanently** — with a
test for exactly that. **A purge that stops purging is a worse bug than the
one being fixed.**

### R9 — the fix for one rule introduced an instance of another
Six document references in rendered copy, **and the seventh arrived from
backend's own rule-18 enum validator while it was fixing the six.** Citations
moved to a logged field rather than deleted, **with both halves asserted so
the fix cannot be satisfied by removing the diagnosis.** The guard is an AST
walk, **because a grep cannot tell a message from the docstring above it.**

### R4 closed except the piece backend does not own
Sessions now purge and log. It also **compounds**: erasure scans that table,
so every un-purged row made erasure slower. **The inventory row is
compliance's file and I am carrying it.**

### Backend's own diagnosis of the round, in its words
**"You read the prose and QA read the table."** That single sentence explains
both the nominee error and the correction-endpoint gap, and it is why the
contract-parsing test matters more than the fix that prompted it.

**Its standing concern is already answered** — QA's forward-dated placements
cover all three judgement calls, with both sides of every split as rows and an
inversion guard that turns a skip into a failure the day the app exists.
Backend could not have known; told.

---

## D-058 — QA converted my ruling's evidence before accepting it
**Date:** 2026-10-22 · **Decider:** ceo-planning
**Suite:** PostgreSQL `1183 passed, 65 skipped, 3 xfailed`; SQLite
`1118 passed, 131 skipped, 2 xfailed`. Zero failures.

### It agreed with the ruling and refused the evidence I had used for it
I deferred a compliance property partly on QA's statement that the test's
content is sound. **QA pointed out that this was a *reading*, and that the
risk independence addresses is not sloppiness but a shared blind spot** — **a
test written from the implementation inherits the implementation's
misconceptions, and reading it tells you it is internally coherent, not that
it is right.** So I was about to defer a compliance property on a sentence
carrying the same weakness the property is about.

**It converted the reading into a measurement before answering.** Five
derivations straight from the specification, choosing the two places
implementer and test are likeliest to share an assumption:

- **The "untouched" list**, because **that is the direction a deletion feature
  gets wrong — every instinct in "delete my account" pulls towards deleting
  more, and what must survive is precisely the record that the deletion was
  lawful.**
- **The salt's location**, because the re-identification claim rests on a
  secret *not stored in the database* — **a deployment property, not a code
  one, and exactly what a test written beside the code assumes, since from
  inside the process the secret is simply there.** Checked the way an attacker
  with a dump would.

Plus the identity-gone/pseudonym-unchanged pair, the second erasure layer
tested against **a brand-new session planted after erasure** so the first
layer cannot be what refuses it, and the warning that layer must refuse
tombstoned accounts only and never suspended ones. **Five derivations, five
agreements.**

**Ruling stands, and now rests on a measurement rather than a reading.**
QA's reason for not asking for the rewrite is better than cost: the deferred
assertions gain their subjects in S4, the file is rewritten then regardless,
and **independence arriving with the coverage is worth more than independence
arriving on its own.** Its condition, adopted: **independence deferred is not
independence waived** — recorded, carried, named in the packet, **and the five
derivations are what make the carry defensible rather than merely
convenient.**

### A second CEO finding: my commit practice destroyed the evidence QA suggested
QA offered the cheap authorship check and noted it had not run it either. **I
ran it. It cannot work here: all four files report the same commit — mine —
because I commit every agent's work in one bulk commit.** So git attributes
authorship to the integrator, not the author.

**Our own commit practice erases per-agent authorship**, which is the
provenance the independence property depends on. **Standing change from S2:
each agent's work is committed separately so authorship survives in history.**

### Two formulations kept
**On why a listing misleads:** *a file listing tells you what exists and never
who wrote it — and the more the filenames match expectations, the more
confidently it will be misread.* My inference was locally reasonable, which is
what made it plausible.

**On narrow marks:** **the narrow mark is also the harder one to write,
because you must decide precisely what the gap is before you can scope a mark
to it. The wide mark lets you skip that decision, which is most of why it is
tempting.** Scoping it is what forced the realisation that the gap was one row
and not one test — **and that distinction is what kept the guard able to catch
the next row.**

---

## D-059 — S1 APPROVED AND COMPLETE. Committed 5799170
**Date:** 2026-10-22 · **Decider:** ceo-planning
**CEO-verified on the commit, clean tree:** PostgreSQL `1183 passed, 65
skipped, 3 xfailed`; SQLite `1118 passed, 131 skipped, 2 xfailed`. Zero
failures.

**Code review: APPROVED. QA: PASS.** Both gates, per rule 5.

### What review checked last, because the approval turned on it
**A just-un-vacuumed guard can pass for a *new* wrong reason.** It measured
per handler that the real token is present **and a bogus token absent** for
all eight gated handlers — so the guard against the authorization bypass is
**live rather than merely no longer vacuous.** The same run confirmed the old
`or` would have rescued all eight.

### The principle extracted from the mark decision, stated so it copies
**`xfail` belongs on an assertion with one subject.** An aggregate assertion
has one outcome for N subjects, so marking the aggregate makes the
expected-failure state satisfiable by **any** subject: a second unreachable
row keeps it xfailing, strictness never fires because it never xpasses, and
**the known failure buys silence for the new one** — and the day the known gap
is fixed the tripwire still does not fire if the new one is present.

**Where a guard asserts over a set, express the expected failure by removing
the known subject, never by marking the aggregate.** QA's version is safe
rather than merely convenient because the exclusion **both** removes the row
**and** attaches its own per-row strict xfail: one gap, two live tripwires.

### Nothing was weakened
Four modified test files, **no deleted assertion, test, skip or xfail line
anywhere.** The charter metric is at zero for this slice.

### Review's one real complaint, and it is mine
**Four consecutive rounds measured a tree that was moving underneath them** —
unexplained numbers, assertion-free files counted as coverage, a mid-review
edit that made a suite red after it was reported green. Its judgement: **the
work is good; the commit discipline around it is the weakest thing left**, and
**a review and a QA pass are both statements about an artefact, which mean
nothing against a tree being edited while it is measured.**

**Adopted from S2: the tree freezes when a slice goes to review** — no agent
edits until the verdict returns — **and each agent's work commits separately**,
since bulk commits have been erasing the authorship that D-058's independence
property depends on.

### A schema gap caught before S2 rather than during it
**The correction endpoint is not implementable as the schema stands:** there
is no column for *what* the student wants corrected, only a payload belonging
to a different right. Backend's reason for flagging early is the one to keep:
**the obvious workaround is to reuse that column, and a column holding two
unrelated things is how the next contract divergence starts.** Same failure as
the wrong stack placement, in the schema rather than the prose.

### A project-instruction edit that should not pass by silence
`CLAUDE.md` gained ~20 lines this slice. Review has no objection on substance
but correctly refused to wave it through: **a project-instruction edit riding
in on a slice commit is the founder's and the CTO's to ratify, not a
reviewer's.** I wrote them and should not also ratify them. Routed — with the
standing counter-argument that **eighteen rules which are really twelve will
be obeyed and nineteen will not**, and I have been adding rather than
consolidating.

### Standing gaps, each with a tripwire
**No WCAG 2.2 AA pass** — a structural sweep exists; the keyboard walkthrough
and the performance percentile skip with stated reasons. **Two live criticals**
awaiting an ownership migration that needs a superuser. **The correction
endpoint absent**, so a suspended student has no correction path at all.
**The deletion test's independence deferred to S4**, against five independent
derivations. **Nothing deployed, no backup restored, no CI.**

---

## D-060 — Rules consolidated 18 → 13 by root cause; rule 9 corrected
**Date:** 2026-10-22 · **Decider:** ceo-planning, on cto ratification

### The correction that mattered: rule 9 endorsed the defect it was meant to catch
As written, rule 9 required a test asserting a named control **exists**. QA
found **a trigger-existence check passing while the table it guarded was
freely updatable**, because a surviving sibling satisfied it. **So the rule's
literal text was satisfied by the exact test that failed.**

Corrected: a conformance test asserts **both that the control exists and that
its property holds.** **Existence diagnoses — it fails by name, so you know
which guard went missing. Behaviour guarantees.** Ship both, never only the
first.

**Two smaller defects fixed:** the old rule 12 said *"four disguises"* and
listed five, then referred to *"all five"* nine lines later — **a rule set
that miscounts its own list is poorly placed to enforce the rule about
lists** — and a hard count that would go stale next slice is now
"repeatedly".

### Consolidation by cause, not by compression
Rules 1–8 are governance and founder-facing; untouched. **The ten engineering
rules were five root causes written twice:**

- **A document's claim is not evidence** (was 9 + 17)
- **A passing check is not evidence** (was 12 + 16 — the refusal-on-the-wrong-
  signal case is the same family, now its sixth disguise)
- **One definition, not many copies** (was 10 + 11 + 15 — **the per-entry
  match rule is precisely the "where an invariant cannot be expressed" branch;
  they were one rule written twice**)
- **One layer is never enough, and layers do different jobs** (was 14 + 18)
- **A guard that collides with the contract gets edited** (was 13, unchanged)

**18 → 13. 212 lines → 171.**

**The condition the CTO attached, and it governed how I did it: the instances
must survive the merge.** These rules are obeyed because each carries the
incident that produced it — **an agent follows "assert the message text"
because it has read what happened when someone didn't.** So: five headings
with the findings as evidence beneath, not deletion. Every incident is still
there.

**And this was the last cheap consolidation** — at 13 it is still one page.

### The gap deliberately NOT given a rule
None of the rules is about end-to-end behaviour; they are all about claims and
controls, and **a seam between artefacts is specified nowhere, so no
spec-first test reaches it.** The CTO's judgement, which I accept:
**adding a nineteenth rule for that would be adding more of the kind of thing
that already missed it.**

It is in TASKS' definition of done instead, where it binds per slice:
**one real journey exercised end to end through the actual UI, by a client
that was served the pages.** A checkbox, not a principle — **and currently the
only thing in the project that closes that seam.** Verified present at line
614, alongside the review-freeze rule at line 24.

### The schema gap closed on a better reason than tidiness
`stated_problem` added; **the nominee column explicitly not reused.** Backend's
argument was sound, but the CTO's is decisive: **the nominee payload is
personal data about a third party — another living person's name and contact
details, with their own retention and notification implications — while a
correction request is the subject's own words about their own record. Two
different data subjects.** One column would force one retention rule and one
access rule onto both, **and the first person to reason about "who is in this
column" would be wrong for half the rows.**

Both-sides applied rather than only constraining the new case, and **a
redundant "subject" argument withdrawn from the CTO's own signature — free
text plus a separate "what area" field was a list sneaking back in.**

---

## D-061 — Standing authorization: run S2 through S7 without per-slice approval
**Date:** 2026-10-22 · **Decider:** HUMAN FOUNDER

**"Proceed and finish all slices, don't wait for approval."** Each slice runs
build → code review → QA → **one real journey through the UI** → commit,
without returning for a go-ahead between slices.

### What this does NOT authorize, and it is unchanged
The four reserved authorities stand: **spending, legal commitments, payment
activation, public launch.** Specifically:
- **S8 is infrastructure and deployment and is therefore NOT covered.** Nothing
  is deployed, no host is paid for, no domain is registered. S8 arrives with a
  packet, not with a commit.
- **The two live criticals need an ownership migration requiring a superuser
  on a real box** — a deployment act, not a code act.
- **No counsel is engaged, no campus is contacted, no money is spent.**

Everything S2–S7 needs is local and costs nothing, which is why this
authorization is possible at all.

### What I will bring the founder anyway, without being asked
A defect that cannot be fixed inside the build; a contract change that alters
what the product *is* rather than how it works; **anything that would make a
false statement to a student or a regulator**; and the handoff packet at the
end. Routine findings, rulings and rework go in the log, not to the founder.

### Process in force for every remaining slice
1. **Run on PostgreSQL before review.** `LIKE` is case-sensitive there and not
   on SQLite — S3's search is where this bites first.
2. **The tree freezes when a slice goes to review.** Four consecutive rounds
   measured a moving tree, and a review is a statement about an artefact.
3. **Each agent commits separately**, so authorship survives for the
   independence property that depends on it.
4. **One real journey exercised end to end through the actual UI**, by a
   client that was served the pages — the only thing in the project that
   closes the seam between artefacts. S1 was 500ing on its first POST with
   1,017 tests green.
5. **Both gates pass before integration**, and the author of a fix never
   grades it.

### The standing risk, recorded once and not re-raised
The product thesis is still unvalidated and no student has been interviewed.
**Building six more slices does not change that, and the founder is carrying
it knowingly** (D-039, D-040). The instrumentation that would answer it ships
with the slices; the answer needs students.

---

## D-062 — Red Team verifies every slice
**Date:** 2026-10-22 · **Decider:** HUMAN FOUNDER

**Standing instruction: every remaining slice is verified by Red Team.**
Encoded in TASKS' definition of done so it binds per slice rather than living
in a decision entry.

### Placement: after both gates, not before and not instead
Red Team's charter is **the strongest plausible failure case plus a test that
could disprove the plan** — a different question from *is this correct* and
*does this match the specification*. Running it earlier collapses it into a
third correctness review, **which is the one thing this project does not need
more of.**

Running it last means it attacks an artefact two gates have already approved,
**which is exactly where its first pass earned its keep: every defect the
apparatus caught was within an artefact, and every defect Red Team found was
at a seam between them.**

### The slice cycle is now five steps
build → **code review** → **QA** → **Red Team** → **one real journey through
the UI** → commit. **A slice is not done until Red Team has reported.**

Findings resolve as any gate's do: fixed, or carried with a tripwire that
fires when the gap closes. **A critical objection it cannot get resolved
escalates to the founder, per its charter — that path is unchanged and the CEO
agent does not absorb it.**

### Scoping, so the passes stay sharp rather than ritual
Its first pass was valuable because it was pointed at the whole apparatus
**and allowed to conclude the apparatus was wrong** — it recommended deleting
two of three review passes and ten tests, and was right. A per-slice pass is
pointed at **that slice's** strongest failure case.

For S2 that is the listing surface meeting a real student: **a seller who
misdescribes, a photo that leaks location, a price that means something
different to the two people reading it, and the gate opening wider than
intended now that there is finally something behind it to show.**

**Each pass must be free to conclude the slice is not worth having, not only
that it has bugs.** A Red Team that can only find defects is a fourth
reviewer.

### Tree and rule
It writes to `tests/redteam/**`. **A probe is not a regression test** — when a
probe finds something real, the finding goes to the owning agent and the
regression is written in *that* agent's tree. This was learned when probe
files in QA's tree made every QA measurement need a workaround for four
rounds.

---

## D-063 — Red Team encoded in three places; the loop is bounded
**Date:** 2026-10-22 · **Decider:** ceo-planning, on cto encoding

Encoded in TASKS' definition of done, in a new §4.1, in S2's own done-when
list — **and in `red-team.md` itself**, which was the gap the CTO correctly
identified: **a standing founder instruction that does not reach the charter
lives in one place while the agent reads another.** Charters are mine; I
edited it rather than ratifying someone else's edit.

### Three refinements the CTO settled rather than leaving to be discovered
**1. This adds a touchpoint; it does not move the existing one.** Red Team
already reviews **every gate, on the plan, before the spend** — the cheap
place to kill a slice. The per-slice pass attacks what was **built**. Keeping
both is what makes the scoping affordable: a slice pass is free to conclude
the slice was not worth having, **and if it does, that conclusion is also a
finding about the gate that let it through.** **A slice-level kill the gate
missed is the more valuable half of the finding.**

**2. The loop terminates.** A fix re-enters Code Review and QA **for the fix
only**, and Red Team re-reports **on the fix only** — never a fresh full pass.
**Three gates in series with no scoping rule is unbounded, and the pressure to
skip the third would arrive within two slices.** Bounded now rather than
skipped later for reasons that will sound practical.

**3. A collision with a rule written three hours earlier, resolved before its
first joint use.** The tree freezes when a slice goes to review; Red Team's
pass is such a measurement, so **the freeze holds through it** — while Red
Team writes freely in its own tree throughout. **The freeze is on the artefact
under measurement, never on the instrument.** Without that sentence the two
rules contradict the first time they meet.

### The metric that says whether this gate is still earning its cost
**What fraction of findings are at seams *between* artefacts rather than
*within* one.** Every defect the other gates caught was within an artefact;
**Red Team's first engineering pass was 100% seams. That is the number to
watch.**

**If two consecutive passes produce only defects review or QA could have
caught, the scoping has gone ritual — and the response is to re-point the
pass, not to drop the gate.** Recorded in the charter's own metrics so the
agent measures itself.

**S2's journey, now fixed in its done-when:** sign in → find by ISBN →
condition, annotations, damage, price → photo → publish → see it listed,
driven by a client that was served the pages. **Its Red Team pass is pointed
at the listing surface meeting a real student.**

---

## D-064 — Rule 13's third collision ratified as an invariant, not three names
**Date:** 2026-10-22 · **Decider:** ceo-planning, recording cto ratification

**The invariant: a money-shaped name is permitted only if it CANNOT carry a
per-transaction value.** That is precisely what P14 protects — the tax
position turns on a determinable gross amount **per transaction** — so **a
declaration identical for every transaction cannot be the thing forbidden.**

Two shapes qualify by construction: **(A)** an ORM lookup that must *end* at
the permitted column, optional relation prefix, suffix from Django's registry;
**(B)** an `UPPER_SNAKE` literal-int bound **pinned by test to a real CHECK
constraint.** Everything per-instance stays forbidden.

### Rule 12 applied honestly, and the two shapes did not get the same answer
**Shape A has a second layer:** a lookup can only reference the permitted
column, and the whitelist guarantees that is the only money column — **to
write `settled_price__gte` you first need a `settled_price` column, which the
whitelist kills.**

**Shape B had none.** A constant is not a column, so the whitelist does not
reach it, **and under rule 12 an exemption with no other catcher is a
widening.** So it was **not granted unpinned.** Requiring the constant to equal
a real CHECK bound supplies the missing layer — and closes a rule 11 gap,
since the bound existed twice and the pin makes one a copy rather than a
second definition free to drift.

### It measured before ratifying, and the measurement changed the write-up
Across the three collisions, QA's attacks and S4's predicted names:
`settled_price`, `offered_price`, `offer_amount` all fail;
`asking_price_paise__total` fails because `total` is not a lookup suffix;
a relation-prefixed lookup passes.

**But `MAX_OFFER_PAISE` passes the shape test and is rejected only by the
pin.** So **the shape rules alone would have admitted exactly the S4 case this
ratification exists to forbid.** The CTO wrote that into the ADR with the name
to re-run, **for anyone who later reads the pin as ceremony.**

### S4 decided in advance, in the right direction
A bound like `MAX_OFFER_PAISE` fails, because shape B needs a CHECK to pin to
and **there is no offer-amount column to have one.** Its reason, which is the
sentence to keep: ***a bound on a quantity we refuse to store is a quantity we
are about to start storing.***

**That is the argument for ratifying an invariant rather than three names — a
name list would have admitted it on the grounds that it looked like the bound
we had just allowed.**

### A correction to my own instruction
I told backend to work the order of resort and land on a rung. For the bound,
**rung 1 was available and harmful**: every honest name for a bound on paise
contains `paise` or `price`, so **renaming it to dodge a grep strips the unit
from the name of a money bound — the exact discipline that keeps integer-paise
safe.** Rung 1 is preferred because a rename is normally neutral; **here it was
not, and "preferred" was never "mandatory."**

### The pattern named: these collisions are structural
**The guard protects a money concept and the one permitted column has money
words in its name, so every slice that touches price will collide by
construction.** That is the argument for a decided invariant over a growing
exemption list — which is what rule 13's first instance cost: a deleted token
took three unrelated tokens with it and left four enforcing nothing.

### One predicted collision deliberately NOT pre-ruled
S7's export aggregate is a **third shape**, mandated by a frozen contract, and
**fails the invariant as stated** — an aggregate over one row equals that
row's value. Whether that matters depends on code that does not exist.
**Pre-deciding it would be deciding without pressure but also without
information, which is the opposite trade from the S4 one.** Decided when it
exists, against this invariant.

---

## D-065 — S2 frontend: three defects found by looking, none findable by testing
**Date:** 2026-10-22 · **Decider:** ceo-planning, recording frontend-developer
**Committed separately as `59ad6cf`** — the new per-agent commit rule, working.

Nine routes, the sell flow, listing page and want form. Zero application
JavaScript, and **the evidence is stronger than a grep: the whole journey was
driven twice by clients that execute none** — the test client across 22
requests including every POST, and a photo probe. The browser pass used only
form submits and navigations.

### The three defects, and why the suite could not have found them
**1. The service worker could never have updated its stylesheet.** A
hand-typed version constant, beside a comment claiming *"a stale one cannot
outlive a deploy"* — **true only while someone remembers to edit it.** It
failed the first time it was tested: a stylesheet change was invisible in the
browser because the worker kept serving the precached copy, **and a student
with the app installed would have kept the old stylesheet indefinitely.**
Rule 9's shape, living in a comment. The cache name is now a hash of the
shell's bytes, with the precache list and the name from one source so they
cannot drift.

**2. The seller-terms checkbox had no accessible name.** Chrome computed it as
`"on"` — its value attribute — because the label contained a link, and a
label may not contain interactive content. **A screen-reader user met an
unlabelled required control on the one tick the regulation needs informed**,
and tapping the link toggled the box. **The accessibility harness passed it,
correctly: a label with text does exist, and that is all a parser can see.**

**3. A masthead link was 28px tall** at the target width, under the floor — an
S1 defect in its own tree, **found by measuring every control's box rather
than reading markup.**

### The ruling that was hardest to hold, and it held
**The copy guard is red on six strings and every red is correct** — the banned
bare label matches anywhere, so it refuses the exact string the deck
prescribes as its replacement and the counsel brief names. **Frontend drafted
two with a substitute word and reverted both**: *editing mandated legal copy so
an over-broad grep stays green is rule 13's exact failure, and it would have
weakened a tax limb to keep a suite green.* Routed to the CTO with the
observation that **its proposed second layer — a rendered-DOM check — does not
exist**, which is the test the money invariant failed on.

### Two vacuity refusals, unprompted
**No route serves a listing photo**, so the criterion forbidding images under
a data-saver header **is satisfied vacuously and must not be reported as
passing.** The page says the honest thing instead: *"The seller attached 4
photos. BookHop has no way to show them yet."* And `shell_version()` **has no
conformance test**, which frontend named rather than let pass, because it owns
no test directory — routed to QA with the exact assertions.

### Where §1.7 was applied before writing rather than after
`sell.published` amended because **both halves were false**; two strings not
used because they label a notification nobody sends; one held back because
**nothing stores the comparison it describes**; and two **restored**, because
the EXIF column now exists and "this book" finally has a referent.

**And a class nobody had looked at: Django's own "This field is required."
reaches students, lives in the framework's catalogue, so the deny-list never
sees it and the deck never ruled on it.** Overridden — **a framework default
is copy nobody reviewed**, and the rest deserve a sweep.

### Measured, not estimated
First screen 985 bytes gzipped, listing page 1,271, full intake 2,717; shared
assets 10,940 once. No horizontal scroll at 320px; every control at or above
44px after the two fixes.

**Photo upload exercised against the real service in seven states**, with the
honest ceiling declared: with no JavaScript, retry re-opens the file picker
because **no browser repopulates a file input, by design.** The progress
indicator is the browser's own — *"determinate, native, zero bytes"* — and
neither it nor the offline state is simulated or claimed.

---

## D-066 — A scope correction, not an exemption — and an honest asymmetry
**Date:** 2026-10-22 · **Decider:** ceo-planning, recording cto ratification

**Reclassified: the copy collision is a SCOPE CORRECTION.** The bare-label
rule's rationale is about how a field is **labelled**; scanning prose with a
label rule was **over-breadth of exactly the kind criterion 7f had — a control
broader than the rationale it was written from, invisible because it still
reads protective.**

### Frontend's revert, recorded in full because of what it prevented
The thing about to be degraded was **legally mandated copy supporting a tax
limb**, the degradation would have been **invisible**, and **the suite would
have gone green.** Rule 13 exists because a deleted token once took three
others with it. **This would have been worse: a weakened tax limb does not
show up as a missing test.**

### Two findings on rule 12, and the CTO refused to pretend either way
**1. The named second layer was never going to be one.** The rendered-DOM
check verifies *what renders*; the risk this correction creates is **a prose
string that defeats negotiability** — and a DOM check does not evaluate
meaning either. **So this does not wait on it** — a different answer from the
money case, and the CTO distinguished them rather than wriggling: **there the
missing layer was the one that would have caught the risk; here the named
layer would not have.**

**2. It accepted a weaker layer here than for money, and said so.** For a
money constant, **any developer can introduce a new instance in any slice,
silently, with no reviewer who owns the concept** — hence the CHECK pin. For a
user-facing string, **nobody can: it comes from the copy deck through design
review, by construction.**

> **The human layer is a real control for copy and is not one for schema.
> Rule 12 is satisfied here in a weaker, partly human way, and anyone quoting
> this ratification should quote that sentence with it.**

### Two conditions, both cheap
Labels get **named manifest entries — msgid, reason, reviewer — so a seventh
label cannot inherit the exemption unreviewed.** And **the phrase list is
extended**, because the original four were never a complete expression of the
rule they enforce. **Narrowing one layer is the right moment to strengthen the
other.**

### The §3 gap treated as a process defect, because three times is not three accidents
A test filename, a verification-method spelling, and now four reads shipped
under names neither the contract nor the interface chose.

**The rule: a read the interface needs is a contract amendment FIRST, then an
implementation** — rule 6 applied to signatures instead of files. **"Contracts
before parallel work" is not satisfied by a contract the work then
overtakes**, and **neither agent invents a name.** Shipped names win for the
four that exist; backend sends the signatures.

### The photo route, specified as a contract fix rather than a missing page
Gate and scope in Django **first** — **a guessable media URL would be a side
channel around the discovery gate exactly as the notification scan would have
been** — then the web server streams. **404 rather than 403 when out of
scope, so the route cannot confirm a listing exists on another campus.**

### The contrast between two placeholders in one pass, which is the lesson
The ownership-scoped read standing in for discovery is **strictly tighter**
than what it replaces, **so the worst case is a missing listing rather than a
leaked one — that is how a placeholder should fail.** The photo gap left a
criterion passing vacuously.

> **The difference is that the first was visible as a restriction and the
> second was invisible as an absence.**

---

## D-067 — The gate governs what you can see, never whether you exist
**Date:** 2026-10-22 · **Decider:** ceo-planning, recording cto rulings

### 1. `User` does not get the gated manager, and the premise was the CTO's
Its ADR said *"S1 ships no ungated read"* — **false: S1 ships the session
lookup and the magic-link request.** Backend measured it rather than arguing
it, which made this a one-line ruling instead of a debate.

**The error named, because it is what would recur: it conflated "a read that
needs gating" with "a read through the default manager".** The gated manager
gates **every** read through the default — including resolving a user from
their own session, **the one read that must never be gated, because
authentication happens before any gate and cannot depend on one.**

**And the 26 failures were not friction: had it "worked", a real student on a
closed campus could not be resolved from their own session.**

> **The discovery gate governs what you can see, never whether you exist.**

**Criterion recorded so S4 does not re-ask it: the gated manager belongs on
models that are DISCOVERED — surfaced to a user who did not create them — not
on models RESOLVED by identity or ownership.** Discovered: listings, photos,
requests. Resolved: users, sessions, tokens — **and transfers, which is read
per-actor, so S4 must not add one there either.**

**The refusal as a test rather than a comment is the right artefact** — a
future retrofit fails loudly instead of rediscovering 26 broken tests.

### 2. The denormalisation remedy replaced, not copied
Backend's statement was exact, and the clinching half was **"every test sets
both through the same service that sets them correctly"** — rule 10's fourth
disguise, **in the control rather than in a test.**

**The CTO's original remedy was a nightly consistency check. It replaced it
rather than reusing it: that detects, does not prevent, and detects up to a
day late.** A **composite foreign key** makes the inconsistency *unwritable* —
by service, admin, raw SQL, migration or fixture. **No trigger, no job, no
window.**

> **Where a database can make a class of wrong state unrepresentable, that
> beats detecting it — and I reached for a job when a constraint was
> available.**

**And the test must write an inconsistent child directly, bypassing the
service, because a service-routed test proves only that the service is
correct — which was never in doubt.**

### 3. A prediction wrong in the helpful direction
Reverse accessors **are** gated. The measurement replaces the prediction, and
**the pinning is what earns the credit: labelling it a cross-library claim
means a Django upgrade turns it red instead of silently losing coverage** —
rule 9's cross-engine limb used on a library, which is the generalisation the
rule was written for.

### 4. Two constraints added while recording the signatures
The seller-block field is **a boolean and never the domain itself**. And
listing creation gains an **explicit** terms-accepted input rather than
reading an ambient account state, because **a seller who accepted v1 has not
accepted v2** — the written contract is accepted at listing time.

### 5. No admin — and the CTO wrote down what that costs its own stack argument
Four compounding reasons, the sharpest being that **a vendor table's column
cannot be renamed, so the first rung is structurally unavailable, and
exempting it would widen the money guard for code we do not control — the one
place an exemption cannot be audited.**

**But the stack ADR called the admin "the load-bearing reason" for choosing
Django.** It recorded that in the ADR rather than letting it pass:

> **Anyone re-reading §2.1 should know the strongest-sounding reason in it is
> the one that did not pay.**

The choice still holds on migrations, i18n and security defaults. **And the
replacement is scheduled rather than glossed: a command is sufficient while
every listing is seed data, and insufficient for Gate C, because the staff
queue needs a visible running timer — and a management command cannot show a
timer to the person being timed.** The staff console becomes a first-party
surface before Gate C.

---

## D-068 — Review: CHANGES REQUIRED. Three findings are about me
**Date:** 2026-10-22 · **Decider:** ceo-planning, recording code-review S2

### The three that are mine
**1. The tree was not frozen, two days after I adopted the rule.** Nineteen
uncommitted files while review measured. **I caused most of it** — dispatching
CTO escalations mid-gate and appending to this log. Review's verdict is
correct: ***rule 3a needs an enforcement mechanism, not another paragraph.***

**The mechanism, decided now: a gate measures a COMMIT, not a working tree.**
Review already attaches approval to a commit; it must *measure* one too. That
frees the working tree without asking anyone to stop typing, which is the only
version of this rule that survives contact. **And I dispatch no work while a
gate is open — findings queue until it reports.**

**2. Three measurements, three answers, one slice.** I reported 8 and 7
failures; review measured **15 and 13**; another pass saw 7. **Because the
tree moved under all three.** No number I gave this slice was trustworthy and
I should have noticed when the second disagreed with the first.

**3. I relayed a claim without checking it, and it was wrong in backend's
favour.** I told the founder media is in no backup scope. **It is** — the
infrastructure doc archives it. **The real defect is worse and I obscured it:
the restore procedure fetches the dump only, asserts the price trigger exists,
and checks no photo byte — then records the result as the charter's restore
test. It prints success on a restore that lost every photo.**

### Four blocking, each measured
- A missing-file photo **500s instead of 404** — *what a dump-only restore
  looks like at runtime.*
- The four-photo cap **fails on PostgreSQL and holds on SQLite.** **It holds
  on the test engine and fails on the production one**, and the model comment
  asserting single-writer is now measured false.
- A superscript digit passes `isdigit()` and raises on `int()`, so **the one
  money column 500s at both layers** — and ADR-003 names the service as the
  only detection layer, so rule 12's "name the other layer" has no answer.
- The denormalisation risk **confirmed by measurement**: flipping only the
  child's flag hides it from both the manager and the parent's accessor while
  the parent stays visible, **and the database does not refuse.** Not a
  disclosure in S2; **it is one in S3.**

### The finding that most resembles our own recurring defect
**The accessibility harness drops 17 of 35 routes silently** — the listing
page and the photo step **have never been swept**, and the intake form is
fetched without its query string so **the whole form is never rendered to
it.** Its self-reconciliation runs over the already-filtered list **and cannot
notice.** **None of S2's new interactive surface is covered, and the slice
reports accessibility green.**

### Credit where it was earned
**The price trigger: PASS, and review calls it the best control in the
project.** The guard-for-the-guard **asserts the price actually changed, so it
cannot be vacuous**, and the negative control is present twice. Its one gap is
handled honestly — the always-enabled property is `ASSUMED THERE` because
verifying it needs a superuser, **and the only place it could be verified is
the restore test that does not look.**

**Two of my relayed claims were wrong in backend's favour**: images being
undecoded is **safer** than reported, and the streaming header is **better
covered** than stated. Fuzzy search is named **the model for rule 10's
both-sides corollary** — opposite properties asserted per engine, neither
vacuous nor skipped.

**Holding all dispatch until QA reports.** That is the freeze, applied to
myself first.

---

## D-069 — QA: S2 does not pass. A photo served past a closed legal gate
**Date:** 2026-10-22 · **Decider:** ceo-planning, recording test-qa S2
**Gate output committed at `ac2d622`.** Thirteen findings, **all reported
rather than work in progress**; all eight baseline failures closed.

### The one that is a compliance failure rather than a defect
**The composite foreign key the architecture specified is not built**, and QA
wrote the inconsistency directly, as the amendment instructs:

> **A photo whose seed flag disagrees with its listing is served — 200, real
> image bytes — to a non-owner, on a campus whose discovery gate is closed.**

The read checks the **child's** flag to decide the **parent's** visibility,
against the contract's own rule that a photo is as gated as its listing.
Repointing the tenant column crosses the tenancy boundary outright. **The
charter does not let this be negotiated down**, and **the nightly check the
amendment replaced is also gone**, so that column now has neither remedy.

### The money defect that cannot be corrected afterwards
**`320,00` is stored as Rs 32,000** — the cleaner strips commas **before** the
decimal check, **and its own docstring names that exact mistake as deserving
its own sentence.** The column is immutable by trigger, **so a student who
mistypes once cannot be fixed.**

### Three more, each measured
The four-photo cap **is nine** under six simultaneous uploads — and it **fails
on PostgreSQL while holding on SQLite**, so it holds on the test engine and
fails on the production one. A photo row whose file is missing **500s instead
of 404**. And the idempotency fingerprint **excludes uploaded files**, so a
different photo under a reused key replays the first and **the second is
silently discarded.**

### A claim withdrawn in backend's favour, and the narrower one is worse
Media **is** in backup scope. **The restore procedure never opens the
tarball** — so paired with the 404 defect, **a restore prints success and
leaves every photo URL at 500.**

### The price trigger survived eleven attack routes
17 pass, 1 named skip. Refused by message text and SQLSTATE on six write
paths including raw SQL and an unqualified table-wide update; **correctly not
refused** on transitions, same-price writes and a full save rewriting every
column at its current value. **QA verified backend's guard-for-the-guard
independently — true, not asserted — and added the two limbs it lacked: a
dropped trigger caught by name, and a *disabled* one caught by state.**

### QA found three unconditional skips in its own tree that could never start
**Including one that left a named compensating control measuring two
operational endpoints instead of the response surface.** All three inverted;
the guard now sweeps all seventeen S2 payloads. **Fourth time a defect was
found in QA's own work, and the fourth time it was QA that reported it.**

### Escalated, not decided: two frozen documents contradict
**A real student creates a listing on a closed campus: 201.** One document
requires a refusal and calls its stack standing; the other **scopes the gate
to reads.** QA declined to pick a side. The underlying question is a product
one: **is a closed gate a statement about what a campus can see, or about
whether it is open for business?**

**The whole open-gate half of the product remains unexercised** — no two real
students have ever interacted, and discovery does not exist.

---

## D-070 — The gate is a read control; and a later ruling invalidated an earlier one
**Date:** 2026-10-22 · **Decider:** ceo-planning, recording cto

### The gate question, settled from the rationale rather than from precedent
**The gate is a READ control.** The CTO **re-read the compliance rationale
rather than reasoning from its own prior ruling**, and the rationale is
explicit: the regulatory trigger is **the browsable surface** — a private
intake nobody can browse is a record, not a platform. **So a student creating
a listing nobody can see is exactly that intake, and blocking the write
protects nothing the law asks us to protect.**

**And a positive reason rather than an absence of objection: R-01.**
Cold-start liquidity is the top risk in the register, and **blocking writes
until discovery opens means the campus opens with zero listings and the first
search fails — R-01 materialising by design.** Accumulating supply behind a
closed surface *is* what a staged launch is.

**My objection was treated as a disclosure problem rather than dismissed.**
The seller must be told at publish that nobody can see it yet — routed as a
required string. The "rules nobody told them about" half was already handled:
terms are accepted **per version at listing time**, so a later version is a
new acceptance rather than a retrospective change.

**One constraint added, and it is the only way this could leak: the create
flow may surface no other user's row, including a count.** No *"3 others are
selling this"*. **That is a read wearing a write's clothing.**

### The CTO's own error, second instance of the same shape
**It wrote the composite-FK amendment in the present tense as though it
existed, and removed the nightly check it "replaced" — so the column had
neither remedy.** Rule 9's shape in its own document, after the correction
endpoint.

**Standing rule extracted, and promoted into `CLAUDE.md` rule 12: never remove
a remedy before its replacement is green.** The new goes in beside the old;
the old comes out in the commit that turns the new one green.
**An upgrade that leaves a gap between the two is a downgrade for the length
of the gap** — and the gap is invisible, because the document already
describes the better state.

### Two controls leaning on each other, now joined
The always-enabled property **only matters under replica role — which is what
a trigger-disabling restore uses.** So **the append-only guarantee was
unverified in exactly the operation during which someone might be rewriting
history.** The restore test now sets replica role and re-runs every refusal.

**That test is the right home precisely because it is the one context where we
hold superuser legitimately**, on a throwaway database — **verifying it
elsewhere would mean granting a privilege in order to check a
privilege-dependent property.** And the sweep's table list is now derived from
the inventory: **the hard-coded three was a list where an invariant belonged,
inside the instrument.**

### A later decision invalidated an earlier justification, and it said so
Giving the copy deck one owner means **the author of a string becomes its only
reviewer** — which **falsifies the explicit ground on which the copy guard's
weaker second layer was accepted this morning.** So **code review takes copy
review as a named obligation** on every change touching the deck or the
catalogues, restoring the second pair of eyes the ratification was leaning on.
Ownership reverts when design returns.

### Third stale status marker, so it fixed the class
**A manifest records the exemption and its reviewer; it does not record
implementation status, because the conformance test already knows it.**
**A status in two places is a rule in two places — and the copy that is not
executed is always the one that is wrong.** Where a status must appear in
prose it now carries the conformance test's name beside it, so a reader can
check rather than believe. **Two of the three stale markers were its own.**

---

## D-072 — The closed friends test is shape 1: nothing completes a purchase

**Date:** 2026-10-23 · **Decider:** founder

Asked directly, answered directly: *"Friends can list, search, browse and
message, but no purchase completes."*

### What this buys

`evidence/CLOSED-TEST.md` establishes that the Consumer Protection
(E-Commerce) Rules attach to a marketplace e-commerce entity with **no
turnover, user-count or transaction threshold anywhere in the instrument** —
verified against the Gazette English text. At shape 2 a company is required at
twelve users exactly as at two thousand. At shape 1 the Rules have nothing to
attach to, **incorporation is not required to run the test**, and the honest
requirement set is four items rather than ten: a published privacy notice,
published terms, a named reachable grievance officer, and the in-force
takedown clocks.

Incorporation is still recommended and still started — it has a four-week lead
time and the founder carries personal liability either way — but it stops
being a **blocker on the test**.

### What it costs, and the condition attached

**Shape 1 is a legal position that depends on the product having no
completion path. That must be enforced, not intended.**

Measured today: `LISTING_TRANSITIONS` permits `RESERVED → CLOSED_TRANSFERRED`
and `web/views.py:850` already renders a label for it — but **no service
function calls into either state**, so shape 1 is true right now *by absence*.
An absence is not a control. The slice that builds reserve-and-complete would
move this company into shape 2 without anybody deciding to, and the document
asserting shape 1 would still read true.

So the position becomes data on the authorisation row and a refusal in
`_transition` — see `API-CONTRACT.md` **A-37**. The legal claim and the code
then cannot drift apart, which is the whole of rule 9 applied to a founder
decision rather than to a control.

### Not decided here

Whether the pilot proper is shape 2. This decision governs **the closed test
only**, and the authorisation row carries a participant ceiling and an expiry
so it cannot silently become the permanent arrangement.

---

## D-071 — S2 rework: both trees clean, and two findings nobody asked for
**Date:** 2026-10-22 · **Decider:** ceo-planning
**Committed separately:** backend `57c6689`, frontend `f24b133`, from
`ac2d622`. **CEO-verified:** PostgreSQL 1570 passed / 3 failed; SQLite 1493 /
5. **Every remaining failure is in QA's tree and none is a defect.**

### The compliance failure is closed by construction
A unique index on the parent's identity tuple and a four-column foreign key
from each child, **so a photo can no longer claim a tenant identity its
listing does not have — by service, admin, raw SQL, migration or fixture.**
**And the read was fixed too**: it had resolved the *child's* flag to decide
the *parent's* visibility. The nightly check is **explicitly superseded with a
test asserting no such job exists**, rather than forgotten — the rule from
D-070 applied the same day it was written.

### There were two hand-written money parsers
Rule 11's exact failure mode, **on the one column that cannot be edited
afterwards.** Now one, in the layer the ADR names as the detection point, and
frontend repointed its call site **so the defect is closed end to end rather
than in one layer.**

**The Tamil-numeral question decided rather than inherited: refused, with its
own sentence, never converted.** The reasoning is the right one — **the column
is immutable, so an amount we read differently from the way it was written
cannot be corrected**; the seller would have to withdraw and relist while the
listing carries a price they did not set. **A refusal costs one retype.**

### The ratified exemption caught two of backend's own names, within the hour
Including **the exact case the CTO measured when it refused to grant the shape
unpinned** — a bound with no constraint behind it. **Both resolved at rung 1
by renaming, and both renames were more accurate than the originals.**

### Two findings nobody asked for
**The stale-listing warning fired on publication date — so on the morning a
campus opened, its entire backlog would have greeted the first buyer with
"listed 40 days ago — this may be gone."** Wrong in both halves: **nothing
could have gone from a listing nobody could ever have taken.** Found by
following a consequence of someone else's ruling into its own strings. **The
approved string is untouched; the defect was the number.**

**And three shipped sentences sat in the catalogue as empty message ids — so
the deny-list read the empty one and reported green.** Our signature defect,
inside the copy control itself, **found by writing the verification that did
not exist.** Django's own required-field message was also reaching students on
29 fields across 10 forms.

### Two judgements endorsed because they are the kind that erode
Frontend **flagged a sibling string for review rather than rewriting it** —
*unilaterally editing approved copy beyond the finding is the other half of
this problem.* And it **refused to forge a gate authorisation to green a
probe**, because **that would be fabricating the evidence the gate exists to
require.**

**My wording was overruled and correctly:** *"listings open when BookHop
launches on your campus"* **reads as an undertaking that the campus will
open**, and we have no date. On a sentence whose only job is to stop a seller
feeling tricked, promising a launch is the failure it exists to prevent.

### Stated, not hidden
The SQLite migration **splices a foreign-key clause using a string index** and
was verified forward only, not round-tripped — backend names it as what it
most wants checked. The photo lock is **asserted by construction and not
re-measured under concurrency.** And `web/selfcheck.py` **is a check that has
not started**, said in capitals by its own author.
