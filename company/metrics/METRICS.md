# Metric Definitions

Owner: CEO / Planning Agent. A metric without a stated **denominator** is not
a metric. No baselines exist yet — the pilot sets them.

---

## Marketplace health

| Metric | Definition | Denominator | Baseline |
|---|---|---|---|
| Verified students | Accounts passing campus + adult verification | — | 0 |
| Valid listings | Listings live, in stock, passing the moderation bar | all listings created | 0 |
| Supply density | Valid listings per active campus | campuses with >=1 active user | 0 |
| Search success rate | Searches returning >=1 result the user then opens | all searches | 0 |
| Match rate | Searches/requests leading to an accepted offer | distinct searching users/week | 0 |
| Time to match | Median hours, listing live -> offer accepted | matched listings | 0 |
| Completion rate | Handovers both parties confirm | accepted offers | 0 |
| No-show rate | Scheduled handovers where one party does not appear | scheduled handovers | 0 |
| Cancellation rate | Accepted offers cancelled before handover | accepted offers | 0 |
| Dispute rate | Transfers raising a condition/authenticity dispute | completed transfers | 0 |
| Repeat transfer @90d | First-time recipients completing another transfer <=90d | first-time recipients cohort | 0 |

## Economics

| Metric | Definition |
|---|---|
| Book value moved | Sum of stated book prices in completed transfers. **Not revenue.** |
| Cash GMV | Subset of the above that actually involved money changing hands. **NOT COMPUTABLE IN v1** - it requires a settled transaction price, and blocker P14 forbids storing one (s194-O, threshold nil). Any v1 report quoting cash GMV is wrong. Asking price x completion is the nearest proxy and is not the same number |
| Platform revenue | Fees we actually collect |
| Contribution margin | Platform revenue minus variable cost per transfer (payment fees, support minutes, infra) |
| CAC | Acquisition spend / verified students acquired by that spend |
| Support load | Support minutes per completed transfer |

**These five are different numbers and are never conflated in any report.**

## Instrumentation note (D-009)

The concierge pilot was cancelled when the founder opened Phase C. Its
measurements are now the app's job, and the schema must make them computable
from the first slice or D-009's mitigation fails silently. The three decisive
ones have query sketches in `architecture/DATA-MODEL.md` §9.2-9.5:

- **Support minutes per transfer** - reported twice, with and without chase
  minutes; the chase-inclusive figure is the pre-registered pass number.
  Rs 2.84/minute, so the 4.00-minute bar is Rs 11.36 and the model needs 2.11.
- **Repeat transfer at 90 days** - the real observable for Red Team's O-10,
  and it works only because the pseudonym survives deletion on the tombstone.
- **Match rate** - search-side and request-side limbs, reported separately.

**Search-success rate (R-01) was not measurable by the concierge design** (no
search existed) and becomes measurable for the first time in v1. Human match
rate was only ever an upper bound on it.

**Support must happen in-app.** A published WhatsApp number or phone line
makes support minutes unmeasurable and voids the mitigation above.

## Delivery

| Metric | Definition |
|---|---|
| Slice lead time | Brief issued -> integrated, review and QA green |
| First-pass rate | Slices passing Code Review + QA without rework |
| Escaped defects | Defects found after integration |
| Evidence coverage | % decisions in the log with a cited source |

## Trust & safety

Reports per 1,000 listings · time to moderate · counterfeit/misdescription
confirmed rate · physical-safety incidents (**target: zero; any incident is a
founder escalation**).

## Accessibility & performance

WCAG 2.2 AA violations (target: zero) · p75 LCP on mid-range Android over 3G ·
p95 search latency.
