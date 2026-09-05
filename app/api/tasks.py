from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import SessionLocal
from app.db.database import get_db
from app.db import models
from app.api.auth import get_current_user

router = APIRouter(prefix="/tasks", tags=["Tasks"])

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

@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(
    task: TaskCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user) 
):
    db_task = models.Task(
        title=task.title, 
        description=task.description,
        user_id=current_user.id 
    )
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return map_task_to_response(db_task)

@router.get("/", response_model=list[TaskResponse])
async def get_all_tasks(
    is_complete: bool | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Базовый фильтр: берем только задачи текущего пользователя
    to_do = select(models.Task).filter(models.Task.user_id == current_user.id)
    
    if is_complete is not None:
        # Добавляем фильтр по статусу, если он передан
        to_do = to_do.filter(models.Task.is_completed == is_complete)
        
    ans = await db.execute(to_do)
    return [map_task_to_response(x) for x in ans.scalars().all()]

@router.patch("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Комбинированный поиск: совпадает и ID задачи, и ID владельца
    stmt = select(models.Task).filter(
        models.Task.id == task_id,
        models.Task.user_id == current_user.id
    )
    
    result = await db.execute(stmt)
    db_task = result.scalar_one_or_none()

    if db_task is None:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    db_task.is_completed = True

    await db.commit()
    await db.refresh(db_task)
    return map_task_to_response(db_task)

@router.delete("/{task_id}")
async def delete_task(
    task_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Комбинированный поиск для безопасного удаления
    stmt = select(models.Task).filter(
        models.Task.id == task_id,
        models.Task.user_id == current_user.id
    )
    
    result = await db.execute(stmt)
    to_delete = result.scalar_one_or_none()

    if not to_delete:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    await db.delete(to_delete)
    await db.commit()

    return {"detail": "успешно удалено"}