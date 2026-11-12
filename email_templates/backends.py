import copy
import logging
from email.utils import parseaddr
from fnmatch import fnmatchcase
from typing import Any, Sequence

from django.conf import settings
from django.core.mail import get_connection
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import EmailMessage

logger = logging.getLogger(__name__)


class AllowlistEmailBackend(BaseEmailBackend):
    """Delivers only to addresses matching settings.EMAIL_ALLOWLIST; drops and logs the rest.

    Used outside production so a local copy of the database can never email real adopters.
    Messages go out through settings.EMAIL_ALLOWLIST_INNER_BACKEND.
    """

    def __init__(self, fail_silently: bool = False, **kwargs: Any) -> None:
        super().__init__(fail_silently=fail_silently)
        self.patterns = [pattern.lower() for pattern in settings.EMAIL_ALLOWLIST]
        self.inner = get_connection(
            settings.EMAIL_ALLOWLIST_INNER_BACKEND, fail_silently=fail_silently, **kwargs
        )

    def open(self) -> bool | None:
        return self.inner.open()

    def close(self) -> None:
        self.inner.close()

    def send_messages(self, email_messages: Sequence[EmailMessage]) -> int:
        allowed_messages = []
        for message in email_messages:
            allowed = copy.copy(message)
            allowed.to = self._filter(message.to, message.subject)
            allowed.cc = self._filter(message.cc, message.subject)
            allowed.bcc = self._filter(message.bcc, message.subject)
            if allowed.recipients():
                allowed_messages.append(allowed)
            else:
                logger.warning("Dropped email %r: no allowlisted recipients", message.subject)
        if not allowed_messages:
            return 0
        return self.inner.send_messages(allowed_messages) or 0

    def _is_allowed(self, address: str) -> bool:
        email = parseaddr(address)[1].lower()
        return any(fnmatchcase(email, pattern) for pattern in self.patterns)

    def _filter(self, addresses: Sequence[str], subject: str) -> list[str]:
        kept = []
        for address in addresses:
            if self._is_allowed(address):
                kept.append(address)
            else:
                logger.warning("Dropped recipient %s from email %r", address, subject)
        return kept
