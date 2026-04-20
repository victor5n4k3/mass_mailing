from pathlib import Path


DB_PATH = Path("campaign.db")


def obtener_ruta_bd() -> Path:
    return DB_PATH
