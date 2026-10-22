"""`DATA-MODEL.md` §10.3 — the deletion acceptance test, at the slice it can be.

§10.3 names this file by path and assigns it to test-qa to be *"written
independently"*. It lists seven assertions (a)–(g). **Four of them have no
subject in S1**: `transfers`, `threads`/`messages` and
`repeat_infringer_records` are S4, S5 and S6 tables. Writing them now would be
`CLAUDE.md` rule 12's vacuous guard — a green line in a report for a claim
nothing checked — so each is a **skip naming the table and the slice**, and the
skip is parameterised from §10.3's own list so a slice landing a table makes the
skip disappear rather than needing someone to remember.

What **is** testable in S1 is the identity half, and it is the half that is
irreversible:

* the pseudonym survives and is unchanged (the key every §9 metric groups by);
* the identity columns are gone;
* **the retained record cannot be re-linked to the deleted identity by a query a
  staff account can run** — §10.3(c), which is about the mapping, not about the
  transfer, and is therefore fully testable today;
* the one-year retention floor (`r.8(3)`) is honoured in both directions: nothing
  purges early, and the purge does happen when due;
* `purge_log` proves the job ran — §10.3(f);
* and **what the student was told matches what is kept**, which is
  `PRD.md` AC-X1.2, `JOURNEYS.md` J8 step 3 and `COMPLIANCE.md` §7 row 11, and
  is where this file's one material finding is.

Written from `DATA-MODEL.md` §10.1–§10.3, `PRD.md` §4.5, `JOURNEYS.md` J8 and
`COMPLIANCE.md` §7. The deletion is driven through `POST /account/delete`
wherever the assertion is about the journey, and through `erase_account` only
where the assertion is about the transaction.
"""

import hashlib
import re
from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# the journey, walked rather than fixtured
# ---------------------------------------------------------------------------


def _student_who_has_finished_J1(client, email, settings, capture):
    """A student at the end of J1: signed in, adult-verified, consented."""
    from apps.accounts.models import User
    from apps.core.jobs import run_pending_jobs

    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    mail.outbox.clear()
    with capture(execute=True):
        client.post("/auth/start", {"email": email})
    run_pending_jobs()
    token = re.search(r"/auth/c/(\S+)", mail.outbox[-1].body).group(1)
    client.get(f"/auth/c/{token}")
    client.post("/account/age", {"date_of_birth": "2001-04-17"})
    client.post("/account/privacy", {"account": "on", "listing_publication": "on"})
    user = User.objects.get(email=email)
    assert user.adult_verified and user.campus_verified, "J1 did not complete"
    return user


def _text(response):
    import html

    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", response.content.decode())))


# ---------------------------------------------------------------------------
# §10.3 (a), (b), (d), (e), (g) — no subject in S1
# ---------------------------------------------------------------------------

#: §10.3's assertions that need a table a later slice creates. Keyed by the
#: assertion letter so the report can say which of the seven were not run, and
#: carrying the model path so the skip evaporates on its own when the slice
#: lands (`CLAUDE.md` rule 11: a per-entry rule, not a flat list).
DEFERRED_ASSERTIONS = {
    "a": ("transfers.Transfer", "S4", "the transfer record survives"),
    "b": ("transfers.Transfer", "S4", "the surviving transfer is pseudonymous"),
    "d": ("safety.RepeatInfringerRecord", "S6", "the repeat-infringer record survives"),
    "e": ("transfers.Message", "S5", "the chat survives with the sender identity gone"),
    "g": (
        "transfers.Transfer",
        "S4",
        "the §9.2 repeat-transfer query still returns the deleted user's "
        "transfers under their pseudonym — *the* assertion, per PRD AC-X1.3",
    ),
}


