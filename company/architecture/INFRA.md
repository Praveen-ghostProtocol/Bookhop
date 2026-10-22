# INFRA.md — infrastructure, backups, rollback, observability, incidents

**Owner:** cto, handing to **platform-sre at slice S8** · **Version:** v1.0
· **Date:** 2026-10-21
**Depends on:** ADR-001 (one VM, Indian region, no Docker in production) ·
`COST-MODEL.md` (spend, unapproved) · `THREAT-MODEL.md` §4 B6, §7.
**Binding rules:** CERT-In — **6-hour** incident report, **180-day** ICT logs
**within Indian jurisdiction**, **NTP sync to NIC/NPL**. DPDP r.6(1)(e) and
r.8(3) — **one year**, which subsumes the 180 days, so **plan on one year**.
Backups **with tested restore** (cto charter hard rule).

**Nothing in this document is provisioned until the founder approves
infrastructure spend.** Everything through slice S4 runs at Rs 0 on the
founder's Windows machine (§1). Proportionality is a design goal here: a
**tested restore matters; a multi-region setup does not.**

---

## 1. Environments

| Env | Where | Data | Cost | Who |
|---|---|---|---|---|
| **local** | Founder's Windows machine. Postgres 16 in Docker, Django dev server, `seed_demo` | seed only, `is_seed=true` | **Rs 0** | backend, frontend, QA |
| **ci** | CI runner, ephemeral Postgres service | fixtures only | Rs 0 on a free tier `ASSUMPTION: free CI minutes sufficient at this volume; verify before relying on it` | all |
| **pilot** | One VM, Indian region | **real student data from Gate C** | `COST-MODEL.md` | platform-sre |

**There is no staging environment, deliberately.** A second box doubles the
cost and the patching work for a pilot with one deployer. The substitutes are:
`seed_demo` locally, the full test suite in CI, and — the one that actually
matters — **a restore of the latest production dump into the local
environment, which is both the staging rehearsal and the restore test at the
same time** (§3.3). One mechanism, two jobs.
`# ponytail: no staging. Ceiling: a migration that only fails against real
data volume or real data shape. Upgrade path: a second VM, which is the first
thing to buy if a migration ever bites.`

---

## 2. The pilot box

Ubuntu LTS, 1 vCPU / 1–2 GB, Indian region.

> **The residency hold is RELEASED (2026-10-21).** Privacy-compliance confirms
> that an Indian region of a foreign-owned provider satisfies CERT-In Direction
> (iv); uncertainty is **LOW**; ADR-001 §8's reversal trigger is **not fired**.
> **Platform/SRE: do not move providers and do not spend the hedge.** The only
> remaining block on deployment is founder approval of spend
> (`COST-MODEL.md` §5), which is not a compliance matter.
>
> The reason the answer is clean is §2.2 plus ADR-001 §3: **every log we owe
> lives on a filesystem we control**, because no hosted error tracker, APM or
> analytics vendor was ever added. **Keep it that way** — adding a SaaS log or
> error product would reopen this question, and it would reopen it on
> *producibility*, not on ownership.

```
internet ──443──► nginx ──unix socket──► gunicorn (3 workers) ──► Django
                    │                                              │
                    ├── /static/         (direct, private cache)     │
                    ├── /media/ INTERNAL (X-Accel-Redirect only)    │
                    └── TLS (Let's Encrypt, auto-renew)             ▼
                                                            Postgres 16
                                                         (localhost only)
systemd: bookhop-web.service
         bookhop-jobs.timer  → run_jobs --once, every minute
         bookhop-nightly.timer → backup, retention_purge, digest, 02:30 IST
         chrony → NTP: NPL / NIC
```

