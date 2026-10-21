# COST-MODEL.md — infrastructure cost at pilot scale

**Owner:** cto · **Version:** v1.0 · **Date:** 2026-10-21
**Status: NOT APPROVED. This is an escalation packet, not a plan of record.**
Infrastructure spend is a reserved founder authority (`README.md` §2).

**Evidence standard applied** (`README.md` §8, `CLAUDE.md` rule 1): **this
agent did not browse.** Every rupee below is tagged `ASSUMPTION:` with the URL
to verify it on and the reason it is believed. No figure here is a fact, and
none should be committed against without the founder or finance checking it on
the provider's own page on the day.

---

## 1. The two assumptions every other number rests on

| | Value | Basis | Test that replaces it |
|---|---|---|---|
| **A-FX** | **Rs 84 = USD 1** | `ASSUMPTION:` no FX source was consulted and the rate on 2026-10-21 is unknown to this agent. Chosen as a round figure near the recent range | Read the rate on the day of purchase. A ±10% move changes Tier 2 by about Rs 175/month — material to the decision only at the margin |
| **A-SCALE** | **One campus · ~200–500 accounts · ~2,000–5,000 listings · ~3,000 photos · <5 req/s peak** | Derived from D-007 (one campus) and `TEST-1`'s 30-handover pass bar; **not measured** | Real pilot traffic. This is the figure most likely to be wrong in the *low* direction, and the box is sized with headroom for that |

Everything else scales off these two.

---

## 2. Tier 0 — build, test and QA: **Rs 0 per month**

Stated first because it is the most useful fact in this document.

| Item | Cost | Note |
|---|---|---|
| Postgres 16 (Docker Desktop, Windows) | Rs 0 | |
| Python, Django, every runtime dependency | Rs 0 | open source, nine packages |
| Local dev server, seed data | Rs 0 | `manage.py seed_demo` |
| CI | Rs 0 | `ASSUMPTION:` a free CI tier covers a repo this size; verify at https://github.com/pricing before relying on it. If not free, CI runs locally as a pre-commit script at Rs 0 |
| Playwright for e2e + a11y | Rs 0 | |
| **Total** | **Rs 0** | |

**Slices S0 through S7 — every line of application code, every test, the whole
state machine, every metric query and the WCAG work — can be built and verified
for Rs 0.** Spend is only needed to put it on the internet, which Gate B
blocks anyway until the company exists.

**This is the single most useful consequence of ADR-001's choices**, and it
means the founder's spending decision can wait until there is working software
to look at rather than being made on a promise.

---

## 3. Tier 1 — minimum pilot: **≈ Rs 630 / month**

The cheapest configuration that is defensible. For a closed Gate C pilot.

