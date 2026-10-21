# BookHop — project instructions

A marketplace for physical used books in India. Pilot: verified adults at
2–3 Chennai campuses, local handovers.

## Read first, every session

`company/README.md` is the company brain. Read the sections relevant to your
task **before acting**, and update them when a decision changes. Nothing is a
fact unless it is in there with a source.

## The agent organization

Charters: `.claude/agents/*.md`. Eight standing agents
(ceo-planning, product-manager, design-director, cto, market-finance,
marketplace-ops, privacy-compliance, red-team) plus specialists created by
their owner immediately before their work begins.

Invoke an agent with the Agent tool using its charter name as `subagent_type`.
If the registry has not picked up a new charter (it loads at session start),
fall back to `general-purpose` and point the agent at its charter file path in
the prompt — do not collapse the role into the main context.

## Rules that do not bend

1. **Never fabricate evidence.** No invented interviews, quotes, survey
   results, enrolment figures, or company metrics. "Not found" is a valid
   result. Every factual claim carries a source URL and date; every number
   without one is tagged `ASSUMPTION:` with the test that would replace it.
2. **Founder authorities are reserved**: spending, legal commitments, payment
   activation, public launch. Escalate with a short evidence-backed packet;
   never commit on their behalf.
3. **Never build escrow. Never hold seller funds.**
4. **No credit that is cash-purchasable, transferable, or redeemable ships**
   before privacy-compliance reviews it against RBI PPI rules. Calling a
   balance "points" is not a compliance analysis.
5. **Code Review and Test & QA pass before integration.** The Code Review
   agent never approves its own code. QA verifies behavior independently of
   implementation.
6. **Contracts before parallel work.** Never two agents editing the same files
   concurrently.
7. **Red Team reviews every gate** and gets the evidence, not just the
   proposal. An objection without a proposed test is unfinished.
8. These four numbers are **unverified planning assumptions**, not facts:
   5 lakh Chennai students · 20% participation · 2 transfers/year ·
   Rs 300 book value.
9. **Every control a document names must have a conformance test asserting
   that control exists in code.** A document may not assert a property; it
   must require a check for it. No claim about a control may be quoted in a
   launch packet, an ADR or a report until its conformance test passes.

   *Why (D-026):* in one pass, four separate defects were all the same shape —
   a specification stronger than its implementation, with no test for the gap.
   A token list named 22 tokens while 15 were enforced. A section named four
   controls, two of which did not exist. A test was specified that **cannot be
   written**. A clause read stronger than the floor it guaranteed. In each
   case the document was the thing that was wrong. The claim and the check are
   one artefact, or they drift.

10. **Never hand-copy a rule into code.** One imported definition, many
    readers. Three hand-made copies of one legal rule existed in three files
    by three authors and disagreed — and the agent whose job was to catch the
    divergence judged the control against its own copy. This was not
    carelessness; it was everyone independently doing the obvious thing.

11. **A list that cannot express its own exceptions gets edited instead of
    extended.** When one entry causes a false positive, the entry is deleted
    and coverage is silently lost. Give a list a per-entry match rule, not a
    flat membership test.

12. **A guard test that passes vacuously is worse than no guard**, because it
    is reported as coverage. This has been found five times. Where a property
    cannot be tested on the available engine, the test **skips with a reason
    naming the engine and the slice** — it never passes.

13. **A guard that fires on the contracts it protects will be edited, not
    obeyed.** Seen three times. The alternative to resolving a false positive
    is never a stricter control — it is a red test on mandated names and an
    edit to a protected file under schedule pressure. When a guard collides
    with a name, the order of resort is:
    1. **Rename our own name.** Always preferred: costs one rename, leaves the
       control at full strength, adds nothing to any document.
    2. **Exempt the shape, ratified**, and only when the colliding name is
       mandated by a frozen contract and so is not ours to rename.
    3. **Widen the allowance — founder escalation.** Nothing has needed this
       yet.

14. **Prefer two independent layers over one strict layer.** An exemption in
    one layer is affordable only when another layer independently rejects the
    same thing. Before granting any exemption, state which other layer still
    catches it — and if none does, it is a widening, not a clarification.

15. **An invariant beats a list.** Ask the property, don't enumerate the
    cases. Twice now a list has been the wrong answer: a money-token list
    enforced 15 of 22 entries, and a whitespace list could never have caught
    zero-width space or a byte-order mark, because those are *format*
    characters rather than whitespace — they survive a strip and render as
    nothing. The replacement asks Unicode, per character, whether anything
    printable and non-format is present; it consults no list and can gain no
    entries. Where an invariant genuinely cannot be expressed — SQL has no
    portable character classes — use a list, **declare its ceiling in the same
    place**, and point at the layer that generalises.

16. **A refused operation is not evidence a guard fired for the right
    reason.** PostgreSQL validates plpgsql syntax at creation but resolves
    identifiers and operators at the first execution of *each branch*, so a
    guard can be created cleanly, pass every happy path, and fail the first
    time someone does the forbidden thing — and the worst form of that failure
    still blocks the operation, so it looks like the guard working. Exercise
    every refusal path and **assert the message text, not the exit status.**

17. **Label every cross-engine or cross-library claim `VERIFIED HERE` or
    `ASSUMED THERE`.** An unverified claim about platform behaviour is a
    prediction and must be written as one, in any architecture document, not
    just the one about engine differences.

    *Why:* rule 9 asks whether a control exists. It does not ask whether a
    document's *explanation* of that control is true — and three predictions
    turned out wrong inside documents that had passing conformance tests. The
    worst was a probe that was green on both engines **for two different wrong
    reasons**: on one it compared untyped integers, on the other it never
    reached the constraint at all, and the document recorded the wrong reason
    as deliberate.

18. **A control that guarantees a *state* does not thereby detect a *bad
    input*.** Seen three times. A constraint proving every box is filled does
    not prove any is true. A guard proving a column cannot hold a float does
    not prove none was passed. A database proving no float is stored does not
    prove none was sent — PostgreSQL rounds `300.75` to `301` silently, and
    **a rounded money value is a wrong value that looks right.**

    In each case the schema is the floor, **detection lives above it**, and
    the obvious test passes while the defect ships. So the test that matters
    is never "the column is of integer type" — it is "passing a non-integer
    is refused."

## Assignment format

Every assignment: **Role** (who owns the outcome) · **Context** (user,
objective, evidence, constraints, dependencies) · **Command** (the specific
result or decision to test) · **Format** (deliverable, acceptance criteria,
verification, handoff recipient).

## Engineering standard (from Phase C)

Modular monolith + responsive PWA unless evidence says otherwise. Multi-campus
and multi-city in the data model from day one; no premature microservices.
Transactional storage, idempotent actions, migrations, background jobs,
backups with **tested** restore, rate limits, observability, rollback.
Current OWASP ASVS as the security checklist. WCAG 2.2 AA, verified not
claimed. Small, complete, testable vertical slices.

## Standard of done

A running app is not done. Done is: usable, trustworthy, measurable,
supportable, and ready for its next rollout stage — with what works, what was
verified, what Red Team challenged, and what remains uncertain all written
down.
