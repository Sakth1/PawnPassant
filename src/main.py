"""Application entry point for launching the Flet chess interface."""

import flet as ft
import logging

from app import EntryPoint
from utils.logging_config import configure_logging

logger = logging.getLogger(__name__)

# Set $env:PAWNPASSANT_DEV = "true" to expose the board-position selector.
# Keeping the flag at the entry point makes dev tooling opt-in without leaking
# test positions into the normal player-facing experience.

if __name__ == "__main__":
    configure_logging()
    logger.info("Starting Pawn Passant...")
    try:
        ft.run(EntryPoint)
    except Exception:
        logger.exception("Unhandled exception occurred in the application")
        raise
