"""§2.5's authorization placements that S1 cannot exercise yet — asserted now.

**Why this file exists, in backend's framing, which is the right one:** *"by S5
the comment will be four slices old and the person implementing it will be
reading the table, not the reasoning. That is the same gap that produced the
nominee error, one slice later and with a safety report on the other end of
it."*

The nominee defect was not a wrong list inside a stack. It was an endpoint
**assigned to the wrong stack**, where every test that enumerated the code's
stacks agreed with the code by construction, and only deriving membership from
`API-CONTRACT.md` §2.5's own table found it. Three further placements have been
ruled and cannot be implemented for several slices. A comment does not survive
that; a test that turns red the day the table appears does.

So each ruling below is written as an assertion that **skips while the endpoint
does not exist and runs the moment it is mounted** — the same shape as the
erasure assertions, which name their model and slice and go red when the model
arrives.

**The failure mode of this pattern, and how it is closed.** A forward-dated
skip can skip *forever* if the endpoint ships under a path this file did not
predict: the test stays green-ish, the endpoint ships in the wrong stack, and
the guard was theatre. So `test_every_ruled_endpoint_is_reachable_once_its_app_exists`
inverts it — once the owning app is installed, a ruled endpoint that cannot be
resolved is a **failure**, not a skip. The skip is only legitimate while the
app itself does not exist.

Everything here is transcribed from §2.5's membership table and its three
"judgement calls" paragraphs, with the contract's own reasoning kept beside
each row, because the reasoning is the part that decides the next ambiguous
case and it is the part that gets lost.
"""

import uuid

import pytest

pytestmark = pytest.mark.django_db

#: §2.5's four narrowable preconditions and the code each produces.
PRECONDITIONS = {
    "status": ("SUSPENDED", 403),
    "adult": ("NOT_ADULT_VERIFIED", 403),
    "campus": ("NOT_CAMPUS_VERIFIED", 403),
    "consent": ("CONSENT_REQUIRED", 403),
}

