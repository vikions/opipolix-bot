"""
Database for TGE Agent Mode - user-controlled autonomous agents
"""
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict


class AgentDatabase:
    def __init__(self, db_path: str = "tge_agents.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Create agents and decisions tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Main agents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tge_agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                agent_name TEXT,
                discord_channel_id TEXT NOT NULL,
                discord_channel_name TEXT,
                auto_trade_enabled BOOLEAN DEFAULT 0,
                max_trade_amount_usdc REAL DEFAULT 10.0,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_checked_at TIMESTAMP,
                UNIQUE(telegram_id, discord_channel_id)
            )
        """)

        # Agent decision history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER NOT NULL,
                discord_message_id TEXT,
                signal_text TEXT,
                confidence_score REAL,
                action TEXT,
                reasoning TEXT,
                market_data JSON,
                predictos_analysis JSON,
                discovered_tools JSON,
                trade_executed BOOLEAN DEFAULT 0,
                trade_amount_usdc REAL,
                trade_order_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES tge_agents(id)
            )
        """)

        conn.commit()
        conn.close()

    def create_agent(
        self,
        telegram_id: int,
        discord_channel_id: str,
        agent_name: str = None,
        discord_channel_name: str = None,
        auto_trade_enabled: bool = False,
        max_trade_amount_usdc: float = 10.0,
    ) -> int:
        """Create new agent, return agent_id"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO tge_agents 
            (telegram_id, agent_name, discord_channel_id, discord_channel_name, 
             auto_trade_enabled, max_trade_amount_usdc, status)
            VALUES (?, ?, ?, ?, ?, ?, 'active')
        """, (telegram_id, agent_name, discord_channel_id, discord_channel_name, auto_trade_enabled, max_trade_amount_usdc))

        agent_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return agent_id

    def get_user_agents(self, telegram_id: int) -> List[Dict]:
        """Get all agents for user"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM tge_agents 
            WHERE telegram_id = ?
            ORDER BY created_at DESC
        """, (telegram_id,))

        agents = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return agents

    def get_active_agents(self) -> List[Dict]:
        """Get all active agents for worker to monitor"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM tge_agents 
            WHERE status = 'active'
        """)

        agents = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return agents

    def toggle_agent_status(self, agent_id: int) -> str:
        """Toggle between active/paused, return new status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT status FROM tge_agents WHERE id = ?", (agent_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return 'not_found'
        current_status = row[0]
        new_status = 'paused' if current_status == 'active' else 'active'

        cursor.execute("UPDATE tge_agents SET status = ? WHERE id = ?", (new_status, agent_id))

        conn.commit()
        conn.close()
        return new_status

    def toggle_auto_trade(self, agent_id: int) -> bool:
        """Toggle auto-trade on/off, return new state"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT auto_trade_enabled FROM tge_agents WHERE id = ?", (agent_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        current_state = bool(row[0])
        new_state = not current_state

        cursor.execute(
            "UPDATE tge_agents SET auto_trade_enabled = ? WHERE id = ?",
            (int(new_state), agent_id),
        )

        conn.commit()
        conn.close()
        return new_state

    def update_max_trade_amount(self, agent_id: int, amount: float):
        """Update max trade amount"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE tge_agents SET max_trade_amount_usdc = ? WHERE id = ?",
            (amount, agent_id),
        )

        conn.commit()
        conn.close()

    def delete_agent(self, agent_id: int):
        """Delete agent"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tge_agents WHERE id = ?", (agent_id,))
        conn.commit()
        conn.close()

    def log_decision(
        self,
        agent_id: int,
        discord_message_id: str,
        signal_text: str,
        confidence_score: float,
        action: str,
        reasoning: str,
        market_data: dict = None,
        predictos_analysis: dict = None,
        discovered_tools: dict = None,
        trade_executed: bool = False,
        trade_amount_usdc: float = None,
        trade_order_id: str = None,
    ):
        """Log agent decision to history"""
        import json

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO agent_decisions
            (agent_id, discord_message_id, signal_text, confidence_score, action,
             reasoning, market_data, predictos_analysis, discovered_tools,
             trade_executed, trade_amount_usdc, trade_order_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            agent_id,
            discord_message_id,
            signal_text,
            confidence_score,
            action,
            reasoning,
            json.dumps(market_data) if market_data else None,
            json.dumps(predictos_analysis) if predictos_analysis else None,
            json.dumps(discovered_tools) if discovered_tools else None,
            int(trade_executed),
            trade_amount_usdc,
            trade_order_id,
        ))

        conn.commit()
        conn.close()

    def get_agent_history(self, agent_id: int, limit: int = 10) -> List[Dict]:
        """Get decision history for agent"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM agent_decisions
            WHERE agent_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """,
            (agent_id, limit),
        )

        history = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return history
