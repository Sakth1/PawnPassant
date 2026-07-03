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
    Lc0 (Leela Chess Zero) integration for computer-opponent play.
engine_manager
    Generic UCI engine subprocess manager.
engine_verify
    Binary verification (ELF, UCI handshake) for any UCI engine.
engine_download
    Download and extract engine binaries from GitHub releases.
lc0_config
    Lc0-specific UCI options, backends, and platform config.
weights_downloader
    Neural network weights download and cache.
"""
