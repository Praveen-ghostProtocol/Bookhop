"""RED TEAM PROBE · S2 re-report. **Not a regression test.**

Subject: **A-29's layer sentence, the fourth time.**

`API-CONTRACT.md` A-29 §3:

> *"With (1) and (2) in place the layer is real: no seller-written catalogue
> text reaches another student without a named human having looked at it."*

That sentence is what justified deleting `CATALOGUE_CHANNEL_KINDS` — every
text rule came off catalogue text on its authority. Across A-26, A-28 and
A-30 the clause that failed measurement was *every time* the one asserting
another layer made a narrowing safe (cto's own count, A-30), and
`CLAUDE.md` rule 12 was amended today to require that layer be measured in
the same pass.

So this file measures it, and it measures the half nobody has looked at.
Code Review and QA both attacked **what the gate serves**. `served_book_text`
withholds the four strings; `tests/unit/test_catalogue_text_gate_is_enforced.py`
walks `apps/**` and `web/**` for any read of those four *attribute names*.

**Neither asks what the database is permitted to do with the text.** The
gate is on the returned value. The sentence is about the text reaching a
student — and a value you may not read is still a value you may *match
against*.
"""

import pytest

pytestmark = pytest.mark.django_db

#: What a seller who wants to skip the app writes into a **global** `books`
#: row. Ten digits, which is what matters below: the extraction below is
#: linear in digits and needs no guess about the rest of the string.
POISONED = "Higher Engineering Mathematics call 9840012345 anytime"


def _unverified_book_titled(author, title):
    from apps.catalog.services import create_book

    book = create_book(
        author, isbn13="9789387432147", title=title,
        authors=["B S Grewal"], edition_label="43rd edition",
        publisher="Khanna", language="en",
    )
    assert book.staff_verified_at is None, "fixture no longer exercises the gate"
    return book


def test_the_gate_withholds_the_string_and_the_search_confirms_it(
    rt_client_as, student, rt_second_student
):
    """**FINDING, if red.**

    **Polarity, stated because this file's conventions must not be guessed:
    every assertion here asserts the SAFE outcome, so red is the finding** —
    the same convention as the S2 memo's probes. A green run here means the
    oracle is closed and the probes are retired.

    `GET /api/v1/books?q=` is a catalogue-identity read, so it passes no
    `reader` and `served_book_text` withholds: the second student is served
    `title: None`, `text_withheld: True`. That part works, and it is the half
    both earlier gates measured.

    **Then the row comes back anyway.** The needle matched seller-written text
    that the same response refuses to print. The gate controls the *value*,
    the query controls the *predicate*, and A-29 §3's sentence is about
    neither — it is about the text *reaching* a student, which a predicate
    does perfectly well.

    **Pass threshold: a needle that appears only in withheld seller-written
    text does not change the result set.**
    """
    _unverified_book_titled(student, POISONED)
    client = rt_client_as(rt_second_student)

    response = client.get("/api/v1/books", {"q": "call 9840012345"})
    assert response.status_code == 200, response.content[:400]
    rows = response.json()["items"]

    # The gate working, on the half that was measured.
    assert all(r["title"] is None and r["text_withheld"] for r in rows)
    assert rows == [], (
        "FINDING: the needle appears nowhere except in a withheld, unverified, "
        f"seller-written title, and it selected {len(rows)} row(s) — "
        f"isbn13={[r['isbn13'] for r in rows]}. No staff member has read this "
        "row and none is queued to"
    )


