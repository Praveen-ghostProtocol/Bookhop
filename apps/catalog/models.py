"""apps.catalog models — DATA-MODEL.md §3 `books` and `prescribed_texts`.

**`books` is global, not tenant-scoped** (ADR-002 §2): *"A book edition is a
global fact. ISBN 978-… is the same edition in Chennai and Coimbatore. Scoping
it would duplicate the catalogue per campus and break edition-locking, which is
the entire wedge."* So it carries no `campus_id`, carries no `is_seed`, and
takes no `GatedManager` — a seed listing and a real listing point at the same
edition row and that is correct.

`prescribed_texts` **is** tenant-scoped: a reading list belongs to a campus and
a term. It is the product thesis in one table (`README.md` §1).

Conventions are DATA-MODEL §0's, identical to the other two apps: enums are
text + CHECK, never a native type; every timestamp is aware; `db_table` is set
explicitly so the P14 guard reads the same names the contract does.

Two engine divergences, both recorded for `ENGINE-DIVERGENCE.md` in the slice
note rather than taken silently:

  * `books.authors` is `text[]` in DATA-MODEL and a `JSONField` list here, for
    the reason `campuses.email_domains` is one (A-16): SQLite has no array type
    and the only operations are display and membership.
  * `books.title_norm`'s index is `GIN (title_norm gin_trgm_ops)` on
    PostgreSQL and a plain B-tree on SQLite, which supports the `startswith`
    prefix path and **not** the trigram path. Migration `0002` carries both
    halves and the difference is asserted, not assumed.
"""

from django.db import models
from django.utils import timezone

#: DATA-MODEL §3 `books.language` and `listings.language`. One definition,
#: imported by `apps.listings` rather than retyped (`CLAUDE.md` rule 10): the
#: listing's language is *"a copy of the physical copy's language, may differ
#: from `books.language`"*, which is the same value set asked twice.
LANGUAGES = ("en", "ta", "hi", "other")

#: DATA-MODEL §3 `prescribed_texts.source`.
PRESCRIBED_SOURCES = ("SYLLABUS_PDF", "DEPT_CONFIRMED", "STUDENT_REPORTED")


def _check_in(column, values):
    return models.Q(**{f"{column}__in": list(values)})


class Book(models.Model):
    """DATA-MODEL §3 `books` — global, the edition lock.

    `isbn13` is `NULL UNIQUE` because a pre-ISBN book has no ISBN and the
    product still has to represent it. **A listing on a NULL-ISBN book cannot
    be self-published** (PRD AC-S4.4): `publish_listing` routes it to staff,
    which is the rule enforced in the service layer because it is about the
    *listing*, not about the book row.

    `merged_into_id` is duplicate resolution **without deleting a row that
    listings point at** (J2-staff step 6, EC-7): a listing on a merged book
    still loads.

    **No price anywhere on this table.** A catalogue price would be a price
    history by another name (ADR-003 §2.2's reasoning for immutability).
    """

    #: `char(13)` in DATA-MODEL; `TextField` + UNIQUE here, because SQLite
    #: ignores `varchar(n)` lengths entirely and a declared width that one
    #: engine enforces and the other does not is a constraint that exists in
    #: production and not in the tests (`CLAUDE.md` rule 17).
    #:
    #: **The shape is checked above the schema, not in it** (`CLAUDE.md`
    #: rule 18). A CHECK can prove a stored *state* — thirteen characters — and
    #: cannot prove the input was a valid ISBN, because the mod-10 checksum has
    #: no portable SQL expression. `services.validate_isbn13` is the detection
    #: layer and it refuses before the row exists; UNIQUE is the floor.
    #: `test_catalog.py::test_a_bad_checksum_is_refused_rather_than_stored` is
    #: the test that matters, and it passes a bad input rather than inspecting
    #: a column type.
    isbn13 = models.TextField(null=True, blank=True, unique=True)
    title = models.TextField()
    #: Lowercased, punctuation-stripped. `services.normalise_title` is the one
    #: definition; nothing writes this column any other way.
    title_norm = models.TextField()
    authors = models.JSONField(default=list)
    edition_label = models.TextField(null=True, blank=True)
    publisher = models.TextField(null=True, blank=True)
    publication_year = models.SmallIntegerField(null=True, blank=True)
    language = models.TextField(default="en")
    #: `COMPLIANCE.md` §2.5. Optional, and *"not stated" is acceptable for a
    #: second-hand private sale* — so there is no CHECK and no default beyond
    #: NULL, and nothing in the product asserts it.
    origin_country = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL,
        db_column="created_by_id", related_name="books_created",
    )
    staff_verified_at = models.DateTimeField(null=True, blank=True)
    merged_into = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT,
        db_column="merged_into_id", related_name="merged_from",
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "books"
        indexes = [
            models.Index(fields=["title_norm"], name="books_title_norm_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=_check_in("language", LANGUAGES), name="books_language_chk"),
        ]

    def __str__(self):
        return f"{self.title} ({self.isbn13 or 'no ISBN'})"

    @property
    def is_staff_verified(self):
        return self.staff_verified_at is not None


class PrescribedText(models.Model):
    """DATA-MODEL §3 `prescribed_texts` — the syllabus-to-shelf layer.

    Tenant-scoped (ADR-002 §2 names it), so both keys are NOT NULL from day
    one. Seeding one department's reading list by hand is **R-01's test** and
    is the first thing in this slice's fixtures.
    """

    campus = models.ForeignKey(
        "core.Campus", on_delete=models.PROTECT, db_column="campus_id",
        related_name="prescribed_texts",
    )
    city = models.ForeignKey(
        "core.City", on_delete=models.PROTECT, db_column="city_id",
        related_name="prescribed_texts",
    )
    course_code = models.TextField()
    course_title = models.TextField()
    term_label = models.TextField()
    book = models.ForeignKey(
        Book, on_delete=models.PROTECT, db_column="book_id", related_name="prescribed_in"
    )
    source = models.TextField()
    source_ref = models.TextField(null=True, blank=True)
    added_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL,
        db_column="added_by_id", related_name="prescribed_texts_added",
    )
    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "prescribed_texts"
        constraints = [
            models.UniqueConstraint(
                fields=["campus", "course_code", "term_label", "book"],
                name="prescribed_campus_course_term_book_uniq",
            ),
            models.CheckConstraint(
                condition=_check_in("source", PRESCRIBED_SOURCES), name="prescribed_source_chk"
            ),
        ]
        indexes = [
            models.Index(fields=["campus", "course_code"], name="prescribed_campus_course_idx"),
        ]

    def __str__(self):
        return f"{self.course_code} → {self.book_id}"
