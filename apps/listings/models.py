"""apps.listings models — DATA-MODEL.md §3 `listings`, `listing_photos`,
`swap_wants`, `book_requests`.

**This is the table the whole of P14 is about.** `listings.asking_price_paise`
is *"the only money column in the database"* (ADR-003 §2.1), it is an integer
number of paise, and it is **immutable by a database trigger** created in
migration `0002` — not by a service-layer rule, because ADR-003 §2.2's ladder
rung is explicit: a DB constraint beats app code, and the thing being guarded
is the difference between an asking price and a settled consideration.

Three columns that look like oversights and are decisions:

  * **No `title` and no `author`.** They live on `books`, which is what
    edition-locking means (DATA-MODEL §3).
  * **No price history, no previous price, no "was/now".** ADR-003 §2.2: a
    price history lets anyone reconstruct the price at the moment of handover,
    which is functionally a settled price. A seller who wants a different
    price withdraws and relists.
  * **No seller rating and no condition score.** `condition` is *seller-stated*
    and the copy may never say "BookHop verified" (`COMPLIANCE.md` §2.5).

Three additions to DATA-MODEL §3's column lists, all additive, all made
because another frozen contract requires them, and all raised to cto in the
slice note rather than taken silently:

  * **`listing_photos.campus_id` / `city_id`** — ADR-002 §2 names
    `listing_photos` in its list of *"tenant-scoped tables (all carry both
    keys)"*, and `apps/core/scoping.py`'s registry (S0) lists it, so
    `tests/unit/test_scoping.py` requires them. DATA-MODEL §3's one-line
    column list simply omits them. ADR-002 wins because it names the table
    explicitly **and** because retrofitting a tenant key later is *"a migration
    across the whole database plus a rewrite of every metric"*.
  * **`listing_photos.is_seed` / `book_requests.is_seed`** — ADR-002 §2.3 puts
    `GatedManager` on both models and TASKS §2 S2 carries it as a checkable
    line item. A gated manager needs the column it gates on;
    `restrict_when_gate_closed` raises `FieldError` on a model without one,
    which is the behaviour S0 chose deliberately *(a gate filter that silently
    no-ops is worse than one that is absent)*. `book_requests.is_seed` is also
    what keeps seed wants out of the §9.3 match rate.
  * **`book_requests.course_code`** is already in DATA-MODEL; nothing added.
"""

from django.db import models
from django.utils import timezone

from apps.catalog.models import LANGUAGES
from apps.core.scoping import GatedManager

#: DATA-MODEL §3 `listings.intent`. **SWAP is representable and UI-hidden**
#: (D-007: *"deferred, not deleted"*), which is a data fact here and a
#: `feature_flags['listings.swap_ui']` fact in the UI.
INTENTS = ("SELL", "SWAP", "GIVE")

#: Seller-stated, never a grade and never a score (PRD AC-S3.1).
CONDITIONS = ("AS_NEW", "GOOD", "FAIR", "HEAVILY_USED")

#: Neutral fact, not a judgement (PRD AC-S3.3).
ANNOTATION_LEVELS = ("NONE", "LIGHT_PENCIL", "HIGHLIGHTED", "HEAVY_NOTES")

#: DATA-MODEL §3: `damage_flags` is a subset of these six. **PRD AC-S3.2
#: requires affirmative confirmation** — *"an empty damage list that submits
#: is an implied no-damage claim the seller never made"* — and that is
#: enforced in `services.create_listing`, which refuses an empty list unless
#: the caller also passes `no_damage=True`. **No column**: the claim the
#: seller made is `damage_flags`, and the fact that they were asked is the
#: `audit_log` row the creation writes. A fourth divergence from DATA-MODEL §3
#: for a fact already recorded elsewhere would be a column that can disagree.
DAMAGE_FLAGS = (
    "WATER", "TORN_PAGES", "MISSING_PAGES", "BROKEN_SPINE", "LOOSE_PAGES", "COVER_DAMAGE",
)

