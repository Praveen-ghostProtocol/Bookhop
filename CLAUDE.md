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
9. **A document's claim is not evidence.**

    Every control a document names must have a conformance test asserting
    **both that the control exists and that its property holds.** Existence
    diagnoses — it fails by name, so you know which guard went missing.
    Behaviour guarantees. Ship both; never only the first.

    The test must assert the control **at the boundary the document claims,
    not the boundary the implementation chose.** And every cross-engine or
    cross-library claim is labelled `VERIFIED HERE` or `ASSUMED THERE`: an
    unverified claim about platform behaviour is a prediction and is written
    as one.

    *Earned:* a token list named 22 and enforced 15. A section named four
    controls, two of which did not exist. A test was specified that **could
    not be written**. A trigger-existence check passed on one engine **while
    the table it guarded was freely updatable**, because a surviving sibling
    satisfied it — so the earlier wording of this rule was satisfied by the
    exact test that failed. A probe was green on both engines **for two
    different wrong reasons**, and the document recorded one of them as
    deliberate.

    *Corollary:* when an explanation and a measurement disagree, **delete the
    explanation** — even when it lives in a document whose job is to explain.

10. **A passing check is not evidence.** A check that cannot fail is worse
    than no check, because it is reported as coverage. Found repeatedly, in
    six disguises:

    - **A test that passes vacuously.** Where a property cannot be tested on
      the available engine, the test **skips with a reason naming engine and
      slice** — it never passes.
    - **A requirement that cannot be satisfied, or cannot be violated.** A
      criterion gated on a value that does not exist; a criterion broader than
      its own rationale, which the main journey must violate to work. These
      surface only when someone tries to build against them.
    - **A guard whose fixture cannot produce the condition.**
    - **A measuring instrument that does not assert it measured.** The
      accessibility harness reached four pages of eleven and **reported
      coverage for a whole slice.** An instrument asserts its own reach, and
      any number it produces is quoted with the count actually reached.
    - **A check that has not started.** A forward-dated test can skip
      **forever**. From outside, *"not yet running"* and *"running and passing
      trivially"* are indistinguishable. **Invert it: once the owning app
      exists, a ruled path that does not resolve is a failure** — and assert
      that failure branch still exists.
    - **A refusal on the wrong signal.** A database validates a function's
      syntax at creation but resolves names at the first execution of *each
      branch*, so a guard can be created cleanly and fail the first time
      someone does the forbidden thing — **and the worst form of that failure
      still blocks the operation, so it looks like the guard working.**
      Exercise every refusal path and **assert the message text, not the exit
      status.**

    *Corollaries.* **Where a rule splits a set, both sides are rows, and a
    test enforces that** — checking only the permitted side passes. **Write a
    guard for a guard when the guard is forward-dated or silent**; the one
    written here caught its own author's bug on its first run. And **a mark
    must be as narrow as the gap it marks**: an expected-failure mark belongs
    on one subject, because marking an aggregate lets a second failure hide
    inside the first.

11. **One definition, not many copies.** Never hand-copy a rule into code —
    one imported definition, many readers. **Ask the property; do not
    enumerate the cases.**

    Where an invariant genuinely cannot be expressed — SQL has no portable
    character classes — use a list, **declare its ceiling in the same place**,
    point at the layer that generalises, and **give each entry its own match
    rule**. A flat list gets *edited* when one entry misfires, and coverage is
    silently lost with it.

    *Earned:* three hand-made copies of one legal rule disagreed, and the
    agent whose job was to catch the divergence judged the control against its
    own copy. A whitespace list could never have caught zero-width space,
    which is a *format* character: it survives a strip and renders as nothing.
    One token was deleted to fix a false positive and **took three unrelated
    tokens with it.**

12. **One layer is never enough, and layers do different jobs.** Before
    granting any exemption, **name the other layer that still catches it** —
    if none does, it is a widening, not a clarification.

    And **a control that guarantees a *state* does not thereby detect a *bad
    input*.** A constraint proving every box is filled does not prove any is
    true. A database proving no float is stored does not prove none was
    passed — it rounds silently, and **a rounded money value is a wrong value
    that looks right.** The schema is the floor; **detection lives above it**,
    and the obvious test passes while the defect ships. The test that matters
    is never "the column is of integer type" — it is "passing a non-integer is
    refused."

13. **A guard that fires on the contracts it protects will be edited, not
    obeyed.** The alternative to resolving a false positive is never a
    stricter control — it is a red test on mandated names and an edit to a
    protected file under schedule pressure. Order of resort:
    1. **Rename our own name.** Costs one rename, leaves the control at full
       strength, adds nothing to any document.
    2. **Exempt the shape, ratified** — only when the colliding name is
       mandated by a frozen contract and so is not ours to rename.
    3. **Widen the allowance — founder escalation.** Nothing has needed this.

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
