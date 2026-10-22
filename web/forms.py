"""L3 forms — real HTML form controls, native types, cheap-keyboard attributes.

Every widget attribute here is from `SYSTEM.md` §4.4's field table or §5.2, and
each one is there for a measured reason on a mid-range Android, not for
tidiness. The three that cause real support load if dropped are called out
inline.

Labels go through `pgettext_lazy` with their `COPY-DECK.md` key as the gettext
context, and **every one of them has an entry in
`locale/en/LC_MESSAGES/django.po`**. That is not decoration:
`tests/unit/test_forbidden_copy.py` greps templates and `.po` files only, so a
label that lived here and nowhere else would be outside the deny-list
entirely. The catalogue is what puts it back in scope.

**The consent purposes are imported, not listed here.** An earlier draft of
this file carried its own tuple and had already diverged from
`REQUIRED_CONSENT_PURPOSES` — `CLAUDE.md` rule 10.
"""

from django import forms
from django.utils.translation import pgettext_lazy as _p

from apps.accounts.services import CONSENT_PURPOSES, REQUIRED_CONSENT_PURPOSES

__all__ = [
    "AgeDeclarationForm",
    "BookDetailsForm",
    "ConsentForm",
    "IsbnForm",
    "ListingForm",
    "NomineeForm",
    "PhotoForm",
    "ProfileForm",
    "SignInForm",
    "WantedForm",
    "CONSENT_PURPOSES",
    "REQUIRED_CONSENT_PURPOSES",
    "ANNOTATION_CHOICES",
    "CONDITION_CHOICES",
    "DAMAGE_CHOICES",
    "MAX_PHOTO_BYTES",
    "MAX_PHOTOS",
    "NO_DAMAGE",
    "seller_words",
]


class _Form(forms.Form):
    """Base form that wires the ARIA a field needs, once, for every form.

    `SYSTEM.md` §4.4 `error` requires `aria-invalid="true"` and the message
    wired to the input via `aria-describedby`. Doing that in the template means
    re-implementing Django's widget rendering by hand for every input type;
    doing it at each call site means five places to forget it. So it happens
    here, on validation, and no view has to remember.

    `aria-describedby` always names both the hint and the error element, and
    `_field.html` always emits both (the error one empty when there is no
    error) — an `aria-describedby` pointing at an id that does not exist is
    invalid ARIA, and an empty described-by target contributes nothing, so the
    always-render version is the correct one.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._wire_aria()

    def _wire_aria(self):
        """Call again from any subclass that adds fields after `super().__init__`."""
        for name, field in self.fields.items():
            hid = f"id_{name}"
            field.widget.attrs["aria-describedby"] = f"{hid}-hint {hid}-error"

    def is_valid(self):
        valid = super().is_valid()
        if not valid:
            for name in self.errors:
                if name in self.fields:
                    self.fields[name].widget.attrs["aria-invalid"] = "true"
        return valid


class SignInForm(_Form):
    """`POST /auth/start`. One field, and `autofocus` is used here and nowhere
    else in the product (`SYSTEM.md` §4.4)."""

    email = forms.EmailField(
        label=_p("auth.email.label", "Your college email address"),
        max_length=254,
        widget=forms.EmailInput(
            attrs={
                "inputmode": "email",
                "autocomplete": "email",
                # All four are required together. Several Android keyboards
                # capitalise and autocorrect the first word of an email field,
                # after which the student cannot sign in and blames us
                # (SYSTEM.md §5.2 item 1).
                "autocapitalize": "off",
                "autocorrect": "off",
                "spellcheck": "false",
                "autofocus": "autofocus",
                "enterkeyhint": "send",
            }
        ),
    )


class AgeDeclarationForm(_Form):
    """`POST /account/age`. Native date input — no library, no custom picker,
    already localised by the OS (`ADR-001` §2.3, `SYSTEM.md` §4.4).

    There is **no client-side age check**: `PRD.md` AC-A2.2 requires the server
    result to be identical with the form bypassed, and a client block that is
    not also a server block is theatre. `max`/`min` attributes are likewise
    absent — a date the browser refuses to submit is a date the student cannot
    be told about honestly.
    """

    date_of_birth = forms.DateField(
        label=_p("age.label", "Your date of birth"),
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        input_formats=["%Y-%m-%d"],
    )


class ConsentForm(_Form):
    """First-run consent. Six purposes, one checkbox each, **none pre-ticked**.

    E-Com r.4(9) and `PRD.md` AC-A3.1: no `checked` attribute may appear on any
    consent input in the rendered HTML, in either locale.
    `BooleanField(required=False)` with no `initial` is what guarantees that —
    there is no code path in this class that can set one, which is why it is a
    plain form built from the imported purpose tuple and not a formset bound to
    existing `consents` rows.

    `account` is the only required purpose (`REQUIRED_CONSENT_PURPOSES`), and it
    is **still not pre-ticked**: a required consent that arrives ticked is not
    consent. Declining it is allowed here and blocks signing in, which the
    screen says.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for key in CONSENT_PURPOSES:
            self.fields[key] = forms.BooleanField(required=False, initial=False)
        self._wire_aria()


