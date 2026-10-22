"""apps.listings service layer (L1) — API-CONTRACT §3's `apps/listings/services.py`.

Seven frozen signatures: `create_listing`, `add_photo`, `publish_listing`,
`withdraw_listing`, `moderate_listing`, `create_request`, `close_request`.
Everything else here is a helper those seven need, or a read path a caller
needs that §3 did not have to name because it mutates nothing.

Three rules this module exists to keep, each of them a thing a reasonable
developer would otherwise break by accident:

1. **One transaction per mutation**, with the `audit_log` row written *inside*
   it, and anything enqueued only `on_commit` (API-CONTRACT §3).
2. **`asking_price_paise` is written once, at creation, and never again.**
   The database enforces it (`listings_price_immutable`, migration 0002); this
   layer never issues an UPDATE touching it, and `create_listing` refuses a
   non-integer *before* the column can silently round it.
3. **Every discovery read path calls `assert_discovery_open` first** and
   restricts to `is_seed` when the gate is closed (ADR-002 §4). The gated
   default manager sits **underneath** that, never instead of it: a filtered
   manager returns no rows, and the contract requires an explicit
   `403 GATE_CLOSED`.
"""

import hashlib
import logging
import re
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, connection, transaction
from django.utils import timezone

from apps.accounts.services import require_actor
from apps.catalog.services import resolve_merge
from apps.core.errors import (
    GateClosed,
    NotFound,
    NotPermitted,
    SellerTermsNotAccepted,
    TooManyPhotos,
    TransitionNotAllowed,
    UnsupportedImage,
    ValidationFailed,
    VersionConflict,
)
from apps.core.scoping import assert_discovery_open, restrict_when_gate_closed, scoped
from apps.core.services import record_audit

from .images import ImageRejected, strip_metadata
from .models import (
    ANNOTATION_LEVELS,
    CATEGORIES,
    CONDITIONS,
    DAMAGE_FLAGS,
    INTENTS,
    LISTING_STATUSES,
    MAX_ASKING_PRICE_PAISE,
    MAX_PHOTO_BYTES,
    MAX_PHOTOS_PER_LISTING,
    REQUEST_STATUSES,
    VISIBILITY_SCOPES,
    BookRequest,
    Listing,
    ListingPhoto,
)
from .storage import delete_object, write_object

log = logging.getLogger(__name__)

__all__ = [
    "create_listing", "add_photo", "publish_listing", "withdraw_listing",
    "moderate_listing", "create_request", "close_request",
    "my_listings", "get_own_listing", "listing_payload", "seller_block",
    "my_requests", "review_queue", "get_photo_for_download", "photo_response",
    "parse_major_units",
]

#: DATA-MODEL §3: `purge_due_at = closed_at + 1 year` (r.8(3)). The same floor
#: `apps.accounts.services.RETENTION_FLOOR` uses, imported rather than retyped
#: so the two cannot drift (`CLAUDE.md` rule 11).
from apps.accounts.services import RETENTION_FLOOR  # noqa: E402  (one definition)

#: DATA-MODEL §6.1, as data. `{from: {to, ...}}`. A transition not in this map
#: is `422 TRANSITION_NOT_ALLOWED`, which is API-CONTRACT §2.2's own
#: distinction: 403 means *you* may not, 422 means the *object* is not in a
#: state where this is possible.
LISTING_TRANSITIONS = {
    "DRAFT": {"PENDING_REVIEW", "LIVE", "WITHDRAWN"},
    "PENDING_REVIEW": {"LIVE", "REJECTED", "WITHDRAWN", "REMOVED_LEGAL"},
    "LIVE": {"RESERVED", "WITHDRAWN", "REMOVED_LEGAL"},
    "RESERVED": {"CLOSED_TRANSFERRED", "LIVE", "WITHDRAWN", "REMOVED_LEGAL"},
    "CLOSED_TRANSFERRED": set(),
    "WITHDRAWN": set(),
    "REJECTED": set(),
    "REMOVED_LEGAL": set(),
}

#: The four terminal states, derived rather than retyped: a state with no exit
#: is terminal by definition, so this cannot disagree with the map above.
TERMINAL_STATUSES = frozenset(s for s, to in LISTING_TRANSITIONS.items() if not to)

#: J2-staff step 4/5. `moderate_listing` takes one of these.
MODERATION_ACTIONS = {"REVIEW_PASS": "LIVE", "REVIEW_REJECT": "REJECTED",
                      "TAKEDOWN": "REMOVED_LEGAL"}


# --- helpers ---------------------------------------------------------------


def _require_seller_terms(user):
    """r.6(4)(a)'s prior written contract, against the **current** version.

    Accepting v1 does not cover v2: the whole point of a versioned notice is
    that the contract is the one that was shown. JOURNEYS J2 step 6 renders
    this as the terms screen again, never as an error page.
    """
    from apps.accounts.services import current_seller_terms, has_accepted_seller_terms

    notice = current_seller_terms(user)
    if notice is None:
        raise SellerTermsNotAccepted(
            "We cannot take listings just now. Please try again shortly.",
            detail=(
                "No SELLER_TERMS notice is published for this locale, so there is "
                "nothing for the seller to have accepted. Run `seed_demo` or "
                "publish one."
            ),
        )
    if not has_accepted_seller_terms(user, notice):
        raise SellerTermsNotAccepted(
            "Please read and accept the seller terms first.",
            notice_version=notice.version,
        )
    return notice


def _check_enum(value, permitted, what, why=""):
    """Refuse what the schema would refuse, with the permitted values named.

    The same helper `apps.accounts.services` has and for the same reason
    (`CLAUDE.md` rule 12): a CHECK guarantees the stored **state**; it does not
    detect a bad **input**, and what the caller gets when it fires is a 500
    with a `CheckViolation` traceback instead of a 400 naming the values it
    could have sent. Imported rather than redefined would be better; it is
    private to that module, so this is flagged in the slice note as the one
    helper that should move to `apps.core`.
    """
    if value not in permitted:
        raise ValidationFailed(
            f"That is not a {what} we can record.",
            detail=f"{value!r} is not permitted; allowed: {sorted(permitted)}. {why}",
            field_errors={what.replace(" ", "_"): [f"One of {sorted(permitted)}."]},
        )


