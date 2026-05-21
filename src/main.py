"""Application entry point for launching the Flet chess interface."""

import flet as ft

from ui.app import main

# Set $env:PAWNPASSANT_DEV = "true" to expose the board-position selector.
# Keeping the flag at the entry point makes dev tooling opt-in without leaking
# test positions into the normal player-facing experience.

if __name__ == "__main__":
    ft.run(main)