| # | Item | USD/mo | Rs/mo | `ASSUMPTION` and where to verify |
|---|---|---|---|---|
| 1 | VM, 1 vCPU / 1 GB / 25 GB SSD, Indian region | 6.00 | 504 | `ASSUMPTION:` the entry-level price for a basic droplet-class VM in an Indian region is USD 6/mo. Long-standing published pricing, **not re-verified today**. Verify: https://www.digitalocean.com/pricing/droplets · compare https://www.e2enetworks.com/pricing (Indian-incorporated — relevant to ADR-001 §5) |
| 2 | Provider weekly snapshots (≈20% of VM) | 1.20 | 101 | `ASSUMPTION:` backups priced at 20% of the droplet. Verify on the same page. **Weekly snapshots alone are not a backup strategy** — item 3 is why |
| 3 | Off-site backup: nightly encrypted dump **pulled to the founder's machine** | 0 | 0 | Rs 0 and that is the problem — it depends on a laptop being switched on. `INFRA.md` §3.2 |
| 4 | Transactional email | — | 25 | `ASSUMPTION:` ~USD 0.10 per 1,000 emails, at a few thousand emails/month → low tens of rupees. Verify: https://aws.amazon.com/ses/pricing/ (ap-south-1 keeps the processor in India) |
| 5 | Domain (.in), amortised | — | 60 | `ASSUMPTION:` Rs ~700/yr for a .in domain. Verify with any Indian registrar |
| 6 | TLS (Let's Encrypt) | 0 | 0 | free |
| 7 | Uptime monitoring (free tier) | 0 | 0 | `ASSUMPTION:` a free tier at 1-minute interval exists; processes no personal data |
| 8 | Error tracking, APM, analytics | 0 | 0 | **Deliberately none** — ADR-001 §3 |
| 9 | Object storage, CDN, SMS/OTP, push vendor | 0 | 0 | **Deliberately none** — ADR-001 §2.5, §2.6 |
| | **Total** | **7.20** | **≈ Rs 630** | **≈ Rs 7,560 / year** |

---

## 4. Tier 2 — recommended pilot: **≈ Rs 1,750 / month**

Two differences from Tier 1, both bought for one reason: **a backup that
survives the founder's laptop dying, and a box that is not one memory spike
from an outage.**

| # | Item | USD/mo | Rs/mo | `ASSUMPTION` and where to verify |
|---|---|---|---|---|
| 1 | VM, 1 vCPU / **2 GB** / 50 GB SSD, Indian region | 12.00 | 1,008 | `ASSUMPTION:` USD 12/mo for the 2 GB tier. Same source as Tier 1 item 1. **Why 2 GB:** Postgres and gunicorn co-resident on 1 GB is the first thing that breaks (`INFRA.md` §6) |
| 2 | Provider weekly snapshots (≈20%) | 2.40 | 202 | as above |
| 3 | **Off-site object storage, Indian region, for nightly encrypted dumps** | 5.00 | 420 | `ASSUMPTION:` USD 5/mo entry tier (~250 GB) for S3-compatible storage. Verify: https://www.digitalocean.com/pricing/spaces · https://aws.amazon.com/s3/pricing/ (ap-south-1). **Confirm an Indian region is available for the chosen product before buying** — if not, this line moves to an Indian provider |
| 4 | Transactional email | — | 25 | as above |
| 5 | Domain, amortised | — | 60 | as above |
| 6–9 | TLS, monitoring, and everything deliberately absent | 0 | 0 | as above |
| | **Total** | **19.40** | **≈ Rs 1,715** | **≈ Rs 20,580 / year** |

Call it **Rs 1,750/month** for planning. Round up, not down.

---

## 5. The escalation — for the founder, via ceo-planning

**Decision needed.** Authorise infrastructure spend, and at which tier.

**Options.**

| | Monthly | Annual | What it gets | What it risks |
|---|---|---|---|---|
| **(a) Nothing yet** | **Rs 0** | Rs 0 | All of S0–S7 built and tested locally. **Gate B blocks deployment anyway until the company exists**, so this costs no calendar time today | Nothing, until there is a reason to deploy. **The deadline is Gate C, not now** |
| **(b) Tier 1** | **Rs 630** | Rs 7,560 | A real, deployed, usable pilot | Off-site backup depends on the founder's laptop. A 1 GB box will need upgrading if usage exceeds A-SCALE |
| **(c) Tier 2 — recommended** | **Rs 1,750** | Rs 20,580 | The same, plus an off-site backup that survives a laptop failure and a box with real headroom | Rs 20,580/year, which **exceeds the entire approved programme budget of Rs 16,500** |

**Evidence.** All figures are `ASSUMPTION`-tagged in §3 and §4 and unverified by
this agent. The stack choice (ADR-001) was made partly to keep this number
small; the three largest costs a conventional stack would have added —
managed Postgres, hosted error tracking and an SMS gateway — are absent by
design, and AWS-managed equivalents were costed at roughly Rs 5,000–8,000/month
(ADR-001 §3, also `ASSUMPTION`).

**Recommendation.** **Approve (a) now and decide between (b) and (c) when Gate
B's legal preconditions are actually close.** The reason is not frugality: it
is that **the infrastructure decision has no deadline until Gate C, while
incorporation does** (Gate B1/B2, three to four weeks elapsed per
`INCORPORATION-AND-BLOCKERS.md` §1.4). Paying Rs 1,750/month to run a server
nobody may lawfully browse is pure burn. When the decision does come, **(c) is
the right answer** — the Rs 1,120/month difference buys the only backup copy
that does not depend on one person's laptop, and `INFRA.md` §3.3's restore
test is the thing the G4 go/no-go packet must be able to show.

**Cost of delay: zero until Gate C.** Provisioning the box and running the
first deploy is a half-day task (`INFRA.md` §4). Nothing in the build order is
blocked by it; slice S8 is the only slice that touches it, and it is last for
exactly this reason.

**What this escalation does not ask for.** No payment provider (ADR-003). No
legal spend (that is `INCORPORATION-AND-BLOCKERS.md` §5's separate ask). No
incorporation cost (D-008 records Rs 8,000–20,000, already outside the D-007
envelope). **No agent has committed, reserved or spent anything.**

---

## 6. Budget reconciliation

From D-008's ledger: **Rs 16,500 approved · Rs 0 spent · Rs 5,000 ring-fenced
for interviews · Rs 2,600 unallocated**, with incorporation separate and
unapproved in amount.

| | |
|---|---|
| Unallocated today | **Rs 2,600** |
| Tier 2 for one month | Rs 1,750 |
| Tier 2 for three months | Rs 5,250 — **exceeds the unallocated balance** |
| Tier 1 for three months | Rs 1,890 — fits, barely |

**Stated plainly: infrastructure at Tier 2 is not fundable from the existing
envelope beyond one month.** It is a new, recurring commitment and should be
approved as one — annually, with a number — rather than drawn down from a
budget approved for interviews and a concierge pilot. **No agent may book it
against the D-007 envelope** (the same warning
`INCORPORATION-AND-BLOCKERS.md` §1.4 gives about incorporation, for the same
reason).

---

## 7. What this cost model deliberately excludes

Not hidden — out of this document's scope, and each has an owner.

| Excluded | Owner | Note |
|---|---|---|
| **Founder and operator labour** | market-finance | The dominant cost. `TEST-1` §3.5 and G1-MEMO O-4 value it at **Rs 2.84/minute** (Rs 30,000/month fully loaded) and that is what the support-minutes metric converts at. At Rs 11.36/transfer (the 4.00-minute pass bar), **support labour exceeds infrastructure at roughly 150 transfers a month** — which is the honest framing: *infrastructure is not this business's cost problem, support is* (R-13, R-25) |
| Incorporation and annual statutory compliance | founder + CS | Rs 8,000–20,000 once, then **Rs 15,000–30,000/year** (`INCORPORATION-AND-BLOCKERS.md` §1.6) |
| Counsel C1–C3 | founder | Unapproved; one scoped engagement |
| Acquisition spend | marketplace-ops | `METRICS.md` CAC; entered manually into the weekly export, not captured by the app |
| Interviews (Rs 5,000 ring-fenced) | product-manager | D-007 |
| Insurance | founder | Gate C8 — a decision, or a recorded decision not to |
| Multi-campus / multi-city infrastructure | cto | Out of scope. Expect roughly linear in VM size, not in campus count — one box serves several campuses at this scale (ADR-002) |

---

## 8. Reversal triggers

- **A-SCALE is exceeded** (sustained >5 req/s, or media past ~15 GB): Tier 2's
  VM step, then object storage for media (ADR-001 §2.6). Not a re-architecture.
- **Privacy-compliance rejects a foreign-owned Indian region** (ADR-001 §5):
  move to an Indian-incorporated provider. Re-cost §3/§4 items 1–3; the stack
  does not change.
- **FX moves more than 10%**: re-run §3 and §4; only Tier 2 is materially
  affected.
- **The pilot is killed** (R-21, D-009's reversal trigger): the recurring spend
  stops within one billing cycle, and the artefact worth keeping — the Postgres
  dump and the metric SQL — costs nothing to keep. **A monthly VM rather than
  an annual commitment is deliberate for exactly this reason.**
