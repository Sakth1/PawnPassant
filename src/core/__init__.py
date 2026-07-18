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
engine_manager
    Generic UCI engine subprocess manager.
engine_verify
    Binary verification (ELF, UCI handshake) for any UCI engine.
engine_download
    Download and extract engine binaries from GitHub releases.
stockfish_config
    Stockfish Elo presets, platform configs, and download configs.
difficulty_presets
    Stockfish Elo level presets (re-exports from stockfish_config).
"""
