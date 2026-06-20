"""Core chess logic independent of Flet presentation controls.

Modules
------
game
    GameManager — board state, move validation, move execution, terminal
    detection, event emission.
movetype
    MoveType enum for special-move classification.
clock
    Threaded chess clock back-end with ticker and flag-fall detection.
bot_manager
    Stockfish integration for computer-opponent play.
"""
