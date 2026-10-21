# DIRECTIONS.md — two visual directions for BookHop v1

**Owner:** `design-director` · **Version:** v1.0 · **Date:** 2026-10-21
**Phase:** B · **Handoff:** `product-manager`, `frontend-developer`, `test-qa`
**Inputs read:** `.claude/agents/design-director.md` · `company/README.md` §1 ·
`decisions/DECISIONS.md` D-007, D-009 (and D-004, D-006, D-008 for the
constraints they set) · `product/DISCOVERY.md` §1, §2, §3 ·
`evidence/COMPETITORS.md` §1–§5 · `architecture/ADR-001-stack.md` ·
`architecture/API-CONTRACT.md` §5–§6 · `architecture/DATA-MODEL.md` §6.2 ·
`metrics/METRICS.md`

> **STATUS — nothing here has been tested.** No student has seen either
> direction. No usability session has been run. `USER-TEST-PLAN.md` is the
> instrument; it has **zero results**, per `README.md` §8. Every claim below
> about what a student will *feel* is my reasoning from the evidence files,
> and is labelled as such.
>
> **Also untested: my Tamil.** I am not a verified Tamil speaker. Every Tamil
> string in `COPY-DECK.md` is a draft requiring native review, and three
> classes of string are marked **BLOCKING** there.

---

## 0. What the design has to do, in one paragraph

A student needs a specific prescribed edition. Their real alternatives are a
₹60–200 photocopy at the campus gate and a free PDF in the batch WhatsApp
group — both instant, both cheaper (`DISCOVERY.md` §2.2(a), §2.2(b), §2.3).
BookHop cannot win on price or speed. It can only win where the student needs
the *whole book for a whole semester* and where **getting the wrong edition is
a real cost** — and edition-exactness is the one part of the thesis with
commercial corroboration outside our own heads: ChennaiUsedBooks refuses
educational stock older than two years "due to frequent updates in edition"
(`COMPETITORS.md` §5.1), and Anna University R2021 syllabi name editions and
years explicitly (same section). So the interface has exactly three jobs,
and the design is answerable for each:

1. **Prove the edition matches** — fast, on a small screen, with no ambiguity.
2. **Make a classmate's listing believable without BookHop vouching for it.**
   We may not say "safe", "verified" or "guaranteed" (and the stack already
   greps templates for "protected" and "assured" too —
   `API-CONTRACT.md` §5.4). The confidence has to come from somewhere else.
3. **Get two people to the same bench at the same time**, over a connection
   that drops, on a phone whose owner pays for the bytes.

Anything that adds a step or a doubt loses to the photocopy shop. That is the
design brief; the visual direction is downstream of it.

### 0.1 Constraints I treated as hard, not as preferences

| Constraint | Source | How it shows up below |
|---|---|---|
| Mid-range Android, 3G, metered data | charter metrics; `DISCOVERY.md` §1.1 (data row `[S]`, handset row `[G]`) | No webfont. No framework. Photo bytes are opt-in under `Save-Data`. §2.1, §5 |
| WCAG 2.2 AA, verified not claimed | charter; `README.md` §7 | Every pair computed, §3. Zero failures or the direction is not shippable |
| EN + Tamil, Tamil not a bolt-on | charter | Changes the type choice, the line-height, every fixed width. §2.3 |
| "safe" / "verified" / "guaranteed" banned | this brief; `COMPLIANCE.md` §5.5 via `API-CONTRACT.md` §5.4 | §4.2 — this is the hardest problem and it drove the recommendation |
| Server-rendered HTML + htmx, no SPA | `ADR-001` §2.3 | Interactions are page loads and fragment swaps. Designed for honestly in `SYSTEM.md` §5 |
| No money in the product, ever | D-004, ADR-003 | No price-paid field, no "was/now", no fee, no wallet. §2.4 |
| Seller-stated condition must never read as our grade | `DATA-MODEL.md` L340; `COMPLIANCE.md` §2.5; CTO escalation #4 | The attributed-claim component, §4.2(1) |

### 0.2 What the competitor audit tells a designer specifically

Not "the space is crowded" — that is a strategy finding. The design findings:

- **Trust theatre is already table stakes and is not working.** Bookaao ships
  escrow, anonymous chat, "Verified Books" ranking and verified-order reviews;
  Clankart ships escrow (`COMPETITORS.md` §3.9, §3.8). We cannot out-badge
  them, and D-004 forbids the escrow that makes a badge mean anything. **A
  trust badge is the one visual device available to us that would be both
  dishonest and legally dangerous.** It is banned in both directions below.
- **Self-contradicting numbers are the category's visual signature.**
  BookMandee shows "Verified Users (10000+)" beside live counters reading 0;
  CampusXchange claims "Trusted by 5,000+ Students" with every counter at ₹0
  and 0%; OldTextBooks claims 50,000 students over 291 listings
  (§3.11, §4.5). A student who has seen one of these has been trained that
  confident platform claims are noise. **Any big self-congratulating number on
  our homepage reads as that.** Both directions ban social-proof counters.
- **The thing that actually works in this market is physical inspection** —
  Moore Market needs no platform because you hold the book (§3.6). Our
  handover *is* that mechanism. The design should treat the inspection moment
  as the product's climax rather than as a legal footnote, which is also
  exactly what Red Team's open O-10 is about (D-008 ruling 2).
- **Listing staleness is the oldest failure mode of campus book exchanges** —
  a 1997 UPenn newsgroup already expired posts after two weeks to keep
  listings current (§3.5). Recency therefore has to be *visible on every
  listing*, not buried. This is why `stale` is a first-class state in
  `SYSTEM.md`, not an afterthought.

---

## 1. The two directions, stated so they can be told apart