> **`/media/` is an `internal` location (A-25, REDTEAM-S2 F51, 2026-10-22).**
> This diagram previously showed it served direct, alongside `/static/`,
> which contradicted `API-CONTRACT.md` §5.2 and would have published every
> listing photo. `/static/` is direct because it holds the stylesheet and the
> app icons; `/media/` holds photographs taken inside students' rooms.
> **The two are not the same kind of file and must not share a location block.**
>
> ```nginx
> location /static/ { alias /var/lib/bookhop/static/; add_header Cache-Control "private, max-age=86400"; }
> location /_protected_media/ { internal; alias /var/lib/bookhop/media/; }
> ```
>
> `internal` makes nginx return 404 to any direct request; the location is
> reachable only through an `X-Accel-Redirect` header Django emits **after**
> it has authorised the read. Set
> `BOOKHOP_MEDIA_INTERNAL_PREFIX=/_protected_media/` to match.
>
> **Verification is a step in §3.3, not a claim here.** With the app stopped:
> `curl -sS -o /dev/null -w '%{http_code}' https://<host>/_protected_media/listings/1/x.jpeg`
> must print `404`. A `200` means the location is not `internal` and every
> listing photo is public.


**Hardening** (`THREAT-MODEL.md` §4 B6): SSH keys only, no password auth, no
root login, UFW allowing 22/80/443 only, fail2ban, unattended-upgrades for
security patches, Postgres listening on localhost with a password the app
reads from an environment file at `/etc/bookhop/env` mode `0600`.

**Secrets** live in that one environment file: `DJANGO_SECRET_KEY`,
`DATABASE_URL`, `EMAIL_*`, `VAPID_*`, `PSEUDONYM_SALT`, `BACKUP_PUBKEY`.
**Not in the repo, not in the database, not in the backup.**
`PSEUDONYM_SALT` is what makes `user_tombstones.email_hash` resistant to a
database-only compromise (`DATA-MODEL.md` §10.1), so it is **never** written
to a dump.
`# ponytail: environment file as the secret store. Ceiling: no rotation
tooling, no audit of secret access, and a second box would need a copy.
Upgrade path: a managed secret store when there is a second box. Declared as
an ASVS V13 gap in THREAT-MODEL.md §1.`

### 2.1 Time — not a detail

CERT-In Direction (i) requires clock synchronisation to NIC or NPL. **Every
SLA clock in the system — 2h, 3h, 24h, 36h, 7d, the 21-day hold, the 48-hour
reservation, the 72-hour follow-up — is a timestamp comparison.** A drifting
clock is simultaneously a compliance breach and a silently wrong product.
`chrony` to `time.nplindia.org` and the NIC pool, and `readyz` reports drift
above 1 second as not-ready.

### 2.2 Logs — one year, in India, structured

| Log | Where | Retention |
|---|---|---|
| Application (JSON: timestamp, level, `request_id`, actor pseudonym, route, status, duration) | `/var/log/bookhop/app.log` | **1 year**, logrotate daily, compressed |
| nginx access + error | `/var/log/nginx/` | **1 year** |
| Postgres (`log_statement='ddl'`, slow queries > 1s, connections) | `/var/log/postgresql/` | **1 year** |
| systemd journal | journald, `SystemMaxUse` capped | **1 year** |
| `audit_log`, `personal_data_access_log` | Postgres | 1 year, **never user-deletable** |

**Logs never contain:** a password, a magic-link token, a full email address
(domain only), a message body, or any ADR-003 deny-listed value. A log
scrubber in the logging formatter drops known-sensitive keys, and
`tests/unit/test_log_scrubbing.py` asserts it.

---

## 3. Backups, and the restore test that makes them real

### 3.1 What is backed up, nightly at 02:30 IST

```
pg_dump --format=custom bookhop            →  db-<UTC-ts>.dump
tar -cz /var/lib/bookhop/media             →  media-<UTC-ts>.tar.gz
cp /etc/bookhop/env.template               →  (template only; NEVER the secrets)
```

Both artefacts are **encrypted on the box before leaving it**
(`age -r $BACKUP_PUBKEY`), so a backup at rest anywhere is useless without the
founder's private key — which is not on the server
(`THREAT-MODEL.md` §4 B6).

### 3.2 Where copies live

