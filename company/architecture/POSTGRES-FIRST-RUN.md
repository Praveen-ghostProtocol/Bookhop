# POSTGRES-FIRST-RUN.md — the execution checklist for the first PostgreSQL run

**Owner:** cto · **Version:** v1.0 · **Date:** 2026-10-21
**Status:** a **deliverable**, not a formality. It gates S2 (`TASKS.md` S2).
**Runs against:** PostgreSQL 16, installed on the founder's machine 2026-10-21.
**Reads with:** `ENGINE-DIVERGENCE.md` · ADR-002 §4.1 · ADR-003 §2.2–2.3 ·
`THREAT-MODEL.md` §6, A14 · `QA-S0.md` · `REVIEW-S0.md`.

---

## 0. Two corrections to this run's premise, before anyone ticks a box

**(a) There are FIVE plpgsql function bodies, not six.** Measured in the
repository:

```
audit_log_is_append_only              (0002)
gate_authorisations_is_append_only    (0002)
campuses_gate_is_authorised           (0003)
bookhop_truncate_guard                (0003)
gate_authorisations_evidence_complete (0005)
```

**The price-immutability trigger is not among them — it does not exist.**
`listings` is an S2 table and `ENGINE-DIVERGENCE.md` §3.9 says so plainly. I
have repeated "six" in three documents and it was wrong; A14 and the S2 gate
are corrected. **This matters because a checklist that lists a control nobody
can run is how an unrun control gets reported as run.**

**(b) Two of the shapes named for this run are not testable yet.** The
**double-booking partial unique index** is on `transfers` (S4) and the
**transaction state machine's MVCC behaviour** needs `transfers` too. Both are
deferred to §3 with the exact shape to test when they arrive. What *is*
testable concurrently today is the **`idempotency_anon`** partial unique index,
which is the same mechanism on a table that exists.

**So: five bodies, five guards, one concurrency property, today.** Everything
else is §3.

---

## 1. Ordered by what is most expensive to discover late

Each item says **what to run**, and then **what a failure means** — which is
the half a checklist usually omits.

---

### 1 · Exercise every REFUSAL path, not every permission path

**Why first.** `check_function_bodies` (on by default) validates plpgsql
**syntax** at `CREATE FUNCTION`. It does **not** resolve identifiers, column
references or operators inside the body — **plpgsql resolves those at the first
execution of each branch.** So a guard can be created cleanly, pass every
happy-path test, and fail the first time anyone triggers the thing it exists to
forbid.

**Run:** for each of the five guards, execute the **forbidden** operation and
assert both that it is refused **and the exception message text**:

| Guard | Forbidden operation to run |
|---|---|
| `audit_log_is_append_only` | `UPDATE audit_log SET action='x'` · `DELETE FROM audit_log` · `DELETE FROM audit_log` with no WHERE |
| `gate_authorisations_is_append_only` | `DELETE` one row · `UPDATE` an immutable column (e.g. `evidence`) · `UPDATE` only `revoked_at` (**must SUCCEED**) |
| `campuses_gate_is_authorised` | `UPDATE campuses SET discovery_enabled_at=now()` with no authorisation · `INSERT` a campus arriving already-open |
| `bookhop_truncate_guard` | `TRUNCATE audit_log` with the GUC unset |
| `gate_authorisations_evidence_complete` | `INSERT` a `gate='C'` row with `evidence='{}'` · with one key missing · with `authorised_by_human=''` |

**A failure here means:** the guard was never a guard. Worst shape — an
exception raised from inside a refusal branch (`relation does not exist`,
`operator does not exist`, `column … does not exist`) still *blocks* the
operation, so it **looks like the guard working** while proving nothing about
the rule. Read the message, not the exit status.

---

### 2 · `TG_OP` ordering on the two statement-level TRUNCATE triggers

**Why this high.** `gate_authorisations_is_append_only` is attached both `FOR
EACH ROW` and `FOR EACH STATEMENT`. **In a statement-level trigger `NEW` and
`OLD` are unassigned**, and the body tests
`IF TG_OP IN ('DELETE','TRUNCATE')` and raises **before** touching them. **I
caught that ordering by reading, in an earlier pass** — which reduced the risk
and did not eliminate it.

**Run:** `TRUNCATE gate_authorisations` and `TRUNCATE audit_log`, and assert
the **intended** message appears — not `record "new" is not assigned yet`.

**A failure here means:** TRUNCATE is still blocked, but **by the wrong
error**, and the ordering is holding by accident. The consequence is not
today's behaviour; it is that **a future reorder of those two blocks leaves the
guard apparently working** and the only signal is the message text. Assert the
string.

---

### 3 · `ENABLE ALWAYS` actually applies, under `session_replication_role = 'replica'`

**Why this high.** A trigger without `ENABLE ALWAYS` **does not fire** when
`session_replication_role` is `replica` — which is what `pg_restore
--disable-triggers` and logical replication apply use. **The failure appears
only during a restore, which is the worst possible moment**: the append-only
guarantee on `audit_log` would silently not hold exactly when someone might be
rewriting history.

