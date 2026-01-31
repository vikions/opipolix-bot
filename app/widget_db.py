import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from database import Database


class WidgetDatabase:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
        self._init_tables()

    def _init_tables(self) -> None:
        conn = self.db.get_connection()
        cursor = conn.cursor()

        if self.db.use_postgres:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS bot_chats (
                    chat_id BIGINT PRIMARY KEY,
                    chat_title TEXT,
                    chat_type TEXT,
                    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS telegram_widgets (
                    widget_id SERIAL PRIMARY KEY,
                    owner_user_id BIGINT NOT NULL,
                    target_chat_id BIGINT NOT NULL UNIQUE,
                    board_message_id BIGINT NOT NULL,
                    selected_market_ids TEXT NOT NULL,
                    interval_seconds INTEGER NOT NULL,
                    enabled BOOLEAN DEFAULT TRUE,
                    compact_mode BOOLEAN DEFAULT TRUE,
                    last_render_hash TEXT,
                    last_rendered_at TIMESTAMP,
                    last_heartbeat_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        else:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS bot_chats (
                    chat_id INTEGER PRIMARY KEY,
                    chat_title TEXT,
                    chat_type TEXT,
                    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS telegram_widgets (
                    widget_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner_user_id INTEGER NOT NULL,
                    target_chat_id INTEGER NOT NULL UNIQUE,
                    board_message_id INTEGER NOT NULL,
                    selected_market_ids TEXT NOT NULL,
                    interval_seconds INTEGER NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    compact_mode INTEGER DEFAULT 1,
                    last_render_hash TEXT,
                    last_rendered_at TIMESTAMP,
                    last_heartbeat_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

        self._ensure_widget_columns(cursor)
        conn.commit()
        conn.close()

    def _ensure_widget_columns(self, cursor) -> None:
        if self.db.use_postgres:
            cursor.execute(
                "ALTER TABLE telegram_widgets "
                "ADD COLUMN IF NOT EXISTS compact_mode BOOLEAN DEFAULT TRUE"
            )
            cursor.execute(
                "ALTER TABLE telegram_widgets "
                "ADD COLUMN IF NOT EXISTS last_heartbeat_at TIMESTAMP"
            )
            return

        cursor.execute("PRAGMA table_info(telegram_widgets)")
        rows = cursor.fetchall() or []
        existing = set()
        for row in rows:
            if isinstance(row, dict):
                existing.add(row.get("name"))
            else:
                existing.add(row[1] if len(row) > 1 else None)

        if "compact_mode" not in existing:
            cursor.execute(
                "ALTER TABLE telegram_widgets ADD COLUMN compact_mode INTEGER DEFAULT 1"
            )
        if "last_heartbeat_at" not in existing:
            cursor.execute(
                "ALTER TABLE telegram_widgets ADD COLUMN last_heartbeat_at TIMESTAMP"
            )

    def _serialize_market_ids(self, market_ids: List[str]) -> str:
        return json.dumps(market_ids or [])

    def _deserialize_market_ids(self, value: Optional[str]) -> List[str]:
        if not value:
            return []
        try:
            data = json.loads(value)
            if isinstance(data, list):
                return [str(item) for item in data]
        except json.JSONDecodeError:
            pass
        return [item.strip() for item in value.split(",") if item.strip()]

    def _coerce_bool(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        if isinstance(value, (int, float)):
            return value != 0
        return str(value).lower() in {"true", "1", "yes"}

    def _parse_timestamp(self, value: Any) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                cleaned = value.replace("Z", "+00:00")
                parsed = datetime.fromisoformat(cleaned)
                return parsed.replace(tzinfo=None)
            except ValueError:
                return None
        return None

    def _row_to_dict(self, row: Any) -> Dict[str, Any]:
        return dict(row) if row is not None else {}

    def record_chat(self, chat_id: int, chat_title: str, chat_type: str) -> None:
        conn = self.db.get_connection()
        cursor = conn.cursor()

        if self.db.use_postgres:
            cursor.execute(
                """
                INSERT INTO bot_chats (chat_id, chat_title, chat_type, last_seen_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (chat_id) DO UPDATE
                SET chat_title = EXCLUDED.chat_title,
                    chat_type = EXCLUDED.chat_type,
                    last_seen_at = CURRENT_TIMESTAMP
                """,
                (chat_id, chat_title, chat_type),
            )
        else:
            cursor.execute(
                """
                INSERT INTO bot_chats (chat_id, chat_title, chat_type, last_seen_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(chat_id) DO UPDATE SET
                    chat_title = excluded.chat_title,
                    chat_type = excluded.chat_type,
                    last_seen_at = CURRENT_TIMESTAMP
                """,
                (chat_id, chat_title, chat_type),
            )

        conn.commit()
        conn.close()

    def get_known_chats(self) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()

        if self.db.use_postgres:
            from psycopg2.extras import RealDictCursor

            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                """
                SELECT chat_id, chat_title, chat_type, last_seen_at
                FROM bot_chats
                ORDER BY last_seen_at DESC
                """
            )
        else:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT chat_id, chat_title, chat_type, last_seen_at
                FROM bot_chats
                ORDER BY last_seen_at DESC
                """
            )

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(row) for row in rows]

    def create_widget(
        self,
        owner_user_id: int,
        target_chat_id: int,
        board_message_id: int,
        selected_market_ids: List[str],
        interval_seconds: int,
        enabled: bool = True,
        compact_mode: bool = True,
        last_render_hash: Optional[str] = None,
        last_rendered_at: Optional[datetime] = None,
        last_heartbeat_at: Optional[datetime] = None,
    ) -> int:
        market_ids_json = self._serialize_market_ids(selected_market_ids)
        rendered_at = last_rendered_at.isoformat() if last_rendered_at else None
        heartbeat_at = last_heartbeat_at.isoformat() if last_heartbeat_at else None

        conn = self.db.get_connection()
        cursor = conn.cursor()

        if self.db.use_postgres:
            cursor.execute(
                """
                INSERT INTO telegram_widgets
                (owner_user_id, target_chat_id, board_message_id, selected_market_ids,
                 interval_seconds, enabled, compact_mode, last_render_hash,
                 last_rendered_at, last_heartbeat_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING widget_id
                """,
                (
                    owner_user_id,
                    target_chat_id,
                    board_message_id,
                    market_ids_json,
                    interval_seconds,
                    enabled,
                    compact_mode,
                    last_render_hash,
                    rendered_at,
                    heartbeat_at,
                ),
            )
            widget_id = cursor.fetchone()[0]
        else:
            cursor.execute(
                """
                INSERT INTO telegram_widgets
                (owner_user_id, target_chat_id, board_message_id, selected_market_ids,
                 interval_seconds, enabled, compact_mode, last_render_hash,
                 last_rendered_at, last_heartbeat_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    owner_user_id,
                    target_chat_id,
                    board_message_id,
                    market_ids_json,
                    interval_seconds,
                    int(enabled),
                    int(compact_mode),
                    last_render_hash,
                    rendered_at,
                    heartbeat_at,
                ),
            )
            widget_id = cursor.lastrowid

        conn.commit()
        conn.close()
        return widget_id

    def _normalize_widget(self, row: Any) -> Optional[Dict[str, Any]]:
        if not row:
            return None
        widget = self._row_to_dict(row)
        widget["selected_market_ids"] = self._deserialize_market_ids(
            widget.get("selected_market_ids")
        )
        widget["enabled"] = self._coerce_bool(widget.get("enabled"))
        compact_value = widget.get("compact_mode")
        widget["compact_mode"] = True if compact_value is None else self._coerce_bool(compact_value)
        widget["interval_seconds"] = int(widget.get("interval_seconds") or 0)
        widget["last_rendered_at"] = self._parse_timestamp(widget.get("last_rendered_at"))
        widget["last_heartbeat_at"] = self._parse_timestamp(
            widget.get("last_heartbeat_at")
        )
        return widget

    def get_widget_by_id(self, widget_id: int) -> Optional[Dict[str, Any]]:
        conn = self.db.get_connection()

        if self.db.use_postgres:
            from psycopg2.extras import RealDictCursor

            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                "SELECT * FROM telegram_widgets WHERE widget_id = %s",
                (widget_id,),
            )
        else:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM telegram_widgets WHERE widget_id = ?",
                (widget_id,),
            )

        row = cursor.fetchone()
        conn.close()
        return self._normalize_widget(row)

    def get_widget_by_chat(self, target_chat_id: int) -> Optional[Dict[str, Any]]:
        conn = self.db.get_connection()

        if self.db.use_postgres:
            from psycopg2.extras import RealDictCursor

            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                "SELECT * FROM telegram_widgets WHERE target_chat_id = %s",
                (target_chat_id,),
            )
        else:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM telegram_widgets WHERE target_chat_id = ?",
                (target_chat_id,),
            )

        row = cursor.fetchone()
        conn.close()
        return self._normalize_widget(row)

    def get_user_widgets(self, owner_user_id: int) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()

        if self.db.use_postgres:
            from psycopg2.extras import RealDictCursor

            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                """
                SELECT w.*, c.chat_title
                FROM telegram_widgets w
                LEFT JOIN bot_chats c ON c.chat_id = w.target_chat_id
                WHERE w.owner_user_id = %s
                ORDER BY w.created_at DESC
                """,
                (owner_user_id,),
            )
        else:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT w.*, c.chat_title
                FROM telegram_widgets w
                LEFT JOIN bot_chats c ON c.chat_id = w.target_chat_id
                WHERE w.owner_user_id = ?
                ORDER BY w.created_at DESC
                """,
                (owner_user_id,),
            )

        rows = cursor.fetchall()
        conn.close()
        return [self._normalize_widget(row) for row in rows]

    def get_enabled_widgets(self) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()

        if self.db.use_postgres:
            from psycopg2.extras import RealDictCursor

            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                """
                SELECT w.*, c.chat_title
                FROM telegram_widgets w
                LEFT JOIN bot_chats c ON c.chat_id = w.target_chat_id
                WHERE w.enabled = TRUE
                ORDER BY w.updated_at DESC
                """
            )
        else:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT w.*, c.chat_title
                FROM telegram_widgets w
                LEFT JOIN bot_chats c ON c.chat_id = w.target_chat_id
                WHERE w.enabled = 1
                ORDER BY w.updated_at DESC
                """
            )

        rows = cursor.fetchall()
        conn.close()
        return [self._normalize_widget(row) for row in rows]

    def update_widget_markets(self, widget_id: int, selected_market_ids: List[str]) -> None:
        market_ids_json = self._serialize_market_ids(selected_market_ids)
        conn = self.db.get_connection()
        cursor = conn.cursor()

        if self.db.use_postgres:
            cursor.execute(
                """
                UPDATE telegram_widgets
                SET selected_market_ids = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE widget_id = %s
                """,
                (market_ids_json, widget_id),
            )
        else:
            cursor.execute(
                """
                UPDATE telegram_widgets
                SET selected_market_ids = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE widget_id = ?
                """,
                (market_ids_json, widget_id),
            )

        conn.commit()
        conn.close()

    def update_widget_interval(self, widget_id: int, interval_seconds: int) -> None:
        conn = self.db.get_connection()
        cursor = conn.cursor()

        if self.db.use_postgres:
            cursor.execute(
                """
                UPDATE telegram_widgets
                SET interval_seconds = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE widget_id = %s
                """,
                (interval_seconds, widget_id),
            )
        else:
            cursor.execute(
                """
                UPDATE telegram_widgets
                SET interval_seconds = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE widget_id = ?
                """,
                (interval_seconds, widget_id),
            )

        conn.commit()
        conn.close()

    def set_widget_enabled(self, widget_id: int, enabled: bool) -> None:
        conn = self.db.get_connection()
        cursor = conn.cursor()

        if self.db.use_postgres:
            cursor.execute(
                """
                UPDATE telegram_widgets
                SET enabled = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE widget_id = %s
                """,
                (enabled, widget_id),
            )
        else:
            cursor.execute(
                """
                UPDATE telegram_widgets
                SET enabled = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE widget_id = ?
                """,
                (int(enabled), widget_id),
            )

        conn.commit()
        conn.close()

    def set_widget_compact_mode(self, widget_id: int, compact_mode: bool) -> None:
        conn = self.db.get_connection()
        cursor = conn.cursor()

        if self.db.use_postgres:
            cursor.execute(
                """
                UPDATE telegram_widgets
                SET compact_mode = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE widget_id = %s
                """,
                (compact_mode, widget_id),
            )
        else:
            cursor.execute(
                """
                UPDATE telegram_widgets
                SET compact_mode = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE widget_id = ?
                """,
                (int(compact_mode), widget_id),
            )

        conn.commit()
        conn.close()

    def mark_widget_dirty(self, widget_id: int) -> None:
        conn = self.db.get_connection()
        cursor = conn.cursor()

        if self.db.use_postgres:
            cursor.execute(
                """
                UPDATE telegram_widgets
                SET last_render_hash = NULL,
                    last_rendered_at = NULL,
                    last_heartbeat_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE widget_id = %s
                """,
                (widget_id,),
            )
        else:
            cursor.execute(
                """
                UPDATE telegram_widgets
                SET last_render_hash = NULL,
                    last_rendered_at = NULL,
                    last_heartbeat_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE widget_id = ?
                """,
                (widget_id,),
            )

        conn.commit()
        conn.close()

    def update_render_state(
        self,
        widget_id: int,
        render_hash: str,
        rendered_at: datetime,
        heartbeat_at: Optional[datetime] = None,
    ) -> None:
        rendered_at_value = rendered_at.isoformat() if rendered_at else None
        heartbeat_value = heartbeat_at.isoformat() if heartbeat_at else None
        conn = self.db.get_connection()
        cursor = conn.cursor()

        if self.db.use_postgres:
            cursor.execute(
                """
                UPDATE telegram_widgets
                SET last_render_hash = %s,
                    last_rendered_at = %s,
                    last_heartbeat_at = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE widget_id = %s
                """,
                (render_hash, rendered_at_value, heartbeat_value, widget_id),
            )
        else:
            cursor.execute(
                """
                UPDATE telegram_widgets
                SET last_render_hash = ?,
                    last_rendered_at = ?,
                    last_heartbeat_at = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE widget_id = ?
                """,
                (render_hash, rendered_at_value, heartbeat_value, widget_id),
            )

        conn.commit()
        conn.close()

    def delete_widget(self, widget_id: int) -> None:
        conn = self.db.get_connection()
        cursor = conn.cursor()

        if self.db.use_postgres:
            cursor.execute(
                "DELETE FROM telegram_widgets WHERE widget_id = %s",
                (widget_id,),
            )
        else:
            cursor.execute(
                "DELETE FROM telegram_widgets WHERE widget_id = ?",
                (widget_id,),
            )

        conn.commit()
        conn.close()