def test_a_second_student_extracts_the_whole_number_ten_digits_at_a_time(
    rt_client_as, student, rt_second_student, engine
):
    """**FINDING, if green. It is green.**

    No human has looked at this row. `review_listings` prints *"Nothing is
    waiting for review"* — A-29 §1 measured that itself, and nothing in the
    fix changed it, because the queue reviews listings and this seller never
    listed.

    The walk below is the ordinary adversary from `THREAT-MODEL.md` §5.6 with
    a shell loop: **ten requests per character, and each one is a lawful,
    signed-in, 200-response catalogue search.** It recovers the digits of a
    phone number out of a column the same endpoint refuses to print, with no
    staff member in the loop at any point.

    `normalise_title` is what makes it clean rather than fiddly: it strips
    punctuation and case, so the attacker does not have to guess separators —
    `title_norm` is a **copy of the seller's words in a column that is not in
    `SELLER_WRITTEN_TEXT`**, and therefore not sealed by the gate's own
    instrument either. The walk never names a sealed attribute, so the AST
    walk cannot see this path even in principle.

    **Pass threshold: a needle that appears only in withheld seller-written
    text must not change the result set.** Measured: it determines it.
    """
    _unverified_book_titled(student, POISONED)
    client = rt_client_as(rt_second_student)

    def matches(needle):
        response = client.get("/api/v1/books", {"q": needle})
        assert response.status_code == 200
        return bool(response.json()["items"])

    # The attacker knows the shape of the thing they are hunting, which is
    # the only knowledge this needs: Indian mobiles are ten digits.
    # **Not a precondition assert.** No foothold is the SAFE outcome, and on
    # PostgreSQL it is the measured one — a short needle cannot reach
    # `similarity() >= 0.3` against a long title. Asserting the foothold here
    # would make this probe red on the engine where the property holds, which
    # is a red that means the opposite of every other red in this tree
    # (`CLAUDE.md` rule 10). The engine is named in the message instead.
    recovered = ""
    for _ in range(10):
        found = next(
            (d for d in "0123456789" if matches(f"call {recovered}{d}")), None
        )
        if found is None:
            break
        recovered += found

    # SAFE OUTCOME ASSERTED, so red is the finding (see probe 1's polarity
    # note). Green means no digit was recoverable.
    assert recovered == "", (
        f"FINDING (engine={engine}): {len(recovered)} digit(s) of a phone "
        "number recovered as "
        f"{recovered!r} out of a column this same endpoint refuses to print, "
        "in ten signed-in 200-response searches per digit, with no staff "
        "member in the loop"
    )


def test_the_oracle_does_not_need_the_author_to_have_published_anything(
    rt_client_as, student, rt_second_student
):
    """**The reason A-29 §2 does not cover this.**

    §2 stops a listing on an unverified book reaching a buyer, and it is a
    real structural gate — `_transition` refuses. But the extraction above
    needs **no listing at all**, which is the same gap §1 recorded against
    A-28's named layer and then did not re-ask about its own.

    Asserted as a property rather than left as prose: zero listings exist.
    """
    from apps.listings.models import Listing

    _unverified_book_titled(student, POISONED)
    assert Listing.all_objects.count() == 0
    client = rt_client_as(rt_second_student)
    assert client.get("/api/v1/books", {"q": "9840012345"}).json()["items"] == [], (
        "FINDING: a bare digit run selects the row with no listing in "
        "existence, so A-29 §2's structural gate is not a layer over this path"
    )


