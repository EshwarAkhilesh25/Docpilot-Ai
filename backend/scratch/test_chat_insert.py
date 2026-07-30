import asyncio
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from app.models.chat_session import ChatSession
from app.models.chat_message import ChatMessage
from app.models.enums import ChatRole

url = 'postgresql+asyncpg://postgres.lhbdzgtyajcpqhwlglsa:MySecurePassword123%21@aws-1-ap-northeast-2.pooler.supabase.com:5432/postgres'

async def test_insert():
    engine = create_async_engine(url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Create a test session
        user_id_res = await session.execute(text("SELECT id FROM users LIMIT 1;"))
        user_id = user_id_res.scalar()
        if not user_id:
            print("No user found in DB")
            return

        chat_session = ChatSession(
            user_id=user_id,
            title="Test Chat Session"
        )
        session.add(chat_session)
        await session.flush()

        # Insert user message and assistant message
        msg1 = ChatMessage(
            session_id=chat_session.id,
            role=ChatRole.USER,
            content="Hello test prompt"
        )
        msg2 = ChatMessage(
            session_id=chat_session.id,
            role=ChatRole.ASSISTANT,
            content="Hello response"
        )
        session.add_all([msg1, msg2])
        await session.commit()
        print(f"Successfully inserted ChatMessages with IDs: {msg1.id}, {msg2.id}")

        # Clean up test session
        await session.delete(chat_session)
        await session.commit()
        print("Cleaned up test session.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_insert())