| Copy | Tier 1 (minimum) | Tier 2 (recommended) |
|---|---|---|
| On-box, last 7 nights | yes | yes |
| Provider snapshot | weekly, provider-managed | weekly, provider-managed |
| **Off-site** | pulled nightly to the founder's machine by a scheduled task | pushed nightly to an Indian-region object store, 30-day lifecycle |

**Tier 1's off-site copy depends on the founder's laptop being on**, which is
exactly the kind of dependency that fails on the week it matters. **That is
the single reason to prefer Tier 2**, and it is worth Rs ~1,100/month more. It
is the founder's call (`COST-MODEL.md` §5).

### 3.3 The restore test — monthly, scripted, Rs 0

`deploy/restore_check.ps1` (Windows) / `.sh`:

1. Fetch the latest encrypted dump; decrypt with the founder's key.
2. `docker compose up` a throwaway Postgres 16.
3. `pg_restore` into it.
4. `manage.py migrate --check` — asserts the dump's schema matches the code.
5. `manage.py verify_audit_chain` — **asserts the restored audit chain is
   intact**, which is the only way to know a backup preserved the evidence and
   not just the rows.
5a. **`SET session_replication_role = 'replica'`, then re-run every
   append-only refusal and confirm each still fires.** Added 2026-10-22, and
   it closes two controls that were leaning on each other.
   **The `ENABLE ALWAYS` property on all seven triggers is `ASSUMED THERE`
   and has never been verified**, because `session_replication_role` needs
   superuser — **and the one place it could be verified is this restore test,
   which did not look.** The property *only* matters under `replica` role,
   which is what `pg_restore --disable-triggers` and logical replication use:
   **so the append-only guarantee is unverified in exactly the operation
   during which someone might be rewriting history.**
   **This test is the right home precisely because it is the one context
   where we hold superuser legitimately** — a throwaway local database we
   created. Verifying it anywhere else would mean granting a privilege to
   verify a privilege-dependent property.
   **And the table list is derived from the expected-trigger inventory, never
   hard-coded.** QA's catalogue sweep hard-coded three tables, so the newest
   trigger's property went unasserted until a human noticed — a list where an
   invariant belonged (rule 11), in the instrument.
6. Run a fixed read-only assertion set: row counts per table within expected
   bounds; the three decisive metric queries (`DATA-MODEL.md` §9.2–9.4) return
   non-error results; `listings_price_immutable` trigger present;
   the ADR-003 deny-list still clean.
6b. **Assert the `/media/` location is `internal` — A-25's second layer at
   the deployment seam, and the one nothing else verifies.** With the app
   stopped, request a storage path directly and require a refusal:

   ```bash
   code=$(curl -sS -o /dev/null -w '%{http_code}'        "https://$HOST/_protected_media/listings/1/0000.jpeg")
   [ "$code" = "404" ] || { echo "FAIL: /media/ is not internal (got $code)"; exit 1; }
   ```

   **A `200` means every listing photo is public**, and the Django
   authorisation decision in front of them guards nothing, because the
   storage path was derivable from the listing payload until A-25 and the
   `internal` location is what replaced that. **A `403` fails too** — it
   means the location exists and is merely access-controlled, which is a
   different arrangement from the one ADR-001 §2.6 now specifies.

   *This step exists because `INFRA.md` §1 claimed "verification is a step in
   §3.3" when no such step existed — a document naming a control that did not
   exist, which is rule 9's own earned example. Added 2026-10-22 by cto, found
   by Code Review as R-R3.*

7. Print **RESTORE OK <dump timestamp> <elapsed>** and tear down.

**The result is recorded in `METRICS.md`'s "restore-from-backup test result"
(a cto charter metric) and in the G4 go/no-go packet. A restore that has not
been tested this month is reported as untested, not as working.**

### 3.4 Targets, chosen to be honest rather than impressive