#: The rulings, transcribed from §2.5. Each row: the endpoint, the method, the
#: stack the contract assigns it, the app and slice that create it, the body
#: discriminator where the split is by field or category, and the contract's
#: **own words** for why — because by S5 the words are what settles the next
#: question, and a table without them is the thing that failed last time.
RULED = [
    {
        "id": "safety_report_incident",
        "method": "POST",
        "path": "/api/v1/reports",
        "app": "apps.safety",
        "slice": "S6",
        "stack": "S",
        "body": {"category": "SAFETY_INCIDENT", "target_type": "USER", "target_id": 1,
                 "body": "qa placement probe"},
        "why": (
            "THREAT-MODEL §5.7 already rules that no safety path is rate-limited "
            "to zero or requires an account. **A suspended user may be the one in "
            "danger**, and a platform that suspends someone and thereby mutes "
            "their safety report has built the wrong thing."
        ),
    },
    {
        "id": "safety_report_ncii",
        "method": "POST",
        "path": "/api/v1/reports",
        "app": "apps.safety",
        "slice": "S6",
        "stack": "S",
        "body": {"category": "NCII_OR_IMPERSONATION", "target_type": "USER",
                 "target_id": 1, "body": "qa placement probe"},
        "why": (
            "The second category §2.5 names in the same breath as "
            "SAFETY_INCIDENT, and the one where the reporter is most likely to "
            "be the person harmed rather than a bystander. Non-consensual "
            "intimate imagery and impersonation are the two the IT Rules give "
            "the shortest clocks, so a precondition that refuses the report is "
            "also a precondition that starts the clock late."
        ),
    },
    {
        "id": "non_safety_report",
        "method": "POST",
        "path": "/api/v1/reports",
        "app": "apps.safety",
        "slice": "S6",
        "stack": "M",
        "body": {"category": "SPAM", "target_type": "LISTING", "target_id": 1,
                 "body": "qa placement probe"},
        "why": (
            "The same endpoint is split by **category**: §2.5's M row reads "
            "'non-safety reports'. A split by a body value is the shape that "
            "already went wrong once on `PATCH /account`, so both sides are "
            "asserted rather than one."
        ),
    },
    {
        "id": "support_ticket_reply",
        "method": "POST",
        "path": "/api/v1/support/tickets/1/replies",
        "app": "apps.support",
        "slice": "S5",
        "stack": "S",
        "body": {"body": "qa placement probe"},
        "why": (
            "**Suspension with no channel to contest it is a due-process "
            "failure**, and it is also a grievance problem: r.3(2)(a) does not "
            "carve out people we have sanctioned. They may reply to an existing "
            "ticket; **opening a new one is in M**, so the channel is the appeal "
            "rather than a fresh queue."
        ),
    },
    {
        "id": "support_ticket_open",
        "method": "POST",
        "path": "/api/v1/support/tickets",
        "app": "apps.support",
        "slice": "S5",
        "stack": "M",
        "body": {"subject": "qa", "body": "qa placement probe"},
        "why": (
            "The other half of the same ruling. Reply is the appeal; **opening a "
            "new ticket is Stack M**, so a suspended student contests the "
            "suspension in the thread that exists rather than by opening a "
            "fresh queue item."
        ),
    },
    {
        "id": "grievance",
        "method": "POST",
        "path": "/api/v1/grievances",
        "app": "apps.safety",
        "slice": "S6",
        "stack": "S",
        "body": {"body": "qa placement probe"},
        "why": (
            "§2.5's table lists `POST /grievances` in S. It is also the route "
            "IT Rules r.3(2)(a) requires to exist, and API-CONTRACT §5.6 makes "
            "it public — so a precondition that refuses a suspended student is "
            "refusing the complaint channel about the suspension."
        ),
    },
    {
        "id": "account_correction",
        "method": "POST",
        "path": "/api/v1/account/correction",
        "app": "apps.accounts",
        "slice": "S1+",
        "stack": "S",
        "body": {"field": "display_name", "value": "A Corrected Name"},
        "open_finding": (
            "QA-S1 F24: §2.5 names `POST /account/correction` twice — in the "
            "Stack S row with its (s12(1)-(2)) citation, and again as the "
            "justification for putting `display_name` in Stack M ('the right is "
            "satisfied by POST /account/correction, which is in S, "
            "staff-reviewed and logged'). It does not exist: no route in "
            "apps/accounts/urls.py, no handler, and no slice in TASKS.md. So a "
            "suspended student can neither change their display name (Stack M "
            "refuses, correctly) nor use the correction route (absent), and "
            "DPDP s12(1)-(2) has no path at all. strict=True: this goes RED the "
            "day the endpoint is mounted, which is when the row stops being a "
            "reminder and becomes a live assertion."
        ),
        "why": (
            "s12(1)–(2). §2.5 names it twice: once in the S row, and again in "
            "the `display_name` judgement call, where it is **the thing that "
            "makes putting `display_name` in M defensible** — 'the right is "
            "satisfied by POST /account/correction, which is in S, "
            "staff-reviewed and logged'. If this ships in M, the reasoning that "
            "justified the other placement is gone and nothing says so."
        ),
    },
]

#: Stack M endpoints only. §2.5 preconditions 6 and 7 — scope → `404`, and the
#: discovery gate → `403 GATE_CLOSED` — cannot be exercised in S1 at all,
#: because no tenant-scoped object exists to be out of scope and nothing reads
#: a listing. They are the two preconditions most likely to be forgotten,
#: because every S1 endpoint is about the caller's own account.
UNEXERCISED_M_PRECONDITIONS = {
    6: ("object is in actor's visible campus scope (ADR-002 §2) → else 404",
        "a 403 here would confirm the object exists and leak the catalogue "
        "(§2.2: 'the same body either way')"),
    7: ("campus discovery gate open, or both parties are seed (ADR-002 §4) → "
        "else 403 GATE_CLOSED",
        "the gate is the control that keeps BookHop from operating a platform "
        "before the company may; §2.5 puts it in the standing preconditions so "
        "it is not a thing each discovery path remembers"),
}


