import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


def _leer_bool(clave: str, por_defecto: bool = False) -> bool:
    valor = os.getenv(clave)
    if valor is None:
        return por_defecto

    texto = valor.strip().lower()
    if texto in {"1", "true", "yes", "on"}:
        return True
    if texto in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{clave} debe ser un booleano valido")


def _leer_entero(clave: str, por_defecto: int, *, minimo: int | None = None) -> int:
    valor_crudo = os.getenv(clave, str(por_defecto))
    valor = int(valor_crudo)
    if minimo is not None and valor < minimo:
        raise ValueError(f"{clave} debe ser >= {minimo}")
    return valor


def _leer_float(clave: str, por_defecto: float, *, minimo: float | None = None) -> float:
    valor_crudo = os.getenv(clave, str(por_defecto))
    valor = float(valor_crudo)
    if minimo is not None and valor < minimo:
        raise ValueError(f"{clave} debe ser >= {minimo}")
    return valor


@dataclass(frozen=True)
class Settings:
    smtp_hostname: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_use_tls: bool
    smtp_use_ssl: bool
    smtp_timeout: float
    from_email: str
    from_name: str
    email_subject: str
    email_body: str
    db_path: Path
    daily_limit: int
    emails_per_hour: int
    delay_between_emails: float
    max_retries: int
    retry_base_delay: float
    log_level: str
    log_file: Path


def load_settings() -> Settings:
    correos_por_hora = _leer_entero("EMAILS_PER_HOUR", 250, minimo=1)
    usar_tls = _leer_bool("SMTP_USE_TLS", False)
    usar_ssl = _leer_bool("SMTP_USE_SSL", False)

    return Settings(
        smtp_hostname=os.getenv("SMTP_HOSTNAME", "localhost").strip(),
        smtp_port=_leer_entero("SMTP_PORT", 25, minimo=1),
        smtp_username=os.getenv("SMTP_USERNAME", "").strip(),
        smtp_password=os.getenv("SMTP_PASSWORD", "").strip(),
        smtp_use_tls=usar_tls,
        smtp_use_ssl=usar_ssl,
        smtp_timeout=_leer_float("SMTP_TIMEOUT", 15.0, minimo=0.1),
        from_email=os.getenv("FROM_EMAIL", "noreply@example.com").strip(),
        from_name=os.getenv("FROM_NAME", "Sistema de Correos").strip() or "Sistema de Correos",
        email_subject=os.getenv("EMAIL_SUBJECT", "Mensaje Importante").strip() or "Mensaje Importante",
        email_body=os.getenv("EMAIL_BODY", "Hola {nombre}, este es un mensaje importante."),
        db_path=Path(os.getenv("DB_PATH", "campaign.db")),
        daily_limit=_leer_entero("DAILY_LIMIT", 500, minimo=1),
        emails_per_hour=correos_por_hora,
        delay_between_emails=3600.0 / correos_por_hora,
        max_retries=_leer_entero("MAX_RETRIES", 3, minimo=0),
        retry_base_delay=_leer_float("RETRY_BASE_DELAY", 5.0, minimo=0.0),
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO",
        log_file=Path(os.getenv("LOG_FILE", "email_sender.log")),
    )


def configure_logging(log_level: str, log_file: Path) -> logging.Logger:
    logger = logging.getLogger("codex_email_sender")
    if logger.handlers:
        return logger

    nivel = getattr(logging, log_level, logging.INFO)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    formato = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    archivo = logging.FileHandler(log_file, encoding="utf-8")
    archivo.setFormatter(formato)

    consola = logging.StreamHandler()
    consola.setFormatter(formato)

    logger.setLevel(nivel)
    logger.addHandler(archivo)
    logger.addHandler(consola)
    logger.propagate = False
    return logger
