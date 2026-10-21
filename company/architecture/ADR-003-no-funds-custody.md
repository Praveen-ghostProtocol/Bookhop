# ADR-003 — No custody of funds, and the price field that must not exist

**Status:** Accepted · **Date:** 2026-10-21 · **Decider:** cto
**Restates and implements:** D-004 (no custody, ever), D-007 (student side
free), D-009 ("**P14 is binding on the schema: never store a settled
transaction price**"), Gate B items **B13** and **B14**, `CLAUDE.md` rule 3
and rule 4.
**Inputs:** `INCORPORATION-AND-BLOCKERS.md` §0, §2 (P12, P14), §4.2, §4.3(iii),
§5 C11 · `COMPLIANCE.md` §3 (PPI), §4.3 (s194-O), §7 row 19 ·
`risks/RISK-REGISTER.md` R-09, R-17, R-20.

This ADR exists because **this is the constraint most likely to be violated by
accident, by a well-meaning developer, in a single line of code, in six
months.** Everything else in the architecture set is a design; this is a
prohibition, and prohibitions need an enforcement mechanism rather than a
paragraph.

---

## 1. The three prohibitions, and the rule behind each

### 1.1 No custody of funds (D-004, `CLAUDE.md` rule 3)

BookHop never holds, escrows, routes, settles, splits or refunds money. Cash
passes directly from buyer to seller, in person, at a handover. There is no
payment integration in v1 — not disabled, **absent**.

### 1.2 No denominated balance of any kind (P12, D-003, D-007)

No wallet, no credits, no points, no stored value, no "coins", no
cash-purchasable or transferable or redeemable balance, under any name.
`COMPLIANCE.md` §3 concluded that design (a) (cash-bought) is a PPI and is
blocked; design (b) (earned, non-transferable) needs counsel; only design (c)
(an **ordinal** reputation level with no denomination) is clean.

**v1 ships none of the three**, including (c) — not because (c) is unlawful
but because a reputation signal increases "vouching" exposure (R-16,
`COMPLIANCE.md` §2.5) and there is nothing to compute it from at one campus.
See ADR-001 §6.

R-20 is live: a draft RBI Master Direction 2026 reportedly removes
"marketplace" from the own-goods exemption by name. If notified, design (b)
collapses into design (a). **Another reason the v1 answer is "none".**

### 1.3 Never store a settled transaction price (P14 — the hard one)

This is not about fees and is not relieved by being free. From
`INCORPORATION-AND-BLOCKERS.md` §0, which re-read the section specifically to
test the founder's hypothesis that free might release us:

- **s194-O Explanation (b)** defines "e-commerce operator" as *"a person who
  owns, operates or manages digital or electronic facility or platform for
  electronic commerce"* — **no payment limb, no consideration limb.**
  (https://indiankanoon.org/doc/72905898/, accessed 2026-10-21.)
- **sub-section (6)** *deems* the operator to be the person responsible for
  paying — a provision that catches us, not a condition that releases us.
- **Income-tax Act 2025, s393, Table Sl. 8(v)**: deductor "any e-commerce
  operator", rate **0.1% of gross amount**, **threshold nil**.
  (https://indiankanoon.org/doc/30529673/, accessed 2026-10-21.)
- The s194-O(2) Rs 5 lakh exemption is **expressly conditional on PAN or
  Aadhaar being furnished** — which P14 forbids collecting. So the exemption
  is unavailable to us by design, and that is the right trade (R-17: the data
  liability of holding Aadhaar/PAN is out of all proportion to the tax).

**The mitigation is the only one available: make the "gross amount of such
sales" indeterminable by never recording a settled consideration anywhere.**
`INCORPORATION-AND-BLOCKERS.md` §4.6 is explicit that this is *"an argument,
not a safe harbour"*, that it holds at 30 handovers and will need counsel
before 3,000. §5 C11 says the question *"becomes urgent that day"* if anyone
proposes storing a transaction price.

---

## 2. The schema consequences, stated as rules a developer can check

### 2.1 What exists

**Exactly one money column in the entire database:**

```sql
listings.asking_price_paise  integer  NOT NULL  CHECK (asking_price_paise >= 0
                                                   AND asking_price_paise <= 10000000)
listings.price_fixed_at      timestamptz NOT NULL
```

- **Integer paise. No floats for money, ever — and the layer that enforces
  that is the SERVICE, not the database.** Amendment 2026-10-21
  (ENGINE-DIVERGENCE §9.16, measured on the first PostgreSQL run):

  > **PostgreSQL enforces integer storage by SILENTLY ROUNDING, not by
  > raising.** `300.75` into an `integer` column returns **`301`**, with
  > `pg_typeof = integer`. A non-numeric *string* is rejected (22P02); a float
  > is not.

  So the claim splits in two, and only the first half was ever true of the
  database:

  | Claim | Layer that holds it |
  |---|---|
  | No float is ever **stored** | the database — guaranteed |
  | A float being **passed** is **detected and reported** | **the service layer, and nothing else** |

  **A silent round is worse than a rejection here**, because a rounded money
  value is a *wrong* value that looks right: sub-paise precision is lost with
  no signal on either engine. **The service layer must therefore reject a
  non-integer asking price rather than coerce it** — `Decimal`/`int` validation
  at the boundary, raising `400 VALIDATION_FAILED`, never `int(round(x))`.

  **And the test that matters is not the obvious one.** "The column is of
  integer type" passes while the bug ships. The required assertion is
  **`create_listing(asking_price_paise=300.75)` is REFUSED** — behaviour at the
  service boundary, not a property of the schema. S2 owns it.

  **This is the third instance of a pattern now worth naming explicitly: a
  control that guarantees a *state* does not thereby detect a *bad input*.**
  The gate's evidence CHECK proves every box is filled, not that any box is
  true (ADR-002 §4.1(b)); W1a proves the column cannot hold a float, not that
  no float was passed (§2.3 W1a); and here the database proves no float is
  stored, not that none was sent. **In all three the schema is the floor and
  the detection lives above it — and in all three the obvious test passes
  while the defect ships.**
- `0` is legal and means a giveaway (`intent = 'GIVE'`).
- The ceiling of 1,00,000 paise ×100 = Rs 1,00,000 is a sanity bound, not a
  policy.
- **It is the seller's asking price, fixed at intake, and it is immutable.**

### 2.2 Immutability is enforced by the database, not by discipline

Ladder rung: a DB constraint beats app code.

```sql
CREATE FUNCTION listings_price_is_immutable() RETURNS trigger AS $$
BEGIN
  IF NEW.asking_price_paise IS DISTINCT FROM OLD.asking_price_paise THEN
    RAISE EXCEPTION
      'P14: asking_price_paise is fixed at intake and cannot be changed '
      '(listing %). Withdraw the listing and create a new one.', OLD.id;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER listings_price_immutable
  BEFORE UPDATE ON listings
  FOR EACH ROW EXECUTE FUNCTION listings_price_is_immutable();
```

**Why immutable rather than versioned?** A price-history table would let
anyone reconstruct "the price at the moment of handover", which is
functionally a settled price. A seller who wants a different price withdraws
the listing and creates a new one, and the two listings are separate rows with
separate `price_fixed_at`. This also mirrors
`INCORPORATION-AND-BLOCKERS.md` §4.3(iii)'s build rule for the pilot: *"fixed
at the time the listing is taken"*.

### 2.3 What must never exist — **a whitelist**, enforced in CI

> **Amendment 2026-10-21 (compliance `COMPLIANCE.md` §4.3.2).** Privacy-
> compliance specified nine requirements for this test and stated that **its
> s194-O position does not hold without items 3, 4 and 9.** All nine are
> accepted. Item 3 **inverts the control from a deny-list into a whitelist**,
> and it is a better design than the one I froze: *"a blacklist is defeated the
> first time a developer writes `transfers.value_x integer`. A whitelist is
> less code and strictly stronger."* That is correct, and it is the correct
> ladder rung — **one assertion over a list that has to keep growing.** The
> deny-list below survives as a second layer, kept for one specific reason
> given in W3.
>
> Item 4 is the one I would have missed and it is the most likely next feature
> anyone proposes: **an accepted offer amount IS a settled consideration.**

#### W1 · The whitelist — `listings.asking_price_paise` is the only money column

**Assertion: every numeric column in the database must either be
`listings.asking_price_paise`, or carry a name ending in one of a short list of
declared non-monetary suffixes — and the one permitted column must be of an
integer type.**

> **Amendment 2026-10-21 on QA-S0 F1/F2.** QA built seven real-DDL attacks
> against this control and **three got through**, plus two that no schema
> control can stop. The whitelist is still the right design; it was
> under-specified in three ways, each fixed below (W1a, W1b, W5). QA also found
> that the *shipped* control had **transcribed** the deny-list from this
> document's prose and diverged from it — including keeping the DOB exemption
> that amendment A-5 explicitly withdrew. **That is a transcription defect this
> ADR caused by expressing the control as a table in prose**, and W6 removes
> the transcription step entirely.

```python
MONEY_COLUMN = ("listings", "asking_price_paise")   # the only one. ADR-003 §2.1

# A numeric column must be MONEY_COLUMN, or its name must END WITH one of
# these words, or BE one of them exactly. Amendment 2026-10-21 — see below.
NON_MONETARY_WORDS = (
    "id", "count", "seconds", "minutes", "attempts", "bytes",
    "width", "height", "year", "position", "version", "no", "status",
)

# Escape hatch for a genuinely odd name that no word above describes.
# An entry requires a one-line reason. Present and empty on purpose.
DECLARED_NON_MONETARY: dict[tuple[str, str], str] = {}
```

**Amendment 2026-10-21 (`ENGINE-DIVERGENCE.md` §8 item 6b, §9 item 6) — and
this is a correction to my spec, not to the
implementation.** W1 as frozen listed these as **suffixes** (`_count`,
`_seconds`, …) while `DATA-MODEL.md` mandates six columns with the **bare**
names: `jobs.attempts`, `listing_photos.width` / `height` / `bytes`,
`support_work_log.seconds`, `search_result_opens.position` — plus
`idempotency_keys.response_status`, which ends in no listed word at all.
**As literally written, my own whitelist rejected SEVEN columns my own frozen
contracts mandate.** Backend caught it before it reproduced the same class of
defect in a new place, and asked for the reading to be stated here so the guard
and the schema stop needing a developer's judgement to reconcile. Correct
request.

**The counterfactual settles it, and it is the strongest argument in favour.**
Refusing the clarification would have left a **P14 guard test red on seven
columns the contracts require** — with the tempting fix being an edit to a
founder-escalating file, under schedule pressure, by whoever was unlucky enough
to hit it. **That is M2 recreated seven times over.** The clarification removes
seven false positives and adds **no** true negative.

**RATIFIED · `NON_MONETARY_WORDS` — cto, 2026-10-21**

> **The thirteen names above are ratified in this ADR, by the CTO, on the date
> shown. `apps/core/p14.py` is their single expression in code (W1d); this
> section is their authority.** Any addition to the list is an amendment to
> this ADR and carries the founder escalation in §2.3's closing paragraph.
>
> **Why the ratification is not a formality**, in the reviewer's words and
> adopted here: *the escalation bar on this file is only credible if the
> provenance of the list is in the ADR. The next person to add a name must face
> a real bar, and they cannot if the list's authority is a comment in a test
> written by the developer the bar exists to constrain.* A control whose
> authority lives in its own implementation is self-certifying, and the whole
> point of W1d was to stop the control and its specification being the same
> artefact.

**Ruling: adopt the suffix-or-exact reading and add `status`. This is a
vocabulary clarification, not a widening of the money allowance** — and here is
the test that makes that claim checkable rather than asserted:

> **The discriminating question for any word in `NON_MONETARY_WORDS`: can this
> word denote a quantity that could be a consideration?**
> `id`, `count`, `seconds`, `minutes`, `attempts`, `bytes`, `width`, `height`,
> `year`, `position`, `version`, `no`, `status` — **none can.** They denote
> identities, counts, dimensions, durations and states.
> If a proposed addition *could* denote money — `total`, `value`, `sum`,
> `amount`, `balance`, `rate` — **it is a widening, it is refused here, and it
> goes to founder escalation.** Those six words are already on W1b's deny-list,
> which is where they belong.

**Why the reading is safe, stated because it is the non-obvious part: W1's
allow-list and W1b's token deny-list are AND-ed, not OR-ed.** A column must
pass *both*. So the bare-name reading admits `attempts` and `position` while
`cash_total` still fails W1 (neither suffix nor exact match) **and**
`payment_status`, `paid_status` and `settlement_status` still fail **W1b**,
because `payment`, `paid` and `settle` are deny tokens. Adding `status` cannot
smuggle a payment concept in. **That interaction is what makes this a
clarification; without it, it would not be.**

**`DECLARED_NON_MONETARY` stays present and empty**, as backend built it. It is
the narrower route and it remains available: a future column whose name no word
above describes gets an exact `(table, column)` entry **with a one-line
reason**, rather than a new word that applies database-wide. **Prefer the exact
entry over a new word.** I did not make it the primary rule because an
allowlist that gains an entry per slice becomes a list reviewers skim — the
failure mode of every manifest nobody reads — whereas a vocabulary rule of
thirteen words that cannot denote money does not churn.

A column named `value_x`, `amt`, `consideration` or `paid` ends in none of
them and **fails the build on sight, without anyone having predicted the
name.** `_paise` is deliberately **not** an allowed suffix: the one column that
uses it is named explicitly, so a second `*_paise` column cannot appear.

**W1a · The type is asserted, not only the name** (QA attack 7:
`asking_price_paise` declared **`real`** passed a name-based control). The one
permitted money column must be an **integer** type — `IntegerField` /
`BigIntegerField` in model meta, `integer`/`bigint` in introspection. A float
or `numeric` declaration fails. §2.1 already says "integer paise, no floats for
money, ever"; **until this amendment that sentence was prose.**

**The limit of this assertion, measured 2026-10-21:** it proves the column
**cannot hold** a float. It does **not** prove a float was never **passed** —
PostgreSQL silently rounds `300.75` to `301` in an integer column. **Detection
belongs to the service layer; see §2.1.** Two different claims, and W1a makes
only the first.

> **Amendment 2026-10-21 on REVIEW-S0 R2 — the two routes compose differently
> for names than for types, and conflating them inverted W1c's whole purpose.**
>
> W4 specifies two introspection routes. The implementation merged them as
> `introspected.update(model_schema())` — **model meta wins.** That precedence
> is **right for names** (a declared field is the stronger fact about what the
> codebase intends) and **backwards for types**, because the entire reason W1a
> exists is to see what the database *actually holds*. A `real` column is
> reported as a float only when no model declares it; in S0 `listings` has no
> model so QA's attack 7 is caught, but **from S2 it has one, and an
> out-of-migration `ALTER COLUMN … TYPE real` would be masked by the model's
> `IntegerField`** — the exact scenario W1a was written against.
>
> **Ruling, stated as the asymmetry it is:**
> - **Names: model meta overrides introspection.** A declared field is the
>   stronger fact.
> - **Types: UNION, not override. The float check fails if *either* route
>   reports a non-integer.** Never trust the declaration about the thing the
>   declaration is suspected of misrepresenting.
>
> **This also resolves the backend-versus-QA disagreement the reviewer
> identified, and both parties come out right:** backend was right about the
> related settlement table, QA was right that float money escapes — for the
> wrong reason — and the union makes both true at once rather than requiring
> either to be wrong.

**W1b · The money-token set is widened, because a suffix allow-list still lets
a plausible name through on a table nobody listed.** QA's attack 2
(`transfers.cash_handed_over`) and the `transfer_settlements.cash_total` variant
both escaped.

**The 22 tokens, and HOW each matches — the second column is new and is the
whole point of this amendment:**

| Tokens | Match rule |
|---|---|
| `price`, `paise`, `rupee`, `amount`, `amt`, `cash`, `money`, `fee`, `cost`, `value`, `total`, `sum`, `consideration`, `settle`, `settled`, `tender`, `charge`, `paid`, `payment`, `due`, `balance` | **substring**, anywhere in the column name |
| `rs_` | **prefix only** — `name.startswith("rs_")` |

**Any column matching any token, anywhere in the database, must be one of the
two columns W1b exempts, or the build fails.**

> **Amendment 2026-10-21 on QA-S0 F6 — four tokens were silently enforcing
> nothing, and the cause was a gap in this specification, not in the code.**
>
> This ADR stated 22 tokens; the shipped guard enforced **15**. Of the seven
> dropped, `fee`, `settled` and `balance` remain caught by the deny-list, and
> **`rs_` was dropped for a genuinely good reason: as a substring it collides
> with `members_count`** ("membe**rs_c**ount"). But **`amt`, `paid`, `payment`
> and `due` were caught by nothing**, and QA built four real-DDL attacks that
> are exactly those four tokens.
>
> **The specification caused this.** W1b said "contains any of these" and gave
> a flat list, so the one token needing a different match rule had no way to be
> expressed — and the only available fix was to drop it, which is what
> happened, with a documented reason that was locally correct and silently cost
> three other tokens with it. **A list that cannot express its own exceptions
> gets edited instead of extended.** Hence the match-rule column: `rs_` as a
> prefix catches `rs_total` and never `members_count`, so **no token has to be
> dropped and coverage is not traded for a false-positive fix.**
>
> All 22 are enforced. A drop requires an amendment here, not a comment there.

**RATIFIED · `MONEY_TOKEN_SHAPE_EXEMPTIONS` — cto, 2026-10-21**

> Enforcing all 22 tokens — correctly, and a tightening needing no escalation —
> turned two of them against names **three frozen contracts mandate**. Backend
> escalated rather than deciding, which is right: **this is an allowance.**
>
> | Exempt shape | Collides with | What it is |
> |---|---|---|
> | `due_at` | ~15 SLA-clock columns from S1 on — `purge_due_at`, `acknowledge_due_at`, `act_due_at`, `disposal_due_at`, `sla_due_at` | a **deadline** |
> | `overdue` | backlog state | a **state** |
> | `consume` | `consume_magic_link`, frozen by `API-CONTRACT.md` §3 and read by W1c's grep | a **verb** |
>
> **Applying this ADR's own discriminating question — *can this word denote a
> quantity that could be a consideration?* — the answer for all three is no.**
> A deadline, a state and a verb. Same class as `status`: **a vocabulary
> clarification, not a money widening.** Ratified.
>
> **And the reason this is safe is stronger than the vocabulary argument, which
> is why I checked rather than agreed: W1a independently rejects every one of
> these as a numeric column.** `due_at`, `overdue` and `purge_due_at` end in no
> word in `NON_MONETARY_WORDS`, so **a numeric column with any of these names
> fails W1a regardless of what W1b exempts.** The exemptions can therefore only
> ever admit **timestamps, booleans and function names — never a number.** The
> two layers cover each other, which is the property that makes an exemption in
> one of them affordable.
>
> **Verified, not assumed:** all eight contract-mandated names pass, and
> `amount_due`, `due_paise`, `due_inr`, `total_due`, `sum_paise`, `cash_sum`,
> `payment_due_at` and `balance_due_at` all still fail — the last two because
> an exempt shape only excuses *its own* token, never the rest of the name.
>
> **The counterfactual is the one used for `status`:** enforcing the bare
> tokens leaves the P14 guard red on contract-mandated names, with the tempting
> fix being an edit to a founder-escalating file under schedule pressure.
> **That is M2 recreated, for the third time.** The pattern is now familiar
> enough to name: *a guard that fires on the contracts it protects will be
> edited, not obeyed.*

**Order of resort when a token collides with one of our own names — adopt
backend's instinct as the rule:**

1. **Rename our name.** Backend changed `run_due_jobs` to `run_pending_jobs`
   rather than exempting it. **This is always preferred** — it costs one
   rename, leaves the control at full strength, and adds nothing to this ADR.
2. **Exempt the shape**, ratified here, only when the colliding name is
   **mandated by a frozen contract** and so is not ours to rename.
3. **Widen the allowance** — a founder escalation, and nothing in this section
   has yet needed it.

**W1c · A source-level check beside the schema one** (QA attacks 6 and 8). A
Python `@property` is **invisible to any schema control** — QA proved it by
adding `settled_price_paise` to a live model and watching the inspected schema
not change by one column. So CI additionally greps `apps/**` and asserts that
**no model field, `@property`, `@cached_property`, serialiser key or API
response key is money-shaped** unless it is `asking_price_paise`. The pattern
is already established: the S1 copy-enforcement tests grep source in CI for
exactly this kind of rule.

**W1d · One source of truth, so there is nothing to transcribe.** The token
sets, the suffix allow-list, the deny patterns and the frozen column lists live
as **data in `apps/core/p14.py`**, which the tests import. **This ADR is the
specification of record; the module is its single expression in code.** QA
measured the shipped control against this document and found them different —
including a withdrawn DOB exemption still live — because the control had been
retyped from a prose table. **A rule that has to be copied by hand into code
will eventually differ from its specification, and the difference will be
silent.** `tests/contract/test_p14.py` asserts the module matches this ADR's
list, so a drift fails rather than hides.

> **STATUS 2026-10-21: `apps/core/p14.py` DOES NOT EXIST, and F6/F7 are this
> amendment's own predicted divergence, already live. W1d is therefore no
> longer a design improvement — it is the fix for an active defect, and it is
> scheduled as one.** It lands **as a condition of S0's re-approval, in the
> same commit as the F6/F7 token and exemption fixes** — not in S1's general
> scope. Fixing four tokens by hand is the fourth hand-made copy of this rule;
> doing it without the module guarantees a fifth.
>
> **And the evidence is now overwhelming, because it came from the measuring
> instrument turning on itself.** QA found that **it had judged the control
> against its own retyped copy, while the guard's attack test checks a third
> inline copy — three hand-made copies of one legal rule, in three files, by
> three authors, disagreeing.** QA wrote that up at its own expense and called
> it W1d's argument made against itself. **It is the strongest evidence this
> ruling will ever get**: the transcription defect was not a developer being
> careless, it was *everyone independently doing the obvious thing*, including
> the agent whose job was to catch it. One imported definition would have made
> all three impossible.
>
> **Second piece of evidence, from the same rework that implemented W1d.**
> Backend's own guard-of-the-guard caught a **real narrowing in flight**:
> `rupees_exchanged` escaped **every layer** until `rupee` and `paise` were
> restored to the token list. A column naming the currency in plain words
> walked through a control in the middle of being strengthened.
>
> **A control that was briefly weaker than its predecessor while being made
> stronger is the best argument available for W1d.** It was not carelessness
> and review would not have caught it: the diff looked like an improvement, and
> it was one everywhere except the single place it silently regressed. **Only a
> test that compares the control against its specification catches that** —
> which is exactly what moving these sets out of prose and into imported data
> buys. Recorded so the next person tempted to inline them has the incident
> rather than the principle.

**Second limb, from item 3's "or sits on a table that has no business holding
money": no column anywhere may match a money token, except the two columns
`listings.asking_price_paise` and `listings.price_fixed_at`.** That is what
forbids item 5's `(listing_id, price, valid_from)`-shaped child table of
`listings` structurally rather than by name.

> **Amendment 2026-10-21 on REVIEW-S0 R1 — the exemption is scoped to two
> COLUMNS, not to the `listings` table. This is a genuine P14 hole and it was
> mine.**
>
> W1b as frozen exempted the whole `listings` table. W1a permits any numeric
> column ending in a declared non-monetary name. **Each rule is defensible
> alone; composed, they left the one table allowed to hold money as the one
> table where a *second* money column was unguarded.** Verified by the
> reviewer: `listings.paise_count`, `rupees_count`, `cash_total_count`,
> `amount_count`, `consideration_count` and `handover_value_count` **all pass
> every layer**, while the same names on `transfers` are caught.
>
> **§2.1 already says "exactly one money column in the entire database", so the
> contract was right and the control disagreed with it.** Scoping the exemption
> to `{("listings","asking_price_paise"), ("listings","price_fixed_at")}` makes
> the control say what the contract already said. `paise_count` then contains
> `paise` and is caught; the two permitted columns are pinned by an existing
> test, so the change cannot break S2.
>
> **This is backend's own pattern applied consistently** — when QA found
> `legal_entities.pincode` passing, backend rescoped the `address` exemption
> from a table to a column. The same move, in the same file, for the same
> reason: **a table-wide exemption is a hole shaped like a convenience.**
>
> **Not currently exploitable — `listings` does not exist until S2 — and the
> fix lands with S2.** Recorded now because the window is exactly when nobody
> is looking at it.
>
> **And the distinction that must stay on the record, because two decisions
> were nearly collapsed into one:** the W1 vocabulary clarification (below) is
> **not** the money widening. **This is.** They arrived together, they touch the
> same file, and they are not the same decision — one removes seven false
> positives without adding a true negative; the other closed a hole that let a
> real second money column through. Ratifying the first does not depend on
> fixing the second, and fixing the second does not reopen the first.

#### W2 · Frozen column lists on the four transaction tables (item 8)

`transfers`, `transfer_events`, `messages` and `transfer_followups` have their
**full column list** asserted against an expected list. **Any** new column on
any of them fails the build until the expected list is edited in the same
commit — which makes the edit visible in the diff, which is the whole point.

Plus the two enum value sets on `transfer_followups`, asserted by value:

```
question_key IN ('STILL_HAVE_BOOK', 'DID_YOU_GET_BOOK')
answer       IN ('YES', 'NO', 'NO_REPLY')
```

`DATA-MODEL.md` §5 promises *"no question about money, ever"*. **Compliance's
instruction — "promise it in the test" — is right: the follow-up is exactly
where a money question would feel natural ("did you pay?"), and widening an
enum is the quietest way to break P14.**

#### W3 · The deny-list survives as a second layer — for the error message

The patterns below are now **redundant** against W1 and W2 for almost every
case. They are kept anyway, and the reason is narrow and worth stating: **a
whitelist failure says "`value_x` is not an allowed numeric column"; a
deny-list failure can say "`offered_price` is a settled consideration — read
ADR-003 §2.3 and `COMPLIANCE.md` §4.3.1".** The second message stops a
developer from renaming the column and moving on. Belt and braces is normally
a smell; here the braces exist to teach.

#### W4 · How the test reads the schema — **correction, 2026-10-21**

v1.0 of this ADR specified that the test *"queries `information_schema.columns`
and `information_schema.tables`"*. **That was wrong and it is corrected here**,
because `ENGINE-DIVERGENCE.md` establishes that the development engine is
SQLite, **which has no `information_schema` at all.** A guard test that errors
or silently passes on the engine developers actually run is the exact defect
class ruled on in `THREAT-MODEL.md` §6.1: a control reporting green over a live
exposure.

**The test must introspect engine-neutrally, by two routes:**

1. **Django model meta** — `django.apps.apps.get_models()`, then each field's
   `db_column or attname` and `get_internal_type()`. This is where the
   whitelist (W1) and the frozen column lists (W2) are actually asserted, and
   it runs identically on both engines. It is also the *better* assertion:
   the constraint is a property of the declared models, so it fails at the
   point a developer adds the field, not after a migration runs.
2. **`connection.introspection`** — `get_table_list()` and
   `get_table_description()`, which Django implements for both backends. This
   catches columns added by `RunSQL` that model meta cannot see.

**`information_schema` must not appear in this test.** Neither must
`PRAGMA table_info` — a test that branches on the engine to read the schema is
a test with two code paths and one of them is never exercised.

With that fixed, the test runs everywhere and **fails the build** on any match
below:

| Forbidden pattern | Covers | Why |
|---|---|---|
| `%settled%`, `%sale_price%`, `%final_price%`, `%sold_price%`, `%agreed_price%`, `%paid_amount%`, `%amount_paid%`, `%transaction_amount%`, `%gross_amount%` | A settled consideration under any name | P14, s194-O / s393 |
| any money column on `transfers`, `transfer_events`, `disputes`, `handover_*` | A price attached to the *transaction* rather than the *listing* | P14 — the transfer is the thing s194-O cares about |
| `pan`, `%pan_number%`, `aadhaar`, `%aadhar%`, `%uidai%`, `%govt_id%`, `%id_proof%` | Government identifiers | P14, SPDI r.3 sensitive personal data |
| `%upi%`, `%vpa%`, `%bank_account%`, `%ifsc%`, `%card_number%` | Financial instrument data | `INCORPORATION-AND-BLOCKERS.md` §4.2 — arguably SPDI r.3 sensitive |
| `%wallet%`, `%credit_balance%`, `%balance%`, `%points%`, `%escrow%`, `%payout%`, `%ledger_entry%` | A denominated balance under any name | P12, D-003, RBI PPI |
| **item 4** — `%offer%amount%`, `%offered_price%`, `%counter%price%`, `%bid%`, `%negotiat%`, `%accepted_price%`, `%deal%` | **An offer, bid or negotiation amount. An accepted offer amount IS a settled consideration** | `COMPLIANCE.md` §4.3.2 item 4 — *"the most likely next feature request"* |
| **item 5** — `%price_history%`, `%price_change%`, `%previous_price%`, `%old_price%`, `%price_at%`, plus W1's structural limb | Price history in any shape — reconstructing "the price at the moment of handover" | §4.3.2 item 5; ADR-003 §2.2 argued this in prose and did not check it |
| **item 6** — `%discount%`, `%rebate%`, `%cashback%`, `%coupon%`, `%voucher%`, `%refund%`, `%adjust%amount%` | Price-derivation fields | §4.3.2 item 6 — Circular 20/2023's gross-amount arithmetic is built from these |
| **item 7** — `%shipping%`, `%delivery%charge%`, `%packaging%`, `%convenience%fee%`, `%commission%`, and `%fee%` **except** `fee_asked_paise` and `fee_paid` (§3), **with `fee_paid` asserted `boolean`, never numeric** | Charge components | §4.3.2 item 7 — these *"shall be a part of the gross amount"*. The only permissible shape is pre-enforced before anyone builds it |
| `date_of_birth`, `dob`, `%birth%` — **no exception** *(amendment 2026-10-21, CG-5: the former `age_check_pending` exception is withdrawn, because that table is deleted and no DOB is persisted anywhere)* | Any DOB storage, durable or transient | P14, `COMPLIANCE.md` §7 row 7: purge DOB after verification — now satisfied by never writing it |
| `%latitude%`, `%longitude%`, `%precise_location%`, `%gps%` — **except on `handover_points`** | Precise user location | `COMPLIANCE.md` §7 row 20; handover points are curated public places, not users |
| `%street%`, `%address_line%`, `%pincode%`, `%postal%` on any user- or listing-scoped table — **except `legal_entities.registered_address`** | Seller addresses | `COMPLIANCE.md` §2.4(i), §5.5 — never published, never collected |

A second test asserts the **API response schemas** contain none of the
forbidden keys, so the prohibition holds at the contract boundary too, not just
in storage — *"a price absent from storage but present in a response is still a
record"* (item 2). **Extended by this amendment: no response key may be named
`price`, `amount`, `total` or `value`.** The money field is
`asking_price_paise` at the boundary as well as in the table, so a template
cannot render "Price:" from a field that invited it. See §2.6.
A third test asserts the `listings_price_immutable` trigger exists and actually
raises.

**What the test must NOT forbid, confirmed by compliance:**
`transfers.completed_at`, `seller_confirmed_at` and `buyer_confirmed_at`.
ADR-003 §5.3 recommended keeping completion, keeping the asking price, and
buying counsel C11; **privacy-compliance endorses that trade in terms** — *"the
completion record is worth more than the marginal tax argument it costs"*
(§4.3.2). Not recording completion is the only materially stronger position
available and it would destroy every metric in `METRICS.md`, the
institutional-payer thesis and D-009's entire measurement mitigation. **So the
open residual in §5.3 stays open by agreement rather than by oversight.**

**The failure message names the rule and this ADR**, so a developer who hits
it learns why in one line instead of deleting the test. If a future slice
genuinely needs one of these, the test is changed **in the same commit as a new
ADR and a privacy-compliance sign-off**, never alone.

**Three diffs now carry that same escalation**, per compliance's added
condition: a change to the deny-list or whitelist; **a widened CHECK
constraint**; and **a new column on one of the four frozen tables.** *"Enum
widening and column addition are how this constraint will actually be broken,
not by someone naming a column `settled_price`."* Code Review's checklist
(`.claude/agents/code-review.md`) treats all three as a founder escalation.

#### W5 · What this control does NOT close

**Three shapes escape every assertion in W1–W4: a number inside a jsonb
document, a number inside free text, and a Python `@property`.** W1c closes the
third. The first two are not closable by any schema or source control.

**The residual, the four things that bound it, and the single sentence for the
G4 packet are stated once, in §5.3** — deliberately not repeated here, because
duplicating a statement is how two copies of it come to disagree, which is the
same argument W1d makes about the token sets.

### 2.4 Completion is a boolean and two timestamps, never an amount

```
transfers.seller_confirmed_at  timestamptz NULL
transfers.buyer_confirmed_at   timestamptz NULL
transfers.state                = 'COMPLETED' when both are set
```

Per `INCORPORATION-AND-BLOCKERS.md` §4.2: *"record completion as a
boolean."* The handover UI asks "did the book change hands?" — **it never asks
what was paid, and there is no field in which to answer.** The handover
guidance says "check the book before you hand over any money" and **"agree the
price between yourselves"** (§2.5a); it does not ask about the money
afterwards.

### 2.5a Negotiability must be real — the schema half of a copy-side limb

**Amendment 2026-10-21.** Compliance has introduced a requirement my schema
cannot carry, and it is right that it cannot. Circular 20/2021's second limb
needs the asking price to be *"not necessarily the price at which the
transaction takes place"*. **§2.2's immutability makes the asking price a
*better* proxy for the settled price, not a worse one** — correct for the
reason I chose it (no price history to reconstruct) and mildly adverse for this
one.

**I am not reversing immutability.** The alternative is worse on its face: a
mutable price with no history means the stored value simply *is* the price at
the time of the transfer, which is closer to recording a settled price, not
further from it. Immutability stays; the negotiation limb lives in copy, and
**the copy half is routed to design-director, not to me.**

**The three things the schema and the contract can do, which is my half:**

1. **The label is enforced at the API boundary, not just asked for in a style
   guide** (§2.3): no response key may be named `price`, `amount`, `total` or
   `value`. The field a template receives is `asking_price_paise`, so
   *"seller's asking price"* is the path of least resistance and *"Price"* is
   the path that requires someone to type the wrong thing deliberately.
2. **The metric is renamed in the export** (§2.5), because compliance's
   sharpest point is that **the document a tax officer actually reads is the
   metrics export, not the schema.**
3. **Nothing stores an offer, bid or counter-offer amount** (§2.3 item 4).

**And the resolution of the apparent tension between 3 and the negotiability
requirement, because it reads like a contradiction and is not.** How can price
be genuinely negotiated if we refuse to store a negotiation? **Because that is
precisely what makes it real.** The parties agree a number in chat and in
person, and BookHop never learns it. A structured counter-offer field would
make negotiation *visible to us* — which would satisfy the circular's
negotiability limb and destroy the structural argument that we know no amount.
**The prohibition on offer amounts and the requirement that negotiation be real
are the same design: BookHop must not know.** Stated here because the next
person to read both paragraphs will think they conflict.

### 2.5 "Book value moved" — the metric that looks like it needs a price

`METRICS.md` defines **Book value moved** = sum of stated book prices in
completed transfers, explicitly *"Not revenue"*, and **Cash GMV** = the subset
that actually involved money changing hands.

- **Book value moved** is computable: `SUM(listings.asking_price_paise)` over
  completed transfers. It is a sum of *asking* prices, which is exactly what
  the metric definition says, and it requires no new field.
  **Amendment 2026-10-21 (compliance §4.3.2 item 9) — it is renamed in every
  export and on every screen to `asking_price_sum_paise`, and it may never be
  rendered or exported without the sentence:** *"sum of asking prices of books
  that changed hands — not a sale value and not revenue"*. A test asserts the
  label travels with the number. **This is the single highest-leverage item in
  the nine**, and the reasoning deserves repeating in full: a report headed
  *"value of books sold"* that sums asking prices over completed transfers **is,
  in substance, BookHop asserting that those books sold for those amounts** —
  which is the exact assertion the whole schema constraint exists to avoid
  making. We would have protected the database and then published the
  conclusion.
- **Cash GMV is NOT computable in v1, and we are not going to make it
  computable.** Determining it requires knowing whether money changed hands
  and how much, which is a settled consideration. **`METRICS.md` must record
  Cash GMV as not-measurable-in-v1 with P14 as the reason.** Flagged to
  ceo-planning as a metrics-definition change — see §5.

This is the first place where P14 costs us a number we would like. It will not
be the last, and the answer is the same every time: **the number is not worth
the tax exposure, and nobody gets to add the column quietly.**

---

## 3. Fee arithmetic, if a fee ever returns

Not in v1 (D-006, D-007). Recorded because D-008's amended reversal trigger
keeps the question alive and because the build rule already exists:

> `INCORPORATION-AND-BLOCKERS.md` §4.3(iii): *"compute the fee as 6% of the
> seller's stated asking price, fixed at the time the listing is taken,
> rounded to the rupee, and recorded as `fee_asked: Rs 18 (6% of asking price
> Rs 300)`. Never ask, and never record, what the book actually sold for."*

So the shape of any future fee field is already determined: it is a function
of `asking_price_paise` and `price_fixed_at`, computed at intake, and the pair
`(fee_asked_paise, fee_paid)` where the second is a **boolean**, not an amount.
**A fee may never be computed from, or recorded against, a settled price.**

Also recorded, because product will propose it: **E-Com r.4(11)(b)** forbids
an e-commerce entity from discriminating between consumers of the same class.
`INCORPORATION-AND-BLOCKERS.md` §4.3(iv) is explicit that a randomised
6%-vs-free split *"would bite on the live platform"* and **must not be
repeated on the platform after Gate B without counsel**. A price A/B is
therefore a compliance change, not an experiment, and the architecture offers
no mechanism for one.

---

## 4. Deliberately not built in v1

| Not building | Add when |
|---|---|
| Any payment provider integration | Never without founder payment-activation authority (`README.md` §2) **and** counsel C10 reactivated |
| Wallet, credits, points, stored value (designs (a) and (b)) | Blocked by P12 / D-003; reactivate counsel C9 first. R-20 may make (b) unavailable |
| Ordinal reputation level (clean design (c)) | After counsel C6, and not before a second campus — ADR-001 §6 |
| Settled price, Cash GMV, revenue per transfer | **Not on any roadmap.** Requires counsel C11 answered favourably first, and probably never |
| Fee fields of any kind | Only if D-008's amended trigger fires *and* a second funded counsel-cleared test is authorised |
| Invoices, receipts, GST fields, TCS returns | No GST obligation in free-to-student v1 (`INCORPORATION-AND-BLOCKERS.md` §2, dropped blockers). Returns with institutional revenue (N2) |
| PAN / Aadhaar collection to claim the s194-O(2) Rs 5 lakh exemption | **Never at pilot scale.** R-17: the data liability exceeds the tax |

---

## 5. Escalations raised by this ADR

1. **To ceo-planning — `METRICS.md` needs an edit.** **Cash GMV is not
   computable in v1** and must be marked so, with P14 as the reason. Leaving
   it in the table implies someone will be asked to produce it, and the only
   way to produce it is to break P14. **Book value moved** stays and is
   computable from asking prices.
2. **To privacy-compliance / founder — the counsel C11 tripwire is now
   mechanical.** P14 is enforced by `tests/unit/test_forbidden_schema.py`. The
   day anyone proposes changing that file, C11 becomes urgent per
   `INCORPORATION-AND-BLOCKERS.md` §5. Code Review is instructed to treat a
   diff to it as a founder escalation, not a review comment.
3. **Standing note for red-team — now answered, and the answer went our way.**
   The weakest point in this ADR is not the schema; it is that
   **`asking_price_paise` plus `state = 'COMPLETED'` is arguably a determinable
   gross amount** if a tax officer reads "the asking price of a book that
   demonstrably changed hands" as the consideration.
   **Compliance took this question up directly in `COMPLIANCE.md` §4.3.1, found
   authority that was missing when this ADR was written, and endorsed the
   recommendation verbatim: keep completion, keep the asking price, buy C11.**
   Three changes follow, and all three are improvements:
   - **C11 moves from "deferrable" to "scheduled at Gate B, bundled"** with the
     C1–C3 engagement, re-drafted as a narrow yes/no on a named circular. That
     is cheaper and more useful than an open-ended question.
   - **The deferral condition was explicitly "if and only if P14 is enforced in
     the schema", and compliance records that condition as met.** The nine
     requirements in §2.3 are the price of keeping it met.
   - **The tripwire gains a third trigger that is not a schema event at all:**
     C11 becomes urgent the day anyone ships **copy or UX presenting the asking
     price as the transaction price**. §2.5a is the response.
4. **To design-director, via the coordinator — the half of §2.5a I do not
   own.** Negotiability must be visibly real: *"agree the price between
   yourselves"* in the handover copy, **"seller's asking price"** everywhere
   and never "price", and the four forbidden strings. **A schema cannot carry
   this limb; only the copy can**, and the limb is load-bearing for a position
   that is otherwise sound.
5. **Correction to this ADR's own framing, recorded rather than quietly
   fixed.** §2.2 justified immutability solely as preventing price-history
   reconstruction. It has a second effect in the opposite direction (§2.5a) and
   the original text did not know it. Immutability is still right; **the
   reasoning was one-sided and now is not.**

### 5.3 The residual exposure and the control that bounds it — one chain, in one place

**Amendment 2026-10-21.** Backend's §9 item 7 is right that the residual
exposure and `test_forbidden_response.py` are **one escalation, not two**, and
that the chain from *"P14 is enforced, not guaranteed"* to the control covering
the gap should be written here rather than left in a test docstring. It is:

**What the whitelist closes.** Backend ran QA's 22-case attack list against the
rewritten control: **20 caught**, including `transfers.cash_handed_over`,
`transfer_settlements.cash_total`, `settlements.amount_minor`,
`receipts.total_inr`, and `asking_price_paise` declared `real` or `numeric`.
**Every *named* and every *typed* escape QA demonstrated is closed.**

**What nothing in the schema or the source can close — three shapes:**

| Residual | Example | Why no schema or source control reaches it |
|---|---|---|
| A number in a jsonb document | `jobs.payload`, and from S3 `notifications.payload`, holding `{"paid": 30000}` | A jsonb column has no column name per key |
| A number in free text | a note column holding "Paid Rs 300" | A text field can always hold a number; no control reads intent |
| A Python `@property` | `settled_price` on a model | **Changes zero columns.** QA proved it: the inspected schema did not change by one column |

**What bounds them — and the chain, end to end:**

1. **W1c** greps `apps/**` for money-shaped fields, properties and serialiser
   keys. **This closes the `@property` shape** — it is the one of the three
   that *is* reachable, by source rather than by schema.
2. **W2's frozen column lists** mean the jsonb and free-text shapes require a
   **new column on a frozen table**, which fails the build and is a founder
   escalation. The exposure cannot be added quietly; it can only be added
   deliberately.
3. **PRD EX-18** — *no in-app "how much did you pay?" field, anywhere, in any
   optional form*. If we never ask, free text does not fill with amounts at
   scale. **This is the honest primary control and it is a product rule, not a
   technical one.**
4. **`tests/unit/test_forbidden_response.py`** — extended to amounts and not
   only to contact details — **is the compensating control for the jsonb and
   free-text limbs**, because a number that reaches no response surface is a
   number the platform does not publish or act on. **Owner: backend,
   S1** (`TASKS.md` §2; it was named by this ADR and by `THREAT-MODEL.md` §6
   and claimed by no slice until that assignment — *a named control with no
   owner is never written*).

### 5.3.1 Implementation status of the chain — because the sentence was true of this document and false of the repository

**Amendment 2026-10-21 on QA-S0 F5.** QA measured the chain above against the
code. **Two of W5's three controls do not exist**: W1c's source grep is
unimplemented (*no test in `tests/unit` or `tests/api` reads a source file at
all* — no `rglob`, no `read_text`, no `Path(__file__)`), and
`test_forbidden_response.py` is assigned but unwritten. **So §5.3's chain
terminated in two controls that were specifications rather than code, and the
sentence I wrote for the G4 packet described the specification.**

**Ruling: do both things — assign and schedule them, AND make the sentence
incapable of overstating us again.** The coordinator's instinct is the right
one: *better the packet understates us than overstates us.*

| Control | Status | Owner / slice |
|---|---|---|
| W1 whitelist + W2 frozen lists + W3 deny-list | **implemented and verified** | shipped, S0 |
| W1a type union (R2) | scheduled | backend, **S2** |
| W1b 22 tokens + column-scoped exemption (F6/F7) | scheduled | backend, **S0 re-approval** |
| W1d `apps/core/p14.py` | scheduled | backend, **S0 re-approval** |
| **W1c source grep** | **NOT IMPLEMENTED** | backend, **S1 — the first commit, before the first response schema exists** |
| **`test_forbidden_response.py`** | **NOT IMPLEMENTED** | backend, **S1** (assigned in `TASKS.md` S1 since the N2 ruling) |
| PRD EX-18 (no "how much did you pay?" field) | product rule, live | product + design |

**And the structural fix, so this cannot recur: the packet sentence may only
name a control that a test proves exists.** QA has already written the
detectors — `test_conformance_w1c_source_grep_exists` and
`test_conformance_w1d_single_source_of_truth_module_exists`. **I am adopting
them as the gate on this section:** `tests/contract/` asserts that every
control §5.3 names is present, so **§5.3 cannot claim a control the repository
does not have** — the claim and the check become one artefact, which is W1d's
principle applied to this ADR's own prose.

**The sentence for the G4 packet, in two versions, and the first is the one
that gets used until the second is earned:**

> **Today:** *P14 is enforced by a schema whitelist, frozen transaction tables
> and a deny-list, all implemented and verified. Two further controls — a
> source-level grep for money-shaped properties and a response-schema
> assertion — are specified and scheduled but **not yet written**, so the
> `@property`, jsonb and free-text residuals currently have no automated
> control. The residual is bounded today by the frozen-table escalation and by
> a product rule, not by code.*

> **Once W1c and `test_forbidden_response.py` pass:** *P14 is enforced by a
> whitelist, frozen tables, a source grep and a response-schema test, and
> guaranteed by none of them — the residual is a number in free text, and the
> control for it is a product rule plus a human reviewing diffs.*

**Nobody may quote the second until the conformance tests are green.** That is
the whole mechanism, and it is cheaper than remembering.

> **The distinction this section exists to protect, kept verbatim from
> REVIEW-S0 §22 because it is the clearest statement of it anyone has made:**
>
> > **An absent control that the compliance document correctly reports as
> > absent is a known gap; an absent control the document claims is a false
> > statement to a regulator.**
>
> **That is why the same gap was blocking a round ago and is acceptable now.**
> Nothing about W1c or `test_forbidden_response.py` changed — both are still
> unwritten. What changed is that **§5.3.1 understates rather than overstates,
> and a conformance test makes it unable to do otherwise.** The reviewer
> accepted S0 integrating on exactly that basis.
>
> The generalisation is worth keeping too: **the claim and the check become one
> artefact.** It is W1d's principle — don't keep a rule in two places that can
> disagree — turned on this ADR's own prose rather than on the token lists.
> `THREAT-MODEL.md` §6.2 promotes it to a standing rule for every control any
> architecture document names.

## 6. Reversal triggers

- **Counsel C11 answers that an asking price plus a completion boolean already
  creates a determinable gross amount**: the response is a tax position and a
  possible deduction mechanism, not a schema change — and it is a founder
  decision.
- **Any fee, or any institutional revenue, arrives**: C10 (GST/TCS) reactivates
  the same day, and this ADR is reopened before the first rupee.
- **The draft RBI Master Direction 2026 is notified** (R-20): re-run
  `COMPLIANCE.md` §3 before anyone mentions credits again.
- **A developer needs a forbidden column**: new ADR + privacy-compliance
  sign-off in the same commit, or it does not ship.