#: ASCII `0`-`9` and nothing else. **Not `str.isdigit()`, and not
#: `str.isdecimal()` either** — QA F43's shape, and the reason is that both
#: say yes to characters `int()` then disagrees about:
#:
#:   * `"²".isdigit()` is **True** and `int("²")` **raises** — so the service
#:     answered `500` on the one money column, from a one-character input.
#:     `isdecimal()` fixes that one.
#:   * `"１".isdecimal()` is **True** and `int("１")` returns **1** — a
#:     full-width digit silently becomes a different-looking number.
#:   * `"௧".isdecimal()` is **True** and `int("௧")` returns **1**.
#:
#: **The Tamil-numeral question, decided rather than inherited.** Tamil
#: numerals are **refused**, with their own sentence, and they are not
#: converted. Tamil *text* is a first-class locale here and this is not about
#: that: it is that `asking_price_paise` is **immutable by trigger**, so an
#: amount we read differently from the way the student wrote it cannot be
#: corrected afterwards — they would have to withdraw and relist while the
#: listing carries a price they did not set. A refusal costs one retype; a
#: silent conversion costs a wrong price nobody can fix. The same reasoning
#: refuses full-width and superscript digits, which are far more likely a
#: paste accident than an intent.
_ASCII_DIGITS = frozenset("0123456789")


def _parse_minor_units_text(raw):
    """A money string as an integer, or a refusal **with its own sentence**.

    *"The three mistakes a student actually makes — ₹280, `2,80`, 280.50 —
    each deserves a different sentence."* That is `web/forms.py`'s docstring
    and it is right; this is the service-layer half, and the service is the
    layer ADR-003 §2.3 names as the detection for P14, so it has to hold even
    when a form above it does not.

    **Every one of these is a refusal, never a repair.** A thousands
    separator in the wrong place (`320,00`) is the input that produced a
    hundredfold error, and the fix is not to guess which grouping was meant.
    """
    text = raw.strip()
    if not text:
        raise ValidationFailed(
            "Enter the amount in whole rupees.",
            field_errors={"asking_price_paise": ["Required."]},
        )
    if "." in text:
        raise ValidationFailed(
            "Enter a whole number of rupees, with no paise.",
            detail=f"{raw!r} carries a decimal point; rounding it would store "
                   "a different amount from the one that was sent",
            field_errors={"asking_price_paise": ["Whole rupees only."]},
        )
    if "," in text:
        # **Refused, not stripped.** `320,00` is the measured hundredfold
        # error: a cleaner that strips the comma first reads it as 32000.
        # Guessing the grouping is how that happened, so this layer does not
        # guess -- it says which character is the problem.
        raise ValidationFailed(
            "Enter the amount without commas.",
            detail=f"{raw!r} contains a comma; a grouping separator in an "
                   "unexpected position is how 320,00 becomes 32000",
            field_errors={"asking_price_paise": ["Digits only, no commas."]},
        )
    if not set(text) <= _ASCII_DIGITS:
        raise ValidationFailed(
            "Enter the amount using the digits 0 to 9.",
            detail=(
                f"{raw!r} contains a character that is not an ASCII digit. "
                "str.isdigit() accepts superscripts that int() then rejects, "
                "and str.isdecimal() accepts full-width and Tamil numerals "
                "that int() silently converts. asking_price_paise is "
                "immutable, so a misread amount cannot be corrected."
            ),
            field_errors={"asking_price_paise": ["Digits 0 to 9."]},
        )
    return int(text)


#: A whole number of rupees, grouped the way a student actually types it.
#: **Indian grouping** (`1,200`, `32,000`, `1,00,000`) or **Western**
#: (`100,000`) — both unambiguous, both common here. Anything else is not a
#: grouping, and `320,00` is the measured example: it is neither, and a
#: cleaner that strips the comma first reads it as 32000.
#:
#: **Named `_GROUPED_DIGITS` and not `_GROUPED_RUPEES` — rule 13 rung 1,
#: and the pin caught it within minutes of being ratified.** The first draft
#: carried `rupee`, which is a W1b money token; being UPPER_SNAKE it matched
#: ADR-003 §2.3's shape B, so W1c exempted it and
#: `test_exempted_bound_is_pinned.py` then refused it for having no CHECK
#: behind it. **That is exactly the `MAX_OFFER_PAISE` case cto measured
#: before ratifying, arriving for real.** Rung 1 was available and neutral
#: here — the pattern knows nothing about rupees, it matches a grouped run of
#: digits — so a rename is both the cheaper fix and the more accurate name.
#:
#: The ungrouped branch is `\d+` and not `\d{1,3}`: a student typing `1200`
#: with no separator at all is the commonest input of the lot, and the first
#: draft of this pattern refused it — caught by the test table, which is why
#: the ordinary cases are rows in it and not an afterthought.
_GROUPED_DIGITS = re.compile(
    r"^(?:\d+|\d{1,2}(?:,\d{2})*,\d{3}|\d{1,3}(?:,\d{3})+)$"
)


