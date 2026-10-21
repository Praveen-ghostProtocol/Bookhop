"""BookHop market sizing + unit economics. All arithmetic for MARKET-SIZING.md and MODEL.md.
Run: python -I model.py
"""

# ---------- 1. Sourced campus enrolment (NIRF / institutional submissions) ----------
# (name, UG+PG headcount, PhD headcount, academic year, district)
TECH = [
    ("IIT Madras (all disciplines)",            3589+1186+172+1859+507+199, 2469+242, "2023-24", "Chennai"),
    ("Anna University (univ. depts only)",      9197+316+2119+308,          1157+652, "2023-24", "Chennai"),
    ("SRM IST (all campuses, not separable)",   10749+37775+3582+7120+707+532+180, 1760+881, "2023-24", "Chengalpattu+"),
    ("VIT (Vellore+Chennai, not separable)",    4407+35957+1367+11+4861+7651, 4516+626, "2023-24", "Vellore+Chennai"),
    ("Sathyabama IST (all disciplines)",        2088+11936+1321+12+1280+21, 552+362,  "2023-24", "Chennai"),
    ("HITS (engineering only - partial)",       4197+86,                    117+312,  "2023-24", "Chengalpattu"),
    ("SSN College of Engineering",              3594+221+62,                241+248,  "2023-24", "Chengalpattu"),
    ("Vel Tech R&D Institute (eng only)",       9462+216,                   179+407,  "2023-24", "Tiruvallur"),
    ("SIMATS Saveetha (all disciplines)",       9703+2810+31+732+711,       658+849,  "2023-24", "Chennai"),
    ("Saveetha Engineering College",            5797+164,                   61+143,   "2024-25", "Kancheepuram"),
    ("BSA Crescent IST (eng only - partial)",   3932+138,                   33+147,   "2023-24", "Chengalpattu"),
    ("St. Joseph's Coll. of Engineering",       5849+19,                    32+153,   "2024-25", "Chennai"),
    ("Rajalakshmi Engineering College",         7938+239,                   123+251,  "2023-24", "Tiruvallur"),
    ("Panimalar Engineering College",           10692+30,                   3+87,     "2024-25", "Tiruvallur"),
    ("Dr. M.G.R. E&RI (eng+arch+dental only)",  6996+362+335+119+440+100,   338+160+30+24, "2023-24", "Chennai"),
]
ARTS = [
    ("University of Madras (depts, PG only)",   3287+97,       1022+464, "2023-24", "Chennai"),
    ("Loyola College",                          7851+1496,     0, "2023-24", "Chennai"),
    ("Madras Christian College",                5584+1314,     0, "2023-24", "Chengalpattu"),
    ("Stella Maris College",                    4603+255+823,  0, "2023-24", "Chennai"),
    ("Presidency College",                      3765+1093,     0, "2023-24", "Chennai"),
    ("Ethiraj College for Women",               6452+1297,     0, "2023-24", "Chennai"),
    ("Women's Christian College",               3577+738,      0, "2022-23", "Chennai"),
    ("Queen Mary's College",                    4413+608,      0, "2024-25", "Chennai"),
    ("D.G. Vaishnav College",                   9659+1251,     0, "2023-24", "Chennai"),
    ("Guru Nanak College",                      6574+653,      0, "2022-23", "Chennai"),
    ("RKM Vivekananda College",                 3342+170,      0, "2024-25", "Chennai"),
    ("Pachaiyappa's College",                   3037+438,      0, "2023-24", "Chennai"),
    ("MOP Vaishnav College for Women",          3474+514,      0, "2024-25", "Chennai"),
    ("The New College",                         6004+456,      0, "2024-25", "Chennai"),
    ("SRM Arts and Science College",            2733+543,      0, "2024-25", "Chengalpattu"),
]

