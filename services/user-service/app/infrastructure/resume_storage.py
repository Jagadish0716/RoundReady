import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class StoredResume:
    object_key: str
    path: Path


class ResumeStorage(Protocol):
    async def put(self, object_key: str, content: bytes) -> StoredResume: ...

    async def resolve(self, object_key: str) -> Path: ...


class LocalResumeStorage:
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    def _path(self, object_key: str) -> Path:
        if Path(object_key).name != object_key:
            raise ValueError("invalid resume object key")
        path = (self._root / object_key).resolve()
        if path.parent != self._root:
            raise ValueError("invalid resume object key")
        return path

    async def put(self, object_key: str, content: bytes) -> StoredResume:
        path = self._path(object_key)

        def write() -> None:
            self._root.mkdir(parents=True, exist_ok=True, mode=0o700)
            path.write_bytes(content)
            path.chmod(0o600)

        await asyncio.to_thread(write)
        return StoredResume(object_key=object_key, path=path)

    async def resolve(self, object_key: str) -> Path:
        path = self._path(object_key)
        exists = await asyncio.to_thread(path.is_file)
        if not exists:
            raise FileNotFoundError(object_key)
        return path
