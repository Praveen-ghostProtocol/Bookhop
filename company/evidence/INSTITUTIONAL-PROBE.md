# The Rs 0 Institutional-Payer Probe

Owner: `market-finance` · Version: v1.0 · Date: 2026-10-21
Authorised by: `DECISIONS.md` **D-007 item 4** — "Run the Rs 0 librarian probe
testing the institutional-payer hypothesis. **Authorised as a test only — the
direction is not committed.**"
Answers: Red Team **O-12** · Red Team Test 3(c) · `MODEL.md` §11 (withdrawn as
strategy, surviving as a hypothesis)
**Cost: Rs 0.** **Elapsed: 5 calendar days.** **Effort: one desk day plus three
conversations of ≤ 15 minutes, inside recruitment `DISCOVERY.md` §6.2 is already
doing.**

---

## 0. Declared conflict of interest — read this before the instrument

**I proposed the institutional channel, and `MODEL.md` §11 ranked it first on no
sources at all.** D-006 condition 6 rejected it as strategy for exactly that
reason. I therefore have a standing incentive to design a probe that confirms it,
and the following constraints exist to remove my ability to act on that incentive.
They are not decoration.

1. **The negative-result criteria in §1 are fixed before any conversation happens
   and I may not revise them afterwards.** If I want them changed, that change is
   recorded in `DECISIONS.md` *before* the first call, with a reason, or not at all.
2. **I do not adjudicate the result.** `red-team` reads the raw sheets and calls
   pass or fail. I may write an interpretation; it carries no weight on its own.
3. **The questions below reveal nothing about BookHop until the last 60 seconds**
   (§3 disclosure script). A librarian who knows what answer we want will give it.
4. **Every question asks about something that has already happened.** No
   hypotheticals, no "would you", no price mentioned, per `DISCOVERY.md` §4.9.
   Red Team's own suggested fourth question — *"would you take 200 used copies of a
   prescribed title at 40% of MRP"* — is **deliberately not used**: it is
   hypothetical, it is leading, it names a price, and a polite librarian says yes to
   it. It is replaced by Q4, which asks what has actually stopped such a purchase.
5. **Non-answers count as non-answers.** "I'd have to check", "we could probably
   arrange something", "in principle yes" are recorded as **NO BUDGET LINE NAMED**.
   A hypothesis that survives only on vagueness has not survived.

---

## 1. Negative-result criteria — stated before the questions

**The institutional-payer hypothesis is recorded as DEAD, and `MODEL.md` §11 is
deleted rather than re-argued, if ANY of the following is true after three
conversations.**

| # | Kill condition | Why it kills |
|---|---|---|
| **K-1** | **Zero of three** librarians can name **both** (a) a budget line that pays for books students use and (b) the person who approves spending from it | Red Team O-12's threshold, adopted unchanged. If no one can name a line and an approver, there is no payer to sell to |
| **K-2** | **Three of three** say second-hand or donated books cannot be *purchased* under the institution's purchase rules (as distinct from merely never having been) | A rule-level prohibition is not something a product can route around. Donations accepted ≠ purchases permitted; record which |
| **K-3** | **Three of three** name the Principal, Registrar or a governing body as the **only** approver, with no delegated authority at any value | Every sale is then a top-level institutional negotiation. That is a different company with a 6-month sales cycle, not an adjacent market for this one |
| **K-4** | Fewer than **three** librarians at **three different institutions** complete the questions within 5 days | The probe did not run. Record as INCONCLUSIVE, not as a pass. Do not extend the window to find a friendlier respondent |

**Survival is not success.** If none of K-1 to K-4 fires, the only finding is *"an
institutional payer is not ruled out"*. That licenses **one** next step — a written
follow-up to the named approver — and it licenses **nothing** in `MODEL.md`,
`README.md` or any PRD. The hypothesis does not graduate to strategy on three
conversations.

**Ambiguity rule, fixed in advance.** Where an answer could be read either way, it
is read as the kill. I wrote the hypothesis; I do not get the benefit of the doubt.

---

## 2. The four questions, verbatim

Ask in this order. Do not reorder — Q4 depends on Q1–Q3 having established that we
are asking about real past purchases, not pitching. Read them as written. The
bracketed prompts are only for when a respondent stalls; they are not read
otherwise.

