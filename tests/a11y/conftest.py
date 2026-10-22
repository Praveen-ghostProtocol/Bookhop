"""Fixtures for the accessibility sweeps. QA's tree.

`client_as` is duplicated from `tests/contract/conftest.py` and
`tests/e2e/conftest.py` rather than hoisted into `tests/conftest.py`: that
file is shared with other agents' trees, and a QA fixture living there is a
QA change to a file another agent edits in the same slice (`CLAUDE.md`
rule 6). Three identical six-line fixtures in three of QA's own directories
is the cheaper side of that trade.
"""

import pytest


@pytest.fixture
def client_as(db):
    """A **fresh** Django test client signed in as `user`.

    Fresh per call: `client.session` mints a new key on each save while the
    cookie still points at the first, so one client reused across users makes
    every actor after the first anonymous.
    """
    from django.test import Client

    from apps.accounts.sessions import SESSION_USER_KEY

    def _sign_in(user):
        client = Client()
        session = client.session
        session[SESSION_USER_KEY] = user.id
        session.save()
        return client

    return _sign_in