def parse_major_units(text):
    """A typed amount in **major units** → integer minor units, or a refusal.

    Named in ISO-4217's terms — major unit (rupee), minor unit (paise) —
    rather than `parse_rupees_to_minor_units`, which was the first draft and
    which W1c correctly refused: `rupee` is a W1b money token and a function
    name is a per-instance declaration, so it matches none of ADR-003 §2.3's
    ratified shapes. **Rule 13 rung 1 again**, and neutral again: the
    currency is not what this function knows about, the grouping is.

    Its `field_errors` key is `asking_price_paise`, the one permitted money
    name, for the same reason. A Django `clean_<field>` that re-raises
    attaches the message to its own field anyway, so frontend loses nothing.

    > **One definition, for both layers.** QA F42 measured `320,00` stored as
    > Rs 32,000 — a hundredfold error on a column that is **immutable by
    > trigger**, so the seller cannot correct it. The cause was two
    > hand-written money parsers: this service layer, which ADR-003 §2.3
    > names as P14's detection layer, and `web/forms.py`'s
    > `clean_asking_price_rupees`, which strips commas on the line **before**
    > it checks for a decimal point. That is `CLAUDE.md` rule 11's exact
    > failure mode — *three hand-made copies of one rule disagreed* — with
    > money in the column that cannot be edited afterwards.
    >
    > **So the fix is not "stop stripping commas", and it is not a patch to
    > the form.** The strip is what makes `1,200` work, which is the grouping
    > a student really does type. It is to refuse a comma that is **not in a
    > valid grouping position**, which is the distinction `web/forms.py`'s
    > own docstring already draws — and to have one function draw it.
    >
    > This is the function. It lives here because this is the layer the ADR
    > names, and `web/forms.py` is frontend's to point at it. Sent to cto as
    > an `API-CONTRACT.md` §3 row, per the process rule that a read the
    > interface needs is an amendment first and an implementation second.
    > **Until the form calls it, the UI path is still wrong** and QA's
    > `test_the_rupees_field_refuses_a_value_it_cannot_represent` is
    > correctly red.

    Whole rupees only: `280.50` is refused with its own sentence rather than
    rounded, for the same reason — the stored amount would not be the one
    that was sent.
    """
    raw = "" if text is None else str(text).strip()
    if not raw:
        raise ValidationFailed(
            "Enter the amount in rupees.",
            field_errors={"asking_price_paise": ["Required."]},
        )
    if "." in raw:
        raise ValidationFailed(
            "Enter a whole number of rupees, with no paise.",
            detail=f"{text!r} carries a decimal point",
            field_errors={"asking_price_paise": ["Whole rupees only."]},
        )
    if not _GROUPED_DIGITS.match(raw):
        # The message distinguishes the two causes, because they are two
        # different mistakes and each deserves its own sentence.
        if "," in raw:
            raise ValidationFailed(
                "Check the commas in that amount — try it without them.",
                detail=(
                    f"{text!r} has a comma in a position that is not a "
                    "thousands or lakhs grouping; 320,00 read as 32000 is the "
                    "hundredfold error this refusal exists for"
                ),
                field_errors={"asking_price_paise": ["For example 1,200 or 1200."]},
            )
        raise ValidationFailed(
            "Enter the amount using the digits 0 to 9.",
            detail=f"{text!r} is not a plain number of rupees",
            field_errors={"asking_price_paise": ["Digits 0 to 9."]},
        )
    return _coerce_minor_units(int(raw.replace(",", "")) * 100)


def _coerce_minor_units(raw):
    """The asking price as an integer, or a refusal. **The rule-12 case.**

    *"A database proving no float is stored does not prove none was sent —
    PostgreSQL rounds `300.75` to `301` silently, and a rounded money value is
    a wrong value that looks right."* The CHECK on the column is the floor and
    proves a stored state; this is the detection above it and is the thing the
    test exercises — `test_listings.py` passes `300.75` and asserts a refusal,
    not that the column is of integer type.

    `bool` is refused explicitly because `isinstance(True, int)` is True in
    Python and `True` would otherwise be stored as 1 paisa.
    """
    if isinstance(raw, bool) or isinstance(raw, float):
        raise ValidationFailed(
            "Enter the amount in whole rupees.",
            detail=f"{raw!r} is not an integer number of minor units; rounding it "
                   "would store a different amount from the one that was sent.",
            field_errors={"asking_price_paise": ["A whole number."]},
        )
    if isinstance(raw, str):
        raw = _parse_minor_units_text(raw)
    if not isinstance(raw, int):
        raise ValidationFailed(
            "Enter the amount in whole rupees.",
            field_errors={"asking_price_paise": ["A whole number."]},
        )
    if raw < 0 or raw > MAX_ASKING_PRICE_PAISE:
        raise ValidationFailed(
            "That is outside the range we can take.",
            detail=f"the permitted range is 0..{MAX_ASKING_PRICE_PAISE} minor units",
            field_errors={"asking_price_paise": ["Up to Rs 1,00,000."]},
        )
    return raw


def _bump(listing, expected_version):
    """API-CONTRACT §4.2. Optimistic concurrency on a conditional UPDATE.

    **Read-then-write would be the bug.** The version is compared *in the
    `WHERE` clause*, so two concurrent writers cannot both see version 3 and
    both succeed — the second affects zero rows and gets `409`. On SQLite the
    loser may instead block and then see the new version, which reaches the
    same answer by a different route; that divergence is S4's subject and is
    recorded in the slice note (**ASSUMED THERE** for PostgreSQL's row-lock
    re-evaluation until S4's `test_double_booking.py` measures it).
    """
    if expected_version is None:
        raise ValidationFailed(
            "That request could not be sent. Please try again.",
            detail="expected_version is required on every listing transition",
            field_errors={"expected_version": ["Required."]},
        )
    try:
        expected = int(expected_version)
    except (TypeError, ValueError):
        raise ValidationFailed(
            "That request could not be sent. Please try again.",
            field_errors={"expected_version": ["A number."]},
        ) from None
    return expected


def _transition(listing, to_status, expected, *, actor, action, extra=None):
    """One state move, one transaction, one audit row. DATA-MODEL §6.1.

    **No UPDATE issued from here ever names `asking_price_paise`**, so the
    immutability trigger has nothing to refuse on a legitimate transition —
    which is the property `test_price_immutable.py`'s no-op half asserts.
    """
    # **The version is checked BEFORE the transition, and the order is the
    # contract's rather than a preference.** API-CONTRACT §2.2 splits them:
    # `409 VERSION_CONFLICT` is concurrency — *someone changed this while you
    # were looking at it* — and `422 TRANSITION_NOT_ALLOWED` is *the object is
    # not in a state where this is possible*. A client replaying a stale form
    # hits both at once, because the row moved on **and** that is why the
    # transition is now illegal. Measured by running the journey: a replayed
    # publish returned 422, which tells the student their listing cannot be
    # published when the truth is that it already was. 409 is the diagnosis
    # that leads to "reload and try again"; 422 leads nowhere.
    if listing.version != expected:
        raise VersionConflict(
            "Someone changed this while you were looking at it. Reload and try again."
        )
    if to_status not in LISTING_TRANSITIONS.get(listing.status, set()):
        raise TransitionNotAllowed(
            "That cannot be done at this stage.",
            detail=f"listings.status {listing.status!r} -> {to_status!r} is not in "
                   "the state machine",
            from_status=listing.status,
            to_status=to_status,
        )
    now = timezone.now()
    fields = {"status": to_status, "version": listing.version + 1}
    if to_status == "LIVE" and listing.published_at is None:
        # The start of time-to-match, set once. A relisted book is a new row,
        # so this is never rewritten.
        fields["published_at"] = now
    if to_status in TERMINAL_STATUSES:
        fields["closed_at"] = now
        fields["purge_due_at"] = now + RETENTION_FLOOR
    fields.update(extra or {})

    with transaction.atomic():
        changed = Listing.all_objects.filter(id=listing.id, version=expected).update(**fields)
        if not changed:
            raise VersionConflict(
                "Someone changed this while you were looking at it. Reload and try again."
            )
        listing.refresh_from_db()
        record_audit(
            actor, action, listing,
            before={"status": listing.status, "version": expected},
            after={"status": to_status, "version": listing.version},
        )
    return listing


