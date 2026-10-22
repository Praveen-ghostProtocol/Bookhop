# API-CONTRACT.md — BookHop v1

**Owner:** cto · **Version:** v1.0 · **Date:** 2026-10-21 · **Status:** FROZEN
**Frozen means:** backend-developer and frontend-developer implement against
this without negotiating. A change is a cto amendment at the bottom of this
file, announced to both agents before either writes code against it.
**Depends on:** ADR-001 · ADR-002 (the discovery gate) · ADR-003 (no money)
· `DATA-MODEL.md` (which is normative for field names and enums).

---

## 1. The three layers, and who owns which

Because two agents work in parallel and **must never edit the same file**
(`CLAUDE.md` rule 6), the contract has three layers with hard ownership.

| Layer | What it is | Owner | Files |
|---|---|---|---|
| **L1 Service layer** | Plain Python functions. **The real contract.** All business rules, all guards, all DB access, all audit writes. | backend-developer | `apps/*/services.py` |
| **L2 JSON API** | Thin `/api/v1/*` handlers that validate input, call L1, serialise. For the PWA's dynamic parts, for QA's contract tests, and for anything a machine calls. | backend-developer | `apps/*/api/*.py` |
| **L3 HTML routes** | Server-rendered pages and htmx fragments. Validate, call **L1 directly** (never L2 over HTTP), render. | frontend-developer | `web/views.py`, `web/forms.py`, `web/urls.py`, `templates/**` |

**Both L2 and L3 call the same L1 functions.** That is what makes it safe for
two agents to work at once: a rule can only be implemented in one place, and
neither agent can quietly diverge. **Views never touch the ORM.** Code Review
rejects a view that imports a model.

**Progressive enhancement is a contract term, not a preference.** Every L3
route works as a plain HTML form POST with JavaScript disabled. htmx adds
fragment swaps on top. No core flow requires JSON. This is how mid-range
Android over 3G and WCAG 2.2 AA are met (ADR-001 §2.3).

---

## 2. Conventions

### 2.1 Transport, auth, headers

- `https` only; HSTS; `Content-Type: application/json` on L2.
- **Session cookie** `bookhop_session`: `HttpOnly`, `Secure`,
  `SameSite=Lax`, `Path=/`, 14-day rolling expiry, rotated on login.
- **CSRF**: every unsafe L3 and L2 request needs the Django CSRF token
  (`X-CSRFToken` header for L2, hidden input for L3). L2 is cookie-authenticated,
  so it is CSRF-relevant; there are no bearer tokens in v1 and **no public API**.
- `X-Request-Id`: accepted from the client, else generated. Echoed on every
  response, written to `audit_log.request_id` and the access log. **This is the
  identifier a 6-hour CERT-In investigation uses**, so it is never optional.
- `Accept-Language: en | ta` selects the locale; the user's `locale` wins when
  authenticated.

### 2.2 Error shape — one shape, everywhere

```json
{
  "error": {
    "code": "GATE_CLOSED",
    "message": "Listings are not open on this campus yet.",
    "field_errors": { "asking_price_paise": ["Must be 0 or more."] },
    "request_id": "01JB...",
    "retry_after": null
  }
}
```

`message` is already localised. `field_errors` is present only on 400.
**L3 renders the same codes as pages/fragments** — never a raw JSON blob.

| HTTP | When | Example codes |
|---|---|---|
| 400 | malformed or failed validation | `VALIDATION_FAILED`, `ISBN_INVALID`, `IDEMPOTENCY_KEY_REQUIRED` |
| 401 | no session | `NOT_AUTHENTICATED` |
| 403 | authenticated but not permitted | `GATE_CLOSED`, `NOT_ADULT_VERIFIED`, `NOT_CAMPUS_VERIFIED`, `SUSPENDED`, `BLOCKED_BY_COUNTERPARTY`, `WRONG_CAMPUS`, `SELLER_TERMS_NOT_ACCEPTED`, `CONSENT_REQUIRED` |
| 404 | not found **or** not visible to this actor | `NOT_FOUND` — *the same body either way; a 403 would confirm existence and leak the catalogue* |
| 409 | concurrency / uniqueness | `VERSION_CONFLICT`, `LISTING_ALREADY_RESERVED`, `IDEMPOTENCY_KEY_REUSED`, `DUPLICATE_OFFER` |
| 410 | gone (purged or tombstoned) | `GONE` |
| 422 | valid request, illegal state transition | `TRANSITION_NOT_ALLOWED`, `RESERVATION_EXPIRED`, `GUARD_FAILED` |
| 429 | rate limited | `RATE_LIMITED` (+ `Retry-After`) |
| 500 | bug | `INTERNAL` — **never echoes an exception message**; the `request_id` is the only thing the user gets, and it is enough to find the log |

**403 vs 422 is a real distinction:** 403 means *you* may not; 422 means the
*object* is not in a state where this is possible. Clients branch on it.

### 2.3 Pagination — cursor only

```
GET /api/v1/listings?cursor=<opaque>&limit=20
→ { "items": [...], "next_cursor": "eyJ..." | null }
```

`cursor` is base64 of `{sort_value, id}`; `limit` 1–50, default 20. **No
offset pagination** — under concurrent inserts offset skips and duplicates
rows, and the first thing a new listing does is shift every page. A cursor
older than 24 hours is rejected with `400 CURSOR_EXPIRED`.
L3 uses the same cursors in its "Load more" link, which works as a plain
`<a href>` without JavaScript.

### 2.4 Rate limits

Enforced by a DB-backed fixed-window counter (ADR-001 §2.4) keyed as stated.
Exceeding returns `429` with `Retry-After`. Staff endpoints are exempt;
every staff action is in `audit_log` instead.

| Endpoint group | Limit | Key |
|---|---|---|
| `POST /auth/magic-link` | 5 / hour | email |
| `POST /auth/magic-link` | 20 / hour | IP |
| `POST /auth/consume` | 10 / hour | IP |
| `POST /listings` | 10 / day | user |
| `POST /listings/{id}/photos` | 40 / day | user |
| `GET /search`, `GET /listings` | 60 / min | session |
| `POST /offers` | 20 / day | user |
| transfer transitions | 60 / hour | user |
| `POST /transfers/{id}/reschedule` *(A-1)* | capped at **2 per transfer** by the guard, not by a window | transfer |
| `POST /transfers/{id}/relay` *(A-6)* | **1 per transfer per 24h, max 2 per transfer** | transfer |
| `POST /messages` | 60 / hour | user |
| `POST /support/tickets` *(A-2)* | 10 / day | user |
| `POST /support/tickets/{id}/replies` *(A-2)* | 60 / hour | user — **deliberately not 10/day: a daily cap on replies would break a conversation mid-problem, which is the off-platform-support failure we are trying to prevent** |
| `POST /reports`, `POST /grievances` | 10 / day | user **or** IP when anonymous |
| `POST /account/erase` | 3 / day | user |
| everything else, authenticated | 300 / min | user |

