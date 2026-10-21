"""Nothing is stubbed silently.

TASKS §3: backend commits the accounts signatures as stubs at the end of S0 so
frontend-developer is unblocked. A stub that returned a plausible value would
let a whole slice be built against behaviour that does not exist, so every one
raises NotImplementedError and names the slice that implements it.

This test also pins the frozen signatures from API-CONTRACT §3: if a name or an
argument changes, frontend's calls break here rather than in the browser.
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


@pytest.mark.parametrize("name,params", sorted(SIGNATURES.items()))
def test_stub_raises_rather_than_returning_a_plausible_value(name, params):
    fn = getattr(services, name)
    with pytest.raises(NotImplementedError, match="S1"):
        fn(**{p: None for p in params})
