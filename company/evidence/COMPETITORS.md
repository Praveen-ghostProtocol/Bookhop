# COMPETITORS.md — Competitor & Category Audit

**Owner:** market-finance · **Status:** Phase A evidence · **Version:** v1.0
**Date of research:** all URLs accessed **2026-10-21** unless stated otherwise.
**Handoff:** ceo-planning, red-team.

> **Evidence standard applied (company/README.md §8).** Every factual claim below
> carries a source URL and date accessed. Every number without a source is tagged
> `ASSUMPTION:` with reasoning and the test that would replace it. No invented
> statistics, no invented user quotes, no invented company metrics. Where a site
> blocked me or a figure could not be found, it says **not found** or **blocked**.
> Self-reported marketing numbers are labelled as such and are not treated as fact.

---

## 1. Verdict

**This is a crowded niche with a real but narrow gap, and the gap is not the one
the product thesis names.** At least eleven Indian platforms already do "buy, sell
and swap used books," several of them student-first, at least two of them
hyperlocal by design, and at least one of them already shipping escrow, anonymous
chat and verified listings. The founder's instinct that *buy/sell/swap alone is
not a differentiator* is **confirmed by the evidence** — it is table stakes, and
has been since at least 2015. But the second half of the thesis, that the wedge is
*trust + proximity + exact-edition matching*, is **also already occupied**:
NearBook is explicitly "hyper-local, zero commission" and was still
**pre-revenue** when it pitched on Shark Tank India in 2025 with ~6 lakh
downloads ([sharktankaudits.com](https://sharktankaudits.com/nearbook-shark-tank-india-episode-review/),
accessed 2026-10-21). The hard finding of this audit is not that the space is
contested — it is that **almost nobody in it makes money**. Clankart, a
student-to-student used-book marketplace with 25,000+ registered students across
India, reported **$1.2K revenue per month** and was described by its own founder
as "still a part-time gig"
([starterstory.com](https://www.starterstory.com/stories/clankart), published
2023-01-02, accessed 2026-10-21). OldTextBooks.com claims "50,000+ students" while
its own listings widget reads "24 of **291**" items in stock
([oldtextbooks.com](https://www.oldtextbooks.com/), accessed 2026-10-21). The
players that *do* turn over real volume — Bookchor, UsedBooksFactory/ChennaiUsedBooks,
MyPustak — are **not marketplaces at all**: they buy inventory outright at
near-scrap prices and resell it, which is a logistics and warehousing business, not
a network business. The honest reading is that **the peer-to-peer used-book
marketplace in India is a repeatedly-attempted, rarely-monetised category**, and
that R-07 (free incumbents already work well enough) is not merely a risk — it is
the most probable explanation for why eleven attempts have produced no winner. A
real gap exists at the intersection of *campus-bounded identity, same-day physical
proximity, and edition-exact academic matching*, and no observed player serves all
three. Whether that gap is worth ₹ anything is the question Phase A primary
research must answer, because **nothing in the public record proves it is.**

---

## 2. Competitor table

Fees, coverage and trust columns record **only what was observed on the site on
2026-10-21**. "not found" means the site did not disclose it.

| # | Player | Type | How money is made | Observed fee | Coverage | Supply acquisition | Trust mechanism | Handover | Scale (sourced) | Core weakness |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **BookFlow** (bookflow.in) | C2C classifieds | not found (no fee charged) | "0% commission"; "100% Free"; also "Get 3 ads for free!" | "200+ Cities Covered" (self-reported); Chennai listed | User-posted free ads | None. Links a "Safety Tips" page; advises meeting in public | None. "Meet the buyer or ship the book" — users self-organise | "20k+ Books Listed Till now", "15k+ Happy Sellers" (self-reported) | No revenue model, no verification, no escrow, no edition field observed |
| 2 | **Bookchor** (bookchor.com) | Inventory retailer + separate resale app | Sells owned inventory; margin on buy-low/sell-high | ₹99 delivery on 1 item; free shipping above ₹499 (cart) / ₹599 (FAQ) — site contradicts itself; POD charge ₹40 | "Pan-India" delivery. **Resale arm "Dump" is "Currently available in Delhi only"** | Buys from vendors + "Dump" buyback app (ISBN scan, doorstep pickup) | "Every book is verified before listing"; 7-day replacement; 4.8/5 self-displayed | Courier | "Since 2015"; "Lakhs of books delivered" (self-reported). Owler estimate $1.5M revenue, flagged by Owler itself as an estimate | Not a marketplace. Its own C2C arm is one city after 10+ years |
| 3 | **MyPustak** (mypustak.com) | Donation-funded distribution + retail | not found | not found on site. One customer review claims "Charging only packing and forwarding charges" — a reviewer's claim, not policy | "Kashmir to Kanyakumari" (self-reported) | Donated books | "Every Book Goes Through" (sentence incomplete on page); unverified reviews | Courier | **None stated** | No disclosed economics; no stated eligibility rules; charitable framing caps pricing power |
| 4 | **OLX Chennai books** | General classifieds | Paid promotion, dealer subscriptions, ad network | Basic listing free; "featured/spotlight" ads paid | Pan-India, city-scoped | User-posted ads | None beyond reporting | User-arranged | OLX India "more than 50 million monthly active users as of 2025" (OLX's own blog) | **See §3.4 — I could not load OLX at all.** Generic: no ISBN/edition field, books compete with phones and cars for attention |
| 5 | **Campus WhatsApp / Telegram groups** | Free social channel | No money | ₹0 | Per-group, per-campus | Members post | Social identity only (you are in the group) | In-person, same day | **not found** — no study, survey or reporting located (§3.5) | Ephemeral, broadcast-only, bounded by membership, no search |
| 6 | **Chennai offline trade** (Moore Market, Luz Corner, pavement) | Cash retail | Buy-low/sell-high margin | Haggled | Chennai, physical | Walk-in sellers, bulk/raddi | Physical inspection — you hold the book | Instant, cash | **not found** | No discovery, no inventory visibility, requires travel |
| 7 | **ChennaiUsedBooks / UsedBooksFactory** | **Chennai-local buyback + national resale** | Buys at ₹5–150/book, resells at 20–60% of MRP | Free doorstep pickup (Chennai); "We have free delivery currently" | **Buys in Chennai only**; sells "anywhere in India" | **Free doorstep pickup, min. 5 books, paid on the spot by cash/UPI/GPay/Paytm** | Quality check; testimonials from SRM, VIT, Omega Intl.; charity partner | Courier to buyer; van pickup from seller | Counters present on page but values not rendered | Pays sellers near-raddi rates; takes the entire margin |
| 8 | **Clankart** (clankart.com) | C2C marketplace with escrow | **10% seller convenience fee** | "For the seller, there is just 10% convenience fee for using Clankart Teleport." "For the buyer, there is no fee." Posting free | Pan-India, **no city filter observed** | User-posted free ads | Escrow: "All payments are routed through our Clankart account", released after buyer confirms; dispute window 2 days; **no ID verification** | **Courier only** — "we only support selling of used books through Clankart Teleport" | **25,000+ registered students; $1.2K revenue/mo; founder + 3 staff; "still a part-time gig"** (Starter Story, 2023-01-02) | **The single most important datapoint in this audit — see §3.8** |
| 9 | **Bookaao** (bookaao.com) | Managed C2C marketplace | **15% seller platform fee** | "minus a platform fee of 15% of the listed price"; buyer pays weight/PIN-based delivery | "500+ cities" (self-reported); ~30 in selector | User listings + shopkeepers; **doorstep pickup or Drop Point** | **Escrow + anonymous chat (numbers not shared) + 3-day returns + "Verified Books" ranking + verified-order reviews** | Managed pickup & delivery; same-city same-day advertised | "1,00,000+ Students Served" (self-reported) | **The most complete competitor found. Already ships BookHop's trust features** |
| 10 | **NearBook** (app) | **Hyperlocal C2C app** | Zero commission — **pre-revenue at pitch** | "zero commission" (Play listing) | "major cities (Delhi, Mumbai, Bangalore)" | User listings | not found | Local; "shows your books to buyers in your immediate area first" | **~6 lakh downloads at pitch; ₹40L for 20% at ₹2cr valuation, Shark Tank India S4 E31; organic traffic reported as 0/mo** | **Closest living analogue to BookHop's thesis, and it had no revenue** |
| 11 | **BookMandee** (bookmandee.com) | C2C classifieds | not found | "Always free to list"; seller plan "₹0 / month" | Pan-India + state pages | User listings | "Verified Users (10000+)" — **contradicted by its own counters showing 0** | None — "courier at your own discretion" | ~9,681 ads across listed categories (site's own category counts) | No revenue model; self-contradicting trust claims |
| 12 | **OldTextBooks.com** | Managed C2C | Referral/commission unclear — **site states 5% and 10% in two places** | "₹0 listing fees for sellers"; suggests listing at 25% of MRP | Pan-India | User listings | "Every listing reviewed by our team"; wallet payout at ₹100 min | Courier | **Claims "50,000+ students" but inventory widget reads "24 of 291"** | Claim-to-inventory gap of ~170:1 |

**Not treated as live competitors** (evidence of non-operation in §4): Doosradeal,
Cultext, StudentDesk, CampusXchange, ResellPanda, Shopo.

---

## 3. Detailed subsections

### 3.1 BookFlow — https://bookflow.in/ and https://bookflow.in/bookflow-chat/

A pure free-classifieds board for used books, running since at least 2016
(copyright reads 2016–2026). It states **"0% commission"** and **"100% Free"**, and
separately offers "Get 3 ads for free!", which the site does not reconcile — it
never says what happens after three ads
([bookflow.in](https://bookflow.in/), accessed 2026-10-21).

- **Money:** No revenue mechanism is disclosed anywhere on the pages read. **not found.**
- **Flow:** "Meet the buyer or ship the book. Get paid instantly." The platform
  explicitly does not handle payment, delivery or escrow. Sellers may share a
  phone number or WhatsApp; otherwise buyers use BookFlow Chat.
- **Trust:** None. A Safety Tips page advises meeting in public places such as
  "colleges or cafes". No identity verification, no ratings, no escrow.
- **Scale (self-reported, unverified):** "20k+ Books Listed Till now",
  "15k+ Happy Sellers", "200+ Cities Covered". Treat as marketing copy.
- **Liveness:** Listings on the homepage were dated **2026-10-20** — the day before
  access. The site is alive, which matters: a ten-year-old free board with Chennai
  in its city list is a live substitute, not a historical one.
- **Categories:** Engineering, Medical, Competitive Exams, Novels & Fiction, School Textbooks.
- **Weakness:** It is a noticeboard. There is no edition field observed, no
  verification, no payment rail, no delivery, and no reason for either side to
  return after one transaction. Its ten-year survival is a function of near-zero
  operating cost, not of traction.
- **Blocked:** `https://bookflow.in/about-us/` returned **HTTP 404**;
  `https://bookflow.in/location/chennai/` returned **HTTP 404**. I could not
  measure Chennai supply depth on BookFlow.

### 3.2 Bookchor — https://www.bookchor.com/

Self-describes as "India's Most Loved Second Hand Bookstore Since 2015". It is
**not a marketplace** — it is an inventory retailer, and the distinction is the
single most useful thing in its profile.

- **Money:** Margin on owned stock, bought cheap and resold. Extras observed:
  extended warranty at ₹2,999 (6 months) / ₹4,999 (12 months), a ₹30 donation
  prompt, and Bookchor Pay (free delivery, no minimum).
- **Observed prices:** *The Girl in Room No 105*, condition "Good", **₹189 against
  ₹399 MRP (−50%)**. Price-band stores at **₹49 / ₹99 / ₹149 / ₹199**, plus 50%,
  65% and 80% off stores. Marketing claims savings "up to 90% compared to MRP".
- **Delivery fees:** ₹99 on a single item in the cart; "Free Shipping above ₹499"
  in the cart but "Order above ₹599 for free delivery" in the FAQ — **the site
  contradicts itself**; Pay-on-Delivery carries a ₹40 delivery charge plus a
  separate POD charge.
- **Supply:** Vendors, plus **"Dump"**, a buyback app where you scan an ISBN or
  type it, choose a pickup slot and get paid. Payout rates **not found** — the app
  copy promises only "appropriate compensation"
  ([apps.apple.com/app/id1666010367](https://apps.apple.com/app/id1666010367),
  accessed 2026-10-21).
- **The decisive fact:** **Bookchor Dump is "Currently available in Delhi only."**
  India's largest second-hand bookseller, operating since 2015, has confined its
  consumer-supply arm to one city. That is strong evidence that **collecting used
  books from individuals does not scale cheaply**, which is exactly the cost
  BookHop proposes to push onto students for free.
- **Scale:** "Lakhs of books delivered" (self-reported). Owler lists $1.5M revenue
  and 60 employees but states its own range as an estimate of $100K–$5.0M
  ([owler.com](https://www.owler.com/company/bookchor), accessed 2026-10-21) —
  **not reliable.** Semrush reported bookchor.com at **162.41 thousand visits** in
  May, majority India
  ([es.semrush.com](https://es.semrush.com/website/bookchor.com/overview), page
  dated 2025-07-07, accessed 2026-10-21). Founding capital was **₹34 lakh from
  family**, bootstrapped
  ([yourstory.com/2016/12/bookchor](https://yourstory.com/2016/12/bookchor/) — note
  this URL returned **HTTP 403** on direct fetch; the figure is quoted from search
  result extracts, so treat it as second-hand).
- **Stated difficulty, in the founders' own framing:** the second-hand books market
  is unorganised and dealing with vendors was not easy (same 403-blocked source,
  via extract).
- **Weakness:** Capital-intensive, warehouse-bound, and its peer-supply arm is
  stuck in one city. It cannot serve "I need this exact book by Thursday."
- **Data quality note:** The homepage carried a stale coupon expiring 2023-05-19
  and placeholder cart data. Treat site-stated numbers with caution.

### 3.3 MyPustak — https://www.mypustak.com/

A donation-driven distributor with a retail arm. The weakest-documented player in
the set.

- **Money:** **not found.** The site discloses no fee structure. The only pricing
  signal is a customer review stating "Charging only packing and forwarding
  charges" — **a reviewer's claim, not company policy**, and I am not treating it
  as a fact.
- **Supply:** Donated books.
- **Coverage:** "We deliver Books from Kashmir to Kanyakumari and every corner of
  the country" (self-reported).
- **Eligibility:** The mission states books go to people who cannot afford them,
  but **no request process or eligibility criteria are published.**
- **Scale:** **None stated.** No books-donated total, no user count, no review count.
- **Blocked:** `https://www.mypustak.com/faq` loaded but contained only navigation —
  no charges, no eligibility rules, no per-person limits. I could not verify the
  shipping-charge question from the primary source.
- **Relevance to BookHop:** It sets a **psychological price floor of near-zero** for
  one slice of demand. A student who will accept any readable copy of a general
  title has a free option. It does not threaten edition-exact academic demand.

### 3.4 OLX Chennai books — **BLOCKED, NOT VERIFIED**

> **I could not access OLX at all from this environment.** Four attempts:
> `https://www.olx.in/chennai_g4059162/books_c453` (ECONNRESET),
> the same URL on retry (ECONNRESET),
> `https://www.olx.in/en-in/chennai_g4059162/books_c453` (ECONNRESET), and
> the bare root `https://www.olx.in/` (ECONNRESET). The root failing identically
> means this is a **domain-level block, not a page-level one** — OLX is refusing
> this client. **Every statement below about OLX is therefore second-hand, and the
> single most important number — how many used-book listings actually exist in
> Chennai right now — is NOT VERIFIED.**

What is established from other sources:

- **Model:** Free basic listings; revenue from paid promotion (featured, spotlight,
  top-of-page) and dealer subscription packages. Sources differ on the mix, and all
  located sources are generic business-model blogs, not OLX filings — e.g.
  [fourweekmba.com](https://fourweekmba.com/how-does-olx-make-money-olx-business-model/)
  (accessed 2026-10-21). **Treat the revenue split as unverified.**
- **Scale:** OLX India's own blog states "more than 50 million monthly active users
  as of 2025"
  ([olx.in/blog/expert-advice/how-to-sell-on-olx](https://www.olx.in/blog/expert-advice/how-to-sell-on-olx/),
  accessed 2026-10-21 via search extract — **self-reported**). A secondary,
  lower-confidence source puts OLX at ~16.6M monthly visits vs Quikr's 1.46M as of
  September 2025 ([grokipedia.com/page/Quikr](https://grokipedia.com/page/Quikr),
  accessed 2026-10-21 — **encyclopedia-style, unverified**).
- **Observed weakness for books, from a third party:** "Discovery is poor for
  academic books specifically"
  ([bookmandee.com/blog/guide-to-sell-old-books-online](https://bookmandee.com/blog/guide-to-sell-old-books-online/),
  accessed 2026-10-21 — note this is a **competitor's blog**, so it has an interest
  in saying so).
- **Trust failure is well documented.** OLX/Quikr C2C fraud in India is extensively
  reported: fake "Army officer" buyers, advance-payment vanishing sellers, and
  reverse-QR scams where a "buyer" sends a QR that debits rather than credits.
  Cyberabad police linked one Rajasthan gang to 40 cases
  ([the420.in](https://the420.in/olx-fraud-conmen-pose-as-army-officers-to-steal-your-money/),
  accessed 2026-10-21); a Rohtak victim paid ₹59,200 via Paytm and received neither
  bike nor refund
  ([tribuneindia.com](https://www.tribuneindia.com/news/archive/haryana/inter-state-olx-advertisement-racket-busted-1-held-in-rohtak-775142),
  accessed 2026-10-21). **This is the strongest objective evidence for a trust
  wedge that this audit found.** Caveat: these cases are high-value items
  (vehicles, phones), not ₹200 books. Scam economics scale with ticket size, and a
  ₹150 textbook is a poor target. **Do not assume book transactions carry the same
  fraud rate — that inference is unsupported.**
- **Required follow-up:** manually open the OLX Chennai books category and count
  listings, note the ten most recent post dates, and record whether any listing
  states an edition. Until then the "OLX is thin for books in Chennai" belief is
  **an untested assumption.**

### 3.5 Campus WhatsApp / Telegram groups — **THE BIGGEST EVIDENCE GAP**

> **I ran five separate searches (three in extended mode) and found no study,
> survey, news report or reliable account of how Indian campus book-trading groups
> actually operate.** Searches covered: campus WhatsApp/Telegram book groups India;
> Reddit/Quora Indian students selling textbooks to juniors; seniors-to-juniors
> book handover; college WhatsApp group book sale mechanics. **Result: not found.**
> Given R-07 names this as the sharpest risk, **this gap is the single most
> important thing primary research must close.** No decision should rest on an
> assumed picture of how these groups work.

The only evidence located, and its limits:

- **A competitor's own guide** (interested party) says a school or college WhatsApp
  community "will frequently result in a sale within hours" with a well-worded
  message, photo and fair price; its stated drawback is that "you can only sell to
  people already in the group, and not every school community is active." Best use
  case given: "School books sold at the end of the academic year; bulk sale of a
  specific class's complete set."
  ([bookmandee.com/blog/guide-to-sell-old-books-online](https://bookmandee.com/blog/guide-to-sell-old-books-online/),
  accessed 2026-10-21). **This is marketing content from a rival platform. It is
  the only description I found, and it is not independent.**
- **One anecdote on WhatsApp-to-Telegram migration for privacy:** a bookstore owner
  in a tier-2 city moved a student book group from WhatsApp to Telegram because
  "the girls were hesitant to join as their phone numbers could get exposed"
  ([x.com/dharmeshba/status/1805480511675994297](https://x.com/dharmeshba/status/1805480511675994297),
  accessed 2026-10-21). **Single social-media anecdote, seller-run group, not
  peer-to-peer.** It is nonetheless the only located signal that **phone-number
  exposure is a felt cost in these groups** — which, if true at scale, is a
  genuine opening, and is precisely what Bookaao's anonymous chat already
  addresses (§3.9).
- **Structural precedent, non-Indian and 29 years old:** a 1997 UPenn student-run
  used-textbook newsgroup expired posts after two weeks "to keep listings current"
  ([thedp.com](https://www.thedp.com/article/1997/01/campus_briefs_thursday_january_16_1997),
  accessed 2026-10-21). Cited only to note that **listing staleness is the oldest
  known failure mode of campus book exchanges** — it long predates WhatsApp.

**What is structurally true of WhatsApp groups regardless of sourcing** (stated as
reasoning, not as sourced fact): messages are chronological and ephemeral, there is
no search by title or ISBN, no persistent inventory, no price history, membership
is capped and gated, and a book offered today is invisible to the student who needs
it in March. These are properties of the medium, not claims about usage. **But the
leap from "the medium has these properties" to "students are therefore dissatisfied"
is exactly the unvalidated step, and no evidence found supports it.**

### 3.6 Chennai offline second-hand trade

Documented but thinly. Chennai has a genuine, named second-hand book trade:

- **Moore Market area (Periamet / near Chennai Central):** described as hosting a
  large concentration of used-book stores selling "everything from classic fiction
  to academic tomes", with named stalls including Famous Book Shop, Annai Book
  Stall, Praveen Bookshop, NVS Book Stall and Baskar Book House. Haggling is
  expected and "starting prices are inflated"
  ([theculturetrip.com](https://theculturetrip.com/asia/india/articles/the-best-second-hand-bookshops-in-chennai)
  — **this URL returned ECONNRESET on direct fetch; details are from search
  extracts of it, and the piece is roughly 8 years old**).
- **Luz Corner, Mylapore:** **Murugan Old Book Stall**, a small stall "known for a
  vast collection of academic volumes that is popular with students" (same source,
  same caveat). **This is the most directly BookHop-relevant offline competitor:
  an academic-book stall, in Mylapore, that students already use.**
- **Pondy Bazaar:** **not found.** Despite being named in the brief, no source
  located documents second-hand book sellers at Pondy Bazaar. Wikipedia describes
  it only as a market on Sir Theagaraya Road, T. Nagar
  ([en.wikipedia.org/wiki/Pondy_Bazaar](https://en.wikipedia.org/wiki/Pondy_Bazaar),
  accessed 2026-10-21). **Do not repeat the Pondy Bazaar book-trade claim without
  a site visit.**
- **Chennai Book Fair** is an annual demand spike with sourced revenue: ~₹6 crore
  (2003), ~₹12 crore (2013), ₹20 crore (2020 pre-COVID), ₹12 crore (2021), and
  BAPASI reported ₹15 crore within 11 days in 2020 with ~800 stands and over 15
  lakh titles, of which **75% of exhibitors were regional-language publishers**
  ([en.wikipedia.org/wiki/Chennai_Book_Fair](https://en.wikipedia.org/wiki/Chennai_Book_Fair)
  and [indianprinterpublisher.com](https://indianprinterpublisher.com/blog/2020/01/regional-language-publications-dominate-chennai-book-fair/),
  both accessed 2026-10-21). Wikipedia also notes **"second-hand pavement shops
  outside the fair also did a good business."** No 2025 or 2026 figures found.
- **The real offline competitor is ChennaiUsedBooks** (§3.7), which explicitly
  positions itself against this trade: it describes its origin as "the
  'unorganized' Moore Market on Luz Corner" which it "reorganizes".
- **Weakness of the offline trade:** zero discovery. You cannot know whether the
  stall has your edition without travelling to Mylapore or Periamet. Pricing is
  opaque and negotiated. **Strength:** instant, cash, no account, no app, and you
  physically inspect the book — which is a complete trust mechanism requiring no
  platform at all.

### 3.7 ChennaiUsedBooks / UsedBooksFactory — **the sharpest Chennai-specific threat**

https://www.chennaiusedbooks.com/ and https://www.usedbooksfactory.com/ (accessed
2026-10-21). This player was not in the brief and should be added to the standing
competitor set.

- **Model:** Buys used books from Chennai individuals with **free doorstep pickup**,
  quality-checks them, and resells nationally through usedbooksfactory.com.
  Donated books go to government-school students via Directions Charitable Trust.
- **Published seller rate card** (this is a rare, directly-sourced price table and
  should be used as the **floor** in any BookHop pricing model):

  | Book type | Maximum paid | Average paid |
  |---|---|---|
  | Engineering | ₹100 | ₹20–50 |
  | JEE | ₹150 | ₹30–50 |
  | CBSE textbooks | ₹20 | ₹10 |
  | Novels | ₹20 | ₹5–10 |

- **Buyer-side promise:** "We guarentee a minimum 40% discount off current MRP upto
  80% discount." [sic]
- **Observed resale prices** (usedbooksfactory.com): Tinkle Comics set ₹39; Hunger
  Games trilogy ₹499; Fifty Shades trilogy ₹299; Eclipse & New Moon combo ₹349;
  kids' books "from Rs 49"; Surprise Box of 10–12 books ₹1,499; engineering "up to
  80% off"; **wholesale sold by weight**.
- **Operational terms:** minimum **5 books** for Chennai pickup; paid on the spot by
  cash, GPay, UPI or Paytm; pickup typically 3–10 days; **Chennai residents only**
  for pickup; free delivery to buyers currently.
- **The edition rule, stated explicitly:** *"NOTE : We accept educational books only
  of last 2 years due to frequent updates in edition."* **This is the strongest
  direct evidence in this audit that edition-exactness is a real, commercially
  binding constraint in the Indian used-textbook trade** — a Chennai operator with
  revenue at stake refuses stock older than two years because editions change.
- **Trust:** quality check; testimonials attributed to Omega International School,
  SRM University and VIT students; named charity partner; claims a background check
  on recipient students.
- **Claims not supportable:** "We pay you approximately 4 times the price paid in
  paper marts" — no comparison data given. Counters for "Customers", "Books
  Re-used", "Trees Saved" are present on the page but **values did not render**, so
  **scale is not found**. Shipping timelines contradict each other ("within a day"
  vs "within a week"). **No publication dates anywhere; I could not confirm the
  site is currently active.**
- **Why it is the sharpest threat:** it already owns the Chennai supply side with a
  free van, pays cash instantly, needs no counterparty match, and asks the student
  to do nothing but hand over five books. BookHop's seller proposition must beat
  **₹20–50 for an engineering book, paid today, zero effort** — and the only way to
  beat it is to deliver a higher price by finding a peer buyer, which requires
  liquidity BookHop will not have on day one.

### 3.8 Clankart — **the most important evidence in this document**

https://www.clankart.com/ and https://www.clankart.com/faq (accessed 2026-10-21).

Clankart is the closest *living* analogue to BookHop's model: a
**"Student-to-Student Bookstore"**, free to list, with payment protection.

- **Fees, quoted verbatim from the FAQ:** *"For the seller, there is just 10%
  convenience fee for using Clankart Teleport."* · *"For the buyer, there is no fee
  for using Clankart Teleport."* · *"Clankart is a free service and does not charge
  you any fees to post ads."*
- **Escrow, verbatim:** *"All payments are routed through our Clankart account."*
  Release requires the buyer to confirm delivery; *"Funds are disbursed within 3-5
  days following the delivery of the order."* Disputes must be raised **within 2
  days**. *"Clankart do not covers the return or replacement of the product."* [sic]
  Orders not shipped within 4 days auto-cancel.
- **Shipping:** *"The buyer and seller mutually agree as to who bears the shipping
  cost."*
- **Verification:** registration only. **No identity or document verification is
  described.**
- **Critical structural gap:** *"Currently we only support selling of used books
  through Clankart Teleport."* — i.e. **courier only. There is no local-handover
  path.** I fetched `https://www.clankart.com/used-books-in-chennai` and the page
  **has no city filter, no location field and no Chennai reference**; it shows 14
  undated "Newly Added Books" with no locations. **Clankart has no geography layer
  at all.** That is a genuine, verified opening.
- **And yet — the numbers.** Starter Story profile, published **2023-01-02**
  ([starterstory.com/stories/clankart](https://www.starterstory.com/stories/clankart),
  accessed 2026-10-21):
  - **$1.2K revenue/month** (~$14K/year)
  - **25,000+ registered students across India**
  - 1 founder + 3 employees; **"still a part-time gig"**
  - Launch cost: "There was no cost associated with the launch."
  - Founder on the hard part: *"On any marketplace platform, building the trust of
    both the buyer and seller is quite challenging"*, and students are
    *"accustomed to conventional 'bazaar-based' trading"*, which he calls
    *"a significant drawback."*
- **Read this carefully.** At a 10% seller fee, $1.2K/month implies roughly
  **$12K/month of GMV across all of India** — and the implied average order value
  and transaction count are the numbers BookHop's model must either beat or explain
  away. `ASSUMPTION:` if average order value is ₹250, $12K/month (≈₹10 lakh) is
  ~4,000 transactions/month nationally, i.e. **~0.16 transactions per registered
  student per month.** *Reasoning:* ₹250 is the midpoint of the observed used-book
  price bands in §5.5; GMV is derived arithmetically from a 10% take on sourced
  revenue. *Test that replaces it:* obtain Clankart's actual order count and AOV,
  or run BookHop's pilot and measure transactions per registered student per month
  directly. **Both the AOV and the resulting transaction count are unverified
  inferences, not findings.** Also note the revenue figure is from **January 2023**
  and may have changed in either direction; **no more recent figure was found.**

### 3.9 Bookaao — **the most complete competitor, and the one to benchmark against**

https://bookaao.com/ (accessed 2026-10-21). Bookaao already ships most of what
BookHop proposes as its wedge.

- **Fee, verbatim from its FAQ:** the seller is paid *"minus a platform fee of 15%
  of the listed price."* Registration is free — *"Register Free"*, *"No documents
  needed."* Buyers pay a delivery charge that *"depends on the packed weight and
  your PIN code"*, shown at checkout.
- **Trust stack already live:** escrow (payment held until delivery confirmed);
  **anonymous chat — phone numbers are not shared**; 3-day return window for
  defective, damaged or wrong books with refunds in 5–7 working days;
  **"Verified Books" ranking**; reviews restricted to **"Verified orders only"**
  (4.7★ displayed).
- **Logistics:** doorstep pickup from the seller **or drop at a nearby Drop Point**;
  **same-city orders advertised as same-day**; pan-India 3–5 working days.
  Payment-timing copy is inconsistent between two sections of the site.
- **Catalogue and prices observed:** Cengage Physics 2e (2nd hand) ₹355; Errorless
  Physics Vol 1&2 (new) ₹950; RD Sharma Class 11 (2nd hand) ₹199; HC Verma (2nd
  hand) ₹298; Cengage JEE Advanced Maths set of 5 (2nd hand) ₹1,785; MBBS bundle
  (2nd hand) ₹4,250. Rentals offered for one, two or three weeks — **rental prices
  not found.**
- **Scale (self-reported, unverified):** "1,00,000+ Students Served", "500+ Cities
  Served", "60–80% below MRP".
- **Why this matters:** "anonymous chat + escrow + verified listings + same-day
  same-city" **is** the trust-plus-proximity wedge, and it is already in market with
  a stated 15% take rate. BookHop cannot claim these as differentiators. It can only
  claim to execute them better *within a campus*, which is a much narrower and much
  less defensible claim.
- **Unverified:** I could not confirm any of Bookaao's scale claims, its real
  transaction volume, whether its 500-city claim reflects coverage or ambition, or
  whether its Chennai same-day service actually functions.

### 3.10 NearBook — the hyperlocal thesis, already tested in public

- **Positioning, from its Play Store listing:** it "shows your books to buyers in
  your immediate area first" and charges **zero commission**
  ([play.google.com/store/apps/details?id=com.show.mybook](https://play.google.com/store/apps/details?id=com.show.mybook&hl=en_IN) —
  **note: two direct fetches of this page returned truncated content and I could
  not read the download count, rating, review count or last-updated date from the
  primary source.** The description text is from search extracts.)
- **Founded 2020** by Sanjay Modi, Rajasthan
  ([indianretailer.com](https://www.indianretailer.com/article/d2c-new-commerce/perspectives/nearbooks-rs-40l-shark-tank-deal-fuels-300pc-growth-second),
  dated 2025-02-18, accessed 2026-10-21).
- **Shark Tank India Season 4, Episode 31:** asked **₹40 lakh for 20%** at a
  **₹2 crore valuation**. **All five sharks initially withdrew** before Anupam
  Mittal offered the original terms.
- **Scale at pitch:** "over 6 Lakh downloads"; **organic traffic reported as
  0 visitors/month**; described as **"a pre-revenue platform"**
  ([sharktankaudits.com](https://sharktankaudits.com/nearbook-shark-tank-india-episode-review/),
  accessed 2026-10-21).
- **Shark objections, which are effectively a free red-team of BookHop's thesis:**
  Anupam Mittal — "the classifieds industry being dominated by larger players like
  Amazon"; Namita Thapar — doubted classifieds still had sufficient market demand;
  **Kunal Bahl — opted out due to "trust issues"**; Ritesh Agarwal — mentorship, no
  money. The audit page lists NearBook's own stated challenges as *"Competition:
  Presence of dominant players like Amazon"*, *"Logistics: Managing book deliveries
  efficiently"*, and *"Awareness: Overcoming stigma against used books"*.
- **Disputed:** whether the deal closed. One tracker says "there are no signs that
  the deal ever closed". The Indian Retailer headline claims "300pc Growth" but
  **the article body does not explain or quantify it** — I fetched the article and
  confirmed the figure is unsupported in the text. **Do not cite the 300% figure.**
- **Interpretation:** a hyperlocal, zero-commission, 600k-download used-book app
  reached national television **with no revenue**. That is the clearest available
  evidence that **downloads in this category do not convert into transactions**, and
  it directly attacks the proximity half of BookHop's thesis.

### 3.11 BookMandee, OldTextBooks, and the long tail

- **BookMandee** (https://bookmandee.com/, accessed 2026-10-21): free listings
  ("Always free to list", seller plan "₹0 / month", "Post unlimited listings"),
  chat-based, **no platform-handled delivery** ("courier at your own discretion"),
  no payment rail, state-level location pages. Category ad counts shown on site:
  Competitive Exam Prep 5,718; School 2,827; Fiction 1,068; Crafts/Home 31;
  Arts/Films 29; Sports 8 — **~9,681 ads total.** Claims "Verified Users (10000+)"
  while **its own live counters read 0** with "Soon" labels. Launched 2018, Delhi
  ([yourstory.com/2019/04/delhi-startup-bookmandee-sell-donate-old-books](https://yourstory.com/2019/04/delhi-startup-bookmandee-sell-donate-old-books) —
  **this URL returned HTTP 403 on direct fetch; founding details are from search
  extracts only**). **No revenue model found after 8 years of operation.**
- **OldTextBooks.com** (accessed 2026-10-21): "₹0 listing fees for sellers";
  suggests listing at **25% of MRP**; wallet payout to UPI at ₹100 minimum; claims
  "Every listing reviewed by our team". **Referral terms stated two contradictory
  ways on the same site ("5% Referral income on buys and sells" vs "Refer a friend,
  earn 10%").** Claims **"50,000+ students"** and "Avg. savings ₹1,240 per student
  / year" — while its own inventory widget reads **"24 of 291"**. Observed prices:
  RD Sharma Class 8 (Like New) ₹438 vs ₹595 MRP; NCERT Maths Class 12 (Good) ₹61 vs
  ₹150; GMAT Official Guide 2019 (Like New) ₹800 vs ₹1,999; Essentials of Medical
  Pharmacology (Like New) ₹1,179 vs ₹1,895; BAMS 1st Prof (Like New) ₹6,400 vs
  ₹16,000. Two book requests dated "10 days ago" and "17 days ago" — **weakly
  active.** The **291-listing inventory against a 50,000-student claim is the
  clearest single illustration of the liquidity problem in this category.**
- **BooksYa** (booksya.com), **Book Thela**, **Locostreet** (Kolkata), **Pustak**
  (Mumbai), **Bookshopers**, **CampusKart** (shopcampuskart.in) — all surfaced in
  searches as further entrants. **Not individually audited; listed so the count of
  attempts is not understated.** Pustakkosh (Noida textbook rental, founded 2016)
  is **still registered as Active** per Tofler with the record updated 2026-07-04
  ([tofler.in](https://www.tofler.in/pustakkosh-book-rentals-private-limited/company/U74999DL2016PTC302274),
  accessed 2026-10-21), but **its Android app was removed from Google Play on
  2024-03-01** ([appbrain.com](https://www.appbrain.com/app/pustakkosh/com.pustakkosh.pustak),
  accessed 2026-10-21) — a registered company with a delisted app is a zombie, not
  a competitor.

---

## 4. Failed and pivoted players — what killed them

### 4.1 Doosradeal — **CONFIRMED DEAD DOMAIN, ZERO PUBLIC FOOTPRINT**

Investigated as a required item at the coordinator's instruction.

- **Primary probe (2026-10-21):** `https://doosradeal.com/` →
  **`getaddrinfo ENOTFOUND doosradeal.com`**. The domain **does not resolve in
  DNS**. This is not a server error or a block — **the domain is gone.**
- **Searches run, all returning nothing on this name:**
  1. `Doosradeal India used books marketplace startup shut down founder story` (extended)
  2. `"Doosra Deal" OR "DoosraDeal" India second hand books app students resale platform` (extended)
  3. `"doosradeal" OR "doosradeal.in" OR "doosra deal" books exchange college India` (extended)
  4. `Doosradeal startup India app Play Store "Doosra" deal marketplace resale books LinkedIn founder` (extended)
- **Result: not found.** No news coverage, no Play Store listing, no LinkedIn
  presence, no directory profile, no funding record, no archived description —
  **nothing in any search result mentions this name at all.**
- **Archive check attempted and BLOCKED:** `archive.org/wayback/available` returned
  **HTTP 429 (rate limited)** on two attempts, and `web.archive.org/cdx/...`
  returned **"Claude Code is unable to fetch from web.archive.org"**. **I could not
  retrieve any historical snapshot. What Doosradeal looked like, when it launched,
  and when it died are all unverified.**
- **Honest conclusion:** this is a **confirmed silent death** — a dead domain with
  no surviving public trace. I can confirm it is gone. **I cannot confirm what it
  was, that it was a used-book or campus marketplace, how far it got, or what
  killed it.** Anyone citing Doosradeal as a cautionary tale must not attribute a
  cause of death; there is no evidence for one.
- **Follow-up that would close this:** a Wayback Machine lookup from an
  unrestricted network, an MCA/Tofler company-registry search for the registered
  entity name, or asking the Product agent for the original source of the lead.

### 4.2 Cultext (formerly Azalea Books) — **CONFIRMED NON-OPERATIONAL, LIKELY DIED 2022**

- **Primary probe (2026-10-21):** `https://cultext.com/` →
  **`connect ECONNREFUSED 162.255.119.64:443`**. The domain **still resolves** but
  the server **actively refuses connections on HTTPS**. The site is down. (The IP
  is in a commercial shared-hosting range; registration may persist while hosting
  has lapsed.)
- **What it was:** *"the most affordable textbook exchange platform for test-prep
  and college students in India"*; **"Cultext, formerly Azalea Books, is a
  web-based platform where users can buy/sell/rent textbooks simultaneously"**
  ([rocketreach.co](https://rocketreach.co/cultext-profile_b7f67935c2ad481e),
  accessed 2026-10-21 — **third-party directory, unverified**). Founded **2020**,
  **Bhopal**, Pvt Ltd, **DPIIT/Startup India recognised** (same source).
- **Buy + sell + rent of textbooks for students is materially BookHop's scope minus
  swap, plus rental.** This is the closest dead analogue located.
- **Timeline of silence:**
  - Won the **Innonext Challenge 2.0** at B-NeST, Bhopal, in **February 2022**.
  - **Last visible post on its X account (@cultextdotcom) is dated 2022-02-08**
    ([x.com/cultextdotcom](https://x.com/cultextdotcom?lang=en) — **direct fetch
    returned HTTP 402; this date is from a search extract and is not verified from
    the primary source**).
  - RocketReach lists **0 employees** (**unverified third-party data**).
  - A YouTube channel exists and points to an `azaleabooks.herokuapp.com` address,
    consistent with the rename — and with a product that never left free hosting
    ([youtube.com/channel/UCqNpVKSEizLKccMvDKLoGhw](https://www.youtube.com/channel/UCqNpVKSEizLKccMvDKLoGhw),
    accessed 2026-10-21).
- **Funding: not found.** No investment, no investors, no revenue figure, no user
  count, no city coverage was located in any source. **Founders' names: not found.**
- **What killed it: NOT FOUND.** There is **no post-mortem, no shutdown
  announcement, no news coverage.** The pattern — incubator win February 2022,
  social silence from February 2022, dead server by 2026 — is consistent with a
  team that won a competition, graduated, and stopped. **That is an inference about
  a pattern, not a sourced cause, and must not be reported as one.**
- **The useful signal, stated carefully:** a DPIIT-recognised student textbook
  exchange, with institutional backing and a competition win, **produced no public
  trace of a single transaction** before going dark. **Both of the coordinator's
  named leads are dead, neither left a post-mortem, and neither left evidence of
  having reached meaningful volume.** For R-07 the implication is blunt: the
  failure mode in this category is not dramatic collapse, it is **silence** — these
  businesses do not blow up, they fail to ever start, which means the market gives
  almost no warning signal before the money is spent.

### 4.3 Snapdeal's Shopo — the best-documented C2C death in India

Not books, but the clearest sourced lesson about C2C marketplaces in India.

- **Shut 2017-02-10.** App-only, **zero-commission** C2C marketplace.
- **Official reason, quoted:** *"it will take some more years for a broader
  ecosystem to develop around the C2C segment"*
  ([business-standard.com](https://www.business-standard.com/article/companies/snapdeal-s-shopo-to-shut-shop-on-february-10-117020900368_1.html),
  accessed 2026-10-21).
- **Scale at death:** ~**50,000 sellers and 3 Mn+ listings** as of 2017-02-08;
  claimed to have helped 2 lakh sellers (its own blog). **No GMV or revenue was
  ever reported** ([inc42.com/buzz/shopo-shutdown](https://inc42.com/buzz/shopo-shutdown/),
  accessed 2026-10-21).
- **The lesson, from a rival C2C CEO quoted in that piece:** Saahil Goel of Kraftly
  argued the **"full stack approach is necessary"** for C2C commerce — *listing,
  discovery, payments and logistics*. **A zero-commission listings layer with 3
  million listings still died.**
- **Direct relevance to BookHop:** "we will be free and just connect people" is the
  exact model that failed here at 60× BookHop's plausible listing count. Observe
  that Clankart (10%), Bookaao (15%) and OldTextBooks all **charge**, while
  BookFlow, BookMandee and NearBook — the free ones — have **no revenue model
  found between them.**

### 4.4 Quikr — the pivot that nearly ended

- **FY22: revenue ₹49.1 crore, down 19% YoY; loss ₹21 crore; cash balance ~₹8
  crore**, reported as "on the brink"
  ([onlinemarketplaces.com](https://www.onlinemarketplaces.com/articles/indian-generalist-quikr-on-the-brink-after-another-underwhelming-year/),
  accessed 2026-10-21).
- Quikr pivoted from horizontal classifieds to verticals, with restructuring and
  workforce reductions through 2019–2020.
- A lower-confidence source reports ~16.6M monthly visits for OLX vs 1.46M for
  Quikr as of September 2025, and a first annual profit of ₹2 crore in FY2024
  ([grokipedia.com/page/Quikr](https://grokipedia.com/page/Quikr), accessed
  2026-10-21 — **unverified, encyclopedia-style**).
- **Lesson:** India's **number two** general classifieds platform, with national
  brand awareness and large funding, generated ₹49 crore of revenue and lost money
  doing it. **The ceiling on Indian C2C classifieds monetisation is low**, and books
  are one of its smallest-ticket categories.

### 4.5 The pre-launch graveyard — attempts that never shipped

Found incidentally while searching, and worth recording because they show the
**idea recurs constantly and rarely survives contact with reality**:

- **StudentDesk** (studentdesk.in) — described in search results as connecting book
  readers across institutes in Delhi, Pune, Bangalore. **Probe 2026-10-21:
  `connect ECONNREFUSED 127.0.0.1:443` — the domain resolves to localhost. It is a
  dead, parked domain.**
- **CampusXchange** (campusxchange.in, accessed 2026-10-21) — **"India's #1 Student
  Marketplace"** for graduating students to sell to incoming students, with
  verification by "institutional email or college ID", "Zero commission at launch",
  handover at "recommended safe campus spots", and categories Textbooks & Notes,
  Cycles, Gadgets, Dorm Essentials. **This is BookHop's thesis almost verbatim.** It
  is a **waitlist landing page**: no live listings, no dates, "Early Access", footer
  "Beta v0.1". It claims **"Trusted by 5,000+ Students"** while **its own impact
  counters all read zero** ("0+ Students already interested", "₹0", "0%"), and its
  trust copy references **".edu" email verification**, which is not an Indian
  college domain convention (Indian institutions use `.ac.in`). **The testimonials
  and the "Sold in 47 min" claim have no verifiable source and the listings shown
  are mockups.** Treat as a non-operating competitor and as evidence of how cheap
  this idea is to announce.
- **ResellPanda** (resellpanda.vercel.app) — claims "50,000+ student users",
  verified sellers, secure payments, hosted on a **free Vercel subdomain**. Direct
  fetch on 2026-10-21 returned **only a title line with no page content**; I could
  not verify a single listing, fee, or user. **Treat the 50,000 claim as
  unsupported.**
- **Tracxn via Business Standard:** **2,148 startups shut operations in India's
  edtech sector in the past five years**
  ([business-standard.com](https://www.business-standard.com/industry/news/over-2-000-startups-in-edtech-sector-shut-shop-in-past-five-years-125010801062_1.html),
  accessed 2026-10-21). Context only — edtech is not used books.

### 4.6 What did NOT die — and why that is also a finding

I searched specifically for shutdowns of **BookAdda, Bookchor, Pustakkosh,
BookMandee, Clankart and Locostreet** and **found no shutdown reports for any of
them.** BookAdda was **acquired** by SapnaOnline in 2014 along with Acadzone and
Koolskool ([medianama.com](https://www.medianama.com/2014/12/223-sapnaonline-acquires-bookadda-acadzone-koolskool/),
accessed 2026-10-21) and Crunchbase still lists it Active. **I found no evidence
that Flipkart or Infibeam exited the books category** — that claim should not be
repeated.

**The pattern is not death. It is dormancy.** These companies persist as registered
entities with live websites and no visible revenue: Clankart at $1.2K/month as a
part-time gig, OldTextBooks at 291 listings, BookMandee with no revenue model after
eight years, Pustakkosh with a delisted app, BookFlow coasting for a decade.
**This category does not kill companies. It strands them.** For BookHop that is the
more dangerous outcome, because a stranded business consumes years without ever
producing a clear signal to stop.

---

## 5. Category analysis

### 5.1 Textbook editions and why edition-exactness matters

This is the best-evidenced part of BookHop's thesis.

- **Prescribed editions are named in the syllabus.** Anna University's Regulation
  2021 UG syllabi specify exact editions — e.g. B.E. CSE lists *"Stuart Russell and
  Peter Norvig, 'Artificial Intelligence – A Modern Approach', **Fourth Edition**,
  Pearson Education, **2021**"*; other departments name e.g. *"Basic Civil and
  Mechanical Engineering, McGraw Hill Education; **First edition, 2018**"*
  ([cac.annauniv.edu UG R 2021](https://cac.annauniv.edu/aidetails/reg/UG%20R%202021.pdf)
  and department syllabi under `cac.annauniv.edu/aidetails/afug_2021_fu/`, accessed
  2026-10-21).
- **Regulations change and the university reserves the right to change them:** the
  R2021 regulations state the University may *"revise, amend or change the
  Regulations, curriculum, syllabus and scheme of examinations"* via the Academic
  Council with Syndicate approval (same source). Anna University runs numbered
  regulation cycles (R2017, R2021), so a cohort's prescribed list is tied to its
  regulation year.
- **A commercial operator enforces a two-year rule.** ChennaiUsedBooks states:
  *"We accept educational books only of last 2 years due to frequent updates in
  edition"* ([chennaiusedbooks.com](https://www.chennaiusedbooks.com/), accessed
  2026-10-21). **A business with cash at risk refuses older editions. That is
  stronger evidence than any claim a platform makes about itself.**
- **Edition obsolescence destroys value:** outdated editions fetch **10–20% of MRP,
  or kabadi (scrap) rates**
  ([indiapost.org](https://indiapost.org/how-to-sell-old-books-online-india),
  accessed 2026-10-21 — **secondary guide, no clear authorship**).
- **But the direction is not uniform.** For UPSC preparation, *"Old editions often
  valued more than new"*
  ([bookmandee.com guide](https://bookmandee.com/blog/guide-to-sell-old-books-online/),
  accessed 2026-10-21 — **competitor blog**). Edition logic is **course-specific**,
  not a single rule.
- **Not found:** any measurement of how often Indian students buy the wrong edition,
  what it costs them, or whether they care. **The "exact-edition matching" wedge is
  structurally plausible and commercially corroborated on the supply side, but
  there is zero evidence of student-side pain.** This is a Phase A interview question.

### 5.2 Seasonal demand shape

- **Academic year:** most Indian colleges begin in **July or August**, with the odd
  semester running July/August–December and the even semester January–May/June
  ([careers360.com](https://www.careers360.com/question-when-does-the-indian-academic-year-start),
  accessed 2026-10-21 — **Q&A site, low authority, but consistent across results**).
- **Publisher revenue is extremely concentrated, and NOT where you would guess.**
  **S. Chand does ~80% of revenue in the Jan–Mar quarter**, spending all year
  building inventory
  ([notpricedin.substack.com/p/book-smarts](https://notpricedin.substack.com/p/book-smarts),
  accessed 2026-10-21 — **independent analyst newsletter, not audited**). A sector
  outlook confirms *"sharp seasonality and working-capital intensity"* in school
  publishing with **high Q4 (Jan–Mar) concentration**
  ([multibagg.ai](https://www.multibagg.ai/deep-dive/sector-analysis/q4-fy2026-printing-and-publication-sector-outlook-cmrb1ymf4003z2rm4l7o29247),
  accessed 2026-10-21 — **unverified sector blog**).
- **This is school publishing (new books, into the trade channel), not college
  second-hand demand, and the two peaks are different.** I explicitly searched for
  an April–June peak and **found no source supporting one**.
- **One channel-level signal:** Class 10 board books show *"Peak demand April–June;
  slower other months"*; school books sell best *"at the end of the academic year"*
  ([bookmandee guide](https://bookmandee.com/blog/guide-to-sell-old-books-online/),
  accessed 2026-10-21 — **competitor blog**).
- **Chennai Book Fair** is a hard annual January demand event, with second-hand
  pavement trade documented alongside it (§3.6).

  `ASSUMPTION:` **College used-book demand in Chennai peaks in a 3–5 week window
  around semester start (late June–August), with a smaller January peak, and is
  near-zero from September–December and February–May.** *Reasoning:* semesters start
  July/August and January; a student buys course books at the start of a semester
  and sells at its end, so supply and demand peak in antiphase at the same calendar
  moments. No source measures this for Indian college used books. *Test that
  replaces it:* instrument listing and transaction counts by week through one full
  pilot year; or, faster, count new used-book listings per week on an existing
  platform's Chennai pages across 12 months. **This single assumption drives the
  entire revenue model and is currently unsupported.** If it holds, BookHop has
  roughly **8 trading weeks a year**, which changes the unit economics completely —
  fixed costs run 52 weeks against revenue earned in 8.

### 5.3 Leisure reading vs academic

- **Academic dominates the resale trade.** Every student-facing platform audited
  leads with exam/academic categories: BookFlow (Engineering, Medical, Competitive
  Exams, School); Clankart (JEE, CAT, GATE, GMAT, NCERT, RD Sharma, Arihant);
  Bookaao ("Most listings are exam-prep titles — JEE, NEET, UPSC, CAT, SSC, GATE");
  OldTextBooks (School, Engineering, Medical, Competitive, College).
- **But the resale *prices* are far higher for academic**, per ChennaiUsedBooks'
  rate card (§3.7): engineering up to ₹100 and JEE up to ₹150 versus **novels at
  ₹5–20**. A general-fiction transaction may be worth a tenth of an academic one to
  the seller.
- **Leisure demand is real but is served by inventory players at low prices**, where
  a trilogy goes for ₹299–₹499 and kids' books start at ₹49 (§3.7), and Bookchor
  runs ₹49/₹99/₹149/₹199 price-band stores (§3.2).
- **Implication for BookHop:** the two halves of the catalogue have different
  economics, different urgency and different seasonality. Academic is high-value,
  edition-sensitive, violently seasonal and matched to a syllabus. Leisure is
  low-value, edition-indifferent, aseasonal, and competes directly against a
  **₹49 price point with free delivery** from a warehouse. **Carrying both in one
  pilot risks measuring neither.**
- **Not found:** any split of the Indian used-book trade by academic vs general.

### 5.4 Language mix, including Tamil

- **Nielsen's 2015 India Book Market Report put the print market at ~₹26,000 crore,
  with English at 55% and Hindi at 35% of Indian-language sales**
  ([prathambooks.org](https://prathambooks.org/nielsens-india-book-market-repor/),
  accessed 2026-10-21). **Tamil is not broken out in any located source.**
- **A material caveat published alongside that report:** *"a large number of
  publishers, especially in Indian languages, do not use ISBNs"*, so the figure is
  *"perhaps more representative of English-language publishers in India"* (same
  source). **This has a direct product consequence: ISBN-based cataloguing — which
  Bookchor's Dump, Clankart and OldTextBooks all rely on — structurally
  under-serves Tamil-language books.** If BookHop builds ISBN-first listing, it
  inherits that blind spot.
- **Regional-language publishing dominates in Chennai specifically:**
  **75% of exhibitors at the 2020 Chennai Book Fair were regional-language
  publishers**, across ~800 stands and 15 lakh+ titles
  ([indianprinterpublisher.com](https://indianprinterpublisher.com/blog/2020/01/regional-language-publications-dominate-chennai-book-fair/),
  accessed 2026-10-21).
- **Competitors already carry Tamil:** Bookchor runs language-specific stores
  including **Tamil**, Hindi, Marathi, Malayalam, Kannada and Sanskrit;
  UsedBooksFactory has a **"Language (Tamil)"** category (§3.2, §3.7).
- **Later market sizing:** NielsenIQ BookData + Federation of Indian Publishers
  project the Indian book publishing market at **₹2 lakh crore by 2030-31** with
  print growing ~**11% CAGR**, report launched **2026-09-03**
  ([tribuneindia.com](https://www.tribuneindia.com/news/book-market/india-book-publishing-market-to-reach-rs-2-lakh-crore-by-2030-31-print-segment-growing-nearly-11-annually-report),
  accessed 2026-10-21). **Not comparable to the 2015 print-only figure** — different
  scope. Hand to MARKET-SIZING; do not use as a TAM without reconciling scope.
- **Open:** what share of a Chennai campus's books are Tamil-medium, whether Tamil
  titles carry ISBNs reliably, and whether engineering students in Chennai study in
  English regardless of language background. **All unverified.**

### 5.5 Condition grading and observed price bands

**No Indian platform audited publishes a defined grading scale.** Bookchor shows a
condition field ("Good") and says condition is "clearly mentioned on each product
page" but defines no scale; UsedBooksFactory makes general quality claims with no
grades; Bookaao has an unexplained "Verified Books" ranking; OldTextBooks uses
"Like New" and "Good" labels without definitions. International practice is no
better: AbeBooks states criteria *"may vary by seller and region"*, defines Very
Good and Good loosely, and **does not define "Acceptable" at all**
([abebooks.com grading guide](https://www.abebooks.com/books/rarebooks/collecting-guide/understanding-rare-books/guide-book-conditions.shtml),
accessed 2026-10-21). **A published, enforced, photo-backed grading scale is
therefore genuinely unoccupied ground — and it is cheap to build.**

**Observed price bands, as % of MRP** (two secondary sources, broadly consistent):

| Condition | % of MRP | Source |
|---|---|---|
| Like new | 55–65% | [bookmandee guide](https://bookmandee.com/blog/guide-to-sell-old-books-online/) |
| Good | 40–55% | same |
| Fair | 25–40% | same |
| Poor | 10–25% | same |
| Near-new current-edition exam guides | 50–60% | [indiapost.org](https://indiapost.org/how-to-sell-old-books-online-india) |
| Clean school textbooks | 40–50% | same |
| Popular fiction | 30–50% | same |
| Outdated editions | 10–20% or scrap | same |

**Both are secondary guides with commercial interests** (one is a competitor's blog,
one has no clear authorship). They agree closely, which is mild corroboration, not
proof.

**Observed absolute prices** (primary, from the sites themselves, 2026-10-21):
₹39 (Tinkle set) · ₹49 (kids', from) · ₹61 (NCERT Maths 12, Good, vs ₹150 MRP) ·
₹189 (Chetan Bhagat, Good, vs ₹399) · ₹199 (RD Sharma 11) · ₹250–₹500 (BookFlow
homepage listings) · ₹298 (HC Verma) · ₹299–₹499 (trilogies) · ₹355 (Cengage
Physics) · ₹438 (RD Sharma 8, Like New, vs ₹595) · ₹800 (GMAT OG 2019, vs ₹1,999) ·
₹1,179 (Medical Pharmacology, vs ₹1,895) · ₹1,785 (Cengage JEE set of 5) ·
₹4,250 (MBBS bundle) · ₹6,400 (BAMS 1st Prof, vs ₹16,000).

**The price floor — what a seller's alternative actually pays:**

| Channel | What the seller gets | Source |
|---|---|---|
| Kabadiwala / raddi | **₹8–15/kg** (Bengaluru ₹8/kg; Delhi ₹11–15/kg; Varanasi ₹12/kg) | [thekabadiwala.com](https://www.thekabadiwala.com/scrap-rates/Bangalore), [delhikabadiwala.com](https://www.delhikabadiwala.com/rate-list/), accessed 2026-10-21 — **dealer-published, indicative only** |
| Local second-hand bookshop | **10–20% of cover price**, resold at 40–60% | [bookmandee guide](https://bookmandee.com/blog/guide-to-sell-old-books-online/) |
| **ChennaiUsedBooks (free pickup)** | **Engineering ₹20–50 (max ₹100); JEE ₹30–50 (max ₹150); CBSE ₹10 (max ₹20); novels ₹5–10 (max ₹20)** | [chennaiusedbooks.com](https://www.chennaiusedbooks.com/) — **primary, published rate card** |
| Peer sale (what BookHop promises) | 40–55% of MRP, minus fee, minus effort, minus waiting | derived from bands above |

**This table is the heart of the seller-side argument.** A ₹650 NEET book goes for
**₹8–15/kg as raddi** versus **₹260 listed honestly at 40% of MRP**
([bookmandee guide](https://bookmandee.com/blog/guide-to-sell-old-books-online/)).
The same guide's blunt framing of why sellers take the bad deal anyway: *"The raddi
wala is always there. He will always take your books, and he will always give you
almost nothing for them."* **BookHop's seller-side value is a genuine 10–30×
improvement on the scrap price — but only if a buyer actually appears.** The raddi
wala's conversion rate is 100%.

### 5.6 Repeat purchase frequency — **largely not found**

- **No Indian government, NCAER or industry figure for books purchased per person
  per year was located.** The only number found is **16 books/year for India** from
  a commercial ranking of self-identifying book readers in 102 countries
  ([ceoworld.biz](https://ceoworld.biz/2024/06/03/ranked-countries-that-reads-the-most-books-2024/),
  accessed 2026-10-21). **This surveys readers, not the population, and is a
  reading figure, not a purchase figure. Do not use it in the model.**
- Older NOP World figures ranking India first at ~10.4–10.7 reading hours/week were
  publicly challenged on sampling grounds
  ([csmonitor.com](https://www.csmonitor.com/layout/set/amphtml/Arts-Culture/Books/chapter-and-verse/2014/0304/Which-country-reads-most-Hint-It-s-not-the-US),
  accessed 2026-10-21). **Not usable.**
- **No platform in this audit discloses repeat-purchase rate, orders per user, or
  cohort retention. Not one.** That absence is itself informative: if any of them
  had a good retention number, it would be on the homepage next to "50,000+
  students".

  `ASSUMPTION:` **A Chennai college student completes 1–2 used-book transactions
  per academic year, concentrated at semester boundaries.** *Reasoning:* a semester
  prescribes roughly 5–8 courses; a student buying second-hand would do so in one
  or two batched sessions at semester start and dispose at semester end; academic
  books are not an impulse category. The brief records "2 transfers/year" as already
  explicitly unverified in the agent charter. *Test that replaces it:* pilot
  telemetry — completed transfers per registered user per semester — or, pre-pilot,
  a 100-student intercept survey at 2 Chennai campuses asking how many used books
  they bought and sold in the last 12 months and through which channel. **Until
  that runs, every frequency number in the financial model is a guess, and the
  model's output range should reflect that.**

---

## 6. Why would a student switch?

### 6.1 The strongest honest case FOR switching

Stated as the best argument the evidence actually supports, with each leg sourced.

1. **No existing channel does edition-exact academic matching, and editions are
   commercially binding.** Anna University prescribes named editions and years
   (§5.1). ChennaiUsedBooks refuses academic stock older than two years *because
   editions change* (§3.7). Outdated editions crash to 10–20% of MRP (§5.1). Yet
   **no platform audited has an edition-aware matching feature** — OLX has no ISBN
   field, WhatsApp groups are free text, and Clankart/Bookaao catalogue by ISBN for
   *listing* but not for *"does this satisfy my syllabus requirement."* A student's
   actual question is not "is there a cheap Russell & Norvig" but **"is there the
   4th edition that HS3152 requires, near me, this week."** Nothing answers that.
2. **Clankart, the closest student-to-student competitor, has no geography layer at
   all.** Verified directly: `clankart.com/used-books-in-chennai` **has no city
   filter, no location field, no Chennai reference**, and Clankart's FAQ states it
   supports **courier only** (§3.8). A Chennai student buying from Clankart waits
   days and pays shipping for a ₹200 book — an absurd ratio. **Same-day campus
   handover is a real, verified gap in the most comparable product.**
3. **Shipping economics are broken for a ₹200 item, and everyone else ships.**
   Bookchor charges ₹99 delivery on a single item (§3.2). Bookaao charges by weight
   and PIN code (§3.9). Clankart makes buyer and seller negotiate who pays (§3.8).
   **On a ₹189 book, ₹99 of delivery is 52% of the item price.** A handover that
   happens on a walk between two lecture halls removes the largest single cost in
   the category. **This is the most quantitatively defensible leg of the argument.**
4. **The seller's realistic alternatives pay 10–30× less.** Raddi pays ₹8–15/kg;
   ChennaiUsedBooks pays ₹20–50 for an engineering book; a peer sale at 40–55% of
   MRP on a ₹600 textbook is ₹240–₹330 (§5.5). **The seller-side value gap is
   large, sourced, and not disputed by any source found.**
5. **Trust in Indian C2C is a documented, policed problem, and the one anecdote
   found about campus groups is about privacy.** OLX fraud patterns are extensively
   reported (§3.4). A Shark explicitly declined NearBook on "trust issues" (§3.10).
   The single located account of an Indian student book group describes migrating
   off WhatsApp **because phone numbers were exposed** (§3.5). **Verified-student
   identity with no phone-number exposure addresses a cost that at least one
   real-world group acted on.**
6. **Nobody publishes a condition grading scale** (§5.5). A defined, photo-backed
   grade is cheap to build and genuinely unoccupied.

**Compressed to one sentence:** *A Chennai engineering student needing the exact
prescribed edition of a ₹600 textbook in the first fortnight of a semester has no
channel that can tell her a verified classmate 400 metres away has that precise
edition, in a stated condition, for ₹250, handed over this afternoon with no
shipping cost and no phone number exchanged — and the seller's only alternative
pays her ₹30.*

### 6.2 The strongest counter-argument — that she would NOT switch

This is the better-evidenced side. **I judge the counter-argument currently
stronger than the case for.**

1. **The prize per student per year is too small to change behaviour.** At
   `ASSUMPTION:` 1–2 transactions/year (§5.6) and an observed used-book price band
   of ₹60–₹400 for most student titles (§5.5), the **annual saving at stake is
   plausibly ₹300–₹1,200**. OldTextBooks' own marketing claims "Avg. savings ₹1,240
   per student / year" (§3.11, self-reported, unverified) — i.e. **even the vendor's
   best case is about ₹100/month.** Behaviour change, app installation, identity
   verification and coordination overhead are being asked for in exchange for
   roughly the price of two coffees a month. **Free incumbents cost zero effort to
   continue using.**
2. **The hyperlocal used-book thesis has already been tested in public and produced
   no revenue.** NearBook: explicitly "shows your books to buyers in your immediate
   area first", zero commission, **~6 lakh downloads, pre-revenue, 0 organic
   visitors/month** (§3.10). **600,000 people downloaded the proximity promise and
   it generated nothing.** This is the most direct refutation of the thesis in the
   entire audit.
3. **The student-to-student model has a decade of evidence and the ceiling is
   visible.** Clankart: 25,000+ registered students, **$1.2K/month**, founder calls
   it a part-time gig (§3.8). OldTextBooks: 50,000-student claim, **291 listings**
   (§3.11). BookMandee: 8 years, ~9,681 ads, **no revenue model** (§3.11). BookFlow:
   10 years, **no revenue model** (§3.1). **Five independent teams, same ceiling.**
4. **Liquidity cannot survive the seasonality.** If demand concentrates into ~8
   trading weeks a year (`ASSUMPTION:` §5.2), then for ~44 weeks the marketplace is
   visibly empty — and an empty marketplace teaches users to stop opening it. Worse,
   **supply and demand peak in antiphase**: sellers have books at semester *end*,
   buyers need them at semester *start*. Without inventory BookHop does not hold,
   the two sides may never be in the market simultaneously. **This is a structural
   objection and no amount of UX solves it.**
5. **Zero-commission listing boards die even at 60× the scale.** Shopo shut with
   50,000 sellers and 3M listings, and the lesson drawn by a rival CEO was that C2C
   requires the **full stack** — listing, discovery, payments, logistics (§4.3). A
   campus handover model deliberately omits logistics, which is the expensive part,
   but also omits the thing that makes the transaction reliable.
6. **The gap BookHop names is already being closed by a funded, shipping
   competitor.** Bookaao already has escrow, **anonymous chat so phone numbers are
   not shared**, verified-order reviews, a Verified Books ranking, drop points, and
   **same-city same-day delivery**, at a 15% take rate (§3.9). BookHop's trust
   features are not novel; they are **catch-up**.
7. **The supply side is already being vacuumed up in Chennai, for free, with a
   van.** ChennaiUsedBooks offers **free doorstep pickup, 5-book minimum, cash on
   the spot** (§3.7). For a graduating student clearing a shelf, that is strictly
   easier than listing six books individually and waiting for matches. **BookHop
   competes for supply against a service that requires the seller to do nothing.**
8. **Senior-to-junior handover may be social, not commercial, and price may not be
   the binding constraint.** `ASSUMPTION:` **a meaningful share of campus book
   transfer happens as a gift or favour within existing social ties rather than as
   a priced transaction.** *Reasoning:* the brief's own R-07 identifies campus
   groups as free incumbents; a book passed to a junior creates social credit worth
   more than ₹200 to the giver. *Test:* ask 100 students what happened to their last
   semester's books, with "gave to a junior/friend" as an explicit option alongside
   sold, kept, and scrapped. **If gifting dominates, BookHop is not competing on
   price or trust — it is competing against reciprocity, and it loses.** This is the
   highest-leverage single question in Phase A and it is **entirely unanswered.**
9. **Both named prior attempts at this exact idea are dead with no post-mortem**
   (§4.1, §4.2), and a third (CampusXchange) is a waitlist page with fabricated-
   looking counters (§4.5). **The idea is cheap to have, cheap to announce, and
   historically has not survived.**
10. **The campus-bounded design caps the market at precisely the point where
    liquidity is thinnest.** A single campus might hold a few thousand students; the
    probability that one of them is selling the exact edition you need, in the week
    you need it, is a function of density that **nobody in this audit has ever
    achieved** — including the national players with 25,000–100,000 users.

### 6.3 My assessment as the owning agent

**The switching argument is real but narrow, and it is weaker than the counter.**
The verified gaps — Clankart has no geography, everyone ships at ₹99 on a ₹189
book, nobody grades condition, nobody matches editions — are genuine. But they are
**gaps nobody has monetised**, and the most likely reason is the one the evidence
keeps repeating: **the per-student annual value at stake is too small to pay for a
marketplace.** Five independent teams hit the same ceiling; a 600k-download
hyperlocal app earned nothing; the two closest prior attempts died silently.

Per my charter I must say plainly whether this can be a business. On the public
evidence available today: **a Chennai student-only used-book marketplace is not
demonstrably a business.** It may be a feature, a wedge into a larger campus
commerce surface, or a service that works only if BookHop takes inventory risk the
way Bookchor and ChennaiUsedBooks do. **I am not recommending a kill** — the
evidence is about *other people's execution*, and none of these players combined
campus identity, same-day handover and edition matching. **I am saying the burden
of proof sits squarely on Phase A primary research, and that the two numbers that
decide it are transactions-per-student-per-year and what share of campus book
transfer is gifting rather than selling.** Neither is known. Both are cheap to
measure. **Measure them before anything is built.**

---

## 7. Open questions only primary research with real students can settle

Ordered by how much they move the decision. Each names the instrument — per
README §8, these are instruments, not results. **No interviews have been run and no
results are reported anywhere in this document.**

| # | Question | Why it decides the business | Instrument |
|---|---|---|---|
| **Q1** | **What actually happened to your books from last semester?** Sold / gave to a junior or friend / kept / scrapped / still on the shelf. | If gifting and hoarding dominate, there is no supply to intermediate and the model fails regardless of product quality. **Highest leverage question in Phase A.** | 100-student intercept survey, 2–3 Chennai campuses, single forced-choice question plus "to whom" |
| **Q2** | **How many used books did you buy and sell in the last 12 months, and through which channel?** | Replaces the `ASSUMPTION:` of 1–2 transactions/year (§5.6) that drives the entire financial model. | Same survey, recall question with channel list: WhatsApp group, OLX, senior/friend, Moore Market/Luz, Bookchor/online, didn't |
| **Q3** | **Show me your campus book group.** How many members, how many book posts in the last 30 days, how many resulted in a transfer, how are prices set, what happens to a post after a day? | §3.5 is the largest evidence gap in this audit and is the core of R-07. **Nothing in the public record describes these groups.** | Screen-share walkthrough with 8–10 students across 3 campuses; count posts and outcomes directly rather than asking |
| **Q4** | **Have you ever bought the wrong edition, or avoided a used book because you were unsure of the edition? What did it cost you?** | Edition-exactness is the best-evidenced *supply-side* constraint (§5.1) with **zero student-side evidence**. If students don't feel it, the wedge is imaginary. | Structured interview, 15 students, with two physical copies of different editions of a prescribed title as a prompt |
| **Q5** | **Would you hand over a book to a stranger from your own college? What would make you not?** And: would you give a stranger your phone number to do it? | Tests whether campus identity is sufficient trust, and whether phone-number exposure (§3.5) is a real felt cost or a one-off anecdote. | Interview + a concrete scenario; compare against the existing WhatsApp/OLX alternative, not against nothing |
| **Q6** | **Here is ₹250 for your used ₹600 textbook, paid in 7 days when a buyer appears — versus ₹40 cash today with free doorstep pickup. Which?** | Directly tests BookHop's seller proposition against **ChennaiUsedBooks' verified published rate card** (§3.7). If students take the ₹40, the supply side is gone. | Forced-choice with real numbers from §5.5; vary the wait (same day / 1 week / 1 month) to find the patience threshold |
| **Q7** | **How many relevant listings would need to exist before you'd check the app a second time?** | Tests the liquidity threshold and the 44-empty-weeks problem (§6.2 item 4). | Concept test with seeded mock inventory at 3 densities (5 / 50 / 200 Chennai listings) |
| **Q8** | **In which weeks of the year would you actually use this?** | Replaces the seasonality `ASSUMPTION:` in §5.2 that determines whether there are 8 or 40 trading weeks. | Calendar exercise: mark buying and selling weeks on a 12-month grid |
| **Q9** | **What fraction of your prescribed books are Tamil-medium, and do they have ISBNs?** | Determines whether ISBN-first cataloguing — which every competitor uses — structurally excludes part of the Chennai catalogue (§5.4). | Photograph 20 students' actual book stacks; check for ISBN and language |
| **Q10** | **Would you pay a 10% fee — and would you pay it rather than meeting the person for free?** | Clankart charges 10%, Bookaao 15% (§3.8, §3.9); the free players have **no revenue model found**. Local handover makes fee avoidance trivial — both parties can simply meet and not tell the app. **Disintermediation is an unexamined existential risk to the revenue model.** | Willingness-to-pay ladder, plus a direct question on whether they would transact off-platform after matching |

### Research that does not need students, and should run in parallel

- **Unblock and count OLX.** Open `olx.in/chennai_g4059162/books_c453` manually,
  record the listing count, the ten most recent post dates, and whether any listing
  states an edition. **§3.4 is currently unverified and it is a named competitor.**
- **Visit Luz Corner (Murugan Old Book Stall) and the Moore Market complex.**
  Record actual asking prices for 10 prescribed Anna University titles, whether
  editions are stocked and stated, and whether students are present. **The only
  source on the Chennai offline trade is an ~8-year-old travel article that I could
  not even fetch directly** (§3.6).
- **Confirm or drop the Pondy Bazaar claim.** No source supports a second-hand book
  trade there (§3.6).
- **Recover the Doosradeal and Cultext histories** via the Wayback Machine from an
  unrestricted network and an MCA/Tofler registry search. **Both archive routes were
  blocked from this environment** (§4.1, §4.2).
- **Count Chennai supply depth on Bookaao, NearBook and BookFlow** by searching
  Chennai PIN codes. If a funded competitor has 40 Chennai listings, that is the
  realistic ceiling BookHop inherits.
- **Install NearBook and complete one transaction end to end.** It is the closest
  living analogue and the cheapest competitive intelligence available.

---

## 8. Register of what this audit could NOT verify

Recorded explicitly so no downstream agent treats absence as evidence.

| Item | Status | Reason |
|---|---|---|
| **OLX Chennai books — listing count, prices, recency, edition fields** | **BLOCKED** | 4 attempts, all `ECONNRESET`, including the bare root `olx.in` — domain-level block |
| **Wayback Machine snapshots for Doosradeal and Cultext** | **BLOCKED** | `archive.org/wayback/available` → HTTP 429 ×2; `web.archive.org/cdx` → "Claude Code is unable to fetch from web.archive.org" |
| **What Doosradeal was, when it launched, what killed it** | **NOT FOUND** | DNS `ENOTFOUND`; 4 searches (3 extended) returned **zero mentions of the name anywhere** |
| **What killed Cultext; its founders; its funding; its users** | **NOT FOUND** | No post-mortem, no coverage; `cultext.com` → `ECONNREFUSED`; X fetch → HTTP 402 |
| **How Indian campus WhatsApp/Telegram book groups actually operate** | **NOT FOUND** | 5 searches (3 extended). Only sources: a competitor's blog and one X anecdote. **Largest gap; directly equals R-07** |
| **NearBook download count, rating, review count, last-updated date** | **NOT VERIFIED** | Play Store page returned truncated content on 2 fetches; figures are from search extracts only |
| **Bookchor's founding capital, sourcing detail** | **SECOND-HAND** | `yourstory.com/2016/12/bookchor` → **HTTP 403**; quoted from search extracts |
| **BookMandee founding details** | **SECOND-HAND** | `yourstory.com/2019/04/...bookmandee` → **HTTP 403** |
| **Chennai offline book trade** | **WEAK** | `theculturetrip.com` → **ECONNRESET**; details from extracts of an ~8-year-old article |
| **Pondy Bazaar second-hand book trade** | **NOT FOUND** | No source supports the claim; do not repeat it |
| **MyPustak charges and eligibility rules** | **NOT FOUND** | FAQ page loaded but contained only navigation |
| **BookFlow Chennai listing depth** | **BLOCKED** | `/about-us/` and `/location/chennai/` both **HTTP 404** |
| **Any competitor's real GMV, order count, AOV, retention or repeat rate** | **NOT FOUND** | **Not one of the twelve players discloses any of these** |
| **Tamil-language share of the Indian book market** | **NOT FOUND** | Nielsen 2015 breaks out English and Hindi only |
| **Indian per-capita book purchase frequency** | **NOT FOUND** | Only a commercial reader-survey "16 books/year" figure, which is reading not purchasing — **unusable** |
| **Academic vs general split of the Indian used-book trade** | **NOT FOUND** | — |
| **Whether Clankart's 2023 revenue figure still holds** | **STALE** | Starter Story dated 2023-01-02; no later figure found |
| **ResellPanda's "50,000+ student users"** | **UNSUPPORTED** | Page returned title line only; free Vercel subdomain |
| **CampusXchange's "5,000+ Students"** | **CONTRADICTED** | Its own on-page counters read 0 |
| **OldTextBooks' "50,000+ students"** | **CONTRADICTED** | Its own inventory widget reads 291 items |
| **BookMandee's "10000+ Verified Users"** | **CONTRADICTED** | Its own counters read 0 with "Soon" labels |
| **Bookaao's "1,00,000+ Students Served", "500+ Cities"** | **UNVERIFIED** | Self-reported, no corroboration found |

---

## 9. Changes recommended to the standing competitor set

The brief named six competitors. This audit found **six more that are equally or
more relevant**, three of which were not previously tracked anywhere:

- **ADD — Bookaao** (§3.9): most complete feature set; already ships escrow,
  anonymous chat and same-city same-day; 15% take rate. **Benchmark against this,
  not BookFlow.**
- **ADD — Clankart** (§3.8): closest student-to-student model; 10% fee; **verified
  to have no geography layer**; its $1.2K/month is the category's reality check.
- **ADD — ChennaiUsedBooks / UsedBooksFactory** (§3.7): **the Chennai-specific
  supply-side competitor**, with a published rate card and a free van. Directly
  contests BookHop's sellers.
- **ADD — NearBook** (§3.10): the hyperlocal thesis, publicly tested, pre-revenue.
- **ADD — OldTextBooks, BookMandee** (§3.11): long-tail evidence of the ceiling.
- **DOWNGRADE — MyPustak** (§3.3): donation-driven, no disclosed economics, not a
  competitor for edition-exact academic demand.
- **FLAG — OLX** (§3.4): **remains unverified**; cannot be ranked until someone
  opens it manually.

---

*Prepared by the Market & Finance agent. Every claim above is sourced or tagged.
Where this document says "not found", that is a result, not an omission — and
several of those results, particularly §3.5 and §4.1–4.2, are among the most
important findings here.*