They disagree about **what the hero object is**, and everything else follows.

|  | **A — "Catalogue Card"** | **B — "Daylight Meet"** |
|---|---|---|
| **The idea, one sentence** | The interface is a bibliographic record: the book's exact identity is the hero, and every human claim about it is shown as an attributed quotation rather than as a fact. | The interface is a plan to meet someone: the counterparty and the appointment are the hero, the book is one line of text, and each screen asks exactly one question. |
| **Who it is for** | The student who has been burned by an edition mismatch, or fears being — the buyer comparing a listing against a syllabus line. Comfortable reading dense text. | The student who has never transacted with a stranger and is not app-fluent — whose doubt is "will this person actually turn up", not "is this the right edition". |
| **Hero object** | The catalogue entry (title / author / **edition** / year / publisher / ISBN-13) | The handover docket (who, where, when, what state it is in) |
| **Borrows from** | Library catalogue cards and accession stamps; Indian academic title pages and the back-matter ISBN block; the bibliographic citation format Anna University syllabi themselves use; rubber date stamps; ledger rules | Campus election and film posters; hostel-door nameplates; bus-route and exam-hall-ticket boards; the flat saturated institutional colour of a Tamil Nadu government notice |
| **Density** | Dense. A result row carries 7 facts. Scanning is the activity. | Sparse. One decision per screen, large type, 3–4 elements. Reading is the activity. |
| **Type posture** | Serif bibliographic line against a system sans UI; monospace for ISBN and windows. English-led typographically, Tamil as an equal second voice | Heavy display weight, Tamil-led: the Tamil string is set first and the layout is sized to it, English fits in the box Tamil needs |
| **Colour posture** | Paper ground, ink text, **one** accent (stamp indigo) used only for action and link. Status is carried in four muted earth tints | Two large flat fields — deep green slab and saffron CTA — against a warm ground. Colour is structural, not accent |
| **Photo role** | Evidence, subordinate. Thumbnails. The record is primary; a photo corroborates it | Not important. One small thumbnail, often absent. The person and place are what you look at |
| **Price role** | Set once, large, in the record, as "asking price" | A line in the docket. Deliberately undramatic |
| **What it feels like on 3G** | §5.1 | §5.2 |
| **Its characteristic failure** | Reads as a database. A student who does not care about editions sees a wall of grey facts and leaves. | Reads as patronising, and it cannot show edition evidence at a glance — the one thing we are supposed to be better at. |

If those two paragraphs could be swapped without changing anything, this
section has failed. They cannot: A's homepage is a search field over a list of
records; B's homepage is a single card that says who you are meeting next.

---

## 2. Direction A — "Catalogue Card", in detail

### 2.1 The idea

A library catalogue card is a 100-year-old solution to exactly our problem:
*establish that this physical object is the specific work you are looking for,
in a glance, with no pictures and almost no bytes.* It also carries a built-in
honesty: a catalogue card states who recorded what and when, and never
appraises the book. That is the posture the lawyers require of us anyway
(§4.2), which is the moment this stopped being a style and became an argument.

The accession stamp supplies the one accent. A rubber stamp is a record of an
*event* — "this was entered on this date" — not a claim of quality. It is the
only decorative device in the direction and it is used for exactly one thing:
the recency of a listing, which `COMPETITORS.md` §3.5 says is the oldest
failure mode in this category.

### 2.2 Type

- **Bibliographic line — serif.** Title, author, edition, year, publisher.
  Set in the platform serif (`ui-serif` → Georgia → Noto Serif). This is the
  entire visual argument: a serif title line says *this is a book's own
  identity*, and it separates the book's facts from the app's chrome without a
  single box or colour.
- **UI chrome — the system sans.** Labels, buttons, navigation, messages.
- **ISBN, ticket numbers, handover windows — monospace, tabular.** An ISBN-13
  is compared digit by digit against a physical book; proportional digits make
  that harder than it needs to be. This is the smallest decision in the
  document and probably the one that most changes whether a student catches a
  mismatch.
- **No webfont is loaded, in either direction.** On 3G a Tamil webfont is
  40–90 KB that buys nothing a student can perceive at 17px on a 2-year-old
  LCD. Both scripts render in the face their own platform hinted — Roboto and
  Noto Sans Tamil on Android (AOSP ships Noto Sans Tamil), Latha on older
  Windows. Zero bytes, no FOIT, no layout shift, and Tamil renders in a face
  designed for Tamil rather than in whatever a Latin webfont substitutes.
  *If* a display face is ever wanted, the rule is: one variable subset
  covering Latin + Tamil, ≤20 KB woff2, headings only,
  `font-display: optional` so it can never block the first render and can
  never shift the layout. Not in v1.

### 2.3 Tamil, as a type and layout problem rather than a string problem

Everything in this subsection applies to **both** directions and is
binding in whichever ships.

