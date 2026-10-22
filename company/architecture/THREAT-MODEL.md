# THREAT-MODEL.md — BookHop v1

**Owner:** cto · **Version:** v1.0 · **Date:** 2026-10-21
**Method:** STRIDE per trust boundary, then a named-threat pass over the eight
risks the brief and the risk register actually identify. Mapped to **OWASP
ASVS** (https://asvs.owasp.org/).
**Depends on:** ADR-001 · ADR-002 · ADR-003 · `DATA-MODEL.md` ·
`API-CONTRACT.md`. **Inputs:** `risks/RISK-REGISTER.md` R-05, R-06, R-16, R-18,
R-26 · `COMPLIANCE.md` §1.5, §5.1–5.3, §5.5 ·
`INCORPORATION-AND-BLOCKERS.md` §4.1.

---

## 1. ASVS level, and why

**Target: ASVS Level 1 in full, plus a named subset of Level 2. Level 3 is not
attempted and will not be claimed.**

The honest reasoning. ASVS L1 is the baseline for any application; L2 is "for
applications handling sensitive data" and is clearly the *right* target here —
BookHop holds adults' identity and contact data, private chat, and
**safety-incident reports**, which is the most sensitive data in the system and
the reason a breach would matter to a real person rather than to a balance
sheet. But L2 in full includes requirements a solo developer at pilot scale
cannot *evidence* (a documented secure SDLC, threat-modelling of every feature,
dependency provenance verification, formal key management). Claiming L2 and
half-doing it is worse than claiming L1 and exceeding it, because the claim is
what a reviewer at G4 relies on.

So: **L1 complete, and L2 fully for the chapters where the data actually
lives.**

| ASVS chapter | Target | Why |
|---|---|---|
| V1 Encoding & sanitization | **L2** | Listings and chat are user-generated content rendered to other users. Stored XSS is the cheapest way to take over an account here. |
| V2 Validation & business logic | **L2** | The transfer state machine *is* business logic, and double-booking is a business-logic flaw, not a memory one. |
| V3 Web frontend security | **L2** | CSP, cookie attributes, CSRF, clickjacking. Cheap and mostly framework defaults. |
| V6 Authentication | **L2** | Magic links and staff 2FA. A magic link has its own failure modes (§5.5). |
| V7 Session management | **L2** | Rotation on login, absolute and idle timeouts, server-side invalidation. |
| V8 Authorization | **L2** | Campus scoping, the discovery gate, staff roles. **This is where the legal gate lives, so a bypass here is a legal exposure, not just a bug.** |
| V9 Self-contained tokens | L1 | We have none. Session cookies are opaque server-side references by design. |
| V10 OAuth / OIDC | n/a | Not used. |
| V11 Cryptography | **L2 for data at rest and in transit**, L1 elsewhere | argon2, TLS 1.2+, salted hashes. **No custom crypto.** |
| V12 Secure communication | **L2** | TLS everywhere, HSTS, no mixed content. |
| V13 Configuration | **L2** | Secrets outside the repo, debug off, minimal exposed surface. |
| V14 Data protection & privacy | **L2** | The whole of `DATA-MODEL.md` §10. This chapter and the DPDP work are the same work. |
| V15 Secure coding & architecture | L1 | **Gap, stated.** No formal SDLC. Compensated by Code Review + Test & QA charters and the CI guards. |
| V16 Security logging & error handling | **L2** | Required anyway by CERT-In's 6-hour clock and DPDP r.6(1)(c). |
| V17 WebRTC | n/a | Not used. |

**Declared gaps**, so they are not discovered at G4: V15's SDLC requirements,
formal key management (we have one secret store: environment variables on one
box, documented in `INFRA.md`), and dependency provenance beyond pinned hashes.
These go into the G4 go/no-go packet as known, accepted, pilot-scale gaps.

---

## 2. Assets, ranked by what it costs us to lose them

1. **Safety-incident records and the identities in them.** A leak here is a
   physical-safety harm to a student, and `METRICS.md` makes any incident a
   founder escalation. Highest sensitivity, smallest row count.
2. **Student contact data (email) and chat content.** The harvesting target
   (§5.4), and the thing a campus would judge us on.
3. **The audit trail, consent records and age-verification events.** If these
   are not trustworthy, every compliance position collapses at once.
4. **The measurement data** (`transfer_events`, `support_work_log`,
   `search_events`). D-009 made the app the instrument; corrupt this and the
   company makes decisions on fiction.
5. **Availability of the takedown path.** Being unable to act for three hours
   is a safe-harbour problem, not an inconvenience.
6. Listing catalogue and `books` — low sensitivity, real scraping value (§5.6).

**Not an asset, because it does not exist:** money, payment credentials,
balances, PAN, Aadhaar, DOB, addresses, precise location. **The single largest
security win in this architecture is the data we decided not to hold** — most
of ADR-003 reads as tax and payments compliance, and it is also the threat
model's biggest control.

---

## 3. Trust boundaries

```
 (B1) Internet ──────────► nginx (TLS, rate limit, static)
                              │
 (B2)                         ▼
       Anonymous user ──► Django: public routes only
                          (/legal/*, /auth/start, /grievance, /legal/copyright-notice,
                           /healthz, /readyz, /manifest, /sw.js)
                              │
 (B3) authenticated session, campus-scoped
       Student ──────────► Django: student routes  ──► L1 services ──► Postgres
                              │                           │
 (B4) staff session + TOTP    │                           │
       Staff ─────────────► Django admin ─────────────────┘
                              │
 (B5) the discovery gate (ADR-002 §4): campus.discovery_enabled_at
       — a boundary between "code is live" and "real students see each other"
                              │
 (B6) the box itself: SSH, systemd, filesystem, postgres superuser
       Founder / operator ──► shell
                              │
 (B7) outbound to processors: transactional email (SES), push endpoints
```

**B5 is the unusual one and it is the most important.** It is not a security
boundary in the ordinary sense — crossing it does not breach confidentiality.
It is a **legal** boundary: crossing it before incorporation makes BookHop an
e-commerce entity that does not legally exist. It is in the threat model
because the failure mode is the same shape as a security failure (an
unauthorised state change with a serious external consequence) and it needs
the same controls: a default-closed flag, a server-side guard, an
evidence-gated command, an append-only authorisation row and a test.

---

## 4. STRIDE per boundary

### B1/B2 — Internet to the public surface

| | Threat | Control | ASVS |
|---|---|---|---|
| **S** | Spoofed grievance or copyright notice to force a takedown of a competitor's or an enemy's listing | Notices are **reviewed by a human before action**; `legal_notices` requires `complainant_authority` and, for r.75, the **undertaking to sue in 21 days**; automatic restoration at 21 days if no court order (`DATA-MODEL.md` §7). Takedown is never automated from an unauthenticated form | V2 |
| **T** | Tampering in transit | TLS 1.2+, HSTS, no mixed content | V12 |
| **R** | "I never filed that notice" | `audit_log` hash chain + `X-Request-Id` + IP on every public POST | V16 |
| **I** | Account enumeration via `/auth/start` | **Always 202, whatever the address** (`API-CONTRACT.md` §5.1). Identical timing: the email is sent by a job, so the response time does not vary with whether the account exists | V6 |
| **I** | Listing catalogue indexed by search engines | `robots.txt Disallow: /`, `X-Robots-Tag: noindex`, **and no unauthenticated listing route exists at all** | V8 |
| **D** | Request flood | nginx connection limits + per-IP rate limits (`API-CONTRACT.md` §2.4); a single box, so a determined flood wins — **accepted at pilot**, mitigated by the provider's network and by the fact that nobody has a reason to | V13 |
| **E** | Reaching a student or staff route unauthenticated | Deny-by-default: routes are explicitly marked public; `tests/api/test_auth_matrix.py` enumerates every route and asserts the expected status for anonymous / student / wrong-campus / staff | V8 |

### B3 — Authenticated student

| | Threat | Control | ASVS |
|---|---|---|---|
| **S** | Session theft / fixation | `HttpOnly`, `Secure`, `SameSite=Lax`; session **rotated on login**; idle 14 d, absolute 30 d; server-side invalidation on logout and on erase; one magic link = one session | V7 |
| **T** | Changing a listing's price after an offer | **Database trigger** makes `asking_price_paise` immutable (ADR-003 §2.2). Not a permission check — a constraint | V2 |
| **T** | Forcing an illegal transition (e.g. `OFFERED → COMPLETED`) | One endpoint per transition, guard list in `DATA-MODEL.md` §6.2, `422 TRANSITION_NOT_ALLOWED`; `transfer_events` written in the same transaction so state and history cannot disagree | V2 |
| **R** | "I never agreed to that handover" / "I never confirmed" | `transfer_events` append-only with actor pseudonym and `request_id`; `consents` append-only against an immutable notice version | V16 |
| **I** | Reading another campus's or another user's data by ID | `scoped()` on every read, **404 not 403** for out-of-scope objects so existence is not confirmed; object-level ownership checks in L1 | V8 |
| **I** | Stored XSS in a listing title or chat message to steal a session | Django autoescaping; **no `|safe`, no `mark_safe` on user content — Code Review rejects both**; strict CSP (`default-src 'self'`, no inline script, nonce for the one bootstrap script); `HttpOnly` cookie means even a successful XSS cannot read the session | V1, V3 |
| **D** | One user filling the campus with listings / offers / reports | Per-user daily caps (`API-CONTRACT.md` §2.4); `business_seller_flag` exists for the volume case | V2 |
| **E** | Student reaching a staff screen | Role checked in L1, not only in the admin; admin requires `is_staff` **and** a confirmed TOTP device | V8 |

### B4 — Staff

Covered in full as a named threat in §5.8 — it is the one where the controls
are weakest and the blast radius largest.

### B5 — The discovery gate

| | Threat | Control |
|---|---|---|
| **T** | Gate opened without the legal preconditions | `discovery_enabled_at` defaults NULL; opened only by `manage.py open_discovery`, which **refuses unless every evidence field in `gate_authorisations` is present** (CIN, INC-20A, grievance officer, notices, counsel ref, SOP ref, rota ref, breach rehearsal, MoU) and a named human is recorded |
| **T** | Real listings leak into a pre-gate discovery response | Query is additionally `AND (:gate_open OR is_seed)`; `CHECK (seller_is_seed = buyer_is_seed)` on transfers; `tests/unit/test_gate.py` asserts a non-seed listing is never returned on a closed campus |
| **R** | "Who opened the gate?" | `gate_authorisations` append-only with `authorised_by_human` |
| **E** | Someone flips the flag with SQL | **Not prevented.** Only §5.8's controls apply. Stated plainly rather than papered over |

### B6 — The box

| | Threat | Control | ASVS |
|---|---|---|---|
| **S** | SSH compromise | Key-only auth, no password, no root login, non-standard port, fail2ban, firewall to 22/80/443 only; Postgres bound to localhost | V13 |
| **T** | Silent modification of the audit chain | `audit_log` hash chain, verified by `manage.py verify_audit_chain`; **the daily digest email prints the chain head**, which puts a copy outside the box at zero cost | V16 |
| **I** | Backup theft | Dumps encrypted with `age`/GPG **before leaving the box**; the key is held by the founder, not on the server | V11, V14 |
| **D** | Disk full (media, logs, jobs) kills the app | `logrotate`, media quota alarm at 70%, `readyz` fails on low disk, uptime monitor pages | V13 |
| **R/E** | Operator actions off-platform | Shell history + `audit_log` for anything done through `manage.py`. **Direct `psql` is invisible** — accepted, named, and the reason §5.8's controls are mostly procedural |

### B7 — Processors

| | Threat | Control |
|---|---|---|
| **I** | Email provider sees personal data (addresses, names, notification content) | **It is a Data Processor and needs a signed DPA** (DPDP r.6(1)(f), Gate B15). Notification bodies are kept minimal — "you have a new offer", never the counterparty's details |
| **I** | Push endpoint sees payload | Web Push payloads are **encrypted to the subscription's own keys**; the push service sees ciphertext |
| **S** | Spoofed mail from our domain | SPF, DKIM, DMARC — a one-off DNS task in `INFRA.md` |
| **T** | A compromised dependency exfiltrates data | Pinned versions with hashes; the dependency list is nine packages (ADR-001 §2.8); **adding one is a Code Review conversation and, if it touches personal data, a founder signature** |

---

## 5. The eight named threats

These are the ones the brief and the risk register actually name. STRIDE above
is the sweep; this is the part that matters.

### 5.1 Listing fraud — a listing for a book the seller does not have

**Why it is survivable here, and the one thing that makes it so:**
inspect-before-pay. No money moves before the buyer holds the book, so the
worst case is a wasted trip, not a loss. That is why `COMPLIANCE.md` §2.4(ii)
calls it *"the single highest-leverage compliance and trust mechanism available
to us, and it costs nothing"*.

Controls: adult + campus verification before listing; `seller_terms_acceptances`
(r.5(2) accuracy undertaking) refused ⇒ no listing; `NO_SHOW` and
`CANCELLED` are recorded per pseudonym and visible to staff; `reports` with
category `MISDESCRIBED`; the handover flow makes inspect-before-pay an explicit
step with its own copy.

**Deliberately absent:** a seller trust score. It would be the obvious control
and it is the wrong one at this stage — R-16 and `COMPLIANCE.md` §2.5 are clear
that the more we appear to vouch, the more we may own, and a score computed on
single-digit transfers is noise presented as authority. **Pattern detection
stays with staff until there is data to justify a signal, and the signal needs
counsel C6 first.**

### 5.2 Counterfeit and pirated books — **the highest-probability content risk (R-05, R-26)**

`COMPLIANCE.md` §5.3: pirated textbooks are *"a when, not an if"*, and R-26
records that cutting general reading **concentrated** the risk onto exactly the
category where photocopies live. `TEST-1` kill condition K7 stops at 3+ pirated
books.

**Prevention at listing time, because a 36-hour takedown is the expensive
path:**
1. **ISBN-13 required** (checksum-validated) — a photocopy of a course pack
   usually has no ISBN to give.
2. The seller undertaking explicitly prohibits photocopied, scanned,
   spiral-bound and unauthorised-reprint copies, accepted per version and
   logged.
3. `suspect_reproduction_flag` → `PENDING_REVIEW` → human review, with
   `LISTING_REVIEW_ALL=true` at pilot so **everything is reviewed**.
4. The seller policy states the honest framing: **reselling a legitimately
   purchased physical copy is not infringement** (s52(1)(a), exhaustion); the
   exposure is unauthorised reproductions.

**Response, with the right clock on each** (`DATA-MODEL.md` §7):
court/government order **3h**; NCII/impersonation **2h**; compliant r.75
copyright notice **36h** then a **21-day hold** with automatic restoration if
no court order; acknowledge everything in **24h**; dispose in **7d**; preserve
removed content **180 days** (r.3(1)(j)); **`repeat_infringer_records`
(r.5(5)) survives account deletion**.

**Honest limit:** `COMPLIANCE.md` grades HIGH uncertainty on *"how a platform
distinguishes a legitimate used copy from an unauthorised reprint from a
photograph"*. We do not solve that. We make it reportable, reviewable and
fast to remove, and we require an ISBN. No image classifier — it would be a
dependency, a training-data problem and a false-confidence generator.

### 5.3 Handover safety — **the one that can hurt a person (R-06)**

`COMPLIANCE.md` §5.5: s79 safe harbour covers third-party *information*, not
offline harm.

Controls: **curated `handover_points` only** — public campus landmarks,
`daylight_only` by default, no free-text addresses anywhere; no address or
precise location is collected, so none can be leaked; blocks prevent an offer
in either direction; `safety_incidents` is a separately permissioned table and
**any row enqueues a founder escalation**; `minor_involved` surfaces the POCSO
mandatory-reporting duty as a required next step.

**The copy control is a security control here.** Eight words are forbidden —
*safe · verified · guaranteed · protected · assured · trusted · certified ·
authentic* — enforced per §6.1, which is a different mechanism in each script
and explains why. `INCORPORATION-AND-BLOCKERS.md` §4.1 is exact about the
reason: *"Guidance is protective. A guarantee is an assumed duty of care."*
Making this a failing test rather than a style guide is the only way it
survives twenty template changes — **and §6.1 is the admission that until the
Tamil manifest exists, the test only covers one of the two languages.**

### 5.4 Contact-data harvesting

**The attack:** register, browse, and scrape student names and emails — either
to spam the campus or to build the WhatsApp group that disintermediates us
(R-02).

Controls: **no email, phone or address appears in any response** —
contract-tested against the response schema, not just the database
(`API-CONTRACT.md` §5.2). A listing shows display name, campus and pseudonym.
Messaging is platform-mediated and exists only between a buyer and a seller on
a specific listing — there is no DM, no user-search, no member directory.
Contact disclosure is a **reviewed, logged, two-person** decision
(`contact_disclosures`, with `approved_by_id <> requested_by_id` as a database
CHECK). Signup requires an institutional email, so the cost of a scraping
account is a real campus mailbox.

**Honest limit:** a determined student will exchange a phone number in chat.
`contact_pattern_flag` records it; we do not block it, because blocking is
trivially evaded and user-hostile, and because `TEST-1` §4.2 already concedes
that real leakage is not measurable. **Harvesting is contained to what users
choose to tell each other, which is the right boundary.**

### 5.5 Account takeover

**Magic links remove the biggest class of ATO** — there is no password to
stuff, reuse, phish for, or breach (ADR-001 §2.5). What replaces it:

| Magic-link threat | Control |
|---|---|
| Token in a URL leaks via Referer, history, or a shared screen | Single use; **10-minute expiry**; consumed on first use; `Referrer-Policy: no-referrer`; the consume route immediately redirects so the token leaves the address bar |
| Mailbox already compromised | **Unmitigated, and this is the real residual risk.** The account is as strong as the campus mailbox. Accepted at pilot: there is no money and no stored payment instrument to take. Noted as the reason not to add any financial feature without re-opening this section |
| Link pre-fetched by a mail scanner, burning the token | Soft user-agent-family binding is **logged, not enforced** — a hard binding would break webmail. A burned token shows a friendly "request a new link" page |
| Token brute force | 32 bytes of CSPRNG, stored as sha256, rate limited 10/hour per IP on consume |
| Login-link spam to a victim's inbox | 5/hour per email |
| Session fixation | Session rotated on consume |
| Staff ATO | **Password + mandatory TOTP.** A staff account without a confirmed device sees no personal data |

### 5.6 Scraping

Discovery requires an authenticated, adult-verified, campus-verified session
**and** an open gate. No unauthenticated listing route exists. `limit ≤ 50`,
cursor pagination with a 24-hour cursor expiry, 60 searches/min per session,
`noindex` everywhere, and `search_events` records every query so a scraper
looks obviously different from a student. A scraping session is suspendable in
one staff action.

**Residual, named:** a logged-in student can page through their own campus's
listings. That is the product working. **At one campus the catalogue is a few
thousand rows of public book metadata and asking prices — losing it costs us
very little, and no personal data travels with it.**

### 5.7 Abuse of the report system

Two directions, and conflating them is how platforms get this wrong.

**(a) Weaponised reporting** — mass-reporting a rival's listing to get it
removed. Control: **no report ever auto-removes anything.** Every removal is a
`moderation_actions` row by a named staff member with a `legal_basis`. Reports
per reporter are counted, and a reporter whose reports are repeatedly
`outcome='NO_ACTION'` is visible in the queue. 10/day per reporter.

**(b) Suppressed reporting** — the subtler failure, where throttling or
friction stops a real victim reporting. Controls: the limit is per *reporter*,
never per *target*; `SAFETY_INCIDENT` and `NCII_OR_IMPERSONATION` **bypass the
rate limit entirely**; `/grievance` and `/legal/copyright-notice` accept
unauthenticated submissions, so a blocked or suspended user can still
complain; every submission returns a ticket number and a 24-hour
acknowledgement job.

**Design rule for the whole system, derived from (b):** no safety path is ever
rate-limited to zero, and no safety path requires an account.

### 5.8 Admin insider risk — **the weakest area, stated as such**

The honest position: at pilot there are one or two staff accounts, probably
both belonging to the founder, with legitimate access to every student's
contact details, chat and safety reports. **No technical control meaningfully
constrains that**, and claiming otherwise would be theatre. What we do instead
is make every access *visible and attributable*, which is the control that
actually survives one person having all the keys:

1. **`personal_data_access_log`** — every staff view of a profile, chat thread
   or report writes a row with the fields accessed and a purpose
   (DPDP r.6(1)(c): *"visibility on the accessing of such personal data"*).
   **The screen tells the staff member it is logged.** Deterrence is most of
   the value.
2. **`audit_log` hash chain** over every staff action, with the chain head
   **printed in the daily digest email** — so tampering requires reaching the
   founder's mailbox too.
3. **No bulk-export screen** (`API-CONTRACT.md` §7). Extraction is a management
   command on the box.
4. **Two-person rule on contact disclosure**, enforced by a database CHECK
   (`approved_by_id <> requested_by_id`). At one staff member this *blocks*
   disclosure rather than reviewing it — **which is the correct behaviour**: a
   disclosure that nobody independent reviewed should not happen, and the
   right fix is a second reviewer, not a weaker constraint.
5. **Staff TOTP**, so a stolen staff password is not enough.
6. **Role separation exists in the schema** (`STAFF_SUPPORT`,
   `STAFF_MODERATOR`, `STAFF_ADMIN`) even though one person holds all three
   today — because granting the right role to the second hire is then a
   configuration change, not a refactor.
7. **`safety_incidents` is separately permissioned** — `STAFF_SUPPORT` cannot
   read it.

**Residual risk, recorded for the G4 packet:** a `STAFF_ADMIN` with shell
access can read and alter anything, and direct `psql` leaves no application
trace. Only separation of duties fixes it, and separation of duties needs a
second person. **This is a people problem that an architecture cannot solve,
and it should be in the go/no-go packet as an accepted pilot-scale risk rather
than as a solved one.**

---

## 6. Controls that are tests, not intentions

Each of these fails the build. They exist because every one of them is a rule
that a reasonable developer would otherwise break by accident.

| Test | Asserts |
|---|---|
| `tests/unit/test_forbidden_schema.py` | **A whitelist, not a deny-list** (ADR-003 §2.3 W1): `listings.asking_price_paise` is the **only** money column in the database; every other numeric column carries a declared non-monetary suffix; no `%price/amount/value/cost/rate/sum/total%` column exists outside `listings`. Plus the deny-patterns — settled price, **offer/bid/negotiation amounts**, price history, price-derivation, charge components, PAN/Aadhaar, UPI, wallet/balance, **DOB (no exception)**, precise location (outside `handover_points`), addresses |
| `tests/unit/test_frozen_transaction_tables.py` | The full column lists of `transfers`, `transfer_events`, `messages`, `transfer_followups` match the expected lists, and the two `transfer_followups` enums match by value set — so **"no question about money, ever" is a test, not a promise**. `COMPLIANCE.md` §4.3.2 item 8 |
| `tests/unit/test_metric_labels.py` | `asking_price_sum_paise` is never rendered or exported without *"sum of asking prices of books that changed hands — not a sale value and not revenue"*. §4.3.2 item 9 |
| `tests/unit/test_flag_resets_with_body.py` | `messages.contact_pattern_flag` is reset in the same statement that sets `body_purged_at`, unless an open report preserves it — no conclusion retained after its evidence is purged. `COMPLIANCE.md` §7 row 22 |
| `tests/unit/test_no_dob_persisted.py` | Submitting an age declaration writes **no** DOB to any table or log — asserted by scanning every column of every table for the submitted date. CG-5 |
| `tests/unit/test_forbidden_copy.py` | **English** (`en`): no template or `.po` entry contains a banned stem as a whole word outside the exception manifest. §6.1 |
| `tests/unit/test_reviewed_locale.py` | **Tamil** (`ta`): every shipped `msgstr` hash-matches a reviewer-signed entry in `locale/ta/REVIEWED.toml`. §6.1 |
| `tests/unit/test_locale_gate.py` | `feature_flags['i18n.ta_enabled']` **cannot be true** while any blocking-class `msgid` is unreviewed. §6.1 |
| `tests/api/test_locale_gate_middleware.py` | With the flag false, **`Accept-Language: ta` yields English on an L3 page AND on an L2 endpoint** — the L2 half is what a `web/` view helper structurally could not cover. §6.1 ruling, 2026-10-22 |
| `tests/unit/test_price_immutable.py` | The `listings_price_immutable` trigger exists and raises |
| `tests/unit/test_gate.py` | A non-seed listing is never returned for a campus with `discovery_enabled_at IS NULL`; **and for an `active=false` campus whose gate is open** (QA-S0 B1) |
| `tests/unit/test_gate_write_guard.py` | **`Campus.objects.update(discovery_enabled_at=…)` cannot open the gate** without a live unrevoked `gate_authorisations` row — the trigger, not a grep. QA-S0 F3 / REVIEW-S0 M0 |
| `tests/unit/test_gate_evidence_typing.py` | `breach_rehearsal_at="not yet"`, `cin` of the wrong shape, a future `inc20a_filed_at`, `notice_version_ids=["none"]`, a placeholder reference and `authorised_by_human="agent"` each **refuse to open the gate**. QA-S0 B2 |
| `tests/unit/test_scoping.py` | Every tenant-scoped model has `campus_id`/`city_id` NOT NULL and a leading index; **every `is_seed` model's default manager is the gated one, `Meta.base_manager_name` is `all_objects`, and `all_objects` appears only in allow-listed call sites** (ADR-002 §2.3) |
| `tests/contract/test_p14.py` | **The whitelist, by type as well as name**; the widened money-token set over **every** table; **no money-shaped model field, property, serialiser key or response key in `apps/**`**; and `apps/core/p14.py` matches ADR-003 §2.3 so the control cannot drift from its spec. QA-S0 F1/F2 |
| `tests/unit/test_forbidden_response.py` | **No response anywhere carries a forbidden key, a money-shaped key, a contact detail or an amount.** ADR-003 §5.3's compensating control — **owner: backend, S1** |
| `tests/contract/test_migration_guards.py` | **Replaces a test I specified that cannot be written** (QA-S0 F9; ADR-001 §2.2 correction). Not "the flush GUC is unset in production" — **no mechanism can make production refuse a `SET`**. What is testable, and is: the escape is **default-deny** (two-arg `current_setting`, `= 'yes'`, NULL falls through to the exception); it appears in **exactly one** plpgsql body, so UPDATE and DELETE have no escape; and every `ENABLE ALWAYS` names a trigger the migrations create |
| `tests/unit/test_p14_conformance.py` | **Every control ADR-003 §5.3 names exists in the repository** — so §5.3 cannot claim a control the code does not have. QA-S0 F4/F5 |
| `tests/api/test_auth_matrix.py` | Every route × {anonymous, student, wrong-campus student, unverified student, staff} returns the expected status |
| `tests/api/test_double_booking.py` | N concurrent accepts ⇒ exactly one success |
| `tests/api/test_idempotency.py` | Replay returns the stored response; same key + different body ⇒ 409 |
| `tests/api/test_system_transitions.py` | A user cannot invoke a SYSTEM-only transition |
| `tests/e2e/test_deletion.py` | `DATA-MODEL.md` §10.3's seven assertions, **written by test-qa independently** |
| `tests/e2e/test_sla_clocks.py` | Each report/notice category gets the right `act_due_at`; the 21-day hold restores |
| `tests/a11y/` | WCAG 2.2 AA on every page, keyboard-only and automated, in EN and TA |

### 6.1 Banned-vocabulary enforcement across scripts — the ruling on design TR-8

**Design Director's finding is accepted, and the diagnosis is sharpened: this
is not a Tamil problem. It is a deny-list problem that Tamil made visible.**

The control as frozen in v1.0 greps English only, so **a Tamil string that
warrants would pass the test clean** — a control reporting green over a live
exposure, and the exposure is the vouching liability `COMPLIANCE.md` §2.5 and
R-16 identify as our worst asymmetry. Design is also right that the fix is not
a longer word list, and for two reasons that no word list can resolve:

1. **Morphology defeats stems.** `பாதுகாப்பு` (protection, noun) ·
   `பாதுகாப்பான` (safe, adj.) · `பாதுகாக்கப்பட்ட` (protected, participle) share
   a stem. A stem match catches all three **and** catches the data-protection
   vocabulary the privacy notice is **legally obliged** to use. A ban broad
   enough to work breaks compliance copy; one narrow enough not to, misses.
2. **The banned concept is subject-dependent.** `சரிபார்` carries both *we
   verified* (banned) and *you check* (**required**). In English the subject
   keeps them apart; `BookHop சரிபார்க்கவில்லை` ("BookHop has not verified") is
   a **required** string containing the banned concept, negated. A matcher that
   is blind to voice and negation cannot rule on it.

**And English has the same defect, just less visibly.** "data protection"
contains *protect*; a report category a student picks could legitimately read
"I felt unsafe". v1.0's test would have had to be weakened on first contact
with the privacy notice. So one mechanism is designed for both.

#### The decision — two different controls, because there are two different threats

| | English (`en`) | Tamil (`ta`) |
|---|---|---|
| **Threat** | A developer **authors** a warranting string | An **unreviewed** string ships |
| **Control** | **Deny-list**, whole-word, + exception manifest | **Allow-list**: reviewed-hash manifest |
| **Why** | Vocabulary is open; the author can be trusted to recognise a flagged word | Vocabulary is closed (two `.po` files we write) and morphology makes a deny-list unsound |

**(a) English — deny-list, three changes from v1.0.**
- **Whole-word matching with word boundaries**, not substring. This is what
  makes "unsafe" and "protection" tractable.
- **The banned set grows from five to eight**, adopting Design's list:
  **safe · verified · guaranteed · protected · assured · trusted · certified ·
  authentic** (`JOURNEYS.md` Appendix A), with their inflections enumerated
  explicitly rather than by stemming.
- **`locale/FORBIDDEN_EXCEPTIONS.toml`**: `msgid` → one-line reason → reviewer.
  A banned word may appear only in a listed msgid. The privacy notice's
  "data protection" and any student-voice report label live here, by name.

**(b) Tamil — an allow-list, which is the part that is actually new.**
`locale/ta/REVIEWED.toml`, one entry per `msgid`:

```toml
[run.why_email]
sha256   = "…"            # of the exact approved msgstr
reviewer = "<native speaker's name>"
reviewed = "2026-11-__"
class    = "blocking" | "standard"
notes    = "TR-1: சரிபார் used for the STUDENT's action; subject is the student"
```

**`test_reviewed_locale.py` fails the build if any shipped `ta` msgstr's hash
is absent from the manifest or does not match.** Editing a reviewed Tamil
string therefore breaks the build until it is re-reviewed, which is the
property we want: **the control is on review, not on vocabulary**, so it is
immune to both morphology and negation.

The narrowed Tamil word list, when the native speaker provides it, still goes
in — but **as a reviewer aid, not a gate**: a hit on a Tamil banned candidate
raises a warning that must be acknowledged in the entry's `notes`, and a hit on
an already-reviewed, hash-matching string is **permitted**, because the
reviewer has already ruled on it. That is how `BookHop சரிபார்க்கவில்லை` ships
and `சரிபார்க்கப்பட்ட` does not.

> **RULING · the locale gate belongs in MIDDLEWARE, not in a view helper ·
> cto, 2026-10-22** *(frontend S1 escalation)*
>
> **Frontend found a real leak and closed it correctly.** `LocaleMiddleware`
> negotiates against `settings.LANGUAGES`, **which lists `ta`** — so without
> intervention the gate leaks through `Accept-Language`, which §6.1(c) below
> forbids by name. Frontend re-activates the locale in its own page helper.
> **That works, and it is enforced in the layer that happened to notice.**
>
> **It belongs one layer down, for a reason that is not tidiness: a view helper
> in `web/` covers only the pages that call it.** §2.1 of
> `API-CONTRACT.md` makes `Accept-Language` select the locale for **L2** as
> well, and L2 handlers live in `apps/*/api/` and never call a `web/` helper.
> **So the leak is closed on the pages frontend wrote and open on every JSON
> endpoint, now and in every later slice** — and it would reopen on the first
> L3 page that forgets the helper.
>
> **Specification: `LocaleGateMiddleware` in `apps/core/middleware.py`
> (backend), placed immediately after
> `django.middleware.locale.LocaleMiddleware`.** If
> `feature_flags['i18n.ta_enabled']` is false and the active language is not in
> the allowed set, re-activate `en` and set `request.LANGUAGE_CODE`. Roughly
> ten lines, one place, every request.
>
> **`ta` stays in `settings.LANGUAGES`** — removing it would also stop
> `makemessages`/negotiation working for staff and QA when the flag is on, and
> a static setting cannot read a database flag at import time anyway. **The
> flag is the gate; the middleware is where it is applied.**
>
> **The test is the half that matters, because it is what the view helper could
> never have covered:** `Accept-Language: ta` must yield English **on an L3
> page AND on an L2 endpoint**, with the flag false. Added to §6's table.
>
> **The general pattern, which is the third instance this project has hit:
> a control enforced where it was noticed covers only the paths that layer
> sees.** Frontend's instinct was right and its placement was local; the
> escalation is exactly what should have happened.

**(c) The locale gate, made mechanical — which is what was asked for.**
Design's position is adopted as a gate: **Tamil is not offered to students
until a native speaker has signed off the three blocking classes — handover
guidance, every no-warranty string, and the legal and rights flows.** It is
enforced, not promised:

1. `feature_flags['i18n.ta_enabled']`, **default `false`**. Tamil is absent
   from the language switcher and from `Accept-Language` negotiation while it
   is false. **This reuses the existing flag table — no new mechanism.**
2. `test_locale_gate.py` asserts that the flag cannot be `true` while **any**
   msgid whose `class = "blocking"` is missing from `REVIEWED.toml` or
   hash-mismatched. The set of blocking msgids is declared in
   `locale/ta/BLOCKING_CLASSES.toml`, derived from `COPY-DECK.md`.
3. Turning it on is therefore a **data** change gated by a test, in the same
   shape as the campus discovery gate (ADR-002 §4): default closed, opened only
   when named evidence exists, with a named human on the record.

**What stays human, stated so nobody expects a test to do it.**
`COPY-DECK.md` §1.2's grammatical rule — *BookHop's voice may describe a
mechanism, name a fact, or give an instruction; it may never make a prediction
or a judgement about a person, a book, or an outcome* — **is not greppable in
any language.** "You'll be fine" and "Trusted seller" contain no banned word.
That rule is a **Code Review checklist item** (`.claude/agents/code-review.md`
item 10) and the six-row test table in `COPY-DECK.md` §1.2 is the checklist.
The grep catches words; the reviewer catches sentences; **neither substitutes
for the other and the test suite must not be read as covering the second.**

**Ownership, so two agents never touch one file.** `locale/**` including both
manifests is **frontend-developer's** (`TASKS.md` §1); the three tests are
**backend-developer's**; the reviewer is a **named human**, not an agent.
**A diff to either manifest is a Code Review escalation, not a review
comment** — same standing as `test_forbidden_schema.py` (ADR-003 §5), because
adding a hash is functionally granting a sign-off.

**Residual risk, named:** nothing stops an agent writing its own name into
`reviewer` and inventing a sign-off. This is the same class as A1 (admin
insider) and the mitigation is the same — it is attributable, it is in the
diff, and Code Review escalates it. **The manifest makes a fabricated sign-off
visible; it cannot make it impossible.**

### 6.2 Standing rule — a named control must be proved to exist, and proved to run

**Promoted from an observation to a rule on 2026-10-21, because the pattern has
now recurred four times.** In my last pass I said that if it happened once more
I would make it standing. It has.

> **Any control named in `company/architecture/**` must have a conformance test
> asserting (a) that it exists in the repository and (b) that it executes
> within the suite's budget. A document may not claim a control that no test
> can find.**

**The four occurrences, because the rule is only credible with its evidence:**
W1b named 22 money tokens while the guard enforced 15; ADR-003 §5.3 named a
source grep and a response-schema test, **neither of which existed**; ADR-001
§2.2 specified a GUC test that **could not be written at all**; and ADR-002
§4.1(b) read stronger than the floor it guaranteed. **In every case the
document asserted a property instead of requiring a check for it, and in every
case the gap was found by someone else.**

**And the clinching evidence for limb (b), which no specification could have
produced.** On its first execution the new source grep **found two real
collisions**, and the float check it replaced had gone **quadratic — taking the
suite from 9 seconds to 72.** A control nobody had run was simultaneously
**incomplete and slow**, and neither fact was visible from the specification
that described it. **A specification can tell you what a control should do. It
cannot tell you that the control is absent, wrong, or so slow that someone will
eventually delete it to get the suite green.** Only execution can, which is why
limb (b) is in the rule and not an afterthought.

Implemented as `tests/unit/test_p14_conformance.py` for ADR-003 §5.3, and
extended to each further named control as its slice lands.

**Dependency and supply chain:** pinned versions with hashes; `pip-audit` in
CI; nine runtime packages (ADR-001 §2.8); htmx vendored rather than loaded from
a CDN, so no third-party script executes in a page that can read a session.

---

## 7. Incident response

The runbook, the four pre-written communications and the rehearsal requirement
are in **`INFRA.md` §7**, built to `COMPLIANCE.md` §8.6 and the **6-hour
CERT-In clock**, which is tighter than anything in DPDP and therefore governs.

Three things that belong here rather than there:

1. **"Becoming aware" is the clock start and it will be scrutinised.** Every
   detection path — monitor alert, log line, user report, staff observation —
   writes a timestamped `audit_log` entry the moment it fires. We log detection
   before we log diagnosis.
2. **`request_id` is the investigation primitive.** Six hours is not long
   enough to grep blind.
3. **Rehearse once before the pilot opens** (Gate C3). An unrehearsed runbook
   is a document, not a capability, and the rehearsal itself is logged.

---

## 8. Accepted risks — the list someone else must agree to

Written so G4 can accept them explicitly rather than inherit them silently.

| # | Accepted risk | Why accepted at pilot | What would change it |
|---|---|---|---|
| A1 | `STAFF_ADMIN` + shell access is effectively unconstrained | One or two staff; separation of duties needs a second person | A second staff member, or any paid feature |
| A2 | A compromised campus mailbox is a compromised account | No money, no stored instrument, no payment | Any financial feature; or evidence of mailbox compromise on campus |
| A3 | Single box: no HA, a flood or a disk failure is an outage | ~200 users; `INFRA.md` RTO 4h / RPO 24h is proportionate | The 2-hour and 3-hour takedown clocks being missed because of an outage |
| A4 | Pirated-vs-legitimate cannot be told from a photo | HIGH uncertainty in `COMPLIANCE.md` §5.3; we compensate with ISBN + review + fast removal | K7 firing (3+ pirated books) |
| A5 | Contact exchange inside chat is flagged, not prevented | Unenforceable; `TEST-1` §4.2 concedes it | Nothing — this is the right boundary |
| A6 | No ASVS L2 for V15 (secure SDLC) and no formal key management | Solo team; compensated by Code Review, Test & QA and CI guards | A second developer, or a security review requirement from a campus |
| ~~A7~~ | ~~CERT-In "within Indian jurisdiction" on a foreign-owned Indian region~~ | **CLOSED 2026-10-21.** Privacy-compliance confirms the reading and downgrades the uncertainty to **LOW** (`COMPLIANCE.md` §4.3.2's provider decision). **No longer an accepted risk** | — |
| A8 | The gate is bypassable by anyone with **direct database** access | §4 B5; only §5.8's controls apply. **Narrowed 2026-10-21:** it is no longer bypassable from the application's own ORM — ADR-002 §4.1(a) adds a write trigger (QA-S0 F3) | Postgres RLS (ADR-002 §6 step 2) |
| **A11** | **Gate C evidence references cannot be verified by code.** A CIN of the right shape is not a company; a non-placeholder `campus_mou_ref` is not a signed MoU | **The typed fields are validated and `notice_version_ids` are real FKs; beyond those the control is a named human's signature and the fields are a prompt.** ADR-002 §4.1(b) states which is which, and the G4 packet must carry that distinction | Nothing cheap. An uploaded-certificate store would add a vendor, a retention rule and a DPA for an unchanged guarantee |
| **A12** | **P14 is enforced, not guaranteed** — a number can live in free text or a jsonb document, and no schema or source control reads intent. **Worse today than this row implied: as of QA-S0 v2.0 the `@property`, jsonb and free-text residuals have NO automated control, because W1c and `test_forbidden_response.py` are specified but unwritten** | Today: the frozen-table escalation and PRD EX-18, a product rule. **Not code.** ADR-003 §5.3.1 tracks the status and a conformance test stops §5.3 claiming controls the repository lacks | W1c + `test_forbidden_response.py` landing in S1; then counsel C11 at Gate B |
| ~~A14~~ | ~~Five plpgsql bodies never parsed by a server~~ | **NARROWED 2026-10-21 by execution.** `POSTGRES-FIRST-RUN.md` ran all nine items on PostgreSQL 16.15 (commit `09e2323`): six triggers live, all `ALWAYS`, every refusal path exercised and **its message text asserted**. **Text review had meaningfully established two of nine items — the run established the rest, and found two real defects invisible to SQLite** (a dropped audit row under contention reported as a tamper; a session-scoped fixture binding a per-connection GUC). **What text review could not have found, it did not find** | — |
| **A14a** | **The residue: four properties still unexecuted, on tables that do not exist yet** — price immutability (S2), the double-booking index and MVCC on `expected_version` (S4), the metric SQL (S7) | Each has its exact test shape pre-written in `POSTGRES-FIRST-RUN.md` §3, so none is re-derived. **A14 is narrowed, not closed, and the packet must say which** | Their slices |
| **A15** | **The audit chain serialises every append on one row** (`prev_hash UNIQUE`). Budget 12 with jitter; 40 concurrent appenders land | **Decision recorded: the chain stays global** (`DATA-MODEL.md` §8) — per-scope would let an insider delete one campus's whole history while other chains verify clean, a regression against §5.8/A1. **Watched by a leading indicator**: attempts-to-win p99 in the digest, `AuditAppendContention` paging on-call | p99 attempts > 6, any contention error, or the first month of real traffic — then checkpoint anchoring |
| **A13** | A reviewer could add a `gate_authorisations` row with a plausible fake human name | Placeholder check + agent-name deny-list catches the lazy case; the append-only trigger makes the row permanent and attributable | Same answer as A1 and A10 — a second human |
| **A9** | **The banned-vocabulary control covers English only until `locale/ta/REVIEWED.toml` exists.** A warranting Tamil string would pass today | **Mitigated by closing the locale, not by accepting the risk**: `i18n.ta_enabled` defaults false and a test keeps it false (§6.1), so no Tamil string reaches a student while the gap is open. **The risk is accepted only for the window in which Tamil is built but not shipped** | The native-speaker review landing, which converts A9 from an open gap into an enforced control. Design TR-8 |
| **A10** | A reviewer sign-off in either locale manifest could be fabricated by an agent writing its own name | Attributable, in the diff, and a Code Review escalation (§6.1) | A second reviewer, i.e. the same answer as A1 |

---

## Amendment log

| Date | Change | Source | Approved by |
|---|---|---|---|
| 2026-10-21 | v1.0 | — | cto |
| 2026-10-21 | **§6.1 added — banned-vocabulary enforcement across scripts.** English keeps a whole-word deny-list (grown to eight words) plus an exception manifest; **Tamil gets a reviewed-hash allow-list**, because morphology and subject-dependence make a Tamil deny-list unsound. `i18n.ta_enabled` defaults false and a test keeps it false until the blocking classes are signed off. New risks **A9** (English-only coverage, mitigated by closing the locale) and **A10** (fabricated sign-off) | Design **TR-8**, TR-1 | cto |
| 2026-10-21 | §6 gains `test_no_dob_persisted`, `test_frozen_transaction_tables`, `test_metric_labels`, `test_flag_resets_with_body`; `test_forbidden_schema` **inverted to a whitelist** | PRD CG-5 · `COMPLIANCE.md` §4.3.2 | cto |
| 2026-10-21 | **A7 CLOSED** — CERT-In residency confirmed, uncertainty LOW | `COMPLIANCE.md` | cto |
| 2026-10-21 | §5.8 / A1: the **relay** (`DATA-MODEL.md` §6.4) is now the mitigation that stops the common case reaching the two-person rule | PRD AC-M4.1 | cto |
