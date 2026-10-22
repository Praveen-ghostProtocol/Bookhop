# SYSTEM.md — BookHop design system (Direction A, "Catalogue Card")

**Owner:** `design-director` · **Version:** v1.0 · **Date:** 2026-10-21
**Phase:** B · **Handoff:** `frontend-developer` (implementation),
`test-qa` (verification), `product-manager` (experience sign-off)
**Normative token file:** `design/tokens.css` — this document explains it;
that file is what ships. It replaces the provisional token file in
`ADR-001` §2.3 / §7.3.

> **Scope note.** This specifies the system for the **recommended** direction
> only (`DIRECTIONS.md` §4). Direction B is not specified to build level.
>
> **The states are the system.** A component is not specified until every
> state in §2.2 is specified for it, including the ones that mean "nothing
> happened" and "we do not know". §4 therefore reads as a long list of
> failure modes, which is the correct shape for a product that runs on an
> intermittent connection.

---

## 1. The eleven rules

Everything else in this document is an application of one of these. If a
build decision is not covered below, apply these in order.

1. **Every core flow works with JavaScript off.** Real `<form>`s, real
   `<a>`s, real page loads. htmx is an enhancement that is allowed to fail
   (`ADR-001` §2.3).
2. **Nothing tappable is under 44px**, and adjacent targets are at least 8px
   apart. The WCAG 2.2 floor (SC 2.5.8) is 24px; the charter sets 44px and
   that is the number we hold.
3. **No colour carries meaning alone** (SC 1.4.1). Every state = a text
   label + a 4px rail + a tint, in that order of importance.
4. **Nothing below 14.9px (`--t-xs`) renders**, and `--t-xs` is for labels and
   timestamps only, never prose.
5. **No webfont, no gradient, no shadow deeper than a 1px rule, no shimmer, no
   decorative motion in a transaction path.**
6. **BookHop's voice may describe a mechanism, name a fact, or give an
   instruction — never a prediction or a judgement.** The trust rule from
   `DIRECTIONS.md` §4.2, enforced in review and partly by
   `tests/unit/test_forbidden_copy.py`.
7. **Every human claim is rendered as an attributed quotation**, never as a
   platform fact. §4.14.
8. **Bytes are the student's money.** Zero images in list views; images lazy
   and dimensioned on detail; under `Save-Data: on` images become a link that
   names its cost.
9. **Never show an optimistic state for a server transition.** The UI shows
   the last state the server confirmed. §5.4.
10. **The layout is sized to the Tamil string, not the English one.** §3.2.
11. **A rupee figure is always the seller's asking price, never "the price",
    and there is no numeric amount input anywhere in the product.** §4.15.
    New in v1.1 on instruction from `COMPLIANCE.md` §4.3.1: this rule carries
    a limb of the tax position and the schema cannot carry it.

---

## 2. Foundations

### 2.1 Breakpoints — two, and the small one is the design target

| Name | Width | Treatment |
|---|---|---|
| `base` | 320–599px | **The design target.** Single column, 16px gutter, sticky bottom action bar on transaction pages |
| `wide` | ≥600px | Content column capped at 36rem, centred. Action bar becomes inline. No new layout, no sidebar, no grid |

There is no desktop design. A 36rem column on a laptop is correct and
finished. At 320px and 200% zoom the layout must reflow with **no horizontal
scroll** (SC 1.4.10) — the one hard layout acceptance test.

### 2.2 The state vocabulary — eight states, used with these exact names

Every component in §4 is specified against these. Where one cannot occur, the
component says so **and why**; silence is not specification.

| State | Means | Rule that cannot be waived |
|---|---|---|
| `default` | Server-confirmed content, current | — |
| `empty` | The request succeeded and there is genuinely nothing | Must name the reason and offer exactly one next action. Never an illustration |
| `loading` | A request is in flight and we have nothing to show yet | Static reserved block + text. No shimmer. Reserve the final height to avoid shift |
| `partial` | A request is in flight and we still have the **previous** content | Previous content stays visible, dimmed to `--c-ink-2`, labelled "Previous results — updating". **This is why `partial` exists: a blank screen on 3G is worse than stale data honestly labelled** |
| `error` | The server answered with a failure, or the request failed | Renders **inside** the component, never replacing a form. Says what happened, what to do, and keeps every typed value |
| `offline` | The device reports no connection, or the fetch failed at the network layer | Distinguished from `error` because the action is different: wait, don't retype. Shows cached content with its age |
| `stale` | Content is from cache or is older than its own validity | Shows an absolute time ("as of 4:12 PM") plus a reload control. Never a relative-only time, which hides age |
| `disabled` | Action is not available right now | Must be accompanied by a visible reason in text. **A disabled control with no stated reason is a defect** |

Plus two interaction states on every control: `focus` (§2.5) and `pressed`.
And one page-level state unique to this product: `gate-closed` (§4.22),
because `assert_discovery_open(campus)` can refuse every discovery call
(`API-CONTRACT.md` §5.3).

### 2.3 Type scale

`html { font-size: 106.25%; }` — a percentage, so 1rem = 17px by default
**and the student's own Android font-size setting still scales it.** Never
set a px font-size on `html`.

| Token | rem | ~px | Used for | Line-height |
|---|---|---:|---|---|
| `--t-xs` | 0.875 | 14.9 | Field labels, timestamps, byte costs, attribution lines. **Never prose.** | `--lh-text` |
| `--t-sm` | 0.9375 | 15.9 | Dense meta inside a card: the edition line, ISBN, status chip text | `--lh-text` |
| `--t-base` | 1 | 17 | Body, form inputs, button labels, messages | `--lh-text` / `--lh-tamil` |
| `--t-md` | 1.125 | 19.1 | Catalogue card title (serif), the one question on a one-question screen | `--lh-tight` |
| `--t-lg` | 1.3125 | 22.3 | Section `h2`, the person's name on a transfer docket | `--lh-tight` |
| `--t-xl` | 1.5 | 25.5 | Page `h1`, the handover window | `--lh-tight` |
| `--t-2xl` | 1.875 | 31.9 | **The asking price, and nothing else.** One instance per page, maximum | `--lh-flat` |

Form inputs are `--t-base` (17px) and never smaller — a sub-16px input makes
iOS Safari zoom the page on focus, and on Android it is simply hard to read.

Weights: **400 and 700 only.** 500/600 are skipped because the system Tamil
face frequently lacks them and Android synthesises intermediate weights badly;
a synthesised Tamil semibold has visibly broken ligature joins.

### 2.4 Spacing, and the one rule about it

The ten steps in `tokens.css` §3. The page gutter is `--s-4` (16px) at every
width — a 320px screen with an 8px gutter reads as broken, and a thumb
resting on the bezel hits a control.

`body { scroll-padding-bottom: var(--s-18); }` — 72px, so that when a sticky
bottom action bar is present, focusing a field near the bottom of a form never
leaves it underneath the bar. **This is SC 2.4.11 (Focus Not Obscured
(Minimum), new in WCAG 2.2) and it is the requirement most easily lost the
first time someone adds a sticky bar.**

### 2.5 Focus — one indicator, everywhere, no exceptions

```css
:focus-visible {
  outline: var(--bw-focus) solid var(--c-focus);   /* 3px, #0B2E8A */
  outline-offset: 2px;
  border-radius: inherit;
}
/* On a stamp-coloured button the ring needs a light halo to stay visible */
.btn--primary:focus-visible {
  outline-color: var(--c-focus-inner);             /* white, 11.85:1 vs the ring */
  box-shadow: 0 0 0 calc(var(--bw-focus) + 2px) var(--c-focus);
}
```

- Ratio: `--c-focus` is **11.08:1** on `--c-paper` and **11.85:1** on
  `--c-card`. The SC 1.4.11 bar is 3:1. We are not close to the line.
- `outline: none` is **forbidden** in the codebase. `test-qa` should grep for
  it as a hard failure.
- `:focus-visible`, not `:focus`, so a mouse/touch press does not paint a ring
  — but **keyboard and switch-control users always get one**.
- 3px + 2px offset means the ring is ≥2px thick and encloses the control,
  which also satisfies SC 2.4.13 (Focus Appearance, AAA) in most cases. We are
  not claiming AAA; we are noting we get it cheaply.

### 2.6 Document structure, every page

```html
<a class="skip" href="#main">Skip to content</a>
<header>  … campus name · language switch · Help …   </header>
<main id="main" tabindex="-1">  <h1>…</h1>  …  </main>
<footer>  … Help · Privacy · Terms · Grievance officer · Report …  </footer>
```

- **Exactly one `<h1>` per page**, and it names the page, not the brand.
- Heading levels never skip.
- **The Help link is in the same place in the footer on every single page**
  — SC 3.2.6 (Consistent Help, new in WCAG 2.2). It is the only mechanism we
  have for a student who gets stuck mid-handover.
- Landmarks are real elements, not ARIA roles on `<div>`s.
- `<html lang="en">` or `lang="ta"` set server-side from the account locale;
  any inline string in the other language carries its own `lang` attribute, so
  TalkBack switches voice instead of reading Tamil with an English engine.

### 2.7 Accessible authentication — satisfied by the stack, worth stating

`ADR-001` §2.5 chose an emailed magic link. That means there is **no password
and no cognitive function test at sign-in**, which satisfies SC 3.3.8
(Accessible Authentication (Minimum), new in WCAG 2.2) by construction rather
than by exception. Do not add a CAPTCHA, a puzzle, or a "type the code from
the email" step — a typed code *is* a cognitive function test and would break
this. Rate limiting (`API-CONTRACT.md` §2.4) is the abuse control; it is
server-side and invisible.

Also satisfied by construction: **SC 2.5.7 Dragging Movements** — there is no
drag anywhere in v1 (no reorderable photos, no sliders, no swipe-to-dismiss).
**SC 3.3.7 Redundant Entry** — the campus email, the handover point and the
book identity are never re-asked within a flow; the handover point picker
pre-selects the point used last.

---

## 3. Colour, verified

### 3.1 How these were produced

Computed with the WCAG 2.x relative-luminance formula. The calculator asserts
zero failures across all 27 Direction A pairs and will fail loudly if a token
is edited into non-compliance. **`test-qa` should port this assertion into the
test suite** so a future token change cannot silently break AA.

### 3.2 Text pairs — bar 4.5:1 (we use no large-text exemption anywhere)