| Property of Tamil | Consequence | Where it is enforced |
|---|---|---|
| Stacked vowel signs above and below the baseline (ெ ொ ௌ) and deep descenders | Tamil body text needs ~1.70 line-height against Latin's 1.45. At 1.45 the marks collide with the line above on a small screen | `tokens.css` `--lh-tamil`, applied via `:lang(ta)` |
| Smaller optical size at the same em than Roboto | Tamil is set at 1.06em so the two scripts read at the same size | `tokens.css` `:root:lang(ta)` |
| UI labels run ~20–40% longer than English | **No fixed-width button, no fixed-height bar, no `text-overflow: ellipsis` on any control.** Buttons grow vertically; two-line buttons are normal, not a bug | `SYSTEM.md` §4.2 |
| No hyphenation; long compounds | `overflow-wrap: break-word` is a last resort, not a layout strategy. The real fix is shorter Tamil phrasing, which is a **copy** decision | `COPY-DECK.md` §1.3 |
| Letter-spacing breaks ligature rendering visually | `letter-spacing` is reset to `normal` under `:lang(ta)` | `tokens.css` |
| `text-transform: uppercase` is meaningless in Tamil | **Banned everywhere, both languages.** No ALL-CAPS buttons or labels | `SYSTEM.md` §3.2 |
| Tamil digits (௧௨௩) are not in everyday Chennai use | Western Arabic digits in both locales — **flagged for native review**, I am not certain and it affects prices and ISBNs | `COPY-DECK.md` §1.4, review item **TR-6** |
| A serif Tamil face is not reliably present on Android | The `--f-biblio` stack deliberately falls through to Noto **Sans** Tamil. A Tamil title in the correct sans beats a Tamil title in a substituted serif | `tokens.css` `--f-biblio` |

**Type choice for Tamil, stated plainly: the device's own Noto Sans Tamil, via
the system font stack, with no webfont.** If a future direction demands a
chosen face, my recommendation is **Anek Tamil** or **Mukta Malar** (both
Indian Type Foundry / Ek Type, both open-licensed, both with real Latin
companions) — but as a subset, headings-only, `font-display: optional`, and
not in v1.

### 2.4 Colour, with computed ratios

All ratios computed with the WCAG 2.x relative-luminance formula; the script
is reproducible and the whole table asserts zero failures. Full per-component
table in `SYSTEM.md` §3.3.

| Token | Hex | Role | Pair | Ratio | Bar | Verdict |
|---|---|---|---|---:|---:|---|
| `--c-paper` | `#FAF7F0` | page ground | — | — | — | — |
| `--c-card` | `#FFFFFF` | card ground | vs paper | 1.06:1 | n/a | decorative; boundary is a rule, never fill alone |
| `--c-ink` | `#1B1A14` | body text | on paper | **16.30:1** | 4.5 | pass |
| | | | on card | **17.44:1** | 4.5 | pass |
| `--c-ink-2` | `#55524A` | secondary text | on paper | **7.29:1** | 4.5 | pass |
| `--c-ink-3` | `#6B675C` | meta / timestamp | on paper | **5.28:1** | 4.5 | pass — this is the lightest text that ships |
| `--c-rule` | `#D9D3C4` | hairline | on paper | 1.40:1 | n/a | **decorative only**; never the sole indicator of a control |
| `--c-rule-strong` | `#8A8274` | input + control border | on paper | **3.55:1** | 3.0 | pass (SC 1.4.11) |
| | | | on card | **3.80:1** | 3.0 | pass |
| `--c-stamp` | `#2B3A8F` | link, primary fill, accent | on paper | **9.33:1** | 4.5 | pass |
| `--c-on-stamp` | `#FFFFFF` | primary button label | on stamp | **9.98:1** | 4.5 | pass |
| `--c-stamp-deep` | `#1E2A6B` | pressed | white on it | **13.14:1** | 4.5 | pass |
| `--c-alert` | `#96241B` | error text | on paper | **7.65:1** | 4.5 | pass |
| | | | on alert-bg | **7.23:1** | 4.5 | pass |
| `--c-alert-bg` | `#FBEEEC` | error panel | ink on it | **15.40:1** | 4.5 | pass |
| `--c-live` | `#1E6136` | available / confirmed | on paper | **6.96:1** | 4.5 | pass |
| | | | on live-bg | **6.57:1** | 4.5 | pass |
| `--c-wait` | `#6F4504` | pending / reserved / stale / offline | on paper | **7.76:1** | 4.5 | pass |
| | | | on wait-bg | **7.41:1** | 4.5 | pass |
| `--c-focus` | `#0B2E8A` | focus ring | on paper | **11.08:1** | 3.0 | pass |
| | | | on card | **11.85:1** | 3.0 | pass |

**Three colour rules that are part of the direction, not the palette:**

1. **One accent.** `--c-stamp` appears only where something is actionable or
   is a link. If indigo is on the screen, it can be touched. Status uses
   earth tints that are deliberately *quieter* than the accent, because a
   status is information and an action is an invitation.
2. **No colour carries meaning alone** (SC 1.4.1). Every state has a text
   label and a 4px left rail; the tint is the third signal, not the first.
   This is also what makes the forced-colours pass in `tokens.css` honest
   rather than cosmetic.
3. **No gradient, no shadow above a 1px rule, no tinted glass.** The single
   elevation token is `0 1px 0 0 var(--c-rule)`. Flat is cheaper to paint on a
   weak GPU and it is the opposite of the category's default styling.

### 2.5 How a listing is presented

