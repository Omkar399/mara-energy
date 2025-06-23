import aiosqlite
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os

DATABASE_PATH = "sla_storage.db"

class SLADatabase:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
    
    async def initialize(self):
        """Initialize the database and create tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # Create SLAs table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS slas (
                    sla_id TEXT PRIMARY KEY,
                    tier TEXT NOT NULL,
                    compute_type TEXT NOT NULL,
                    compute_units INTEGER NOT NULL,
                    duration_hours INTEGER NOT NULL,
                    site_id TEXT NOT NULL,
                    site_name TEXT NOT NULL,
                    company_name TEXT,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    estimated_revenue REAL NOT NULL,
                    actual_revenue REAL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'active',
                    claude_optimized BOOLEAN DEFAULT 0,
                    preferred_region TEXT,
                    metadata TEXT DEFAULT '{}'
                )
            """)
            
            # Create SLA usage tracking table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sla_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sla_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    compute_units_used INTEGER NOT NULL,
                    power_consumed_mw REAL NOT NULL,
                    revenue_generated REAL NOT NULL,
                    efficiency_score REAL NOT NULL,
                    uptime_percentage REAL NOT NULL,
                    FOREIGN KEY (sla_id) REFERENCES slas (sla_id)
                )
            """)
            
            # Create SLA commitments summary table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sla_commitments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    tier TEXT NOT NULL,
                    total_power_mw REAL NOT NULL,
                    total_compute_units INTEGER NOT NULL,
                    active_slas_count INTEGER NOT NULL
                )
            """)
            
            # Create indexes for better performance
            await db.execute("CREATE INDEX IF NOT EXISTS idx_slas_status ON slas(status)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_slas_expires ON slas(expires_at)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_slas_site ON slas(site_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_usage_sla ON sla_usage(sla_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON sla_usage(timestamp)")
            
            await db.commit()
            
            # Run migrations
            await self._run_migrations()
    
    async def _run_migrations(self):
        """Run database migrations"""
        async with aiosqlite.connect(self.db_path) as db:
            # Check if company_name column exists, if not add it
            try:
                cursor = await db.execute("PRAGMA table_info(slas)")
                columns = await cursor.fetchall()
                column_names = [col[1] for col in columns]
                
                if 'company_name' not in column_names:
                    await db.execute("ALTER TABLE slas ADD COLUMN company_name TEXT")
                    await db.commit()
                    print("✅ Added company_name column to slas table")
            except Exception as e:
                print(f"⚠️ Migration error: {e}")
    
    async def create_sla(self, sla_data: Dict) -> bool:
        """Create a new SLA record"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO slas (
                        sla_id, tier, compute_type, compute_units, duration_hours,
                        site_id, site_name, company_name, created_at, expires_at, estimated_revenue,
                        status, claude_optimized, preferred_region, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    sla_data['sla_id'],
                    sla_data['tier'],
                    sla_data['compute_type'],
                    sla_data['compute_units'],
                    sla_data['duration_hours'],
                    sla_data['site_id'],
                    sla_data.get('site_name', ''),
                    sla_data.get('company_name', ''),
                    sla_data['created_at'],
                    sla_data['expires_at'],
                    sla_data['estimated_revenue'],
                    sla_data.get('status', 'active'),
                    sla_data.get('claude_optimized', False),
                    sla_data.get('preferred_region', ''),
                    json.dumps(sla_data.get('metadata', {}))
                ))
                await db.commit()
                return True
        except Exception as e:
            print(f"Error creating SLA: {e}")
            return False
    
    async def get_active_slas(self) -> List[Dict]:
        """Get all active SLAs"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("""
                    SELECT * FROM slas 
                    WHERE status = 'active' AND datetime(expires_at) > datetime('now')
                    ORDER BY created_at DESC
                """) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting active SLAs: {e}")
            return []
    
    async def get_slas_by_site(self, site_id: str) -> List[Dict]:
        """Get all active SLAs for a specific site"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("""
                    SELECT * FROM slas 
                    WHERE site_id = ? AND status = 'active' AND datetime(expires_at) > datetime('now')
                    ORDER BY created_at DESC
                """, (site_id,)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting SLAs for site {site_id}: {e}")
            return []
    
    async def update_sla_status(self, sla_id: str, status: str) -> bool:
        """Update SLA status"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE slas SET status = ? WHERE sla_id = ?
                """, (status, sla_id))
                await db.commit()
                return True
        except Exception as e:
            print(f"Error updating SLA status: {e}")
            return False
    
    async def record_sla_usage(self, usage_data: Dict) -> bool:
        """Record SLA usage metrics"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO sla_usage (
                        sla_id, timestamp, compute_units_used, power_consumed_mw,
                        revenue_generated, efficiency_score, uptime_percentage
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    usage_data['sla_id'],
                    usage_data.get('timestamp', datetime.now().isoformat()),
                    usage_data['compute_units_used'],
                    usage_data['power_consumed_mw'],
                    usage_data['revenue_generated'],
                    usage_data['efficiency_score'],
                    usage_data['uptime_percentage']
                ))
                await db.commit()
                return True
        except Exception as e:
            print(f"Error recording SLA usage: {e}")
            return False
    
    async def get_sla_usage_history(self, sla_id: str, hours: int = 24) -> List[Dict]:
        """Get SLA usage history for the last N hours"""
        try:
            cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("""
                    SELECT * FROM sla_usage 
                    WHERE sla_id = ? AND timestamp > ?
                    ORDER BY timestamp DESC
                """, (sla_id, cutoff_time)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting SLA usage history: {e}")
            return []
    
    async def cleanup_expired_slas(self) -> int:
        """Mark expired SLAs as expired and return count"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Update expired SLAs
                await db.execute("""
                    UPDATE slas 
                    SET status = 'expired' 
                    WHERE status = 'active' AND datetime(expires_at) <= datetime('now')
                """)
                
                # Get count of updated rows
                cursor = await db.execute("SELECT changes()")
                count = (await cursor.fetchone())[0]
                await db.commit()
                return count
        except Exception as e:
            print(f"Error cleaning up expired SLAs: {e}")
            return 0
    
    async def get_sla_statistics(self) -> Dict:
        """Get comprehensive SLA statistics"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                # Active SLAs by tier
                async with db.execute("""
                    SELECT tier, COUNT(*) as count, SUM(compute_units) as total_units,
                           SUM(estimated_revenue) as total_revenue
                    FROM slas 
                    WHERE status = 'active' AND datetime(expires_at) > datetime('now')
                    GROUP BY tier
                """) as cursor:
                    tier_stats = {row['tier']: dict(row) for row in await cursor.fetchall()}
                
                # Active SLAs by compute type
                async with db.execute("""
                    SELECT compute_type, COUNT(*) as count, SUM(compute_units) as total_units
                    FROM slas 
                    WHERE status = 'active' AND datetime(expires_at) > datetime('now')
                    GROUP BY compute_type
                """) as cursor:
                    compute_stats = {row['compute_type']: dict(row) for row in await cursor.fetchall()}
                
                # Site distribution
                async with db.execute("""
                    SELECT site_id, site_name, COUNT(*) as active_slas, 
                           SUM(compute_units) as total_units
                    FROM slas 
                    WHERE status = 'active' AND datetime(expires_at) > datetime('now')
                    GROUP BY site_id, site_name
                """) as cursor:
                    site_stats = [dict(row) for row in await cursor.fetchall()]
                
                # Total statistics
                async with db.execute("""
                    SELECT COUNT(*) as total_active,
                           SUM(compute_units) as total_compute_units,
                           SUM(estimated_revenue) as total_estimated_revenue,
                           AVG(estimated_revenue) as avg_revenue_per_sla
                    FROM slas 
                    WHERE status = 'active' AND datetime(expires_at) > datetime('now')
                """) as cursor:
                    total_stats = dict(await cursor.fetchone())
                
                return {
                    'tier_breakdown': tier_stats,
                    'compute_breakdown': compute_stats,
                    'site_distribution': site_stats,
                    'totals': total_stats,
                    'last_updated': datetime.now().isoformat()
                }
        except Exception as e:
            print(f"Error getting SLA statistics: {e}")
            return {}
    
    async def update_sla_commitments(self, commitments: Dict) -> bool:
        """Update SLA commitments summary"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                timestamp = datetime.now().isoformat()
                
                for tier, power_mw in commitments.items():
                    # Count active SLAs for this tier
                    async with db.execute("""
                        SELECT COUNT(*) as count, SUM(compute_units) as units
                        FROM slas 
                        WHERE tier = ? AND status = 'active' AND datetime(expires_at) > datetime('now')
                    """, (tier,)) as cursor:
                        result = await cursor.fetchone()
                        count = result[0] if result[0] else 0
                        units = result[1] if result[1] else 0
                    
                    await db.execute("""
                        INSERT INTO sla_commitments (
                            timestamp, tier, total_power_mw, total_compute_units, active_slas_count
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (timestamp, tier, power_mw, units, count))
                
                await db.commit()
                return True
        except Exception as e:
            print(f"Error updating SLA commitments: {e}")
            return False
    
    async def get_database_info(self) -> Dict:
        """Get database information and statistics"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                info = {
                    'database_path': self.db_path,
                    'database_size': os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0,
                    'tables': {}
                }
                
                # Get table counts
                for table in ['slas', 'sla_usage', 'sla_commitments']:
                    async with db.execute(f"SELECT COUNT(*) FROM {table}") as cursor:
                        count = (await cursor.fetchone())[0]
                        info['tables'][table] = count
                
                return info
        except Exception as e:
            print(f"Error getting database info: {e}")
            return {'error': str(e)}

# Global database instance
sla_db = SLADatabase() 