import asyncio
from uuid import uuid4
from app.db.unit_of_work import UnitOfWorkFactory
from app.chat.pipeline.orchestrator import ChatPipelineService
from app.chat.providers.groq_provider import GroqLLMProvider
from app.embeddings.providers.sentence_transformer_provider import SentenceTransformerEmbeddingProvider
from app.vectorstore.providers.faiss_provider import FAISSVectorProvider
from app.chat.classification.rule_based_classifier import RuleBasedClassifier

async def test():
    uow_factory = UnitOfWorkFactory.create
    
    # 1. Create a dummy session in DB with document_ids
    uow1 = uow_factory()
    async with uow1:
        from sqlalchemy import text
        res = await uow1._session.execute(text("SELECT id FROM users LIMIT 1;"))
        user_id = res.scalar()
        if not user_id:
            print("No user found")
            return

    session_id = uuid4()
    doc_id = uuid4()

    # Create session with document_ids stored in DB
    from app.models.chat_session import ChatSession
    from app.models.chat_message import ChatMessage
    from app.models.enums import ChatRole

    uow2 = uow_factory()
    async with uow2:
        sess = ChatSession(
            id=session_id,
            user_id=user_id,
            title="First Session",
            document_ids=[str(doc_id)] # Stored as list of str in JSON column
        )
        await uow2.chat_session_repository.create(sess)
        
        msg1 = ChatMessage(session_id=session_id, role=ChatRole.USER, content="First question")
        msg2 = ChatMessage(session_id=session_id, role=ChatRole.ASSISTANT, content="First answer")
        await uow2.chat_message_repository.create(msg1)
        await uow2.chat_message_repository.create(msg2)
        await uow2.commit()

    print(f"Created session {session_id} with document_ids = {[str(doc_id)]}")

    # Now instantiate ChatPipelineService and execute pipeline with session_id
    llm = GroqLLMProvider()
    embed = SentenceTransformerEmbeddingProvider()
    vec = FAISSVectorProvider()
    await vec.create_index(384)
    classifier = RuleBasedClassifier()

    pipeline = ChatPipelineService(
        uow_factory=uow_factory,
        llm_provider=llm,
        vector_index_service=vec,
        embedding_service=embed,
        intent_classifier=classifier
    )

    print("Running second request on existing session...")
    # Monkeypatch format_error to print exact exception
    orig_format_error = pipeline._format_error
    def debug_format_error(msg, log_dict):
        print("PIPELINE ERROR LOG DICT:", log_dict)
        return orig_format_error(msg, log_dict)
    pipeline._format_error = debug_format_error

    try:
        res = await pipeline.execute_pipeline(
            question="Second question",
            session_id=session_id,
            user_id=user_id,
            document_ids=None # Frontend sends null or [] on second request!
        )
        print("RESULT OF SECOND REQUEST:", res)
    except Exception as e:
        import traceback
        print("SECOND REQUEST EXCEPTION:")
        traceback.print_exc()

    # Cleanup
    uow3 = uow_factory()
    async with uow3:
        await uow3.chat_session_repository.delete(session_id)
        await uow3.commit()
        print("Cleaned up session.")

if __name__ == "__main__":
    asyncio.run(test())