#: **GENERAL_READING is representable and UI-hidden** (D-007), pending R-26's
#: copyright reassessment.
CATEGORIES = ("PRESCRIBED_TEXTBOOK", "REFERENCE", "GENERAL_READING")

#: ADR-002 §5. Widening discovery to a city is a data change, never a
#: migration — which is the property this column exists to buy.
VISIBILITY_SCOPES = ("CAMPUS", "CITY", "NATIONAL")

#: DATA-MODEL §6.1. Eight states; four of them terminal.
LISTING_STATUSES = (
    "DRAFT", "PENDING_REVIEW", "LIVE", "RESERVED",
    "CLOSED_TRANSFERRED", "WITHDRAWN", "REJECTED", "REMOVED_LEGAL",
)

#: DATA-MODEL §3 `book_requests.status`.
REQUEST_STATUSES = ("OPEN", "FULFILLED", "WITHDRAWN", "EXPIRED")

#: ADR-003 §2.1 / DATA-MODEL §3: `CHECK (>=0 AND <=10000000)`. Rs 1,00,000 in
#: the Indian minor unit, which is JOURNEYS J2 step 5's stated ceiling. One
#: definition, read by the CHECK, by the service-layer refusal and by the tests.
#:
#: **This name keeps both money tokens on purpose, and that is a ruling rather
#: than an oversight** — ADR-003 §2.3's `SOURCE_GUARD_SHAPE_EXEMPTIONS`, cto
#: 2026-10-22, rule 13 rung 2.
#:
#: W1c's AST walk sees module constants by design (QA-S0 F13 added that shape
#: because `SETTLED_PRICE_PAISE = 30000` used to be invisible), so this went
#: red. Rung 1 — rename ours — **was available and was judged harmful**: every
#: honest name for a bound on paise contains `paise` or `price`, and renaming
#: it to something unit-free to dodge a grep removes the unit from the name of
#: a money bound, which is the exact discipline that keeps integer-paise safe.
#: *Preferred was never mandatory.*
#:
#: It is exempt as **shape B** — an UPPER_SNAKE literal-int bound — and the
#: exemption is **conditional**: `tests/unit/test_exempted_bound_is_pinned.py`
#: asserts this equals the bound in the CHECK below, which is the second layer
#: rule 12 requires, because a constant is not a column and W1's whitelist
#: cannot reach it. A bound with no CHECK behind it fails there.
MAX_ASKING_PRICE_PAISE = 10_000_000

#: Photo limits — DATA-MODEL §3 and API-CONTRACT §5.2.
MAX_PHOTOS_PER_LISTING = 4
MAX_PHOTO_BYTES = 8 * 1024 * 1024


def _check_in(column, values):
    return models.Q(**{f"{column}__in": list(values)})