| | Target | Why this number |
|---|---|---|
| **RPO** | **24 hours** | Nightly dumps. Losing a day of a one-campus pilot is recoverable: listings can be re-entered, and the irreplaceable rows — `audit_log`, `consents`, `age_verification_events`, `repeat_infringer_records`, `safety_incidents` — are small and in every dump. **Continuous archiving would reduce this to minutes and is the first upgrade to buy if real students are relying on the service.** |
| **RTO** | **4 hours** | Provision a VM, restore, re-point DNS, by one person following `ops/runbooks/restore.md`. |
| **Retention** | 7 nightly on-box, 30 nightly off-site, 4 weekly provider snapshots | Covers the one-year statutory floor through the live database, not through backups — backups are for recovery, retention is a database property |

`# ponytail: nightly logical dumps, no PITR. Ceiling: RPO 24h. Upgrade path:
WAL archiving to the same object store — one Postgres config change plus
~20 lines in the backup script, worth doing the day a real cohort depends on
it.`

---

## 4. Deploy and rollback

```bash
# deploy/deploy.sh  — run by a human, on the box, one at a time
set -euo pipefail
PREV=$(git rev-parse HEAD); echo "$PREV" > /var/lib/bookhop/last_good_sha
git fetch --tags && git checkout "$1"            # an explicit tag or SHA
pg_dump --format=custom bookhop > /var/backups/bookhop/pre-deploy-$(date -u +%FT%TZ).dump
pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py collectstatic --noinput
systemctl restart bookhop-web
sleep 3; curl -fsS localhost:8000/readyz || { echo "READYZ FAILED"; exit 1; }
python manage.py verify_audit_chain
echo "deployed $1 (previous $PREV)"
```

**Rollback** is `deploy/rollback.sh`: check out `last_good_sha`, reinstall,
restart, `readyz`.

**The honest constraint on rollback: code rolls back, migrations do not.** A
deploy that drops a column cannot be undone by `git checkout`. Therefore a
standing rule, enforced by Code Review:

> **Migrations are expand-then-contract. A slice may add a column, backfill it
> and start writing it. Dropping or renaming anything happens in a *later*
> slice, after the previous release is known good.** No destructive migration
> ships in the same release as the code that stops needing the column.

That rule is what makes a one-box, one-script deploy safe enough for a pilot.
The pre-deploy dump in the script is the backstop.

**No automated deployment.** One person, one command, an audit trail in shell
history and in `audit_log` (ADR-001 §6).

---

## 5. Observability — proportionate, and tied to the clocks

| Signal | Mechanism | Threshold / action |
|---|---|---|
| Liveness | External pinger on `/healthz`, 1 min `ASSUMPTION: a free uptime-monitor tier is sufficient; it processes no personal data, only an HTTP status` | 2 consecutive failures → email + push to on-call |
| Readiness | `/readyz`: DB reachable, migrations applied, **last successful `run_jobs` < 5 min**, clock drift < 1 s, disk < 90% | not-ready → alert |
| **Job runner stalled** | the `readyz` limb above | **Highest-priority alert after liveness.** A stalled runner silently stops reservation expiry, follow-ups, SLA alerts, notifications and the retention purge — the failure is invisible in the UI, which is exactly why it is monitored rather than noticed |
| **SLA breach imminent** | `sla.check` job every 5 min over `reports` and `legal_notices` | **75% of the clock elapsed** → notify on-call; 100% → founder escalation. The 2-hour clock gets a 90-minute warning |
| Errors | 5xx count per hour from the access log; the daily digest lists every 5xx with its `request_id` | > 10/hour → alert |
| Latency | p50/p95 per route from the access log, in the digest | p95 search > 1 s → investigate (a `METRICS.md` metric) |
| Disk | nightly check | 70% warn, 90% `readyz` fails |
| **Daily digest email, 07:00 IST** | one job | 5xx list, p95 per route, job failures, queue depth, pending moderation count, **open SLA items with time remaining**, new reports, **the `audit_log` chain head**, **audit-append attempts-to-win p50/p99** (see below), backup result, disk, cert expiry |
| **`AuditAppendContention`** | alert | **> 0 in an hour pages on-call.** The `prev_hash` retry budget was exhausted and a mutation failed. **Distinct from the tamper class on purpose** (`DATA-MODEL.md` §8) — and that split is only safe because this row exists: **splitting an error class without adding a watcher converts a false alarm into a silent failure** |
| **`AuditChainBroken`** | alert | **founder escalation.** It asserts tampering and must keep meaning that. It no longer fires on load |
| **Audit-append attempts-to-win, p99** | digest counter | Informational, but **p99 > 6** (half the budget of 12) over a rolling day is the trigger to revisit the global-chain decision (`DATA-MODEL.md` §8). **A leading indicator — contention is visible here before it exhausts the budget and breaks a mutation** |
| Backup | nightly job result in the digest | a missing or failed backup is an alert, not a digest line |
| Monthly | restore test (§3.3) + `pip-audit` + `verify_audit_chain` | failures are alerts |