def _app_installed(dotted):
    from django.conf import settings

    return dotted in settings.INSTALLED_APPS


def _route_exists(path):
    """Does a **real** handler answer this path?

    `resolve()` alone is not the question: `web/urls.py` ends in a catch-all
    `^.*$` for the 404 page, so every path resolves and the naive check was
    True for everything — which would have made every assertion in this file
    pass vacuously the moment its app was installed. Found by this file's own
    `account_correction` row, which is in an app that already exists.

    So the match has to come from an `apps.*` urlconf, which is where L2 lives.
    """
    from django.urls import Resolver404, resolve

    try:
        match = resolve(path)
    except Resolver404:
        return False
    return getattr(match.func, "__module__", "").startswith("apps.")


def _code(response):
    try:
        return response.json().get("error", {}).get("code")
    except Exception:  # noqa: BLE001
        return None


@pytest.fixture
def suspended_student(db):
    """The actor every ruling below is about: a student we have sanctioned.

    `status='SUSPENDED'` is the single precondition that separates Stack S from
    Stack M for a verified student, so it is the one that makes each placement
    observable with one request.
    """
    from apps.accounts.models import User
    from apps.core.models import Campus, City

    city = City.objects.create(name="Chennai", state="Tamil Nadu")
    campus = Campus.objects.create(
        city=city, name="Placement Campus", slug="placement",
        email_domains=["example.test"],
    )
    return User.objects.create(
        email="suspended@example.test", display_name="Suspended Student",
        campus=campus, city=city, status="SUSPENDED",
        adult_verified=True, campus_verified=True,
    )


@pytest.fixture
def sign_in():
    from django.test import Client

    from apps.accounts.sessions import SESSION_USER_KEY

    def _sign_in(user):
        client = Client()
        session = client.session
        session[SESSION_USER_KEY] = user.id
        session.save()
        return client

    return _sign_in


# --------------------------------------------------------------------------
# the three rulings, asserted before the code exists
# --------------------------------------------------------------------------


def _params():
    """Rows, with a strict xfail on any row whose finding is still open.

    **Strict, and on the row rather than the module**, because a permanently
    red suite means every later run carries a known failure and the only way to
    tell a new one is to read the names — which is how a real failure gets
    waved through, and this project has already paid for failures landing on
    tests that did not cause them. `xfail(strict=True)` has the semantics the
    finding actually wants: quiet while the gap is open, **red the day it
    closes** and the reminder is no longer needed.
    """
    out = []
    for ruling in RULED:
        marks = []
        if ruling.get("open_finding"):
            marks.append(pytest.mark.xfail(strict=True, reason=ruling["open_finding"]))
        out.append(pytest.param(ruling, marks=marks, id=ruling["id"]))
    return out


