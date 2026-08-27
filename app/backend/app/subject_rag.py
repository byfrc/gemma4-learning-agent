from __future__ import annotations

from threading import RLock

from .config import Settings
from .rag import HybridRAGEngine
from .subjects import normalize_subject


class SubjectRAGManager:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._lock = RLock()
        self._engines: dict[str, HybridRAGEngine] = {}

    def get(self, subject: str | None = None) -> HybridRAGEngine:
        key = normalize_subject(subject)
        with self._lock:
            engine = self._engines.get(key)
            if engine is None:
                engine = HybridRAGEngine(
                    knowledge_dir=self.settings.knowledge_dir_for(key),
                    index_path=self.settings.rag_index_path_for(key),
                    chunk_size=self.settings.rag_chunk_size,
                    overlap=self.settings.rag_chunk_overlap,
                )
                self._engines[key] = engine
            return engine

    def rebuild(self, subject: str | None = None) -> None:
        self.get(subject).rebuild()

    def status(self, subject: str | None = None) -> tuple[int, int, list[str]]:
        return self.get(subject).status()
