"""Persistent application settings for Pawn Passant."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any, Protocol

from utils.events import SettingsChangedEvent
from utils.models import AppSettings
from utils.signals import bus


class SettingsBackend(Protocol):
    async def load(self) -> dict[str, Any] | None: ...

    async def save(self, payload: dict[str, Any]) -> None: ...


class SharedPreferencesSettingsBackend:
    """Native key-value settings backed by Flet shared preferences."""

    def __init__(self, storage, storage_key: str):
        self.storage = storage
        self.storage_key = storage_key

    async def load(self) -> dict[str, Any] | None:
        raw_settings = await self._maybe_await(self.storage.get(self.storage_key))
        return self._decode_payload(raw_settings)

    async def save(self, payload: dict[str, Any]) -> None:
        await self._maybe_await(self.storage.set(self.storage_key, json.dumps(payload)))

    @staticmethod
    async def _maybe_await(value):
        if inspect.isawaitable(value):
            return await value
        return value

    @staticmethod
    def _decode_payload(raw_settings) -> dict[str, Any] | None:
        if isinstance(raw_settings, dict):
            return raw_settings
        if isinstance(raw_settings, str):
            try:
                decoded = json.loads(raw_settings)
            except json.JSONDecodeError:
                return None
            return decoded if isinstance(decoded, dict) else None
        return None


class JsonFileSettingsBackend:
    """JSON file settings stored under an app-local platform directory."""

    def __init__(self, file_path: Path):
        self.file_path = file_path

    async def load(self) -> dict[str, Any] | None:
        if not self.file_path.exists():
            return None
        try:
            return json.loads(self.file_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    async def save(self, payload: dict[str, Any]) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(json.dumps(payload), encoding="utf-8")


class SettingsController:
    """Owns app settings and persists them using platform-appropriate storage."""

    STORAGE_KEY = "pawnpassant.settings.v1"
    FILE_NAME = "settings.json"

    def __init__(self, page=None, settings: AppSettings | None = None):
        self.page = page
        self.settings = settings or AppSettings()
        self._backend: SettingsBackend | None = None

    async def load(self) -> AppSettings:
        backend = await self._get_backend()
        payload = await backend.load() if backend is not None else None
        self.settings = AppSettings.from_dict(payload)
        bus.emit(SettingsChangedEvent(self.settings))
        return self.settings

    async def save(self) -> None:
        backend = await self._get_backend()
        if backend is not None:
            await backend.save(self.settings.to_dict())

    def update(self, **changes: Any) -> AppSettings:
        self.settings = self.settings.updated(**changes)
        bus.emit(SettingsChangedEvent(self.settings))
        self._schedule_save()
        return self.settings

    def reset_defaults(self) -> AppSettings:
        self.settings = AppSettings()
        bus.emit(SettingsChangedEvent(self.settings))
        self._schedule_save()
        return self.settings

    def _schedule_save(self) -> None:
        if self.page is None:
            return
        run_task = getattr(self.page, "run_task", None)
        if callable(run_task):
            run_task(self.save)

    async def _get_backend(self) -> SettingsBackend | None:
        if self._backend is not None:
            return self._backend

        self._backend = await self._build_backend()
        return self._backend

    async def _build_backend(self) -> SettingsBackend | None:
        if self.page is None:
            return None

        platform_name = self._platform_name()
        storage = self._shared_preferences_storage()

        if platform_name == "android" and storage is not None:
            return SharedPreferencesSettingsBackend(storage, self.STORAGE_KEY)

        if platform_name == "windows":
            support_dir = await self._resolve_support_directory()
            if support_dir is not None:
                backend = JsonFileSettingsBackend(support_dir / self.FILE_NAME)
                await self._migrate_shared_preferences_to_file(backend, storage)
                return backend

        if storage is not None:
            return SharedPreferencesSettingsBackend(storage, self.STORAGE_KEY)

        support_dir = await self._resolve_support_directory()
        if support_dir is not None:
            return JsonFileSettingsBackend(support_dir / self.FILE_NAME)

        return None

    def _shared_preferences_storage(self):
        if self.page is None:
            return None

        storage = getattr(self.page, "shared_preferences", None)
        if storage is not None:
            return storage

        storage = getattr(self.page, "client_storage", None)
        if storage is not None:
            return storage

        shared_preferences_factory = getattr(self.page, "SharedPreferences", None)
        if callable(shared_preferences_factory):
            return shared_preferences_factory()

        return None

    async def _resolve_support_directory(self) -> Path | None:
        storage_paths = getattr(self.page, "storage_paths", None)
        if storage_paths is None or not hasattr(
            storage_paths, "get_application_support_directory"
        ):
            return None

        path = await self._maybe_await(
            storage_paths.get_application_support_directory()
        )
        if not path:
            return None
        return Path(path) / "pawnpassant"

    async def _migrate_shared_preferences_to_file(
        self,
        backend: JsonFileSettingsBackend,
        storage,
    ) -> None:
        if storage is None or backend.file_path.exists():
            return

        legacy_backend = SharedPreferencesSettingsBackend(storage, self.STORAGE_KEY)
        legacy_payload = await legacy_backend.load()
        if legacy_payload is not None:
            await backend.save(legacy_payload)

    def _platform_name(self) -> str:
        platform = getattr(self.page, "platform", None)
        if platform is None:
            return ""

        value = getattr(platform, "value", platform)
        return str(value).strip().lower()

    @staticmethod
    async def _maybe_await(value):
        if inspect.isawaitable(value):
            return await value
        return value
