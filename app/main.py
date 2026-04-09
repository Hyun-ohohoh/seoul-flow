from fastapi import FastAPI
from app.database import engine, Base
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.scheduler.collector import collect_all_async

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(collect_all_async, 'interval', minutes=15)
    scheduler.start()
    print("스케줄러 시작!")
    yield

    scheduler.shutdown()
    print("스케줄러 종료!")

Base.metadata.create_all(bind=engine)

app = FastAPI(lifespan=lifespan)

@app.get("/")
def root():
    return {"message": "Seoul Traffic API"}