@pytest.mark.parametrize("ruling", _params())
def test_the_ruled_stack_placement_holds_the_day_the_endpoint_exists(
    ruling, suspended_student, sign_in
):
    """One ruling, one assertion, live from the day the route is mounted.

    While the owning app does not exist this **skips, naming the app, the slice
    and the contract's reasoning** — so the reasoning travels with the test and
    a developer who hits the skip reads the argument rather than a TODO.

    The assertion is behavioural and needs no knowledge of the handler: a
    suspended student is sent at the endpoint, and

    * **Stack S** must not refuse with `401`/`403`. Any other answer — including
      a `400` for a body this file could not have predicted four slices early —
      means the precondition gate let the actor through, which is the whole
      claim.
    * **Stack M** must refuse with exactly `403 SUSPENDED`.

    That asymmetry is deliberate: for S the question is *"was the right
    switched off?"* and a validation error answers it; for M the question is
    *"was the marketplace write refused for the stated reason?"* and only the
    stated code answers it.
    """
    if not _app_installed(ruling["app"]):
        pytest.skip(
            f"NOT BUILT YET (app={ruling['app']}, slice={ruling['slice']}): "
            f"§2.5's table places {ruling['method']} {ruling['path']} in "
            f"**Stack {ruling['stack']}**. This runs the day that app is "
            f"installed.\n\nThe contract's reasoning, which is the part that "
            f"decides the next ambiguous case: {ruling['why']}"
        )

    assert _route_exists(ruling["path"]), (
        f"{ruling['app']} is installed but {ruling['path']} does not resolve. "
        "Either the path moved — in which case this row needs updating in the "
        "same commit, not later — or the endpoint is not built and the app "
        "landed first."
    )

    client = sign_in(suspended_student)
    response = client.post(
        ruling["path"], data=ruling["body"], content_type="application/json",
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )

    if ruling["stack"] == "S":
        status = response.status_code
        # The claim for Stack S is about the **gate**, so any response that
        # proves the actor reached the handler answers it -- including a 400
        # for a body this file could not have predicted four slices early.
        # But three families prove nothing and one contradicts the ruling:
        #
        #   401 / 403  the gate refused. The finding.
        #   404 / 405  never routed, or routed and the method was wrong, so the
        #              gate was never reached and the cell is unmeasured.
        #   5xx        would mask a crash *inside* the gate as a pass.
        #   429        rate limited, so the gate's answer is unobservable -- and
        #              on the safety rows it contradicts the very reasoning this
        #              row cites, THREAT-MODEL §5.7: no safety path is rate
        #              limited to zero.
        assert status not in (401, 403), (
            f"{ruling['id']}: §2.5 places this in Stack S and a suspended "
            f"student was refused with {status} {_code(response)}."
            f"\n\n{ruling['why']}\n\n§2.5: 'A right that a precondition can "
            "switch off is not a right.'"
        )
        assert status not in (404, 405), (
            f"{ruling['id']}: {status} means the request never reached the "
            "gate, so this cell is unmeasured rather than passing. Either the "
            "path or the method in this row is wrong and must be corrected in "
            "the same commit as whatever moved it."
        )
        assert status < 500, (
            f"{ruling['id']}: {status} would mask a crash inside the gate as a "
            f"pass. Body: {response.content[:200]!r}"
        )
        assert status != 429, (
            f"{ruling['id']}: rate limited, so the gate's answer is "
            "unobservable. On a safety row this is also a finding in its own "
            "right — THREAT-MODEL §5.7: no safety path is rate limited to "
            "zero, and this row's own reasoning cites it."
        )
    else:
        assert (response.status_code, _code(response)) == (403, "SUSPENDED"), (
            f"{ruling['id']}: §2.5 places this in Stack M, so a suspended "
            f"student must get 403 SUSPENDED; got {response.status_code} "
            f"{_code(response)}.\n\n{ruling['why']}"
        )


def test_every_ruled_endpoint_is_reachable_once_its_app_exists():
    """**The guard that stops this file becoming theatre.**

    A forward-dated skip can skip forever: if the endpoint ships at a path this
    file did not predict, every assertion above stays skipped, the endpoint
    ships in whichever stack somebody chose, and the test that was supposed to
    catch it reported nothing. That is a `CLAUDE.md` rule 12 failure with a
    four-slice fuse.

    So the condition is inverted. Once the owning app is **installed**, a ruled
    endpoint that does not resolve is a failure — either the path moved and
    this row must move with it in the same commit, or the endpoint is missing
    and §2.5 lists it.

    **Rows with an open finding are excluded here, deliberately**, and they have
    their own strict-xfail assertion below. If the known gap were left in this
    list the whole test would be an xfail, and a *second* row going unreachable
    later would be absorbed into an expected failure — a known failure masking a
    new one, which is the exact thing converting these to xfail was meant to
    prevent. One known gap must not buy silence for the next.
    """
    unreachable = [
        f"{r['method']} {r['path']} (app={r['app']}, slice={r['slice']})"
        for r in RULED
        if not r.get("open_finding")
        and _app_installed(r["app"])
        and not _route_exists(r["path"])
    ]
    assert unreachable == [], (
        "these endpoints' apps are installed but §2.5's ruled paths do not "
        f"resolve, so their stack placements are no longer being checked: "
        f"{unreachable}"
    )