We deliberately do **not** rely on the 3:1 large-text exemption, so no
component breaks when a student scales text down or when Tamil renders at a
different optical size.

| Foreground | Background | Ratio | Verdict | Used by |
|---|---|---:|---|---|
| `--c-ink` `#1B1A14` | `--c-paper` `#FAF7F0` | **16.30:1** | pass | all body text |
| `--c-ink` | `--c-card` `#FFFFFF` | **17.44:1** | pass | card text |
| `--c-ink-2` `#55524A` | `--c-paper` | **7.29:1** | pass | labels, secondary prose |
| `--c-ink-2` | `--c-card` | **7.80:1** | pass | card meta |
| `--c-ink-3` `#6B675C` | `--c-paper` | **5.28:1** | pass | timestamps, attribution, byte costs. **Lightest text that ships** |
| `--c-stamp` `#2B3A8F` | `--c-paper` | **9.33:1** | pass | links |
| `--c-stamp` | `--c-card` | **9.98:1** | pass | links on cards |
| `--c-on-stamp` `#FFFFFF` | `--c-stamp` | **9.98:1** | pass | primary button label |
| `--c-on-stamp` | `--c-stamp-deep` `#1E2A6B` | **13.14:1** | pass | primary button, pressed |
| `--c-alert` `#96241B` | `--c-paper` | **7.65:1** | pass | error text |
| `--c-alert` | `--c-alert-bg` `#FBEEEC` | **7.23:1** | pass | error text in panel |
| `#FFFFFF` | `--c-alert` | **8.19:1** | pass | destructive button label |
| `--c-ink` | `--c-alert-bg` | **15.40:1** | pass | prose in an error panel |
| `--c-live` `#1E6136` | `--c-paper` | **6.96:1** | pass | "Available", "Confirmed" |
| `--c-live` | `--c-live-bg` `#EAF3EC` | **6.57:1** | pass | chip text |
| `--c-ink` | `--c-live-bg` | **15.38:1** | pass | prose in a live panel |
| `--c-wait` `#6F4504` | `--c-paper` | **7.76:1** | pass | "Reserved", "Offline", "As of…" |
| `--c-wait` | `--c-wait-bg` `#FBF1DF` | **7.41:1** | pass | chip text |
| `--c-ink` | `--c-wait-bg` | **15.57:1** | pass | prose in a wait panel |

### 3.3 Non-text pairs — bar 3:1 (SC 1.4.11)

| Element | Colour | Against | Ratio | Verdict |
|---|---|---|---:|---|
| Input / select / textarea border | `--c-rule-strong` `#8A8274` | `--c-paper` | **3.55:1** | pass |
| Same, on a card | `--c-rule-strong` | `--c-card` | **3.80:1** | pass |
| Secondary button border | `--c-rule-strong` | `--c-paper` | **3.55:1** | pass |
| Focus ring | `--c-focus` `#0B2E8A` | `--c-paper` | **11.08:1** | pass |
| Focus ring | `--c-focus` | `--c-card` | **11.85:1** | pass |
| Focus ring halo | `--c-focus-inner` `#FFFFFF` | `--c-focus` | **11.85:1** | pass |
| Control glyph (chevron, close ×) | `--c-stamp` | `--c-paper` | **9.33:1** | pass |
| State rail (4px) | `--c-live` / `--c-wait` / `--c-alert` | `--c-paper` | 6.96 / 7.76 / 7.65 | pass |

### 3.4 Pairs that are decorative, declared so they cannot be mistaken for failures

| Pair | Ratio | Why it is exempt |
|---|---|---|
| `--c-rule` `#D9D3C4` on `--c-paper` | 1.40:1 | A hairline that separates content. It is **never** the boundary of a control and never the only indicator of anything. Every control has `--c-rule-strong` or better |
| `--c-card` on `--c-paper` | 1.06:1 | Card fill. The card's boundary is its top rule, not its fill |
| `--c-alert-bg` / `--c-live-bg` / `--c-wait-bg` on `--c-paper` | 1.06 / 1.07 / 1.07:1 | Panel fills. Each panel carries a 4px rail in its state colour (≥6.9:1) which is the actual boundary |

### 3.5 What state colour means, so it is used consistently

| Tint | Meaning | Never used for |
|---|---|---|
| `--c-live` green | A fact that is settled and good: listing available, message sent, handover confirmed | "Verified", or any quality judgement — see §4.14 |
| `--c-wait` amber-brown | Time is involved and the outcome is open: reserved, awaiting confirmation, offline, stale, loading | Errors. A slow connection is not the student's mistake |
| `--c-alert` red | Something failed, or a destructive action | Warnings about other people. We do not flag students to each other |
| `--c-stamp` indigo | **Actionable.** Links and the primary action, nothing else | Status. If it is indigo it can be touched |

### 3.6 No dark theme in v1 — the decision and its trigger

A second palette is a second full verification pass: 27 pairs, re-computed,
re-tested in TalkBack and in forced-colours mode. Against that cost:
`--c-paper` at 16.30:1 is already the better choice in Chennai daylight,
which is where a campus handover happens, and a mid-range LCD gains no battery
from dark pixels.

`tokens.css` is structured so a dark theme is a token override and nothing
else, and it already includes a `forced-colors` block so the high-contrast
modes a student may actually be using are handled today.

**Add a dark theme when:** user testing shows participants have system dark
mode on and report the light UI as uncomfortable, **or** a second campus
reports it. Not before — and when it is added, §3.2–§3.4 are recomputed in
full, not spot-checked.

---

## 4. Components, and every state of each

Format for each: what it is, its anatomy, then a state table. `N/A` always
carries a reason.

### 4.1 Page shell

Header: campus name (text, not a logo lockup), language switch (`EN | தமிழ்`,
two links, 44px each, `rel="alternate" hreflang`), Help. Footer: Help ·
Privacy · Terms · Community rules · Handover guidance · Grievance officer ·
Report. Footer links are identical and identically ordered on every page
(SC 3.2.6).

| State | Specification |
|---|---|
| `default` | As above |
| `empty` | N/A — the shell always has content |
| `loading` | N/A — server-rendered; the shell arrives with the page |
| `partial` | N/A |
| `error` | 4xx/5xx render the same shell with an `error` notice in `<main>`. **Never a bare framework error page** — a 500 still shows the footer, because the grievance-officer contact is a regulatory requirement (`API-CONTRACT.md` §5.1) and an outage is exactly when someone needs it |
| `offline` | Service-worker `/offline` page uses the same shell; footer links that need the network are rendered as plain text with "needs a connection" |
| `stale` | N/A |
| `disabled` | N/A |

### 4.2 Button

Variants: `primary` (stamp fill), `secondary` (transparent, `--c-rule-strong`
1.5px border), `destructive` (alert fill), `quiet` (text + underline).

- Heights: `--tap-action` 48px default; `--tap-commit` 56px for the one
  irreversible action on a page; never below `--tap-min` 44px.
- Full width at `base`. **Height grows for two lines of Tamil** — `min-height`
  not `height`, `white-space: normal`, no `text-overflow`.
- `text-transform` is never set.
- One primary button per screen. If a screen needs two, it is two screens.

