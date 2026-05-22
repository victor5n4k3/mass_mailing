import argparse
import asyncio
import sys

from config import configure_logging, load_settings
from database import ContactRepository
from mailer import Mailer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Envio masivo de correos con SQLite y SMTP"
    )
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Crea la base de datos y la tabla contactos si no existen",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Cantidad maxima de contactos a procesar en esta ejecucion",
    )
    parser.add_argument(
        "--reset-processing",
        action="store_true",
        help="Devuelve a pending los contactos que quedaron en processing",
    )
    return parser


def print_summary(logger, stats) -> None:
    """Resumen corto para ver rapido como cerro la corrida."""

    logger.info("=" * 60)
    logger.info("RESUMEN")
    logger.info("Total: %s", stats.total)
    logger.info("Enviados: %s", stats.sent)
    logger.info("Fallidos: %s", stats.failed)
    logger.info("Invalidos: %s", stats.invalid)
    logger.info("Exito: %.2f%%", stats.success_rate)
    logger.info("=" * 60)


async def run() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        settings = load_settings()
    except ValueError as exc:
        print(f"Configuracion invalida: {exc}", file=sys.stderr)
        return 2

    logger = configure_logging(settings.log_level, settings.log_file)
    repository = ContactRepository(settings.db_path)

    if args.init_db:
        repository.initialize()
        logger.info("Base de datos inicializada en %s", settings.db_path)
        return 0

    is_valid, message = repository.validate_schema()
    if not is_valid:
        logger.error(message)
        logger.info("Usa --init-db para crear la estructura base si aun no existe.")
        return 1

    logger.info(message)

    # Esto sirve como boton de rescate si la corrida anterior se corto a mitad.
    if args.reset_processing:
        reset_count = repository.reset_processing_contacts()
        logger.info("Contactos recuperados desde processing: %s", reset_count)

    batch_limit = args.limit if args.limit is not None else settings.daily_limit
    if batch_limit < 1:
        logger.error("--limit debe ser >= 1")
        return 2

    contacts = repository.claim_pending_contacts(batch_limit)
    if not contacts:
        logger.info("No hay contactos pendientes para enviar")
        return 0

    logger.info("Reserve %s contactos para esta ejecucion", len(contacts))
    mailer = Mailer(settings, repository, logger)
    stats = await mailer.send_batch(contacts)
    print_summary(logger, stats)

    return 0 if stats.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