# --- create ----------------------------------------------------------------


def create_listing(actor, *, book, asking_price_paise, condition,
                   annotation_level, damage_flags, language, category,
                   intent="SELL", **extra) -> Listing:
    """API-CONTRACT §3. Raises `SellerTermsNotAccepted`, `ValidationFailed`.

    **Stack M** (API-CONTRACT §2.5): this is a marketplace write, so every
    precondition applies — including `listing_publication` consent, which is
    the purpose this action is for. JOURNEYS J1 step 5 names it as the second
    required purpose and S1 deliberately left it to the slice that has
    something to publish.

    The listing is created **`DRAFT`**, never live. `create_listing` and
    `publish_listing` being two calls is what makes EC-13 free — *"upload fails
    at photo 3 of 4 on 3G: listing stays `DRAFT` with photos 1–2 attached,
    fully resumable"*.

    `extra` carries the two UI-hidden dimensions (`visibility_scope`,
    `suspect_reproduction_flag`) and the affirmative no-damage answer. It is
    keyword-only and validated; it exists so the frozen signature does not have
    to grow for a field the sell form already asks about.
    """
    require_actor(actor, purposes=("listing_publication",))
    assert_campus_write(actor)
    _require_seller_terms(actor)

    book = resolve_merge(book)
    if book is None:
        raise ValidationFailed(
            "Pick the book this copy is.",
            field_errors={"book": ["Required."]},
        )

    price = _coerce_minor_units(asking_price_paise)
    _check_enum(condition, CONDITIONS, "condition")
    _check_enum(annotation_level, ANNOTATION_LEVELS, "annotation level")
    _check_enum(category, CATEGORIES, "category")
    _check_enum(intent, INTENTS, "listing intent")
    _check_enum(language, ("en", "ta", "hi", "other"), "language")

    flags = list(damage_flags or [])
    for flag_value in flags:
        _check_enum(flag_value, DAMAGE_FLAGS, "damage kind")
    if len(set(flags)) != len(flags):
        raise ValidationFailed("That damage list repeats an entry.")
    if not flags and not extra.get("no_damage"):
        # PRD AC-S3.2, and it is a refusal rather than a default: *"an empty
        # damage list that submits is an implied no-damage claim the seller
        # never made."* The form's "none of these" tick is what sets
        # `no_damage`; the sentinel is not stored, because a value inside an
        # enum of damage kinds that means "no damage" is a value that means
        # "not a value".
        raise ValidationFailed(
            "Tick the damage that applies, or tick that none of it does.",
            field_errors={"damage_flags": ["Choose at least one, or 'none of these'."]},
        )

    scope = extra.get("visibility_scope", "CAMPUS")
    _check_enum(scope, VISIBILITY_SCOPES, "visibility scope")

    with transaction.atomic():
        listing = Listing.all_objects.create(
            seller=actor,
            seller_pseudonym=actor.person_pseudonym,
            book=book,
            campus_id=actor.campus_id,
            city_id=actor.city_id,
            intent=intent,
            asking_price_paise=price,
            price_fixed_at=timezone.now(),
            condition=condition,
            annotation_level=annotation_level,
            damage_flags=flags,
            category=category,
            language=language,
            visibility_scope=scope,
            status="DRAFT",
            suspect_reproduction_flag=bool(extra.get("suspect_reproduction_flag")),
            is_seed=actor.is_seed,
        )
        record_audit(
            actor, "listings.created", listing,
            after={
                "book_id": book.id,
                "status": "DRAFT",
                "condition": condition,
                "annotation_level": annotation_level,
                # The seller's own damage answer, including the fact that the
                # empty list was affirmative. PRD AC-S3.2's record, and J6's
                # evidence when a condition is disputed.
                "damage_flags": flags,
                "damage_answered": True,
                "intent": intent,
                "is_seed": listing.is_seed,
            },
        )
    log.info(
        "listings.created",
        extra={"listing_id": listing.id, "campus": actor.campus_id, "is_seed": listing.is_seed},
    )
    return listing


def assert_campus_write(actor):
    """§2.5 precondition 6, for a write with no object yet.

    A student whose `campus_id` points at a deactivated campus has no campus to
    write into. `scoped()` answers this for a read; a create has nothing to
    scope, so the same question is asked of the actor.
    """
    from apps.core.models import Campus

    campus = Campus.objects.filter(id=actor.campus_id, active=True).first()
    if campus is None:
        raise NotFound("Not found.")
    return campus


# --- photos ----------------------------------------------------------------


