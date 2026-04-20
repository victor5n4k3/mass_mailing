import logging
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "email_sender.log"


def configurar_logger() -> logging.Logger:
    logger = logging.getLogger("codex_email_sender")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formato = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    archivo = logging.FileHandler(LOG_FILE, encoding="utf-8")
    archivo.setFormatter(formato)

    consola = logging.StreamHandler()
    consola.setFormatter(formato)

    logger.addHandler(archivo)
    logger.addHandler(consola)
    logger.propagate = False
    return logger


logger = configurar_logger()
