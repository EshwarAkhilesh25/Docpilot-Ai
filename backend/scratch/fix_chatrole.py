import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

url = 'postgresql+asyncpg://postgres.lhbdzgtyajcpqhwlglsa:MySecurePassword123%21@aws-1-ap-northeast-2.pooler.supabase.com:5432/postgres'

async def fix():
    engine = create_async_engine(url, isolation_level='AUTOCOMMIT')
    async with engine.connect() as conn:
        try:
            await conn.execute(text("ALTER TYPE chatrole ADD VALUE IF NOT EXISTS 'user';"))
            print("Added 'user' to chatrole enum")
        except Exception as e:
            print("user error:", e)

        try:
            await conn.execute(text("ALTER TYPE chatrole ADD VALUE IF NOT EXISTS 'assistant';"))
            print("Added 'assistant' to chatrole enum")
        except Exception as e:
            print("assistant error:", e)

        res = (await conn.execute(text("""
            SELECT enumlabel
            FROM pg_enum
            JOIN pg_type ON pg_enum.enumtypid = pg_type.oid
            WHERE typname = 'chatrole'
            ORDER BY enumsortorder;
        """))).fetchall()
        print("Updated Supabase chatrole enum labels:", [r[0] for r in res])
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(fix())