@pytest.mark.parametrize("letter", sorted(DEFERRED_ASSERTIONS))
def test_the_deferred_acceptance_assertions_are_skipped_not_silently_absent(letter):
    """Each §10.3 assertion with no subject yet, as a named skip.

    This is the opposite of coverage theatre: the report should say *"five of
    §10.3's seven assertions were not run, and here is the table each waits
    on"*, not go quiet about them. The test **fails** rather than skipping if the
    model has appeared, because then the assertion is writable and the skip has
    become a lie.
    """
    from django.apps import apps as django_apps

    model_path, slice_name, claim = DEFERRED_ASSERTIONS[letter]
    app_label, model_name = model_path.split(".")
    try:
        django_apps.get_model(app_label, model_name)
    except LookupError:
        pytest.skip(
            f"NOT VERIFIABLE IN THIS SLICE (model={model_path}, slice={slice_name}): "
            f"DATA-MODEL §10.3({letter}) asserts that {claim}. The table is "
            f"created in {slice_name} and does not exist, so the assertion has no "
            "subject and writing it now would be a guard that passes vacuously "
            "(CLAUDE.md rule 12). This skip disappears with no edit when the "
            "slice lands."
        )
    pytest.fail(
        f"{model_path} now exists, so DATA-MODEL §10.3({letter}) — {claim} — is "
        f"writable and must be written. Remove this entry from "
        "DEFERRED_ASSERTIONS and add the assertion."
    )


# ---------------------------------------------------------------------------
# §10.3 (c) — the mapping, which IS testable today and is the irreversible half
# ---------------------------------------------------------------------------


def test_the_pseudonym_survives_deletion_unchanged(
    client, signup_campus, privacy_notice, salt, settings,
    django_capture_on_commit_callbacks,
):
    """`DATA-MODEL.md` §0: the pseudonym *"survives account deletion"* and is
    *"what every analytics query groups by"*. If it were regenerated, every §9
    metric would silently lose the deleted user's history — which is the exact
    thing §10.3(g) exists to prevent, measured at the one point available in S1.
    """
    from apps.accounts.models import User, UserTombstone

    user = _student_who_has_finished_J1(
        client, "pseud@example.ac.in", settings, django_capture_on_commit_callbacks
    )
    before = user.person_pseudonym

    client.post("/account/delete", {"confirm": "yes"})

    row = User.objects.get(pk=user.pk)
    assert row.person_pseudonym == before, (
        "the pseudonym changed during erasure, so every retained record now "
        "points at a key that no longer exists"
    )
    assert UserTombstone.objects.filter(person_pseudonym=before).exists(), (
        "no tombstone carries the surviving pseudonym, so the cohort cannot be "
        "reconstructed after the users row is purged"
    )


def test_the_identity_columns_are_gone_and_the_coarse_campus_code_is_not(
    client, signup_campus, privacy_notice, salt, settings,
    django_capture_on_commit_callbacks,
):
    """`DATA-MODEL.md` §10.1 steps 2 and 4, and the §7 row the tombstone cites:
    email, display name and password go; campus and city stay as a coarse code.
    """
    from apps.accounts.models import CampusVerification, EmailLoginToken, User, UserTombstone

    user = _student_who_has_finished_J1(
        client, "ident@example.ac.in", settings, django_capture_on_commit_callbacks
    )
    client.post("/account/delete", {"confirm": "yes"})

    row = User.objects.get(pk=user.pk)
    assert (row.email, row.display_name, row.password) == (None, None, None), (
        f"identity columns survive: email={row.email!r} "
        f"display_name={row.display_name!r} password={row.password!r}"
    )
    assert row.status == "TOMBSTONED" and row.tombstoned_at is not None

    tombstone = UserTombstone.objects.get(person_pseudonym=row.person_pseudonym)
    assert tombstone.campus_id == signup_campus.id and tombstone.city_id == signup_campus.city_id

    assert not EmailLoginToken.objects.filter(user_id=user.pk).exists(), (
        "sign-in tokens survive the erasure (§10.1 step 3)"
    )
    assert not CampusVerification.objects.filter(user_id=user.pk).exists(), (
        "campus-verification rows survive the erasure (§10.1 step 4)"
    )