def test_the_engine_decides_whether_the_gate_holds_and_nothing_records_that(
    rt_client_as, student, rt_second_student, engine
):
    """**The shape of the finding, and the reason it is not merely a bug.**

    Measured, both engines, same probe:

    | engine | `?q=call 9840012345` | digits recovered |
    |---|---|---|
    | SQLite | selects the row | **10 of 10** |
    | PostgreSQL 16 | selects nothing | 0 — no foothold |

    **VERIFIED HERE on both engines.** The difference is `search_books`:
    SQLite gets `title_norm__contains=needle`, PostgreSQL gets
    `similarity(title_norm, needle) >= 0.3`, and trigram similarity is a
    whole-string measure — a 15-character needle against a 53-character
    title cannot reach the threshold whatever it contains. So on the engine
    that ships, A-29 §3's sentence holds **by trigram arithmetic**, and
    nobody chose that.

    Three things follow, and they are why this is not "SQLite only":

    1. **`search_books`' own docstring states the contract:** *"the contract
       either engine satisfies is the weaker one — substring — so nothing
       above this function may assume fuzziness."* The weaker contract **is**
       the oracle. A-29 §3's sentence is false against the documented
       contract and true only against one engine's implementation of it.
    2. **`ENGINE-DIVERGENCE.md` records the functional half of this
       divergence** — *a misspelling finds nothing* — and not the half that
       decides whether gated text is readable. The document that exists to
       catch exactly this did not catch it, because the divergence was
       classified as a search-quality difference.
    3. **The obvious fixes to (1) reopen it.** Any substring or prefix
       fallback for short needles — the natural answer to "a misspelling
       finds nothing" and to a short query matching nothing — restores the
       oracle on PostgreSQL, and `search_books`' own `ponytail` note already
       schedules a change to this predicate in S3.

    This probe asserts the recorded state rather than the behaviour, so it
    stays meaningful on both engines: **it is red until some document says
    which engine the gate's safety depends on.**
    """
    import pathlib

    doc = (pathlib.Path(__file__).resolve().parents[2]
           / "company" / "architecture" / "ENGINE-DIVERGENCE.md").read_text(
        encoding="utf-8")
    assert "staff_verified_at" in doc or "A-29" in doc, (
        f"FINDING (engine={engine}): ENGINE-DIVERGENCE.md records that a "
        "misspelling behaves differently and does not record that the two "
        "engines disagree about whether gated seller-written text is "
        "recoverable through the search predicate. On SQLite ten digits came "
        "out; on PostgreSQL none did; no document names which of those the "
        "gate's safety rests on"
    )


def test_a_student_cannot_replace_the_bare_line_with_their_own_words(
    rt_client_as, student, rt_second_student
):
    """**FINDING, if green.** A-32's remedy is unreachable from the screen
    that motivated it.

    A-32 shipped two halves in one ruling:

      * *"a student's own words are served back to that student in place of a
        withheld row's text"* — the remedy for a bare `ISBN 978…` line;
      * *"idempotency for a request carrying a book FK keys on `book_id` and
        `course_code`, never on the typed label"* — so two spellings of one
        want are one want.

    Walk the journey the first half exists for. A student looks up an ISBN,
    finds the row, types no title (the form does not require one once the
    ISBN resolves), and is shown the bare line. They now do the one thing the
    screen invites: they go back and type the title.

    **The second half swallows it.** Same `book_id`, same `course_code`
    (`None`, because the field is optional), so `create_request` returns the
    existing row and the typed title is dropped on the floor — with a flash
    saying *"That is on your list below"*, which is true and useless. There
    is no `update_request`, so the state is terminal: that row's line stays
    bare for as long as the row exists.

    This is **F51's defect — "a student's own typed title is silently
    discarded" — re-created by the ruling that fixed it**, on the retry path
    rather than the first submission. Neither half is wrong alone; the seam
    between them is.

    **Pass threshold: after the second submission the student's own words are
    on the page.**
    """
    book = _unverified_book_titled(student, POISONED)
    client = rt_client_as(rt_second_student)

    first = client.post("/wanted", {"isbn": book.isbn13, "title": "", "course_code": ""})
    assert first.status_code in (302, 303), first.content[:400]
    page = client.get("/wanted").content.decode()
    assert f"ISBN {book.isbn13}" in page, (
        "the bare line is gone; this probe's premise is retired"
    )

    second = client.post(
        "/wanted",
        {"isbn": book.isbn13, "title": "Grewal maths 43rd ed", "course_code": ""},
    )
    assert second.status_code in (302, 303), second.content[:400]

    from apps.listings.models import BookRequest

    rows = list(BookRequest.all_objects.filter(book=book))
    assert len(rows) == 1, "idempotency no longer collapses the retry"

    page = client.get("/wanted").content.decode()
    assert "Grewal maths 43rd ed" in page, (
        "FINDING: the student typed a title to replace the bare line and the "
        f"row still carries free_text_title={rows[0].free_text_title!r}; the "
        "page still shows the ISBN and there is no path that can ever change it"
    )
