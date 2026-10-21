"""`manage.py open_discovery --campus <slug>` — ADR-002 §4.1(b).

Discovery cannot be opened by `UPDATE campuses SET discovery_enabled_at =
now()`. It is opened here, and only if a `gate_authorisations` row exists for
the campus with `gate='C'`, not revoked, and every evidence item present.

The command prints the checklist with each item's state and **exits non-zero on
the first missing one**. The row it reads is written by a named human, never by
an agent.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.core.models import Campus, GateAuthorisation
from apps.core.services import record_audit

#: ADR-002 §4.1(b), the `evidence` jsonb keys. Each maps to a Gate item.
EVIDENCE_KEYS = [
    ("counsel_engagement_ref", "Gate B5 — counsel C1–C3 engaged"),
    ("takedown_sop_ref", "Gate B6 — takedown SOP written"),
    ("oncall_rota_ref", "Gate C4 — on-call rota"),
    ("breach_rehearsal_at", "Gate C3 — breach runbook rehearsed"),
    ("campus_mou_ref", "Gate C1 — signed campus MoU"),
    # S1 additionally asserts these ids exist in `notice_versions` for PRIVACY,
    # TERMS and SELLER_TERMS in both locales; that table does not exist yet, so
    # S0 checks the evidence reference only and says so rather than implying a
    # stronger check than it makes.
    ("notice_version_ids", "Gate B5 — PRIVACY, TERMS, SELLER_TERMS published"),
]

LEGAL_ENTITY_FIELDS = [
    ("cin", "Gate B1 — Certificate of Incorporation"),
    ("inc20a_filed_at", "Gate B2 — INC-20A filed (s10A bar on commencing business)"),
    ("grievance_officer_name", "Gate B4 — grievance officer name"),
    ("grievance_officer_email", "Gate B4 — grievance officer email"),
    ("grievance_officer_phone", "Gate B4 — grievance officer phone"),
]


def has_visible_character(text):
    """The invariant a blank check actually wants: **at least one visible
    character** — not "lacks the whitespace we remembered".

    REVIEW-S0 C1. `str.strip()` gets eleven of twelve forms right because it
    uses the Unicode whitespace property, but zero-width space and BOM are
    *format* characters (category `Cf`), not whitespace, so they survive a
    strip and render as nothing. `authorised_by_human = "\\u200b"` would have
    opened the gate and shown nobody's name in the go/no-go packet.

    This asks Python's Unicode database per character instead of consulting a
    list, so it needs no entries and gains none: a character is visible if it
    is printable and is neither whitespace nor a format character. A new
    invisible codepoint in a future Unicode version is covered on the day
    Python is upgraded.

    The database floor in migration 0005 enumerates the known forms instead,
    because neither engine can express this test — SQLite has no regex and
    Postgres's `[[:graph:]]` is locale-dependent. That asymmetry is deliberate
    and declared there: the floor catches every form anyone has measured, and
    this catches the ones nobody has.
    """
    import unicodedata

    return any(
        ch.isprintable() and not ch.isspace() and unicodedata.category(ch) != "Cf"
        for ch in text
    )


def _present(value):
    """Is this evidence actually present?

    S4: a string of spaces is not evidence of a signed MoU. C1: neither is a
    string of zero-width spaces. Lists and dicts are tested by length, and
    their *elements* too — `notice_version_ids: [" "]` is not a published
    notice. Falsy scalars (0, False) are not evidence either.
    """
    if isinstance(value, str):
        return has_visible_character(value)
    if isinstance(value, (list, tuple, set)):
        return any(_present(item) for item in value)
    if isinstance(value, dict):
        return any(_present(item) for item in value.values())
    return bool(value)


def checklist(campus, auth=None):
    """Return ([(ok, label, detail)], auth) for every gate item, in order.

    `auth` is injectable so the checklist can be tested on a row the database
    will not accept. Migration 0005 moved the evidence requirement into a
    trigger, so an incomplete `gate='C'` row can no longer be saved — which is
    the point, and which also means the only way to exercise the *printed*
    checklist is to hand it one.
    """
    items = []

    if auth is None:
        auth = (
            GateAuthorisation.objects.filter(
                gate="C", scope_type="CAMPUS", scope_id=campus.id, revoked_at__isnull=True
            )
            .order_by("-authorised_at")
            .first()
        )
    items.append((auth is not None, "gate_authorisations row (gate='C', scope=CAMPUS, not revoked)",
                  f"id={auth.id}" if auth else "no row — a named human must authorise this"))
    if auth is None:
        return items, None

    items.append((_present(auth.authorised_by_human),
                  "authorised_by_human", auth.authorised_by_human or "empty"))

    items.append((campus.active, "campuses.active", str(campus.active)))
    items.append((campus.legal_entity_id is not None, "campuses.legal_entity_id",
                  str(campus.legal_entity_id)))

    # S5: the authorisation names its own legal entity and the campus names
    # one. Reading the CIN and INC-20A facts from the campus's entity while the
    # authorisation was granted against a different one would let a row
    # authorised for entity A open a campus whose evidence is entity B's. The
    # two must be the same row; there is no fallback, because a fallback is how
    # that mismatch would go unnoticed.
    items.append((
        auth.legal_entity_id == campus.legal_entity_id,
        "gate_authorisations.legal_entity_id == campuses.legal_entity_id",
        f"auth={auth.legal_entity_id} campus={campus.legal_entity_id}",
    ))
    entity = campus.legal_entity

    for field, label in LEGAL_ENTITY_FIELDS:
        value = getattr(entity, field, None) if entity else None
        items.append((_present(value), f"legal_entities.{field} — {label}", str(value)))

    evidence = auth.evidence or {}
    for key, label in EVIDENCE_KEYS:
        value = evidence.get(key)
        items.append((_present(value), f"evidence.{key} — {label}", str(value)))

    return items, auth


class Command(BaseCommand):
    help = "Open the discovery gate for one campus, if and only if the evidence is complete."

    def add_arguments(self, parser):
        parser.add_argument("--campus", required=True, help="campuses.slug")
        # N5: the audit row for the most legally significant action in the
        # system read `actor_type='SYSTEM'`, with no human named on it.
        #
        # Deliberately **optional**, and it defaults to the authorisation row's
        # own `authorised_by_human` rather than to a placeholder. That name is
        # already required and already validated, so the audit row gets a human
        # either way; and a new required argument would break every existing
        # caller for a note-level improvement, which is a bad trade. Pass --by
        # when the operator differs from the authorising human.
        parser.add_argument("--by", default="",
                            help="the human running this command, if not the authorising human")

    def handle(self, *args, **options):
        slug = options["campus"]
        # C1: the same invariant as the checklist, so `--by "​"` cannot
        # put an invisible operator name into the audit row either.
        supplied = (options["by"] or "").strip()
        operator = supplied if has_visible_character(supplied) else ""
        try:
            campus = Campus.objects.get(slug=slug)
        except Campus.DoesNotExist:
            raise CommandError(f"no campus with slug {slug!r}")

        if campus.discovery_enabled_at is not None:
            self.stdout.write(f"discovery already open for {slug} at {campus.discovery_enabled_at}")
            return

        items, auth = checklist(campus)
        for ok, label, detail in items:
            self.stdout.write(f"  [{'x' if ok else ' '}] {label}: {detail}")
            if not ok:
                raise CommandError(
                    f"GATE C NOT SATISFIED for {slug}: {label}. "
                    "ADR-002 §4.1(b). Nothing was changed."
                )

        with transaction.atomic():
            campus.discovery_enabled_at = timezone.now()
            campus.save(update_fields=["discovery_enabled_at"])
            record_audit(
                None, "discovery.open", campus,
                before={"discovery_enabled_at": None},
                after={"discovery_enabled_at": campus.discovery_enabled_at,
                       "gate_authorisation_id": auth.id,
                       "authorised_by_human": auth.authorised_by_human,
                       "opened_by_operator": operator or auth.authorised_by_human},
            )
        self.stdout.write(f"discovery OPEN for {slug} at {campus.discovery_enabled_at}")