def test_each_ruling_carries_the_contracts_reasoning_and_not_just_a_verdict():
    """The rulings are kept with their *why* because the why is what was lost.

    §2.5 calls these "three placements that are judgement calls, with the
    reasoning, because each could defensibly have gone the other way". A table
    of verdicts with the reasoning stripped out is exactly what the next person
    will read, and it is what makes them choose the other way.
    """
    for ruling in RULED:
        assert len(ruling["why"]) > 80, f"{ruling['id']} has no reasoning recorded"
        assert ruling["stack"] in ("S", "M")
        assert ruling["slice"], ruling["id"]


def test_both_sides_of_each_split_endpoint_are_covered():
    """A split endpoint asserted on one side only is the nominee error again.

    `POST /reports` is split by **category** and the support endpoints are split
    across **two paths**; each needs a row on both sides, or the half that is
    not asserted is the half that drifts. Derived from the rows rather than
    counted, so a new split needs both halves to satisfy this.
    """
    by_path = {}
    for ruling in RULED:
        by_path.setdefault(ruling["path"], set()).add(ruling["stack"])
    split_paths = {p for p, stacks in by_path.items() if len(stacks) > 1}
    assert "/api/v1/reports" in split_paths, (
        "the category split on POST /reports is asserted on one side only"
    )

    support = {r["stack"] for r in RULED if "support/tickets" in r["path"]}
    assert support == {"S", "M"}, (
        "the ticket reply/open split is asserted on one side only: the ruling "
        "is that reply is the appeal channel and opening is not"
    )


# --------------------------------------------------------------------------
# the two Stack M preconditions S1 cannot exercise at all
# --------------------------------------------------------------------------


@pytest.mark.parametrize("number", sorted(UNEXERCISED_M_PRECONDITIONS))
def test_a_stack_m_precondition_s1_cannot_exercise(number):
    """§2.5 preconditions 6 and 7, recorded as unexercised rather than assumed.

    Every S1 endpoint is about the caller's own account, so **no S1 request can
    be out of scope and none reads a listing**. These two are therefore the
    preconditions most likely to be forgotten by the first endpoint that needs
    them, and they are the two with the largest consequences — one leaks the
    catalogue, the other is the discovery gate.

    This is a skip rather than a silence: `CLAUDE.md` rule 12 says a property
    that cannot be tested skips with a reason naming the slice, and the reason
    here names the precondition verbatim so the S2 developer reading the skip
    reads the rule.
    """
    rule, why = UNEXERCISED_M_PRECONDITIONS[number]
    if not _app_installed("apps.listings"):
        pytest.skip(
            f"NOT EXERCISABLE IN S1 (slice=S2, precondition={number}): §2.5 "
            f"Stack M precondition {number} — {rule}. No tenant-scoped object "
            f"exists for a request to be out of scope of, and nothing reads a "
            f"listing, so there is no subject. Why it matters: {why}. QA's "
            "gate journey in tests/e2e/test_gate_journey.py covers the gate "
            "itself; this is about the gate being part of the *standing* "
            "preconditions on every marketplace write."
        )
    pytest.fail(
        f"`apps.listings` exists, so §2.5 precondition {number} is now "
        "exercisable and this placeholder must become a real assertion: "
        f"{rule}"
    )


