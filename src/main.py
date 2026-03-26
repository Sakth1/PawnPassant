"""Application entry point for launching the Flet chess interface."""

import flet as ft

from Ui.Gui import main

# Set $env:PAWNPASSANT_DEV = "true" to expose the development board-position selector.
# Remove the variable to return to the normal player-facing experience.

if __name__ == "__main__":
    ft.run(main)
