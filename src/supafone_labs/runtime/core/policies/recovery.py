from __future__ import annotations

import re

from supafone_labs.runtime.core.decision import RuntimeDecision


_SPOKEN_REPLACEMENTS = (
    (" at ", "@"),
    (" dot ", "."),
    (" underscore ", "_"),
    (" hyphen ", "-"),
    (" dash ", "-"),
)


def normalize_spoken_email(raw_text: str) -> str:
    text = f" {(raw_text or '').strip().lower()} "
    for source, target in _SPOKEN_REPLACEMENTS:
        text = text.replace(source, target)
    text = text.strip().replace(" ", "")
    if text.count("@") > 1:
        parts = text.split("@")
        text = "".join(parts[:-1]) + "@" + parts[-1]
    return text


def email_needs_repair(email: str) -> bool:
    if not email:
        return True
    if " " in email or ".." in email:
        return True
    if email.count("@") != 1:
        return True
    local_part, domain = email.split("@", 1)
    if not local_part or not domain or "." not in domain:
        return True
    return re.search(r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$", email) is None


class RecoveryMessagePolicy:
    def evaluate_email_repair(self, raw_text: str) -> RuntimeDecision | None:
        normalized = normalize_spoken_email(raw_text)
        if not email_needs_repair(normalized):
            return None
        return RuntimeDecision.request_field_repair(
            field="email",
            message="I think I may have gotten the email wrong. Can you tell me again so I can try again?",
        )
