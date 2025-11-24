"""Deduplication system for tracking previously reported sources.

Prevents repeating the same stories in weekly reports by maintaining
a rolling cache of source hashes (URL + title).
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Set, Dict, Any
import logging

logger = logging.getLogger(__name__)


class DeduplicationCache:
    """Manages deduplication cache for weekly reports."""

    def __init__(self, cache_dir: str = "./.cache/deduplication", window_days: int = 30):
        """Initialize deduplication cache.

        Args:
            cache_dir: Directory to store deduplication cache
            window_days: How many days back to check for duplicates
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.window_days = window_days
        self.index_file = self.cache_dir / "index.json"

    def _hash_source(self, url: str, title: str) -> str:
        """Generate hash for a source (URL + title).

        Args:
            url: Source URL
            title: Source title

        Returns:
            Hash string
        """
        combined = f"{url}|{title}".lower().strip()
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    def _load_index(self) -> Dict[str, Any]:
        """Load the deduplication index.

        Returns:
            Index dictionary
        """
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load deduplication index: {e}")
                return {"reports": []}
        return {"reports": []}

    def _save_index(self, index: Dict[str, Any]):
        """Save the deduplication index.

        Args:
            index: Index dictionary to save
        """
        try:
            with open(self.index_file, 'w') as f:
                json.dump(index, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save deduplication index: {e}")

    def load_previous_hashes(self) -> Set[str]:
        """Load all source hashes from the deduplication window.

        Returns:
            Set of hashes from previous reports within window
        """
        index = self._load_index()
        cutoff_date = datetime.now() - timedelta(days=self.window_days)

        all_hashes = set()
        for report in index.get("reports", []):
            try:
                report_date = datetime.fromisoformat(report["date"])
                if report_date >= cutoff_date:
                    all_hashes.update(report.get("hashes", []))
            except Exception as e:
                logger.debug(f"Could not parse report date: {e}")

        logger.info(f"Loaded {len(all_hashes)} previous source hashes from last {self.window_days} days")
        return all_hashes

    def check_duplicates(self, sources: List[Any], previous_hashes: Set[str]) -> tuple[List[Any], List[Any]]:
        """Check sources for duplicates against previous hashes.

        Args:
            sources: List of search results with url and title attributes
            previous_hashes: Set of hashes from previous reports

        Returns:
            Tuple of (new_sources, duplicate_sources)
        """
        new_sources = []
        duplicates = []

        for source in sources:
            url = getattr(source, 'url', '')
            title = getattr(source, 'title', '')

            if not url or not title:
                new_sources.append(source)  # Include if missing info
                continue

            source_hash = self._hash_source(url, title)

            if source_hash in previous_hashes:
                duplicates.append(source)
                logger.debug(f"Duplicate found: {title[:60]}...")
            else:
                new_sources.append(source)

        logger.info(f"Deduplication: {len(new_sources)} new, {len(duplicates)} duplicates ({len(duplicates)/len(sources)*100:.1f}%)")
        return new_sources, duplicates

    def save_report_hashes(self, sources: List[Any], report_date: datetime = None):
        """Save hashes from current report to cache.

        Args:
            sources: List of search results used in report
            report_date: Date of report (defaults to now)
        """
        if report_date is None:
            report_date = datetime.now()

        # Generate hashes for all sources
        hashes = []
        for source in sources:
            url = getattr(source, 'url', '')
            title = getattr(source, 'title', '')
            if url and title:
                hashes.append(self._hash_source(url, title))

        # Load index and add new report
        index = self._load_index()
        if "reports" not in index:
            index["reports"] = []

        report_entry = {
            "date": report_date.isoformat(),
            "hash_count": len(hashes),
            "hashes": hashes
        }
        index["reports"].append(report_entry)

        # Save updated index
        self._save_index(index)
        logger.info(f"Saved {len(hashes)} source hashes for report dated {report_date.date()}")

    def prune_old_entries(self):
        """Remove entries older than the deduplication window."""
        index = self._load_index()
        cutoff_date = datetime.now() - timedelta(days=self.window_days)

        original_count = len(index.get("reports", []))
        index["reports"] = [
            report for report in index.get("reports", [])
            if datetime.fromisoformat(report["date"]) >= cutoff_date
        ]

        pruned_count = original_count - len(index["reports"])
        if pruned_count > 0:
            self._save_index(index)
            logger.info(f"Pruned {pruned_count} old deduplication entries")

    def get_stats(self) -> Dict[str, Any]:
        """Get deduplication cache statistics.

        Returns:
            Dictionary with cache stats
        """
        index = self._load_index()
        reports = index.get("reports", [])

        if not reports:
            return {
                "total_reports": 0,
                "total_hashes": 0,
                "oldest_date": None,
                "newest_date": None
            }

        total_hashes = sum(r.get("hash_count", 0) for r in reports)
        dates = [datetime.fromisoformat(r["date"]) for r in reports]

        return {
            "total_reports": len(reports),
            "total_hashes": total_hashes,
            "oldest_date": min(dates).date().isoformat() if dates else None,
            "newest_date": max(dates).date().isoformat() if dates else None,
            "window_days": self.window_days
        }