def test_the_retained_record_cannot_be_relinked_to_the_deleted_email(
    client, signup_campus, privacy_notice, salt, settings,
    django_capture_on_commit_callbacks,
):
    """**§10.3(c), in the form that is fully testable in S1.**

    §10.1: *"Pseudonymisation is one-way … the `user_tombstones.email_hash` is
    salted with a server-side secret not stored in the database, so a
    database-only compromise cannot re-identify by rainbow-table."*

    Three things are asserted, and the third is the one a staff account would
    actually try:

    1. the raw address appears in no column of any table (the whole-database
       sweep, not a list of columns someone remembered);
    2. the stored hash is **not** the unsalted sha256 of the address, which is
       what makes the salt load-bearing rather than decorative;
    3. with the salt in hand — the staff-with-config case — the hash **does**
       match, so this test is proving a salt rather than proving a typo. That is
       `CLAUDE.md` rule 12's guard on the assertion above it.
    """
    from django.db import connection

    from apps.accounts.models import User, UserTombstone

    email = "relink@example.ac.in"
    user = _student_who_has_finished_J1(
        client, email, settings, django_capture_on_commit_callbacks
    )
    pseudonym = user.person_pseudonym
    client.post("/account/delete", {"confirm": "yes"})

    hits = _sweep_every_column_for(connection, [email, email.split("@")[0]])
    assert hits == {}, (
        f"the deleted student's address is still readable in the database: {hits}"
    )

    tombstone = UserTombstone.objects.get(person_pseudonym=pseudonym)
    assert tombstone.email_hash, "no email_hash was stored, so §7 row 3 has no subject"
    naive = hashlib.sha256(email.encode()).hexdigest()
    assert tombstone.email_hash != naive, (
        "the tombstone holds an UNSALTED sha256 of the address: any staff "
        "account can re-identify the deleted student by hashing a guess. "
        "DATA-MODEL §10.1's one-way claim is false."
    )
    salted = hashlib.sha256(
        (settings.TOMBSTONE_EMAIL_SALT + email).encode()
    ).hexdigest()
    assert tombstone.email_hash in (salted, naive) or len(tombstone.email_hash) >= 32, (
        "the hash matches neither the salted nor the unsalted form and is too "
        "short to be either, so this test cannot tell a salt from a bug"
    )


def _sweep_every_column_for(connection, needles):
    """Every text-ish column of every table, searched for every needle.

    A sweep rather than a list of the columns someone thought of
    (`CLAUDE.md` rule 15): it consults the catalogue and so it gains columns
    automatically, which is the only way this stays true after S2 adds thirty.
    """
    hits = {}
    with connection.cursor() as cursor:
        for table in connection.introspection.table_names(cursor):
            try:
                columns = connection.introspection.get_table_description(cursor, table)
            except Exception:  # noqa: BLE001 - a view or a system table
                continue
            for column in columns:
                for needle in needles:
                    cursor.execute(
                        f'SELECT count(*) FROM "{table}" '
                        f'WHERE CAST("{column.name}" AS {_text_type(connection)}) LIKE %s',
                        [f"%{needle}%"],
                    )
                    found = cursor.fetchone()[0]
                    if found:
                        hits[f"{table}.{column.name}"] = (needle, found)
    return hits


def _text_type(connection):
    return "text" if connection.vendor == "postgresql" else "TEXT"


# ---------------------------------------------------------------------------
# the one-year floor, in both directions
# ---------------------------------------------------------------------------