class Listing(models.Model):
    """DATA-MODEL §3 `listings`. `COMPLIANCE.md` §7 row 10.

    **`objects` is gated and `all_objects` is not** (ADR-002 §2.3). The gated
    manager is defence in depth *underneath* `assert_discovery_open`, never
    instead of it: a closed campus must produce `403 GATE_CLOSED`, not an empty
    page. `Meta.base_manager_name` points at the unfiltered manager so cascade
    deletes, `refresh_from_db` and related descriptors keep seeing every row.
    """

    objects = GatedManager()
    all_objects = models.Manager()

    #: NULL after erasure (DATA-MODEL §10.1 step 6); the pseudonym survives.
    seller = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL,
        db_column="seller_id", related_name="listings",
    )
    seller_pseudonym = models.UUIDField()
    book = models.ForeignKey(
        "catalog.Book", on_delete=models.PROTECT, db_column="book_id", related_name="listings"
    )
    campus = models.ForeignKey(
        "core.Campus", on_delete=models.PROTECT, db_column="campus_id", related_name="listings"
    )
    city = models.ForeignKey(
        "core.City", on_delete=models.PROTECT, db_column="city_id", related_name="listings"
    )

    intent = models.TextField(default="SELL")

    #: **The only money column in the database** (ADR-003 §2.1), integer paise,
    #: and immutable by the `listings_price_immutable` trigger in migration
    #: 0002. Never a float: `300.75` rounded to `301` is a wrong value that
    #: looks right (`CLAUDE.md` rule 18), which is why
    #: `services.create_listing` refuses a non-integer **before** the column
    #: can round it, and why the test that matters passes a float rather than
    #: inspecting the column's type.
    asking_price_paise = models.IntegerField()
    price_fixed_at = models.DateTimeField(default=timezone.now)

    condition = models.TextField()
    annotation_level = models.TextField()
    #: `text[]` in DATA-MODEL; a JSON list here for the reason
    #: `campuses.email_domains` is one (A-16) — SQLite has no array type and
    #: the only operations are display and membership. The subset rule is
    #: enforced in `services.create_listing`, because neither engine can
    #: express "every element of this array is in that set" portably: PG could
    #: with an array CHECK, SQLite cannot at all, and a constraint that exists
    #: on one engine is a constraint the tests do not cover (rule 17).
    damage_flags = models.JSONField(default=list)

    category = models.TextField(default="PRESCRIBED_TEXTBOOK")
    #: *"a copy of the physical copy's language, may differ from
    #: `books.language`"* — DATA-MODEL §3. An international student edition in
    #: English of a Tamil-language title is the case this exists for.
    language = models.TextField(default="en")
    visibility_scope = models.TextField(default="CAMPUS")
    status = models.TextField(default="DRAFT")

    #: R-26, P9: *prevention is cheaper than 36-hour takedowns.* Photocopy,
    #: spiral binding or scan — set by the seller's own answer at intake and by
    #: staff at review, never inferred from an image.
    suspect_reproduction_flag = models.BooleanField(default=False)

    is_seed = models.BooleanField(default=False)
    #: **The start of time-to-match** (DATA-MODEL §9.3). Set once, when the
    #: listing first reaches LIVE, and never rewritten — a relisted listing is
    #: a new row.
    published_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    #: `closed_at + 1 year` (r.8(3)). Set by whatever closes the listing, so
    #: the retention clock starts with the event rather than with a later job.
    purge_due_at = models.DateTimeField(null=True, blank=True)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "listings"
        base_manager_name = "all_objects"
        indexes = [
            models.Index(
                fields=["campus", "status", "-published_at"], name="listings_browse_idx"
            ),
            models.Index(fields=["book", "campus", "status"], name="listings_book_campus_idx"),
            models.Index(fields=["seller_pseudonym"], name="listings_seller_idx"),
            models.Index(
                fields=["status"],
                name="listings_review_queue_idx",
                condition=models.Q(status="PENDING_REVIEW"),
            ),
        ]
        constraints = [
            models.CheckConstraint(condition=_check_in("intent", INTENTS), name="listings_intent_chk"),
            models.CheckConstraint(
                condition=_check_in("condition", CONDITIONS), name="listings_condition_chk"
            ),
            models.CheckConstraint(
                condition=_check_in("annotation_level", ANNOTATION_LEVELS),
                name="listings_annotation_chk",
            ),
            models.CheckConstraint(
                condition=_check_in("category", CATEGORIES), name="listings_category_chk"
            ),
            models.CheckConstraint(
                condition=_check_in("language", LANGUAGES), name="listings_language_chk"
            ),
            models.CheckConstraint(
                condition=_check_in("visibility_scope", VISIBILITY_SCOPES),
                name="listings_visibility_chk",
            ),
            models.CheckConstraint(
                condition=_check_in("status", LISTING_STATUSES), name="listings_status_chk"
            ),
            #: ADR-003 §2.1 / DATA-MODEL §3, verbatim. The floor; the detection
            #: layer above it is `create_listing`, which refuses a non-integer
            #: before PostgreSQL can round it into range (`CLAUDE.md` rule 12:
            #: a database proving no float is *stored* does not prove none was
            #: *passed*).
            #:
            #: **The two lookups are ratified shape A** (ADR-003 §2.3, cto
            #: 2026-10-22): an ORM lookup that must *end* at the permitted
            #: column is a query key, not storage, so it cannot carry a
            #: per-transaction value. Rung 1 is genuinely unavailable here —
            #: the colliding name is derived from the one column P14 permits,
            #: so renaming it means renaming that column.
            #:
            #: Shape A's second layer is W1's whitelist itself: to write
            #: `settled_price__gte` you first need a `settled_price` column,
            #: and the whitelist refuses the column. `asking_price_paise__total`
            #: is **not** exempt, because `total` is not a lookup — asserted in
            #: `test_forbidden_source.py` rather than claimed here.
            models.CheckConstraint(
                condition=models.Q(
                    asking_price_paise__gte=0,
                    asking_price_paise__lte=MAX_ASKING_PRICE_PAISE,
                ),
                name="listings_asking_price_range_chk",
            ),
        ]

    def __str__(self):
        return f"listing {self.pk} ({self.status})"

    @property
    def is_live(self):
        return self.status == "LIVE"


