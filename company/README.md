# BookHop — Company Brain

Shared, versioned context. **Every agent reads the relevant section before
acting and updates it when a decision changes.** If a claim is not in here
with a source, it is not a fact.

Version: v0.4 · Last updated: 2026-10-21 · Owner: CEO / Planning Agent

---

## 1. What we are building

A marketplace for **physical used books** in India. Pilot: verified adults at
2–3 Chennai campuses, local handovers. Designed from day one for multi-campus
and multi-city, released stage by stage.

### v1 scope — narrowed by founder decision D-007 (2026-10-21)

**v1 ships: buy and sell, edition-locked prescribed textbooks, one campus.**

1. **Buy** a listed book.
2. **Sell** a book at a stated price.

**Deferred, not deleted** — the data model must still accommodate both:

3. ~~**Exchange** — direct two-person swap.~~ Cut from v1. Supply and demand
   peak in *antiphase* (sellers release at semester end, buyers need books at
   semester start), and direct swap requires two mutually matching needs at
   the same moment. It also generates zero cash. Returns to scope if Test 1
   shows swap-only users are the cheapest supply we can acquire.
4. ~~General reading.~~ Cut from v1. Dilutes the only defensible wedge across
   a category where we hold no advantage.

**The student side is free in v1.** The 6% transaction fee is falsified
(D-006): minimum take rate to cover support and payment cost alone is 16.7%
at base. Red Team's O-10 — *inspect-before-pay is the disintermediation
event* — remains open and is why this is a falsification, not a repricing.

A future **credit-based exchange** (removing the need for a perfect two-person
match) is designed but **not released** until its economics and applicable
payment rules are reviewed. See `evidence/COMPLIANCE.md`.

### Product thesis — v0.2, revised after Phase A and G1

> A **syllabus-to-shelf matching layer for edition-locked prescribed
> textbooks on one campus**, free to students permanently by design — no fee,
> no escrow, no custody. The hypothesised payer is the **institution**.

**Status: the monetisation thesis is FALSIFIED. The product thesis stands,
unvalidated.** Zero students have been interviewed.

What Phase A killed in the v0.1 thesis: "find a relevant book nearby" is not
a wedge. The campus-gate photocopy at Rs 60–200 beats us on price and speed;
the free PDF in the batch WhatsApp group beats us on everything but reading
experience. Proximity alone is refuted by NearBook — explicitly hyperlocal,
~600k downloads, pre-revenue. The only wedge that survived is the
**whole-book, whole-semester need** where both alternatives fail.

Charging students free by design is not generosity — it deletes fee
collection, disintermediation-as-revenue-risk, the entire PPI question and
most e-commerce exposure in one move. The institutional payer is a
**hypothesis with a Rs 0 test attached** (D-007 item 4), not a strategy.

---

## 2. Reserved founder authorities

The founder (human) retains final authority over:

- **Spending** of any kind
- **Legal commitments** (campus agreements, terms, contracts)
- **Payment activation**
- **Public launch** / any irreversible release action

No agent may commit these. Escalation format: decision needed, options,
evidence, recommendation, cost of delay. Short.

---

## 3. The agent organization

Charters live in `.claude/agents/`. Each specifies objective, authority,
inputs, deliverables, metrics, dependencies, escalation.

### Standing agents (created 2026-10-21)
| Agent | Owns |
|---|---|
| `ceo-planning` | Program, sequencing, decision log, company brain, weekly loop |
| `product-manager` | User, problem, PRD, roadmap, acceptance criteria, experience |
| `design-director` | Visual direction, interaction, a11y, EN/TA copy, design system |
| `cto` | Architecture, contracts, security, build order, production readiness |
| `market-finance` | Competitors, TAM/SAM/SOM, pricing, unit economics, forecasts |
| `marketplace-ops` | Supply seeding, handovers, moderation, support, disputes |
| `privacy-compliance` | DPDP, e-commerce rules, payments, tax, terms, launch risk |
| `red-team` | Adversarial review of every consequential decision |

### Specialist agents (created by their owner, before their work begins)
| Agent | Created by | Created when | Status |
|---|---|---|---|
| `backend-developer` | cto | Phase C start | **created 2026-10-21** |
| `frontend-developer` | cto | Phase C start | **created 2026-10-21** |
| `code-review` | cto | Phase C start | **created 2026-10-21** (never reviews its own diff) |
| `test-qa` | cto | Phase C start | **created 2026-10-21** (writes tests from spec, not implementation) |
| `platform-sre` | cto | infrastructure work begins | **created 2026-10-21, DORMANT** until S8 + founder spend approval |
| `campus-growth` | marketplace-ops | Phase D prep | not yet created |
| `trust-support` | marketplace-ops | Phase D prep | not yet created |

No further agents unless an owner can state the distinct outcome it delivers.

---

## 4. Assignment format (mandatory)

Every assignment to an agent uses exactly this shape:

- **Role** — who owns the outcome.
- **Context** — user, objective, evidence, constraints, dependencies.
- **Command** — the specific result to produce or decision to test.
- **Format** — deliverable, acceptance criteria, verification, handoff recipient.

---

## 5. The weekly loop: audit → delegate → measure → improve

1. **Audit** — where did work queue, rework, or stall this week?
2. **Delegate** — assign repeatable work to the agent that owns the outcome.
3. **Measure** — compare against the recorded baseline in `metrics/METRICS.md`.
4. **Improve** — keep, change, or **retire** the workflow. Retiring counts.

