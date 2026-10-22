# COPY-DECK.md — BookHop v1, English and Tamil

**Owner:** `design-director` · **Version:** v1.0 · **Date:** 2026-10-21
**Handoff:** `product-manager` (voice sign-off), `frontend-developer`
(`.po` files), `test-qa` (forbidden-string test), **and a native Tamil
speaker (blocking — see §2)**

> ## TAMIL STATUS — READ THIS BEFORE USING ANY STRING BELOW
>
> **Every Tamil string in this document is a DRAFT by an agent that cannot
> verify its own Tamil fluency. None of it is approved. None of it may ship
> as written.** It is here so a native speaker has something concrete to
> correct rather than a blank column, which is faster and cheaper than
> starting from English alone.
>
> Three classes of string are **BLOCKING** — they must not ship in Tamil in
> any form until a named native speaker has signed them off, because a
> mistranslation has a legal or physical consequence, not merely an awkward
> one:
>
> - **B1 — the handover guidance (§7).** A mistranslation here is a safety
>   and liability problem. If the Tamil accidentally warrants anything, we
>   have warranted it.
> - **B2 — every no-warranty string (§3).** The English is engineered word by
>   word to describe a mechanism and never to promise. Tamil has to carry the
>   same restraint, and a natural-sounding Tamil rendering is very likely to
>   over-promise.
> - **B3 — the legal and rights flows (§9, §10.3, §10.4):** reporting,
>   grievance, age gate, consent, erase. These carry statutory meaning
>   (DPDP, IT Rules, E-Com rules) and the wording is a compliance artefact.
> - **B4 — the negotiability strings (§3.1), new in v1.1.** These carry a
>   limb of the s194-O position (`COMPLIANCE.md` §4.3.1). A Tamil rendering
>   that reads as "the price is ₹280" rather than "₹280 is what the seller is
>   asking for" would weaken a tax position in a language the forbidden-string
>   test cannot read. **Of the four blocking classes this is the one where a
>   wrong translation is least visible to us and most expensive.**
>
> Everything else is **TR** (translation review): correct it, don't block on
> it. Open TR items are listed in §11.
>
> **Policy, recorded so nobody ships around it:** until §2's sign-off exists,
> the Tamil locale is **not offered to students**. English-only is honest.
> A half-translated bilingual product that drops into English at the handover
> screen is worse than one language done properly.

---

## 1. The rules this copy follows

### 1.1 The banned words, and the wider set the codebase already enforces

Two separate bans, from two separate legal sources. Both are enforced by
`tests/unit/test_forbidden_copy.py`, which greps every template and `.po`
file.

**Ban 1 — the vouching ban.** Banned in all copy, both languages:
**safe · verified · guaranteed**, and — because `API-CONTRACT.md` §5.4 and
`COMPLIANCE.md` §5.5 already enforce them — **protected · assured**. Source:
we hold no funds and cannot refund, so the more we vouch the more we own.

**Ban 2 — the fixed-price ban (new in v1.1).** Banned phrases:
**"pay the listed price" · "fixed price" · "non-negotiable" · "final price"**,
and the **bare label "Price"**. Source: `COMPLIANCE.md` §4.3.1, trap (1).
This one is a tax limb, not a liability limb, and §1.6 below explains it
because a copywriter who does not understand *why* will reintroduce the
phrase in a synonym.

**Neither ban can catch Tamil today**, and that gap now carries legal weight
in two directions rather than one. §11 proposes the Tamil strings both bans
need; a native speaker must confirm the list before it is added, because an
over-broad ban would make ordinary Tamil unusable (e.g. `பாதுகாப்பு` is a
normal word in "data protection" contexts we are legally required to use in
the privacy notice, and `விலை` — "price" — obviously cannot be banned
outright). See **TR-8** and **TR-11**.

### 1.2 The grammatical rule — the actual mechanism

> **BookHop's voice may describe a mechanism, name a fact, or give an
> instruction. It may never make a prediction or a judgement about a person, a
> book, or an outcome.**

A grep catches words. This catches sentences. The review checklist:

| Test | Fails | Passes |
|---|---|---|
| Does it predict? | "You'll be fine." "This will go smoothly." | "Check the book before you pay." |
| Does it judge a person? | "Trusted seller." "Reliable buyer." | "Signed in with a college email address." |
| Does it judge a book? | "Good condition." (as our words) | "Condition, in the seller's words: 'Good — cover is bent…'" |
| Does it imply we checked? | "Reviewed listing." | "BookHop hasn't checked this book." |
| Does it imply recourse we don't have? | "Money-back if it's wrong." | "If it isn't the book described, don't pay. Tell us and we'll take the listing down." |
| Is the subject of the sentence a person who isn't us? | "Priya is a careful seller." | "Priya wrote this 3 days ago." |

**Why this produces confidence rather than coldness** — the full argument is
`DIRECTIONS.md` §4.2. Short version: this category has trained students that
platform claims are noise (BookMandee's "10000+ verified users" beside
counters reading 0; CampusXchange's "Trusted by 5,000+" beside ₹0 —
`COMPETITORS.md` §3.11, §4.5). Against that background, a listing that
volunteers its own defects and tells you exactly what to check is more
believable than one that boasts. We are not giving up a trust signal; we are
choosing the one that still works.

### 1.3 Tamil is written first, then English

Every string in §3–§10 was *laid out* to the length Tamil needs. The practical
rules:

1. **No fixed-width or fixed-height control.** Two-line Tamil buttons are
   normal (`SYSTEM.md` §4.2).
2. **Short Tamil beats literal Tamil.** Where a faithful Tamil rendering runs
   40% longer than the English, **change the English** so both are short. The
   English is ours to edit; the Tamil is a constraint.
3. **No ALL-CAPS, no letter-spacing, no truncation with an ellipsis on any
   control** (`tokens.css`, `DIRECTIONS.md` §2.3).
4. **No idioms, in either language.** §1.5.
5. **One sentence per line, one idea per sentence.** Tamil's agglutination
   makes a long English sentence into a very long Tamil word-chain.

### 1.4 Numerals, dates, currency

Western Arabic digits (0–9) in both locales. Rupees as `₹280`, with the symbol
outside the input (`SYSTEM.md` §4.4). Times are absolute and include the day:
`4:30 PM, செவ்வாய் 21 அக்டோபர்`. **Tamil digits (௧௨௩) are not proposed** —
my understanding is that everyday Chennai usage is Western digits, including
for prices and ISBNs, but this is an assumption and it is review item
**TR-6**.

### 1.5 "Worth your while" — the copy decision, not a translation

Product flagged the phrase as untranslatable. **Decision: it is deleted, not
translated, and a general rule replaces it.**

The phrase was doing persuasion work in the seller's empty state — roughly
*"selling your old books is worth your while"*. The problems with translating
it are two, and only the first is about Tamil:

