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
    "ConsentForm",
    "NomineeForm",
    "ProfileForm",
    "SignInForm",
    "CONSENT_PURPOSES",
    "REQUIRED_CONSENT_PURPOSES",
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