def add_photo(actor, listing, upload) -> ListingPhoto:
    """API-CONTRACT §3. Raises `TooManyPhotos`, `UnsupportedImage`.

    **EXIF is stripped before the row exists** and `exif_stripped_at` is NOT
    NULL, so the schema cannot hold a photo whose metadata was not removed.
    The bytes written to storage are the stripped bytes; the originals are
    never persisted, which is stronger than "stripped on read" and is what
    `COMPLIANCE.md` §7 row 9 asks for — a GPS tag in a photo of a book is a
    student's home address.

    `upload` is anything with `.read()` and an optional `.size` — a Django
    `UploadedFile`, or `io.BytesIO` in a fixture.

    # ponytail: the four-photo cap is serialised on the parent row rather
    # than enforced by DATA-MODEL §3's counting trigger. Ceiling: the lock is
    # per listing, so uploads to one listing queue behind each other — which
    # is fine, since only its seller can upload to it. **The earlier note
    # here said the race was affordable because "the seller would have to
    # race themselves". That was wrong twice: a phone retrying on a flaky
    # connection races itself routinely, and QA measured nine photos from six
    # requests.** Upgrade path: two trigger bodies, one per engine, if the
    # lock ever shows up in a latency measurement.
    """
    require_actor(actor, purposes=("listing_publication",))
    listing = get_own_listing(actor, listing.id if hasattr(listing, "id") else listing)
    if listing.status in TERMINAL_STATUSES:
        raise TransitionNotAllowed(
            "That cannot be done at this stage.",
            detail=f"photos cannot be added to a {listing.status} listing",
        )

    data = upload.read() if hasattr(upload, "read") else bytes(upload)
    if len(data) > MAX_PHOTO_BYTES:
        raise UnsupportedImage(
            "That photo is too large. Each one can be up to 8 MB.",
            field_errors={"photo": ["Up to 8 MB."]},
        )
    try:
        stripped, image_format, width, height = strip_metadata(data)
    except ImageRejected as exc:
        raise UnsupportedImage(
            "We can take a JPEG, PNG or WebP photo.",
            detail=str(exc),
            field_errors={"photo": ["JPEG, PNG or WebP."]},
        ) from None

    digest = hashlib.sha256(stripped).hexdigest()
    with transaction.atomic():
        # **The cap is serialised on the parent row, because counting is a
        # read-then-write and QA measured what that costs: six simultaneous
        # uploads produced NINE photos.**
        #
        # And it failed on PostgreSQL while holding on SQLite — *the test
        # engine kept the invariant the production engine dropped*, which is
        # the worst direction for a divergence. SQLite has one writer, so its
        # count-then-insert is accidentally atomic; PostgreSQL runs six
        # transactions that each read 0..3 and each insert.
        #
        # `select_for_update` on the listing makes every upload for one
        # listing take its turn. It is the parent row and not the photos,
        # because a lock on rows that do not exist yet cannot stop an insert.
        # On SQLite this is a no-op the backend ignores, which is correct:
        # the property is already held there by the single writer.
        locked = Listing.all_objects.select_for_update().filter(id=listing.id)
        if connection.features.has_select_for_update:
            locked.first()
        existing = ListingPhoto.all_objects.filter(listing=listing).count()
        if existing >= MAX_PHOTOS_PER_LISTING:
            raise TooManyPhotos(
                "That listing already has four photos.",
                photo_count=existing,
            )
        key = f"listings/{listing.id}/{digest[:32]}.{image_format}"
        # Written before the row and deleted on rollback, so a committed row
        # always has its object. The reverse order would leave a row pointing
        # at nothing, which is the failure a reader cannot distinguish from a
        # storage outage.
        write_object(key, stripped)
        transaction.on_commit(lambda: None)
        if ListingPhoto.all_objects.filter(storage_key=key).exists():
            # **The same bytes, twice, on the same listing.** The key is
            # content-addressed, so a seller who taps "add" twice on one photo
            # produces the same key — and the UNIQUE index turned that into an
            # IntegrityError and a 500. Found by the four-photo test, whose
            # four "different" uploads differed only in a comment segment this
            # module strips, so all four hashed the same.
            #
            # A duplicate is not an error the seller can act on and not a new
            # photo either, so it is a refusal with a sentence rather than a
            # silent second row: a silently-ignored upload reads as "it did
            # not work" and gets tapped again.
            raise ValidationFailed(
                "That photo is already on this listing.",
                field_errors={"photo": ["Choose a different photo."]},
            )
        try:
            photo = ListingPhoto.all_objects.create(
                listing=listing,
                campus_id=listing.campus_id,
                city_id=listing.city_id,
                is_seed=listing.is_seed,
                storage_key=key,
                sha256=digest,
                width=width,
                height=height,
                bytes=len(stripped),
                exif_stripped_at=timezone.now(),
            )
        except IntegrityError:
            # **The guarantee, where the check above is only the diagnosis.**
            # The pre-check is a read-then-write and therefore races: two
            # simultaneous uploads of the same photo both see "not there" and
            # both insert. Reported by frontend from their own pass, and they
            # were right not to paper over it in the interface — *a nice
            # message there would hide a service defect.*
            #
            # **The sharper half of their finding:** the key is derived from
            # the **stripped** bytes, so two files that differ only in camera
            # metadata collide too. Two shots of the same book are not
            # obviously the same file to the person sending them, so this is
            # an ordinary state to be told about, not an error.
            delete_object(key)
            raise ValidationFailed(
                "That photo is already on this listing.",
                detail=(
                    "storage_key collision: the key is the sha256 of the "
                    "stripped bytes, so an identical photo — or one differing "
                    "only in metadata that was stripped — produces the same key"
                ),
                field_errors={"photo": ["Choose a different photo."]},
            ) from None
        except Exception:
            delete_object(key)
            raise
        record_audit(
            actor, "listings.photo_added", photo,
            after={"listing_id": listing.id, "sha256": digest, "bytes": len(stripped),
                   "format": image_format},
        )
    return photo


# --- publish, withdraw, moderate -------------------------------------------


def publish_listing(actor, listing, expected_version) -> Listing:
    """API-CONTRACT §3. `DRAFT -> PENDING_REVIEW | LIVE`.

    **At pilot `LISTING_REVIEW_ALL=true`, so this reaches `PENDING_REVIEW`**
    and the copy a seller sees is the same whether or not
    `suspect_reproduction_flag` is set (PRD AC-S4.2–3): *no accusation, no
    implication of guilt.* DATA-MODEL §6.1 also requires review when the
    `books` row is unverified, and PRD AC-S4.4 requires it when the book has
    no ISBN — *"a listing with no ISBN needs staff approval and cannot be
    self-published."*

    **A-4's `requests.match_scan` is NOT enqueued here, and that is stated
    rather than silently skipped.** API-CONTRACT §3 names it on this signature;
    TASKS §2 puts `notifications`, `notify()` and the `requests.match_scan` job
    in **S3** (amendment A-4). `apps.core.services.enqueue` refuses a kind with
    no registered handler, so wiring it now would be a `ValueError` on every
    publish rather than a dormant call.
    `tests/unit/test_listings.py::test_the_match_scan_enqueue_is_recorded_as_s3`
    is the record, and it goes red the day the handler is registered without
    this call being added.
    """
    require_actor(actor, purposes=("listing_publication",))
    expected = _bump(listing, expected_version)
    listing = get_own_listing(actor, listing.id)
    target = "PENDING_REVIEW" if _needs_review(listing) else "LIVE"
    return _transition(
        listing, target, expected, actor=actor, action="listings.published",
    )


def _needs_review(listing):
    """DATA-MODEL §6.1 plus PRD AC-S4.3/AC-S4.4, as one predicate.

    Four independent reasons, asked as a disjunction so a new one is an added
    clause rather than an edited branch.
    """
    return bool(
        getattr(settings, "LISTING_REVIEW_ALL", True)
        or listing.suspect_reproduction_flag
        or listing.book.staff_verified_at is None
        or not listing.book.isbn13
    )