Automate routine steps. Route exceptions and high-risk decisions to a human.

---

## 6. Gates

At each gate, Red Team receives the proposal **and its evidence**, returns
objections plus falsification tests, and the CEO agent records a reasoned
decision in `decisions/DECISIONS.md`.

- Ordinary objection: one round, then decide. No endless debate.
- **Critical** unresolved objection: escalates to the founder.

| Gate | Entry criteria | Decider |
|---|---|---|
| G1 Strategy | Phase A evidence complete, thesis survives Red Team | CEO + founder |
| G2 Build | PRD + design system + ADRs + contracts frozen | CEO |
| G3 Pilot | Working slices, QA green, compliance cleared, supply seeded | founder |
| G4 Public | Go/no-go packet (see §7) | **founder only** |

---

## 7. Public-release go/no-go packet (contents)

Security · privacy · accessibility · legal and tax review · payment readiness ·
terms and policies · support capacity · backups with tested restore ·
operating costs · unresolved Red Team objections.

### How to read a gate authorisation row (accepted risk A11)

A `gate_authorisations` row is **a named person asserting these things on a
date. It is not verification.** Whoever assembles this packet must read it that
way.

What the system genuinely checks, and what it cannot:

| Evidence | Guarantee |
|---|---|
| `cin`, `incorporation_date`, `inc20a_filed_at`, grievance-officer fields | Read from typed columns on `legal_entities`. Dates must parse, must not be in the future, and filing must not precede incorporation. CIN **shape** is validated — **shape is not existence.** |
| `notice_version_ids` | Real foreign keys that must resolve to published notices of the three required kinds. **The one evidence item verifiable end-to-end in the database**, so it carries the weight the others cannot. |
| `breach_rehearsal_at` | A date. Must parse. |
| `counsel_engagement_ref`, `takedown_sop_ref`, `oncall_rota_ref`, `campus_mou_ref` | **Genuinely external.** A placeholder deny-list catches a field nobody filled in. **It cannot catch one filled in falsely.** |
| `authorised_by_human` | Rejects every name an agent would type, including all thirteen charter names. This field carries the whole "no agent writes this row" rule. |

**So: beyond the typed fields, the control is a human signature and the
references are a prompt that refuses to be blank.** Uploaded certificates were
considered and rejected — nothing can validate a PDF of a certificate of
incorporation either, and it would buy a document store, a retention rule and
a processor agreement for an unchanged guarantee.

**The row, not the audit entry, is the packet artefact.** They give different
guarantees: the row gives immutability of content via an append-only trigger;
the audit chain gives tamper-evidence over the fact and the time. Neither
substitutes for the other. The audit entry points at the row, so following the
chain reaches the named human in one hop **without the chain ever storing a
person's name.**

---

## 8. Evidence standard

- Every factual claim: source URL + date accessed.
- Every number without a source: tagged `ASSUMPTION:` with reasoning and the
  test that would replace it.
- **Interviews and survey results are never fabricated.** If we have not run
  them, the deliverable is the *instrument*, not the *results*.
- Agents may not cite each other as the origin of a fact.

---

## 9. Index

| Area | File | Owner | Status |
|---|---|---|---|
| Decision log | `decisions/DECISIONS.md` | ceo-planning | live |
| Risk register | `risks/RISK-REGISTER.md` | ceo-planning | live |
| Metric definitions | `metrics/METRICS.md` | ceo-planning | live |
| Competitor audit | `evidence/COMPETITORS.md` | market-finance | live (Phase A complete) |
| Market denominator | `evidence/MARKET-SIZING.md` | market-finance | live (Phase A complete) |
| Compliance review | `evidence/COMPLIANCE.md` | privacy-compliance | live (Phase A complete) |
| Persona & research plan | `product/DISCOVERY.md` | product-manager | live (instruments ready, ZERO results) |
| Red Team memos | `evidence/RED-TEAM/` | red-team | G1 memo complete |
| Financial model | `finance/MODEL.md` | market-finance | live (Phase A complete, re-runnable) |
| PRD | `product/PRD.md` | product-manager | Phase B |
| Journeys | `product/JOURNEYS.md` | product-manager | Phase B |
| Design directions | `design/DIRECTIONS.md` | design-director | Phase B |
| Design system | `design/SYSTEM.md` | design-director | Phase B |
| ADRs / data model / API | `architecture/` | cto | **live, contracts FROZEN** |
| **Test 1 concierge kit** | `ops/TEST-1-CONCIERGE-PILOT.md` + `ops/test1/` | marketplace-ops | **ready to run** |
| **Incorporation & blockers** | `ops/INCORPORATION-AND-BLOCKERS.md` | privacy-compliance | **live** |
| **Institutional probe** | `evidence/INSTITUTIONAL-PROBE.md` | market-finance | **ready to run** |
| **G1 founder packet** | `decisions/G1-FOUNDER-PACKET.md` | ceo-planning | approved D-007 |
| Pilot playbook | `ops/PILOT-PLAYBOOK.md` | marketplace-ops | Phase D |
| Support & moderation | `ops/SUPPORT.md`, `ops/MODERATION.md` | marketplace-ops | Phase D |
| Rollout plan | `ops/ROLLOUT.md` | ceo-planning | Phase E |
