"""Session establishment — API-CONTRACT §2.1's cookie, in one place.

**Why this module exists at all.** API-CONTRACT §3 freezes
`consume_magic_link(token, ip, user_agent) -> User`: L1 returns the user and the
*caller* establishes the session, because a service function that touched
`request` would not be callable from a management command or a job. But L2
(`apps/accounts/api.py`, mine) and L3 (`web/views.py`, frontend's) both need to
do it, and two implementations of "what it means to be signed in" is the
hand-copied rule `CLAUDE.md` rule 10 is about. So it is three functions here,
imported by both.

It lives in `apps.accounts` rather than `apps.core` because it loads a `User`,
and `apps.core` is the one app nothing else may depend on in the other
direction.

There is **no password path and no `django.contrib.auth`**. Students have no
password column at all (ADR-001 §2.5), so Django's auth framework would buy a
second user table and a login view nobody can reach. Staff sign-in is password
plus TOTP in the Django admin and lands with the admin in S2.
"""

from django.utils import timezone

from .models import User

#: The session key holding the signed-in user's id. Namespaced so it cannot
#: collide with a Django or third-party key, and read by `erase_account`'s
#: session invalidation — which is why it is a constant and not a literal in
#: two files.
SESSION_USER_KEY = "_bookhop_user_id"


def start_session(request, user):
    """Sign `user` in. **Rotates the session key** (API-CONTRACT §2.1).

    Rotation on login is ASVS V7 L2 and it is the control against session
    fixation: without it, an attacker who plants a session cookie before sign-in
    holds a valid session afterwards. `cycle_key` keeps the session's data and
    issues a new key, which is exactly the required behaviour.
    """
    request.session.cycle_key()
    request.session[SESSION_USER_KEY] = user.id
    return user


def end_session(request):
    """Sign out. Flushes server-side, not just the cookie (ASVS V7 L2)."""
    request.session.flush()


def session_user(request):
    """The signed-in `User`, or None. Never raises on a stale session.

    A session pointing at a tombstoned or missing user returns None **and
    flushes**, so a student whose account was erased on another device is signed
    out here rather than holding a session that resolves to a deleted identity.
    """
    user_id = request.session.get(SESSION_USER_KEY)
    if not user_id:
        return None
    user = User.all_objects.filter(id=user_id).exclude(status="TOMBSTONED").first()
    if user is None:
        request.session.flush()
        return None
    # `last_seen_at` is the only thing a read updates, and it is not rewritten
    # on every request: SESSION_SAVE_EVERY_REQUEST already gives the rolling
    # expiry, and a write per request would make every GET a write.
    if user.last_seen_at is None or (timezone.now() - user.last_seen_at).total_seconds() > 3600:
        User.all_objects.filter(id=user.id).update(last_seen_at=timezone.now())
    return user
