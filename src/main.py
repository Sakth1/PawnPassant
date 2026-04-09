"""Application entry point for launching the Flet chess interface."""

from ui.gui import main

import flet as ft

# Set $env:PAWNPASSANT_DEV = "true" to expose the development board-position selector.
# Remove the variable to return to the normal player-facing experience.

if __name__ == "__main__":
    ft.run(main)