def show(rows, label):
    print(f"\n--- {label} ---")
    for n, ugpg, phd, ay, d in rows:
        print(f"{n:42s} {ugpg:7,d} UG+PG  {phd:6,d} PhD  {ay}  {d}")
    s_ugpg = sum(r[1] for r in rows); s_phd = sum(r[2] for r in rows)
    print(f"{'SUBTOTAL':42s} {s_ugpg:7,d}        {s_phd:6,d}")
    return s_ugpg, s_phd

t_ugpg, t_phd = show(TECH, "Technical / professional")
a_ugpg, a_phd = show(ARTS, "Arts & science")
ALL_UGPG = t_ugpg + a_ugpg
ALL_PHD  = t_phd + a_phd
print(f"\nNAMED-CAMPUS SOURCED FLOOR (30 institutions): {ALL_UGPG:,d} UG+PG, {ALL_PHD:,d} PhD, total {ALL_UGPG+ALL_PHD:,d}")

# Chennai-metro-only subset: drop the two that are not separable from non-Chennai campuses
NONSEP = {"SRM IST (all campuses, not separable)", "VIT (Vellore+Chennai, not separable)"}
chennai_floor = sum(r[1] for r in TECH + ARTS if r[0] not in NONSEP)
print(f"Floor excluding the 2 non-separable multi-campus filings: {chennai_floor:,d} UG+PG")

# ---------- 2. AISHE context ----------
AISHE = {
    "India total enrolment (all modes)":      45001123,
    "India regular mode":                     39664479,
    "Tamil Nadu total enrolment (all modes)": 3577047,
    "Tamil Nadu regular mode":                3193831,
    "Tamil Nadu colleges":                    2983,
}
print("\n--- AISHE 2023-24 ---")
for k, v in AISHE.items():
    print(f"{k:42s} {v:,d}")
tn_share = AISHE["Tamil Nadu regular mode"] / AISHE["India regular mode"]
print(f"TN share of India regular-mode enrolment: {tn_share:.1%}")
print(f"Named floor as share of TN regular mode : {chennai_floor/AISHE['Tamil Nadu regular mode']:.1%}")

# ---------- 3. Chennai metro denominator: proxy range (ASSUMPTION, error bars) ----------
# Proxy A: DCE college-count share, 4 metro districts = 191 of 1,566 TN colleges = 12.2%.
#          Understates: metro colleges are larger than the TN average.
# Proxy B: Anna University affiliated-college statistics, Chennai *region* = 142 of 488 (29.1%),
#          but that region spans 10 districts, so the 4-district subset is lower.
PROXY_A = 191/1566
print(f"\nProxy A (DCE 4-district college share): {PROXY_A:.1%} -> {PROXY_A*AISHE['Tamil Nadu regular mode']:,.0f}")
print(f"Proxy B (Anna Chennai region share)   : {142/488:.1%} (10 districts, upper bound)")
CHENNAI = {"low": 320_000, "base": 460_000, "high": 650_000}   # regular-mode higher-ed, 4 metro districts
for k, v in CHENNAI.items():
    print(f"  Chennai metro regular-mode enrolment, {k:4s}: {v:,d}  (floor coverage {chennai_floor/v:.0%})")

# ---------- 4. Driver table ----------
D = {
#  driver                        low        base       high
 "pct_adult":                  (0.90,      0.95,      0.97),
 "pct_book_active":            (0.35,      0.60,      0.75),
 "signup_rate_y1":             (0.04,      0.15,      0.30),
 "activation_rate":            (0.10,      0.30,      0.45),
 "transfers_per_active_yr":    (1.10,      1.80,      3.00),
 "swap_share":                 (0.40,      0.20,      0.10),
 "gift_share_of_nonswap":      (0.30,      0.15,      0.08),
 "avg_book_price_inr":         (140.0,     220.0,     350.0),
 "take_rate":                  (0.00,      0.06,      0.10),
 "fee_collection_rate":        (0.20,      0.55,      0.80),
 "inapp_payment_share":        (0.20,      0.50,      0.75),
 "pg_cost_pct":                (0.0236,    0.0236,    0.0099),
 "support_cost_per_transfer":  (30.0,      12.0,      6.0),
 "infra_cost_per_user_yr":     (40.0,      18.0,      8.0),
 "cac_per_registered_user":    (180.0,     60.0,      25.0),
 "fixed_cost_y1_inr":          (1_500_000, 900_000,   500_000),
}
CASES = ("low", "base", "high")
IDX = {c: i for i, c in enumerate(CASES)}
def g(k, case): return D[k][IDX[case]]