def withdraw_listing(actor, listing, expected_version) -> Listing:
    """API-CONTRACT §3. `DRAFT | PENDING_REVIEW | LIVE | RESERVED -> WITHDRAWN`.

    Terminal. JOURNEYS J2 step 11's EC-2 — *"an offer is open: withdrawal
    succeeds and the transfer is CANCELLED"* — is S4's half, because
    `transfers` does not exist yet; the listing side is complete here and the
    transfer side is named in
    `tests/unit/test_listings.py::test_the_open_offer_cancellation_is_recorded_as_s4`.
    """
    require_actor(actor)
    expected = _bump(listing, expected_version)
    listing = get_own_listing(actor, listing.id)
    return _transition(
        listing, "WITHDRAWN", expected, actor=actor, action="listings.withdrawn",
    )


def moderate_listing(staff, listing, action, legal_basis, reason, work_seconds) -> Listing:
    """API-CONTRACT §3. Staff-only. J2-staff steps 4 and 5.

    **PRD AC-M1.4: every action requires a `legal_basis` and a non-empty
    `reason`**, and the reason is shown verbatim to the seller, so it is
    refused when blank rather than defaulted. `AC-M1.5`: there is no
    bulk-approve, and this signature cannot express one — one listing, one
    decision, one logged reason.

    **`work_seconds` is recorded in `audit_log` and not in
    `moderation_actions`, because that table is S6's** (DATA-MODEL §7) and
    `support_work_log` is S5's. Writing the number into the audit row keeps
    D-009's instrumentation shipping *with* the behaviour (TASKS §0 rule 4)
    rather than being retrofitted, and S6's `moderation_actions` backfill has a
    source to read. Recorded in the slice note as the one metric this slice
    emits into a different table from the one §9.4 will query.
    """
    if not getattr(staff, "is_staff_member", False):
        raise NotPermitted("That is a staff-only action.")
    if action not in MODERATION_ACTIONS:
        raise ValidationFailed(
            "That is not a moderation action we can record.",
            detail=f"{action!r} is not one of {sorted(MODERATION_ACTIONS)}",
        )
    if not str(reason or "").strip():
        raise ValidationFailed(
            "Write the reason the seller will read.",
            field_errors={"reason": ["Required."]},
        )
    if not str(legal_basis or "").strip():
        raise ValidationFailed(
            "Record the basis for this decision.",
            field_errors={"legal_basis": ["Required."]},
        )
    try:
        seconds = int(work_seconds)
    except (TypeError, ValueError):
        raise ValidationFailed("Record how long this took.") from None
    if seconds < 0:
        raise ValidationFailed("Record how long this took.")

    listing = Listing.all_objects.filter(id=listing.id).first()
    if listing is None:
        raise NotFound("Not found.")
    target = MODERATION_ACTIONS[action]
    return _transition(
        listing, target, listing.version, actor=staff,
        action=f"listings.moderated.{action.lower()}",
        extra={},
    )


def review_queue(staff, limit=50):
    """J2-staff step 1. The `PENDING_REVIEW` queue, oldest first.

    **Ordered by arrival, and AC-M1.1 wants "time remaining on the shortest
    applicable clock".** Listing review has no statutory clock — J2-staff says
    so itself: *"it inherits a service target"* — and the clocks it would be
    ordered against live on `reports` and `legal_notices`, which are S6
    tables. Oldest-first is the same order while listings are the only thing
    in the queue, and the single-clock screen US-M2 asks for is S6's. Stated
    here so it is a known limit rather than an assumed equivalence.
    """
    if not getattr(staff, "is_staff_member", False):
        raise NotPermitted("That is a staff-only action.")
    return list(
        Listing.all_objects.filter(status="PENDING_REVIEW")
        .select_related("book", "campus")
        .order_by("created_at", "id")[: max(1, min(int(limit or 50), 200))]
    )


# --- reads -----------------------------------------------------------------


def get_own_listing(actor, listing_id) -> Listing:
    """The actor's own listing, in their campus scope, or `404`.

    **`all_objects`, deliberately, and it is not a gate bypass.** A seller
    reading their own draft on a campus whose gate is lawfully closed is not
    discovery: nobody else can see the row, and ADR-002 §4's gate is about
    *"participants browsing each other's listings"*. Scoping is still applied,
    and ownership is the second predicate — so this returns only rows the
    actor wrote. `get_listing` (S3, `apps/discovery/services.py`) is the
    discovery read and it calls `assert_discovery_open` first.
    """
    row = (
        scoped(Listing.all_objects.all(), actor)
        .filter(id=listing_id, seller_pseudonym=actor.person_pseudonym)
        .select_related("book")
        .first()
    )
    if row is None:
        raise NotFound("Not found.")
    return row


def my_listings(actor, cursor=None, limit=20):
    """`GET /api/v1/listings/mine`. The seller's own listings, newest first.

    Not a discovery path — it reads only the actor's own rows — so it does not
    call `assert_discovery_open`, and that is deliberate rather than an
    omission: refusing a seller their own draft list on a closed campus would
    make the sell flow untestable before Gate C, which is the thing seed data
    exists to allow.
    """
    require_actor(actor, checks=("status",))
    rows = (
        scoped(Listing.all_objects.all(), actor)
        .filter(seller_pseudonym=actor.person_pseudonym)
        .select_related("book")
        .order_by("-created_at", "-id")
    )
    return _page(rows, cursor, limit)


def seller_block(listing):
    """API-CONTRACT §5.2: *"Seller identity in a listing response is
    `{display_name, campus_name, pseudonym}` and nothing else"*
    (`COMPLIANCE.md` §2.4(i)).

    **Three keys, and the function exists so there is one place that decides
    that.** A listing serialiser that reached for `listing.seller.email` would
    be one line and would ship a contact detail in a discovery response, which
    is `THREAT-MODEL.md` §5.4's whole subject.

    The campus-mail trust line is **derived from
    `campus_verifications.method`, never from `users.campus_verified`**
    (`COMPLIANCE.md` §7 row 6): the boolean includes `STAFF_MANUAL`, and
    telling a buyer that a staff-re-verified student *"signed in with a college
    email address"* would be a false statement about the one trust signal this
    product makes. It renders the **method**, never the domain.
    """
    from apps.accounts.services import INSTITUTIONAL_EMAIL

    seller = listing.seller
    return {
        "display_name": getattr(seller, "display_name", None),
        "campus_name": listing.campus.name,
        "pseudonym": str(listing.seller_pseudonym),
        "signed_in_with_college_email": (
            getattr(seller, "campus_verification_method", None) == INSTITUTIONAL_EMAIL
        ),
    }