class ProfileForm(_Form):
    """`POST /account`. `{display_name?, locale?}` and nothing else."""

    display_name = forms.CharField(
        label=_p("profile.display_name.label", "The name other students see"),
        max_length=60,
        required=False,
        widget=forms.TextInput(
            attrs={"autocomplete": "nickname", "enterkeyhint": "done"}
        ),
    )

    def __init__(self, *args, locales=("en",), **kwargs):
        super().__init__(*args, **kwargs)
        # Tamil appears here only when `i18n.ta_enabled` is on
        # (`THREAT-MODEL.md` §6.1(c)). With one locale offered the control is
        # still rendered, because a student needs to see what their account is
        # set to, and a hidden field is a worse answer than a list of one.
        self.fields["locale"] = forms.ChoiceField(
            label=_p("profile.locale.label", "Language"),
            choices=[(c, {"en": "English", "ta": "தமிழ்"}[c]) for c in locales],
            required=True,
        )
        self._wire_aria()


class NomineeForm(_Form):
    """`POST /account/nominee` — the s14 nomination.

    **Name and email only.** `record_nomination` rejects any other key, because
    a nominee's phone or address would be personal data about a third party
    with no `COMPLIANCE.md` §7 row. The shape is closed on both sides.

    Not promoted as a feature (`PRD.md` AC-X2.2) — it is one disclosure inside
    privacy settings, behind a `<details>`, because a student who came to find
    a textbook does not need a nominee flow in their way.
    """

    name = forms.CharField(
        label=_p("nominee.name.label", "Their name"),
        max_length=120,
        widget=forms.TextInput(attrs={"autocomplete": "off", "enterkeyhint": "next"}),
    )
    email = forms.EmailField(
        label=_p("nominee.email.label", "Their email address"),
        max_length=254,
        widget=forms.EmailInput(
            attrs={
                "inputmode": "email",
                "autocomplete": "off",
                "autocapitalize": "off",
                "autocorrect": "off",
                "spellcheck": "false",
                "enterkeyhint": "done",
            }
        ),
    )


# ===========================================================================
# S2 — the sell flow, the listing, and the want
# ===========================================================================
#
# THE OPTION TEXT IS THE DISPLAY TEXT, AND THAT IS THE WHOLE DESIGN.
#
# `SYSTEM.md` §4.14 and `PRD.md` AC-S3.1: the four-value `condition` enum is
# **never rendered outside the seller's attributed quotation**. `listings` has
# no free-text description column (`DATA-MODEL.md` §3) — the enum IS what the
# seller stated — so the words a seller picks here are the words that appear
# inside the quotation marks on the listing, verbatim, with nothing of
# BookHop's written between them.
#
# That is why each label below reads as a complete statement a person could
# have made rather than a bare token: a quotation needs a sentence, and
# stitching "Good" + "light pencil" + "torn pages" into prose of our own would
# be BookHop's voice dressed as the seller's (`COPY-DECK.md` §1.2).
#
# `seller_words()` is the one reader that turns stored values back into those
# same labels (`CLAUDE.md` rule 10 — one definition, many readers). A template
# never maps an enum value to a word.