def rev_per_transfer(case):
    return (g("take_rate",case) * (1-g("swap_share",case)) * (1-g("gift_share_of_nonswap",case))
            * g("avg_book_price_inr",case) * g("fee_collection_rate",case))
def varcost_per_transfer(case):
    """MARGINAL cost only: payment processing + support. CAC and infra are charged
    per REGISTERED USER, not per transfer, and therefore are not marginal to a transfer."""
    return (g("avg_book_price_inr",case)*(1-g("swap_share",case))*(1-g("gift_share_of_nonswap",case))
            * g("inapp_payment_share",case)*g("pg_cost_pct",case) + g("support_cost_per_transfer",case))

def run(students, case, include_cac=True, include_fixed=True):
    addressable = students * g("pct_adult", case) * g("pct_book_active", case)
    registered  = addressable * g("signup_rate_y1", case)
    active      = registered * g("activation_rate", case)
    transfers   = active * g("transfers_per_active_yr", case)
    price       = g("avg_book_price_inr", case)

    book_value_moved = transfers * price
    cash_transfers   = transfers * (1 - g("swap_share", case)) * (1 - g("gift_share_of_nonswap", case))
    cash_gmv         = cash_transfers * price
    revenue          = cash_gmv * g("take_rate", case) * g("fee_collection_rate", case)

    pg_cost      = cash_gmv * g("inapp_payment_share", case) * g("pg_cost_pct", case)
    support_cost = transfers * g("support_cost_per_transfer", case)
    infra_cost   = registered * g("infra_cost_per_user_yr", case)
    cac_cost     = registered * g("cac_per_registered_user", case) if include_cac else 0.0
    variable     = pg_cost + support_cost + infra_cost + cac_cost

    contribution = revenue - variable
    profit       = contribution - (g("fixed_cost_y1_inr", case) if include_fixed else 0.0)
    return dict(students=students, addressable=addressable, registered=registered, active=active,
                transfers=transfers, book_value_moved=book_value_moved, cash_transfers=cash_transfers,
                cash_gmv=cash_gmv, revenue=revenue, pg_cost=pg_cost, support_cost=support_cost,
                infra_cost=infra_cost, cac_cost=cac_cost, variable=variable,
                contribution=contribution, profit=profit)

def report(title, students_by_case, include_cac=True, include_fixed=True):
    print(f"\n{'='*78}\n{title}\n{'='*78}")
    rs = {c: run(students_by_case[c], c, include_cac, include_fixed) for c in CASES}
    keys = ["students","addressable","registered","active","transfers","book_value_moved",
            "cash_transfers","cash_gmv","revenue","pg_cost","support_cost","infra_cost",
            "cac_cost","variable","contribution","profit"]
    print(f"{'line':24s}{'low':>17s}{'base':>17s}{'high':>17s}")
    for k in keys:
        print(f"{k:24s}" + "".join(f"{rs[c][k]:17,.0f}" for c in CASES))
    for c in CASES:
        r = rs[c]
        cm = r["contribution"]/r["transfers"] if r["transfers"] else 0
        rev = r["revenue"]/r["transfers"] if r["transfers"] else 0
        rpu = r["revenue"]/r["registered"] if r["registered"] else 0
        print(f"  {c:4s}: revenue/transfer Rs {rev:7.2f} | contribution/transfer Rs {cm:9.2f} "
              f"| revenue/registered user/yr Rs {rpu:7.2f}")
    return rs

# ---------- 5. TAM / SAM / SOM ----------
tam = report("TAM - India higher education, regular mode (AISHE 2023-24: 3,96,64,479)",
             {c: AISHE["India regular mode"] for c in CASES})
