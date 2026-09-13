import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO
from app.core.config import settings


class StorageBackend(ABC):
    """Abstract storage backend for files (local, S3, MinIO)."""

    @abstractmethod
    async def save_file(self, file_obj: BinaryIO, destination_path: str) -> str:
        pass

    @abstractmethod
    async def get_file_path(self, relative_path: str) -> str:
        pass

    @abstractmethod
    async def delete_file(self, relative_path: str) -> bool:
        pass


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage implementation."""

    def __init__(self, base_dir: str = settings.UPLOAD_DIR):
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def save_file(self, file_obj: BinaryIO, destination_path: str) -> str:
        full_path = (self.base_dir / destination_path).resolve()
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "wb") as f:
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)
            shutil.copyfileobj(file_obj, f)
        return str(full_path)

    async def get_file_path(self, relative_path: str) -> str:
        full_path = (self.base_dir / relative_path).resolve()
        return str(full_path)

    async def delete_file(self, relative_path: str) -> bool:
        full_path = (self.base_dir / relative_path).resolve()
        if full_path.exists():
            os.remove(full_path)
            return True
        return False


# Global default storage
storage: StorageBackend = LocalStorageBackend()