```
┌──────────────────────────────────────────────┐
│ ●  Listed 3 days ago            Available   │  ← stamp dot + recency, status chip
├──────────────────────────────────────────────┤
│ Artificial Intelligence:                     │  ← serif, 19px, 2 lines max, no ellipsis on
│ A Modern Approach                            │     the title (it may truncate at 3 lines
│ Russell & Norvig                              │     with a visible "more" on detail only)
│                                               │
│ 4th edition · 2021 · Pearson                 │  ← THE EDITION LINE. 15.9px, ink, never grey.
│ ISBN 978-93-534-0000-5                        │  ← monospace, 15.9px. Tappable: "copy"
├──────────────────────────────────────────────┤
│ Seller's asking price                         │  ← label, --t-xs. NEVER the bare word "Price"
│ ₹280                                          │  ← 31.9px numerals, --lh-flat. The only 2xl
│                                               │     type on the page. No MRP, no struck-
│                                               │     through, no "was/now" (E-Com r.4(13))
│ This is what the seller is asking. The two    │  ← v1.1, REQUIRED: COMPLIANCE §4.3.1 trap (1).
│ of you agree the actual price between         │     The immutable asking price must not read
│ yourselves.                                   │     as the price paid. See SYSTEM §4.15
├──────────────────────────────────────────────┤
│ Condition, in the seller's words              │  ← attributed-claim header, --t-xs, ink-2
│ “Good — cover is bent, no writing inside,     │  ← the seller's text, in quotation marks,
│  pages 40–44 have pencil marks.”              │     in the serif. OUR voice never grades it.
│ BookHop hasn't checked this book.             │  ← SCOPED to the book (v1.2). The book
├──────────────────────────────────────────────┤     block ends here.
│ About this seller                             │  ← the second labelled block. The scope
│ Priya S · Mechanical, 3rd year · Guindy       │     label is what stops the next two
│ Signed in with a college email address.       │     sentences reading as a contradiction
│ That's all BookHop knows about them.          │  ← the qualifier sits immediately after the
│ We haven't checked who they are.              │     positive fact, never across the page
├──────────────────────────────────────────────┤     (SYSTEM §4.11, §4.11a)
│ ▢ ▢ ▢   Show 3 photos (about 45 KB)          │  ← under Save-Data: text link, bytes named.
│                                               │     Otherwise: three 320px thumbs, lazy,
│                                               │     width/height set so nothing shifts
├──────────────────────────────────────────────┤
│ [       Offer to buy this copy        ]      │  ← 56px, full width, --c-stamp
│  Check the book before you pay. Meet at a    │  ← guidance under the button, not a promise
│  named point on campus, in daylight.          │
└──────────────────────────────────────────────┘
```

**Why the book cover is subordinate.** Three reasons, in order of weight.
(a) A cover photo is 15–40 KB and cannot settle the one question that matters,
because the 3rd and 4th editions of a textbook routinely share cover art.
(b) A seller's photo of a cover is *their* evidence, and the direction's whole
posture is that evidence is attributed and secondary to the record.
(c) Bytes. The list view loads zero photos; photos appear on the detail page,
lazily, and under `Save-Data: on` they become a named, priced link the student
chooses to spend data on. A student who pays ₹20/GB (`DISCOVERY.md` §1.1
`[S]`) should never have us spend it for them.

**Search results** are the same record, shorter: title / edition line / ISBN /
asking price / recency / status. Seven facts, one row, no image, ~900 bytes of
HTML. Thirty results is a ~30 KB page.

### 2.6 What a book "cover" looks like when there is no photo

A generated spine, not a grey placeholder: a 3:4 block in `--c-rule` with the
title's first two words set in the serif, rotated, and the ISBN's last four
digits in monospace at the foot. It is pure CSS and text — no image request,
no layout shift, and it is recognisably *this* book rather than a missing-image
icon. This is the one place the direction permits itself a flourish, and it
costs zero bytes.

---

## 3. Direction B — "Daylight Meet", in detail

### 3.1 The idea

The product's actual failure mode is not a wrong edition — it is two people
who agreed and never met. The audit says the model dies of *silence*
(`COMPETITORS.md` §4.2, §4.6), and the open Red Team objection is about
whether a completion is ever *observed* (D-008 ruling 2). So this direction
treats the appointment as the product. The home screen is not a catalogue; it
is a single card that says **who you are meeting, where, when, and what you
have to do next.** Searching is a secondary mode reached by one button.

What it borrows is Tamil Nadu's public-notice visual culture rather than
print: the flat saturated field of a government notice board, the heavy
display type of a campus election poster, the plain who/where/when grid of a
bus-route board or an exam hall ticket. These are objects designed to be read
across a corridor by someone who is not concentrating — which is the real
reading condition at a handover.

### 3.2 Type

- **Tamil-led.** The Tamil string is set first and the component is sized to
  it; English takes the space Tamil needed. In practice this means every
  button is two lines tall, every label has 40% more room than English wants,
  and nothing truncates — because the longest string was the design input.
- **One family, two weights (400/700), large sizes.** Body starts at 19px, not
  17px. No serif anywhere; a heavy sans at 25–32px is the poster voice.
- Monospace only for the handover window.
- Same no-webfont rule as Direction A, for the same reason.

### 3.3 Colour, with computed ratios

| Token | Hex | Role | Pair | Ratio | Bar | Verdict |
|---|---|---|---|---:|---:|---|
| `ground` | `#F4F1EA` | page | — | — | — | — |
| `ink` | `#141414` | body | on ground | **16.33:1** | 4.5 | pass |
| `ink-2` | `#4A4A46` | secondary | on ground | **7.89:1** | 4.5 | pass |
| `slab` | `#0E3B2E` | the green notice field | on ground (as heading/icon) | **11.06:1** | 4.5 | pass |
| `slab-on` | `#FFFFFF` | text on slab | on slab | **12.47:1** | 4.5 | pass |
| `hot` | `#F0B429` | CTA fill | on slab (non-text) | **6.69:1** | 3.0 | pass |
| | | | on ground (non-text) | 1.65:1 | 3.0 | **FAILS as a bare fill** |
| `hot-on` | `#141414` | CTA label | on hot | **9.88:1** | 4.5 | pass |
| `slab` on `hot` | — | dark label on saffron | | **6.69:1** | 4.5 | pass |

**The honest note on that one failure, because it is the kind of thing that
gets quietly dropped:** my first saffron (`#C2410C`) failed 3:1 against the
green slab (2.41:1) and I changed it rather than reporting a pass. The
replacement (`#F0B429`) passes on the slab but is only 1.65:1 against the warm
ground, so **on the page ground the saffron button is only AA-compliant with a
1.5px `ink` border** (16.33:1), which supplies the boundary SC 1.4.11 requires.
That border is a condition of the direction, not a detail: a borderless
saffron button on this ground is a contrast failure and must not ship.

