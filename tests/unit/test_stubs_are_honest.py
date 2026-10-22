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

**S2 empties `PENDING`, and the empty set is asserted rather than deleted.**
`accept_seller_terms` was the one remaining stub: `seller_terms_acceptances`
is an S2 table (DATA-MODEL §2) and `create_listing` is the caller that refuses
without it, so S1 implementing it would have been a function with no table and
no caller. Both now exist.

The parametrised test below therefore runs over nothing, which is exactly the
shape `CLAUDE.md` rule 10 is about — so
`test_the_pending_set_is_empty_because_every_stub_landed` asserts the
**reason** it is empty, and `test_no_service_function_is_a_silent_stub` is the
standing control that a future slice cannot add one back unannounced.
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
PENDING = {}


def test_the_pending_set_is_empty_because_every_stub_landed():
    """Why `PENDING` is empty, asserted so emptiness is a fact and not a gap.

    An empty parametrisation silently runs zero assertions. This says what the
    zero means: `accept_seller_terms` was the last stub and S2 implemented it
    against the table and the caller that make it meaningful.
    """
    assert PENDING == {}, PENDING
    fn = getattr(services, "accept_seller_terms")
    source = inspect.getsource(fn)
    assert "NotImplementedError" not in source, (
        "accept_seller_terms is listed as landed but still raises"
    )


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
    assert implemented | set(PENDING) == set(SIGNATURES)

    # **The "one side is empty" assertion is gone, and that is the point of
    # this comment.** It was right while a stub existed: an empty `PENDING`
    # with a stub still in the code is the gap. S2 landed the last stub, so
    # `PENDING` is legitimately empty — and asserting it must not be would
    # mean the suite could only go green again by keeping a stub, which is a
    # test demanding the defect it was written to catch.
    #
    # What replaces it is the thing that was actually wanted: **no name may be
    # in neither set** (the line above), and **no implemented name may still
    # be a stub** — asserted by behaviour below rather than by bookkeeping, so
    # a future slice cannot add a stub and forget to register it.
    for name in sorted(implemented):
        source = inspect.getsource(getattr(services, name))
        assert "raise NotImplementedError" not in source, (
            f"{name} is on the implemented side of the partition and still "
            "raises NotImplementedError. Add it to PENDING with its slice, or "
            "implement it — a stub that nothing declares is how a frontend "
            "gets built against behaviour that does not exist."
        )