**Run:** `SET session_replication_role = 'replica';` then re-run the refusals
from item 1 for the three `ENABLE ALWAYS` triggers. They must still refuse.
Then confirm every `ALTER TABLE … ENABLE ALWAYS TRIGGER` in 0003 and 0005 named
a trigger that exists — **a name typo fails the migration loudly on Postgres,
which is the good case**, and is unobservable on SQLite.

**A failure here means:** the audit chain is mutable during exactly the
operation `INFRA.md` §3.3's restore test performs, and the tamper-evidence
claim in the G4 packet is false for that window.

---

### 4 · `chr()` and the database encoding, for the eleven invisible codepoints

**Why.** The set is built as `chr(32) || chr(9) || … || chr(65279)`, which is
**better than a string literal** — it sidesteps `standard_conforming_strings`
entirely, where `'​'` in a plain literal would have been six literal
characters and the guard would have stripped backslashes while letting
zero-width space through. Credit where due. **But `chr(n)` for n > 127 requires
the database encoding to be UTF8.**

**Run:** `SHOW server_encoding` (expect `UTF8`); then assert each of the eleven
codepoints round-trips —
`SELECT chr(65279) = U&'\FEFF'`, and the same for `0x200B`, `0x1680`, `0x2007`,
`0x00A0`.

**A failure here means:** on a non-UTF8 database `chr()` either errors (loud,
fine) or yields a different character — and the guard then strips a set nobody
intended while the eleven forms it was written for pass. **This is the one item
where the control could be silently protecting against the wrong thing.**

---

### 5 · `btrim` behaves as `btrim`, not as assumed — including the declared ceiling

**Run, as four separate assertions:**
1. **Set semantics**, not substring: `btrim` treats argument 2 as a *set of
   characters*. Confirm `btrim('ab', 'ba') = ''`.
2. **Ends only**: `'A' || chr(8203) || 'B'` is **unchanged** by btrim and
   **passes** the guard — correct, there is a visible character.
3. **NULL path**: `authorised_by_human = NULL` must be **refused**. The body
   wraps it in `coalesce(…, '')`, so this should hold — **but a bare
   `btrim(NULL, ws) = ''` evaluates to NULL, and a CHECK constraint is
   *satisfied* by NULL.** The trigger form avoids that trap; confirm by
   execution that the trigger form is what runs.
4. **The ceiling, asserted rather than trusted:** U+2060 WORD JOINER is **not**
   in the eleven and **must pass the database floor**. The migration declares
   this; a passing test is what stops it being read as covered.

**A failure on 1–3 means:** the one field carrying *"a named human signed
this"* can be satisfied by something that renders as nothing in the audit row
and in the go/no-go packet. **A failure on 4 means the ceiling moved** — which
is good news that must still be written down, because the command above the
floor is what generalises (`CLAUDE.md` rule 14).

---

### 6 · `NEW.evidence -> k` resolves against the real column type

**Why.** `evidence` is `jsonb` on Postgres and `TEXT` on SQLite
(`ENGINE-DIVERGENCE.md` §2.2). The body uses `->`, `->>`, `jsonb_typeof` and
`jsonb_array_length`, and **plpgsql resolves operators at first execution.**

**Run:** `\d+ gate_authorisations` and confirm `evidence` is `jsonb`; then
insert a `gate='C'` row with `notice_version_ids` as an **empty array** and
assert it is refused by the array-length branch specifically.

**A failure here means:** the completeness guard raises `operator does not
exist` on every insert — loud and cheap — **or**, if Django created the column
as `json` rather than `jsonb`, the `jsonb_*` branches behave differently and
the empty-array check silently never fires.

---

### 7 · The TRUNCATE escape defaults to deny, and the harness fixture exists

**Run, three cases:** GUC **unset** → refused; `SET bookhop.allow_flush =
'yes'` → `TRUNCATE` succeeds; `SET bookhop.allow_flush = 'no'` → refused. Then
confirm `tests/conftest.py` sets it for a Postgres session.

**A failure on the default means:** `audit_log` is mutable by one `SET`.
**A missing fixture means** the first Postgres run of S4's transactional
`test_double_booking.py` fails in teardown — **and the tempting fix at that
moment is deleting the guard**, which is the failure mode the charters' last
hard rule names. Note the standing position (ADR-001 §2.2): **no mechanism can
make production refuse this `SET`.** The escape is gated by the threat model's
accepted scope (direct SQL, A8), not by Django.

---

### 8 · `idempotency_anon` under genuine concurrency

**Run:** N simultaneous inserts of the same `key` with `user_id IS NULL`, from
N real connections. Exactly one must win; the losers must raise a unique
violation the service converts to a replay or a 409.

**A failure here means:** QA-S0 B3 is not actually fixed. **This is the only
concurrency property testable before S4**, and it exercises the same mechanism
the double-booking guard will use — so a pass here is a meaningful rehearsal
and a failure here predicts a failure there.