sam = report("SAM - Chennai metro higher education, regular mode (proxy range)", CHENNAI)

# SOM: three sourced Chennai-district pilot campuses
PILOT = [("Anna University (univ. depts)", 11940), ("Loyola College", 9347), ("D.G. Vaishnav College", 10910)]
pilot_n = sum(x[1] for x in PILOT)
print(f"\nPilot campuses: " + ", ".join(f"{n} {v:,d}" for n, v in PILOT) + f" = {pilot_n:,d}")
som = report("SOM - 3 pilot campuses, year one", {c: pilot_n for c in CASES})

# ---------- 6. Sensitivity on the three drivers that matter most ----------
print(f"\n{'='*78}\nSENSITIVITY (SOM year one, all other drivers at BASE)\n{'='*78}")
def som_at(overrides):
    saved = {k: D[k] for k in overrides}
    for k, v in overrides.items():
        D[k] = (v, v, v)
    r = run(pilot_n, "base")
    for k, v in saved.items():
        D[k] = v
    return r

for drv, vals in [("fee_collection_rate", [0.0, 0.2, 0.4, 0.55, 0.7, 0.9]),
                  ("transfers_per_active_yr", [0.8, 1.1, 1.5, 1.8, 2.5, 3.5]),
                  ("activation_rate", [0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.90])]:
    print(f"\n{drv}:")
    print(f"{'value':>10s}{'transfers':>12s}{'cash GMV':>14s}{'revenue':>12s}{'contribution':>14s}"
          f"{'contrib/xfer':>14s}{'marginal/xfer':>15s}{'profit':>12s}")
    for v in vals:
        r = som_at({drv: v})
        saved = D[drv]; D[drv] = (v, v, v)
        marg = rev_per_transfer("base") - varcost_per_transfer("base")
        D[drv] = saved
        print(f"{v:10.2f}{r['transfers']:12,.0f}{r['cash_gmv']:14,.0f}{r['revenue']:12,.0f}"
              f"{r['contribution']:14,.0f}{r['contribution']/r['transfers']:14,.2f}{marg:15,.2f}"
              f"{r['profit']:12,.0f}")

# ---------- 7. Breakeven ----------
print(f"\n{'='*78}\nBREAKEVEN (base drivers, contribution margin incl. CAC, vs Rs 9,00,000 fixed)\n{'='*78}")
b = run(pilot_n, "base")
cm_per_transfer = b["contribution"] / b["transfers"]
print(f"base contribution per transfer: Rs {cm_per_transfer:,.2f}")
if cm_per_transfer > 0:
    print(f"transfers needed to cover fixed cost: {g('fixed_cost_y1_inr','base')/cm_per_transfer:,.0f}")
    print(f"  = {g('fixed_cost_y1_inr','base')/cm_per_transfer/b['transfers']:.1f}x the base-case transfer volume")
else:
    print("contribution per transfer is NEGATIVE: no volume reaches breakeven.")

# steady-state (CAC excluded - returning users)
ss = run(pilot_n, "base", include_cac=False)
print(f"\nSteady state, CAC excluded (year 2+, same cohort):")
print(f"  contribution Rs {ss['contribution']:,.0f}  = Rs {ss['contribution']/ss['transfers']:,.2f}/transfer")
print(f"  profit after Rs 9,00,000 fixed: Rs {ss['profit']:,.0f}")

# What take rate / price would base need to break even on contribution alone?
print(f"\nWhat it would take (base drivers, CAC excluded, fixed Rs 9,00,000):")
for tr in [0.06, 0.10, 0.15, 0.25, 0.40]:
    r = som_at({"take_rate": tr})
    r2 = run(pilot_n, "base", include_cac=False)
    saved = D["take_rate"]; D["take_rate"] = (tr, tr, tr)
    r2 = run(pilot_n, "base", include_cac=False); D["take_rate"] = saved
    print(f"  take rate {tr:5.0%}: revenue Rs {r2['revenue']:9,.0f}  contribution(no CAC) Rs {r2['contribution']:10,.0f}")