def test_the_unexercised_list_shrinks_rather_than_being_deleted():
    """When S2 lands, the test above **fails** rather than silently continuing
    to skip — that is the point of the `pytest.fail` branch. This asserts the
    branch exists, so nobody converts the placeholder into a permanent skip by
    deleting the condition.
    """
    import inspect

    source = inspect.getsource(test_a_stack_m_precondition_s1_cannot_exercise)
    assert "pytest.fail" in source, (
        "the placeholder no longer fails when its slice arrives, so it will "
        "skip forever"
    )
    assert set(UNEXERCISED_M_PRECONDITIONS) == {6, 7}, (
        "§2.5 has preconditions 1-8; 1-5 are exercised by "
        "test_standing_preconditions_matrix.py and 8 by the idempotency "
        "contract tests. If this set changed, say which test covers the "
        "difference."
    )


# --------------------------------------------------------------------------
# what a reader needs to know before reusing this pattern
# --------------------------------------------------------------------------


def test_every_ruled_path_is_an_l2_path():
    """**This pattern cannot serve an L3 route, and the limit is load-bearing.**

    `_route_exists` defines existence as "handled by an `apps.*` module", which
    is true of L2 and false of L3 by design: `web/**` is frontend-developer's
    tree and its views live in `web.views`. So a ruled row pointing at an L3
    path would be judged non-existent forever, skip forever, and assert
    nothing — the failure mode the inversion guard exists to close, reopened
    from the other end.

    §2.5's stacks are L1 preconditions and both layers call the same L1
    services, so checking them at L2 checks them for both. But that is an
    argument for *why one layer is enough*, not a licence to put an L3 path in
    the table. Asserted so a future row cannot.
    """
    offenders = [r["id"] for r in RULED if not r["path"].startswith("/api/v1/")]
    assert offenders == [], (
        f"these ruled rows are not L2 paths: {offenders}. `_route_exists` "
        "judges existence by the handler's module being under `apps.`, which "
        "no L3 route satisfies, so such a row would skip forever. Assert L3 "
        "placements through web/** instead, or via the L1 service both layers "
        "call."
    )


def test_the_module_attribution_the_pattern_rests_on_is_the_current_one():
    """**A caveat QA was handed, measured, and found to be already out of
    date — which is why it is a test and not a note.**

    Code review's warning was that `@endpoint` returns a closure, so every
    decorated handler reports its module as `apps.core.api` where the decorator
    is defined, and that anyone tightening `_route_exists` from *"handled by an
    `apps.*` module"* to *"handled by the app that owns it"* would break every
    row at once. That was true when review read it.

    Measured now: `/api/v1/account/export` reports **`apps.accounts.api`** — the
    app that owns it. The fix for the `inspect.getsource` defect was
    `functools.wraps`, which also copies `__module__` and sets `__wrapped__`,
    so correcting the source-reading problem silently corrected the attribution
    problem too. One change, two caveats retired.

    **The check is still not tightened, and for a different reason than the one
    that no longer applies.** What `_route_exists` needs to answer is "did this
    path reach a real L2 handler, or did it fall into `web/urls.py`'s catch-all
    `^.*$`?" — and `apps.*` answers exactly that. Tightening to the owning app
    would add a second thing that must be kept in step with every row for no
    extra discrimination, and the row already names its app.

    This test is the standing record of which of those two facts is current.
    """
    from django.urls import resolve

    module = resolve("/api/v1/account/export").func.__module__
    assert module == "apps.accounts.api", (
        "the handler no longer reports its owning app. If `functools.wraps` "
        "was removed from `@endpoint`, review's original caveat is live again "
        "and `inspect.getsource` on a handler is reading the decorator: "
        f"{module}"
    )
    assert module.startswith("apps."), (
        "whatever the attribution, `_route_exists` only needs it to be under "
        "`apps.`, which is what separates a real L2 handler from web/urls.py's "
        "catch-all 404"
    )
