from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from ..core import RubroNomenclatorEntry, RubroNormalizationResult


@dataclass
class RubroNomenclator:
    """Simple in-memory nomenclator.

    Architectural decision: keep this as a thin data holder so we can later
    replace it with a database or vector store-backed RAG without changing
    the orchestrator.
    """

    by_code: Dict[str, RubroNomenclatorEntry]
    by_name: Dict[str, RubroNomenclatorEntry]

    @classmethod
    def from_csv(cls, path: Path) -> "RubroNomenclator":
        by_code: Dict[str, RubroNomenclatorEntry] = {}
        by_name: Dict[str, RubroNomenclatorEntry] = {}
        with path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row.get("code") or ""
                name = row.get("name") or ""
                if not code or not name:
                    continue
                entry = RubroNomenclatorEntry(code=code, name=name)
                by_code[code] = entry
                by_name[name.lower()] = entry
        return cls(by_code=by_code, by_name=by_name)

    def normalize(self, rubro_raw: str) -> Optional[RubroNomenclatorEntry]:
        # Trivial implementation: exact match by name (case-insensitive)
        return self.by_name.get(rubro_raw.lower())


class RubroNormalizerService:
    """Service responsible for normalizing rubros using a nomenclator.

    For MVP we keep the logic minimal and deterministic. RAG/LLM-based
    enrichment can be added later behind this interface.
    """

    def __init__(self, nomenclator: Optional[RubroNomenclator] = None) -> None:
        self._nomenclator = nomenclator

    def normalize_lines(self, rubros: Iterable[str]) -> List[RubroNormalizationResult]:
        results: List[RubroNormalizationResult] = []
        for idx, rubro_raw in enumerate(rubros):
            entry: Optional[RubroNomenclatorEntry] = None
            if self._nomenclator is not None:
                entry = self._nomenclator.normalize(rubro_raw)
            results.append(
                RubroNormalizationResult(
                    line_index=idx,
                    original_rubro=rubro_raw,
                    normalized_code=entry.code if entry else None,
                    normalized_name=entry.name if entry else None,
                )
            )
        return results