#: `listings.condition` CHECK IN (...) — `DATA-MODEL.md` §3.
#: Four descriptions, not grades. No badge, chip, star, letter or score ever
#: renders beside one (AC-S3.1).
CONDITION_CHOICES = (
    ("AS_NEW", _p("sell.condition.AS_NEW", "As new")),
    ("GOOD", _p("sell.condition.GOOD", "Good")),
    ("FAIR", _p("sell.condition.FAIR", "Fair")),
    ("HEAVILY_USED", _p("sell.condition.HEAVILY_USED", "Heavily used")),
)

#: `listings.annotation_level`. **Neutral fact, never a defect and never a
#: feature** (AC-S3.3): a senior's pencil marks are the one thing a hand-me-down
#: has that a new copy does not, and calling them damage would be a judgement.
ANNOTATION_CHOICES = (
    ("NONE", _p("sell.annotation.NONE", "Nothing written in it")),
    ("LIGHT_PENCIL", _p("sell.annotation.LIGHT_PENCIL", "Some pencil marks")),
    ("HIGHLIGHTED", _p("sell.annotation.HIGHLIGHTED", "Highlighting in it")),
    ("HEAVY_NOTES", _p("sell.annotation.HEAVY_NOTES", "Notes written throughout")),
)

#: `listings.damage_flags` — a `text[]` whose members are a subset of these.
DAMAGE_CHOICES = (
    ("WATER", _p("sell.damage.WATER", "Water damage")),
    ("TORN_PAGES", _p("sell.damage.TORN_PAGES", "Torn pages")),
    ("MISSING_PAGES", _p("sell.damage.MISSING_PAGES", "Missing pages")),
    ("BROKEN_SPINE", _p("sell.damage.BROKEN_SPINE", "Broken spine")),
    ("LOOSE_PAGES", _p("sell.damage.LOOSE_PAGES", "Loose pages")),
    ("COVER_DAMAGE", _p("sell.damage.COVER_DAMAGE", "Damage to the cover")),
)

#: The affirmative "none of these" of AC-S3.2. **It is a form value only and is
#: never stored**: `damage_flags` stays `[]`, which is what the column means.
#: Its label is written as a statement because it is quoted on the listing like
#: every other thing the seller said — an empty damage list rendered as silence
#: would be the implied no-damage claim AC-S3.2 exists to prevent, and rendered
#: as BookHop's "no damage" would be our claim about their book.
NO_DAMAGE = "NONE_OF_THESE"
_NO_DAMAGE_LABEL = _p("sell.damage.none", "No damage to report")

#: `listings.language` and `books.language` CHECK IN ('en','ta','hi','other').
#: The *physical copy's* language, which may differ from the catalogue row's.
LANGUAGE_CHOICES = (
    ("en", _p("sell.language.en", "English")),
    ("ta", _p("sell.language.ta", "Tamil")),
    ("hi", _p("sell.language.hi", "Hindi")),
    ("other", _p("sell.language.other", "Another language")),
)

#: `listings.category`. **`GENERAL_READING` is representable and UI-hidden**
#: (D-007, `DATA-MODEL.md` §3) — it is absent from this tuple rather than
#: present-and-disabled, because a disabled option still discloses the choice.
CATEGORY_CHOICES = (
    ("PRESCRIBED_TEXTBOOK", _p("sell.category.PRESCRIBED_TEXTBOOK", "On a reading list")),
    ("REFERENCE", _p("sell.category.REFERENCE", "A reference book")),
)

#: `API-CONTRACT.md` §5.2. Both are also enforced by L1; these exist so the
#: student is told in words rather than by a 413 or a 422.
MAX_PHOTOS = 4
MAX_PHOTO_BYTES = 8 * 1024 * 1024

#: `asking_price_paise` CHECK (>=0 AND <=10000000) — `DATA-MODEL.md` §3.
MAX_PRICE_RUPEES = 100000

_LABELS = {
    "condition": dict(CONDITION_CHOICES),
    "annotation_level": dict(ANNOTATION_CHOICES),
    "damage": dict(DAMAGE_CHOICES),
}


