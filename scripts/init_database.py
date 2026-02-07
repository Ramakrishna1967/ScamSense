import asyncio
import asyncpg
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/scamshield")

TABLES = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        phone VARCHAR(50),
        password_hash VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT NOW(),
        subscription_tier VARCHAR(50) DEFAULT 'free'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS user_settings (
        user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        alert_methods JSONB DEFAULT '{"push": true, "email": false}',
        aggressive_blocking BOOLEAN DEFAULT false,
        family_alerts_enabled BOOLEAN DEFAULT true,
        auto_report_to_authorities BOOLEAN DEFAULT false,
        updated_at TIMESTAMP DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS trusted_contacts (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        name VARCHAR(100) NOT NULL,
        email VARCHAR(255),
        phone VARCHAR(50),
        relationship VARCHAR(50),
        notify_on_scam BOOLEAN DEFAULT true,
        created_at TIMESTAMP DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS user_blocklist (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        blocked_identifier VARCHAR(255) NOT NULL,
        identifier_type VARCHAR(50) DEFAULT 'phone',
        reason TEXT,
        blocked_at TIMESTAMP DEFAULT NOW(),
        auto_blocked BOOLEAN DEFAULT false,
        UNIQUE(user_id, blocked_identifier)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_blocklist_user ON user_blocklist(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_blocklist_identifier ON user_blocklist(blocked_identifier)",
    "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)"
]


async def init_database():
    print("Connecting to PostgreSQL...")
    print(f"URL: {DATABASE_URL[:50]}...")
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        print("Connected successfully!")
        
        for table_sql in TABLES:
            await conn.execute(table_sql)
        print("Database initialized successfully")
        await conn.close()
    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(init_database())
