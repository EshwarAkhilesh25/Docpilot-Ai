import asyncio
from app.db.unit_of_work import UnitOfWorkFactory

async def test():
    uow = UnitOfWorkFactory.create()
    print("Entering first async with uow...")
    async with uow:
        res = await uow.user_repository.get_by_id("00000000-0000-0000-0000-000000000000")
        print("First query done.")

    print("Entering second async with uow...")
    try:
        async with uow:
            res2 = await uow.user_repository.get_by_id("00000000-0000-0000-0000-000000000000")
            print("Second query done.")
    except Exception as e:
        print("SECOND QUERY FAILED WITH ERROR:", type(e), e)

if __name__ == "__main__":
    asyncio.run(test())