### 3.4 How a listing is presented

A listing in Direction B is a *line*, and the handover is a *card*:

```
┌──────────────────────────────────────────────┐
│████ TODAY, 4:30–5:00 PM ████████████████████│  ← slab field, 25.5px, white
│                                              │
│  Meet  Priya S                               │  ← 31.9px. The PERSON is the headline.
│  at    Library steps, Gate 2                 │  ← 25.5px, with a tiny plan sketch, not a map
│                                              │
│  You are collecting                          │  ← 14.9px label
│  AI: A Modern Approach, 4th ed · ₹280        │  ← ONE LINE. The whole book, as a line.
│                                              │
│  Check the book before you pay.              │
│                                              │
│  [        I got the book        ]            │  ← saffron, 56px, ink label, ink border
│  [  Something is wrong          ]            │  ← secondary, 48px
└──────────────────────────────────────────────┘
```

A search result is: title, edition, ₹, and the name of the person — four
things, 25px type, one per row, three results per screen. The edition is
present but it is a fragment of a sentence rather than a field in a record,
and **that is the direction's real cost**: a student cross-checking a syllabus
line cannot scan ten of these the way they can scan ten catalogue rows.

### 3.5 What it does better than A

- **First-run comprehension.** "Who, where, when, do this" is legible to a
  student who has never used a marketplace. A's record view assumes the
  reader knows what a catalogue entry is for.
- **It cannot be mistaken for any other marketplace.** Direction A's
  discipline is quiet; B's is loud, and loud is more defensible against the
  "any marketplace with the logo swapped" failure.
- **Tamil gets a real typographic role** rather than an equal-partner one.
  Tamil display type at 32px is genuinely beautiful and nobody in this
  category does it.
- **It points at the measurement problem.** If the thing we most need is for
  pairs to confirm in-app (D-008 ruling 2; `METRICS.md`), a design whose
  entire home screen is "confirm this" is the design that produces that data.

---

## 4. Recommendation: **Direction A — "Catalogue Card"**, with two things taken from B

### 4.1 The reasoning, in the order that decided it

**1. It is the only one of the two that can carry the trust posture we are
legally required to hold.** This is the deciding argument and it is not
aesthetic. We may not vouch. The whole-screen flat institutional colour field
in Direction B *is* vouching: a deep-green government-notice slab with white
display type reads as **the platform asserting something**, and the one thing
the platform must never appear to assert is that a classmate's book is as
described. Direction A's posture — a record that states who said what and
when, in their own words, in quotation marks — is the visual grammar of
*not* vouching. It is also, conveniently, 400 years old and understood
without instruction. §4.2 below is the full mechanism.

**2. It is the only one that makes the edition evidence scannable.** The one
wedge that survived Phase A is the whole-book, whole-semester need where the
edition matters (`DISCOVERY.md` §2.2(a), §3.3). A student holding a syllabus
line — *"Fourth Edition, Pearson Education, 2021"* — needs to compare it
against a listing in two seconds, and against ten listings in twenty. A
dedicated monospaced edition line in a dense record does that. B's
one-line-per-listing poster cannot, and no amount of type weight fixes it.

**3. It is cheaper over 3G, and the margin is not small.** A 30-result
Direction A page is ~30 KB of text with zero images. Direction B's
large-type, low-density layout needs 3–4× the scrolling for the same
information, and its colour fields invite the photo-forward treatment that
its sparseness would otherwise demand. Density is a data-cost strategy, not
just an information-design one.

**4. Recency and staleness have a native home in it.** A catalogue card has a
date stamp because a catalogue's whole problem is currency. The oldest known
failure mode of campus book exchanges is stale listings
(`COMPETITORS.md` §3.5), and A puts the stamp on every row for free. In B the
listing date is a detail with nowhere to live.

**5. It survives the "logo swapped" test better than it looks.** The first
instinct is that B is the distinctive one. But a bold flat poster UI is now a
commodity look; a genuinely bibliographic interface — serif title lines,
monospaced ISBNs, attributed quotations, an accession stamp, generated CSS
spines instead of cover images — is rarer and much harder to re-skin, because
its character is in the *information structure*, not in a colour.

### 4.2 The trust-without-warranting solution

This is the hardest copy problem in the product and Direction A is built
around it. Confidence comes from four mechanisms, none of which is a claim by
BookHop. Full strings in `COPY-DECK.md` §3; the principle is here because it
is a *design* decision before it is a copy one.

**(1) Attribution. Every human claim is a quotation with a name and a date on
it.** Condition is never rendered as a bare grade. `DATA-MODEL.md` L340 stores
`condition ∈ {AS_NEW, GOOD, FAIR, HEAVILY_USED}` and the CTO's own escalation
#4 flags that a bare grade reads as BookHop's endorsement. So the component
renders:

> **Condition, in the seller's words**
> "Good — cover is bent, no writing inside, pages 40–44 have pencil marks."
> — Priya S, 3 days ago

The grade is inside the quotation, in the seller's voice, in the serif, with
the attribution visible. The platform's voice is only the label. **This single
component closes the CTO's open escalation #4 and it is the most load-bearing
thing in this document.**

**(2) Checkable facts instead of adjectives.** Replace every reassuring
adjective with a verifiable mechanism the student can evaluate themselves:

