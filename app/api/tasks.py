from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import SessionLocal
from app.db import models
from sqlalchemy import select

router = APIRouter(prefix="/tasks", tags=["Tasks"])

# ИСПРАВЛЕНО: Опечатка в названии (TaskResponse вместо TaskReaponse)
class TaskResponse(BaseModel):
    id: int
    title: str
    description: str | None
    is_completed: bool

    model_config = {"from_attributes": True}

class TaskCreate(BaseModel):
    title: str
    description: str | None = None

def map_task_to_response(task: models.Task) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        is_completed=task.is_completed
    )

async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()

@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(task: TaskCreate, db: AsyncSession = Depends(get_db)):
    db_task = models.Task(title=task.title, description=task.description)
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return map_task_to_response(db_task)

@router.get("/", response_model=list[TaskResponse])
async def get_all_tasks(db: AsyncSession = Depends(get_db), is_complete: bool | None = None):
    if is_complete is not None:
        to_do = select(models.Task).filter(models.Task.is_completed == is_complete)
    else:
        to_do = select(models.Task)
        
    ans = await db.execute(to_do)
    return [map_task_to_response(x) for x in ans.scalars().all()]

@router.patch("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(models.Task).filter(models.Task.id == task_id)
    
    result = await db.execute(stmt)
    db_task = result.scalar_one_or_none()

    if db_task is None:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    db_task.is_completed = True

    await db.commit()
    await db.refresh(db_task)
    return map_task_to_response(db_task)

@router.delete("/{task_id}")
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(models.Task).filter(models.Task.id == task_id)
    
    result = await db.execute(stmt)
    to_delete = result.scalar_one_or_none()

    if not to_delete:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    await db.delete(to_delete)
    await db.commit()

    return {"detail": "успешно удалено"}