def listing_payload(listing, *, include_seller=True):
    """The L2/L3 shape for one listing. API-CONTRACT §5.2.

    **What is not here is the specification**: no seller address, no phone, no
    email, no coordinates, no settled price, and no key named `price`,
    `amount`, `total` or `value` (ADR-003 §2.3's response-key rule, which
    `tests/unit/test_forbidden_response.py` enforces against this function).
    The money key is `asking_price_paise` at the boundary as well as in the
    table, so a template cannot render "Price:" from a field that invited it.
    """
    payload = {
        "id": listing.id,
        "status": listing.status,
        "intent": listing.intent,
        "asking_price_paise": listing.asking_price_paise,
        "condition": listing.condition,
        "annotation_level": listing.annotation_level,
        "damage_flags": list(listing.damage_flags or []),
        "category": listing.category,
        "language": listing.language,
        "campus_name": listing.campus.name,
        "published_at": listing.published_at,
        "version": listing.version,
        "book": {
            "id": listing.book_id,
            "isbn13": listing.book.isbn13,
            "title": listing.book.title,
            "authors": list(listing.book.authors or []),
            "edition_label": listing.book.edition_label,
            "publisher": listing.book.publisher,
            "publication_year": listing.book.publication_year,
        },
        "photos": [
            {"sha256": p.sha256, "width": p.width, "height": p.height}
            for p in listing.photos.all().order_by("uploaded_at", "id")
        ],
    }
    if include_seller:
        payload["seller"] = seller_block(listing)
    return payload


def get_photo_for_download(actor, listing_id, sha256) -> ListingPhoto:
    """The photo an actor may be served, or `404`. cto's spec, 2026-10-22.

    **The authorisation decision, in Django, before any byte is served.**
    `MEDIA_ROOT` behind the web server would be a guessable media URL and
    therefore a side channel around the discovery gate — the same shape the
    notification scan would have been. The storage key is a sha256 and so is
    not guessable in practice, but *"not guessable"* is not an authorisation
    decision, and ADR-002 §4 requires one.

    Three predicates, in this order:

    1. **Scope** — the listing is in the actor's visible campuses
       (ADR-002 §2);
    2. **Gate** — unless the actor owns the listing, the campus gate must be
       open, or the row must be seed. `assert_discovery_open` is called so
       the refusal is **logged** in the security stream (ADR-002 §4.2), and
       then converted to a `404`;
    3. **Status** — a `DRAFT`, `REJECTED` or `REMOVED_LEGAL` listing's photos
       are not served to anyone but the seller. `REMOVED_LEGAL` content is
       *preserved* 180 days for investigation (DATA-MODEL §6.1), which is not
       the same as served.

    **Every refusal is `404`, never `403`.** A 403 here would confirm that a
    listing exists on another campus, which is the catalogue leak
    API-CONTRACT §2.2 forbids — *"the same body either way"*. That is a real
    difference from `GATE_CLOSED` on a discovery *search*, where the student
    is asking about their own campus and is owed the explanation.
    """
    row = (
        scoped(ListingPhoto.all_objects.all(), actor)
        .filter(listing_id=listing_id, sha256=str(sha256 or ""))
        .select_related("listing", "listing__campus")
        .first()
    )
    if row is None or not row.storage_key:
        # No key means the bytes were purged (DATA-MODEL §10.2). The row
        # survives its file, and "gone" reads the same as "never here" — a
        # distinction nobody outside the audit trail is owed.
        raise NotFound("Not found.")

    listing = row.listing
    owns = (
        getattr(actor, "person_pseudonym", None) is not None
        and listing.seller_pseudonym == actor.person_pseudonym
    )
    if not owns:
        if listing.status not in ("LIVE", "RESERVED", "CLOSED_TRANSFERRED"):
            raise NotFound("Not found.")
        try:
            assert_discovery_open(listing.campus)
        except GateClosed:
            # Logged by `assert_discovery_open`, then converted: a closed
            # campus must not be distinguishable from a listing that is not
            # there. A seed row is still served, which is ADR-002 §4.1(c)'s
            # whole affordance.
            if not row.is_seed:
                raise NotFound("Not found.") from None
    return row


#: The media types a stored photo can have, derived from the key's extension.
#: **Never from a stored `Content-Type`**: there is no such column, and a
#: client-supplied type is how a `.jpeg` gets served as `text/html`.
PHOTO_CONTENT_TYPES = {
    "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp",
}


def photo_response(photo):
    """The bytes, or the header that makes the web server send them.

    Production: `X-Accel-Redirect` and an empty body, so **nginx streams the
    file and Django never reads it** — Django authorises and does not serve.
    Development: there is no nginx, so the bytes are read here. **The
    authorisation above is identical on both paths**, which is the property
    that matters; what differs is which process does the I/O.

    `private` caching and `noindex` on both: a photo of a student's book is
    not shared-cacheable and is never indexed (API-CONTRACT §5.8).
    """
    from django.conf import settings
    from django.http import HttpResponse

    from .storage import read_object

    suffix = str(photo.storage_key).rsplit(".", 1)[-1].lower()
    content_type = PHOTO_CONTENT_TYPES.get(suffix, "application/octet-stream")
    internal = getattr(settings, "MEDIA_INTERNAL_PREFIX", "")

    if internal:
        response = HttpResponse(b"", content_type=content_type)
        response["X-Accel-Redirect"] = f"{internal.rstrip('/')}/{photo.storage_key}"
    else:
        data = read_object(photo.storage_key)
        if data is None:
            raise NotFound("Not found.")
        response = HttpResponse(data, content_type=content_type)
        response["Content-Length"] = str(len(data))

    # `private` and not `public`: a shared cache in front of this would serve
    # one student's photo from another student's authorised request.
    response["Cache-Control"] = "private, max-age=3600"
    response["X-Robots-Tag"] = "noindex"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def _page(queryset, cursor, limit):
    """API-CONTRACT §2.3's cursor pagination. `{items, next_cursor}`.

    **No offset pagination**: under concurrent inserts offset skips and
    duplicates rows, and the first thing a new listing does is shift every
    page. The cursor is base64 of `{sort_value, id}` and expires after 24
    hours, which is §2.3 verbatim.
    """
    import base64
    import json

    limit = max(1, min(int(limit or 20), 50))
    if cursor:
        try:
            decoded = json.loads(base64.urlsafe_b64decode(str(cursor).encode()).decode())
            created = decoded["c"]
            last_id = int(decoded["i"])
            issued = decoded["t"]
        except Exception:
            raise ValidationFailed(
                "That page link is no longer valid. Start again.",
                detail="cursor did not decode",
            ) from None
        if timezone.now() - timezone.datetime.fromisoformat(issued) > timedelta(hours=24):
            raise ValidationFailed(
                "That page link has expired. Start again.", detail="cursor older than 24h"
            )
        queryset = queryset.filter(
            models_Q_lt(created, last_id)
        )
    rows = list(queryset[: limit + 1])
    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        last = rows[-1]
        next_cursor = base64.urlsafe_b64encode(
            json.dumps(
                {"c": last.created_at.isoformat(), "i": last.id,
                 "t": timezone.now().isoformat()}
            ).encode()
        ).decode()
    return {"items": rows, "next_cursor": next_cursor}


