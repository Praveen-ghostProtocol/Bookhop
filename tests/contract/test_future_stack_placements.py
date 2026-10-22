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
        "body": {"stated_problem": "My display name is wrong."},
        #: **QA-S1 F24 is CLOSED in S2.** The row kept a `strict=True` xfail
        #: carrying the finding, and the strictness did its job: the day the
        #: endpoint was mounted the row **XPASSed** and the suite went red,
        #: which is the signal that the reminder is spent. The xfail is
        #: removed and the assertion is now live — with one change to the
        #: body, because the shipped signature is §3's
        #: `request_correction(actor, *, stated_problem)` and the
        #: `{field, value}` shape this row guessed four slices early was
        #: withdrawn by the contract itself ("the separate `subject` argument
        #: is withdrawn: redundant with free text").
        #:
        #: What it now asserts is what it always meant to: a **suspended**
        #: student can still exercise s12(1)–(2). That is also what makes
        #: §2.5's `display_name`-in-Stack-M reasoning quotable again.
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
    # **Amended by A-22, 2026-10-22, on this file's own escalation.** The text
    # below is §2.5's current wording, not the one QA tested against; the
    # ruling and what it does and does not permit are in the test's docstring.
    7: ("campus discovery gate open — on READS that can surface a row the "
        "actor did not create, and not on writes of the actor's own rows "
        "(ADR-002 §4) → else 403 GATE_CLOSED",
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


@pytest.fixture
def s2_actor(db, privacy_notice):
    """A **real** (non-seed) fully-qualified student. Factory by campus.

    Non-seed is the whole point: ADR-002 §4.1(c)'s subject is *"a real
    student on a closed campus"*, and every fixture in `tests/conftest.py` is
    `is_seed=True` because that is the only actor the slice could lawfully be
    built with. Preconditions 6 and 7 are the two that only a real student
    can exercise.
    """
    import itertools

    from apps.accounts.models import User
    from apps.accounts.services import grant_consent

    counter = itertools.count()

    def build(campus, **overrides):
        fields = dict(
            email=f"real{next(counter)}-{uuid.uuid4().hex[:6]}@example.test",
            display_name="A Real Student",
            campus=campus, city_id=campus.city_id, status="ACTIVE",
            adult_verified=True, campus_verified=True, is_seed=False,
        )
        fields.update(overrides)
        user = User.objects.create(**fields)
        for purpose in ("account", "listing_publication"):
            grant_consent(user, purpose, privacy_notice, "SIGNUP_FORM", None, "qa")
        user.refresh_from_db()
        return user

    return build


def test_precondition_6_a_cross_campus_object_is_404_and_never_403(
    sign_in, s2_actor, s2_listing, legal_entity, privacy_notice
):
    """§2.5 precondition 6 — **now exercisable, so now asserted.**

    > *object is in actor's visible campus scope (ADR-002 §2) → else `404`*

    The code is the assertion, not just the refusal: §2.2 requires *"the same
    body either way"* because **a 403 would confirm the object exists and leak
    the catalogue.** So a 403 here is as much a finding as a 200.

    Both tenant-scoped reads S2 exposes are driven, because a rule enforced on
    one route and forgotten on the sibling is this project's most-repeated
    defect.
    """
    from apps.core.models import Campus

    other = Campus.objects.create(
        city_id=s2_listing.city_id, name="Elsewhere", slug="elsewhere",
        legal_entity=legal_entity, email_domains=["elsewhere.ac.in"],
    )
    outsider = sign_in(s2_actor(other))

    for path in (
        f"/api/v1/listings/{s2_listing.id}",
        f"/api/v1/listings/{s2_listing.id}/photos/{'0' * 64}",
    ):
        response = outsider.get(path)
        assert response.status_code == 404, (
            f"§2.5 precondition 6 on {path}: a cross-campus object answered "
            f"{response.status_code} {_code(response)}. {UNEXERCISED_M_PRECONDITIONS[6][1]}"
        )
        assert response.status_code != 403, "403 confirms the object exists"


def test_precondition_7_the_gate_is_a_read_control(
    sign_in, s2_actor, signup_campus, book, seller_terms_notice
):
    """§2.5 precondition 7 — **the escalation this test raised is ruled, and
    the ruling went against what this test used to assert.**

    *7. campus discovery gate open — on READS that can surface a row the
    actor did not create, and not on writes of the actor's own rows
    (ADR-002 §4) → else `403 GATE_CLOSED`*

    QA measured `201` where §2.5's old wording required `403 GATE_CLOSED`,
    declined to pick a side, and escalated. **A-22 settled it from the
    compliance rationale rather than from either document's precedent**: the
    r.3(1)(b) trigger is the *browsable surface*, so a private intake nobody
    can browse is a record and not a platform, and **blocking the write
    protects nothing the law asks us to protect.** The ruling added a reason
    QA did not have and should have had: blocking writes until discovery
    opens means a campus launches with **zero listings and the first search
    fails** — R-01, the register's top risk, materialising by design.

    So `201` is correct and this is now the regression. It is written as the
    ruling's **two halves**, because a ruling recorded on only the permitted
    side is the shape `CLAUDE.md` rule 10's corollary names — *"where a rule
    splits a set, both sides are rows, and a test enforces that."*

    **A-22, verbatim, on what each half contains:** *"Permitted pre-gate:
    create a listing, upload its photos, record a want, read your own rows.
    Still gated: all discovery, and `→ OFFERED`."*
    """
    import io
    import json
    import struct

    assert signup_campus.discovery_enabled_at is None, (
        "this test is about a CLOSED campus; with the gate open it measures "
        "nothing"
    )
    actor = s2_actor(signup_campus)
    from apps.accounts.models import NoticeVersion
    from apps.accounts.services import accept_seller_terms

    terms = NoticeVersion.objects.filter(kind="SELLER_TERMS").order_by("-id").first()
    if terms:
        accept_seller_terms(actor, terms, None)
    client = sign_in(actor)

    def post(path, body):
        return client.post(
            path, data=json.dumps(body), content_type="application/json",
            headers={"Idempotency-Key": str(uuid.uuid4())},
        )

    # --- A-22's permitted half ------------------------------------------
    created = post("/api/v1/listings", {
        "accept_seller_terms": True, "book_id": book.id,
        "asking_price_paise": 30000, "condition": "GOOD",
        "annotation_level": "NONE", "damage_flags": [], "no_damage": True,
        "language": "en", "category": "PRESCRIBED_TEXTBOOK",
    })
    assert created.status_code == 201, (
        "A-22: *create a listing* is permitted pre-gate, because the "
        "alternative is a campus that opens with zero supply and a first "
        f"search that fails. Got {created.status_code} {_code(created)}: "
        f"{created.content[:200]}"
    )
    listing = created.json()

    wanted = post("/api/v1/requests", {"free_text_title": "A book nobody has listed"})
    assert wanted.status_code == 201, (
        "A-22: *record a want* is permitted pre-gate, and it is the demand "
        f"signal R-01 is measured with. Got {wanted.status_code} {_code(wanted)}"
    )

    jpeg = (
        bytes((0xFF, 0xD8))
        + bytes((0xFF, 0xC0)) + struct.pack(">H", 11) + bytes((8,))
        + struct.pack(">HH", 3, 4) + bytes((1,)) + bytes((1, 0x11, 0))
        + bytes((0xFF, 0xDA)) + struct.pack(">H", 8) + bytes((1, 1, 0, 0, 0x3F, 0))
        + bytes((0, 0)) + bytes((0xFF, 0xD9))
    )
    photo_file = io.BytesIO(jpeg)
    photo_file.name = "p.jpg"
    photo = client.post(
        f"/api/v1/listings/{listing['id']}/photos",
        data={"photo": photo_file},
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert photo.status_code == 201, (
        "A-22: *upload its photos* is permitted pre-gate. Got "
        f"{photo.status_code} {_code(photo)}: {photo.content[:200]}"
    )

    own = client.get(f"/api/v1/listings/{listing['id']}")
    assert own.status_code == 200, (
        f"A-22: *read your own rows* is permitted pre-gate. Got {own.status_code}"
    )
    mine = client.get("/api/v1/listings/mine")
    assert mine.status_code == 200
    assert [row["id"] for row in mine.json()["items"]] == [listing["id"]]

    # --- A-22's still-gated half ----------------------------------------
    # The read side is S3 (`apps.discovery`), so the only gated read that
    # exists today is the photo route on somebody ELSE's listing. That is the
    # right subject anyway: it is the exact route whose gate QA broke in F34.
    stranger = s2_actor(
        signup_campus, email=f"stranger-{uuid.uuid4().hex[:6]}@example.test"
    )
    from apps.listings.models import ListingPhoto

    row = ListingPhoto.all_objects.get(listing_id=listing["id"])
    refused = sign_in(stranger).get(
        f"/api/v1/listings/{listing['id']}/photos/{row.sha256}"
    )
    assert refused.status_code == 404, (
        "A-22 keeps *all discovery* gated, and a photo is as gated as the "
        "listing it belongs to (§5.2). A second real student on the same "
        "closed campus must not reach another student's row — 404 rather "
        f"than 403, per §2.2. Got {refused.status_code} {_code(refused)}"
    )


def test_the_create_flow_surfaces_no_other_students_row_not_even_a_count(
    client_as, s2_actor, signup_campus, book, seller, s2_listing
):
    """**A-22's narrowest clause, and the one most likely to be lost.**

    > *"the create flow may surface no other user's row **including a
    > count**"*

    The ruling permits a pre-gate write precisely because nothing browsable
    is produced. A count is not a row and it **is** a disclosure: *"3 other
    students are selling this book"* on the sell page tells a student the
    campus has supply, which is the browsable surface r.3(1)(b) is about, in
    aggregate form. It is also exactly the kind of thing a helpful
    social-proof change adds two slices later without anyone reading A-22.

    Asserted over the **served HTML** of the three pre-gate pages, with
    `s2_listing` — another student's LIVE listing — in the database, so there
    is something for a count to count.
    """
    import re

    assert signup_campus.discovery_enabled_at is None
    other = s2_actor(
        signup_campus, email=f"counter-{uuid.uuid4().hex[:6]}@example.test"
    )
    client = client_as(other)

    assert s2_listing.seller_pseudonym != other.person_pseudonym, (
        "the fixture listing must belong to somebody else, or this measures "
        "the actor's own row"
    )

    for path in ("/sell", f"/sell/find-book?isbn={book.isbn13}", "/wanted"):
        response = client.get(path)
        assert response.status_code == 200, (path, response.status_code)
        html = response.content.decode()

        assert str(s2_listing.id) not in re.findall(r"/listing/(\d+)", html), (
            f"{path} links to another student's listing before the gate opens"
        )
        for phrase in ("other student", "others are", "already selling",
                       "copies available", "on your campus are"):
            assert phrase not in html.lower(), (
                "A-22: *'the create flow may surface no other user's row "
                f"including a count'*. {path} contains {phrase!r}, which "
                "discloses supply on a campus whose gate is closed."
            )


def test_the_unexercised_list_is_now_empty_or_still_named():
    """The guard that stopped the placeholders skipping forever has done its
    job, so this is what replaces it: both preconditions have a real test
    above, and the set is asserted so a third one cannot be added as a
    comment.
    """
    assert set(UNEXERCISED_M_PRECONDITIONS) == {6, 7}, (
        "§2.5 has preconditions 1-8; 1-5 are exercised by "
        "test_standing_preconditions_matrix.py and 8 by the idempotency "
        "contract tests. If this set changed, say which test covers the "
        "difference."
    )
    for number, test in (
        (6, test_precondition_6_a_cross_campus_object_is_404_and_never_403),
        (7, test_precondition_7_the_gate_is_a_read_control),
    ):
        assert callable(test), number
        def flatten(text):
            return " ".join(text.replace("`", "").replace("*", "").split())

        doc = flatten(test.__doc__ or "")
        rule = flatten(UNEXERCISED_M_PRECONDITIONS[number][0])
        assert rule in doc, (
            f"precondition {number}'s test no longer quotes the contract rule "
            f"it is about, so the two can drift. Expected: {rule!r}"
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


# --------------------------------------------------------------------------
# A-29 §1 on S3's buyer-facing listing read — the clause nobody owns yet
# --------------------------------------------------------------------------
#
# Every other A-29 §1 control in the repository is retrospective: it holds
# because somebody found a missed read path and closed it. There are now five
# — `/sell`, `/sell/find-book`, `/sell/{id}/photos`, `/listing/{id}`,
# `/wanted` — and four of them were found by a human reading code rather than
# by anything failing.
#
# **The sixth has not been written yet.** `apps.discovery` is S3's, it is the
# first read where the reader is a *buyer* rather than the row's own actor,
# and nothing in the tree obliges whoever writes it to ask the gate. Backend
# flagged it; `web/views.listing_detail`'s docstring promises S3 *"swaps one
# line"* to `discovery.get_listing`, and
# `tests/unit/test_catalogue_text_gate_is_enforced.py::test_listing_detail_is_still_an_own_rows_read`
# reddens on that swap — which tells the author that the *reader* changed and
# says nothing about whether the new module asks the gate at all.
#
# This is `CLAUDE.md` rule 10's fifth disguise, so it is written inverted, in
# this file because this file is where that shape already lives: while the app
# does not exist the assertion skips with its reason, and **the moment the app
# is installed a read that does not resolve through the gate is a failure.**
# The failure branch is exercised below on synthetic sources, because a
# forward-dated guard whose red path has never run is indistinguishable from
# one that cannot go red.

#: The spellings that mean "the gate was asked". **Not a list of allowed call
#: sites** — these three are the gate, the single wrapper every payload uses,
#: and the view-layer mapper, and rule 11's point is that there is one
#: definition with many readers. A module serving listing text without any of
#: these three in it has either forgotten the gate or has its own copy of the
#: condition, and both are the defect.
GATE_CALLS = ("served_book_text", "book_block", "_book_of")

#: A-29 §1's unowned clause, in the same shape as `RULED` above.
A29_DISCOVERY = {
    "app": "apps.discovery",
    "slice": "S3",
    "read": "the buyer-facing listing read that `/listing/{id}` swaps to",
    "why": (
        "A-29 §1: *'A book row with `staff_verified_at IS NULL` has its "
        "seller-written free text served only to the actor who created it. "
        "Every other reader is served the ISBN and a neutral, BookHop-voiced "
        "label.'* A-29 §2 keeps such a listing away from a buyer today, so "
        "this read is the first place where §1 is the **only** layer — "
        "A-31(b) is explicit that the viewer-form is correct without §2 and "
        "the owner-form is correct only because of it"
    ),
}


def _asks_the_gate(sources):
    """Do these module sources ask A-29 §1's gate anywhere? `(bool, which)`.

    A pure function of text so that **both** branches can be exercised now,
    while the app it is about does not exist. A predicate only ever run on
    the green side is rule 10's first disguise with a slice-long fuse.
    """
    hits = sorted({call for text in sources for call in GATE_CALLS if call in text})
    return bool(hits), hits


def test_the_discovery_listing_read_asks_a29s_gate_the_day_the_app_exists():
    """Inverted, so it cannot skip forever.

    While `apps.discovery` is absent this skips **naming the app and the
    slice**, which is the only legitimate reason to skip. Once it is
    installed, three things become failures rather than absences: the app has
    no Python at all, the app serves listing data without one of
    `GATE_CALLS`, or the gate module it would import has been renamed out
    from under it.

    It deliberately does **not** assert which function reads the listing or
    what the payload is called. S3 has not been designed, and a guard that
    predicts the shape would be the thing that gets edited (rule 13). What it
    asserts is the property A-29 §1 fixes regardless of shape: the decision
    is asked, in that app, through the one place that makes it.
    """
    if not _app_installed(A29_DISCOVERY["app"]):
        pytest.skip(
            f"{A29_DISCOVERY['app']} does not exist yet ({A29_DISCOVERY['slice']}) — "
            "engine-independent. A-29 1's clause on "
            f"{A29_DISCOVERY['read']} is unowned until it does, and this "
            "assertion inverts the day it lands."
        )

    import pathlib

    root = pathlib.Path(__file__).resolve().parents[2] / A29_DISCOVERY["app"].replace(
        ".", "/"
    )
    files = sorted(root.rglob("*.py"))
    assert files, (
        f"{A29_DISCOVERY['app']} is in INSTALLED_APPS but has no Python "
        "modules, so this guard would pass on an empty package"
    )

    asked, which = _asks_the_gate([p.read_text(encoding="utf-8") for p in files])
    assert asked, (
        f"{A29_DISCOVERY['app']} is installed and nothing in it calls any of "
        f"{GATE_CALLS}, so {A29_DISCOVERY['read']} is serving seller-written "
        "catalogue text without asking A-29 §1's gate — or asking it with a "
        "copy of the condition, which rule 11 makes the same defect.\n\n"
        f"{A29_DISCOVERY['why']}\n\n"
        "The reader to pass is the **buyer**, not the listing's seller: "
        "A-31(b) ruled the viewer-form is the tighter of the two and the "
        "owner-form is safe only while A-29 §2 holds. Route the read through "
        "`apps.catalog.services.served_book_text` (or `book_block`, which "
        "calls it) and thread the viewer down to it."
    )

    from apps.catalog import services as catalog

    assert hasattr(catalog, "served_book_text"), (
        "the gate has been renamed, so the spelling this guard matches on no "
        "longer identifies it. Update `GATE_CALLS` in the same commit."
    )


def test_the_failure_branch_of_the_discovery_guard_still_exists():
    """The guard for the forward-dated guard (rule 10's corollary).

    The test above cannot have run its red path — the app it is about does
    not exist — so from outside, *"skipping until S3"* and *"a predicate that
    cannot return False"* look identical. This runs both sides on synthetic
    sources now, so the day `apps/discovery` lands the inversion is known to
    work rather than hoped to.

    Both sides are rows (rule 10's corollary): a module that asks the gate
    passes, a module that serves the same text without asking fails, and the
    near-miss — a module that keeps its **own copy** of the
    `staff_verified_at` condition instead of asking — fails too, which is the
    case rule 11 is about and the one a reviewer is most likely to wave
    through.
    """
    serves_without_asking = (
        "def get_listing(viewer, listing_id):\n"
        "    row = Listing.objects.get(id=listing_id)\n"
        '    return {"title": row.book.title}\n'
    )
    own_copy_of_the_condition = (
        "def get_listing(viewer, listing_id):\n"
        "    row = Listing.objects.get(id=listing_id)\n"
        "    if row.book.staff_verified_at is None:\n"
        '        return {"title": None}\n'
        '    return {"title": row.book.title}\n'
    )
    asks_the_gate = (
        "from apps.listings.services import book_block\n"
        "def get_listing(viewer, listing_id):\n"
        "    row = Listing.objects.get(id=listing_id)\n"
        '    return {"book": book_block(row.book, viewer)}\n'
    )

    assert _asks_the_gate([serves_without_asking]) == (False, []), (
        "the predicate reports the gate asked by a module that reads "
        "`row.book.title` raw, so the guard above cannot go red"
    )
    assert _asks_the_gate([own_copy_of_the_condition]) == (False, []), (
        "a module with its own copy of the `staff_verified_at` condition is "
        "reported as asking the gate. That is the rule 11 defect — three "
        "hand-made copies of one legal rule disagreed once already — and it "
        "must fail here, not pass"
    )
    asked, which = _asks_the_gate([asks_the_gate])
    assert (asked, which) == (True, ["book_block"]), (
        "the predicate does not recognise a module that does ask the gate, "
        "so the guard above would be red on correct code and would be edited "
        f"rather than obeyed (rule 13): {which}"
    )


def test_the_discovery_app_is_still_absent_so_the_skip_is_honest():
    """The skip's own precondition, asserted rather than trusted.

    A skip is legitimate only while the app genuinely does not exist. A
    half-landed `apps/discovery` — a package on disk, not yet in
    `INSTALLED_APPS` — would make the guard above skip while the code it is
    about was being written, which is the worst moment for it to be silent.
    So absence is checked **two** ways, and this test inverts into a one-line
    deletion the day S3 starts.
    """
    import pathlib

    installed = _app_installed(A29_DISCOVERY["app"])
    on_disk = (
        pathlib.Path(__file__).resolve().parents[2] / "apps" / "discovery"
    ).is_dir()
    assert installed == on_disk, (
        f"`apps/discovery` exists on disk ({on_disk}) but installed is "
        f"{installed}. While those disagree the guard above skips on an app "
        "that is being written right now. Add it to `INSTALLED_APPS` in the "
        "same commit as the package, or delete the package."
    )
