import asyncio
import logging
from email.message import EmailMessage

from aiosmtplib import SMTP, SMTPException
from pydantic import ValidationError

from config import Settings
from database import ContactRepository
from models import BatchResult, Contact


class Mailer:
    def __init__(self, settings: Settings, repository: ContactRepository, logger: logging.Logger):
        self.settings = settings
        self.repository = repository
        self.logger = logger

    def _smtp_kwargs(self) -> dict[str, object]:
        options: dict[str, object] = {
            "hostname": self.settings.smtp_hostname,
            "port": self.settings.smtp_port,
            "timeout": self.settings.smtp_timeout,
            "use_tls": self.settings.smtp_use_tls,
            "use_ssl": self.settings.smtp_use_ssl,
        }
        if self.settings.smtp_username:
            options["username"] = self.settings.smtp_username
        if self.settings.smtp_password:
            options["password"] = self.settings.smtp_password
        return options

    def _build_message(self, contact: Contact) -> EmailMessage:
        correo = EmailMessage()
        correo["Subject"] = self.settings.email_subject
        correo["From"] = f"{self.settings.from_name} <{self.settings.from_email}>"
        correo["To"] = contact.email
        correo.set_content(self.settings.email_body.format(nombre=contact.nombre))
        return correo

    async def _send_once(self, smtp: SMTP, contact: Contact) -> None:
        await smtp.send_message(self._build_message(contact))

    async def _retry_send(self, contact: Contact) -> bool:
        for attempt in range(1, self.settings.max_retries + 1):
            delay = self.settings.retry_base_delay * (2 ** (attempt - 1))
            self.logger.warning("Voy a reintentar %s en %.1fs", contact.email, delay)
            await asyncio.sleep(delay)

            smtp = SMTP(**self._smtp_kwargs())
            try:
                await smtp.connect()
                await self._send_once(smtp, contact)
            except Exception as exc:
                self.logger.warning("El reintento %s fallo para %s: %s", attempt, contact.email, exc)
            else:
                self.repository.update_status(contact.email, "sent")
                return True
            finally:
                try:
                    await smtp.quit()
                except Exception:
                    pass

        self.repository.update_status(contact.email, "failed", "Agotados los reintentos")
        return False

    async def send_batch(self, contacts: list[Contact]) -> BatchResult:
        result = BatchResult(total=len(contacts))
        if not contacts:
            return result

        smtp = SMTP(**self._smtp_kwargs())
        try:
            await smtp.connect()

            for contact in contacts:
                try:
                    contacto_valido = Contact.model_validate(contact.model_dump())
                    await self._send_once(smtp, contacto_valido)
                except ValidationError as exc:
                    self.repository.update_status(contact.email, "invalid", str(exc))
                    result.invalid += 1
                    result.failed += 1
                except (SMTPException, OSError, asyncio.TimeoutError) as exc:
                    enviado_tras_reintento = False
                    if self.settings.max_retries > 0:
                        enviado_tras_reintento = await self._retry_send(contact)

                    if enviado_tras_reintento:
                        result.sent += 1
                    else:
                        self.repository.update_status(contact.email, "failed", str(exc))
                        result.failed += 1
                else:
                    self.repository.update_status(contact.email, "sent")
                    result.sent += 1
        finally:
            try:
                await smtp.quit()
            except Exception:
                pass

        return result