def seller_words(condition, annotation_level, damage_flags):
    """The seller's own statements about one copy, in display order.

    The single reader of `_LABELS`. Returns a list of strings, each one the
    exact option text the seller chose, for rendering inside the attributed
    quotation and **nowhere else** (`SYSTEM.md` §4.14).

    An unrecognised stored value is **dropped rather than printed raw**: a
    screen reading `HEAVILY_USED` would be `JOURNEYS.md` Appendix A's
    "raw state name" failure, and inventing a word for a value we do not know
    would be putting words in a student's mouth. A value that arrives here
    unknown means the enum moved, and the listing then shows less than the
    seller said — which is the safe direction.
    """
    words = [
        _LABELS["condition"].get(condition),
        _LABELS["annotation_level"].get(annotation_level),
    ]
    flags = list(damage_flags or ())
    if flags:
        words += [_LABELS["damage"].get(flag) for flag in flags]
    else:
        words.append(_NO_DAMAGE_LABEL)
    return [str(word) for word in words if word]


class IsbnForm(_Form):
    """`GET /sell/find-book` — step 1 of `JOURNEYS.md` J2, and the whole of it.

    **One field, and the ISBN is required** (AC-S4.4: a book with no ISBN needs
    staff approval and cannot be self-published, so there is no "I don't have
    one" path here to offer).

    THIS FORM CHECKS SHAPE; THE SERVICE OWNS THE RULE. Thirteen digits is a
    shape and it buys the student a precise message with the count in it
    (`sell.isbn.error`). The **checksum** is `catalog.find_book_by_isbn`'s and
    is not re-implemented here — `CLAUDE.md` rule 10, and a second hand-made
    copy of a check digit is exactly the divergence that rule exists for.

    A GET form, so the resolved book is a shareable, reloadable,
    back-button-able URL. `inputmode="numeric"` and not `type="number"`: a
    spinner on a 13-digit identifier is wrong, and Android's numeric keypad is
    what the student actually needs.
    """

    isbn = forms.CharField(
        label=_p("sell.isbn.label", "ISBN (13 digits, under the barcode)"),
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "inputmode": "numeric",
                "autocomplete": "off",
                "autocapitalize": "off",
                "autocorrect": "off",
                "spellcheck": "false",
                "enterkeyhint": "search",
            }
        ),
    )

    def clean_isbn(self):
        raw = "".join(ch for ch in self.cleaned_data["isbn"] if ch.isdigit())
        if len(raw) != 13:
            raise forms.ValidationError(
                _p(
                    "sell.isbn.error",
                    "That is %(n)s digits. An ISBN-13 has 13 — check the "
                    "number under the barcode.",
                )
                % {"n": len(raw)}
            )
        return raw


class BookDetailsForm(_Form):
    """The "we don't have this ISBN yet" branch of J2 step 2.

    Never a dead end (`COPY-DECK.md` `sell.isbn.notfound`): the student types
    what is on the title page and `catalog.create_book` makes the row, which
    lands with `staff_verified_at` NULL for the review queue.

    Edition is **required** here and nowhere else. It is the field the whole
    product turns on — *"a syllabus-to-shelf matching layer for edition-locked
    prescribed textbooks"* — and the one a seller is most likely to skip.
    """

    title = forms.CharField(
        label=_p("sell.title.label", "Title, exactly as it is on the cover"),
        max_length=300,
        widget=forms.TextInput(attrs={"enterkeyhint": "next"}),
    )
    authors = forms.CharField(
        label=_p("sell.authors.label", "Author or authors"),
        max_length=300,
        widget=forms.TextInput(attrs={"enterkeyhint": "next"}),
    )
    edition_label = forms.CharField(
        label=_p("sell.edition.label", "Edition"),
        max_length=120,
        widget=forms.TextInput(attrs={"enterkeyhint": "next"}),
    )
    publisher = forms.CharField(
        label=_p("sell.publisher.label", "Publisher"),
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={"enterkeyhint": "next"}),
    )
    publication_year = forms.IntegerField(
        label=_p("sell.year.label", "Year it was published"),
        required=False,
        min_value=1400,
        max_value=2100,
        widget=forms.NumberInput(attrs={"inputmode": "numeric", "enterkeyhint": "next"}),
    )

    def clean_authors(self):
        """`books.authors` is `text[]`. One field, split on commas, because two
        inputs for "A. Kumar and R. Singh" is a worse form than one."""
        names = [n.strip() for n in self.cleaned_data["authors"].split(",")]
        return [n for n in names if n]


