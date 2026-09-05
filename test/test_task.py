import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from main import app
from app.db import models
from app.api.tasks import get_db
import pytest_asyncio

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

async def override_get_db():
    async with TestingSessionLocal() as db:
        yield db

app.dependency_overrides[get_db] = override_get_db

@pytest_asyncio.fixture(autouse=True)
async def prepare_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_create_task():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/tasks/", json={
            "title": "тест", 
            "description": "тест"
        })

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "тест"
        assert data["description"] == "тест"
        assert "id" in data

@pytest.mark.asyncio
async def test_patch_task():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/tasks/", json={
            "title": "тест", 
            "description": "тест"
        })

        assert response.status_code == 201

        data = response.json()
        index = data["id"]

        patch = await ac.patch(f"/tasks/{index}/complete")

        assert patch.status_code == 200
        assert patch.json()["is_completed"] == True

@pytest.mark.asyncio
async def test_get_tasks():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        completed_task = await ac.post("/tasks/", json={
            "title": "тест1", 
            "description": "тест1"
        })
        assert completed_task.status_code == 201

        index_of_completed = completed_task.json()["id"]

        patch = await ac.patch(f"/tasks/{index_of_completed}/complete")
        assert patch.status_code == 200

        uncompleted_task = await ac.post("/tasks/", json={
            "title": "тест2", 
            "description": "тест2"
        })
        assert uncompleted_task.status_code == 201


        get_completed = await ac.get("/tasks/?is_complete=true")
        assert get_completed.status_code == 200
        assert isinstance(get_completed.json(), list)
        assert len(get_completed.json()) == 1

        info_completed = get_completed.json()[0]

        assert info_completed["title"] == "тест1"
        assert info_completed["description"] == "тест1"
        assert info_completed["is_completed"] == True


        get_uncompleted = await ac.get("/tasks/?is_complete=false")
        assert get_uncompleted.status_code == 200
        assert isinstance(get_uncompleted.json(), list)
        assert len(get_uncompleted.json()) == 1

        info_uncompleted = get_uncompleted.json()[0]

        assert info_uncompleted["title"] == "тест2"
        assert info_uncompleted["description"] == "тест2"
        assert info_uncompleted["is_completed"] == False


        get_all = await ac.get("/tasks/")
        assert get_all.status_code == 200
        assert isinstance(get_all.json(), list)
        assert len(get_all.json()) == 2



@pytest.mark.asyncio
async def test_delete_task():
        async with AsyncClient(app=app, base_url="http://test") as ac:
            to_delete = await ac.post("/tasks/", json={
            "title": "тест", 
            "description": "тест"
            })

            index = to_delete.json()["id"]
            
            response = await ac.delete(f"/tasks/{index}")

            assert response.status_code == 200

            data = response.json()
            assert data["detail"] == "успешно удалено"

            response = await ac.delete(f"/tasks/{index}")

            assert response.status_code == 404
            data = response.json()
            assert data["detail"] == "Задача не найдена"