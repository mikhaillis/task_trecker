from fastapi import FastAPI
from app.api.tasks import router as tasks_rounter
from app.api.auth import router as auth_router

from app.db.database import engine, Base
from app.db import models

app = FastAPI(
     title="Task Tracker API",
    description="Пет-проект для стажировки Т-Банк",
    version="1.0.0" 
)

app.include_router(tasks_rounter)
app.include_router(auth_router)

@app.get("/")
def root():
    return {"message":"task-tracker успешно запущен"}