class ListingForm(_Form):
    """`POST /sell` — J2 steps 4, 5 and 6 on one screen.

    Three screens of required input is AC-S1.1's ceiling and this is the middle
    one: what is wrong with the copy, what the seller is asking, and the
    undertaking. Nothing here is pre-ticked and nothing is pre-filled with a
    judgement.

    **THERE IS NO SUGGESTED PRICE, NO RANGE AND NO "SIMILAR BOOKS" ON THIS
    FORM** (EX-3, AC-S2.2). The seller's own number is the entire mechanism.
    """

    condition = forms.ChoiceField(
        label=_p("sell.condition.pick", "Which of these describes your copy?"),
        choices=CONDITION_CHOICES,
        widget=forms.RadioSelect,
    )
    annotation_level = forms.ChoiceField(
        label=_p("sell.annotation.pick", "Has anyone written in it?"),
        choices=ANNOTATION_CHOICES,
        widget=forms.RadioSelect,
    )
    damage_flags = forms.MultipleChoiceField(
        label=_p("sell.damage.pick", "Is anything damaged?"),
        choices=DAMAGE_CHOICES + ((NO_DAMAGE, _NO_DAMAGE_LABEL),),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )
    language = forms.ChoiceField(
        label=_p("sell.language.label", "What language is this copy in?"),
        choices=LANGUAGE_CHOICES,
        initial="en",
    )
    category = forms.ChoiceField(
        label=_p("sell.category.label", "What kind of book is it?"),
        choices=CATEGORY_CHOICES,
        initial="PRESCRIBED_TEXTBOOK",
    )
    asking_price_rupees = forms.CharField(
        label=_p("sell.price.label", "What are you asking for it?"),
        max_length=12,
        widget=forms.TextInput(
            attrs={
                "inputmode": "numeric",
                "autocomplete": "off",
                "spellcheck": "false",
                "enterkeyhint": "next",
            }
        ),
    )
    seller_terms = forms.BooleanField(
        label=_p(
            "sell.terms.label",
            "I have read the seller terms and this copy is the original, not a "
            "photocopy, a scan or a spiral-bound reproduction.",
        ),
        required=True,
        initial=False,
    )

    def clean_damage_flags(self):
        """AC-S3.2: damage is **affirmatively confirmed**, both ways.

        An untouched list that submits as empty is an implied no-damage claim
        the seller never made — *"exactly the misdescription we would have
        authored"* — so nothing ticked is a validation error, not a default.
        And "none of these" beside a damage tick is a contradiction we must not
        resolve on the seller's behalf.

        `NONE_OF_THESE` is stripped here, so what reaches L1 is always a subset
        of the six real flags and `[]` carries its CHECK-constraint meaning.
        """
        picked = set(self.cleaned_data.get("damage_flags") or ())
        real = sorted(picked - {NO_DAMAGE})
        if not picked:
            raise forms.ValidationError(
                _p(
                    "sell.damage.error",
                    "Tick what is damaged, or tick “No damage to report”.",
                )
            )
        if NO_DAMAGE in picked and real:
            raise forms.ValidationError(
                _p(
                    "sell.damage.contradiction",
                    "You ticked “No damage to report” and also ticked "
                    "damage. Leave only the one that is true.",
                )
            )
        return real

    def clean_asking_price_rupees(self):
        """Whole rupees, refused rather than rounded.

        **`CLAUDE.md` rule 18.** The column is an integer and PostgreSQL will
        happily round `300.75` to `301` — *a rounded money value is a wrong
        value that looks right*, and this is the one column ADR-003 §2.1
        permits to exist. A schema that cannot hold a float does not detect one
        being sent, so detection lives here: a decimal point is named and
        refused, never silently resolved in either direction.

        Parsed by hand rather than with `IntegerField` because the three
        mistakes a student actually makes — `₹280`, `2,80`, `280.50` —
        each deserve a different sentence, and `IntegerField` gives one.
        """
        raw = self.cleaned_data["asking_price_rupees"].strip()
        cleaned = raw.replace(",", "").replace("₹", "").replace(" ", "").lstrip("+")
        if "." in cleaned:
            raise forms.ValidationError(
                _p(
                    "sell.price.whole",
                    "Whole rupees only, no paise. Round it to the rupee yourself "
                    "rather than letting BookHop round it for you.",
                )
            )
        if not cleaned.isdigit():
            raise forms.ValidationError(
                _p("sell.price.digits", "Type the amount in rupees, in digits.")
            )
        rupees = int(cleaned)
        if rupees > MAX_PRICE_RUPEES:
            raise forms.ValidationError(
                _p("sell.price.ceiling", "The most a book can be listed at is ₹%(max)s.")
                % {"max": MAX_PRICE_RUPEES}
            )
        return rupees