**No hosted APM, no error aggregator, no analytics SDK** — ADR-001 §3, because
each would be a Data Processor needing a DPA (Gate B15) and would put personal
data outside India. The digest plus `request_id` plus `grep` is the pilot-scale
answer.
`# ponytail: daily email digest instead of a dashboard. Ceiling: the first
week nobody reads it. Upgrade path: self-hosted GlitchTip on the same box —
same DPA-free property.`

**The chain head in the digest is doing real work**: it puts a copy of the
audit chain's state outside the box every day, at zero cost, so tampering with
the log requires reaching the founder's mailbox as well
(`THREAT-MODEL.md` §5.8).

---

## 6. Capacity, and what breaks first

At pilot — one campus, a few hundred accounts, a few thousand listings — the
box is idle. The honest bottleneck order, so nobody optimises the wrong thing:

1. **Memory on a 1 GB box**, with Postgres and gunicorn co-resident. First fix
   is Tier 2's 2 GB, not tuning.
2. **Media disk**, at roughly 15 GB (ADR-001 §2.6).
3. **`search_events` / `transfer_events` / `audit_log` row growth**, which
   makes the nightly purge slow before it makes anything else slow
   (ADR-002 §6 step 4: monthly partitions, then `DROP PARTITION`).
4. **One job worker**, which is fine until it is not (ADR-001 §2.4: add
   workers, `SKIP LOCKED` already permits it).

Nothing here is a reason to build for scale now.

---

## 7. Incident response — the 6-hour clock governs

Built to `COMPLIANCE.md` §8.6 and §1.7. The templates live in
`ops/runbooks/breach/` in the repo, pre-written, because six hours is not
enough time to compose four documents.

| T+ | Action | Source |
|---|---|---|
| **T+0** | **Log the detection timestamp first, before diagnosing.** Any path — monitor, log line, user report, staff observation — writes an `audit_log` entry. "Becoming aware" is the clock start and it will be scrutinised | `COMPLIANCE.md` §1.7, §8.6 |
| T+0 | Declare: one named incident lead (the CERT-In PoC on `legal_entities`), one `request_id`-tagged timeline file | |
| T+0–1h | Contain: rotate `DJANGO_SECRET_KEY` and invalidate all sessions if credentials or sessions are implicated; revoke staff TOTP devices; block the vector | |
| T+1h | Scope: which `COMPLIANCE.md` §7 rows, how many pseudonyms, which Annexure I category | |
| **T+6h** | **Report to CERT-In** — `incident@cert-in.org.in` / 1800-11-4949. **The binding clock today.** Annexure I items (xi) Data Breach and (xii) Data Leak are the likely categories | CERT-In Direction (ii) |
| T+immediate | **Notify each affected data principal** with all five Rule 7(1) elements: nature/extent/timing; consequences for her; mitigation done and in progress; steps she can take; a named contact | DPDP r.7(1) — template ready now, operative 13 May 2027 |
| T+immediate | Initial Board intimation — nature, extent, timing, **location**, likely impact | r.7(2)(a), from 13 May 2027 |
| T+72h | Detailed Board report — facts, causes, mitigation, findings on who caused it, remedial measures, **and a report on the intimations given to data principals** | r.7(2)(b), from 13 May 2027 |
| T+7d | Written post-mortem: cause, timeline, what detected it, what should have, one change made | cto |