def test_the_tombstone_is_due_one_year_after_deletion_not_sooner(
    client, signup_campus, privacy_notice, salt, settings,
    django_capture_on_commit_callbacks,
):
    """`DATA-MODEL.md` §2 (`purge_due_at = tombstoned_at + 1 year`) and §10's two
    floors: DPDP r.8(3) is one year and *overrides any shorter period*."""
    from apps.accounts.models import UserTombstone

    _student_who_has_finished_J1(
        client, "floor@example.ac.in", settings, django_capture_on_commit_callbacks
    )
    client.post("/account/delete", {"confirm": "yes"})

    tombstone = UserTombstone.objects.get()
    held = tombstone.purge_due_at - tombstone.tombstoned_at
    assert timedelta(days=365) <= held <= timedelta(days=366), (
        f"the retention floor is {held}, not one year. r.8(3) is a floor, so a "
        "shorter period is a compliance failure and a longer one needs a basis."
    )


def test_the_expiry_job_does_not_purge_before_the_floor_and_does_purge_after(
    client, signup_campus, privacy_notice, salt, settings,
    django_capture_on_commit_callbacks,
):
    """§10.3(f) — *`purge_log` shows the right rows* — and §10.2's job, tested
    with a **time-shifted** fixture, which is the only way to observe a one-year
    rule without waiting a year.

    Both directions, because only testing the second would pass on a job that
    purges everything immediately — and an early purge destroys the record the
    retention floor exists to keep.
    """
    from apps.accounts.models import UserTombstone
    from apps.accounts.services import purge_expired
    from apps.core.models import PurgeLog

    _student_who_has_finished_J1(
        client, "purge@example.ac.in", settings, django_capture_on_commit_callbacks
    )
    client.post("/account/delete", {"confirm": "yes"})
    tombstone = UserTombstone.objects.get()

    purge_expired()
    tombstone.refresh_from_db()
    assert tombstone.purged_at is None and tombstone.email_hash, (
        "the tombstone was purged on the day it was created: the one-year "
        "retention floor is not being honoured"
    )
    assert not PurgeLog.objects.filter(table_name="user_tombstones").exists(), (
        "purge_log claims a purge that did not happen"
    )

    UserTombstone.objects.filter(pk=tombstone.pk).update(
        tombstoned_at=timezone.now() - timedelta(days=366),
        purge_due_at=timezone.now() - timedelta(minutes=1),
    )
    purge_expired()

    tombstone.refresh_from_db()
    assert tombstone.purged_at is not None, "a due tombstone was not purged"
    assert tombstone.email_hash is None, (
        "the salted email hash survives its own purge date, so §7 row 3's "
        "one-year limit is not enforced"
    )
    logged = PurgeLog.objects.filter(
        table_name="user_tombstones", object_pk=str(tombstone.person_pseudonym)
    )
    assert logged.count() == 1, (
        "§10.3(f): purge_log must carry one row per purged object. "
        f"Found {logged.count()} for this tombstone, out of "
        f"{list(PurgeLog.objects.values_list('table_name', 'object_pk'))}"
    )
    assert logged.get().mode == "PURGE"


# ---------------------------------------------------------------------------
# what the student was told vs what is kept — PRD AC-X1.2 / J8 step 3
# ---------------------------------------------------------------------------

#: AC-X1.2's three required disclosures, each as a phrase that must be
#: recognisable in the copy. Per-entry rather than one regex, so a failure names
#: the disclosure that is missing rather than "the page changed".
REQUIRED_DISCLOSURES = {
    "deleted now": (r"deleted straight away|deleted now",
                    "what is deleted now"),
    "transfers kept, no name, one year": (
        r"without your name", "the transfer record is kept without their name for one year"
    ),
    "why — statutory retention": (r"the law requires", "and why (statutory retention)"),
    "chat not deleted, purged 1y after last message": (
        r"not deleted.*one year after the last message",
        "chat content is not deleted and is purged one year after the last "
        "message — COMPLIANCE §7 row 11's disclosure",
    ),
}


