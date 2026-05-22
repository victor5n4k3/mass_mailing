import sqlite3
from pathlib import Path

from models import Contact


VALID_STATUSES = ("pending", "processing", "sent", "failed", "invalid")


class ContactRepository:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS contactos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE,
                    nombre TEXT NOT NULL DEFAULT 'Cliente',
                    status TEXT NOT NULL DEFAULT 'pending',
                    last_error TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_contactos_status
                ON contactos(status)
                """
            )

    def validate_schema(self) -> tuple[bool, str]:
        if not self.db_path.exists():
            return False, f"No existe la base de datos: {self.db_path}"

        required_columns = {
            "email",
            "nombre",
            "status",
            "last_error",
            "created_at",
            "updated_at",
        }

        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='contactos'"
                ).fetchone()
                if row is None:
                    return False, "La tabla 'contactos' no existe"

                columns = {
                    item["name"]
                    for item in connection.execute("PRAGMA table_info(contactos)").fetchall()
                }
        except sqlite3.Error as exc:
            return False, f"Error validando la base de datos: {exc}"

        missing_columns = sorted(required_columns - columns)
        if missing_columns:
            return False, f"Faltan columnas requeridas: {', '.join(missing_columns)}"

        return True, "Base de datos validada"

    def claim_pending_contacts(self, limit: int) -> list[Contact]:
        # Reservamos primero y enviamos despues. Asi evitamos que dos corridas
        # tomen los mismos contactos al mismo tiempo.
        query = """
            UPDATE contactos
            SET status = 'processing',
                updated_at = CURRENT_TIMESTAMP,
                last_error = NULL
            WHERE id IN (
                SELECT id
                FROM contactos
                WHERE status = 'pending'
                ORDER BY id
                LIMIT ?
            )
            RETURNING email, nombre, status
        """

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(query, (limit,)).fetchall()
            connection.commit()

        return [Contact.model_validate(dict(row)) for row in rows]

    def update_status(self, email: str, status: str, error_message: str | None = None) -> None:
        if status not in VALID_STATUSES:
            raise ValueError(f"Estado no permitido: {status}")

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE contactos
                SET status = ?, last_error = ?, updated_at = CURRENT_TIMESTAMP
                WHERE email = ?
                """,
                (status, error_message, email),
            )

    def reset_processing_contacts(self) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE contactos
                SET status = 'pending', updated_at = CURRENT_TIMESTAMP
                WHERE status = 'processing'
                """
            )
            return cursor.rowcount