**Rehearse once before the pilot opens, end to end, and log the rehearsal**
(Gate C3). `COMPLIANCE.md` §8.6: *"An unrehearsed runbook is a document, not a
capability."* The rehearsal is a slice-S8 deliverable with a named date, not an
aspiration.

### 7.1 The non-breach incidents, which are more likely

| Incident | First action | Runbook |
|---|---|---|
| Box down | Check provider status; if unrecoverable, restore to a new VM (§3.3, RTO 4h) | `ops/runbooks/restore.md` |
| Job runner stalled | `systemctl status bookhop-jobs`; drain the backlog; **check for missed SLA clocks first**, because that is the part with a legal consequence | `ops/runbooks/jobs.md` |
| Database corruption | Stop writes, restore the latest good dump, replay what can be replayed from the audit log | `ops/runbooks/restore.md` |
| Bad deploy | `rollback.sh`; if a migration is implicated, restore the pre-deploy dump | `ops/runbooks/rollback.md` |
| **Missed 2h/3h takedown clock** | Act now, then record the breach and why, in `audit_log`. **Do not backdate anything** — a falsified timestamp is far worse than a missed clock | `ops/runbooks/sla-breach.md` |
| **Physical-safety incident** | `safety_incidents` row → automatic founder escalation; police referral if advised; **POCSO reporting if a minor is involved** | `ops/runbooks/safety.md` |
| Minor discovered on the platform | Suspend, erase, log (`age_verification_events` `REVOKED_MINOR_DISCOVERED`); POCSO duty if an incident is involved | `ops/runbooks/minor.md` |
| Certificate expiry | auto-renew; digest reports days remaining | — |

---

## 8. Gate B / Gate C obligations this document discharges

| Gate item | Discharged by |
|---|---|
| **B10** — breach runbook to 6 hours; logs in India, 180-day rolling minimum, NTP-synced | §2.1, §2.2, §7 |
| **B15** — signed data-processing contract with every vendor touching personal data | §9 — the vendor list is **two** |
| **C3** — breach runbook rehearsed once, end to end, logged | §7 |
| cto charter — backups **with tested restore** | §3.3 |
| cto charter — rate limits, observability, rollback | `API-CONTRACT.md` §2.4, §5, §4 |
| `README.md` §7 — operating costs for the go/no-go packet | `COST-MODEL.md` |

## 9. Processors — the whole list, because each one is a signature

| Vendor | Role | Personal data it sees | DPA needed (Gate B15) |
|---|---|---|---|
| **VM / hosting provider** (Indian region) | Data Processor | everything at rest and in memory | **Yes — blocking** |
| **Transactional email** (SES ap-south-1 or equivalent) | Data Processor | email addresses, notification subject lines | **Yes — blocking** |
| Object storage for backups (**Tier 2 only**) | Data Processor | encrypted dumps only; **cannot decrypt** | Yes, and the encryption makes it low-risk |
| External uptime monitor | not a processor | an HTTP status code | No |
| ~~Hosted error tracking / APM / log SaaS~~ | **deliberately none** | — | **Adding one reopens the CERT-In residency question** (§2), so this absence is now a compliance control and not only a cost decision |
| Browser push services (Google, Mozilla, Apple) | not a processor in substance | **ciphertext only** — Web Push payloads are encrypted to the subscription's keys | No |
| Let's Encrypt | not a processor | a domain name | No |

**Two blocking DPAs. That is the entire third-party surface**, and it is the
direct result of ADR-001's decisions to drop SMS, hosted error tracking,
analytics and object storage from v1. Every vendor avoided is a founder
signature not needed before Gate B.

---

## Amendment log

| Date | Change | Approved by |
|---|---|---|
| 2026-10-21 | v1.0; handoff to platform-sre at S8 | cto |
| 2026-10-21 | **§2's residency hold released** — compliance confirms the CERT-In reading, uncertainty LOW, no provider move, no hedge spend. §9's processor list and the no-SaaS-logs rule are now load-bearing for that answer, not just for cost | cto |