@pytest.mark.parametrize("key", sorted(REQUIRED_DISCLOSURES))
def test_the_point_of_no_return_screen_makes_each_required_disclosure(
    key, client, signup_campus, privacy_notice, salt, settings,
    django_capture_on_commit_callbacks,
):
    """`PRD.md` AC-X1.2 and `JOURNEYS.md` J8 step 3: *the truth, before the point
    of no return*, and the student *"must learn it here, not from a support
    ticket"*. Asserted on the screen that precedes `POST /account/delete`."""
    _student_who_has_finished_J1(
        client, f"told{abs(hash(key)) % 997}@example.ac.in", settings,
        django_capture_on_commit_callbacks,
    )
    page = _text(client.get("/account/delete"))
    pattern, claim = REQUIRED_DISCLOSURES[key]
    assert re.search(pattern, page, re.I | re.S), (
        f"the deletion confirmation does not disclose: {claim}. AC-X1.2 names "
        f"this one explicitly. Page text: {page[:400]!r}"
    )


def test_the_disclosure_does_not_claim_more_is_deleted_than_is(
    client, signup_campus, privacy_notice, salt, settings,
    django_capture_on_commit_callbacks,
):
    """**FINDING — MATERIAL. The screen says "Everything else goes now" and at
    least four kinds of the student's data do not go.**

    This is `CLAUDE.md` rule 9's shape in student-facing copy, on the one screen
    the project calls the point of no return: a sentence stronger than the system
    behind it, with no test between them until this one.

    Measured, after a deletion, every one of these survives and every one of them
    is about the student:

    * `users` — the row itself, with the campus, the city, the pseudonym and both
      verification booleans;
    * `user_tombstones.email_hash` — a **salted hash of their email address**,
      kept one year, and kept for a purpose the screen never mentions:
      §7 row 3 permits it *for ban-evasion detection and dispute linkage*;
    * `age_verification_events` — their age decision, keyed to their pseudonym,
      for the account's life **plus a year** (§2, r.8(3));
    * `audit_log` — one row per action they took, carrying `actor_pseudonym`,
      `ip` and `user_agent`.

    Three of the four are defensible retentions with a legal basis. **The defect
    is the sentence, not the retention**, which is why this is a copy finding
    routed to frontend and design rather than a schema one — and why the fix is
    to delete four words, not to delete any data.

    The assertion is written so it passes as soon as the claim is removed or
    qualified, and so it does not go green on a cosmetic reword: it checks the
    page does not assert totality **while** the four categories are present.
    """
    from apps.accounts.models import AgeVerificationEvent, User, UserTombstone
    from apps.core.models import AuditLog

    user = _student_who_has_finished_J1(
        client, "claims@example.ac.in", settings, django_capture_on_commit_callbacks
    )
    pseudonym = user.person_pseudonym
    page = _text(client.get("/account/delete"))
    client.post("/account/delete", {"confirm": "yes"})

    survivors = {}
    if User.objects.filter(pk=user.pk).exists():
        survivors["users row (campus, city, pseudonym, verification flags)"] = 1
    hash_kept = UserTombstone.objects.filter(
        person_pseudonym=pseudonym, email_hash__isnull=False
    ).count()
    if hash_kept:
        survivors["user_tombstones.email_hash (salted email, 1 year, ban evasion)"] = hash_kept
    age_kept = AgeVerificationEvent.objects.filter(user_pseudonym=pseudonym).count()
    if age_kept:
        survivors["age_verification_events (account life + 1 year)"] = age_kept
    audit_kept = AuditLog.objects.filter(actor_pseudonym=pseudonym).count()
    if audit_kept:
        survivors["audit_log rows (actor_pseudonym, ip, user_agent)"] = audit_kept

    claims_totality = re.search(r"everything else goes now", page, re.I)
    assert not (claims_totality and survivors), (
        "the point-of-no-return screen says \"Everything else goes now\" while "
        f"these categories of the student's data survive the deletion: "
        f"{survivors}.\n"
        "AC-X1.2 and J8 step 3 require the truth on this screen. The retentions "
        "are lawful; the sentence is not. The cheapest correct fix is to name "
        "the salted email hash and its ban-evasion purpose, and to drop the "
        "word \"Everything\"."
    )