| Banned instinct | What we show instead | Why it is not a warranty |
|---|---|---|
| "Verified seller" | "Signed in with a college email address." **+ immediately: "That's all BookHop knows about them. We haven't checked who they are."** | A statement about a mechanism that occurred, not a judgement about a person — and literally all our evidence is (`ADR-001` §2.5). **Ruled and approved, `COMPLIANCE.md` §2.5a.** The qualifier is not a retraction: a trust signal that states its own ceiling is the only kind we are allowed to ship, and against this category's background noise it is also the believable kind |
| "Verified listing" | "ISBN matches the catalogue entry for this edition" | A machine comparison of two strings, which is exactly what happened |
| "Safe handover" | "Library steps, Gate 2 · a point other students use" | A description of a place |
| "Make an offer of ₹X" (a numeric bid field) | "Tell Priya what you'd pay for it." — in a free-text message | **`COMPLIANCE.md` §4.3.3.** Inviting negotiation is permitted and recommended; *capturing* a number is not. Copy that **causes** negotiation is stronger evidence than copy that asserts it. **And the field is unbuildable, not merely unwanted** — `ADR-003` §2.3 item 4 |
| "Trusted" / "4.8★" | **nothing.** No ratings in v1 (`ADR-001` §6, R-16) | The absence is the honest position at one campus with no data |
| "100% guaranteed" | "BookHop hasn't checked this book. Look at it before you hand over any money." | The disclosure *is* the trust signal — see (4). **Scoped to the book in v1.2**, so it cannot read as contradicting the seller block |

**(3) Specificity as the actual confidence mechanism.** The finding behind
this is in the audit: students in this category have been trained that
confident platform claims are noise, because BookMandee's "10000+ verified
users" sits beside counters reading 0 and CampusXchange's "Trusted by 5,000+"
sits beside ₹0 (`COMPETITORS.md` §3.11, §4.5). Against that background,
**a listing that admits its own limits is more credible than one that
boasts.** "Pages 40–44 have pencil marks" is believable in a way that "Good
condition — verified!" is not, and it is believable *because* it volunteers a
defect. The design therefore rewards specificity: the seller's description
field is large, prompted field-by-field ("what is wrong with it?" is a
required question, not an optional one), and the listing shows how much the
seller actually told you.

**(4) Honest disclosure of what we do not do, placed where it is useful rather
than where it is defensive.** "BookHop hasn't checked this book" is not buried
in terms; it is on the listing, next to the offer button, in the same type
size as the rest — and its twin, "That's all BookHop knows about them. We
haven't checked who they are", sits directly under the sign-in fact in the
seller block. This is counter-intuitive and I want the reasoning on the
record: a platform that tells you it has not checked anything, *and in the
same breath tells you exactly what to check*, has given you something you can
act on. A badge gives you something you can only trust. The first is honest,
legally safe, and — against this category's background noise — more
persuasive.

**Each of those sentences names its own scope, which is a v1.2 change and not
cosmetic.** An unscoped "nothing here is checked" beside a sign-in fact reads
as the product arguing with itself, and compliance's observation is right
that *a contradiction in trust copy is worse than either string alone*
(`COMPLIANCE.md` §2.5a). Scoped and paired, each positive fact arrives with
its own ceiling attached — which is the strongest form of this mechanism, not
a weakening of it.

**The grammatical rule that keeps copy compliant, stated once so it can be
tested:** *BookHop's voice may describe a mechanism, name a fact, or give an
instruction. It may never make a prediction or a judgement about a person, a
book or an outcome.* Any string that fails that test fails review.
`COPY-DECK.md` §1.2 turns it into a checklist and
`tests/unit/test_forbidden_copy.py` (already specified in
`API-CONTRACT.md` §5.4) greps for the forbidden words; the grammatical rule
needs human review because a grep cannot catch "you'll be fine".

### 4.3 The two things taken from Direction B

Taking these is not hedging; A is weak in exactly two places and B is strong
in both.

1. **One decision per screen for the whole handover flow.** From the moment an
   offer is accepted, every screen asks one question and offers one primary
   action at 56px in the thumb zone. The transfer page's hero is the
   **who / where / when** block in B's layout, not a record. Rationale: this
   is the part of the product where a mistake is a person standing alone
   outside a library, and density is a liability there in a way it is an asset
   during search.
2. **The person is named before the book on the transfer page.** "Meet Priya S
   at Library steps, Gate 2" above the book line. A's instinct would lead with
   the record; B is right that at 4:25 PM nobody is checking an ISBN.

### 4.4 What we lose by not choosing Direction B

Stated plainly, because these are real and I expect at least two of them to
show up in the first user test.

1. **First-run comprehension for the student who is not app-fluent.** A's
   record view assumes the reader knows what a catalogue entry is *for*. B
   needs no such knowledge. **This is the single biggest risk in choosing A**,
   and `USER-TEST-PLAN.md` Task 1 and Probe P1 exist specifically to detect
   it. If first-run comprehension fails in testing, the mitigation is to adopt
   B's one-question-per-screen pattern for first-run too — not to repaint.
2. **Tamil's typographic role shrinks.** In A, Tamil is an equal second voice
   in a 15–19px interface; in B it would have been the 32px headline. That is
   a real loss of character and of respect, and the compensating commitment is
   in `COPY-DECK.md` §1.3: Tamil strings are written first and the layout is
   sized to Tamil, even though the type is small.
3. **Distinctiveness is quiet rather than loud.** A's identity is in
   structure. A casual observer will call it plain. The defence is that it
   cannot be re-skinned into a generic marketplace without destroying it,
   whereas a flat-colour poster UI can — but "quiet" is still a cost and a
   reviewer should name it.
4. **The confirmation metric loses its home-screen advocate.** B's homepage
   *is* "confirm this handover", which is the measurement D-008 ruling 2 says
   we most need. A's homepage is a search field. Mitigation: in A, any
   transfer in `SCHEDULED` or `AWAITING_CONFIRMATION` pins B's docket card
   above the search field on the home page. This is specified in
   `SYSTEM.md` §4.12 and it is not optional.
