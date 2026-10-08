import asyncio
import app.core.sqlite_compat
from app.core.database import get_async_session
from app.repositories.base import BaseRepository
from app.guardrails import GuardrailFinding, Guardrail

async def test():
    try:
        async with get_async_session() as session:
            g_repo = BaseRepository(Guardrail, session)
            print("Guardrails:", await g_repo.list())
            f_repo = BaseRepository(GuardrailFinding, session)
            print("Findings:", await f_repo.list())
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(test())
