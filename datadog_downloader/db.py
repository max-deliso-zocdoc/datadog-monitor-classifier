"""Database operations for storing monitor data."""

import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Set

from .client import Monitor, NotificationTarget

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
-- Monitors table stores the main monitor information
CREATE TABLE IF NOT EXISTS monitors (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    message TEXT,
    type TEXT,
    query TEXT,
    priority TEXT,
    state TEXT,
    overall_state TEXT,
    options TEXT,  -- JSON string
    project TEXT,
    first_seen TIMESTAMP,
    last_updated TIMESTAMP,
    fetched_at TIMESTAMP,  -- When the monitor was last fetched from the API
    is_active BOOLEAN DEFAULT 1
);

-- Tags table for monitor tags
CREATE TABLE IF NOT EXISTS monitor_tags (
    monitor_id INTEGER,
    tag TEXT,
    PRIMARY KEY (monitor_id, tag),
    FOREIGN KEY (monitor_id) REFERENCES monitors(id) ON DELETE CASCADE
);

-- Notifications table for storing notification targets and context
CREATE TABLE IF NOT EXISTS monitor_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    monitor_id INTEGER,
    target TEXT NOT NULL,
    context TEXT,
    is_recovery BOOLEAN,
    FOREIGN KEY (monitor_id) REFERENCES monitors(id) ON DELETE CASCADE
);

-- Downtimes table for storing monitor downtimes
CREATE TABLE IF NOT EXISTS monitor_downtimes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    monitor_id INTEGER,
    downtime_data TEXT,  -- JSON string
    FOREIGN KEY (monitor_id) REFERENCES monitors(id) ON DELETE CASCADE
);

-- Index for faster project lookups
CREATE INDEX IF NOT EXISTS idx_monitors_project ON monitors(project);

-- Index for faster tag lookups
CREATE INDEX IF NOT EXISTS idx_monitor_tags_tag ON monitor_tags(tag);

-- Index for faster fetched_at lookups
CREATE INDEX IF NOT EXISTS idx_monitors_fetched_at ON monitors(fetched_at);
"""


class MonitorDB:
    """Database operations for monitor data."""

    def __init__(self, db_path: Optional[str] = None, fetch_interval: timedelta = timedelta(days=1)):
        """Initialize database connection."""
        if db_path is None:
            db_path = Path("data") / "monitors.db"

        # Ensure directory exists
        db_path.parent.mkdir(exist_ok=True)

        self.db_path = db_path
        self.fetch_interval = fetch_interval
        self._init_db()

    @contextmanager
    def get_connection(self):
        """Get a database connection with automatic closing."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        """Initialize database schema."""
        with self.get_connection() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

    def get_monitors_needing_refresh(self) -> Set[int]:
        """Get set of monitor IDs that need to be refreshed based on fetch_interval."""
        cutoff_time = datetime.utcnow() - self.fetch_interval
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Get monitors that haven't been fetched recently or have never been fetched
            cursor.execute("""
                SELECT id FROM monitors
                WHERE fetched_at IS NULL
                OR fetched_at < ?
                OR is_active = 1
            """, (cutoff_time,))
            return {row[0] for row in cursor.fetchall()}

    def get_all_monitor_ids(self) -> Set[int]:
        """Get all monitor IDs in the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM monitors")
            return {row[0] for row in cursor.fetchall()}

    def upsert_monitor(self, monitor: Monitor):
        """Upsert a monitor and its related data."""
        now = datetime.utcnow()

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Check if monitor exists
            cursor.execute(
                "SELECT first_seen FROM monitors WHERE id = ?",
                (monitor.id,)
            )
            result = cursor.fetchone()
            first_seen = result[0] if result else now

            # Upsert monitor
            cursor.execute("""
                INSERT INTO monitors (
                    id, name, message, type, query, priority,
                    state, overall_state, options, project,
                    first_seen, last_updated, fetched_at, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    message = excluded.message,
                    type = excluded.type,
                    query = excluded.query,
                    priority = excluded.priority,
                    state = excluded.state,
                    overall_state = excluded.overall_state,
                    options = excluded.options,
                    project = excluded.project,
                    last_updated = excluded.last_updated,
                    fetched_at = excluded.fetched_at,
                    is_active = 1
            """, (
                monitor.id, monitor.name, monitor.message, monitor.type,
                monitor.query, monitor.priority, monitor.state,
                monitor.overall_state, str(monitor.options), monitor.project,
                first_seen, now, now
            ))

            # Update tags
            cursor.execute("DELETE FROM monitor_tags WHERE monitor_id = ?", (monitor.id,))
            cursor.executemany(
                "INSERT INTO monitor_tags (monitor_id, tag) VALUES (?, ?)",
                [(monitor.id, tag) for tag in monitor.tags]
            )

            # Update notifications
            cursor.execute(
                "DELETE FROM monitor_notifications WHERE monitor_id = ?",
                (monitor.id,)
            )
            cursor.executemany(
                """INSERT INTO monitor_notifications
                   (monitor_id, target, context, is_recovery)
                   VALUES (?, ?, ?, ?)""",
                [(monitor.id, n.target, n.context, n.is_recovery)
                 for n in monitor.notify_targets]
            )

            # Update downtimes
            if monitor.matching_downtimes:
                cursor.execute(
                    "DELETE FROM monitor_downtimes WHERE monitor_id = ?",
                    (monitor.id,)
                )
                cursor.executemany(
                    "INSERT INTO monitor_downtimes (monitor_id, downtime_data) VALUES (?, ?)",
                    [(monitor.id, str(downtime))
                     for downtime in monitor.matching_downtimes]
                )

            conn.commit()

    def mark_inactive_monitors(self, active_monitor_ids: List[int]):
        """Mark monitors not in the active list as inactive."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ','.join('?' * len(active_monitor_ids))
            cursor.execute(
                f"UPDATE monitors SET is_active = 0 WHERE id NOT IN ({placeholders})",
                active_monitor_ids
            )
            conn.commit()

    def get_monitor_count_by_project(self) -> Dict[str, int]:
        """Get count of active monitors by project."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT project, COUNT(*) as count
                FROM monitors
                WHERE is_active = 1
                GROUP BY project
            """)
            return {row[0]: row[1] for row in cursor.fetchall()}