class PhotoForm(_Form):
    """`POST /sell/{id}/photos` — **one file per request, always.**

    `SYSTEM.md` §4.5: *"on 3G a 4-file request that dies at 90% loses all four;
    four requests lose one."* With JavaScript off that property comes free —
    one `<input type="file">`, one submit, one round trip, and the page that
    comes back is the resumable state. There is no queue to lose.

    `capture` is on the control per `ADR-001` §2.3 and `SYSTEM.md` §4.5.
    # ponytail: `capture` makes several Android builds open the camera and skip
    # the gallery. Ceiling — a seller who already photographed the book cannot
    # reuse that photo. Drop the attribute if user testing shows sellers
    # photograph books before they reach the form.

    The size limit is checked here **and** by L1. This copy exists so the
    student reads a sentence instead of meeting a 413 from a proxy after paying
    for the upload — 8 MB over 3G is roughly a minute of their money.
    """

    photo = forms.FileField(
        label=_p("sell.photos.label", "Add photos (up to 4)"),
        widget=forms.ClearableFileInput(
            attrs={"accept": "image/*", "capture": "environment"}
        ),
        # Django's default is *"This field is required."* — which is a string
        # that lives in Django's own catalogue, not in `locale/en`, so
        # `tests/unit/test_forbidden_copy.py` never sees it and `COPY-DECK.md`
        # §10.2 never ruled on it. **A framework default is copy nobody
        # reviewed.** It is overridden here because an empty file picker is a
        # real and frequent outcome on a phone, and the sentence should say
        # what happened rather than name a field.
        error_messages={
            "required": _p("sell.photos.none_chosen", "No photo was chosen."),
        },
    )

    def clean_photo(self):
        upload = self.cleaned_data["photo"]
        if upload.size > MAX_PHOTO_BYTES:
            raise forms.ValidationError(
                _p(
                    "sell.photos.too_big",
                    "That photo is %(mb)s MB. The most BookHop takes is 8 MB — "
                    "your camera's own settings can make a smaller one.",
                )
                % {"mb": round(upload.size / (1024 * 1024), 1)}
            )
        return upload


class WantedForm(_Form):
    """`POST /wanted` — `JOURNEYS.md` J4 step 2.

    **This form promises nothing** (AC-B2.5): not a time, not a probability,
    not that the book will arrive. It records a row. `book_requests` CHECK is
    `(book_id IS NOT NULL OR free_text_title IS NOT NULL)`, so an ISBN we do
    not recognise is carried as free text rather than refused — EC-17, and one
    of the few places the product learns something about a syllabus we did not
    know.

    Both fields are optional individually and one is required between them.
    L1 re-asserts the CHECK and will raise; this exists so the student gets a
    sentence rather than a 422.
    """

    isbn = forms.CharField(
        label=_p("wanted.isbn.label", "ISBN, if you have it"),
        max_length=20,
        required=False,
        widget=forms.TextInput(
            attrs={
                "inputmode": "numeric",
                "autocomplete": "off",
                "autocapitalize": "off",
                "spellcheck": "false",
                "enterkeyhint": "next",
            }
        ),
    )
    title = forms.CharField(
        label=_p("wanted.title.label", "Title of the book"),
        max_length=300,
        required=False,
        widget=forms.TextInput(attrs={"enterkeyhint": "next"}),
    )
    course_code = forms.CharField(
        label=_p("wanted.course.label", "Course code, if you know it"),
        max_length=40,
        required=False,
        widget=forms.TextInput(
            attrs={"autocapitalize": "characters", "enterkeyhint": "done"}
        ),
    )

    def clean_isbn(self):
        return "".join(ch for ch in self.cleaned_data.get("isbn", "") if ch.isdigit())

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("isbn") and not cleaned.get("title"):
            raise forms.ValidationError(
                _p("wanted.need_one", "Give either the ISBN or the title.")
            )
        return cleaned