5. **A has no answer for the student who cannot read dense text comfortably**
   — low vision beyond what zoom fixes, low literacy, or just a cracked
   screen. Partial mitigation: the layout reflows to 320px at 200% zoom
   without horizontal scroll (SC 1.4.10), and nothing below 14.9px ships. Not
   a full answer. Logged as an open risk in `SYSTEM.md` §7.

### 4.5 What would make me change my mind

Pre-committed, before testing, so the decision cannot be rationalised later:

- **If ≥3 of 8 participants cannot complete Task 1 (find the right edition)
  unaided**, the density argument has failed on real devices and B's layout
  takes over the search surface, not just the handover.
- **If ≥2 of 8 participants, when asked Probe P1 ("what has BookHop promised
  you here?"), answer with any form of a warranty** — "they checked it", "they
  will give my money back" — the trust mechanism in §4.2 has failed. That is a
  copy and layout failure in A, and the first fix is to move the "nothing here
  is checked by BookHop" line above the fold, not to adopt B.
- **If the Tamil interface tests materially worse than the English one** on
  task success, the problem is the 15–19px Tamil body size, and B's larger
  type wins on that axis alone.

---

## 5. What each direction feels like on a mid-range Android over 3G

Honest engineering description of the recommended path, written against
`ADR-001` §2.3 (server-rendered HTML, htmx, no SPA, no build step) rather than
against an SPA we are not building. Numbers below marked `[E]` are my
estimates from the component specs, **not measurements** — nothing has been
built or profiled. Verifying them is `test-qa`'s item in `SYSTEM.md` §7.

### 5.1 Direction A

- **First view is a complete page, not a shell.** Search page = one `<form>`,
  a list of text records, inline critical CSS (~6 KB `[E]`), no images, no
  blocking script. htmx (~14 KB gzipped) is `defer`red and cached by the
  service worker; **the page is usable before it arrives**, because every
  control is a real form or link (`ADR-001` §2.3).
- **No webfont means no invisible text and no reflow.** The first paint has
  final metrics. On 3G this is the single largest perceived-speed decision in
  the document — a 60 KB font swap at 2.5 s is worse than anything else we
  could do wrong.
- **Scrolling never triggers a request.** Pagination is a "Show 30 more"
  button (cursor-based, per `API-CONTRACT.md` §2.3). Infinite scroll on a
  metered connection spends the student's money without asking.
- **Photos are a decision, not a default.** List view: zero images. Detail
  view: three 320px thumbs, `loading="lazy"`, explicit `width`/`height`.
  Under `Save-Data: on`: a text link that names the cost — "Show 3 photos
  (about 45 KB)".
- **An htmx swap looks like a swap.** The submit button becomes "Sending…"
  after 400 ms (`--m-indicator`), is disabled for the duration via
  `hx-disabled-elt`, and the swapped region gets focus moved into it.
  Under 400 ms nothing flashes at all. Full spec in `SYSTEM.md` §5.
- **When it fails it fails in place.** A 3G timeout (25 s, set explicitly —
  htmx has no default) re-renders an error *inside* the form, with everything
  the student typed still in it. The form is never replaced.
- **The honest bad case:** a search on a cold cache over a genuinely
  congested 3G link is one round trip, and one round trip on 3G is 1.5–3 s of
  latency before a byte of ours moves `[E]`. We cannot fix that, so the design
  does not pretend otherwise — it shows a determinate "Searching…" in the
  results region with the previous results still on screen beneath it, greyed
  and labelled as previous. Partial, not blank. That is the `partial` state in
  `SYSTEM.md` and it is why `partial` is a real state and not a nicety.

### 5.2 Direction B

Lighter per screen but heavier per task: 3–4× the scroll depth for the same
information means more screens, and more screens over htmx means more round
trips. The large flat colour fields are nearly free (solid fills), but the
sparseness pushes toward a photo per card to fill the space, and that is where
the bytes would go. On a slow link B *feels* calmer and *costs* more, because
calm came from showing less per request.

---

## 6. What is banned in both directions, with the reason

| Banned | Why |
|---|---|
| Any trust, safety or verification badge | `COMPLIANCE.md` §2.5 via `API-CONTRACT.md` §5.4; and D-004 means we have nothing to back it with |
| Social-proof counters ("5,000+ students", "20k books listed") | The category's signature tell, and at one campus any such number would be a lie or a seed count (`COMPETITORS.md` §3.11, §4.5) |
| Star ratings, reputation scores, review text | `ADR-001` §6, R-16. Not built in v1 |
| MRP, struck-through prices, "was/now", "% off" | E-Com r.4(13) via `API-CONTRACT.md` §5.3; and no settled price exists to compare against (P14) |
| **The bare label "Price"; "pay the listed price", "fixed price", "non-negotiable", "final price"** | **New in v1.1.** `COMPLIANCE.md` §4.3.1 trap (1): because P14 makes the asking price immutable, presenting it as *the* price weakens the limb of CBDT Circular 20/2021 that keeps us outside a withholding obligation. **This limb lives in copy because the schema cannot carry it.** `SYSTEM.md` §4.15, `COPY-DECK.md` §1.6 |
| **Any numeric offer, counter-offer or bid control; any rupee amount in a notification** | Same source, trap (2): a structured offer amount **is** a settled consideration. Negotiation happens in free-text messages only |
| Any money affordance — wallet, fee, escrow, "pay in app" | D-004, ADR-003. There is no money in the product |
| A dashboard of metrics for the student | Charter ban. A student needs one next action, not a chart |
| Gradients, glassmorphism, tinted shadows, hero illustrations | Charter ban. Also bytes and GPU on a cheap phone |
| Decorative motion anywhere in a transaction path | Charter ban. `--m-fast` (120 ms) exists only for a state-change tint |
| Skeleton shimmer animation | A shimmer is a decorative animation that specifically delays comprehension. We use a static reserved block with "Loading…" text |
| Infinite scroll | Spends metered data without consent |
| Carousels, modals over forms, bottom sheets that trap focus | SC 2.4.11, SC 2.1.2; and all three are worse than a page on a 5-inch screen |
| ALL-CAPS labels and buttons | Meaningless in Tamil; and `text-transform` on Tamil is a rendering hazard |
| Toast notifications as the only feedback | Transient, easily missed, and badly handled by TalkBack. Feedback is inline and persistent |
| Any AI feature | Charter ban. Nobody asked |
| A promoted or sponsored listing slot | E-Com r.4(12) via `API-CONTRACT.md` §5.3 — no personalisation, no promoted placement |

---

## 7. Open questions I am escalating rather than deciding

1. **To `product-manager` — the four condition grades.** The attributed-claim
   component in §4.2(1) makes a bare grade safe to show *inside a quotation*,
   but the four-value enum is still BookHop's vocabulary applied to someone
   else's book. My recommendation is to keep the enum for filtering and
   **never render the bare grade outside the seller's own quoted sentence**.
   This closes CTO escalation #4 in `DATA-MODEL.md` §4 if Product agrees.
2. **To `product-manager` — "worth your while".** Decided in
   `COPY-DECK.md` §1.5 as a deletion, not a translation, with a general rule
   attached. Flagged here because it is a product-voice decision, not only a
   copy one.
3. **✅ CLOSED v1.2 — "Signed in with a college email address" ships.**
   `COMPLIANCE.md` §2.5a confirmed my §1.2 reading on vouching and added three
   disclosure conditions, all implemented (`SYSTEM.md` §4.11a, criteria
   7f–7h). **The round trip earned its cost on condition 3**, which neither I
   nor compliance's v1.1 had seen: a student who came through the
   staff-assisted re-verification path is `campus_verified = true` and did
   **not** sign in with a college email address, so an un-gated string would
   have published a false statement about a person — in production, for
   exactly the users least able to notice, passing every happy-path review.
   That is the case for not reading silence as approval, and it is worth
   keeping on the record. `COPY-DECK.md` §12 item 1, §3.2.
4. **To `ceo-planning` / founder — the user test is unfunded.**
   `USER-TEST-PLAN.md` §7 costs ₹2,400–3,600 in incentives against ₹2,600
   unallocated (D-008 ledger). A ₹0 variant is specified. **No spend is
   committed by this document.**
5. **To `test-qa` — the performance claims in §5.1 are estimates `[E]`.** They
   need measuring on a real mid-range Android over a throttled 3G profile
   before anyone cites them.
6. **✅ CLOSED v1.3 — the schema guard exists and is stronger than my ask.**
   `ADR-003` §2.3 item 4 forbids the **patterns** `%offer%amount%`,
   `%offered_price%`, `%counter%price%`, `%bid%`, `%negotiat%`,
   `%accepted_price%`, `%deal%`; `%agreed_price%` is caught by the
   settled-consideration row; `THREAT-MODEL.md` §9 holds the whole control as
   a **whitelist**. Verified by reading those files. I had asked for four
   column names added to a deny-list; patterns beat a name list, and a
   whitelist beats both. **The §6 banned-list row below should be read
   accordingly: the design forbids a bid field, and the schema makes it
   unbuildable.**
7. **✅ CLOSED v1.3 — the `handover-guidance` rename.** Amendment **A-7**.
   See `SYSTEM.md` §7.7 for the pattern worth keeping: the forbidden-copy test
   guards strings, so the identifiers that *generate* strings need guarding by
   naming.

**The open list, in full, is now two items — and neither is a design
decision:** a named native Tamil speaker (§7.2, `COPY-DECK.md` §12 item 4),
and the user test, which is unrun, unfunded and zero-participant (§7.4).

---

## 8. Amendment log

| Version | Date | Change |
|---|---|---|
| v1.0 | 2026-10-21 | Two directions, recommendation of A, the trust-without-warranting mechanism, Tamil type decision, 3G behaviour, banned list, five escalations |
| **v1.3** | **2026-10-21** | **Escalations 6 and 7 closed after reading `ADR-003`, `THREAT-MODEL.md`, `API-CONTRACT.md`, `DATA-MODEL.md` and `TASKS.md` directly.** The no-bid-field rule is enforced in the schema as patterns under a whitelist, so §6's banned row is backed by an unbuildable column rather than by design discipline. The open list is now exactly two items, neither of them a design decision |
| **v1.2** | **2026-10-21** | **Both compliance rulings implemented.** §2.5 listing anatomy restructured into a **book block and a seller block**, with the sign-in fact and its qualifier adjacent — the adjacency fix compliance flagged and left to design. §4.2(2) updated: the trust table now carries the approved string plus its ceiling-stating qualifier, and a row rejecting a numeric bid field in favour of a free-text invitation. §7.3 closed, with condition 3 recorded as the reason the escalation was worth making |
| **v1.1** | **2026-10-21** | **Negotiability added on instruction from `COMPLIANCE.md` §4.3.1** — the §2.5 listing anatomy relabelled to "Seller's asking price" with the negotiability sentence, two rows added to §6's banned list, escalation 6 added. `trust.campus_mail` recorded as **blocked pending a compliance ruling** in §4.2(2) and §7.3; compliance's silence is explicitly not treated as approval |