class ListingPhoto(models.Model):
    """DATA-MODEL §3 `listing_photos`. `COMPLIANCE.md` §7 row 9.

    **`exif_stripped_at` is NOT NULL, and that is the whole control**: the row
    cannot exist unless EXIF was stripped, which makes *"purge EXIF at upload"*
    a structural guarantee rather than a code path somebody has to remember.
    `services.add_photo` writes the stripped bytes and the row in one
    transaction, so a row with no stripped file is not reachable.

    Max four per listing. DATA-MODEL says *"CHECK via a trigger count"*; it is
    a conditional insert inside the service's transaction instead, and the
    reason is `CLAUDE.md` rule 17 rather than convenience: a counting trigger
    is two different bodies on two engines for a limit that has no legal
    consequence, where the append path is already single-writer per listing.
    The ceiling is declared on `add_photo`.
    """

    objects = GatedManager()
    all_objects = models.Manager()

    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, db_column="listing_id", related_name="photos"
    )
    #: ADR-002 §2 names `listing_photos` as tenant-scoped. Denormalised from
    #: the listing at insert, like every other scoped row.
    campus = models.ForeignKey(
        "core.Campus", on_delete=models.PROTECT, db_column="campus_id",
        related_name="listing_photos",
    )
    city = models.ForeignKey(
        "core.City", on_delete=models.PROTECT, db_column="city_id",
        related_name="listing_photos",
    )
    is_seed = models.BooleanField(default=False)

    #: NULL once the object has been purged (`jobs.purge_media`). The **row**
    #: survives its bytes: it is what proves a listing had four photos when a
    #: dispute is read a year later, and the bytes are the personal data.
    #: NULL rather than `""` because the column is UNIQUE and two purged rows
    #: would collide on the empty string; NULLs are distinct on both engines.
    storage_key = models.TextField(null=True, blank=True, unique=True)
    #: API-CONTRACT A-25, from Red Team F51: *"The stored filename gains a
    #: component that appears in **no** response — a per-photo random token,
    #: stored on the row. The URL keeps the `sha256`; the disk does not."*
    #:
    #: The key used to be `listings/{id}/{sha256[:32]}.{fmt}` while
    #: `listing_payload` published both the id and the full `sha256`, so any
    #: authorised reader could write down the exact path on disk and hand it
    #: to anyone — the authorisation decision standing in front of a door
    #: whose key is printed on the door. The Django decision is still the
    #: layer that matters; this is the layer that survives `INFRA.md` §1
    #: routing `/media/` publicly, which it currently does.
    #:
    #: NULL on a purged row, like `storage_key`, and NULL on any row written
    #: before migration 0004's backfill reached it.
    storage_token = models.TextField(null=True, blank=True)
    sha256 = models.TextField()
    width = models.IntegerField()
    height = models.IntegerField()
    bytes = models.IntegerField()
    exif_stripped_at = models.DateTimeField()
    uploaded_at = models.DateTimeField(default=timezone.now)
    purge_due_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "listing_photos"
        base_manager_name = "all_objects"
        indexes = [
            models.Index(fields=["campus", "uploaded_at"], name="photos_campus_uploaded_idx"),
            models.Index(fields=["listing"], name="photos_listing_idx"),
        ]
        constraints = [
            # **The same photo twice on one listing, as the database says
            # it.** This was previously enforced as a side effect of
            # `storage_key` being UNIQUE and content-addressed; A-25 makes
            # the key random, so that side effect is gone and the guarantee
            # had to move before it did (`CLAUDE.md` rule 12: the new remedy
            # goes in beside the old, and the old comes out in the commit
            # that turns the new one green). It is also the *property* —
            # "one copy of these bytes per listing" — rather than a
            # consequence of how a filename happened to be spelled.
            models.UniqueConstraint(
                fields=["listing", "sha256"], name="listing_photos_one_copy_per_listing"
            ),
        ]

    def __str__(self):
        return self.storage_key