1. There is no Tamil equivalent that is both idiomatic and short. Every
   candidate either becomes a clause ("உங்கள் நேரத்திற்கு ஏற்ற பலன்
   உண்டு" — unwieldy, and it still has problem 2) or lands as a vague
   assurance.
2. **It is a prediction, so it fails §1.2 regardless of language.** "Worth
   your while" claims the student will get a benefit. We do not know that. At
   one campus on day one, with no liquidity, it is very likely false. It also
   edges toward the kind of inducement E-Com rules take an interest in.

So the English is rewritten to be factual and the Tamil follows easily:

| Key | English | Tamil (draft) |
|---|---|---|
| `sell.empty.title` | You haven't listed a book yet. | நீங்கள் இன்னும் எந்தப் புத்தகத்தையும் பட்டியலிடவில்லை. |
| `sell.empty.body` | It takes about two minutes: the ISBN from the back of the book, what's wrong with it, and your price. | இதற்கு சுமார் இரண்டு நிமிடம்: புத்தகத்தின் பின்பக்கம் உள்ள ISBN, அதில் என்ன பிரச்சினை, உங்கள் விலை. |
| `sell.empty.cta` | List a book | ஒரு புத்தகத்தைப் பட்டியலிடு |

**The standing rule this creates, for every agent writing copy from now on:**

> No English string ships that cannot be said plainly in Tamil at roughly the
> same length. An idiom is rewritten in English, never translated. If the
> English needs an idiom to be persuasive, the claim underneath it is probably
> one we are not allowed to make.

### 1.5a "College" or "campus" — the wording latitude, exercised

`COMPLIANCE.md` §2.5a leaves the choice between "college email address" and
"campus email address" to me. **Decision: "college" for the institution and
the account; "campus" for the place.**

- **College** = the institution you are enrolled at. Used for the email
  address, the sign-in, the account: `auth.email.label` ("Your college email
  address"), `run.cta` ("Sign in with your college email"),
  `trust.campus_mail` ("Signed in with a college email address").
- **Campus** = the physical place you walk around and meet people in. Used for
  location and for the handover: `run.h1` ("Textbooks from your own campus"),
  `search.count` ("{n} copies on your campus"), `hand.guidance.3`
  ("Don't go anywhere off campus").

This was already the deck's implicit usage; it is now a rule, because the two
words are not interchangeable in the one product where "the place I meet a
stranger" and "the institution that issued my email" are separate facts doing
separate jobs. The token key stays `trust.campus_mail` for continuity with
`COMPLIANCE.md` §2.5a even though its text now says "college" — renaming a
key that a ruling cites by name would cost more than it buys.

**Adopted beyond this deck (v1.3).** `ceo-planning` has taken this up as a
**project rule rather than a copy rule**, so the distinction is expected to
survive into the schema and the staff-console wording as well as the student
UI. Two consequences for anyone reading this section as the source: the rule
is **not mine to relax** any more, and where a schema or admin label has to
choose, the test is the same one — *does this name the institution that issued
an email, or the place two people walk to?* `campuses` as a table name is the
place; a verification method keyed off an email domain is the institution.

### 1.6 The negotiability requirement — new in v1.1, and it is a tax limb

**Added on instruction from `COMPLIANCE.md` §4.3.1. This is not a preference
and it is not a tone question. It is one of the six limbs of the position
that keeps BookHop outside a withholding obligation, and it is the only limb
the schema cannot carry.**

The short version of why, so nobody reintroduces a banned phrase in a
synonym:

- CBDT Circular 20/2021 holds that TDS does not attach to a platform that
  does **price discovery only**, where the discovered price is
  *"not necessarily the price at which the transaction takes place"* and both
  the transaction and the payment happen outside the portal. BookHop
  satisfies five of its six limbs by design (`COMPLIANCE.md` §4.3.1).
- The weak limb is the second one, and the reason it is weak is *our own
  schema*: because P14 makes the asking price **immutable**, the asking price
  becomes a *better* proxy for what was actually paid, not a worse one. If the
  product then presents that number as the price, then "the asking price of a
  book that demonstrably changed hands" becomes a good estimate of the
  consideration — and the whole position weakens.
- Compliance's conclusion, quoted because it is addressed to me: *"The
  product must make it visibly true that price is negotiated between the
  parties and that BookHop does not know the outcome… The schema cannot carry
  this limb. Only the copy can."*
- And it is already asserted to counsel as a **fact**: Q9's statement of
  facts says *"Price is negotiable and the product says so; the asking price
  is labelled as the seller's asking price throughout."* **If the copy does
  not do this, counsel is being asked to opine on a product that does not
  exist.** That is the sharpest reason to get it right.

**Four rules, which the rest of this deck now obeys.**

1. **The number is never labelled "Price".** It is **"Seller's asking
   price"** on first appearance in any component, and **"Asking price"**
   thereafter within the same component where space demands. The bare word
   "Price" does not appear as a label anywhere in the product — including
   filter labels, sort labels, table headers, form labels, and notification
   text.
2. **Every place the number appears for the first time in a flow carries the
   negotiability fact in plain words**, at least once per flow: the two
   students agree the price between themselves, and BookHop does not know
   what was paid.
3. **The handover copy says it explicitly**, at the moment it is true:
   "Agree the price between yourselves when you meet."
4. **There is no numeric offer, counter-offer, bid or "name your price"
   control anywhere in the UI.** Negotiation happens in the message thread,
   in the students' own words. This is rule 4 of the copy deck *and* a
   standing design constraint — see §6.3's note, which is addressed to
   `product-manager` and `cto` as much as to the frontend.

**Why this sits comfortably inside §1.2's governing rule.** "The two of you
agree the price" is an **instruction**. "BookHop does not record what you
paid" is a **fact about our database**. Neither is a prediction and neither
is a judgement. The negotiability copy is the easiest copy in the deck to
write honestly, because it is simply true.

---

## 2. Review sign-off block — fill this in, do not delete it

| Class | Scope | Reviewer (name) | Date | Verdict |
|---|---|---|---|---|
| **B1** | §7 handover guidance | — | — | **NOT REVIEWED** |
| **B2** | §3 no-warranty strings | — | — | **NOT REVIEWED** |
| **B3** | §9, §10.3, §10.4 legal and rights flows | — | — | **NOT REVIEWED** |
| **B4** | §3.1 negotiability strings | — | — | **NOT REVIEWED** |
| TR | everything else | — | — | **NOT REVIEWED** |

Reviewer brief (give them this, not the whole document): *"These are draft
Tamil strings for a student book-exchange app in Chennai. Two things matter
more than elegance. First: the Tamil must not promise anything — not that a
book is as described, not that a meeting will be fine, not that we checked
anything. If a Tamil sentence sounds reassuring, flag it. Second: it must
sound like a classmate wrote it, not like a bank. Tell us where the register
is wrong. Third, and this one is narrow: wherever a rupee amount appears, the
Tamil must say it is **what the seller is asking for** and must never read as
**the price of the book**. The difference matters to us legally. Length
matters: shorter is better than faithful."*

---

## 3. The trust strings — B2, BLOCKING

The hardest strings in the product. Each one replaces an instinct that would
have been a warranty.

| Key | English | Tamil (draft) | Replaces the instinct | Why it is not a warranty |
|---|---|---|---|---|
| `trust.not_checked` **(rescoped v1.2)** | BookHop hasn't checked this book. | இந்தப் புத்தகத்தை BookHop சரிபார்க்கவில்லை. | "Verified listing" | A statement about what we did *not* do. Cannot be a warranty. **Was "Nothing here is checked by BookHop" — scoped to the book in v1.2 to resolve the adjacency problem in §3.2** |
| `trust.check_yourself` | Look at the book before you hand over any money. | பணம் கொடுப்பதற்கு முன் புத்தகத்தைப் பார்த்துக் கொள்ளுங்கள். | "Safe payment" | An instruction to the student |
| `trust.campus_mail` **✅ RULED: SHIP (English)** | Signed in with a college email address. | கல்லூரி மின்னஞ்சல் முகவரியால் உள்நுழைந்தவர். | "Verified student" | **`COMPLIANCE.md` §2.5a, v1.2.** Approved content: the mechanism named, no domain, no judgement. **No `{domain}` placeholder — see §3.2 condition 1.** Renders only when `campus_verifications.method = 'INSTITUTIONAL_EMAIL'` (condition 3). Tamil still blocked on B2 like every trust string |
| `trust.account_only` **(new v1.2)** | That's all BookHop knows about them. We haven't checked who they are. | BookHop அவரைப் பற்றி அறிந்திருப்பது இதுமட்டுமே. அவர் யார் என்பதை நாங்கள் சரிபார்க்கவில்லை. | letting a sign-in fact imply we vetted a person | A statement about the limit of our own knowledge. **This is the string that resolves the adjacency problem (§3.2) and it makes the pair stronger than either sentence alone** |
| `trust.isbn_match` | This ISBN matches the catalogue entry for this edition. | இந்த ISBN இந்தப் பதிப்பின் பட்டியல் பதிவுடன் பொருந்துகிறது. | "Verified edition" | A string comparison, described |
| `trust.seller_words.label` | Condition, in the seller's words | நிலை — விற்பவர் எழுதியது | "Condition: Good" | The grade stays inside the seller's quotation (`SYSTEM.md` §4.14) |
| `trust.seller_words.empty` | The seller did not describe the condition. | விற்பவர் புத்தகத்தின் நிலையைப் பற்றி எதுவும் எழுதவில்லை. | hiding the gap | A fact a buyer should weigh |
| `trust.attribution` | — {name}, {n} days ago | — {name}, {n} நாட்களுக்கு முன் | an anonymous "Good" | Names who claimed it and when |
| `trust.changed_after_offer` | Changed after you offered. [See what it said before] | நீங்கள் கேட்ட பிறகு மாற்றப்பட்டது. [முன்பு என்ன இருந்தது] | silence | The most decision-relevant event on a listing |
| `trust.no_ratings` | There are no ratings on BookHop. | BookHop-ல் மதிப்பெண்கள் இல்லை. | a 4.8★ display | True; and `ADR-001` §6 |
| `trust.recourse` | If it isn't the book described, don't pay. Tell us and we'll take the listing down. | விவரித்தபடி புத்தகம் இல்லையென்றால், பணம் கொடுக்க வேண்டாம். எங்களுக்குச் சொல்லுங்கள், அந்தப் பட்டியலை நீக்குவோம். | "Money-back" | Describes **our own action**, which we control, and nothing about the outcome |
| `trust.stale_listing` | Listed {n} days ago — this may be gone. | {n} நாட்களுக்கு முன் பட்டியலிடப்பட்டது — இது இல்லாமல் போயிருக்கலாம். | a fresh-looking old listing | A statement about elapsed time |
| `trust.exif` | We remove the location and camera details from your photos. | உங்கள் படங்களிலிருந்து இடம் மற்றும் கேமரா விவரங்களை நீக்குகிறோம். | "Your photos are safe" | Describes a processing step (`ADR-001` §2.6) |

**TR-1 (important):** the Tamil word `சரிபார்` ("check / verify") appears in
`trust.not_checked` and `trust.check_yourself`. In English the distinction
between *we verified* (banned) and *you check* (required) is carried by the
subject. **The reviewer must confirm Tamil keeps that distinction clearly**,
and must tell us whether `சரிபார்` is safe to use at all in our voice or
whether a different verb is needed for the student's action.

### 3.1 The negotiability strings — B4, BLOCKING

New in v1.1 per `COMPLIANCE.md` §4.3.1 and §1.6 above. Every string here
carries a tax limb. They are grouped with the trust strings rather than with
the listing copy because, like the trust strings, each one exists to prevent a
specific sentence we are not allowed to say.

| Key | English | Tamil (draft) | Replaces the instinct | Why it holds the limb |
|---|---|---|---|---|
| `price.label.full` | Seller's asking price | விற்பவர் கேட்கும் விலை | "Price" | Names whose number it is. **First appearance in every component** |
| `price.label.short` | Asking price | கேட்கும் விலை | "Price" | Second and later appearances within the same component only |
| `price.value` | Seller's asking price ₹{amount} | விற்பவர் கேட்கும் விலை ₹{amount} | "₹280" standing alone | A bare figure beside a book reads as the price of the book |
| `price.negotiable` | This is what the seller is asking. The two of you agree the actual price between yourselves. | இது விற்பவர் கேட்கும் விலை. உண்மையான விலையை நீங்கள் இருவரும் பேசி முடிவு செய்ய வேண்டும். | "Pay the listed price" | Two facts and an instruction. **At least once per flow** (§1.6 rule 2) |
| `price.not_recorded` | BookHop does not know and does not record what you actually pay. | நீங்கள் உண்மையில் எவ்வளவு கொடுக்கிறீர்கள் என்பதை BookHop அறியாது, பதிவும் செய்யாது. | silence, which lets the asking price stand as the price | A statement about our database. This is P14 said out loud, and it is the sentence Circular 20/2021's second limb needs to be true |
| `price.agree_at_handover` | Agree the price between yourselves when you meet. | சந்திக்கும்போது விலையை நீங்கள் இருவரும் பேசி முடிவு செய்யுங்கள். | "Pay ₹280 to the seller" | Compliance's own wording (`COMPLIANCE.md` §4.3.1). Sits in the handover block, §7 |
| `price.ask_in_messages` **(strengthened v1.2)** | Tell {name} what you'd pay for it. | நீங்கள் எவ்வளவு கொடுப்பீர்கள் என்று {name}-க்குச் சொல்லுங்கள். | a numeric counter-offer control | **`COMPLIANCE.md` §4.3.3 released and recommends this.** Was "If you want to discuss the price, say so in your message" — which pointed at the thread without inviting a figure. It now invites one, **addressed to the seller, never to us** (condition 4). Free text only; never a field |
| `price.filter.label` | Highest asking price I'll look at | நான் பார்க்க விரும்பும் அதிகபட்ச கேட்கும் விலை | "Max price" | `max_price_paise` filters the **asking** price (`API-CONTRACT.md` §5.3); the label must say which number it filters |
| `price.seller.hint` | This is the price you're asking for. You can agree something different when you meet — BookHop won't record it either way. | இது நீங்கள் கேட்கும் விலை. சந்திக்கும்போது வேறு விலையை முடிவு செய்யலாம் — எப்படியிருந்தாலும் BookHop அதைப் பதிவு செய்யாது. | "Set your price" | Tells the seller, at intake, that the number is a starting point. **This is where negotiability becomes real rather than stated** |

**On the one that is doing the most work.** `price.seller.hint` is the string
that makes the limb *true* rather than merely *claimed*. Compliance requires
negotiability to be real; a buyer-side disclaimer alone would be a label on a
product that still behaves like a fixed-price listing. Telling the **seller**,
at the moment they type the number, that it is a starting point is what
changes behaviour. If any string in §3.1 has to survive a shortening pass,
it is this one.

**The buyer-side figure prompt — reversed in v1.2, and I was wrong.** In v1.1
I declined to invite a buyer to name a figure, reasoning that a rupee number
in a stored message body was the most reconstructable thing left in the
product, and I escalated it rather than deciding it.
**`COMPLIANCE.md` §4.3.3 released the constraint and went further: it
recommends the prompt.** The reasoning is better than mine and the part I
under-weighted is decisive — **in Circular 20/2021 the e-auctioneer conducts
the auction itself**, which is a far more active role in price formation than
a hint text, and CBDT still held the charge did not apply, because the
transaction and payment happened off-platform and the operator did not know
the quantum. Nothing in our system links a figure to an outcome: offers carry
no amount, `transfers` has no money column, and accepting an offer accepts
**a buyer, not a price**. Unresolved, unstructured, unlinked numbers are
affirmative evidence *for* the limb we are weakest on. And students haggle
whether we prompt or not, so the marginal effect was density, not mechanism.

**The sentence I should have written myself:** copy that *asserts*
negotiability is the weakest form of the limb; copy that *causes* negotiation
produces evidence. I had already identified `price.seller.hint` as "where
negotiability becomes real rather than stated" for the seller — and then
stopped one step short of applying the same insight to the buyer, for a risk
that was not there. Recorded plainly because an over-conservative call that
costs the product utility is still a wrong call, and the next agent should see
how it was reached.

**And the schema backs this up, which it did not when v1.1 was written.**
`ADR-003` §2.3 item 4 forbids the *patterns* `%offer%amount%`,
`%offered_price%`, `%counter%price%`, `%bid%`, `%negotiat%`,
`%accepted_price%`, `%deal%`, with `%agreed_price%` caught by the
settled-consideration row above it, and `THREAT-MODEL.md` §9 holds the control
as a **whitelist**. So the figure prompt is not a copy rule balanced on top of
a permissive schema: **the column cannot exist.** `ADR-003` §2.4 states the
resolution better than my v1.1 wording did, and it is worth quoting because
the two rules read like a contradiction and are not: *"The prohibition on
offer amounts and the requirement that negotiation be real are the same
design: BookHop must not know."*

**What the deck still does NOT do, which is the actual boundary: invite a
conversation, never capture a number.** No numeric input, no amount field, no
parsing or extraction of figures out of `messages.body` into any column, no
"detected price" annotation, no aggregate over amounts mentioned in messages.
And `messages.contact_pattern_flag`'s regex is **never** extended to currency
patterns (`₹`, `Rs`, `INR`, `\d+/-`) — someone will propose it as a leakage
signal, and it would convert the unstructured free text this ruling depends on
into a column we can group by (`COMPLIANCE.md` §4.3.2 item 10,
`SYSTEM.md` §4.23). **The composer stays silent about the flag** for the
reason already in `SYSTEM.md` §4.23, and now for a second reason as well.

### 3.2 `trust.campus_mail` — the three conditions, and the adjacency problem

`COMPLIANCE.md` §2.5a rules that the string ships. Limb 1 (vouching) passed on
my own reading of §1.2; limb 2 (disclosure) carries three conditions, of which
the third is the one nobody had seen.

**Condition 1 — the domain is never rendered.** The string carries **no
`{domain}` placeholder**. A campus may run `student.x.ac.in` alongside
`x.ac.in`, or per-department or per-intake domains, so showing *which* domain
a seller used can disclose student-versus-staff status, department or intake
year — attribute disclosure smuggled in as a trust badge. And it buys nothing:
the listing already shows the campus, and in v1 with one campus the domain is
identical on every listing, so it discriminates between nothing. Enforced by
`SYSTEM.md` §6 criterion 7f.

**Condition 2 — the disclosure is notified.** Showing the fact to a
counterparty is a *different processing operation* from verifying it. The
privacy notice and the `listing_publication` consent text must say so in one
sentence; the string is `consent.listing_publication.disclosure` in §10.4.

**Condition 3 — it renders only when it is true.** `ADR-001` §2.5 provides a
staff-assisted re-verification path for a student who loses institutional email
access. **That user did not sign in with a college email address**, so showing
them the string would be a false statement about a person and would fail
§1.2's own "name a fact" test. **Gate on
`campus_verifications.method = 'INSTITUTIONAL_EMAIL'`, never on
`users.campus_verified`** — two different facts, and the UI must not conflate
them.

**What a staff-re-verified seller's listing shows instead: nothing.** No
substitute string. I considered "Verified by BookHop staff" and rejected it
immediately — it is BookHop asserting something about a person, which is the
single worst string that could exist in this deck. The line is simply absent,
and **we never comment on its absence.**
*Honest residual risk, flagged not solved:* at one campus almost every seller
will be `INSTITUTIONAL_EMAIL`, so a rare absence is more conspicuous than a common
one, and a buyer may read it as a negative signal we did not intend. The
alternatives are worse (a substitute string vouches; a "not available" label
comments on it), so this is accepted with the risk named. Revisit if
staff-assisted re-verification turns out to be common.

#### The adjacency problem — compliance flagged it, layout is mine

`COMPLIANCE.md` §2.5a: *"a contradiction in trust copy is worse than either
string alone."* Correct, and the contradiction is real — "Signed in with a
college email address" next to "Nothing here is checked by BookHop" reads as
the product arguing with itself, because neither sentence states its scope.

**The fix is scope plus adjacency, not separation.** My first instinct was to
push the two sentences to opposite ends of the page. That is the wrong move:
far apart they still contradict, just less visibly, and a reader who holds
both in mind is left to reconcile them alone. Instead:

1. **`trust.not_checked` is rescoped to the book**: "BookHop hasn't checked
   this book." It lives in the **book** block, beside the condition
   quotation and the offer button.
2. **The account fact is scoped by its own block and immediately qualified.**
   In the **seller** block:

   > **About this seller**
   > Signed in with a college email address.
   > That's all BookHop knows about them. We haven't checked who they are.

**Putting the limiting sentence directly after the positive one converts an
apparent contradiction into a single coherent statement, and the pair is
stronger copy than either half alone** — because it tells the buyer exactly
what the signal is worth, which is what §1.2 and `DIRECTIONS.md` §4.2(3) were
always trying to do. A trust signal that states its own ceiling is the only
kind we are allowed to ship, and it happens to be the kind this category's
students have been trained to believe.

Layout consequence in `SYSTEM.md` §4.11: the listing detail page has two
labelled blocks — **the book** and **this seller** — and no trust sentence
ever appears outside the block whose scope it names.

## 4. First run

| Key | English | Tamil (draft) | Note |
|---|---|---|---|
| `run.h1` | Textbooks from your own campus | உங்கள் கல்லூரியில் உள்ள பாடப் புத்தகங்கள் | No tagline, no slogan |
| `run.sub` | Buy a copy from a classmate, or sell the ones you've finished with. | ஒரு வகுப்புத் தோழரிடம் வாங்குங்கள், அல்லது படித்து முடித்தவற்றை விற்றுங்கள். | States the two v1 verbs (D-007) and nothing else |
| `run.what_it_is` | BookHop matches the exact edition your syllabus asks for with a copy someone on your campus already owns. | உங்கள் பாடத்திட்டம் கேட்கும் சரியான பதிப்பை, உங்கள் கல்லூரியில் யாரிடம் இருக்கிறதோ அவருடன் BookHop இணைக்கிறது. | The thesis in one sentence |
| `run.free` | Free for students. There is no fee and no payment inside BookHop. | மாணவர்களுக்கு இலவசம். BookHop-ல் கட்டணம் இல்லை, பணப் பரிமாற்றமும் இல்லை. | D-007, D-004. Both halves matter |
| `run.money` | You and the other student settle the money between yourselves, in person. | பணத்தை நீங்களும் மற்ற மாணவரும் நேரில் சந்தித்துக் கொள்ளுங்கள். | ADR-003 |
| `run.cta` | Sign in with your college email | உங்கள் கல்லூரி மின்னஞ்சலால் உள்நுழையுங்கள் | — |
| `run.why_email` | Your college address is how we know you're on this campus. We don't ask for a document or a phone number. | நீங்கள் இந்தக் கல்லூரியில் இருப்பதை உங்கள் கல்லூரி முகவரியே காட்டுகிறது. ஆவணமும் தொலைபேசி எண்ணும் கேட்கவில்லை. | The campus-verification mechanism, as a mechanism |

**Deliberately absent, with reasons:** no onboarding carousel (three screens
of nothing on a metered connection), no "Welcome!", no counters, no "Join
5,000 students", no app-store-style feature tour.

---

## 5. Campus verification (magic link)

| Key | English | Tamil (draft) | Note |
|---|---|---|---|
| `auth.h1` | Sign in | உள்நுழைக | — |
| `auth.email.label` | Your college email address | உங்கள் கல்லூரி மின்னஞ்சல் முகவரி | — |
| `auth.email.hint` | Ends in {domain}. We send a link — there's no password to remember. | {domain} என்று முடியும். ஒரு லிங்க் அனுப்புவோம் — நினைவில் வைக்க கடவுச்சொல் இல்லை. | **TR-2:** `இணைப்பு` means both "link" and "connection". I used the loanword `லிங்க்` to disambiguate; reviewer to decide |
| `auth.submit` | Send me the link | எனக்கு லிங்க் அனுப்பு | — |
| `auth.sent.h1` | Check your email | உங்கள் மின்னஞ்சலைப் பாருங்கள் | A page, not a spinner (`SYSTEM.md` §4.25) |
| `auth.sent.body` | We sent a link to {email}. Open it on this phone. It works once and stops working after 10 minutes. | {email} க்கு ஒரு லிங்க் அனுப்பியுள்ளோம். அதை இதே ஃபோனில் திறக்கவும். ஒரு முறை மட்டும் வேலை செய்யும், 10 நிமிடத்தில் காலாவதியாகும். | Same message whatever happened — `POST /auth/magic-link` always returns 202 (`API-CONTRACT.md` §5.1), so this copy must never hint whether the address is known |
| `auth.sent.resend` | Send another link | மற்றொரு லிங்க் அனுப்பு | Enabled after 60s |
| `auth.sent.resend_wait` | You can ask for another in {n} seconds. | {n} வினாடிகளில் மற்றொன்று கேட்கலாம். | — |
| `auth.expired` | That link has already been used, or it's more than 10 minutes old. [Send a new one] | அந்த லிங்க் ஏற்கெனவே பயன்படுத்தப்பட்டுவிட்டது, அல்லது 10 நிமிடத்திற்கு மேல் ஆகிவிட்டது. [புதிதாக அனுப்பு] | — |
| `auth.wrong_domain` | That isn't a {domain} address. BookHop is only open at {campus} right now. | அது {domain} முகவரி அல்ல. BookHop தற்போது {campus}-ல் மட்டுமே உள்ளது. | One campus (D-007) |
| `auth.offline` | This didn't reach BookHop. Nothing was lost — tap Send again when you have signal. | இது BookHop-ஐ எட்டவில்லை. எதுவும் தொலைந்துவிடவில்லை — சிக்னல் வந்தபிறகு மீண்டும் "அனுப்பு" தட்டுங்கள். | Reused everywhere a request fails at the network layer (`SYSTEM.md` §4.6) |

---

## 6. Listing a book, searching, and offering

### 6.1 Listing a book (seller)

| Key | English | Tamil (draft) | Note |
|---|---|---|---|
| `sell.h1` | List a book | ஒரு புத்தகத்தைப் பட்டியலிடு | — |
| `sell.isbn.label` | ISBN (13 digits, under the barcode) | ISBN (13 இலக்கங்கள், பார்கோடுக்குக் கீழே) | Tells them *where it is* |
| `sell.isbn.hint` | On the back cover, or the first page inside. | பின் அட்டையில், அல்லது உள்ளே முதல் பக்கத்தில். | — |
| `sell.isbn.found` | {title} · {edition} · {year} · {publisher}. Is this the one? | {title} · {edition} · {year} · {publisher}. இதுதானா? | Confirmation, not assumption |
| `sell.isbn.notfound` | We don't have this ISBN yet. Type the title, author and edition and we'll add it. | இந்த ISBN இன்னும் எங்களிடம் இல்லை. தலைப்பு, ஆசிரியர், பதிப்பு எழுதுங்கள், சேர்த்துக்கொள்வோம். | Never a dead end |
| `sell.isbn.error` | That's {n} digits. An ISBN-13 has 13 — check the number under the barcode. | அது {n} இலக்கங்கள். ISBN-13-ல் 13 இருக்கும் — பார்கோடுக்குக் கீழே உள்ள எண்ணைப் பாருங்கள். | Says what to do, not just what's wrong |
| `sell.edition.label` | Edition | பதிப்பு | The field that matters most |
| `sell.edition.hint` | Students look for an exact edition. If you're not sure, it's on the title page. | மாணவர்கள் சரியான பதிப்பைத் தேடுவார்கள். உறுதியாகத் தெரியவில்லை என்றால், தலைப்புப் பக்கத்தில் இருக்கும். | — |
| `sell.condition.label` | What's wrong with it? | அதில் என்ன பிரச்சினை? | **Required, and phrased to invite defects.** This is the §1.2-compliant way to produce a believable listing (`DIRECTIONS.md` §4.2(3)) |
| `sell.condition.hint` | Torn pages, writing, a bent cover, a missing CD — say it plainly. Buyers trust a description that admits things. | கிழிந்த பக்கங்கள், எழுதியிருப்பது, வளைந்த அட்டை, இல்லாத CD — தெளிவாகச் சொல்லுங்கள். குறைகளைச் சொல்லும் விவரிப்பையே வாங்குபவர்கள் நம்புவார்கள். | **TR-3:** "trust a description that admits things" is close to an idiom. Reviewer: make this plain Tamil, change the English if needed |
| `sell.price.label` | What are you asking for it? | இதற்கு எவ்வளவு கேட்கிறீர்கள்? | **A question, not the label "Price".** Ban 2 (§1.1). A question makes the number the seller's opening position grammatically, before any hint text does it semantically |
| `sell.price.hint` | = `price.seller.hint` (§3.1) | = `price.seller.hint` (§3.1) | **B4.** The string that makes negotiability real rather than stated, and the student-facing face of P14 |
| `sell.price.locked` | You can't change this number later. You can still agree a different price when you meet. | இந்த எண்ணை பின்னர் மாற்ற முடியாது. சந்திக்கும்போது வேறு விலையை முடிவு செய்யலாம். | Immutability is a real constraint the seller will hit (P14, ADR-003 §2.2), so we say it. **The second sentence is the one that stops immutability reading as a fixed price** — which is exactly the trap in `COMPLIANCE.md` §4.3.1(1) |
| `sell.photos.label` | Add photos (up to 4) | படங்கள் சேர் (அதிகபட்சம் 4) | — |
| `sell.photos.hint` | One of the cover and one of the worst page helps a buyer decide. | அட்டையின் ஒரு படமும் மிகவும் மோசமான பக்கத்தின் ஒரு படமும் வாங்குபவருக்கு உதவும். | — |
| `sell.photos.uploading` | Uploading {i} of {n}… | {n}-ல் {i} பதிவேற்றப்படுகிறது… | Determinate (`SYSTEM.md` §4.5) |
| `sell.photos.failed` | Didn't upload. [Try again] | பதிவேற்றப்படவில்லை. [மீண்டும் முயற்சி] | — |
| `sell.photos.skip` | Publish without this photo | இந்தப் படம் இல்லாமல் வெளியிடு | After 3 failures |
| `sell.photos.partial` | {i} of {n} photos attached. | {n} படங்களில் {i} இணைக்கப்பட்டது. | — |
| `sell.publish` | Put this on the list | இதைப் பட்டியலில் சேர் | — |
| `sell.published` | It's on the list. We'll tell you when someone offers. | பட்டியலில் சேர்ந்துவிட்டது. யாராவது கேட்டால் உங்களுக்குத் தெரிவிப்போம். | — |
| `sell.withdraw` | Take this down | இதை நீக்கு | — |

### 6.2 Searching (buyer)

| Key | English | Tamil (draft) | Note |
|---|---|---|---|
| `search.label` | Title or ISBN | தலைப்பு அல்லது ISBN | One field, server decides |
| `search.submit` | Search | தேடு | — |
| `search.count` | {n} copies on your campus | உங்கள் கல்லூரியில் {n} பிரதிகள் | — |
| `search.loading` | Searching… | தேடுகிறது… | — |
| `search.partial` | Previous results — updating | முந்தைய முடிவுகள் — புதுப்பிக்கப்படுகிறது | `SYSTEM.md` §4.13 `partial` |
| `search.empty.title` | No copy of this edition on campus right now. | இந்தப் பதிப்பின் பிரதி தற்போது கல்லூரியில் இல்லை. | **The most important empty state** |
| `search.empty.cta` | Tell me when someone lists it | யாராவது பட்டியலிட்டால் எனக்குத் தெரிவி | Creates a `wanted` request |
| `search.other_editions` | {n} copies of a different edition | வேறு பதிப்பின் {n} பிரதிகள் | Shown separately, never mixed in |
| `search.other_editions.warn` | This is the {other} edition, not the {wanted} edition your syllabus names. | இது {other} பதிப்பு, உங்கள் பாடத்திட்டம் குறிப்பிடும் {wanted} பதிப்பு அல்ல. | The whole product in one sentence |
| `search.stale` | As of {time}. [Search again] | {time} நிலவரம். [மீண்டும் தேடு] | Absolute time (`SYSTEM.md` §5.5) |
| `search.offline` | Search needs a connection. | தேடுவதற்கு இணைய இணைப்பு தேவை. | `இணைய இணைப்பு` = internet connection, disambiguating per TR-2 |
| `search.photos_gate` | Show {n} photos (about {kb} KB) | {n} படங்களைக் காட்டு (சுமார் {kb} KB) | `Save-Data` honoured (`SYSTEM.md` §4.16) |
| `listing.price` *(detail page)* | = `price.value` (§3.1): Seller's asking price ₹{amount} | = `price.value` (§3.1) | **Changed in v1.1.** Was "Asking ₹{amount}". "Asking" alone is a verb with no subject and reads as the platform's framing; the limb needs the seller named (`COMPLIANCE.md` §4.3.1) |
| `listing.price.row` *(dense list row)* | Asking ₹{amount} | கேட்கும் விலை ₹{amount} | = `price.label.short`. The short form is permitted **only** in a list row, and only because `listing.price.note` sits once at the top of the results region (`SYSTEM.md` §4.15, final paragraph). **Never `₹{amount}` alone and never under a `Price` heading** |
| `listing.price.note` **(extended v1.2)** | = `price.negotiable` **+ `price.not_recorded`** (§3.1) | same | **On the listing detail page, once, near the figure.** The "once per flow" of §1.6 rule 2 for the buying flow — **and `price.not_recorded` is now mandatory here, not optional, because `COMPLIANCE.md` §4.3.3 condition 3 requires it in the same view as the figure prompt, and the offer form lives on this page** |
| `listing.seller.label` **(new v1.2)** | About this seller | இந்த விற்பவரைப் பற்றி | The scoping label for the seller block (§3.2). Without a label the two trust sentences read as a contradiction |
| `listing.book.label` **(new v1.2)** | About this book | இந்தப் புத்தகத்தைப் பற்றி | The scoping label for the book block (§3.2) |
| `search.filter.price` | = `price.filter.label` (§3.1) | = `price.filter.label` (§3.1) | Inside the `<details>` filter panel |
| `listing.seller` | {name} · {dept}, {year} · {campus} | {name} · {dept}, {year} · {campus} | `display_name` + campus only (`API-CONTRACT.md` §5.2) |
| `listing.reserved` | Someone else is collecting this one. | வேறு யாரோ இதை வாங்கப் போகிறார்கள். | — |
| `listing.reserved.cta` | Tell me if it comes back | திரும்பக் கிடைத்தால் எனக்குத் தெரிவி | — |
| `listing.withdrawn` | The seller took this down. | விற்பவர் இதை நீக்கிவிட்டார். | — |
| `gate.closed.title` | Listings aren't open at {campus} yet. | {campus}-ல் பட்டியல்கள் இன்னும் திறக்கப்படவில்லை. | `403 GATE_CLOSED` (`SYSTEM.md` §4.22) |
| `gate.closed.body` | You can leave a note saying which book you need, and we'll tell you when listings open. | உங்களுக்குத் தேவையான புத்தகத்தைக் குறிப்பிட்டு வைக்கலாம், பட்டியல்கள் திறக்கும்போது தெரிவிப்போம். | **No date is given, because we don't have one** |

### 6.3 Making an offer

| Key | English | Tamil (draft) | Note |
|---|---|---|---|
| `offer.cta` | Offer to buy this copy | இந்தப் பிரதியை வாங்க கேள் | An offer **to buy**, not an offer **of an amount**. `POST /offers` carries no amount field and the UI must never add one (§1.6 rule 4). If this label ever tests as "make a bid", rename it — "Tell the seller you want this copy" is the fallback |
| `offer.message.label` | Anything you want to ask? (optional) | ஏதாவது கேட்க வேண்டுமா? (விரும்பினால்) | — |
| `offer.message.hint` **(changed again v1.2)** | For example: is the CD still inside? Or tell {name} what you'd pay for it. | உதாரணமாக: CD இன்னும் உள்ளே இருக்கிறதா? அல்லது நீங்கள் எவ்வளவு கொடுப்பீர்கள் என்று {name}-க்குச் சொல்லுங்கள். | **`COMPLIANCE.md` §4.3.3 recommends this.** Craft note: compliance offered "tell {name} what you'd be willing to pay"; I shortened to "what you'd pay for it" because "willing to pay" is near-formal register (TR-4) and runs long in Tamil (§1.3 rule 2). **Addressed to {name}, never to us** — condition 4. The compliance content is unchanged |
| `offer.under_button` **(rescoped v1.2)** | BookHop hasn't checked this book. Look at it before you hand over any money. | இந்தப் புத்தகத்தை BookHop சரிபார்க்கவில்லை. பணம் கொடுப்பதற்கு முன் அதைப் பார்த்துக் கொள்ளுங்கள். | §3, B2. Directly under the commit button, **inside the book block** (§3.2 adjacency fix) |
| `offer.sent` | Offer sent. Waiting for {name} to reply. | கேட்டது அனுப்பப்பட்டது. {name} பதில் சொல்லும் வரை காத்திருங்கள். | — |
| `offer.conflict` | Someone offered just before you. [See what changed] | உங்களுக்கு முன்பே வேறு யாரோ கேட்டுவிட்டார்கள். [என்ன மாறியது] | 409, in human terms (`SYSTEM.md` §4.18) |
| `offer.received` | {name} wants to buy this. | {name} இதை வாங்க விரும்புகிறார். | Seller's view |
| `offer.accept` | Accept — agree a time next | ஏற்றுக்கொள் — அடுத்து நேரம் முடிவு செய் | Label names the next step |
| `offer.decline` | Decline | வேண்டாம் என்று சொல் | — |
| `offer.accepted.clock` | You have until {absolute_time} to agree a time and place. After that the book goes back on the list. | நேரமும் இடமும் முடிவு செய்ய {absolute_time} வரை அவகாசம். அதற்குப் பிறகு புத்தகம் மீண்டும் பட்டியலுக்குச் செல்லும். | The 48h reservation, as an absolute time |

---

## 7. Arranging a handover — B1, BLOCKING

This is the guidance that `API-CONTRACT.md` §5.4 makes a precondition of
reaching `SCHEDULED`, and the component is `SYSTEM.md` §4.20.

| Key | English | Tamil (draft) |
|---|---|---|
| `hand.h1` | Agree a time and place | நேரமும் இடமும் முடிவு செய்யுங்கள் |
| `hand.point.label` | Where will you meet? | எங்கே சந்திப்பீர்கள்? |
| `hand.point.hint` | These are points on campus other students use. | இவை கல்லூரியில் மற்ற மாணவர்கள் பயன்படுத்தும் இடங்கள். |
| `hand.point.empty` | There are no agreed meeting points on your campus yet. Message {name} and agree one between you. | உங்கள் கல்லூரியில் இன்னும் முடிவு செய்யப்பட்ட சந்திப்பு இடங்கள் இல்லை. {name}-க்கு செய்தி அனுப்பி ஒன்றை முடிவு செய்யுங்கள். |
| `hand.day.label` | Which day? | எந்த நாள்? |
| `hand.time.label` | Roughly what time? | சுமார் எந்த நேரம்? |
| `hand.propose` | Propose this time | இந்த நேரத்தைப் பரிந்துரை |
| `hand.their_proposal` | {name} proposed {time} at {point}. | {name} {point}-ல் {time} என்று பரிந்துரைத்துள்ளார். |
| `hand.price` **(B4)** | = `price.agree_at_handover` (§3.1): Agree the price between yourselves when you meet. {name} is asking ₹{amount}. | = `price.agree_at_handover` (§3.1) + {name} ₹{amount} கேட்கிறார். | **New in v1.1, and required.** `COMPLIANCE.md` §4.3.1's instruction names the handover copy specifically. Placed immediately **above** the guidance block, not inside it, so the B1 and B4 review classes stay separate |
| **`hand.guidance.h`** | **Before you go** | **போவதற்கு முன்** |
| **`hand.guidance.1`** | **Look at the book before you hand over any money. Check the edition on the title page.** | **பணம் கொடுப்பதற்கு முன் புத்தகத்தைப் பார்த்துக் கொள்ளுங்கள். தலைப்புப் பக்கத்தில் பதிப்பைப் பாருங்கள்.** |
| **`hand.guidance.2`** | **Meet at the point you both agreed, in daylight, where other students are around.** | **நீங்கள் இருவரும் முடிவு செய்த இடத்தில், பகல் வெளிச்சத்தில், மற்ற மாணவர்கள் இருக்கும் நேரத்தில் சந்திக்கவும்.** |
| **`hand.guidance.3`** | **Don't go anywhere off campus. If something feels wrong, leave. You don't owe anyone an explanation.** | **கல்லூரிக்கு வெளியே எங்கும் போக வேண்டாம். ஏதோ சரியில்லை என்று தோன்றினால், கிளம்பிவிடுங்கள். யாருக்கும் விளக்கம் சொல்ல வேண்டியதில்லை.** |
| **`hand.guidance.4`** | **BookHop hasn't checked the book or the person. You're meeting a classmate, the same as you would through a group chat.** | **BookHop புத்தகத்தையும் சரிபார்க்கவில்லை, நபரையும் சரிபார்க்கவில்லை. நீங்கள் ஒரு வகுப்புத் தோழரைச் சந்திக்கிறீர்கள், குழு அரட்டையில் சந்திப்பது போலவே.** |
| `hand.agree` | I've read this — agree {time} at {point} | இதைப் படித்தேன் — {point}-ல் {time} ஒப்புக்கொள்கிறேன் |
| `hand.scheduled` | Agreed. {time}, {point}. | ஒப்புக்கொள்ளப்பட்டது. {time}, {point}. |
| `hand.reminder` | Today, {time} at {point}. You're collecting {title}. | இன்று, {point}-ல் {time}. நீங்கள் {title} வாங்கப் போகிறீர்கள். |
| `hand.guidance.updated` | This guidance was updated. [Read it again] | இந்த வழிகாட்டல் புதுப்பிக்கப்பட்டது. [மீண்டும் படி] |
| `hand.guidance.already` | You read the handover guidance on {date}. [Read again] | நீங்கள் {date}-ல் கைமாற்ற வழிகாட்டலைப் படித்தீர்கள். [மீண்டும் படி] |

**Three notes on `hand.guidance.4`, which is the single most carefully
engineered sentence in the product.**
(a) It names the limit of our role without using any banned word.
(b) The group-chat comparison is deliberate and honest: `DISCOVERY.md` §2.2(f)
and `COMPETITORS.md` §3.5 establish that the status quo *is* a WhatsApp group,
so the sentence tells the student the true risk profile is the one they
already accept — without claiming it is low.
(c) **It must not be softened in Tamil.** A natural Tamil rendering will want
to add reassurance. Reviewer: don't.

---

## 8. Confirming

| Key | English | Tamil (draft) | Note |
|---|---|---|---|
| `confirm.q` | Did the book change hands? | புத்தகம் கை மாறியதா? | The endpoint's one question (`API-CONTRACT.md` §5.4) |
| `confirm.yes` | Yes — I got the book ({title}, {edition}) | ஆம் — புத்தகம் கிடைத்தது ({title}, {edition}) | Buyer. Unambiguous out of context (SC 2.5.3) |
| `confirm.yes.seller` | Yes — I handed it over ({title}, {edition}) | ஆம் — கொடுத்துவிட்டேன் ({title}, {edition}) | Seller |
| `confirm.no` | No — it didn't happen | இல்லை — நடக்கவில்லை | — |
| `confirm.waiting` | You confirmed. Waiting for {name}, until {absolute_time}. | நீங்கள் உறுதிப்படுத்திவிட்டீர்கள். {absolute_time} வரை {name}-க்காகக் காத்திருக்கிறோம். | The 72h clock. One side alone is never a completion (`DATA-MODEL.md` §6.2) |
| `confirm.done` | Done. Both of you confirmed. | முடிந்தது. நீங்கள் இருவரும் உறுதிப்படுத்திவிட்டீர்கள். | No action after |
| `confirm.why` | We only ask this so the next student can see the service is being used. We don't ask what you paid, and we don't record it. | அடுத்த மாணவர் இந்தச் சேவை பயன்படுத்தப்படுவதைப் பார்க்கவே இதைக் கேட்கிறோம். நீங்கள் எவ்வளவு கொடுத்தீர்கள் என்று கேட்கவில்லை, பதிவும் செய்யவில்லை. | **Why this matters:** D-008 ruling 2 says a confirmation is the evidence the whole thesis needs. Asking honestly is better than nagging. **The second sentence is `price.not_recorded` (§3.1) at the one moment a student would most expect to be asked for a figure** — which makes it the strongest placement of the limb in the whole product. Extended in v1.1 to say "and we don't record it", because "we don't ask" alone leaves room for inferring we derived it |
| `confirm.other_side` | {name} confirmed. Your turn. | {name} உறுதிப்படுத்திவிட்டார். உங்கள் முறை. | — |
| `noshow.report` | {name} didn't turn up | {name} வரவில்லை | — |
| `noshow.result` | Reported. No penalty is applied to anyone. | புகார் பதிவு செய்யப்பட்டது. யாருக்கும் எந்த தண்டனையும் இல்லை. | `DATA-MODEL.md` §6.2 — no automatic penalty, so we say so |
| `expired.reservation` | The 48 hours ran out and the book went back on the list. | 48 மணி நேரம் முடிந்துவிட்டது, புத்தகம் மீண்டும் பட்டியலுக்குச் சென்றுவிட்டது. | — |

---

## 9. Reporting and problems — B3, BLOCKING

| Key | English | Tamil (draft) | Note |
|---|---|---|---|
| `report.cta` | Report a problem | ஒரு பிரச்சினையைப் புகாரளி | In the footer on every page |
| `report.reason.label` | What happened? | என்ன நடந்தது? | — |
| `report.reason.1` | The book wasn't what the listing described | பட்டியலில் விவரித்தபடி புத்தகம் இல்லை | — |
| `report.reason.2` | The other person didn't turn up | மற்ற நபர் வரவில்லை | — |
| `report.reason.3` | This is a photocopy or a pirated copy | இது ஒரு நகல் அல்லது திருட்டுப் பிரதி | Copyright risk rose when scope narrowed to textbooks (D-008) |
| `report.reason.4` | The other person behaved badly | மற்ற நபர் தவறாக நடந்துகொண்டார் | — |
| `report.reason.5` | Something else | வேறு ஏதாவது | — |
| `report.body.label` | Tell us what happened, in your own words | என்ன நடந்தது என்று உங்கள் வார்த்தைகளில் சொல்லுங்கள் | — |
| `report.submitted` | Ticket #{n}. We'll reply within 24 hours. | டிக்கெட் #{n}. 24 மணி நேரத்திற்குள் பதில் சொல்வோம். | r.3(2)(a)(i) / r.5(3)(b) |
| `report.offline` | This didn't reach BookHop. [Copy this text] so you don't lose it. | இது BookHop-ஐ எட்டவில்லை. தொலைந்துவிடாமல் இருக்க [இந்த உரையை நகலெடுங்கள்]. | `SYSTEM.md` §4.24 |
| `block.cta` | Block {name} | {name}-ஐத் தடு | — |
| `block.result` | {name} can't offer on your listings or message you. | {name} உங்கள் பட்டியல்களில் கேட்கவோ, உங்களுக்குச் செய்தி அனுப்பவோ முடியாது. | States the effect exactly |
| `grievance.cta` | Contact the grievance officer | குறைதீர்ப்பு அதிகாரியைத் தொடர்பு கொள்ள | **Works without an account** (`API-CONTRACT.md` §5.6) |
| `dispute.open` | You raised a problem. Ticket #{n}. | நீங்கள் ஒரு பிரச்சினையைத் தெரிவித்தீர்கள். டிக்கெட் #{n}. | — |
| `dispute.unresolved` | We couldn't settle this. Ticket #{n} is closed. | இதை எங்களால் தீர்க்க முடியவில்லை. டிக்கெட் #{n} மூடப்பட்டது. | `CLOSED_UNRESOLVED` — honest, not padded |

---

## 10. Cross-cutting strings

### 10.1 Failure, offline, stale — one wording each, reused everywhere

| Key | English | Tamil (draft) |
|---|---|---|
| `sys.offline` | This didn't reach BookHop. Nothing was lost — try again when you have signal. | இது BookHop-ஐ எட்டவில்லை. எதுவும் தொலையவில்லை — சிக்னல் வந்தபிறகு மீண்டும் முயற்சிக்கவும். |
| `sys.no_connection` | No connection. This is what we had at {time}. | இணைய இணைப்பு இல்லை. {time} மணிக்கு இருந்தது இதுதான். |
| `sys.stale` | As of {time}. [Reload] | {time} நிலவரம். [மீண்டும் ஏற்று] |
| `sys.retry` | Try again | மீண்டும் முயற்சி |
| `sys.sending` | Sending… | அனுப்பப்படுகிறது… |
| `sys.loading` | Loading… | ஏற்றப்படுகிறது… |
| `sys.unchanged` | That didn't go through. Nothing has changed. | அது நடக்கவில்லை. எதுவும் மாறவில்லை. |
| `sys.conflict` | {name} changed something while you were looking. [Reload to see it] | நீங்கள் பார்த்துக் கொண்டிருக்கும்போதே {name} ஏதோ மாற்றியிருக்கிறார். [பார்க்க மீண்டும் ஏற்று] |
| `sys.fix_count` | {n} things to fix | சரிசெய்ய வேண்டியவை: {n} |
| `sys.help` | Help | உதவி |
| `sys.skip` | Skip to content | உள்ளடக்கத்திற்குச் செல் |

**On `sys.unchanged`:** "Nothing has changed" is the most reassuring sentence
we are allowed to write, and it is allowed because it is a statement about our
database, not a prediction.

### 10.2 Things we never say

| Never | Because |
|---|---|
| "Oops!" / "Uh oh!" / "Something went wrong" | Infantilising, and the last one says nothing. Name what failed |
| "Please try again later" | "Later" is not an instruction |
| Any exclamation mark in an error | — |
| "Successfully" | A result either happened or it didn't |
| "Our team is working on it" | Not true at pilot scale; there is no team |
| "Don't worry" | A prediction (§1.2) |
| "Trusted", "reliable", "genuine", "authentic" | Judgements about people or books (§1.2) |
| "Instant", "quick", "hassle-free" | Predictions we would lose to the photocopy shop on anyway (`DISCOVERY.md` §2.3) |
| "Join thousands of students" | False at one campus, and it is the category's tell (`COMPETITORS.md` §3.11) |
| **"pay the listed price" / "fixed price" / "non-negotiable" / "final price"** | **Ban 2 (§1.1).** Forbidden strings in `tests/unit/test_forbidden_copy.py` per `COMPLIANCE.md` §4.3.1 |
| **the bare label "Price"** | Same. Use `price.label.full` / `price.label.short` (§3.1) |
| "Pay ₹{amount}" / "Total: ₹{amount}" / "You owe ₹{amount}" | Each one states the asking price **as** the transaction price, which is the exact reading Circular 20/2021's second limb must not support |
| "Price drop", "Reduced", "Best price", "Deal" | Imply a price we set or endorse; and E-Com r.4(13) already bars was/now framing |
| An amount in any notification or email | **New rule in v1.1:** push and email never carry the figure (§10.5). A number in a notification is the one place a student would read it as an invoice |
| **"What would you pay?" / "Enter your offer" / "Your price"** | **New in v1.2.** A figure prompt must address the **seller**, never us — "what would you pay?" reads as BookHop collecting an answer (`COMPLIANCE.md` §4.3.3 condition 4). Use `price.ask_in_messages` |
| **Any `@`-prefixed email domain literal, anywhere** | **New in v1.2.** `COMPLIANCE.md` §2.5a condition 1 — a multi-domain campus leaks student-versus-staff status, department or intake year through what looks like a trust badge |
| "Verified by BookHop staff" (for a staff-re-verified seller) | §3.2 — BookHop asserting something about a person. The line is **absent** for those users, and we do not comment on its absence |

### 10.3 Age gate — B3, BLOCKING

| Key | English | Tamil (draft) | Note |
|---|---|---|---|
| `age.label` | Your date of birth | உங்கள் பிறந்த தேதி | Native `<input type="date">` |
| `age.why` | BookHop is only for students aged 18 and over. We don't keep this date. | BookHop 18 வயது மற்றும் அதற்கு மேல் உள்ள மாணவர்களுக்கு மட்டுமே. இந்தத் தேதியை நாங்கள் வைத்துக்கொள்ள மாட்டோம். | DOB is never persisted (`API-CONTRACT.md` §5.1) |
| `age.rejected` | BookHop is only for students aged 18 and over. Your account has been removed and the date you entered was not kept. | BookHop 18 வயது மற்றும் அதற்கு மேல் உள்ள மாணவர்களுக்கு மட்டுமே. உங்கள் கணக்கு நீக்கப்பட்டுவிட்டது, நீங்கள் கொடுத்த தேதி வைத்துக்கொள்ளப்படவில்லை. | Hard and complete. No softening, no "come back when you're 18" |

### 10.4 Privacy, consent, erase — B3, BLOCKING

| Key | English | Tamil (draft) | Note |
|---|---|---|---|
| `privacy.h1` | What BookHop knows about you | BookHop உங்களைப் பற்றி அறிந்திருப்பது | A heading from the student's point of view |
| `consent.row` | {purpose} — {granted_or_not} | {purpose} — {granted_or_not} | A real checkbox in a 44px row, a toggle not an email (DPDP r.3(c)(i)) |
| `consent.notice_changed` | The privacy notice changed on {date}. [Read what changed] | தனியுரிமை அறிவிப்பு {date}-ல் மாறியது. [என்ன மாறியது] | `stale` state |
| `consent.listing_publication.disclosure` **(new v1.2, B3)** | When you put a book on the list, other students on your campus see your display name, your campus, and that you signed in with a college email address. | நீங்கள் ஒரு புத்தகத்தைப் பட்டியலில் சேர்க்கும்போது, உங்கள் கல்லூரியில் உள்ள மற்ற மாணவர்கள் உங்கள் காட்சிப் பெயரையும், கல்லூரியையும், நீங்கள் கல்லூரி மின்னஞ்சல் முகவரியால் உள்நுழைந்ததையும் பார்ப்பார்கள். | **`COMPLIANCE.md` §2.5a condition 2.** Showing the sign-in fact to a counterparty is a *different processing operation* from verifying it, so it must be notified before it is lawful (DPDP s5). Belongs in the `listing_publication` consent text **and** the privacy notice. **Without this sentence `trust.campus_mail` is outside the notified purpose and must not render** |
| `erase.cta` | Delete my account | எனது கணக்கை நீக்கு | — |
| `erase.confirm.h` | This cannot be undone | இதை மீட்டெடுக்க முடியாது | — |
| `erase.confirm.retained` | We have to keep these records for one year, because the law requires it: {list}. Everything else goes now. | இந்தப் பதிவுகளை ஒரு வருடம் வைத்திருக்க வேண்டும், சட்டம் அதைக் கோருகிறது: {list}. மற்ற அனைத்தும் இப்போதே நீக்கப்படும். | **r.8(3) stated before the button, not after** (`API-CONTRACT.md` §5.1) |
| `erase.done` | Your account is gone. | உங்கள் கணக்கு நீக்கப்பட்டுவிட்டது. | — |

### 10.5 Notification copy (Web Push, email)

Push kinds from `DATA-MODEL.md` §8: `OFFER_RECEIVED`, `OFFER_ACCEPTED`,
`OFFER_DECLINED`, `HANDOVER_SCHEDULED`, `HANDOVER_REMINDER`,
`CONFIRM_HANDOVER`.

Two rules. **(a)** A notification names the thing and the next action, and
never asks for engagement — no "You have 1 new notification", no "Don't miss
out". **(b) New in v1.1: no notification or email ever contains a rupee
amount.** Not the asking price, not anything. A figure in a push notification
has no surrounding context to make it the seller's asking price, so it reads
as an amount due — and that is precisely the reading
`COMPLIANCE.md` §4.3.1(1) tells us to avoid. The amount lives on the listing
and the handover page, where `price.negotiable` can sit beside it.

| Kind | English | Tamil (draft) |
|---|---|---|
| `OFFER_RECEIVED` | {name} wants to buy {title}. | {name} {title} வாங்க விரும்புகிறார். |
| `OFFER_ACCEPTED` | {name} accepted. Agree a time and place. | {name} ஏற்றுக்கொண்டார். நேரமும் இடமும் முடிவு செய்யுங்கள். |
| `OFFER_DECLINED` | {name} declined. | {name} வேண்டாம் என்று சொல்லிவிட்டார். |
| `HANDOVER_SCHEDULED` | {time}, {point}, with {name}. | {time}, {point}, {name}-உடன். |
| `HANDOVER_REMINDER` | Today {time} at {point}. {title}. | இன்று {point}-ல் {time}. {title}. |
| `CONFIRM_HANDOVER` | Did the book change hands? | புத்தகம் கை மாறியதா? |

---

## 11. Open review items for the Tamil reviewer

| # | Item | Why it matters |
|---|---|---|
| **TR-1** | `சரிபார்` ("check/verify") is used for the **student's** action in `trust.check_yourself` and for **our non-action** in `trust.not_checked`. Confirm Tamil keeps those apart clearly, and tell us whether `சரிபார்` is usable in BookHop's voice at all | The whole §3 trust mechanism depends on this distinction |
| **TR-2** | `இணைப்பு` means both "link" and "connection". I used the loanword `லிங்க்` for the magic link and `இணைய இணைப்பு` for the network. Confirm or replace | A student who reads "your connection has expired" instead of "your link has expired" cannot sign in |
| **TR-3** | `sell.condition.hint` ("Buyers trust a description that admits things") is near-idiomatic. Rewrite in plain Tamil; the English may be changed to match | §1.5's rule |
| **TR-4** | Register throughout: is this a classmate's voice or a bank's? Flag anything that reads as officialese, especially §7 and §8 | Officialese reads as the platform asserting things (§1.2) |
| **TR-5** | Loanwords. I kept `ISBN`, `CD`, `KB`, `BookHop`, `டிக்கெட்`, `லிங்க்`, `சிக்னல்`. Which of these do Chennai students actually use, and which should be Tamil? | Over-Tamilising technical terms is as wrong as under-translating |
| **TR-6** | Digits. I propose Western Arabic (0–9) in both locales, including prices and ISBNs, and **no Tamil numerals**. Confirm | Affects every price and every ISBN comparison |
| **TR-7** | `BookHop` in Tamil: transliterate (`புக்ஹாப்`) or keep Latin? I kept Latin | Product name; `product-manager` also has a view |
| **TR-8** | **Proposed Tamil additions to `tests/unit/test_forbidden_copy.py` for Ban 1.** Candidates for the banned concepts: `பாதுகாப்பான` / `பத்திரமான` (safe), `சரிபார்க்கப்பட்ட` / `உறுதிசெய்யப்பட்ட` (verified), `உறுதியளிக்கப்பட்ட` / `கியாரண்டி` (guaranteed), `பாதுகாக்கப்பட்ட` (protected), `உறுதி அளிக்கப்பட்ட` (assured). **Must be narrowed by a native speaker before it goes in the test** — `பாதுகாப்பு` is a normal word in the data-protection language the privacy notice is legally required to use, so a careless ban would break compliance copy | Until this lands, **a Tamil string that warrants would pass the grep**. **And since v1.1 this gap has company: the same test now carries a tax limb (Ban 2, TR-11) and still greps English only, so a Tamil string that reads as a fixed price would also pass.** One blind spot, two legal exposures. `test-qa` must be told (`SYSTEM.md` §7.3) |
| **TR-9** | Second person. I used the plural/respectful form (`-ங்கள்`) throughout. Is that right for students addressing students, or is the familiar form the honest register? | Affects every single string |
| **TR-10** | §7 `hand.guidance.*` — confirm nothing in the Tamil adds reassurance the English does not contain | B1 is blocking on exactly this |
| **TR-12** *(new, v1.2)* | **The two strings that now do the trust work as a pair (§3.2): `trust.campus_mail` + `trust.account_only`.** They must read as one coherent statement — *this is the one thing we know, and it is the only thing we know* — not as a boast followed by a retraction. If the Tamil for the second sentence reads as an apology or as casting doubt on the seller, it is wrong. Also confirm `கல்லூரி மின்னஞ்சல் முகவரி` is how a Chennai student would say "college email address", and that `காட்சிப் பெயர்` is usable for "display name" in `consent.listing_publication.disclosure` or give us the word students actually use | **B2 and B3.** A mistranslation here either over-promises (B2) or misdescribes a notified disclosure (B3) |
| **TR-11** *(new, v1.1)* | **The negotiability strings (§3.1).** Two questions. (a) Does `விற்பவர் கேட்கும் விலை` reliably read as *"the price the seller is asking"* rather than *"the seller's price"*? If the genitive collapses the distinction in natural Tamil, we need a different construction — this is the whole limb. (b) **Proposed Tamil forbidden strings for Ban 2**, to be narrowed by the reviewer: `நிர்ணயிக்கப்பட்ட விலை` / `நிலையான விலை` (fixed price), `பேரம் பேச முடியாது` (non-negotiable), `இறுதி விலை` (final price), `பட்டியல் விலையைச் செலுத்து` (pay the listed price). **`விலை` alone cannot be banned** — it is the ordinary word for price and appears in every approved string | **This is the one TR item that carries a tax limb.** It belongs in the B4 batch, not the TR batch, and it is listed here only so the reviewer sees all the open questions in one place |

---

## 12. Items referred to another agent — two closed, two open

A blocked string does not ship in either language, and **silence is not
approval**. Items 1 and 2 were closed by `COMPLIANCE.md` v1.2; items 3 and 4
remain open.

1. **✅ CLOSED v1.2 — `trust.campus_mail`.** `COMPLIANCE.md` §2.5a rules it
   **ships**, with the domain removed: *"Signed in with a college email
   address."* Compliance confirmed my own §1.2 reading on the vouching limb
   rather than second-guessing it. The disclosure limb carries three
   conditions, all implemented: no domain ever rendered, the disclosure
   notified (`consent.listing_publication.disclosure`, §10.4), and the string
   gated on `campus_verifications.method = 'INSTITUTIONAL_EMAIL'` rather than on
   `users.campus_verified`. The adjacency problem compliance flagged but did
   not make a condition is solved in §3.2. **Refusing to read silence as
   approval was the right call and it cost nothing** — one round trip against
   shipping a false statement about a person, which is what condition 3 would
   otherwise have let through. Tamil remains blocked on B2.

2. **✅ CLOSED v1.2 — the buyer-side figure prompt, and I was wrong.**
   `COMPLIANCE.md` §4.3.3: a student-authored rupee figure in a free-text
   message does not change the s194-O position *"not at the margin, not at
   all"*, and compliance **recommends** the prompt rather than merely
   permitting it. Implemented in `price.ask_in_messages` and
   `offer.message.hint`. The full reasoning, and the part of it I
   under-weighted, is recorded at §3.1 rather than buried here, because the
   lesson generalises: an over-conservative call that costs the product
   utility is still a wrong call. The four conditions are implemented at §3.1
   (no structured capture, no currency in the contact-pattern regex),
   `listing.price.note` (condition 3) and `offer.message.hint`
   (condition 4). **Condition 1 is additionally enforced in the schema** —
   `ADR-003` §2.3 item 4, verified — so it does not rest on copy discipline.

3. **✅ CLOSED v1.3 — the slug is renamed.** Amendment **A-7**:
   `handover-safety` → `handover-guidance`, `HANDOVER_SAFETY` →
   `HANDOVER_GUIDANCE`, across `API-CONTRACT.md`, `DATA-MODEL.md` and
   `TASKS.md`. Verified by reading all three. The deck's label and the
   identifier behind it now agree, which was the point: **a slug is a route,
   but an identifier is where a label comes from**, and no grep catches the
   identifier that suggested the wrong label.

4. **⏳ STILL OPEN — four blocking Tamil classes and twelve TR items
   (§2, §11). This is the deck's one real blocker, and it needs a person, not
   a decision.** What changed in v1.3 is that the policy is no longer a
   promise in this file: `feature_flags['i18n.ta_enabled']` is seeded
   **false**, `locale/ta/BLOCKING_CLASSES.toml` and `locale/ta/REVIEWED.toml`
   exist from slice S1, and the release checklist requires a reviewer-signed
   entry before any blocking-class string can be served
   (`TASKS.md` A-7/A-9, `THREAT-MODEL.md` §6.1). Tamil strings are written and
   will stay written and unserved. **Until a named native speaker reviews
   them, "Tamil is supported" is not a true statement about this product, and
   nobody should make it on the strength of this deck existing.**
   *Needed from:* the founder — a named native Tamil speaker. §2's sign-off
   block is the artefact that closes it.

---

## Amendment log

| Version | Date | Change |
|---|---|---|
| v1.0 | 2026-10-21 | First deck. Vouching ban, the §1.2 governing rule, "worth your while" deleted rather than translated, three blocking Tamil classes, ten TR items |
| **v1.3** | **2026-10-21** | **Two referred items closed after reading the contracts directly rather than on report.** §12 item 3 closed by amendment **A-7** (`handover-safety` → `handover-guidance`, `HANDOVER_SAFETY` → `HANDOVER_GUIDANCE`). §3.1 and §12 item 2 updated: the no-offer-amount rule is enforced by **`ADR-003` §2.3 item 4 as patterns, under a whitelist** — the column cannot exist, so copy is not holding that line alone; `ADR-003` §2.4's resolution quoted. §1.5a records that the college/campus distinction is now a **project rule** owned beyond this deck. §12 item 4 restated: the Tamil gate is now mechanical (`i18n.ta_enabled` false, `locale/ta/REVIEWED.toml`), so what is open is a **person, not a control** |
| **v1.2** | **2026-10-21** | **Both open compliance rulings implemented (`COMPLIANCE.md` v1.2 §2.5a and §4.3.3); §12 items 1 and 2 closed.** `trust.campus_mail` ships as "Signed in with a college email address" — no domain, notified, gated on verification *method*. New `trust.account_only`; `trust.not_checked` and `offer.under_button` **rescoped to the book**; new §3.2 solving the adjacency problem with two labelled blocks (`listing.seller.label`, `listing.book.label`); new §1.5a fixing "college" vs "campus". **Buyer-side figure prompt adopted** — `price.ask_in_messages` and `offer.message.hint` now invite a figure *addressed to the seller*; `listing.price.note` gains `price.not_recorded` as a mandatory condition; currency patterns banned from the contact-pattern regex. Three rows added to §10.2, one to §10.4. New TR-12 |
| **v1.1** | **2026-10-21** | **Negotiability added as a copy requirement on instruction from `COMPLIANCE.md` §4.3.1.** New Ban 2 (§1.1), new §1.6 (the reasoning), new §3.1 (nine strings, blocking class **B4**), new TR-11. Changed: `sell.price.label` from a label to a question, `sell.price.hint` → `price.seller.hint`, new `sell.price.locked`, `listing.price` from "Asking ₹{n}" to "Seller's asking price ₹{n}", new `listing.price.note`, new `search.filter.price`, `offer.message.hint` extended, new `hand.price`, `confirm.why` extended, six new rows in §10.2, new rule (b) in §10.5. `trust.campus_mail` marked **blocked** pending a compliance ruling. New §12 |