| State | Specification |
|---|---|
| `default` | Label is a verb phrase naming the effect: "Offer to buy this copy", not "Submit" |
| `empty` | N/A |
| `loading` | Label swaps to the progressive form ("Sending…") **after 400 ms** (`--m-indicator`); `aria-busy="true"`; `hx-disabled-elt="this"` prevents a second submit; width does not change (reserve the longer label's width). Under 400 ms nothing visibly happens |
| `partial` | N/A |
| `error` | Button returns to `default` and is re-enabled. The message appears in the form's error slot (§4.6), not on the button |
| `offline` | Label unchanged, but on submit the form's error slot says the request did not leave the phone and the typed values are kept. The button is **not** disabled — a student may regain signal and tap again |
| `stale` | N/A |
| `disabled` | `disabled` attribute **plus** a visible sentence immediately below saying why ("Add at least one photo first"). A silent disabled button is a defect |
| `focus` | §2.5. On `primary`, the white-halo variant |
| `pressed` | `primary` → `--c-stamp-deep`; others → 1px inset. No transform, no scale |

### 4.3 Link

`--c-stamp`, **always underlined** (colour alone is not an indicator —
SC 1.4.1). Inline links in prose get `text-underline-offset: 2px` so Tamil
descenders are not crossed out by the underline. A link that is a 44px row
has the whole row as its hit area. External links say so in text, never only
with an icon.

| State | Specification |
|---|---|
| `default` / `focus` / `pressed` | As above; `pressed` darkens to `--c-stamp-deep` |
| `loading` | A link that triggers an htmx swap gets `aria-busy` on its target region, not on itself |
| `disabled` | N/A — a disabled link is rendered as plain text with the reason beside it. There is no disabled `<a>` |
| others | N/A — links have no content state of their own |

### 4.4 Form field

`<label>` above the control, always visible, never a placeholder-as-label.
Input 48px min, 17px text, `--c-rule-strong` 1.5px border, `--r-sm`.
Hint text below the label, above the input, `--t-xs` `--c-ink-3`.
`aria-describedby` wires hint and error to the input.

**Cheap-keyboard behaviour, which is a real constraint and not a nicety:**

| Field | Attributes | Why |
|---|---|---|
| Campus email | `type="email" inputmode="email" autocomplete="email" autocapitalize="off" autocorrect="off" spellcheck="false"` | Android keyboards capitalise and autocorrect the first word of an email field by default and students then cannot sign in. All four must be off |
| ISBN | `inputmode="numeric" pattern="[0-9Xx\- ]*" autocomplete="off" maxlength="17"` | A numeric pad, but `type="text"` — `type="number"` strips hyphens, shows spinners, and loses leading zeros |
| Asking price | `type="text" inputmode="numeric" pattern="[0-9]*"` with a `₹` prefix rendered outside the input | Same reasons; and the prefix must not be inside the value |
| Date of birth (age gate) | `<input type="date">`, native (`ADR-001` §2.3) | Native picker, no library, already localised by the OS |
| Condition description | `<textarea rows="4">`, `enterkeyhint="enter"` | Multi-line; Enter must insert a newline, not submit |
| Handover window | two `<select>`s (day, time band), not a free text time | A time picker on a cheap keyboard is a failure path |
| Search | `type="search" enterkeyhint="search" autocomplete="off"` | Gives the keyboard a Search key instead of a newline |

`autofocus` is used **once** in the product — the email field on the sign-in
page — and nowhere else, because an unexpected keyboard eats half a small
screen.

| State | Specification |
|---|---|
| `default` | As above |
| `empty` | Only meaningful for optional fields: hint reads "Optional". Required fields carry "Required" in the label text, not an asterisk — an asterisk is unreadable to a screen reader without extra wiring |
| `loading` | Only the ISBN/title typeahead: a `--t-xs` "Looking up…" line below the input after 400 ms, in a `aria-live="polite"` region. **The input is never disabled while looking up** — the student keeps typing |
| `partial` | Typeahead shows the previous suggestions dimmed with "Previous matches — updating" |
| `error` | 1.5px `--c-alert` border, `aria-invalid="true"`, and the message in the field's own error slot: what is wrong **and** what to do ("That ISBN is 12 digits. An ISBN-13 has 13 — check the number under the barcode"). **The typed value is never cleared** |
| `offline` | Typeahead silently degrades to the manual-entry path with a `--c-wait` line: "Can't look that up right now — type the title and we'll match it later" |
| `stale` | N/A |
| `disabled` | As §4.2: visible reason required |
| `focus` | §2.5 |

### 4.5 Photo upload row — specified in full because it is the most likely thing to fail

`<input type="file" accept="image/*" capture>` (native, `ADR-001` §2.3), max 4
files, ≤8 MB each (`API-CONTRACT.md` §5.2). **Files upload one at a time,
sequentially, each to `POST /sell/{id}/photos` — never as one multi-file
request.** On 3G a 4-file request that dies at 90% loses all four; four
requests lose one.

Each selected file gets its own row: filename (truncated from the middle,
never the extension), size in KB, and a state.

| State | Specification |
|---|---|
| `default` | Zero rows. Control reads "Add photos (up to 4)" + hint "A photo of the cover and one of the worst page helps a buyer decide." |
| `empty` | After publishing with no photos: "No photos. Buyers will only have your description." Not an error — photos are not required |
| `loading` | Per row: `--c-wait` rail, "Uploading… 1 of 3", and a **determinate** progress element driven by `XMLHttpRequest.upload.onprogress` (htmx exposes `htmx:xhr:progress`). A determinate bar matters here: on 3G an indeterminate spinner for 40 s is indistinguishable from a hang |
| `partial` | Two of three uploaded: the two show `done`, the third shows `loading`, and the publish button is **enabled** with the line "2 of 3 photos attached" |
| `error` | Per row, `--c-alert` rail: "Didn't upload — [Try again]". The row keeps the chosen file so Retry does not re-open the picker. After 3 failures the row offers **"Publish without this photo"**. **Crucially: the listing row already exists as a draft before any photo is sent**, so the typed description, price and ISBN are never at risk from a photo failure |
| `offline` | All queued rows show `--c-wait` "Waiting for a connection". No retry loop that burns battery — one retry on `online` event, then a manual button. Offline *writes* are explicitly out of scope (`ADR-001` §6), so we never pretend a queued photo is saved |
| `stale` | N/A |
| `disabled` | After 4 files: control disabled with "Maximum 4 photos" beside it |
| `focus` / `pressed` | §2.5 / §4.2 |

Server-side (for `frontend-developer`'s awareness, since it changes the UI
copy): EXIF is stripped before the row exists and images are re-encoded to a
1600px max edge (`ADR-001` §2.6). The upload hint therefore says "We remove
the location and camera information from your photos" — a mechanism
statement, which is permitted; not "your photos are safe", which is not.

### 4.6 Form error slot

Every `<form>` has one reserved region immediately below the `<h1>` or legend:
`<div id="form-errors" role="alert" aria-atomic="true">`. It holds a summary
with in-page links to each failing field. Field-level messages also render
beside their field (§4.4 `error`).

| State | Specification |
|---|---|
| `default`/`empty` | Rendered but empty, with **height reserved** so appearing errors do not shift the form |
| `error` | `--c-alert-bg` panel, 4px `--c-alert` rail, heading "2 things to fix", then links. Focus moves to this region on an htmx error response; on a full page post the server renders it and `autofocus` is **not** used — the `role="alert"` announces it |
| `offline` | Same panel in `--c-wait`: "This didn't reach BookHop. Nothing was lost — tap Send again when you have signal." |
| others | N/A — an error slot has no other content |

### 4.7 Notice banner

Page-level message. Variants `info` (`--c-rule` rail), `error`, `offline`,
`stale`, `gate-closed`. 4px left rail + text label + tint, per rule 3.

| State | Specification |
|---|---|
| `default` | N/A — a banner is always in one of the variants below |
| `error` | `--c-alert` rail + `--c-alert-bg`. States the failure and the next action |
| `offline` | `--c-wait` rail. "No connection. This is what we had at 4:12 PM." Includes a Reload button |
| `stale` | `--c-wait` rail. Absolute time, never "2 hours ago" alone, plus Reload |
| `gate-closed` | `--c-wait` rail. §4.22 |
| `loading` / `partial` / `empty` / `disabled` | N/A — the banner is itself a state report |

### 4.8 Flash / live region

One `<div id="flash" role="status" aria-live="polite" aria-atomic="true">`
directly after `<main>`'s opening tag, for the results of actions ("Offer
sent", "Listing withdrawn"). **Not a toast:** it is in the document, it
persists until the next navigation, and it is the first thing in the content
order so a screen reader reaches it immediately.

`role="alert"` is reserved for the error slot (§4.6). Two simultaneous
assertive regions means one of them is lost.

### 4.9 Status chip

Small, inline, `--t-sm`, `--r-sm`, 1px border in its state colour, tinted
background, **always with text**. Used for listing status (`LIVE`,
`RESERVED`, `WITHDRAWN`) and for the eleven transfer states.

| State | Specification |
|---|---|
| `default` | Text + tint + border |
| `loading` | `--c-wait` tint, text "Updating…"; `--m-fast` 120 ms tint transition is the only animation in the system, and it is removed under `prefers-reduced-motion` |
| `stale` | Chip gets a dotted border and its `title`/visible suffix shows the as-of time |
| `empty`/`partial`/`error`/`offline`/`disabled` | N/A — a chip reflects a value; absence of a value means no chip, not an empty chip |

### 4.10 Status banner with rail — the transfer state display

The authoritative display of a transfer's state. Eleven states
(`DATA-MODEL.md` §6.2): `OFFERED`, `DECLINED`, `ACCEPTED`, `SCHEDULED`,
`AWAITING_CONFIRMATION`, `COMPLETED`, `CANCELLED`, `EXPIRED`, `NO_SHOW`,
`DISPUTED`, `CLOSED_UNRESOLVED`.

Anatomy: 4px rail · state name as a sentence in the reader's own role
("You offered to buy this", not "OFFERED") · the single next action, or an
explicit statement that there is none · the clock if one is running.

**Every state must render differently for buyer and seller**, because
"waiting for them" and "waiting for you" are opposite instructions.

| Transfer state | Rail | Buyer sees | Seller sees | Clock shown |
|---|---|---|---|---|
| `OFFERED` | wait | "You offered. Waiting for Priya to reply." | "Arun offered to buy this. [Accept] [Decline]" | — |
| `ACCEPTED` | wait | "Accepted. Agree a time and place." | "You accepted. Agree a time and place." | **48h reservation expiry, absolute time** |
| `SCHEDULED` | live | The docket (§4.12) | The docket | Window start/end |
| `AWAITING_CONFIRMATION` | wait | "Did the book change hands? [Yes] [No]" | same | **72h, absolute** |
| `COMPLETED` | live | "Done. Both of you confirmed." No action. | same | — |
| `DECLINED` | rule | "Priya declined. [Find another copy]" | "You declined." | — |
| `CANCELLED` | rule | Who cancelled, in plain words. [Find another copy] | same | — |
| `EXPIRED` | wait | "The 48 hours ran out and the book went back on the list." | same | — |
| `NO_SHOW` | wait | "Reported as a no-show. **No penalty is applied.** [Report a problem]" | same | — |
| `DISPUTED` | alert | "You raised a problem. Ticket #1234. We reply within 24 hours." | "A problem was raised. Ticket #1234." | **24h ack** |
| `CLOSED_UNRESOLVED` | rule | "We could not settle this. Ticket #1234 is closed." | same | — |

| Component state | Specification |
|---|---|
| `default` | As the table |
| `loading` | During a transition swap: rail turns `--c-wait`, text becomes "Sending…", **the old state text stays visible beneath it** — this is `partial` behaviour applied to a state change, and it is deliberate: on a dying connection the student must still be able to read where things actually stand |
| `partial` | As above |
| `error` | Rail `--c-alert`, "That didn't go through. The transfer is still: [old state]. [Try again]". **The old state is named explicitly.** A 409 from `expected_version` (`API-CONTRACT.md` §4.2) renders "Priya changed something while you were looking. [Reload to see it]" — never a raw conflict error |
| `offline` | Rail `--c-wait`, "No connection. As of 4:12 PM this was: [state]." Action buttons stay visible but tapping gives §4.6 `offline` |
| `stale` | Absolute as-of time + Reload |
| `empty` | N/A — a transfer always has a state |
| `disabled` | Terminal states (`*` in `DATA-MODEL.md` §6.2) render **no action buttons at all** rather than disabled ones, plus one sentence saying it is finished |

### 4.11 Catalogue card

The listing, in list form and detail form. Anatomy and reasoning:
`DIRECTIONS.md` §2.5.

List row (zero images): recency stamp · status chip · serif title ·
**edition line** · monospaced ISBN · asking price (§4.15) · campus. ~900 bytes.

**The detail page has exactly two labelled blocks, and this structure is a
compliance control, not a layout preference** (`COPY-DECK.md` §3.2,
`COMPLIANCE.md` §2.5a):

| Block | Label | Contains | The trust sentence it scopes |
|---|---|---|---|
| **The book** | "About this book" | Bibliographic identity, asking price + negotiability + not-recorded (§4.15), the attributed condition quotation (§4.14), photo strip (§4.16), the offer form (§4.18) | "BookHop hasn't checked this book." |
| **This seller** | "About this seller" | `display_name` · department, year · campus; then the sign-in fact and its qualifier (§4.11a) | "Signed in with a college email address. That's all BookHop knows about them. We haven't checked who they are." |

**No trust sentence ever appears outside the block whose scope it names.**
Compliance flagged that "Signed in with a college email address" and an
unscoped "Nothing here is checked by BookHop" read as the product arguing with
itself, and that *a contradiction in trust copy is worse than either string
alone*. Two labelled blocks plus a rescoped sentence is the fix; separating
the two sentences across the page is **not** — far apart they still
contradict, just less visibly.

**Changed in v1.1:** the figure in the list row reads `Asking ₹280`, never
`₹280` alone and never under a `Price` heading, and the negotiability sentence
sits once at the top of the results region (§4.15). On the detail page the
full three-part anatomy applies.

| State | Specification |
|---|---|
| `default` | As above |
| `empty` | N/A for a single card — see §4.13 for the results list |
| `loading` | Static reserved block, exact final height, `--c-rule` 1px outline, centred `--t-xs` "Loading…". **No shimmer** (banned, §1.5) |
| `partial` | In a list being refreshed: text dims to `--c-ink-2`, list is labelled "Previous results — updating" |
| `error` | Single card failing to load: a `--c-alert` panel in its place with "Couldn't load this listing. [Try again]". The rest of the list is untouched |
| `offline` | Cached card renders with a `--c-wait` "as of 4:12 PM" line appended, and the offer button is replaced by plain text "You need a connection to make an offer" |
| `stale` | Any listing whose `published_at` is older than 21 days gets a `--c-wait` line: "Listed 24 days ago — this may be gone." Not a warning about the seller; a statement about time. (Rationale: listing staleness is the category's oldest failure mode, `COMPETITORS.md` §3.5) |
| `disabled` | `RESERVED` listing: offer button removed, replaced by "Someone else is collecting this one. [Tell me if it comes back]" (creates a `wanted` request). `WITHDRAWN`: the card renders with no action and the line "The seller took this down" |
| `focus` | The whole row is one link; the focus ring encloses the row |
| `pressed` | Row background → `--c-paper` on a card, `--c-card` on paper. No transform |

### 4.11a Seller block — new in v1.2, and condition 3 is an engineering gate

The "About this seller" block of §4.11. Anatomy:

```
About this seller                          ← listing.seller.label, --t-xs, --c-ink-2
Priya S · Mechanical, 3rd year · Guindy    ← display_name + campus only
Signed in with a college email address.    ← trust.campus_mail. NO DOMAIN, EVER
That's all BookHop knows about them.       ← trust.account_only. Directly after,
We haven't checked who they are.              same block, same type size
```

**Three hard rules, each one a condition of `COMPLIANCE.md` §2.5a:**

1. **No part of `campuses.email_domains` reaches any student-facing surface.**
   The string has no `{domain}` placeholder and no template may interpolate
   one. A multi-domain campus (`student.x.ac.in` vs `x.ac.in`, per-department,
   per-intake) would leak student-versus-staff status, department or intake
   year through what looks like a trust badge — and with one campus in v1 the
   domain discriminates between nothing, so it buys nothing to pay for that.
   Criterion 7f.
2. **The block does not render at all until the disclosure is in the notice.**
   `consent.listing_publication.disclosure` (`COPY-DECK.md` §10.4) must be
   live in the `listing_publication` consent text and the privacy notice.
   Showing the fact to a counterparty is a different processing operation from
   verifying it. Criterion 7g.
3. **`trust.campus_mail` renders only when gated on
   `campus_verifications.method = 'INSTITUTIONAL_EMAIL'` — never on
   `users.campus_verified`.** These are two different facts. A student who
   came through the staff-assisted re-verification path (`ADR-001` §2.5) is
   `campus_verified = true` **and did not sign in with a college email
   address**, so rendering the string for them is a false statement about a
   person and fails rule 6 of §1. Criterion 7h, and it is a 22-snapshot-test
   kind of defect: it will pass every happy-path review and be wrong in
   production for exactly the users least able to notice.

| State | Specification |
|---|---|
| `default` | The four lines above |
| `empty` | **Method ≠ `INSTITUTIONAL_EMAIL`:** the sign-in line and its qualifier are **both absent**; the block shows `display_name` · department, year · campus and stops. **No substitute string** — "Verified by BookHop staff" would be BookHop asserting something about a person, which is the worst string that could exist in this product. **And no comment on the absence**: no "not available", no greyed placeholder, no tooltip |
| `loading` | Renders with the page; no independent loading state |
| `partial` | N/A — the block is atomic |
| `error` | If the verification method cannot be read, the block degrades to `empty`. **Fail closed**: an unknown method must never render the string |
| `offline` | Renders from cache with the page's as-of time (§4.11) |
| `stale` | N/A — neither fact changes without a staff action |
| `disabled` | N/A |

**Residual risk, flagged not solved.** At one campus almost every seller is
`INSTITUTIONAL_EMAIL`, so a rare absence is *more* conspicuous than a common one and
a buyer may read it as a negative signal we did not intend. Every alternative
is worse — a substitute string vouches, a "not available" label comments on
it — so this is accepted with the risk named. Revisit if staff-assisted
re-verification turns out to be common. `COPY-DECK.md` §3.2.

### 4.12 Transfer docket — the one component borrowed from Direction B

Hero of every active transfer page, and **pinned above the search field on the
home page whenever a transfer is in `SCHEDULED` or `AWAITING_CONFIRMATION`**
(`DIRECTIONS.md` §4.4 item 4 — this is not optional; it is the mitigation for
A's weakest point).

Order, which is the whole point of the component: **when → who → where → what
→ one action.** The book is one line.

| State | Specification |
|---|---|
| `default` | As above, at `--t-xl` / `--t-lg`, 56px commit button |
| `empty` | No active transfer → the component is absent. The home page is the search field. **Not** an empty docket |
| `loading` | Reserved block at final height, "Loading…" |
| `partial` | Previous docket dimmed + "Updating" |
| `error` | `--c-alert` panel inside the docket; the when/who/where block stays readable. **A student standing at Gate 2 must never see an error page instead of the meeting place** |
| `offline` | Fully readable from the service-worker cache, with "No connection. As of 4:12 PM." The meeting point, time and the other person's display name are the highest-value cached content in the product |
| `stale` | Absolute as-of time + Reload |
| `disabled` | Terminal state → docket collapses to a one-line summary |

### 4.13 Search form and results region

Form: one `type="search"` input, one submit button, three optional filters
(`condition_in`, `max_price_paise`, `course_code`) inside a native
`<details>` (`ADR-001` §2.3 — no custom disclosure widget). ISBN and free
text go in the same field; the server decides which it is.

**The `max_price_paise` filter is labelled "Highest asking price I'll look
at", never "Max price" or "Price"** (§4.15, `COMPLIANCE.md` §4.3.1). The
negotiability sentence (`COPY-DECK.md` `price.negotiable`) appears once at the
top of the results region, which is where the buying flow discharges its
once-per-flow obligation.

Results region is the htmx swap target and carries
`aria-live="polite" aria-atomic="false"`, plus a visually-hidden count
("12 copies") so a screen-reader user hears the result of a search without
hunting for it.

| State | Specification |
|---|---|
| `default` | Result count, then rows (§4.11), then "Show 30 more" (§4.17) |
| `empty` | **The most important empty state in the product.** "No copy of this edition on campus right now." Then one action: "[Tell me when someone lists it]" → creates a `wanted` request (`POST /wanted`). Then, only if the ISBN matched the catalogue: "3 copies of other editions" as a secondary list, each labelled with its edition difference — because the wrong edition is the thing we exist to prevent, it is never offered silently |
| `loading` | First search: reserved block + "Searching…" |
| `partial` | Re-search with results on screen: previous rows stay, dimmed, under "Previous results — updating". **Never a blank region** |
| `error` | `--c-alert` panel inside the results region; the query stays in the input; "[Search again]" |
| `offline` | `--c-wait` panel: "Search needs a connection." Below it, any cached listing pages the student already opened, labelled with their age |
| `stale` | Results older than 10 minutes get "as of 4:12 PM · [Search again]" at the top of the region |
| `disabled` | Submit disabled on an empty query, with "Type a title or an ISBN" beside it |
| `gate-closed` | §4.22 replaces the whole region |

### 4.14 Attributed-claim block — **the trust primitive**

The mechanism from `DIRECTIONS.md` §4.2(1). Used for the seller's condition
description, the seller's notes, and any other human claim.

```
Condition, in the seller's words                     ← label, --t-xs, --c-ink-2
“Good — cover is bent, no writing inside,            ← the person's text, serif,
 pages 40–44 have pencil marks.”                        --t-base, in quote marks
— Priya S, 3 days ago                                ← --t-xs, --c-ink-3
```

Rules, all of them load-bearing:
- The four-value `condition` enum (`DATA-MODEL.md` L340) is **never rendered
  outside this quotation.** It is a filter value, not a display value.
- The quotation marks are real characters in the markup, inside
  `<blockquote><p>` with `<cite>` for the attribution, not CSS decoration —
  they must survive a screen reader and reader mode.
- BookHop's voice appears only in the label. The label is a noun phrase
  ("Condition, in the seller's words"), never a verb that implies checking.
- A user-generated string is escaped and rendered as prose. No markdown, no
  links, no HTML from a student.

| State | Specification |
|---|---|
| `default` | As above |
| `empty` | "The seller did not describe the condition." **Stated as a fact, with no excuse and no softening** — a missing description is information a buyer should weigh, and hiding it would be the dishonest option |
| `loading` | Reserved block, "Loading…" |
| `partial` | N/A — a quotation is atomic |
| `error` | "Couldn't load the seller's description. [Try again]" — never a silent omission, because a buyer could read an empty block as "nothing wrong with it" |
| `offline` | Renders from cache with the as-of time |
| `stale` | If the seller edited it after an offer was made, the block shows both: "Changed after you offered — [see what it said before]". A changed claim is the single most decision-relevant event on a listing |
| `disabled` | N/A |

### 4.15 Seller's asking price — **relabelled in v1.1, and the label is a legal control**

`--t-2xl` numerals, `--lh-flat`, prefix ₹ outside the number.
**One per page.** No MRP, no struck-through value, no "% off", no "was/now"
(E-Com r.4(13), `API-CONTRACT.md` §5.3).

**The label is `Seller's asking price` on first appearance in any component,
`Asking price` on later appearances within the same component, and never
`Price`.** This is not a wording preference. `COMPLIANCE.md` §4.3.1 trap (1)
establishes that because P14 makes the asking price **immutable**, that number
becomes a *better* proxy for what was actually paid — which weakens the limb
of CBDT Circular 20/2021 requiring the stated price to be *"not necessarily
the price at which the transaction takes place"*. Compliance's conclusion is
that **this limb lives in copy because the schema cannot carry it**, and
Q9's statement of facts already asserts to counsel that *"the asking price is
labelled as the seller's asking price throughout"*. A template that renders
`Price` makes that assertion false.

Anatomy, which does the work in three parts:

```
Seller's asking price                 ← --t-xs, --c-ink-2. Names whose number it is
₹280                                  ← --t-2xl, the one large numeral on the page
This is what the seller is asking.    ← --t-sm, --c-ink-2. price.negotiable,
The two of you agree the actual          once per flow (COPY-DECK §1.6 rule 2)
price between yourselves.
```

Hard constraints on this component and everything that touches a rupee figure:

- **No numeric amount input exists anywhere in the product.** No offer field,
  no counter-offer, no bid, no "name your price", no slider. `POST /offers`
  carries no amount (`API-CONTRACT.md` §5.4) and the UI must never invent one.
  A structured offer amount **is** a settled consideration, and it is the
  single most likely well-intentioned proposal to break the tax position
  (`COMPLIANCE.md` §4.3.1 trap (2)).
- **No notification or email carries a rupee figure** (`COPY-DECK.md` §10.5).
  A number with no surrounding context reads as an amount due.
- **The `max_price_paise` filter is labelled "Highest asking price I'll look
  at"**, because it filters the *asking* price (`API-CONTRACT.md` §5.3) and a
  label reading "Max price" asserts the thing we are denying.
- Seller-side, the intake field's label is a question — "What are you asking
  for it?" — not a label reading `Price`, and its hint tells the seller the
  number is a starting point. **That hint is what makes negotiability real
  rather than merely stated**, which is what Compliance actually requires.

| State | Specification |
|---|---|
| `default` | As the anatomy above |
| `empty` | N/A — a listing cannot exist without an asking price |
| all others | Inherit the card's state (§4.11). The figure never has an independent state |

**The control of last resort, recorded so nobody reaches for the wrong one.**
`COMPLIANCE.md` §4.3.3 names, and explicitly does **not** request, a listing
with **no asking price at all** — which cannot be a determinable gross amount
on any reading, and does not depend on copy, behaviour or a user test. It
would cost the price filter, a large amount of buyer utility and probably
liquidity, and it would be a P14 amendment and an ADR. It is on the record
here for one reason: **if copy fails repeatedly, the available move is to
record fewer prices, not more.** Nobody should conclude from a failed copy
control that the remaining option is to start recording settled prices. That
direction is closed permanently (D-004, ADR-003, P14).

In a dense list row where the three-part anatomy does not fit, the row shows
`Asking ₹280` (`COPY-DECK.md` `listing.price.row`) **and the negotiability
sentence appears once at the top of the results region instead** — the "once
per flow" obligation is satisfied per flow, not per row. It is never dropped
from both places, and the figure never appears as `₹280` alone.

### 4.16 Photo strip, and the `Save-Data` gate

Detail page only. Up to 3 thumbs at 320px CSS width, `loading="lazy"`,
explicit `width`/`height`, `<picture>` with webp + jpeg. Tapping opens the
full image as a **page navigation**, not a lightbox (no focus trap, back
button works, works with JS off).

Alt text: generated and honest — "Photo 1 of 3, uploaded by the seller". We
do not describe a photo we have not seen, and we must not imply we reviewed
it.

| State | Specification |
|---|---|
| `default` | Three thumbs |
| `empty` | The generated CSS spine (`DIRECTIONS.md` §2.6) plus "No photos" |
| `loading` | `width`/`height` reserve the box; the browser's own placeholder. No JS skeleton |
| `partial` | 1 of 3 loaded: the loaded one shows, the others keep their reserved boxes |
| `error` | Broken image → the generated spine with "Photo didn't load. [Try again]" |
| `offline` | Cached thumbs show; uncached ones show the spine and "Needs a connection" |
| `stale` | N/A |
| `disabled` | **`Save-Data: on` →** no `<img>` is emitted at all. A link: "Show 3 photos (about 45 KB)" — the byte figure is computed from the actual stored sizes, not estimated. Honouring the student's own data-saver setting is the single most respectful thing this interface does |

### 4.17 Pagination

A "Show 30 more" button, cursor-based (`API-CONTRACT.md` §2.3). **No infinite
scroll** — it spends metered data without being asked. Appended rows are
focused via a visually-hidden heading so a keyboard user lands on the new
content rather than at the top.

| State | Specification |
|---|---|
| `default` | "Show 30 more" |
| `empty` | Button absent; the list ends with "That's all 12." |
| `loading` | "Loading…", disabled for the duration, existing rows untouched |
| `partial` | N/A — appending, so prior content never leaves |
| `error` | Inline below the button: "Couldn't load more. [Try again]". Existing rows untouched |
| `offline` | Button becomes text: "You'll need a connection for more" |
| `stale`/`disabled` | N/A |

### 4.18 Offer form

On the listing page. One optional **free-text** message field, one 56px commit
button, and above the button the handover guidance line (§4.20). Carries
`Idempotency-Key` and `expected_version` (`API-CONTRACT.md` §4).

**There is no amount field on this form and there must never be one.** The
endpoint carries none (`API-CONTRACT.md` §5.4) and an accepted offer amount
would be a settled consideration (`COMPLIANCE.md` §4.3.1 trap (2)).

**Changed in v1.2 — the message hint now invites a figure, addressed to the
seller.** `COMPLIANCE.md` §4.3.3 rules that a student-authored rupee figure in
free text does not affect the tax position and **recommends** the prompt,
because copy that *causes* negotiation produces evidence for the limb while
copy that merely *asserts* it does not. The boundary is **invite a
conversation, never capture a number**, which gives this form three
constraints:

1. The hint addresses `{name}`, never us. "What would you pay?" reads as
   BookHop collecting an answer and is a banned shape
   (`COPY-DECK.md` §10.2).
2. **`price.not_recorded` must appear in this same view** — condition 3. It
   does, inside the price block (§4.15), and that is now mandatory rather
   than editorial: if the figure prompt ships without it, the compliance
   sign-off does not hold. Criterion 7i.
3. Nothing parses, extracts, flags or aggregates the figure. See §4.23.

| State | Specification |
|---|---|
| `default` | "Offer to buy this copy" |
| `empty` | N/A |
| `loading` | §4.2 `loading` |
| `partial` | N/A |
| `error` | §4.6. A 409 renders "Someone offered just before you. [See what changed]" — not "conflict" |
| `offline` | §4.6 `offline`; the typed message is preserved |
| `stale` | If the listing went `RESERVED` while the page was open, the form is replaced on submit by §4.11 `disabled` with "Someone else is collecting this one" |
| `disabled` | Not signed in → the button is replaced by a sign-in link, not disabled. Own listing → no form, with "This is your listing" |

### 4.19 Handover point and window pickers

Point: a `<select>` (or radio list of ≤6) of curated `handover_points` for the
campus, each with its name and a one-line description of where it is. Window:
two `<select>`s — day (next 14, per the `ACCEPTED → SCHEDULED` guard) and a
time band. No free-text time, no custom calendar widget, no map.

**SC 3.3.7 (Redundant Entry):** the point used in the student's last completed
handover is pre-selected.

| State | Specification |
|---|---|
| `default` | Point + day + band, then "Propose this time" |
| `empty` | **No active handover points on this campus** → "There are no agreed meeting points on your campus yet. [Message Priya to agree one]" with the guidance line. An empty point list must never block the flow entirely |
| `loading` | §4.2 |
| `partial` | The other party's proposal shows above, dimmed, while yours sends |
| `error` | §4.6. A window outside 14 days or in the past → the specific sentence, at the field |
| `offline` | §4.6 `offline` |
| `stale` | The other party proposed something after this page loaded → "Priya proposed 4:30 PM at Library steps. [See it]" before your own submission is accepted |
| `disabled` | Transfer not in `ACCEPTED` → the picker is absent, with the current state (§4.10) in its place |

### 4.20 Handover guidance acknowledgement

A transfer **cannot reach `SCHEDULED`** until the current `HANDOVER_GUIDANCE`
notice version has been shown to both parties — backend-enforced
(`API-CONTRACT.md` §5.4). This is the component that shows it.

Design decision: **it is not a modal and not a checkbox-with-fine-print.** It
is a short block on the page, above the "Agree this time" button, with the
guidance in three lines, and the acknowledgement is **the act of pressing the
button**, whose label says what it means: "I've read this — agree 4:30 PM at
Library steps". Reasons: a modal is a focus trap and dies with JS off; a
checkbox invites a reflex tick; and pressing a labelled button is a recorded
act (`transfer_events`) that is legible in both directions.

Copy: `COPY-DECK.md` §7. The words "safe", "verified", "protected",
"guaranteed" and "assured" cannot appear
(`API-CONTRACT.md` §5.4 — and a test greps for them). The guidance is
instructional: check the book, meet at a named point, in daylight, with other
people around.

**Added in v1.1 — the `hand.price` line sits immediately above the guidance
block, not inside it:** "Agree the price between yourselves when you meet.
{name} is asking ₹{amount}." `COMPLIANCE.md` §4.3.1 names the handover copy
specifically as where this limb must appear, and this is the moment at which
it is literally true. It is kept **outside** the guidance block so the two
review classes stay separate — the guidance block is a liability artefact
(`COPY-DECK.md` B1), this line is a tax artefact (B4), and merging them would
mean one reviewer signing off on both.

| State | Specification |
|---|---|
| `default` | Block + labelled commit button |
| `empty`/`partial` | N/A |
| `loading` | §4.2 |
| `error` | §4.6. If the notice version changed since render: "This guidance was updated. [Read it again]" and the submission is refused — a stale acknowledgement is not an acknowledgement |
| `offline` | §4.6 `offline`. The guidance text itself is cached by the service worker and always readable offline — it is the one piece of prose that matters most at the moment of the meeting |
| `stale` | As `error` above |
| `disabled` | Already acknowledged this version → the block collapses to "You read the handover guidance on 18 Oct. [Read again]" |

### 4.21 Confirm control

`POST /transfer/{id}/confirm`. The endpoint asks exactly one question — "did
the book change hands?" — and there is **no amount field anywhere**
(`API-CONTRACT.md` §5.4, ADR-003 §2.4).

The accessible name of the button must be unambiguous out of context, because
a screen reader lists controls without their surroundings (SC 2.5.3 Label in
Name, SC 2.4.6 Headings and Labels): **"Yes — I got the book (Artificial
Intelligence: A Modern Approach, 4th ed.)"**, not "Yes".

| State | Specification |
|---|---|
| `default` | Question at `--t-md`, then two buttons: 56px commit "Yes — I got the book", 48px secondary "No — it didn't happen" |
| `empty` | N/A |
| `loading` | §4.2 |
| `partial` | **One side confirmed, waiting for the other:** "You confirmed. Waiting for Priya." The 72-hour clock shows as an absolute time. This is the state the whole completion metric depends on (D-008 ruling 2), so it is a real, explicit, non-ambiguous screen — not a greyed button |
| `error` | §4.6; the state banner names the unchanged state (§4.10 `error`) |
| `offline` | §4.6 `offline`. Nothing is queued and nothing is implied to have been recorded (`ADR-001` §6: no offline writes) |
| `stale` | Other party confirmed meanwhile → "Priya confirmed. Your turn." |
| `disabled` | Outside `SCHEDULED`/`AWAITING_CONFIRMATION` → control absent, state banner in its place |

### 4.22 Gate-closed page

`assert_discovery_open(campus)` can refuse every discovery call
(`API-CONTRACT.md` §5.3), and a real student on a closed campus gets
`403 GATE_CLOSED` with **no listing data on the page at all**.

Full-page `--c-wait` notice: what is happening, when it changes if we know
(and nothing if we do not — we do not invent a date), and the one thing they
can do (leave a `wanted` request, which needs no open gate). No search field,
no sample listings, no "coming soon" countdown.

| State | Specification |
|---|---|
| `gate-closed` | As above |
| `error`/`offline`/`stale` | Standard banners (§4.7) |
| all others | N/A — this page has one job |

### 4.23 Message thread and composer

A thread exists only between a buyer and a seller on one listing
(`API-CONTRACT.md` §5.5). No DMs, no contact details ever exchanged by the
platform. Messages matching a phone/email/UPI pattern are **flagged, not
blocked** (`DATA-MODEL.md` §8).

Design consequence of "flagged, not blocked": the composer must **not** warn,
scold, or hint that a pattern was detected. A visible warning would teach
students to evade the flag, and the flag is a moderation signal, not a rule
we are enforcing on them. The composer is silent about it.

**The thread is where price is negotiated, and that imposes a hard limit on
what may ever be derived from it.** `COMPLIANCE.md` §4.3.3 permits — and
recommends — inviting a buyer to name a figure here, **on the condition that
nothing structures it.** Therefore, and these are bans rather than defaults:

- **No numeric or amount-shaped input in the composer.** Free text only.
- **Nothing parses figures out of `messages.body` into any column**, no
  "detected price" annotation, no analytics or aggregate over amounts
  mentioned in messages.
- **`messages.contact_pattern_flag`'s regex is never extended to currency
  patterns** — `₹`, `Rs`, `INR`, `\d+/-`. `COMPLIANCE.md` §4.3.2 item 10
  predicts that someone will propose exactly this as a leakage signal. It
  would create a derived, queryable, per-message indicator that an amount was
  discussed, which converts the unstructured free text the tax position relies
  on into a column we can group by. Row 22 exists for phone, email and
  UPI-handle patterns, for contact-sharing and safety, **never for money.**
  Criterion 7j asserts the pattern set, not just the column.

This is the clearest case in the product of a design constraint that looks
like a missing feature: "flag when students discuss price" is an obvious,
well-intentioned moderation idea, and it would quietly undo a legal position.

| State | Specification |
|---|---|
| `default` | Messages oldest→newest, each with sender display name and absolute time; composer pinned at the bottom with `scroll-padding-bottom` honoured |
| `empty` | "No messages yet. Ask about the book before you offer." |
| `loading` | Reserved block, "Loading messages…" |
| `partial` | New messages appended below; existing ones never re-render (append-only swap, so the student does not lose their scroll position or a half-typed message) |
| `error` | Failed send: the message stays in the composer with "Not sent. [Try again]" beneath. **The text is never lost and never shown as if it were delivered** |
| `offline` | Composer stays usable; on send, §4.6 `offline`. Thread renders from cache with the as-of time |
| `stale` | "as of 4:12 PM · [Check for new messages]" |
| `disabled` | Transfer terminal or either party blocked → composer replaced by a sentence naming which |

### 4.24 Report / block / grievance form

`POST /report`, `POST /block`, `POST /grievance` (the last is unauthenticated
— a parent or rights-holder is not a user). Every submission returns a
**ticket number** and an acknowledgement clock, and the response states both
in plain words (E-Com r.5(3)(b), r.3(2)(a)(i)).

| State | Specification |
|---|---|
| `default` | A reason `<select>`, a free-text box, submit. Reasons are concrete ("The book was not what the listing described", "The person did not turn up", "This listing is a copied/photocopied book") |
| `empty` | `GET /reports` with none: "You haven't reported anything." |
| `loading` | §4.2 |
| `partial` | N/A |
| `error` | §4.6. **The typed report text is never lost** — it may be the only record of a bad experience and asking a student to retype it is how a report gets abandoned |
| `offline` | §4.6 `offline`, with the text preserved and a visible "[Copy this text]" control so the student can keep it outside the app |
| `stale` | An open ticket's page shows the ack clock as an absolute deadline |
| `disabled` | N/A — reporting is never unavailable. The grievance route works unauthenticated and offline-to-online without an account |

### 4.25 Account screens: sign-in, link-sent, age gate, consents, erase

| Screen | Notes and states |
|---|---|
| Sign-in | One email field (§4.4), `autofocus` (the one permitted use). `default` / `loading` / `error` / `offline`. **Always the same confirmation whatever happens** — `POST /auth/magic-link` always returns 202 to avoid an account-enumeration oracle, so the UI must never reveal whether the address is known |
| Link-sent | A terminal page, not a spinner: "We sent a link to {email}. Open it on this phone." Plus "[Send another]" after 60 s, with the wait stated. `default` / `error` / `offline`. **No auto-polling** — polling on 3G for an email is pure waste. **Note on criterion 7f, so it is not over-applied:** `{email}` here is the address the student just typed, echoed back to **themselves**, which they need in order to know where to look. That is not a `campuses.email_domains` interpolation and not a disclosure to a counterparty. The ban is on rendering *another person's* domain, and on domain literals in `.po` strings — not on showing someone their own address |
| Age gate | Native `<input type="date">`. States: `default`, `error`. Under 18 → `403 NOT_ADULT_VERIFIED`, the account is deleted immediately, **the DOB is never persisted** (`API-CONTRACT.md` §5.1), and the page says plainly that the account has been removed and the date was not kept. Hard, honest, no softening |
| Consents | One row per purpose, a real `<input type="checkbox">` in a 44px row with the purpose in plain language and the notice version. A **toggle, not an email** (DPDP r.3(c)(i)). States: `default`/`loading`/`error`/`offline`/`stale` (notice version changed → "The privacy notice changed on 12 Oct. [Read what changed]") |
| Erase | Two-step confirm. The confirmation screen **states which records are retained for one year and why**, before the final button (`API-CONTRACT.md` §5.1 — the user learns it here, not from a support ticket). Destructive button variant. `default`/`loading`/`error`/`offline` |

### 4.26 Empty-state block (the generic primitive)

Used by §4.13, §4.23, §4.24, and the seller's own listing list. Anatomy: one
sentence saying what is not there and why, then **exactly one** action, then
nothing. No illustration, no mascot, no "Oops!", no exclamation mark.

The seller's empty list is the only one with a persuasive job, and this is
where `DIRECTIONS.md` / `COPY-DECK.md` §1.5's "worth your while" decision
lands: the copy is concrete and factual, not an idiom.

### 4.27 Offline page (service worker)

`GET /offline` (`API-CONTRACT.md` §5.8). The service worker caches the app
shell, the stylesheet, the offline page **and the handover guidance text**
(§4.20) — the last because it is the prose most needed at the worst moment.
Shows: the notice, any cached transfer docket with its as-of time, and the
grievance-officer contact as plain text.

**It never shows a queued-action list**, because `ADR-001` §6 excludes offline
writes and a UI that implies a queued write is a lie about durability.

---

## 5. Interaction, mobile, and making htmx legible

### 5.1 Touch and thumb reach

- 44px minimum, 48px for submits, 56px for the one commit action
  (`tokens.css` §4). 8px minimum between adjacent targets.
- **Thumb zone.** On a 5–6" phone held one-handed, the comfortable arc is the
  bottom ~45% and the inner side. Therefore: the primary action on any
  transaction page sits in a **sticky bottom bar**; destructive actions never
  sit next to it (minimum 24px apart, and preferably a separate screen);
  back/cancel sits at the top where a mis-tap is cheap.
- **The sticky bar obeys SC 2.4.11.** `scroll-padding-bottom: var(--s-18)`
  and `env(safe-area-inset-bottom)` padding. The bar holds exactly one button.
- No swipe gestures, no long-press, no drag — SC 2.5.7, and all three are
  undiscoverable. Every action is a visible control.
- Hit areas extend to the full row for list items; the visible text is not the
  only tappable part.

### 5.2 Cheap-keyboard behaviour

The per-field table is §4.4. The three that will otherwise cause real support
load:

1. **Email autocapitalisation.** Android capitalises the first letter of an
   `type="email"` field in several keyboard apps. `autocapitalize="off"`
   plus `autocorrect="off"` plus `spellcheck="false"` on the sign-in field, or
   students will be unable to sign in and will blame us.
2. **ISBN must be `type="text"` with `inputmode="numeric"`,** never
   `type="number"` — `number` discards hyphens, shows spinners, and a long
   digit string in a `number` field triggers locale grouping on some Android
   browsers.
3. **`enterkeyhint`** on every single-field form so the Enter key says
   "Search" / "Send" / "Go" rather than inserting a newline into a field the
   student thought was a search box.

Also: never `autofocus` except on sign-in; never open a keyboard on page load
elsewhere; never use a JS-driven input mask (masks fight Android IMEs and the
Tamil keyboard particularly badly) — validate on submit and explain, instead.

### 5.3 Making htmx swaps legible rather than confusing

This is the part most likely to go wrong, so it is specified as rules the
frontend agent can apply mechanically.

1. **Every htmx control is a real form or link first.** `hx-post` sits on a
   `<form method="post" action="…">`; with JS off the same action runs as a
   full page load. This is the `ADR-001` §2.3 contract and it is also the
   accessibility floor.
2. **Indicator with a delay, and words not just a spinner.**
   `hx-indicator` reveals after `--m-indicator` (400 ms). Under 400 ms nothing
   changes on screen — a flashed spinner reads as a fault. Over 400 ms the
   button's own label becomes "Sending…". Uploads get a **determinate** bar
   (§4.5).
3. **Disable the submitter, not the form.** `hx-disabled-elt="this"` on the
   button; the fields stay readable and editable. Combined with
   `Idempotency-Key` (`API-CONTRACT.md` §4.1) this makes a double-tap
   harmless.
4. **Set an explicit timeout.** htmx has none by default.
   `hx-request='{"timeout": 25000}'` — 25 s is long enough for a 3G round trip
   with a photo and short enough that the student is not left guessing.
5. **Swap targets are always visible, and focus follows the swap.** A swapped
   region begins with a heading carrying `tabindex="-1"`; on
   `htmx:afterSwap` focus moves to it. Without this, a keyboard or TalkBack
   user's focus is silently destroyed and lands at the top of the document —
   the single most common htmx accessibility defect.
6. **One live region per role.** `role="status"` for the flash (§4.8),
   `role="alert"` for form errors (§4.6). Swapped content regions use
   `aria-live="polite"` only when the student did not initiate the change;
   when they did, moving focus is better than announcing.
7. **Reserve the height of anything that will be swapped**, so a slow response
   does not shift the page under a thumb already on its way down.
8. **Errors never replace a form.** `htmx:responseError` and
   `htmx:sendError` both render into the form's error slot (§4.6). The form
   element, and everything typed into it, survives.
9. **`hx-swap="outerHTML"` on self-replacing state components** (the status
   banner, the docket) so a transition cannot leave two states on screen.
   `beforeend` for append-only lists (messages, pagination).
10. **No `hx-trigger="every Ns"` anywhere.** Polling on a metered 3G
    connection spends a student's money to tell them nothing. State changes
    arrive by Web Push (`ADR-001` §2.3) or on their next page load.
11. **No `hx-boost` on the whole document.** Boosting every link turns
    ordinary navigations into fetches and breaks the back button's
    scroll restoration for no benefit on a server-rendered site.

### 5.4 When the connection dies mid-transaction

The design position, stated once: **the UI shows the last state the server
confirmed, and nothing else.** There is no optimistic rendering of a state
transition anywhere in this product.

| Moment | What the student sees | Why |
|---|---|---|
| Request never left the phone (`htmx:sendError`, or `navigator.onLine` false) | Form intact, §4.6 `offline`: "This didn't reach BookHop. Nothing was lost — tap Send again when you have signal." | True, and actionable |
| Request sent, response lost | Same message, and **Retry reuses the same `Idempotency-Key`** (`API-CONTRACT.md` §4.1), so if the server did process it the retry returns the same result instead of creating a second offer | This is the entire reason the idempotency contract exists; the UI must actually use it |
| Student reloads after a dropped response | The server-rendered page shows the **real** state. If the action did land, they see it done; if not, they see the action still available | No reconciliation logic, no guessing |
| Page was open while the other party acted | `expected_version` returns 409; §4.10 `error` renders "Priya changed something while you were looking. [Reload to see it]" | A conflict is a human event, described in human terms |
| Phone goes offline while standing at the handover | Docket (§4.12) renders from the service-worker cache: when, who, where, and the guidance text. Marked "As of 4:12 PM" | This is the one moment where cached data is worth more than fresh data |
| Confirmation tapped, connection dies | **Nothing is implied to have been recorded.** The confirm control returns to `default` with the offline message. `ADR-001` §6 excludes offline writes, so the UI never claims a queued confirmation | A false "confirmed" would corrupt the one metric the pilot exists to measure (D-009) |

### 5.5 Focus order, keyboard, and screen reader

- **DOM order equals visual order, everywhere.** No `order`, no `flex-direction:
  row-reverse`, no positive `tabindex`. Positive `tabindex` is forbidden in the
  codebase; `-1` is permitted only as a programmatic focus target (§5.3 rule 5).
- Reading order on a transaction page: skip link → header → **flash region
  (§4.8)** → `h1` → **state banner (§4.10)** → content → single primary action
  → footer. The state banner is deliberately second so a TalkBack user learns
  where the transfer stands before anything else.
- Visible focus on every interactive element, §2.5. `outline: none` is a
  build failure.
- **No focus traps.** No modals, no bottom sheets, no custom dropdowns in v1.
  Disclosure is `<details>`; an "overlay" is a page.
- `<details>` summaries are 44px rows and announce their expanded state
  natively — which is why we are not building a custom accordion.
- Icons are decorative and always paired with text; `aria-hidden="true"` on
  the glyph. There is no icon-only button in v1.
- Form controls use real `<label for>`. `aria-label` is used only on the
  search landmark and on the two language links.
- The language switch sets `lang` on `<html>`; inline cross-language strings
  carry their own `lang` so TalkBack switches its Tamil voice instead of
  reading Tamil text with an English engine. **This is the single biggest
  screen-reader quality item in a bilingual product and it costs one
  attribute.**
- Absolute times everywhere ("4:30 PM, Tue 21 Oct"), with relative time only
  as an *addition* ("3 days ago"). A relative time alone is unusable when the
  page is cached, and it is the stale-data bug students will not notice.

---

## 6. Acceptance criteria — the things `test-qa` can fail the build on

Objective, binary, and mapped to the charter's metrics.

| # | Criterion | How to verify |
|---|---|---|
| 1 | **Zero WCAG 2.2 AA violations** on every v1 page | axe-core via Playwright (already in the `ADR-001` §2.8 dependency list), on every route, in **both locales** |
| 2 | **Zero contrast failures**, including in the Tamil locale and in forced-colours mode | Port §3's calculator into the test suite as an assertion over `tokens.css`; plus axe |
| 3 | **No interactive element under 44×44 CSS px** at 320px width | Playwright `boundingBox()` sweep over every `a, button, input, select, textarea, summary, [role=button]` |
| 4 | **No horizontal scroll at 320px and 200% zoom** (SC 1.4.10) | `document.scrollingElement.scrollWidth <= clientWidth` at 320×512 and at 640px-equivalent zoom |
| 5 | **Every core flow completes with JavaScript disabled** | Playwright with `javaScriptEnabled: false`: sign in, list a book, search, offer, agree handover, confirm, report |
| 6 | **`outline: none` and positive `tabindex` appear nowhere** | grep |
| 7 | **No forbidden word** in any template or `.po` file: safe, verified, guaranteed, protected, assured | `tests/unit/test_forbidden_copy.py`, already specified in `API-CONTRACT.md` §5.4. **Extend it to the Tamil `.po` with the Tamil equivalents** once the `COPY-DECK.md` TR-8 review lands |
| **7b** | **No forbidden phrase** in any template or `.po` file: "pay the listed price", "fixed price", "non-negotiable", "final price" — **and no element whose visible label or `<th>` is the bare word "Price"** | Same test, new assertions. `COMPLIANCE.md` §4.3.1. The bare-label limb needs a rendered-DOM check as well as a grep, because a label can be assembled from a translation variable. Tamil equivalents blocked on `COPY-DECK.md` TR-11 |
| **7c** | **No `<input>`, `<select>` or `<textarea>` in the student-facing UI accepts a rupee amount, except the seller's intake price field** | grep the templates for amount-shaped fields; assert the offer form and the message composer have none. `COMPLIANCE.md` §4.3.1 trap (2) — a structured offer amount is a settled consideration |
| **7d** | **No notification or email template contains a currency symbol or an amount placeholder** | grep `notify` templates for `₹` and for the amount variable |
| **7e** | **Every flow that displays a rupee figure displays the negotiability sentence at least once** | One assertion per flow: listing detail, search results region, handover page. `COPY-DECK.md` §1.6 rule 2 |
| **7f** | **No template interpolates `campuses.email_domains` or any element of it, and no `.po` string contains an `@`-prefixed domain literal** | grep + a template-variable check. `COMPLIANCE.md` §2.5a condition 1 / §4.3.2 item 11. **Scope note:** echoing the student their own submitted address on the link-sent page (§4.25) is explicitly in scope of the product and out of scope of this ban |
| **7g** | **The seller block does not render the sign-in line unless `consent.listing_publication.disclosure` is present in the live `listing_publication` consent text and the privacy notice** | One test asserting the notice string exists; the block's template guards on it. `COMPLIANCE.md` §2.5a condition 2 |
| **7h** | **`trust.campus_mail` renders if and only if `campus_verifications.method = 'INSTITUTIONAL_EMAIL'`** — never on `users.campus_verified`, and an unknown method renders nothing | Two tests: a staff-re-verified user's listing shows no sign-in line and no substitute text; a NULL/unknown method fails closed. **`COMPLIANCE.md` §2.5a condition 3 — the defect this catches passes every happy-path review** |
| **7i** | **Any view containing the figure prompt also contains `price.not_recorded`** | Assert on the listing detail route. `COMPLIANCE.md` §4.3.3 condition 3 |
| **7j** | **`messages.contact_pattern_flag`'s pattern set contains no currency pattern** (`₹`, `Rs`, `INR`, `\d+/-`), and nothing derives an amount from `messages.body` | Assert the pattern set itself, not just the column list. `COMPLIANCE.md` §4.3.3 condition 2 / §4.3.2 item 10 |
| **7k** | **The link-sent page DOES render the address the student just submitted** | A **positive** assertion, deliberately: criteria 7f and 7g forbid rendering a domain, and the obvious way to over-comply is to strip the echo from the one page where the student needs it, breaking sign-in while believing a control was tightened. Showing someone their own submitted address is not a disclosure to a counterparty. A prose scope note would be read once; a failing test is read every time |
| 8 | **The `condition` enum never renders outside the attributed quotation** | grep the templates for the enum values outside the `blockquote` partial |
| 9 | **No `<img>` emitted when `Save-Data: on`** | request with the header, assert zero image requests on the listing detail route |
| 10 | **Every one of the eleven transfer states renders a distinct buyer view and seller view** with a next action or an explicit statement that there is none | 22 snapshot tests against §4.10 |
| 11 | **Every component renders all its applicable states** per §4 | A state gallery route (`/dev/states`, staff-only) rendering each component in each state; reviewed and snapshotted |
| 12 | **No webfont request on any page** | Assert zero requests with a font MIME type |
| 13 | **p75 LCP on a mid-range Android over 3G** meets the `METRICS.md` target | Real device, throttled profile. **Currently unmeasured** — `DIRECTIONS.md` §5.1's numbers are estimates `[E]` |

---

## 7. Open risks and what I am escalating

1. **Density is untested on real devices with real students.** Direction A's
   core bet (`DIRECTIONS.md` §4.1 item 2) could fail. Pre-committed
   change-of-mind conditions are in `DIRECTIONS.md` §4.5; the instrument is
   `USER-TEST-PLAN.md`. **Nothing has been run.**
2. **A has no good answer for a student who cannot read dense text
   comfortably** beyond zoom reflow and a 14.9px floor
   (`DIRECTIONS.md` §4.4 item 5). Open. A text-size control in the product is
   the obvious mitigation and I have deliberately *not* specified one, because
   the OS already has one and duplicating it is the kind of thing that then
   has to be maintained in two places — **but if testing shows students do not
   know their phone's font-size setting exists, that reasoning is wrong and we
   add the control.**
3. **The Tamil `.po` cannot be written without a native speaker.**
   `COPY-DECK.md` lists the review items; **four** are now **BLOCKING** (B4
   was added in v1.1). The forbidden-copy test (criteria 7 and 7b) cannot be
   extended to Tamil until that review names the Tamil equivalents — so
   **a Tamil string that warrants would pass today's grep, and since v1.1 a
   Tamil string that reads as a fixed price would pass it too. One blind spot,
   two legal exposures: a liability one and a tax one.**

   **The gate is now mechanical rather than a promise in my file, and I did
   not build it** (verified in `TASKS.md`, amendments A-7/A-8/A-9):
   `feature_flags['i18n.ta_enabled']` is seeded **`false`** and stays false
   until the native-speaker review lands; the frontend creates
   `locale/FORBIDDEN_EXCEPTIONS.toml`, `locale/ta/BLOCKING_CLASSES.toml` and an
   initially-empty `locale/ta/REVIEWED.toml`; and the release checklist
   requires **a reviewer-signed entry in `locale/ta/REVIEWED.toml`** per
   `THREAT-MODEL.md` §6.1. Tamil strings may be written — and are — but **no
   student is offered the Tamil locale while any blocking-class string is
   unreviewed.** `TASKS.md`'s own wording for this is the right standard and I
   am adopting it over my prose: *"That is the gate, and it is a test, not a
   promise."*

   **What remains genuinely open is therefore not a control but a person:** a
   named native Tamil speaker, which the founder has not yet provided. The
   blind spot above persists until then, and `test-qa` should know that the
   Tamil `.po` passing CI means only that the flag is off.
3a. **✅ CLOSED v1.2 — `trust.campus_mail` ships.** `COMPLIANCE.md` §2.5a:
   *"Signed in with a college email address."* The vouching limb passed on my
   own §1.2 reading; the disclosure limb's three conditions are implemented in
   §4.11a and enforced by criteria 7f–7h. **Condition 3 is the one that
   justified the round trip** — a staff-re-verified student is
   `campus_verified = true` and did **not** sign in with a college email
   address, so an un-gated string would have been a false statement about a
   person, in production, for exactly the users least able to notice. Refusing
   to read silence as approval cost one round trip and caught that.
   `COPY-DECK.md` §12 item 1.
4. **To `product-manager`:** the `condition` enum recommendation
   (`DIRECTIONS.md` §7.1), which closes CTO escalation #4 if accepted.
5. **To `privacy-compliance` — ✅ answered, with one onward dependency.** The
   `trust.campus_mail` string is ruled (§7.3a). The one thing still owed by
   someone else: `COMPLIANCE.md` §2.5a condition 2 amends §7 row 6's purpose,
   and the string should be shown to counsel as part of **C1's notice
   review**. **Criterion 7g blocks the seller block from rendering until the
   notice sentence is live**, so this cannot ship ahead of the notice by
   accident.
6. **To `ceo-planning` / founder:** `USER-TEST-PLAN.md` is unfunded against a
   ₹2,600 unallocated balance (D-008). A ₹0 variant exists. No spend is
   committed here.
7. **✅ CLOSED v1.3 — the slug is renamed.** Amendment **A-7** took
   `handover-safety` → **`handover-guidance`** and `notice_versions.kind`
   `HANDOVER_SAFETY` → **`HANDOVER_GUIDANCE`** across `API-CONTRACT.md`
   (§5.1, §5.4, A-7), `DATA-MODEL.md` (L254, A-7) and `TASKS.md` (S1, A-7).
   **Verified by reading those three files, not taken on report.** §4.20 now
   names the new identifier. The CTO recorded the reasoning I gave: a slug is
   a route, **but an identifier is where a label comes from** — a developer
   reading `HANDOVER_SAFETY` writes "Handover safety" in a template, and no
   grep catches the identifier that suggested the wrong label. Worth keeping
   as a pattern: the forbidden-copy test guards strings, so the places that
   *generate* strings need guarding by naming.
8. **✅ CLOSED v1.3 — `/dev/states` is in the plan.** `TASKS.md` A-8 adds it
   to slice S2. Criterion 11 is therefore buildable as written.
9. **✅ CLOSED v1.3 — the schema guard exists, and it is better than what I
   asked for.** I recommended adding four column names to the forbidden-schema
   list. **ADR-003 §2.3 item 4 already forbids the patterns** —
   `%offer%amount%`, `%offered_price%`, `%counter%price%`, `%bid%`,
   `%negotiat%`, `%accepted_price%`, `%deal%` — with `%agreed_price%` caught by
   the settled-consideration row above it, and `THREAT-MODEL.md` §9 records the
   control as a **whitelist** rather than a deny-list. Patterns beat the name
   list I proposed, and a whitelist beats both. The CTO accepted compliance's
   item 4 before my escalation arrived and quotes the same reasoning I reached
   independently: *an accepted offer amount IS a settled consideration*, and it
   is the most likely next feature request.
   **So the line in §4.15 and §4.18 should be read the other way round now:
   copy is not defending a column that exists — the column cannot exist.**
   `ADR-003` §2.4 also resolves the apparent tension better than I did, and it
   is worth quoting here because the next reader will think the two rules
   conflict: *"The prohibition on offer amounts and the requirement that
   negotiation be real are the same design: BookHop must not know."*

---

## 8. Amendment log

| Version | Date | Change |
|---|---|---|
| v1.0 | 2026-10-21 | First system. Ten rules, eight-state vocabulary, 27 verified colour pairs, ~27 components with every state, htmx legibility rules, 13 acceptance criteria |
| **v1.2** | **2026-10-21** | **Both compliance rulings implemented (`COMPLIANCE.md` v1.2 §2.5a, §4.3.3).** New **§4.11a seller block** with the three §2.5a conditions, including the fail-closed gate on `campus_verifications.method` and the deliberate *absence* (no substitute string) for staff-re-verified sellers. §4.11 restructured into **two labelled blocks** — the adjacency fix compliance flagged and left to me. §4.18 message hint now **invites a figure addressed to the seller**; §4.23 gains the hard ban on currency patterns in `contact_pattern_flag` and on deriving any amount from `messages.body`. §4.15 records the no-asking-price control of last resort, with its cost, so nobody concludes that recording prices is the remaining option. **New failable criteria 7f–7j.** Escalations 3a and 5 closed |
| **v1.1** | **2026-10-21** | **Negotiability added as a design constraint on instruction from `COMPLIANCE.md` §4.3.1.** New rule 11. §4.15 relabelled from "Asking price" to "Seller's asking price" with a three-part anatomy, a ban on any numeric amount input, a ban on amounts in notifications, and the `max_price_paise` filter label. Consequential edits to §4.11, §4.13, §4.18, §4.20. New acceptance criteria 7b–7e. Escalation 9 added (schema-side guard). `trust.campus_mail` recorded as **blocked pending a compliance ruling** (§7.3a) rather than shipped on assumption |

---

## Amendment, 2026-10-22 — ceo-planning, per cto rulings (DATA-MODEL A-26, API-CONTRACT A-17)

**Criterion 7h's spelling corrected throughout: `campus_verifications.method
= 'INSTITUTIONAL_EMAIL'`.** `EMAIL_DOMAIN` was never a value — the schema
CHECK and the running code have always said `INSTITUTIONAL_EMAIL` — so **7h
could only ever pass vacuously**, with the gate spelled two ways across three
documents and the code. Found by frontend-developer trying to build against
it, which is the only way a criterion like that surfaces.

Ratified reasoning, so it is not re-litigated: **`INSTITUTIONAL_EMAIL` names
the thing verified (an institutional affiliation) rather than the mechanism
used (a domain match)**, which is how its sibling `STAFF_MANUAL` is named, and
which stays correct when a second method arrives that still matches a domain.
`EMAIL_DOMAIN` would be wrong again within a year.

**Frontend's both-spellings tolerance should now be dropped** — a tolerance
that outlives its divergence is how the divergence returns.

### Criterion 7f — NARROWED, with its rationale travelling beside it

**7f now reads: no template may interpolate *another person's* email domain.**
The second limb is untouched and is the part doing real work: **no domain
literal in any string file; the value arrives from the service at render
time.**

**Rationale, which must stay next to the criterion:** COMPLIANCE §2.5a is
entirely about **a seller's** domain on **a listing**, where it is attribute
disclosure about an identifiable person dressed as a trust badge. The
*accepted-domain list* on the link-sent page is campus configuration —
identical for every visitor, about nobody, and already printed on the
institution's own website. **There is no data subject.** Meanwhile PRD AC-A1.2
is a product requirement, so as written **the primary journey could only work
by violating a failable criterion.**

**Why the rationale is now mandatory beside the rule, and this is its third
instance: a criterion written from a rationale, without the rationale
travelling with it, drifts wider than the risk it was written for — and the
widening is invisible because the criterion still reads protective.** Strip
this paragraph and the broad version gets restored by the next careful person.