class SwapWant(models.Model):
    """DATA-MODEL §3 `swap_wants` — representable, UI-hidden (D-007).

    *"Writable only by staff/fixtures in v1; the UI never exposes it while
    `feature_flags['listings.swap_ui']` is false. Tested with seed data so it
    is known to work when swap returns."*

    Not tenant-scoped: both ends are already scoped (the listing carries the
    campus, the book is global), so a third copy of the campus key would be a
    third thing that can disagree.
    """

    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, db_column="listing_id", related_name="swap_wants"
    )
    book = models.ForeignKey(
        "catalog.Book", on_delete=models.PROTECT, db_column="book_id", related_name="wanted_in_swaps"
    )

    class Meta:
        db_table = "swap_wants"
        constraints = [
            models.UniqueConstraint(fields=["listing", "book"], name="swap_want_listing_book_uniq"),
        ]


class BookRequest(models.Model):
    """DATA-MODEL §3 `book_requests` — the demand side.

    **A want with no supply is the measurement that tells us the campus is
    illiquid** (R-01), and it is one limb of `METRICS.md`'s match rate (§9.3).
    JOURNEYS J4 is the journey: on a cold campus the honest answer to most
    searches is "not yet", and this row is how that answer becomes a number.

    `fulfilled_by_transfer_id` is **not** a column here yet: `transfers` is an
    S4 table and a FK to a table that does not exist cannot be created. The
    column lands with S4's `confirm_handover` (amendment A-3), which is the
    only thing that writes it — recorded here rather than left to be
    rediscovered, and asserted by
    `tests/unit/test_listings.py::test_the_fulfilment_column_is_recorded_as_pending`.
    """

    objects = GatedManager()
    all_objects = models.Manager()

    requester = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL,
        db_column="requester_id", related_name="book_requests",
    )
    requester_pseudonym = models.UUIDField()
    book = models.ForeignKey(
        "catalog.Book", null=True, blank=True, on_delete=models.PROTECT,
        db_column="book_id", related_name="requests",
    )
    #: EC-17: an ISBN we do not recognise is carried here, and it is one of the
    #: few places the product tells staff something about the syllabus we did
    #: not know.
    free_text_title = models.TextField(null=True, blank=True)
    campus = models.ForeignKey(
        "core.Campus", on_delete=models.PROTECT, db_column="campus_id", related_name="book_requests"
    )
    city = models.ForeignKey(
        "core.City", on_delete=models.PROTECT, db_column="city_id", related_name="book_requests"
    )
    course_code = models.TextField(null=True, blank=True)
    status = models.TextField(default="OPEN")
    is_seed = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    closed_at = models.DateTimeField(null=True, blank=True)
    purge_due_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "book_requests"
        base_manager_name = "all_objects"
        indexes = [
            models.Index(fields=["campus", "status", "created_at"], name="requests_campus_idx"),
            models.Index(fields=["book", "campus", "status"], name="requests_book_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=_check_in("status", REQUEST_STATUSES), name="requests_status_chk"
            ),
            #: DATA-MODEL §3, verbatim. A want that names neither a book nor a
            #: title is a row that cannot be matched and cannot be read.
            models.CheckConstraint(
                condition=models.Q(book__isnull=False) | models.Q(free_text_title__isnull=False),
                name="requests_book_or_title_chk",
            ),
        ]

    def __str__(self):
        return f"request {self.pk} ({self.status})"