**Also assert the Django-level trap now, while it is cheap:** an
`IntegrityError` inside an `atomic()` block **poisons the transaction**, so the
service converting it to a 409 must sit inside a **nested atomic / savepoint**
or the error response itself fails. **This cannot happen on SQLite**, where the
loser gets `database is locked` instead, so it has never been exercised.

---

### 9 · Migrations apply forward and reverse, from empty

**Run:** `migrate` from an empty database; then reverse 0005 → 0001 and
re-apply. The reverse must drop triggers **before** their functions.

**A failure here means:** no rollback path (`INFRA.md` §4), on the one class of
change that `git` cannot undo.

---

## 2. What this run will NOT prove — the half a packet gets wrong

1. **That the controls are correct. Only that they execute as written.** A
   guard that faithfully refuses the wrong thing passes every item above.
   Correctness is what three review passes were for; this run tests
   *existence and behaviour*, not *fitness*.
2. **Nothing about `listings` or `transfers`** — so nothing about
   price-immutability (ADR-003 §2.2), the double-booking index, or the
   transaction state machine. **Two of the controls most often cited as
   verified by this run cannot be touched by it.**
3. **Nothing about the application-layer P14 controls** — the whitelist, frozen
   column lists, the source grep, `test_forbidden_response.py`, copy
   enforcement. Those are Python, they already run, and two of them are still
   unwritten (ADR-003 §5.3.1).
4. **Nothing about evidence being true.** Presence-not-truth (ADR-002 §4.1(b))
   is unchanged by execution: `campus_mou_ref='TODO'` and a plausible fake
   `authorised_by_human` still open the gate. **Every box filled is still not
   every box true.**
5. **Nothing about production** — the box, log residency, NTP, backups, the
   tested restore. Different exercise, `INFRA.md` §3.3.
6. **Nothing about behaviour at scale.** A green run on a near-empty database
   says nothing about the retention purge, or about the quadratic regression a
   reviewer already found once in a guard nobody had executed.
7. **Nothing about the 54 skips** that remain skipped for reasons other than
   the engine.

---

## 3. Deferred, with the exact shape to test when the table arrives

| Property | Arrives | The shape, so it is not re-derived |
|---|---|---|
| Price immutability (ADR-003 §2.2) | **S2** | `UPDATE listings SET asking_price_paise = …` raises; a no-op update of other columns succeeds; the trigger exists and is `ENABLE ALWAYS` |
| Double-booking (`DATA-MODEL.md` §5) | **S4** | N concurrent `accept_offer` on one listing → exactly one 2xx, N−1 × `409 LISTING_ALREADY_RESERVED`; the loser's IntegrityError handled in a savepoint |
| MVCC on `expected_version` | **S4** | Two concurrent `UPDATE transfers … WHERE version = :v` under READ COMMITTED: the second blocks on the row lock, re-evaluates against the new committed version, affects **0 rows**, returns `409 VERSION_CONFLICT`. **On SQLite the loser gets `database is locked` instead, so this has never been exercised** |
| Reservation-expiry vs accept race | **S4** | A job expiring a reservation while a request accepts it must resolve one way, not both |
| `DATA-MODEL.md` §9 metric SQL | **S7** | `percentile_cont`, `FILTER`, `date_trunc` — none runs on SQLite |

---

## 4. What text review can and cannot have covered

**Text review reduced the risk; it did not eliminate it.** The evidence that it
was worth doing is concrete: reading the bodies caught the `TG_OP`-before-
`NEW`/`OLD` ordering in `gate_authorisations_is_append_only`, which **would
have deployed and protected nothing** — a guard that fails with an internal
error instead of its rule.

**Items text review cannot have covered at all**, because reading cannot
establish them: **1** (runtime identifier resolution per branch), **3**
(`replica` role), **4** (encoding and `chr()`), **6** (operator resolution
against the real column type), **7** (GUC semantics), **8** (concurrency), **9**
(migration apply/reverse).

**Partially covered:** **2** — the ordering was found by reading, but the
runtime message is unverified. **5** — the logic was reviewed; the encoding
underneath it was not.

**So of nine items, text review has meaningfully touched two.** That ratio is
the argument for this run, and it is also the honest answer to *"three agents
have reviewed these controls, why is a run still needed?"*

---

## 5. Reporting

One result line per item: **PASS / FAIL / NOT APPLICABLE (with the reason)**.
`NOT APPLICABLE` is a real and expected outcome for anything in §3 — **it is
never recorded as PASS**, per `CLAUDE.md` rule 12.

The completed checklist is an artefact for the G4 go/no-go packet, filed with
**§2 attached**, because §2 is what stops the run being read as more than it
is. **A14 is not closed by this run** — it is narrowed from "five bodies never
parsed" to whatever §1 actually establishes, and the residue is §3.

*(Operational note: the project became a git repository on 2026-10-21, so a bad
migration edit during this run is now recoverable. It was not, for the whole
project before that point.)*

---

## Amendment log

| Date | Change | Approved by |
|---|---|---|
| 2026-10-21 | v1.0. **Corrects the "six plpgsql bodies" figure to five** across A14 and the S2 gate: the price-immutability trigger does not exist until S2 | cto |
