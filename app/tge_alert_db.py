import json
import logging
from typing import Dict, List, Optional

from database import Database
from tge_alert_config import DEFAULT_TGE_KEYWORDS, normalize_keywords


logger = logging.getLogger(__name__)


class TgeAlertDatabase:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
        self._init_tables()

    def _init_tables(self) -> None:
        conn = self.db.get_connection()
        cursor = conn.cursor()

        if self.db.use_postgres:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tge_project_alerts (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT NOT NULL,
                    project_name TEXT NOT NULL,
                    discord_channel_id TEXT,
                    keywords TEXT NOT NULL,
                    active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(telegram_id, project_name)
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tge_discord_state (
                    id SERIAL PRIMARY KEY,
                    project_name TEXT NOT NULL,
                    discord_channel_id TEXT NOT NULL,
                    last_message_id TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(project_name, discord_channel_id)
                )
                """
            )
        else:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tge_project_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    project_name TEXT NOT NULL,
                    discord_channel_id TEXT,
                    keywords TEXT NOT NULL,
                    active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(telegram_id, project_name)
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tge_discord_state (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_name TEXT NOT NULL,
                    discord_channel_id TEXT NOT NULL,
                    last_message_id TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(project_name, discord_channel_id)
                )
                """
            )

        conn.commit()
        conn.close()

    def _serialize_keywords(self, keywords: Optional[List[str]]) -> str:
        normalized = normalize_keywords(keywords or DEFAULT_TGE_KEYWORDS)
        return json.dumps(normalized)

    def _deserialize_keywords(self, value: Optional[str]) -> List[str]:
        if not value:
            return normalize_keywords(DEFAULT_TGE_KEYWORDS)
        try:
            data = json.loads(value)
            if isinstance(data, list):
                return normalize_keywords(data)
        except json.JSONDecodeError:
            pass
        parts = [item.strip() for item in value.split(",")]
        return normalize_keywords(parts)

    def _row_to_dict(self, row: object) -> Dict:
        return dict(row) if row is not None else {}

    def _coerce_active(self, value: object) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        if isinstance(value, (int, float)):
            return value != 0
        return str(value).lower() in {"true", "1", "yes"}

    def create_or_update_alert(
        self,
        telegram_id: int,
        project_name: str,
        discord_channel_id: Optional[str],
        keywords: Optional[List[str]] = None,
        active: bool = True,
    ) -> int:
        keywords_json = self._serialize_keywords(keywords)
        existing = self.get_alert_by_user_project(telegram_id, project_name)

        conn = self.db.get_connection()
        cursor = conn.cursor()

        if existing:
            if self.db.use_postgres:
                cursor.execute(
                    """
                    UPDATE tge_project_alerts
                    SET discord_channel_id = %s,
                        keywords = %s,
                        active = %s
                    WHERE id = %s
                    """,
                    (discord_channel_id, keywords_json, active, existing["id"]),
                )
            else:
                cursor.execute(
                    """
                    UPDATE tge_project_alerts
                    SET discord_channel_id = ?,
                        keywords = ?,
                        active = ?
                    WHERE id = ?
                    """,
                    (discord_channel_id, keywords_json, int(active), existing["id"]),
                )
            alert_id = existing["id"]
        else:
            if self.db.use_postgres:
                cursor.execute(
                    """
                    INSERT INTO tge_project_alerts
                    (telegram_id, project_name, discord_channel_id, keywords, active)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (telegram_id, project_name, discord_channel_id, keywords_json, active),
                )
                alert_id = cursor.fetchone()[0]
            else:
                cursor.execute(
                    """
                    INSERT INTO tge_project_alerts
                    (telegram_id, project_name, discord_channel_id, keywords, active)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        telegram_id,
                        project_name,
                        discord_channel_id,
                        keywords_json,
                        int(active),
                    ),
                )
                alert_id = cursor.lastrowid

        conn.commit()
        conn.close()
        return alert_id

    def get_alert_by_user_project(self, telegram_id: int, project_name: str) -> Optional[Dict]:
        conn = self.db.get_connection()

        if self.db.use_postgres:
            from psycopg2.extras import RealDictCursor

            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                """
                SELECT * FROM tge_project_alerts
                WHERE telegram_id = %s AND project_name = %s
                """,
                (telegram_id, project_name),
            )
        else:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM tge_project_alerts
                WHERE telegram_id = ? AND project_name = ?
                """,
                (telegram_id, project_name),
            )

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        alert = self._row_to_dict(row)
        alert["keywords"] = self._deserialize_keywords(alert.get("keywords"))
        alert["active"] = self._coerce_active(alert.get("active"))
        return alert

    def get_alert_by_id(self, alert_id: int) -> Optional[Dict]:
        conn = self.db.get_connection()

        if self.db.use_postgres:
            from psycopg2.extras import RealDictCursor

            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                """
                SELECT * FROM tge_project_alerts
                WHERE id = %s
                """,
                (alert_id,),
            )
        else:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM tge_project_alerts
                WHERE id = ?
                """,
                (alert_id,),
            )

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        alert = self._row_to_dict(row)
        alert["keywords"] = self._deserialize_keywords(alert.get("keywords"))
        alert["active"] = self._coerce_active(alert.get("active"))
        return alert

    def get_user_alerts(self, telegram_id: int) -> List[Dict]:
        conn = self.db.get_connection()

        if self.db.use_postgres:
            from psycopg2.extras import RealDictCursor

            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                """
                SELECT * FROM tge_project_alerts
                WHERE telegram_id = %s
                ORDER BY created_at DESC
                """,
                (telegram_id,),
            )
        else:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM tge_project_alerts
                WHERE telegram_id = ?
                ORDER BY created_at DESC
                """,
                (telegram_id,),
            )

        rows = cursor.fetchall()
        conn.close()

        alerts = [self._row_to_dict(row) for row in rows]
        for alert in alerts:
            alert["keywords"] = self._deserialize_keywords(alert.get("keywords"))
            alert["active"] = self._coerce_active(alert.get("active"))
        return alerts

    def get_active_alerts(self) -> List[Dict]:
        conn = self.db.get_connection()

        if self.db.use_postgres:
            from psycopg2.extras import RealDictCursor

            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                """
                SELECT * FROM tge_project_alerts
                WHERE active = TRUE
                ORDER BY created_at DESC
                """
            )
        else:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM tge_project_alerts
                WHERE active = 1
                ORDER BY created_at DESC
                """
            )

        rows = cursor.fetchall()
        conn.close()

        alerts = [self._row_to_dict(row) for row in rows]
        for alert in alerts:
            alert["keywords"] = self._deserialize_keywords(alert.get("keywords"))
            alert["active"] = self._coerce_active(alert.get("active"))
        return alerts

    def set_alert_active(self, alert_id: int, active: bool) -> None:
        conn = self.db.get_connection()
        cursor = conn.cursor()

        if self.db.use_postgres:
            cursor.execute(
                """
                UPDATE tge_project_alerts
                SET active = %s
                WHERE id = %s
                """,
                (active, alert_id),
            )
        else:
            cursor.execute(
                """
                UPDATE tge_project_alerts
                SET active = ?
                WHERE id = ?
                """,
                (int(active), alert_id),
            )

        conn.commit()
        conn.close()

    def remove_alert(self, alert_id: int) -> None:
        conn = self.db.get_connection()
        cursor = conn.cursor()

        if self.db.use_postgres:
            cursor.execute(
                "DELETE FROM tge_project_alerts WHERE id = %s",
                (alert_id,),
            )
        else:
            cursor.execute(
                "DELETE FROM tge_project_alerts WHERE id = ?",
                (alert_id,),
            )

        conn.commit()
        conn.close()

    def get_last_discord_message_id(
        self, project_name: str, discord_channel_id: str
    ) -> Optional[str]:
        conn = self.db.get_connection()

        if self.db.use_postgres:
            from psycopg2.extras import RealDictCursor

            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                """
                SELECT last_message_id FROM tge_discord_state
                WHERE project_name = %s AND discord_channel_id = %s
                """,
                (project_name, discord_channel_id),
            )
        else:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT last_message_id FROM tge_discord_state
                WHERE project_name = ? AND discord_channel_id = ?
                """,
                (project_name, discord_channel_id),
            )

        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        if isinstance(row, dict):
            return row.get("last_message_id")
        return row[0]

    def set_last_discord_message_id(
        self, project_name: str, discord_channel_id: str, message_id: str
    ) -> None:
        conn = self.db.get_connection()
        cursor = conn.cursor()

        if self.db.use_postgres:
            cursor.execute(
                """
                SELECT id FROM tge_discord_state
                WHERE project_name = %s AND discord_channel_id = %s
                """,
                (project_name, discord_channel_id),
            )
        else:
            cursor.execute(
                """
                SELECT id FROM tge_discord_state
                WHERE project_name = ? AND discord_channel_id = ?
                """,
                (project_name, discord_channel_id),
            )

        row = cursor.fetchone()
        exists = row is not None

        if exists:
            if self.db.use_postgres:
                cursor.execute(
                    """
                    UPDATE tge_discord_state
                    SET last_message_id = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE project_name = %s AND discord_channel_id = %s
                    """,
                    (message_id, project_name, discord_channel_id),
                )
            else:
                cursor.execute(
                    """
                    UPDATE tge_discord_state
                    SET last_message_id = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE project_name = ? AND discord_channel_id = ?
                    """,
                    (message_id, project_name, discord_channel_id),
                )
        else:
            if self.db.use_postgres:
                cursor.execute(
                    """
                    INSERT INTO tge_discord_state
                    (project_name, discord_channel_id, last_message_id)
                    VALUES (%s, %s, %s)
                    """,
                    (project_name, discord_channel_id, message_id),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO tge_discord_state
                    (project_name, discord_channel_id, last_message_id)
                    VALUES (?, ?, ?)
                    """,
                    (project_name, discord_channel_id, message_id),
                )

        conn.commit()
        conn.close()