# ---------- 8. Clankart reality check ----------
print(f"\n{'='*78}\nREALITY CHECK vs Clankart (Starter Story: $1.2K/mo, 25,000+ registered students)\n{'='*78}")
USD = 88.0  # ASSUMPTION: INR/USD
ck_rev_yr = 1200 * 12 * USD
print(f"Clankart annual revenue ~ Rs {ck_rev_yr:,.0f} across 25,000 registered users")
print(f"  = Rs {ck_rev_yr/25000:,.2f} revenue per registered user per year")
for c in CASES:
    r = som[c]
    print(f"BookHop SOM {c:4s}: Rs {r['revenue']/r['registered'] if r['registered'] else 0:,.2f} "
          f"revenue/registered user/yr  (total revenue Rs {r['revenue']:,.0f})")

# ---------- 9. Trading-window check ----------
print(f"\n{'='*78}\nTRADING WINDOW (competitor audit: supply and demand peak in antiphase, ~8 trading weeks/yr)\n{'='*78}")
for c in CASES:
    r = som[c]
    print(f"{c:4s}: {r['transfers']:,.0f} transfers/yr over 8 weeks = {r['transfers']/8:,.0f}/week "
          f"= {r['transfers']/8/7:,.1f}/day across 3 campuses")

# ---------- 10. What would it take ----------
print(f"\n{'='*78}\nWHAT WOULD IT TAKE (SOM, 3 campuses)\n{'='*78}")

for c in CASES:
    print(f"{c:4s}: revenue/transfer Rs {rev_per_transfer(c):6.2f}  marginal cost/transfer Rs "
          f"{varcost_per_transfer(c):6.2f}  -> marginal margin Rs {rev_per_transfer(c)-varcost_per_transfer(c):7.2f}")

# minimum take rate so one transfer pays for itself (support + PG only, base everything else)
den = (1-g("swap_share","base"))*(1-g("gift_share_of_nonswap","base"))*g("avg_book_price_inr","base")*g("fee_collection_rate","base")
need = varcost_per_transfer("base")/den
print(f"\nMinimum take rate for a BASE transfer to cover support+PG alone: {need:.1%}")
for sup in [12.0, 6.0, 3.0, 1.0, 0.0]:
    D["support_cost_per_transfer"] = (30.0, sup, 6.0)
    n = varcost_per_transfer("base")/den
    print(f"  if support cost/transfer were Rs {sup:5.2f} -> min take rate {n:.1%}")
D["support_cost_per_transfer"] = (30.0, 12.0, 6.0)

# Best realistic: high drivers, zero CAC (organic/campus ambassador), infra at Rs 8/user
print(f"\nBEST REALISTIC CASE (high drivers, organic acquisition so CAC = 0):")
r = run(pilot_n, "high", include_cac=False)
print(f"  transfers {r['transfers']:,.0f} | book value moved Rs {r['book_value_moved']:,.0f} | cash GMV Rs {r['cash_gmv']:,.0f}")
print(f"  revenue Rs {r['revenue']:,.0f} | contribution Rs {r['contribution']:,.0f} "
      f"(Rs {r['contribution']/r['transfers']:.2f}/transfer) | profit Rs {r['profit']:,.0f}")
print(f"  revenue covers {r['revenue']/360000:.2f} of ONE salary at Rs 30,000/month (Rs 3,60,000/yr)")

# How many campuses at best-realistic unit economics to fund one salary + fixed?
cm_pc = r["contribution"] / 3
print(f"  contribution per campus Rs {cm_pc:,.0f}; campuses needed for Rs 9,00,000 fixed: "
      f"{900000/cm_pc:,.1f}" if cm_pc > 0 else "  contribution per campus is negative")

# Scale run: best-realistic unit economics applied to the whole Chennai SAM
print(f"\nSAME best-realistic unit economics across ALL of Chennai metro (base denominator 460,000):")
rs = run(CHENNAI["base"], "high", include_cac=False)
print(f"  transfers {rs['transfers']:,.0f} | cash GMV Rs {rs['cash_gmv']:,.0f} | revenue Rs {rs['revenue']:,.0f}")
print(f"  contribution Rs {rs['contribution']:,.0f} | profit after Rs 9,00,000 fixed Rs {rs['profit']:,.0f}")
print(f"  revenue funds {rs['revenue']/360000:.1f} salaries at Rs 30,000/month")

