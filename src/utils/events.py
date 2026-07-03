from dataclasses import dataclass
from typing import Optional

from utils.models import ActiveColor, AppSettings
from utils.game_state import GameAgainst
from ui.chess_piece import ChessPiece


class BaseEvent:
    pass


@dataclass(frozen=True)
class PieceMovedEvent(BaseEvent):
    board_fen: str
    active_color: ActiveColor


@dataclass(frozen=True)
class GameStartedEvent(BaseEvent):
    opponent_nature: GameAgainst


@dataclass(frozen=True)
class SettingsChangedEvent(BaseEvent):
    settings: AppSettings


@dataclass(frozen=True)
class GameEndedEvent(BaseEvent):
    winner: Optional[str]
    reason: str
    message: str


@dataclass(frozen=True)
class ClockTickEvent(BaseEvent):
    color: ActiveColor
    minutes: int
    seconds: int
    milliseconds: int
    is_critical: bool


@dataclass(frozen=True)
class ClockStateEvent(BaseEvent):
    state: str
    active_color: Optional[ActiveColor]


@dataclass(frozen=True)
class PieceCapturedEvent(BaseEvent):
    piece: ChessPiece
    color: ActiveColor


@dataclass(frozen=True)
class EngineInfoReadyEvent(BaseEvent):
    release_tag: str
    asset_name: str
    asset_size_bytes: int
    asset_sha256: str
    asset_platform: str
    asset_arch: str


@dataclass(frozen=True)
class EngineDownloadProgressEvent(BaseEvent):
    bytes_downloaded: int
    total_bytes: int


@dataclass(frozen=True)
class EngineDownloadCompleteEvent(BaseEvent):
    download_path: str
    asset_name: str


@dataclass(frozen=True)
class EngineDownloadFailedEvent(BaseEvent):
    error_message: str


@dataclass(frozen=True)
class EngineBundledDetectedEvent(BaseEvent):
    path: str
    version: str


@dataclass(frozen=True)
class EngineDownloadReadyEvent(BaseEvent):
    download_path: str
    release_tag: str


@dataclass(frozen=True)
class BinaryVerificationResultEvent(BaseEvent):
    valid: bool
    path: str
    version: str

