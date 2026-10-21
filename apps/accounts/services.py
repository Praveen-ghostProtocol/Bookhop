"""apps.accounts service layer (L1) — API-CONTRACT §3, accounts block.

**These are S0 stubs.** The signatures are frozen and are what
frontend-developer codes `web/views.py` against from today (TASKS §3). The
bodies land in S1 together with the `users`, `email_login_tokens`,
`age_verification_events`, `campus_verifications`, `notice_versions`,
`consents`, `data_subject_requests`, `user_tombstones` and
`personal_data_access_log` tables.

**There is no `age_check_pending` table.** DATA-MODEL §2 deletes it (amendment
A-5 / PRD CG-5) and ADR-003 §2.3 withdrew its deny-list exception: **no DOB is
persisted anywhere, in any state.** `submit_age_declaration` checks the
declared date and writes only the outcome. This paragraph is here because the
earlier version of this docstring named the table, which read as an instruction
to recreate it (REVIEW-S0 S10).

Every one raises. None returns a plausible-looking value: a stub that returns a
fake User is how a frontend gets built against behaviour that does not exist,
and how a gate gets tested against a mock that always passes.
"""

_S1 = (
    "apps.accounts.services.{name}() is an S0 signature stub. "
    "Implemented in S1 (TASKS.md §2 'S1 — Accounts, age, campus verification, "
    "profile, deletion'). Do not work around this; the frozen signature is in "
    "API-CONTRACT.md §3."
)


def _todo(name):
    raise NotImplementedError(_S1.format(name=name))


def request_magic_link(email: str, ip, user_agent) -> None:
    """ADR-001 §2.5. Raises RateLimited, EmailDomainNotRecognised.

    Note for L2/L3: the endpoint **always returns 202 whatever happens**
    (API-CONTRACT §5.1) — a different response for an unknown address is an
    account-enumeration oracle.
    """
    _todo("request_magic_link")


def consume_magic_link(token: str, ip, user_agent):
    """Returns User. Raises TokenInvalid, TokenExpired, TokenAlreadyUsed."""
    _todo("consume_magic_link")


def submit_age_declaration(user, dob, ip):
    """Returns AgeOutcome. Raises UnderEighteen.

    Writes `age_verification_events`. A declared DOB under 18 is rejected
    before any row is written and **the DOB is never persisted**
    (DATA-MODEL §2).
    """
    _todo("submit_age_declaration")


def review_age(staff, user, outcome: str, note: str) -> None:
    """Raises NotPermitted. `note` must not contain a date of birth."""
    _todo("review_age")


def grant_consent(user, purpose_key, notice_version, mechanism, ip, user_agent) -> None:
    """Appends a `consents` row. Never updates one (DATA-MODEL §2)."""
    _todo("grant_consent")


def withdraw_consent(user, purpose_key, mechanism, ip, user_agent) -> None:
    """Appends a new row with `withdrawn_at` set. A toggle, not an email."""
    _todo("withdraw_consent")


def accept_seller_terms(user, notice_version, ip) -> None:
    _todo("accept_seller_terms")


def update_profile(user, *, display_name=None, locale=None):
    _todo("update_profile")


def erase_account(user, reason="USER_REQUEST") -> None:
    """DATA-MODEL §10.1, one transaction. Tombstone-plus-purge, never DELETE."""
    _todo("erase_account")


def log_personal_data_access(staff, subject_pseudonym, fields, purpose) -> None:
    """DPDP r.6(1)(c). Every admin view of a student's data writes a row."""
    _todo("log_personal_data_access")