# ---------- 11. Linearity self-check and CAC breakeven (R-23 / red-team O-1) ----------
# This block exists to make the model's central limitation VISIBLE IN ITS OWN OUTPUT
# rather than buried in its construction. It adds no drivers and changes no result.
print(f"\n{'='*78}\nLINEARITY SELF-CHECK - the model has NO density mechanism\n{'='*78}")
print("Same drivers (high, CAC=0), three scales 50x apart. If contribution per transfer")
print("is identical, the model cannot represent ANY improvement from density, automation,")
print("referral or repeat use - so it must not be used to argue for or against scale.")
SCALES = [("1 campus (Loyola 9,347)", 9347), ("3 pilot campuses", pilot_n),
          ("all Chennai metro (base denom.)", CHENNAI["base"])]
cpt = []
for label, n in SCALES:
    r = run(n, "high", include_cac=False)
    cpt.append(round(r["contribution"]/r["transfers"], 2))
    print(f"  {label:34s} transfers {r['transfers']:9,.0f}  contribution/transfer Rs {cpt[-1]:7.2f}")
assert len(set(cpt)) == 1, f"density mechanism present: {cpt}"
print(f"  -> IDENTICAL to the paisa across a {CHENNAI['base']/9347:.0f}x range. STRICTLY LINEAR (R-23 open).")
print(f"  -> The Chennai-monopoly profit figure is therefore Rs {cpt[0]:.2f} x "
      f"{run(CHENNAI['base'],'high',include_cac=False)['transfers']:,.0f} transfers less fixed cost,")
print( "     i.e. an assumption of no density effect restated as an output, not evidence about one.")

print(f"\n{'='*78}\nBREAKEVEN CAC per registered user (all other drivers held at the named case)\n{'='*78}")
for c in CASES:
    r = run(pilot_n, c, include_cac=False)          # contribution with CAC stripped out
    be = r["contribution"] / r["registered"] if r["registered"] else 0.0
    verdict = ("ACHIEVABLE - verdict turns on CAC" if be > 0 else
               "IMPOSSIBLE - negative, so CAC=0 does not rescue this case")
    print(f"  {c:4s}: contribution before CAC Rs {r['contribution']:11,.0f} over {r['registered']:9,.0f} "
          f"registered -> breakeven CAC Rs {be:7.2f}  [{verdict}]")
print(f"  published CAC assumptions: low Rs {g('cac_per_registered_user','low'):.0f} / "
      f"base Rs {g('cac_per_registered_user','base'):.0f} / high Rs {g('cac_per_registered_user','high'):.0f}")

print(f"\n{'='*78}\nWHERE THE FULLY-LOADED PER-TRANSFER FIGURE COMES FROM (base)\n{'='*78}")
b = run(pilot_n, "base")
tpr = b["transfers"] / b["registered"]
print(f"  transfers per registered user: {tpr:.2f}  (i.e. {1/tpr:.2f} registrations acquired per transaction)")
for k, lab, per_user in [("revenue","revenue",False), ("pg_cost","payment processing",False),
                         ("support_cost","support",False), ("infra_cost","infrastructure",True),
                         ("cac_cost","CAC",True)]:
    v = b[k] / b["transfers"] * (1 if k == "revenue" else -1)
    tag = "per REGISTERED USER / 0.54 transfers per registered user" if per_user else "per transfer"
    print(f"  {lab:20s} Rs {v:9.2f}   {tag}")
print(f"  {'TOTAL':20s} Rs {b['contribution']/b['transfers']:9.2f}")
print(f"  share of the negative that is CAC+infra: "
      f"{(b['cac_cost']+b['infra_cost'])/(b['variable']-b['revenue']):.0%}")