> **Q1.** "In the last financial year, what did this library spend on books that
> students actually borrow for their courses — textbooks rather than reference or
> journals? And is that a separate budget line from the rest of the book budget, or
> the same one?"
>
> *[If stalled: "A rough figure or even the number of volumes is fine — I'm trying
> to understand whether textbooks are budgeted separately, not to get an exact
> number."]*

> **Q2.** "Who decides what that money gets spent on during the year — is it the
> library, the departments, a committee, or someone else? And once it's decided,
> whose approval does the purchase need before the order goes out?"
>
> *[If stalled: "Does the approver change above a certain amount?"]*

> **Q3.** "Think of the last batch of books the library bought. Who did you buy them
> from, how was that supplier chosen, and what did the purchase have to go through
> before it was paid for?"
>
> *[If stalled: "Quotations, tender, an empanelled vendor list, a purchase order,
> anything like that?"]*

> **Q4.** "Has this library ever taken in second-hand or donated books? If it has —
> where did they come from and what happened to them? And if the library has never
> *bought* second-hand books, what's the reason — is it a rule, a practical problem,
> or just that it has never come up?"
>
> *[If stalled: "I'm asking because I don't know whether it's prohibited or just
> unusual."]*

**Total speaking time: under 15 minutes.** Q1 and Q2 are the only two that must be
answered for the probe to count; Q3 and Q4 are short because Q1 and Q2 do the work.

### Why these four and not others

| Question | What it establishes | Maps to kill condition |
|---|---|---|
| Q1 | Whether student textbooks are **already paid for** by the institution, and whether they are a budget line or invisible inside a general vote | K-1(a) |
| Q2 | **Who decides, and who signs** — the approver, and whether authority is delegated below the Principal | K-1(b), K-3 |
| Q3 | The **procurement path** a supplier like us would actually have to walk: vendor empanelment, quotations, tender, purchase order, payment terms | — (characterises effort; no threshold) |
| Q4 | The **flat no**: whether used stock is rule-prohibited, practically blocked, or merely novel. Phrased so a prohibition and a never-tried come back as different answers | K-2 |

### Recording sheet — one row per librarian, filled during the call

```
Institution | Date | Respondent role (not name) | Minutes
Q1  textbook spend last FY (figure or volumes): ______  separate line? Y / N / DON'T KNOW
Q2  who decides: ______   who approves: ______   delegated below Principal? Y / N / DON'T KNOW
    value threshold at which the approver changes: ______
Q3  last supplier: ______  how chosen: ______  process (quotes/tender/empanelled/PO): ______
Q4  ever taken second-hand or donated: Y / N   source: ______   outcome: ______
    never bought used because: RULE / PRACTICAL / NEVER CAME UP / DON'T KNOW
BUDGET LINE NAMED?  Y / N        APPROVER NAMED?  Y / N      <- these two decide K-1
Verbatim quote worth keeping: ______
```

Three sheets, filed at `company/evidence/RAW/librarian-01..03.md`. **Raw sheets go
in before any interpretation does**, and `red-team` reads the sheets, not my summary.

---

## 3. Running it — 5 days, Rs 0

| Day | Action |
|---|---|
| 1 | Desk day (§4). Request the three librarian conversations through the recruitment `DISCOVERY.md` §6.2 is already running — **no separate ask, no incentive payment, nothing that touches the Rs 16,500** |
| 2–4 | Three conversations, ≤ 15 min each, in person or by phone. Sheets filed same day |
| 5 | `red-team` reads the three sheets against §1 and calls it. `market-finance` writes the interpretation afterwards, not before |

**Recruitment note, paste-ready:**

> We're a small team looking at how college libraries handle course textbooks in
> Chennai. Could we take 15 minutes of a librarian's time to ask four questions
> about how books get bought here? We're not selling anything and there's nothing to
> sign — we're trying to understand the process before we assume anything about it.
> Happy to share what we learn across the campuses we speak to.

**Disclosure script — read only after Q4 is answered and the sheet is filled:**

> Thank you — that's what I needed. For transparency: we're exploring whether a
> student-to-student used-textbook service could be useful on campuses here, and one
> of the open questions is whether an institution would ever be the buyer rather
> than the students. I deliberately didn't say that up front because I didn't want
> to lead the answers. If any of this turns into something concrete, may I come back
> to you?

**Three things not to do.** Do not ask a fifth question that tests enthusiasm. Do
not leave a one-pager. Do not accept an introduction to "someone who'd be
interested" as a data point — it is a referral, not a budget line.

---

## 4. The Rs 0 desk day — the two items Red Team specified

Both are Red Team Test 3(a) and 3(b). Neither needs campus access, a budget or a
respondent, and **neither is blocked on anything** — they run on day 1.

### D-1 · Chennai live-listing counts (Red Team O-5)

Count live Chennai used-book listings and record the ten most recent post dates on
each of: **Bookaao**, **NearBook**, **BookFlow**, **Clankart**. Search by Chennai
PIN codes where the site has a location field; record "no geography layer" where it
does not (this is already the verified finding for Clankart).

**Threshold (O-5, unchanged):** best-funded competitor under **100** live Chennai
listings → the category ceiling is execution, not demand. Over **1,000** → the
channel exists and nobody monetises it, which strengthens the pessimistic reading.

> **OLX is excluded and will not be retried.** The competitor audit was blocked at
> **domain level**, not by a rate limit or a single bad page, so the block does not
> expire and re-attempting it is not a cheap action with a low success rate — it is
> a known-zero. **Record OLX Chennai as `BLOCKED — domain-level, count unverified`
> in `COMPETITORS.md` §8 and leave it there.** If the founder wants the number, it
> takes five minutes in an ordinary browser on a phone; it is a founder action, not
> an agent retry loop. **The O-5 threshold is evaluated on the four sites above
> without OLX, and the result is reported as a floor, not a count.**

### D-2 · 12-month listing-date series (Red Team O-9)

Count new used-book listings per week over 12 archived months on Clankart's and
BookFlow's India pages, and plot them.

**Why this one is not optional for me.** `model.csv` carries
`trading_weeks_per_year = 8` on the competitor audit's antiphase finding, which
`COMPETITORS.md` §5.2 itself flags as having **no source**. That single unsourced
constant compresses the entire revenue model — it is what charges `fixed_cost_y1_inr`
and `infra_cost_per_user_yr` against 8 weeks instead of 52, at 6.5× the naive rate.
Red Team's O-9 works the cited academic calendar through and gets a gap of **6–8
weeks, not months**, which would make my own structural objection #3 (`MODEL.md`
§10) substantially weaker than I stated it. **This test can go against me and I am
running it first.**

**Threshold (O-9, unchanged):** median gap between a cohort's disposal week and the
next cohort's acquisition week **over 10 weeks** → antiphase confirmed as
structural. **Under 6 weeks** → refuted, and `MODEL.md` §10(3) and the
`trading_weeks_per_year` driver are both restated.

### D-3 · Published library expenditure, if it exists (new — Rs 0)

The three pilot campuses' enrolment figures in `MODEL.md` §6 come from NIRF
filings, which are already downloaded and already cited. **Check whether those same
filings publish a library or book expenditure figure.** If they do, it is a
**sourced** answer to part of Q1 that does not depend on a librarian's recall, and
it lets Q1's answer be checked against a document.

`ASSUMPTION:` **that NIRF filings contain such a field at all — unverified, this is
a thing to look for on day 1, not a number to cite.** If the field does not exist,
record NOT FOUND and move on; do not substitute a figure from anywhere else.

---

## 5. What this probe cannot do, stated so nobody over-reads it

- **Three librarians is not a sample.** It is a screen for whether a payer exists at
  all. It can return a confident NO (K-1 to K-3) and it cannot return a confident YES.
- **It does not test willingness to pay, price, or volume.** Deliberately. Those
  questions cannot be asked without naming a number, and naming a number to a
  librarian who is being friendly produces an answer worth nothing.
- **It does not measure the supply side** — what happens to superseded editions,
  hostel clear-out stock, book banks. That is a second probe and it is only worth
  running if this one survives.
- **A survival result changes no document.** Per §1, it licenses one written
  follow-up to a named approver. `MODEL.md` §11 stays withdrawn either way until
  something with a source replaces it.

---

*Every threshold in this document is Red Team's, adopted unchanged, except K-2,
K-3 and K-4, which are additions that make the probe easier to fail and not
easier to pass. No number in this document is a forecast. The only figures that
appear are thresholds, and each cites the objection it comes from.*