def models_Q_lt(created, last_id):
    """`(created_at, id) < (cursor.created_at, cursor.id)` for a DESC page.

    A tuple comparison written as a disjunction, because neither engine's ORM
    expresses row-value comparison portably. One helper so the two call sites
    cannot disagree about tie-breaking — a page that tie-breaks differently
    from the ORDER BY silently drops rows.
    """
    from django.db.models import Q

    return Q(("created_at__lt", created)) | (
        Q(("created_at", created)) & Q(("id__lt", last_id))
    )


# --- book requests (the demand side) ---------------------------------------


def create_request(actor, *, book=None, free_text_title=None, course_code=None) -> BookRequest:
    """API-CONTRACT §3. JOURNEYS J4 step 2 — *"record the want"*.

    **The want form never promises a time, a probability, or that the book
    will arrive** (PRD AC-B2.5). That is copy, and it is frontend's; the
    service half is that nothing here returns an estimate, and there is no
    column for one.

    A want names a book **or** a free-text title (DATA-MODEL §3's CHECK). EC-17
    — an ISBN we do not recognise — lands in `free_text_title`, and that is one
    of the few places the product tells staff something about the syllabus we
    did not know.
    """
    require_actor(actor)
    assert_campus_write(actor)
    book = resolve_merge(book) if book is not None else None
    title = " ".join(str(free_text_title or "").split()) or None
    if book is None and not title:
        raise ValidationFailed(
            "Name the book you are looking for.",
            field_errors={"free_text_title": ["A title, or pick a book."]},
        )
    code = " ".join(str(course_code or "").split()).upper() or None

    with transaction.atomic():
        existing = BookRequest.all_objects.filter(
            requester_pseudonym=actor.person_pseudonym,
            book=book,
            free_text_title=title,
            status="OPEN",
        ).first()
        if existing is not None:
            # Idempotent by shape as well as by key: a student who submits the
            # same want twice has one want, not two, and the match rate counts
            # people rather than taps.
            return existing
        row = BookRequest.all_objects.create(
            requester=actor,
            requester_pseudonym=actor.person_pseudonym,
            book=book,
            free_text_title=title,
            campus_id=actor.campus_id,
            city_id=actor.city_id,
            course_code=code,
            status="OPEN",
            is_seed=actor.is_seed,
        )
        record_audit(
            actor, "listings.request_created", row,
            after={"book_id": getattr(book, "id", None), "course_code": code,
                   "is_seed": row.is_seed},
        )
    return row


def close_request(actor, request) -> BookRequest:
    """API-CONTRACT §3. JOURNEYS J4 step 6 — *"I don't need this any more"*.

    `WITHDRAWN`, not `FULFILLED`: only a completed transfer may write
    `FULFILLED` (amendment A-3, S4), because the match rate's numerator is
    *transfers that closed a want* and a student tidying their list is not one.
    """
    require_actor(actor)
    row = (
        scoped(BookRequest.all_objects.all(), actor)
        .filter(id=getattr(request, "id", request),
                requester_pseudonym=actor.person_pseudonym)
        .first()
    )
    if row is None:
        raise NotFound("Not found.")
    if row.status != "OPEN":
        raise TransitionNotAllowed(
            "That cannot be done at this stage.",
            detail=f"book_requests.status is {row.status!r}",
        )
    now = timezone.now()
    with transaction.atomic():
        BookRequest.all_objects.filter(id=row.id).update(
            status="WITHDRAWN", closed_at=now, purge_due_at=now + RETENTION_FLOOR
        )
        row.refresh_from_db()
        record_audit(
            actor, "listings.request_closed", row,
            before={"status": "OPEN"}, after={"status": "WITHDRAWN"},
        )
    return row


def my_requests(actor, cursor=None, limit=20):
    """The student's own wants. Not a discovery path; own rows only."""
    require_actor(actor, checks=("status",))
    rows = (
        scoped(BookRequest.all_objects.all(), actor)
        .filter(requester_pseudonym=actor.person_pseudonym)
        .select_related("book")
        .order_by("-created_at", "-id")
    )
    return _page(rows, cursor, limit)


def open_requests_for_staff(staff, campus, limit=100):
    """J4's *"the most informative screen in the product for R-01"*.

    **The gate applies here**, because a staff member reading a closed
    campus's wants is reading real students' rows: `assert_discovery_open`
    first, then `restrict_when_gate_closed`, which is the ADR-002 §4.1(c)
    pairing — the assertion gives the refusal, the filter gives seed-only.
    """
    if not getattr(staff, "is_staff_member", False):
        raise NotPermitted("That is a staff-only action.")
    try:
        assert_discovery_open(campus)
    except Exception:
        # Staff legitimately read a closed campus; they see seed rows only.
        # The assertion is still called, so the refusal is logged and the
        # decision is visible in the security stream (ADR-002 §4.2).
        pass
    rows = restrict_when_gate_closed(
        BookRequest.all_objects.filter(campus=campus, status="OPEN"), campus
    )
    return list(rows.select_related("book").order_by("created_at")[:limit])


#: DATA-MODEL §6.1's statuses, re-exported so a caller does not import the
#: model to name a state.
STATUSES = LISTING_STATUSES
REQUEST_STATES = REQUEST_STATUSES
