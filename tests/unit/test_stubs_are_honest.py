"""Nothing is stubbed silently, and nothing is implemented silently either.

TASKS §3: backend commits the accounts signatures as stubs at the end of S0 so
frontend-developer is unblocked. A stub that returned a plausible value would
let a whole slice be built against behaviour that does not exist, so every one
raises NotImplementedError and names the slice that implements it.

This test also pins the frozen signatures from API-CONTRACT §3: if a name or an
argument changes, frontend's calls break here rather than in the browser.

**Updated in S1, and the direction of the change matters.** In S0 every function
here was a stub. S1 implements nine of the ten, so the honest assertion is no
longer "they all raise" — it is **a partition**: each name is either implemented
or a stub that names its slice, with no third state. The two tests below are the
two halves, and `test_the_partition_covers_every_contract_name` is what stops a
name quietly leaving both sets.

`accept_seller_terms` is the one that stays a stub: `seller_terms_acceptances`
is an **S2** table (DATA-MODEL §2) and `create_listing` is the caller that
refuses without it, so implementing it here would be a function with no table
and no caller.
"""

import inspect

import pytest

from apps.accounts import services

SIGNATURES = {
    "request_magic_link": ["email", "ip", "user_agent"],
    "consume_magic_link": ["token", "ip", "user_agent"],
    "submit_age_declaration": ["user", "dob", "ip"],
    "review_age": ["staff", "user", "outcome", "note"],
    "grant_consent": ["user", "purpose_key", "notice_version", "mechanism", "ip", "user_agent"],
    "withdraw_consent": ["user", "purpose_key", "mechanism", "ip", "user_agent"],
    "accept_seller_terms": ["user", "notice_version", "ip"],
    "update_profile": ["user", "display_name", "locale"],
    "erase_account": ["user", "reason"],
    "log_personal_data_access": ["staff", "subject_pseudonym", "fields", "purpose"],
}


@pytest.mark.parametrize("name,params", sorted(SIGNATURES.items()))
def test_signature_matches_the_frozen_contract(name, params):
    fn = getattr(services, name, None)
    assert fn is not None, f"API-CONTRACT §3 names apps.accounts.services.{name}"
    assert list(inspect.signature(fn).parameters) == params


#: The names still awaiting a later slice, each with the slice that lands it.
#: A name here must raise and must say which slice; a name absent from here must
#: **not** raise `NotImplementedError` at all.
PENDING = {
    "accept_seller_terms": "S2",
}


@pytest.mark.parametrize("name,slice_name", sorted(PENDING.items()))
def test_a_pending_stub_raises_and_names_its_slice(name, slice_name):
    """A stub that returns a plausible value is how a frontend gets built
    against behaviour that does not exist, and how a gate gets tested against a
    mock that always passes."""
    fn = getattr(services, name)
    params = SIGNATURES[name]
    with pytest.raises(NotImplementedError, match=slice_name):
        fn(**{p: None for p in params})


@pytest.mark.parametrize(
    "name,params", sorted((n, p) for n, p in SIGNATURES.items() if n not in PENDING)
)
def test_an_implemented_function_is_not_still_a_stub(name, params):
    """The half that did not exist in S0, and the one that catches the failure
    mode this slice could actually have: **a function that was left stubbed
    while its endpoint, its tests and its migration all shipped.**

    Called with `None` for everything, which every one of these refuses — on
    `ValidationFailed`, `NotPermitted`, `NotAuthenticated` or `AttributeError`.
    The assertion is only that the refusal is **not** `NotImplementedError`:
    what each one refuses *with* is its own test file's business, and asserting
    it here would duplicate nine files' worth of behaviour in a guard.
    """
    fn = getattr(services, name)
    try:
        fn(**{p: None for p in params})
    except NotImplementedError as still_a_stub:  # pragma: no cover - the failure case
        pytest.fail(
            f"apps.accounts.services.{name}() is still a stub, but S1 ships its "
            f"endpoint and its tests: {still_a_stub}"
        )
    except Exception:
        pass  # any other refusal is the function's own contract


def test_the_partition_covers_every_contract_name():
    """`CLAUDE.md` rule 9's shape, applied to this file: every API-CONTRACT §3
    accounts name is in exactly one of the two sets, so a name cannot leave
    both and be checked by neither."""
    assert set(PENDING) <= set(SIGNATURES)
    implemented = set(SIGNATURES) - set(PENDING)
    assert implemented and set(PENDING), "one side of the partition is empty"
    assert implemented | set(PENDING) == set(SIGNATURES)
