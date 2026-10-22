"""Outbound transactional email — the backend half only.

**The ownership line, and it is the reason this file is three functions long.**
TASKS §1: *"Backend owns **no** templates — not even for emails. Email bodies
are templates under `templates/email/` and **frontend owns them**; backend
passes a context dict."* So this renders a template it does not own and must not
create, from a context dict it does.

**It raises when the template is missing, and does not fall back to a built-in
string.** A fallback body would be backend writing copy — the thing the
ownership line exists to prevent — and it would ship untranslated English past
the copy-enforcement tests (`THREAT-MODEL.md` §6.1), which read `templates/**`
and `locale/**`. A failed job with a message naming the missing file and its
owner is the honest outcome: the job retries, and the fix is frontend's
template, not backend's string.

Transport is Django's `EMAIL_BACKEND`. In development that is the console
backend, so a magic link is readable in the runserver output; SES lands in S7
with the rest of the delivery channels, and `BOOKHOP_EMAIL_HOST*` is already
reserved in `.env.example` so nobody invents a second name for it.
"""

import logging

from django.core.mail import EmailMessage
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.utils import translation

log = logging.getLogger(__name__)

#: `templates/email/<name>.subject.txt` and `.body.txt`. Two files so the
#: subject is translatable and reviewable as copy rather than being a Python
#: literal with a `%s` in it.
SUBJECT_TEMPLATE = "email/{name}.subject.txt"
BODY_TEMPLATE = "email/{name}.body.txt"


def deliver_email(*, to, name, context, locale="en"):
    """Render `templates/email/{name}.*` and send it. Returns the message.

    Raises `TemplateDoesNotExist` naming the file and its owner.
    """
    with translation.override(locale):
        try:
            subject = render_to_string(SUBJECT_TEMPLATE.format(name=name), context).strip()
            body = render_to_string(BODY_TEMPLATE.format(name=name), context)
        except TemplateDoesNotExist as missing:
            raise TemplateDoesNotExist(
                f"{missing} is missing. Email bodies live in templates/email/ and are "
                "frontend-developer's (TASKS.md §1: backend owns no templates, not even "
                "for emails). Backend passes the context dict and must not write a "
                "fallback body — a fallback is untranslated copy that no "
                "forbidden-copy test reads. Needed: "
                f"{SUBJECT_TEMPLATE.format(name=name)} and {BODY_TEMPLATE.format(name=name)}."
            ) from missing

    message = EmailMessage(subject=subject, body=body, to=[to])
    message.send(fail_silently=False)
    log.info("mail.sent", extra={"template": name, "locale": locale})
    return message
