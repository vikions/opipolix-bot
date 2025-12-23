"""
Worker Health Monitor
Track worker status, iterations, and errors
"""
import os
import json
from datetime import datetime
from typing import Dict, Optional

HEALTH_FILE = "worker_health.json"


class WorkerHealthMonitor:
    """Monitor worker health and activity"""
    
    def __init__(self):
        self.health_file = HEALTH_FILE
        self.load_health()
    
    def load_health(self):
        """Load health data from file"""
        if os.path.exists(self.health_file):
            try:
                with open(self.health_file, 'r') as f:
                    self.health = json.load(f)
            except:
                self.health = self.create_default_health()
        else:
            self.health = self.create_default_health()
    
    def create_default_health(self) -> Dict:
        """Create default health structure"""
        return {
            'status': 'stopped',
            'started_at': None,
            'last_check': None,
            'total_iterations': 0,
            'active_orders_checked': 0,
            'orders_executed': 0,
            'orders_failed': 0,
            'last_error': None,
            'uptime_seconds': 0
        }
    
    def save_health(self):
        """Save health data to file"""
        try:
            with open(self.health_file, 'w') as f:
                json.dump(self.health, f, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to save health: {e}")
    
    def mark_started(self):
        """Mark worker as started"""
        self.health['status'] = 'running'
        self.health['started_at'] = datetime.now().isoformat()
        self.health['last_check'] = datetime.now().isoformat()
        self.save_health()
    
    def mark_iteration(self, active_orders_count: int = 0):
        """Mark completed iteration"""
        self.health['status'] = 'running'
        self.health['last_check'] = datetime.now().isoformat()
        self.health['total_iterations'] += 1
        self.health['active_orders_checked'] += active_orders_count
        
        # Calculate uptime
        if self.health['started_at']:
            started = datetime.fromisoformat(self.health['started_at'])
            now = datetime.now()
            self.health['uptime_seconds'] = int((now - started).total_seconds())
        
        self.save_health()
    
    def mark_order_executed(self):
        """Mark order as executed"""
        self.health['orders_executed'] += 1
        self.save_health()
    
    def mark_order_failed(self):
        """Mark order as failed"""
        self.health['orders_failed'] += 1
        self.save_health()
    
    def mark_error(self, error: str):
        """Mark error"""
        self.health['last_error'] = {
            'message': str(error),
            'timestamp': datetime.now().isoformat()
        }
        self.save_health()
    
    def mark_stopped(self):
        """Mark worker as stopped"""
        self.health['status'] = 'stopped'
        self.save_health()
    
    def get_health(self) -> Dict:
        """Get current health status"""
        return self.health
    
    def is_healthy(self) -> bool:
        """Check if worker is healthy"""
        if self.health['status'] != 'running':
            return False
        
        # Check if last check was recent (within 60 seconds)
        if self.health['last_check']:
            last_check = datetime.fromisoformat(self.health['last_check'])
            now = datetime.now()
            seconds_ago = (now - last_check).total_seconds()
            
            if seconds_ago > 60:
                return False  # Worker hasn't checked in over 60 seconds
        
        return True
    
    def format_status(self) -> str:
        """Format status message"""
        health = self.get_health()
        is_healthy = self.is_healthy()
        
        # Status emoji
        status_emoji = "🟢" if is_healthy else "🔴"
        status_text = "RUNNING" if is_healthy else "STOPPED/STALE"
        
        # Uptime
        uptime = health.get('uptime_seconds', 0)
        uptime_str = self.format_uptime(uptime)
        
        # Last check
        last_check = health.get('last_check')
        if last_check:
            last_check_dt = datetime.fromisoformat(last_check)
            last_check_str = last_check_dt.strftime("%Y-%m-%d %H:%M:%S")
            seconds_ago = int((datetime.now() - last_check_dt).total_seconds())
            last_check_str += f" ({seconds_ago}s ago)"
        else:
            last_check_str = "Never"
        
        # Build message
        lines = [
            f"{status_emoji} *Worker Status: {status_text}*\n",
            f"⏰ *Uptime:* {uptime_str}",
            f"🔄 *Iterations:* {health.get('total_iterations', 0)}",
            f"📊 *Orders checked:* {health.get('active_orders_checked', 0)}",
            f"✅ *Executed:* {health.get('orders_executed', 0)}",
            f"❌ *Failed:* {health.get('orders_failed', 0)}",
            f"🕐 *Last check:* {last_check_str}"
        ]
        
        # Last error
        if health.get('last_error'):
            error_msg = health['last_error'].get('message', 'Unknown')
            error_time = health['last_error'].get('timestamp', '')
            if error_time:
                error_dt = datetime.fromisoformat(error_time)
                error_time_str = error_dt.strftime("%H:%M:%S")
            else:
                error_time_str = "Unknown"
            
            lines.append(f"\n⚠️ *Last error:*")
            lines.append(f"  {error_msg}")
            lines.append(f"  At: {error_time_str}")
        
        return "\n".join(lines)
    
    def format_uptime(self, seconds: int) -> str:
        """Format uptime seconds to human readable"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}m"
        elif seconds < 86400:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            return f"{days}d {hours}h"


# Global instance
_monitor = None

def get_monitor() -> WorkerHealthMonitor:
    """Get global health monitor instance"""
    global _monitor
    if _monitor is None:
        _monitor = WorkerHealthMonitor()
    return _monitor