**Note on `POST /reports`:** a *low* limit is itself an abuse vector (it lets
one bad actor exhaust a victim's ability to report). 10/day is per *reporter*,
never per *target*, and report-system abuse is handled by review, not by
throttling the target — see `THREAT-MODEL.md` §5.7.

### 2.5 Standing preconditions — TWO stacks, because a right is not a marketplace action

> **Amendment 2026-10-22 (QA erasure pass, P-1). v1.0 of this section was
> headed "every student-facing write" and listed one stack — which, read
> literally, means a student we suspended cannot export or delete their own
> data.** Backend has just wired `require_actor` correctly (it was called by
> nothing, and a suspended student could edit their profile), so **the defect
> is about to harden into behaviour.**
>
> **Export and erasure are statutory rights. Suspension is our own moderation
> action, not a forfeiture of them.** Fixing an authorization bypass by
> denying a data subject their s11 and s12(3) rights would be, exactly as the
> coordinator puts it, **correct in the diff and wrong in the product.**
>
> **And the defect is wider than suspension**, which is why the fix is a
> restructure rather than one exception: preconditions 3 and 4 have the same
> shape. A student who signed up, never completed campus verification and now
> wants their data deleted would be refused erasure by
> `403 NOT_CAMPUS_VERIFIED`. **The stack was written for marketplace writes and
> then declared to apply to every write.**

**Stack M — marketplace actions.** Checked in L1 in this order, so the error
the user sees is the most useful one:

1. authenticated → else `401 NOT_AUTHENTICATED`
2. `status='ACTIVE'` → else `403 SUSPENDED`
3. `adult_verified` → else `403 NOT_ADULT_VERIFIED`
4. `campus_verified` → else `403 NOT_CAMPUS_VERIFIED`
5. required consent purposes granted → else `403 CONSENT_REQUIRED`
   (body names the missing `purpose_key`)
6. object is in actor's visible campus scope (ADR-002 §2) → else `404`
7. **campus discovery gate open** — **on READS that can surface a row the
   actor did not create**, and **not on writes of the actor's own rows**
   (ADR-002 §4) → else `403 GATE_CLOSED`. **Amended 2026-10-22; see below.**
8. idempotency + version checks (§4)

> **RULING · the gate is a READ control. §2.5 precondition 7 was over-broad;
> ADR-002 §4 is right · cto, 2026-10-22** *(QA S2: a real, verified,
> non-seed student creates a listing on a closed campus and gets 201)*
>
> **Two frozen documents contradicted and QA declined to pick — correctly, the
> question underneath is a product question.** You put it exactly right: *is
> the closed gate a statement about what a campus can SEE, or about whether a
> campus is open for business at all?*
>
> **The compliance rationale settles it, and it cuts against the stricter
> reading.** `INCORPORATION-AND-BLOCKERS.md` §3 A0 is explicit about what
> makes us an e-commerce entity:
>
> > *"A private intake form feeding a private spreadsheet that only the
> > operator reads is a record, not a platform — there is no facility on which
> > buyers encounter sellers' goods. **The moment participants can browse each
> > other's listings**, BookHop is operating a platform."*
>
> **A student creating a listing nobody can browse is precisely that private
> intake form.** The r.3(1)(b) trigger is the browsable surface, not the act
> of recording. So the gate is a read control, and **blocking the write
> protects nothing the law asks us to protect.**
>
> **And there is a positive product reason, not merely an absence of
> objection: R-01.** Cold-start liquidity is the top risk in the register —
> *too few books per campus for a first search to succeed.* **If writes are
> blocked until discovery opens, the campus opens with zero listings and the
> first search fails, which is R-01 materialising by design.** Accumulating
> supply behind a closed surface and then opening it is what a staged launch
> *is*.
>
> **Your objection is real and it is a disclosure problem, not a permission
> problem.** A seller whose listing nobody can see has done work that cannot
> yet pay off, and must be told so **at the moment of publishing**, not
> discovered at Gate C: *"Saved. Nobody can see this yet — listings open when
> BookHop launches on your campus."* One string, honest, and it makes early
> sellers first in the queue rather than misled. **Routed to design-director
> as a required string.** The "rules nobody told them about" half is already
> handled: seller terms are accepted **per version** at listing time
> (`seller_terms_acceptances`), so a seller was told the rules they accepted,
> and a later version is a new acceptance.
>
> **Consistency with my ruling three hours ago, since you flagged it:** *the
> discovery gate governs what you can see, never whether you exist.* This is
> the same principle one layer out, and I would have reached the same answer
> had the compliance text pointed the other way only by overriding it — it
> does not, so the two agree.
>
> **The scope of the amendment is narrow, and the counterparty paths stay
> shut.** Permitted pre-gate: **creating a listing, uploading its photos,
> recording a want, and reading your own rows.** Still gated: search, browse,
> any listing detail the actor does not own, the wants index, and
> **`→ OFFERED`, whose guard already requires the gate open or both parties
> seed** — an offer requires having discovered a listing, and you cannot.
>
> **One thing the create flow must not do:** surface any other user's row,
> **including a count** — no *"3 other people are selling this"*. That is a
> read wearing a write's clothing and it is the one way this amendment could
> leak.
>
> **Accepted consequence, named rather than discovered:** Gate C opens onto a
> backlog of listings created earlier, some from sellers since gone quiet.
> Existing copy already covers it — `trust.stale_listing`, *"Listed {n} days
> ago — this may be gone"* — and `listings.published_at` makes the age
> visible. No new mechanism.

**Stack S — self-service rights, safety, and the right to contest.** Checked
in L1:

1. authenticated → else `401 NOT_AUTHENTICATED`
2. **`status <> 'TOMBSTONED'`** → else `401` *(not 403 — the account is gone;
   see `DATA-MODEL.md` §10.1 layer 2)*
3. idempotency + version checks (§4)

**And nothing else. Not `ACTIVE`, not `adult_verified`, not
`campus_verified`, not consent, not the discovery gate.** A right that a
precondition can switch off is not a right.

| Stack | Endpoints |
|---|---|
| **S** | `POST /auth/logout` · `GET /account` · `GET /account/export` (s11) · `POST /account/erase` (s12(3)) · `GET` and `PUT /account/consents/{purpose_key}` — **withdrawal above all** (DPDP r.3(c)(i): as easy as granting) · `POST /account/nominee` (s14) · `POST /account/correction` (s12(1)–(2)) · `PATCH /account` **for `locale` only** · `GET /legal/{kind}` · `POST /grievances` · `POST /reports` where category is `SAFETY_INCIDENT` or `NCII_OR_IMPERSONATION` · `GET /help`, `GET /help/{id}` and **`POST /help/{id}/reply` on the student's own ticket** |
| **M** | Everything else: listings and photos, `book_requests`, search and discovery, offers and every transfer transition, handover and contact disclosure, messages, blocks, non-safety reports, `POST /support/tickets`, and **`PATCH /account` for `display_name`** |

**Three placements that are judgement calls, with the reasoning, because each
could defensibly have gone the other way:**

- **Safety reports stay in S.** `THREAT-MODEL.md` §5.7 already rules that no
  safety path is rate-limited to zero or requires an account. **A suspended
  user may be the one in danger**, and a platform that suspends someone and
  thereby mutes their safety report has built the wrong thing.
- **Replying to their own support ticket stays in S.** **Suspension with no
  channel to contest it is a due-process failure**, and it is also a grievance
  problem: r.3(2)(a) does not carve out people we have sanctioned. They may
  reply to an existing ticket; **opening a new one is in M**, so the channel is
  the appeal rather than a fresh queue.
- **`display_name` is in M while `locale` is in S.** Correction of personal
  data is a statutory right, but **it is not a right to a public-facing handle
  while suspended** — changing the name counterparties recognise is an evasion
  vector after a safety report. The right is to be satisfied by
  `POST /account/correction`, which is in S, staff-reviewed and logged —
  **and that endpoint DOES NOT EXIST YET. See the status note below before
  quoting this reasoning anywhere.**

> **STATUS · `POST /account/correction` is NOT IMPLEMENTED · QA F24,
> 2026-10-22**
>
> **This is rule 9's shape one level up, and it is mine: a document naming a
> control as the reason ANOTHER control is acceptable, with nothing asserting
> the first exists.** §2.5 names the correction route twice — once in the
> Stack S table with its s12(1)–(2) citation, and once as **the justification
> for putting `display_name` in Stack M.** Measured by QA: no route, no
> handler, no slice.
>
> **So today a suspended student cannot change their display name — correctly,
> by the M placement — and cannot use the correction route either, because
> there is none. The correction right currently has no path at all.**
>
> **The M placement stands; what is wrong is that its justification is
> unbuilt.** I am not moving `display_name` to Stack S to close the gap: that
> would trade a missing endpoint for a live evasion vector, and the endpoint is
> small.
>
> **Until the conformance test is green, the `display_name` reasoning above
> may not be quoted as satisfied — in a go/no-go packet, an ADR, or a
> report.** Same mechanism and same reason as ADR-003 §5.3.1: **an absent
> control correctly reported as absent is a known gap; an absent control a
> document claims is a false statement.** QA's two red tests are the correct
> state and must not be skipped to green the suite.
>
> **Slice: S2**, with the other S1 carry-overs — and S2 is the right slice on
> the merits rather than the convenient one. **`display_name` is visible to
> nobody but its owner until listings exist, so the restriction only starts
> costing a student anything in S2 — which is exactly when its justification
> has to be real.**

**The `403 SUSPENDED` body must name what the student can still do** — export,
erase, withdraw consent, reply to their ticket. **A suspension that tells
someone only "no" is the failure this amendment exists to prevent**, and a
response that lists the open doors costs one sentence. Copy routed to
design-director.

---

## 3. Service layer (L1) — the signatures both agents code against

> **§3 IS THE CONTRACT, AND IT HAS NOW DRIFTED THREE TIMES. Procedural fix,
> 2026-10-22.**
>
> S2 found **four reads the interface needs that this section does not name**,
> and **backend shipped all four under different names than frontend
> proposed.** That is the third instance of one pattern: *frontend proposes a
> name, backend ships another, the contract names neither* — after
> `test_forbidden_source.py` and the `INSTITUTIONAL_EMAIL`/`EMAIL_DOMAIN`
> split. **Three times is a process defect, not three accidents.**
>
> **The rule, which is only `CLAUDE.md` rule 6 applied to signatures rather
> than to files: a read the interface needs is a §3 amendment FIRST, then an
> implementation.** "Contracts before parallel work" is not satisfied by a
> contract that the work then overtakes. Neither agent invents a name: frontend
> requests the read, cto names it here, backend implements that name.
>
> **For the four that already exist: backend's shipped names win**, on the
> same reasoning as the `test_forbidden_source.py` ruling — the code is live,
> tests import it, and renaming to match a document that named nothing would
> turn green tests red to no purpose. **Backend supplies the four signatures
> and they are recorded here on receipt**; until then §3 is knowingly short of
> the code, which is a state this section should never be in again.

Abbreviated to signature + raises. Full docstrings live in the code; **these
names and arguments are frozen.** `actor` is always a `User` or the sentinel
`SYSTEM`.

```python
# apps/core/services.py
def assert_discovery_open(campus) -> None                     # GateClosed
def visible_campus_ids(actor) -> list[int]
def scoped(qs, actor)                                          # ADR-002 §2
def flag(key, campus=None) -> bool
def record_audit(actor, action, obj, before=None, after=None) -> None
def enqueue(kind: str, payload: dict, run_after=None) -> int

# apps/accounts/services.py
def request_magic_link(email: str, ip, user_agent) -> None     # RateLimited, EmailDomainNotRecognised
def consume_magic_link(token: str, ip, user_agent) -> User     # TokenInvalid, TokenExpired, TokenAlreadyUsed
def accepted_email_domains(campus) -> list[str]
#   A-17: for the link-sent page (PRD AC-A1.2). Campus configuration, not
#   anybody's attribute. Permitted in a template; never a literal in a .po.
def submit_age_declaration(user, dob: date, ip) -> AgeOutcome  # UnderEighteen  (writes age_verification_events; DOB not persisted if rejected)
def review_age(staff, user, outcome: str, note: str) -> None   # NotPermitted
def grant_consent(user, purpose_key, notice_version, mechanism, ip, user_agent) -> None
def withdraw_consent(user, purpose_key, mechanism, ip, user_agent) -> None
def accept_seller_terms(user, notice_version, ip) -> None
def update_profile(user, *, display_name=None, locale=None) -> User
#   Stack M for display_name, Stack S for locale (§2.5).
def request_correction(actor, *, stated_problem: str) -> DataSubjectRequest
#   s12(1)-(2). Stack S. NOT IMPLEMENTED — S2 (§2.5 status note, QA F24).
#   Creates a data_subject_requests row, kind='CORRECTION', due_at = +7 days,
#   with the text in `stated_problem` — a column added for it (DATA-MODEL
#   A-29). It does NOT reuse `nominee`, which holds a third party's data.
#   Free text, not an enum of correctable fields: staff decide, and an enum
#   here would be a list where a judgement belongs.
#   (The separate `subject` argument in the 2026-10-22 draft is withdrawn:
#    redundant with free text.)
def decide_correction(staff, dsr, *, outcome: str, applied: dict, note: str) -> DataSubjectRequest
#   Staff-only. Applies the correction, writes audit_log and completes the DSR.
def erase_account(user, reason='USER_REQUEST') -> None         # DATA-MODEL §10.1, one transaction
def log_personal_data_access(staff, subject_pseudonym, fields: list[str], purpose) -> None

# apps/catalog/services.py
def find_book_by_isbn(isbn13: str) -> Book | None              # IsbnInvalid
def search_books(q: str, limit: int) -> list[Book]
def create_book(actor, **fields) -> Book                       # DuplicateIsbn
def merge_books(staff, source: Book, target: Book) -> None

# apps/listings/services.py
def create_listing(actor, *, book, asking_price_paise, condition,
                   annotation_level, damage_flags, language, category,
                   intent='SELL',
                   seller_terms_accepted: bool = False) -> Listing
#   SellerTermsNotAccepted, ValidationFailed. The explicit field is recorded
#   2026-10-22: r.6(4)(a)'s prior written contract is accepted AT listing
#   time, so it is an input to this call and not an ambient account state —
#   a seller who accepted v1 terms has not accepted v2 (DATA-MODEL
#   `seller_terms_acceptances`).
def add_photo(actor, listing, upload) -> ListingPhoto          # TooManyPhotos, UnsupportedImage  (strips EXIF, else no row)
def publish_listing(actor, listing, expected_version) -> Listing   # TransitionNotAllowed, VersionConflict
#   AMENDMENT A-4 (CG-4): enqueues `requests.match_scan` on commit.
def withdraw_listing(actor, listing, expected_version) -> Listing
def moderate_listing(staff, listing, action, legal_basis, reason, work_seconds) -> Listing
def create_request(actor, *, book=None, free_text_title=None, course_code=None) -> BookRequest
def close_request(actor, request) -> BookRequest
# Recorded 2026-10-22 under A-21's procedure — backend's shipped names, which
# win because the code is live and tests import them. §3 was short of the code.
def my_listings(actor, cursor=None, limit=20) -> Page
def get_own_listing(actor, listing_id) -> Listing        # NotFound if not theirs
def my_requests(actor, cursor=None, limit=20) -> Page
def seller_block(listing) -> dict
#   {display_name, campus_name, pseudonym, signed_in_with_college_email}
#   The ONLY shape in which a seller's identity reaches a reader. No email, no
#   phone, no address, no domain (§5.2, A-17). `signed_in_with_college_email`
#   is the campus-email trust string and is TRUE only for
#   campus_verifications.method = 'INSTITUTIONAL_EMAIL' (DATA-MODEL §2's
#   ratified spelling) — a boolean, never the domain itself.

# apps/discovery/services.py
def search_listings(actor, *, q=None, isbn=None, course_code=None,
                    condition_in=None, max_price_paise=None,
                    cursor=None, limit=20) -> Page             # GateClosed  (records a search_event)
def record_result_open(actor, search_event_id, listing_id, position) -> None
def get_listing(actor, listing_id) -> Listing                  # NotFound  (404 also when out of scope)

# apps/transfers/services.py
def make_offer(actor, listing, message=None) -> Transfer        # DuplicateOffer, GuardFailed, GateClosed
def accept_offer(actor, transfer, expected_version) -> Transfer # ListingAlreadyReserved(409), VersionConflict
def decline_offer(actor, transfer, expected_version, reason_code) -> Transfer
def propose_handover(actor, transfer, point, window_start, window_end, expected_version) -> Transfer
def agree_handover(actor, transfer, expected_version) -> Transfer   # -> SCHEDULED
def reschedule_handover(actor, transfer, expected_version) -> Transfer
#   AMENDMENT A-1 (CG-1): SCHEDULED -> ACCEPTED. Raises RescheduleCapReached (422)
#   after 2, WindowAlreadyEnded (422) past handover_window_end.
#   Resets reservation_expires_at = now()+48h; does NOT rewrite accepted_at.
def confirm_handover(actor, transfer, expected_version) -> Transfer # sets one side; both -> COMPLETED
#   AMENDMENT A-3 (CG-3): on reaching COMPLETED, in the SAME transaction,
#   closes matching OPEN book_requests (status='FULFILLED',
#   fulfilled_by_transfer_id, closed_at). Never overwrites a FULFILLED row;
#   never touches a free_text_title request.
def relay_to_counterparty(actor, transfer) -> None
#   AMENDMENT A-6: not a state transition. Reopens the listing thread, sends
#   COUNTERPARTY_NUDGE, writes a transfer_events row with
#   reason_code='RELAY_SENT' and from_state = to_state. Writes NO
#   contact_disclosures row. Max 2 per transfer, >=24h apart.
#   Raises RelayCapReached (422).
def report_no_show(actor, transfer, party, expected_version) -> Transfer
def cancel_transfer(actor, transfer, reason_code, expected_version) -> Transfer
def raise_dispute(actor, transfer, category, body) -> Dispute
def resolve_dispute(staff, dispute, resolution, notes) -> Dispute
def answer_followup(actor, transfer, question_key, answer) -> None
def request_contact_disclosure(actor, transfer, justification) -> ContactDisclosure
#   AMENDMENT A-6 adds the guard AC-M4.2 always implied: raises RelayFirst (422)
#   unless 2 RELAY_SENT events exist >=72h apart with no intervening message
#   from the counterparty.
def decide_contact_disclosure(staff, disclosure, outcome, fields, note) -> ContactDisclosure  # TwoPersonRuleViolated
# SYSTEM-only, called by jobs:
def expire_reservation(transfer) -> Transfer
def close_handover_window(transfer) -> Transfer
def classify_leakage(transfer) -> Transfer

# apps/safety/services.py
def file_report(actor_or_none, *, target_type, target_id, category, body, ip) -> Report
def acknowledge_report(staff, report) -> Report
def act_on_report(staff, report, action, legal_basis, reason, work_seconds) -> Report
def dispose_report(staff, report, outcome) -> Report
def record_legal_notice(staff, **fields) -> LegalNotice
def act_on_legal_notice(staff, notice, action, reason) -> LegalNotice
def restore_after_hold(notice, decided_by) -> LegalNotice       # SYSTEM + named human
def file_grievance(actor_or_none, body, external=None) -> Grievance
def record_safety_incident(staff, **fields) -> SafetyIncident   # enqueues notify.founder_escalation
def block_user(actor, target_pseudonym) -> None
def unblock_user(actor, target_pseudonym) -> None

# apps/support/services.py
def open_ticket(staff, *, kind, transfer=None, listing=None, user_pseudonym=None, channel) -> Ticket
# AMENDMENT A-2 (CG-2) -- the student side, which v1.0 of this contract omitted:
def open_ticket_as_student(actor, *, kind, transfer=None, listing=None,
                           body: str, origin_reason_code=None,
                           channel='IN_APP') -> Ticket
#   Guards: §2.5's standing preconditions; the transfer or listing must be one
#   the actor is a party to (else 404); rate limited 10/day.
#   Writes support_tickets(opened_by_student=True) + the first support_messages
#   row, in one transaction.
def reply_to_ticket(actor_or_staff, ticket, body: str) -> SupportMessage
#   A student may reply only to their own ticket (else 404). A staff reply
#   enqueues a SUPPORT_REPLY notification. locale is taken from the author.
def list_my_tickets(actor, cursor=None, limit=20) -> Page
def get_my_ticket(actor, ticket_id) -> Ticket                  # NotFound if not theirs
def start_timer(staff, ticket, bucket) -> WorkLog
def stop_timer(staff, worklog) -> WorkLog
def log_manual_minutes(staff, ticket, bucket, minutes, note) -> WorkLog
def log_batch_match(staff, run_id, total_seconds, transfer_ids: list[int]) -> None  # TEST-1 §3.2 batch rule
def close_ticket(staff, ticket) -> Ticket
#   AMENDMENT A-2: raises NoWorkLogged (422) on a ticket with zero
#   support_work_log rows (AC-H6.6). Closing a spam ticket means logging the
#   0.1 minutes it took to read it -- TEST-1 §3.1's floor, never 0.

# apps/notify/services.py
def notify(user_pseudonym, kind, payload, channels=None, dedupe_key=None) -> None
def set_preference(user, kind, **channels) -> None
def register_push(user, endpoint, p256dh, auth) -> None
```

Every L1 function that mutates: one database transaction, writes its
`audit_log` row (and `transfer_events` row where applicable) **inside** that
transaction, and enqueues notifications **after** commit (`transaction.on_commit`)
so a rolled-back transition never sends an email.

---

## 4. Idempotency and optimistic concurrency

Two mechanisms, two different jobs. Both are required on transitions.

### 4.1 `Idempotency-Key` — for retries of the *same* request

- **Required** on every `POST`/`PATCH`/`DELETE` to L2, and on every L3 form
  POST that causes a state transition (the token is a hidden input, generated
  when the form is rendered). Missing ⇒ `400 IDEMPOTENCY_KEY_REQUIRED`.
- Server stores `(user_id, key, endpoint, request_hash, response_status,
  response_body)`, unique on `(user_id, key)`, 24-hour retention.

**Key format, and the invariant it rests on — amendment 2026-10-21
(REVIEW-S0 §21). The invariant is normative; the rule is its consequence.**

> **An `Idempotency-Key` on an unauthenticated request MUST be a UUID. On an
> authenticated request the format is unconstrained.**
>
> **This asymmetry is deliberate and it rests on one invariant:
> `user_id` partitions the key namespace, and every key in a partition is
> written by that one principal.** An authenticated short key can therefore
> collide only with the same user's own keys — and a collision with a different
> endpoint or body returns `409 IDEMPOTENCY_KEY_REUSED`, while a collision with
> both the same *is* the same request, which is what idempotency is for. The
> anonymous namespace is **global**, which is different in kind, and that is
> why it alone needs the format rule.
>
> **If any endpoint ever writes a key on another principal's behalf, the
> authenticated namespace acquires the anonymous one's property and the UUID
> rule extends to it.** That sentence is the one that matters, because it is
> the invariant and not the conclusion — the conclusion rots silently, the
> invariant stays checkable against a future design.

**Three ways the invariant breaks, all reachable from the current roadmap, so
none of them is hypothetical:**

| Break | Where it arrives |
|---|---|
| **A staff tool acting on a student's behalf** | **S5 support and S6 moderation put staff inside a student's objects.** The moment any endpoint writes an idempotency key under the student's `user_id` on a staff action, that partition has two principals |
| **Any impersonation or service-account path** | Same mechanism, same consequence |
| **`user_id` reuse after purge** | Narrow but real: `ENGINE-DIVERGENCE.md` §2.10 records that SQLite reuses the max rowid once the highest row is deleted, **S1 adds purge**, and the replay window is 24 hours — so a reused id could inherit the previous user's unexpired keys |

**Defence in depth on top of the format rule, which backend added and I did not
require:** an anonymous replay returns the stored status with a **NULL body**,
so **no anonymous caller can receive another's response body even if a key is
guessed.** That matters because the measured disclosure was a `grievance_ref`
reaching a stranger on `/grievances` — the door a distressed non-user reaches
us through.
- **Replay with the same body** ⇒ the stored response is returned verbatim,
  with `Idempotency-Replayed: true`. The handler does not run again.
- **Same key, different body** ⇒ `409 IDEMPOTENCY_KEY_REUSED`.
- A request that is still in flight (row inserted, no response yet) ⇒
  `409 IDEMPOTENCY_IN_PROGRESS` with `Retry-After: 2`. The insert of the key row
  is the lock, so two simultaneous retries cannot both execute.

> **Amendment 2026-10-21 on QA-S0 B3 — anonymous POSTs had no idempotency at
> all, and that is a contract gap, not an implementation defect.** §4.1 as
> frozen makes `Idempotency-Key` required on **every** POST while keying the
> table on `(user_id, key)`. With a NULL `user_id` the unique constraint does
> not fire on either engine, so **a replay claims a second row instead of
> replaying the first.** The contract has four anonymous POSTs:
> `/auth/magic-link`, `/auth/consume` (S1), `/grievances` and the public
> copyright-notice form (S6).
>
> **Ruling, corrected 2026-10-21 — my sentinel was wrong and backend's
> rejection is right.** I specified `(COALESCE(user_id, 0), key)`. The obvious
> reading of that is `user_id NOT NULL DEFAULT 0`, which **breaks the foreign
> key to `users` that S1 adds** — there is no user 0 and there must not be one.
> My own parenthetical offered a separate non-FK column as an alternative, but
> that is an extra column carrying a value derived from another, for a property
> a partial index already gives.
>
> **The specification is backend's implementation: a second, partial unique
> index on `key` alone, `WHERE user_id IS NULL`**, alongside the existing
> `(user_id, key)`. No extra column, no FK violation, one property, two
> indexes.
>
> Anonymous keys therefore share **one global namespace**. That is sound
> because the key is a client-generated UUIDv4: a collision requires guessing
> one, and the consequence of a collision is a `409`, not data loss or
> disclosure. **Keying on IP was also rejected, and rightly — it breaks the
> retry it exists to serve the moment a phone changes network**, which on a
> campus is the normal case rather than the edge case.
>
> **Why not exempt them, which was the cheaper option:** `/grievances` and the
> copyright-notice form are the two paths a rights holder or a distressed
> non-user reaches us on, and `THREAT-MODEL.md` §5.7 rules that **no safety
> path may be rate-limited to zero or require an account.** A double-submitted
> grievance creating two tickets with two separate 24-hour clocks is a
> compliance problem, not a cosmetic one — the acknowledgement SLA would be
> running twice on one complaint. These are exactly the endpoints that need
> idempotency most.
>
> **And the question backend asked that B3 only implies — do anonymous POSTs
> carry a key at all? Yes, and required.** Three points settle it:
> - **For `/grievances` and the public copyright-notice form the answer is not
>   close.** A double-submitted grievance creates two tickets with two separate
>   24-hour acknowledgement clocks running on one complaint. These are the
>   endpoints that need idempotency *most*, and §5.7 forbids a safety path
>   requiring an account, so "authenticate first" is not available.
> - **There is no friction cost.** An L3 form gets a hidden
>   server-generated key at render time, so the student does nothing; only L2
>   callers generate their own.
> - **One precise exemption:** `/auth/consume` in its L3 form is
>   `GET /auth/c/{token}`. A GET carries no idempotency key, and it needs none —
>   **a single-use token is idempotent by construction**, which is the same
>   property by a cheaper mechanism. The L2 `POST /api/v1/auth/consume` carries
>   a key like any other POST.
>
> **Must close before S1 wires the first anonymous endpoint.** S1 ships
> `/auth/magic-link`.

This makes a flaky 3G connection safe: the user taps "Accept" twice, one
transfer is accepted, and both taps see the same answer.

### 4.2 `expected_version` — for *conflicting* concurrent requests

Every transition body carries `expected_version` (L2) or a hidden
`expected_version` input (L3), read from the object the client was shown.

```sql
UPDATE transfers SET state = :new, state_changed_at = now(), version = version + 1
 WHERE id = :id AND version = :expected;
```

Zero rows ⇒ `409 VERSION_CONFLICT`, body includes the current `state` and
`version` so the client can re-render rather than guess. Same pattern on
`listings`.

### 4.3 Double-booking — the database is the guard

Per `DATA-MODEL.md` §5, a partial unique index on `transfers (listing_id)`
over the active states means a second `accept_offer` on the same listing
**cannot** succeed. The service catches the integrity error and returns
`409 LISTING_ALREADY_RESERVED`. There is no application lock, no
`SELECT FOR UPDATE` on the listing, and no race window.
`tests/api/test_double_booking.py` fires N concurrent accepts and asserts
exactly one 2xx and N−1 409s.

### 4.4 Job idempotency

Jobs are at-least-once (ADR-001 §2.4). Every handler is idempotent:
transitions check the current state and no-op if already moved;
`notifications.dedupe_key` is UNIQUE so a duplicate send is a harmless failed
insert; purge is driven by `purge_due_at` and records `purge_log`.

---

## 5. Endpoints

`{id}` is always a bigint. Unless stated, every endpoint requires §2.5's
preconditions. L3 paths are listed beside their L2 equivalent so the frontend
agent knows exactly what it owns.

### 5.1 Auth and account

| L2 | L3 | Notes |
|---|---|---|
| `POST /api/v1/auth/magic-link` | `POST /auth/start` | body `{email}`. **Always returns 202 whatever happens** — a different response for an unknown address is an account-enumeration oracle. Rate limited per §2.4. |
| `POST /api/v1/auth/consume` | `GET /auth/c/{token}` | single use, 10-minute expiry. Rotates the session. On success: 200 with **`{needs: ["age","consent"]}`** so the client knows the next step. **`"campus"` REMOVED 2026-10-22 (QA F22) — it cannot occur**, see below |

> **F22 — `needs: ["campus"]` was an unreachable value, and removing it
> exposes a real gap it was concealing.**
>
> **It cannot occur.** `request_magic_link` raises `EmailDomainNotRecognised`
> for an address outside `campuses.email_domains`, so **no link is ever sent to
> an unrecognised domain** — and consuming a link therefore *proves* the domain
> matched. The magic link **is** the campus evidence (ADR-001 §2.5); that is
> the whole point of the design. A client branching on `"campus"` would be
> writing a screen no student can reach.
>
> **The gap underneath it, which is why this is worth more than deleting a
> string.** `DATA-MODEL.md` §1 says an empty `email_domains` means "no
> self-service signup", and those users are staff-created with
> `campus_verifications.method = 'STAFF_MANUAL'`. **But such a user still has
> no way to sign in** — `request_magic_link` would refuse their address too.
> **So a campus with empty `email_domains` currently has no student sign-in
> path at all**, and the unreachable `needs` value was the only thing in the
> contract that looked like it addressed that.
>
> **Not fixed here, deliberately:** v1 is one campus with a working
> institutional domain, and the trigger for solving it is already written —
> ADR-001 §2.5 says a second campus without usable institutional email is what
> reopens the SMS question. **Recorded so the next person who reads
> `STAFF_MANUAL` does not assume a sign-in path exists for it.**
| `POST /api/v1/auth/logout` | `POST /auth/logout` | |
| `POST /api/v1/account/age-declaration` | `POST /account/age` | body `{date_of_birth}`. **Under 18 ⇒ `403 NOT_ADULT_VERIFIED` and the account is deleted immediately**; `age_verification_events` records the rejection; **the DOB is never persisted** (`DATA-MODEL.md` §2). |
| `GET /api/v1/account/consents` | `GET /account/privacy` | current state per purpose + the notice version |
| `PUT /api/v1/account/consents/{purpose_key}` | `POST /account/privacy` | `{granted: true|false}`. **A toggle, not an email** (DPDP r.3(c)(i)). Appends a row, never updates. |
| `GET /api/v1/account` | `GET /account` | profile |
| `PATCH /api/v1/account` | `POST /account` | `{display_name?, locale?}` |
| `GET /api/v1/account/export` | `GET /account/export` | **s11 access right** — a JSON summary of personal data and processing activities |
| `POST /api/v1/account/nominee` | `POST /account/nominee` | **s14 nomination.** In the Act, built once, nobody else builds it |
| `POST /api/v1/account/correction` | `POST /account/correction` | **s12(1)–(2) correction.** Stack S. Creates a `CORRECTION` data-subject request, 7-day clock, staff-reviewed, logged. **NOT IMPLEMENTED — S2** (§2.5 status note). It is what makes the `display_name` restriction defensible |
| `POST /api/v1/account/erase` | `POST /account/delete` | two-step confirm in L3. Runs `erase_account`. **Response states plainly which records are retained for one year and why** (r.8(3)) — the user learns it here, not from a support ticket |
| `GET /api/v1/notices/{kind}` | `GET /legal/{kind}` | public, unauthenticated. `privacy`, `terms`, `seller-terms`, `community-rules`, **`handover-guidance`** *(renamed — see below)*, **`ranking`**, **`grievance-officer`** — the last composes the `GRIEVANCE_PROCEDURE` notice with the officer fields read from `legal_entities` at render time, never copied into a notice (`DATA-MODEL.md` A-25) |

> **Amendment A-17 (2026-10-22) — `accepted_email_domains` is permitted on the
> link-sent page, and design criterion 7f is narrowed to say so.**
>
> **The defect:** criterion 7f forbids any template interpolating
> `campuses.email_domains`. **PRD AC-A1.2 — which the PRD itself calls *a
> product requirement, not polish* — requires the link-sent page to tell the
> student which domains the campus accepts**, and backend built
> `accepted_email_domains(campus)` for exactly that page. **So the primary
> journey could only work by violating a failable criterion.**
>
> **7f's rationale does not reach this case, and reading the rationale is what
> settles it.** `COMPLIANCE.md` §2.5a is entirely about **a seller's** domain
> appearing on **a listing** — where it is attribute disclosure about an
> identifiable person, dressed as a trust badge. The accepted-domain list is
> **campus configuration: identical for every visitor, about nobody, and
> already public** (it is printed on the institution's own website). There is
> no data subject.
>
> **Narrowed to: no template may render ANOTHER PERSON'S email domain.** The
> second limb is kept exactly as it is — **no domain literal in any string
> file; the value arrives from the service at render time** — which is what
> frontend implemented and is the same rule A-25 applies to the grievance
> officer's contact details.
>
> This is the third time a control has been **broader than its own rationale**.
> The pattern worth naming: **a criterion written from a rationale, without the
> rationale travelling with it, drifts wider than the risk it was written
> for** — and the widening is invisible because the criterion still reads
> protective. **7f's narrowed form must carry its rationale in one line beside
> it**, or the next person restores the broad version.
>
> **Routed to design-director** (criterion 7f and `SYSTEM.md` are not mine to
> edit). The contract position above is normative meanwhile: the route and the
> service function are permitted and specified here.

> **Amendment A-7 — the `handover-safety` slug is renamed to
> `handover-guidance`, and `notice_versions.kind` from `HANDOVER_SAFETY` to
> `HANDOVER_GUIDANCE`.** Design Director's catch (`SYSTEM.md` §7 item 7) is
> accepted rather than accepted-as-a-mismatch, and the reasoning is worth one
> line because the premise was right and the conclusion still goes the other
> way: a slug **is** a route and not copy, so it never broke the grep. But a
> route is read by humans — it sits in the address bar, in a shared link, in a
> footer `href` and in an email — and **an identifier is where a label comes
> from.** A developer reading `HANDOVER_SAFETY` writes "Handover safety" in the
> template, and no test would catch the identifier that suggested it. The
> rename costs nothing today (nothing is built; S1 creates these pages) and the
> mismatch would have to be remembered by every future reader. **Renaming the
> enum too, for the same reason: it is the identifier a label is copied from.**
>
> Scope boundary, so this does not spread: `tests/unit/test_forbidden_copy.py`
> continues to cover **templates and `.po` files only, never identifiers.**
> `safety_incidents`, the `SAFETY_INCIDENT` report category and
> "physical-safety" stay exactly as they are — they are internal or staff-facing
> and the word is accurate there. **The ban is on BookHop promising safety to a
> student, not on the word existing in the codebase.**

### 5.2 Catalogue and listings

| L2 | L3 |
|---|---|
| `GET /api/v1/books?isbn=` · `?q=` | `GET /sell/find-book` (htmx typeahead, degrades to a submit button) |
| `POST /api/v1/books` | part of `POST /sell` |
| `POST /api/v1/listings` | `POST /sell` |
| `POST /api/v1/listings/{id}/photos` | `POST /sell/{id}/photos` — multipart, ≤4 photos, ≤8 MB each, jpeg/png/webp; **EXIF stripped before the row exists** |
| **`GET /media/listing-photo/{photo_id}`** *(added 2026-10-22)* | same path, no L2/L3 split — it serves bytes | **Stack M.** The read that was missing: the storage key existed and nothing served it |

> **The photo route — added because its absence made a criterion vacuous, not
> because a page looked incomplete.**
>
> `listing_photos.storage_key` existed, §5.2 had no `GET`, and **inventing a
> media URL is not the interface layer's to do** — frontend was right to
> refuse. The consequence is rule 10's shape and the reason this is a contract
> fix rather than a nicety: **the criterion forbidding images under a
> data-saver header is currently satisfied because there are no images. It
> must not be reported as passing.** Frontend's page says the honest thing —
> *"The seller attached 4 photos. BookHop has no way to show them yet."* —
> and that stays until this route exists.
>
> **Specification.** A Django view, **not** a public static path:
> - **Gate and scope first**: `assert_discovery_open`, campus scope, and the
>   listing visible to this actor — a photo is as gated as the listing it
>   belongs to, and a guessable media URL would be a side channel around
>   ADR-002 §4 exactly as `match_scan` would have been.
> - **nginx serves the bytes** via `X-Accel-Redirect` to an internal location.
>   Django authorises; it does not stream. The files stay off any
>   publicly-routable path (ADR-001 §2.6).
> - `Cache-Control: private, max-age=86400` · `X-Robots-Tag: noindex` ·
>   `Content-Type` from the stored type, never from the request.
> - **404, not 403**, for a photo outside scope — consistent with §2.2, so the
>   route cannot be used to confirm a listing exists on another campus.
> - EXIF is already absent by construction: `exif_stripped_at` is `NOT NULL`,
>   so no row can exist for an unstripped file (`DATA-MODEL.md` §3).
>
> **Slice: S2**, with the listing surface it completes.
| `POST /api/v1/listings/{id}/publish` | `POST /sell/{id}/publish` |
| `POST /api/v1/listings/{id}/withdraw` | `POST /sell/{id}/withdraw` |
| `GET /api/v1/listings/mine` | `GET /sell` |
| `GET /api/v1/listings/{id}` | `GET /listing/{id}` |
| `POST /api/v1/requests` · `DELETE /api/v1/requests/{id}` | `POST /wanted` · `POST /wanted/{id}/close` |

**Listing responses never contain:** a seller address, a phone number, an
email, precise coordinates, a settled price, or any field in ADR-003 §2.3's
deny-list. A contract test asserts this against the response schema, not just
the database.

Seller identity in a listing response is `{display_name, campus_name,
pseudonym}` and nothing else (`COMPLIANCE.md` §2.4(i)).

### 5.3 Discovery — **gated**

| L2 | L3 |
|---|---|
| `GET /api/v1/search?q=&isbn=&course_code=&condition_in=&max_price_paise=&cursor=&limit=` | `GET /search` |
| `POST /api/v1/search/{search_event_id}/open` | recorded by the L3 listing link |
| `GET /api/v1/listings?cursor=` | `GET /browse` |
| `GET /api/v1/requests?cursor=` | `GET /wanted/all` |

**Every one of these calls `assert_discovery_open(campus)` first** and
restricts to `is_seed=true` when the gate is closed (ADR-002 §4.1). A real
student on a closed campus gets `403 GATE_CLOSED`; L3 renders a page saying
listings open when the service launches, with no listing data on it.

`max_price_paise` filters on the **asking** price. There is no sort-by-price
*descending with a struck-through original* and no "was/now" anywhere
(r.4(13)).

**Ranking** is `published_at DESC` within an exact-ISBN match, then trigram
similarity on title. It is **documented in descending order of significance**
in `/legal/ranking` (r.5(3)(f), r.4(11)(c)) and there is no personalisation
and no promoted placement (r.4(12)).

### 5.4 Offers, transfers, handover — one endpoint per transition

All take `Idempotency-Key` and `expected_version`. All return the full
transfer. All write a `transfer_events` row.

| L2 | Transition | L3 |
|---|---|---|
| `POST /api/v1/offers` `{listing_id, message?}` | → `OFFERED` | `POST /listing/{id}/offer` |
| `POST /api/v1/transfers/{id}/accept` | `OFFERED → ACCEPTED` | `POST /transfer/{id}/accept` |
| `POST /api/v1/transfers/{id}/decline` `{reason_code}` | `OFFERED → DECLINED` | `POST /transfer/{id}/decline` |
| `POST /api/v1/transfers/{id}/propose-handover` `{handover_point_id, window_start, window_end}` | stays `ACCEPTED` | `POST /transfer/{id}/propose` |
| `POST /api/v1/transfers/{id}/agree-handover` | `ACCEPTED → SCHEDULED` | `POST /transfer/{id}/agree` |
| **`POST /api/v1/transfers/{id}/reschedule`** *(A-1)* | **`SCHEDULED → ACCEPTED`**, max 2 | `POST /transfer/{id}/reschedule` |
| `POST /api/v1/transfers/{id}/confirm` | `SCHEDULED|AWAITING_CONFIRMATION → AWAITING_CONFIRMATION|COMPLETED` | `POST /transfer/{id}/confirm` |
| `POST /api/v1/transfers/{id}/no-show` `{party}` | `SCHEDULED → NO_SHOW` | `POST /transfer/{id}/no-show` |
| `POST /api/v1/transfers/{id}/cancel` `{reason_code}` | → `CANCELLED` | `POST /transfer/{id}/cancel` |
| `POST /api/v1/transfers/{id}/dispute` `{category, body}` | → `DISPUTED` | `POST /transfer/{id}/dispute` |
| `POST /api/v1/transfers/{id}/followup` `{question_key, answer}` | no transition | `POST /transfer/{id}/followup` |
| **`POST /api/v1/transfers/{id}/relay`** *(A-6)* | **no transition** — writes a `RELAY_SENT` event, reopens the thread, sends `COUNTERPARTY_NUDGE` | `POST /transfer/{id}/relay` — labelled **"ask BookHop to reach them"**, never "request contact details" (AC-M4.1) |
| `POST /api/v1/transfers/{id}/contact-disclosure` `{justification}` | no transition | `POST /transfer/{id}/contact-request` — **only offered after two relays over 72h** (A-6) |
| `GET /api/v1/transfers/{id}` · `GET /api/v1/transfers?role=buyer|seller&state_in=` | — | `GET /transfer/{id}` · `GET /transfers` |

**The confirm endpoint asks one question: "did the book change hands?"** There
is no amount field on any of these endpoints and no response contains one
(ADR-003 §2.4).

**The handover flow has a mandatory step the backend enforces:** a transfer
cannot reach `SCHEDULED` unless the current `HANDOVER_GUIDANCE` notice version
has been shown to both parties (recorded as a `consents`-adjacent
acknowledgement on the transfer's event log). The copy is guidance, **never a
warranty** — "check the book before you hand over any money", "meet at [named
public point] in daylight". The words "safe", "verified", "protected",
"guaranteed" and "assured" are **forbidden strings** — along with *trusted*, *certified* and *authentic*,
enforced per `THREAT-MODEL.md` §6.1, which uses a **different mechanism per
script** and says plainly that Tamil is gated rather than grepped
(`INCORPORATION-AND-BLOCKERS.md` §4.1, `COMPLIANCE.md` §5.5).

### 5.5 Messaging

| L2 | L3 |
|---|---|
| `GET /api/v1/threads` · `GET /api/v1/threads/{id}` | `GET /messages` · `GET /messages/{id}` |
| `POST /api/v1/threads/{id}/messages` `{body}` | `POST /messages/{id}` |

A thread exists only between a buyer and a seller **on a specific listing**.
There is no open messaging, no user-to-user DM outside a listing, and no
contact detail is ever exchanged by the platform. Messages matching a
phone/email/UPI pattern set `contact_pattern_flag` — **flagged, not blocked**
(`DATA-MODEL.md` §8).

**Staff are never participants in a thread.** That invariant is why support
gets its own tables in §5.5a rather than reusing these.

### 5.5a Support — the student side *(amendment A-2, PRD CG-2)*

| L2 | L3 | Notes |
|---|---|---|
| `POST /api/v1/support/tickets` `{kind, transfer_id?, listing_id?, body, origin_reason_code?}` | `POST /help/ask` | **Contextual entry is a measurement requirement, not a convenience** (AC-H6.1): an unbound ticket lands in `DAILY_UNALLOCATED` and is excluded from the per-transfer median that decides the business. Every transfer, listing and account screen carries "get help with this" and passes the id |
| `POST /api/v1/support/tickets/{id}/replies` `{body}` | `POST /help/{id}/reply` | |
| `GET /api/v1/support/tickets` · `GET /api/v1/support/tickets/{id}` | `GET /help` · `GET /help/{id}` | The student's own tickets, with history. **The student is never told to check their email for the answer** (AC-H6.2) |

Before the form, the L3 surface states what we can and cannot do (AC-H6.5) and
offers the five commonest answers as static copy — **not a CMS, and we do not
measure deflection**; the "this didn't answer it" link carries
`origin_reason_code`, which is the only mis-routing measurement taken.

**No phone number and no WhatsApp number appears anywhere** in the product, the
emails, the notices or any description of the service (AC-H6.4). The statutory
grievance email is published because r.4(2) requires it, and **every message
arriving there is opened as a ticket with `channel='EMAIL'` and timed like any
other** — so those minutes are measured too. Only unlogged WhatsApp is
invisible, which is why none exists.

**No SLA number is promised for help.** Statutory clocks apply to reports,
grievances and disputes and those are stated exactly; help says *"we aim to
reply the same day"* and nothing more (AC-H6.7).

### 5.6 Reports, grievances, takedown — public where it has to be

| L2 | L3 | Auth |
|---|---|---|
| `POST /api/v1/reports` | `POST /report` | authenticated |
| `POST /api/v1/grievances` | `POST /grievance` | **unauthenticated allowed** — a rights holder or a parent is not a user |
| `POST /api/v1/legal/copyright-notice` | `POST /legal/copyright-notice` | **unauthenticated.** Captures r.75's requirements: the work, the infringing location, the complainant's authority, and the **undertaking to sue within 21 days** |
| `GET /api/v1/reports/mine` | `GET /reports` | authenticated |
| `POST /api/v1/blocks` · `DELETE /api/v1/blocks/{pseudonym}` | `POST /block` · `POST /unblock` | authenticated |

Every one of these returns a **ticket number** (E-Com r.5(3)(b)) and triggers
an acknowledgement within 24 hours (r.3(2)(a)(i)) — the acknowledgement is a
job, not a human remembering. The response states the ack and disposal clocks
in plain words.

### 5.7 Staff — Django admin, not a REST API

Moderation, age review, takedown clocks, dispute resolution, support timers
and handover-point curation are all **Django admin screens**, for the reason
in ADR-001 §2.1. They are L1 calls behind admin actions, not L2 endpoints.

Three non-negotiables on every staff screen:
1. Opening a student's profile, chat thread or report detail writes
   `personal_data_access_log` — and **the screen says so to the staff member**.
2. Every action writes `moderation_actions` (with `work_seconds`) and
   `audit_log`.
3. **There is no bulk export screen.** Data extraction is a management command
   run on the box, which is logged by the shell and the audit chain
   (`THREAT-MODEL.md` §5.8).

Staff sign-in requires password **plus TOTP**. A staff account with no
confirmed TOTP device cannot reach any screen that shows personal data.

### 5.8 Operational endpoints

| Path | Auth | Purpose |
|---|---|---|
| `GET /healthz` | none | process liveness. No version, no detail |
| `GET /readyz` | none | DB reachable, migrations applied, last job run < 5 min ago |
| `GET /metricsz` | token | plain-text counters for the uptime monitor |
| `GET /manifest.webmanifest`, `GET /sw.js`, `GET /offline` | none | PWA shell (ADR-001 §2.3) |
| `GET /robots.txt` | none | **`Disallow: /`** — no listing is ever indexed, and every listing page sends `X-Robots-Tag: noindex` |
| `GET /dev/states` | **staff session + TOTP** | **Accepted** (Design `SYSTEM.md` §7 item 8): a gallery of every component in every state, so state coverage is provable instead of argued. Conditions: staff-only via the same guard as the admin, **seed data only — it may not render a real row**, `noindex`, and no write of any kind. It is a view over fixtures, not an escape hatch, and `test_auth_matrix.py` includes it |

**Management commands (not HTTP):** `run_jobs`, `open_discovery`,
`close_discovery`, `retention_purge`, `export_metrics`, `verify_audit_chain`,
`restore_check`, `seed_demo`.

---

## 6. The transaction state machine

The normative diagram, the eleven states, every transition with its guard, and
the SYSTEM timers are in **`DATA-MODEL.md` §6.2**. It is there rather than
duplicated here because the states are columns and the transitions are rows in
`transfer_events`; two copies would drift.

What belongs here is the **endpoint-to-transition mapping (§5.4)** and these
four contract guarantees:

1. **Every transition is one endpoint, one L1 function, one `transfer_events`
   row, one transaction.** No endpoint performs two transitions.
2. **Every transition is idempotent** under `Idempotency-Key` and safe under
   concurrency via `expected_version` (§4).
3. **Double-booking is impossible**, enforced by a partial unique index, not by
   code (§4.3).
4. **SYSTEM transitions** (`expire_reservation`, `close_handover_window`,
   `classify_leakage`) are reachable **only** from the job runner. They are not
   exposed on L2 or L3, and `tests/api/test_system_transitions.py` asserts that
   a user cannot invoke them.

---

## 7. What this API deliberately does not have

| Absent | Why |
|---|---|
| Any payment, wallet, credit, balance, fee or refund endpoint | ADR-003 |
| Any field containing a settled price | ADR-003 §2.3 |
| A public, unauthenticated listing or search endpoint | ADR-002 §4 — a browsable surface is the r.3(1)(b) trigger |
| Bearer tokens, OAuth, API keys, a third-party API | No consumer, and each would be a new auth surface (ASVS V13) |
| A seller-address endpoint | `contact_disclosures` is the reviewed, logged substitute |
| Bulk export over HTTP | Insider risk — `THREAT-MODEL.md` §5.8 |
| Webhooks | No integration partner |
| GraphQL | One client, which we write. A query language is a rate-limiting and depth-attack problem we would be buying for free |
| Versioning beyond `/api/v1` | One client, deployed with the server |
| Ratings, reviews, reputation endpoints | ADR-001 §6, R-16 |
| Push via a vendor SDK | VAPID Web Push needs no vendor and no DPA |

---

## Amendment log

| # | Date | Change | Source | Approved by |
|---|---|---|---|---|
| — | 2026-10-21 | v1.0 frozen | — | cto |
| **A-1** | 2026-10-21 | `reschedule_handover` + `POST /transfers/{id}/reschedule` (§3, §5.4); rate-limit row | PRD **CG-1** | cto |
| **A-2** | 2026-10-21 | `open_ticket_as_student`, `reply_to_ticket`, `list_my_tickets`, `get_my_ticket`; **new §5.5a** support endpoints; `close_ticket` zero-seconds guard; rate limits | PRD **CG-2** | cto |
| **A-3** | 2026-10-21 | `confirm_handover` closes matching `book_requests` | PRD **CG-3** | cto |
| **A-4** | 2026-10-21 | `publish_listing` enqueues `requests.match_scan` | PRD **CG-4** | cto |
| **A-6** | 2026-10-21 | `relay_to_counterparty` + `POST /transfers/{id}/relay`; `request_contact_disclosure` gains the relay-first guard | **cto's own gap** | cto |
| **A-7** | 2026-10-21 | **`handover-safety` slug → `handover-guidance`**; `HANDOVER_SAFETY` → `HANDOVER_GUIDANCE`; forbidden-copy scope boundary stated | Design `SYSTEM.md` §7.7 | cto |
| **A-8** | 2026-10-21 | `GET /dev/states` accepted, staff-only, seed-data-only | Design `SYSTEM.md` §7.8 | cto |
| **A-9** | 2026-10-21 | Banned vocabulary grows to eight words; enforcement is per-script — see `THREAT-MODEL.md` §6.1 | Design **TR-8** | cto |
| **A-13** | 2026-10-21 | **§4.1 — anonymous POSTs get real idempotency** via a non-null sentinel key, not an exemption. Must close before S1 wires `/auth/magic-link` | QA-S0 **B3** | cto |
| **A-14** | 2026-10-21 | §2.2's error-shape renderer, CSP middleware and `test_forbidden_response.py` **assigned to S1 backend** — named controls that belonged to no slice | REVIEW-S0 N1–N3 | cto |
| **A-22** | 2026-10-22 | **§2.5 precondition 7 narrowed: the discovery gate is a READ control.** A listing created on a closed campus is the "private intake form feeding a record" compliance explicitly says is **not** a platform (A0) — the r.3(1)(b) trigger is the browsable surface. **Blocking the write protects nothing and guarantees R-01**, because the campus would open with zero supply. Permitted pre-gate: create a listing, upload its photos, record a want, read your own rows. Still gated: all discovery, and `→ OFFERED`. **A required disclosure string routed to design**, and the create flow may surface no other user's row **including a count** | QA S2 contradiction | cto |
| **A-21** | 2026-10-22 | **§3 procedural fix after a THIRD naming drift.** A read the interface needs is a **§3 amendment first, then an implementation** — rule 6 applied to signatures, not just files. Backend's four shipped names win and are recorded on receipt | S2 frontend pass | cto |
| **A-20** | 2026-10-22 | **`GET /media/listing-photo/{photo_id}` added** — the storage key existed and nothing served it, so **the data-saver criterion was passing vacuously and must not be reported as passing** (rule 10). Gate- and scope-checked in Django, bytes served by nginx via `X-Accel-Redirect`, 404 not 403 out of scope | S2 frontend pass | cto |
| **A-19** | 2026-10-22 | **F24: `POST /account/correction` added to §3 and §5.1, marked NOT IMPLEMENTED (S2).** §2.5 named it twice — as a Stack S right and as the *justification* for `display_name` sitting in Stack M — and it did not exist, **so the correction right had no path at all.** The M placement stands; **its reasoning may not be quoted as satisfied until the conformance test is green** | QA **F24** | cto |
| **A-18** | 2026-10-22 | **F22: `"campus"` removed from `/auth/consume`'s `needs`** — unreachable, because the magic link *is* the campus evidence and no link is ever sent to an unrecognised domain. **Removing it exposed the gap it concealed: a campus with empty `email_domains` has no student sign-in path at all** — recorded, not fixed, under ADR-001 §2.5's existing trigger | QA **F22** | cto |
| **A-17b** | 2026-10-22 | **§2.5 split into Stack M and Stack S** so suspension cannot remove statutory rights | QA erasure pass **P-1** | cto |
| **A-16** | 2026-10-21 | **§4.1 key-format scope stated as an INVARIANT, not a conclusion**: UUID required when unauthenticated, unconstrained when authenticated, resting on *`user_id` partitions the key namespace, one principal per partition* — **and extending to the authenticated namespace the moment any endpoint writes a key on another principal's behalf.** Three reachable breaks named: staff-acting-for-student in S5/S6, impersonation or service accounts, and `user_id` reuse after purge | REVIEW-S0 **§21** | cto |
| **A-15** | 2026-10-21 | **§4.1 anonymous idempotency re-specified** as a partial unique index on `key WHERE user_id IS NULL` — my `user_id = 0` sentinel is **withdrawn**, it breaks the S1 FK. **Anonymous POSTs require a key**, with one exemption: the L3 `GET /auth/c/{token}`, where a single-use token is idempotent by construction | ENGINE-DIVERGENCE §9.6a | cto |
