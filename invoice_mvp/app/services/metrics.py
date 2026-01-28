"""Metrics collection and analysis for extractors."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path

from .extractors.base import ExtractionMetrics


class ExtractionMetricsCollector:
    """Collects and analyzes extraction metrics."""

    def __init__(self, metrics_file: str = "extraction_metrics.json"):
        self.metrics_file = Path(metrics_file)
        self.metrics: List[Dict[str, Any]] = []
        self._load_metrics()

    def _load_metrics(self) -> None:
        """Load existing metrics from file."""
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file, 'r') as f:
                    self.metrics = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.metrics = []

    def _save_metrics(self) -> None:
        """Save metrics to file."""
        try:
            with open(self.metrics_file, 'w') as f:
                json.dump(self.metrics, f, indent=2, default=str)
        except IOError:
            pass  # Silently fail if can't write

    def record_extraction(self, metrics: ExtractionMetrics, filename: str = "") -> None:
        """Record extraction metrics."""
        record = {
            "timestamp": datetime.now().isoformat(),
            "filename": filename,
            "provider": metrics.provider,
            "processing_time": metrics.processing_time,
            "success": metrics.success,
            "confidence": metrics.confidence,
            "error_message": metrics.error_message,
        }
        
        self.metrics.append(record)
        self._save_metrics()

    def get_provider_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics by provider."""
        stats = {}
        
        for metric in self.metrics:
            provider = metric["provider"]
            if provider not in stats:
                stats[provider] = {
                    "total_extractions": 0,
                    "successful_extractions": 0,
                    "failed_extractions": 0,
                    "avg_processing_time": 0.0,
                    "avg_confidence": 0.0,
                }
            
            provider_stats = stats[provider]
            provider_stats["total_extractions"] += 1
            
            if metric["success"]:
                provider_stats["successful_extractions"] += 1
            else:
                provider_stats["failed_extractions"] += 1
            
            provider_stats["avg_processing_time"] += metric["processing_time"]
            
            if metric["confidence"]:
                provider_stats["avg_confidence"] += metric["confidence"].get("overall", 0.0)
        
        # Calculate averages
        for provider_stats in stats.values():
            if provider_stats["total_extractions"] > 0:
                provider_stats["avg_processing_time"] /= provider_stats["total_extractions"]
                provider_stats["avg_confidence"] /= provider_stats["total_extractions"]
                provider_stats["success_rate"] = (
                    provider_stats["successful_extractions"] / provider_stats["total_extractions"]
                )
            else:
                provider_stats["success_rate"] = 0.0
        
        return stats

    def get_recent_extractions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent extraction records."""
        return self.metrics[-limit:] if self.metrics else []

    def clear_metrics(self) -> None:
        """Clear all metrics."""
        self.metrics = []
        self._save_metrics()


# Global metrics collector instance
metrics_collector = ExtractionMetricsCollector()
