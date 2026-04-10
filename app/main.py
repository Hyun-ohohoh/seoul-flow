from fastapi import FastAPI
from app.database import engine, Base
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.scheduler.collector import collect_all_async
from app.routers.traffic import router as traffic_router

scheduler = AsyncIOScheduler()   # 비동기 스케줄러 생성

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시 실행 (Spring의 @PostConstruct와 비슷)
    scheduler.add_job(collect_all_async, 'interval', minutes=10)
    scheduler.start()
    print("스케줄러 시작!")
    yield  # 서버 실행 중 (여기서 대기)

    # 서버 종료 시 실행
    scheduler.shutdown()
    print("스케줄러 종료!")

Base.metadata.create_all(bind=engine)
# Base를 상속받은 모든 모델 클래스를 보고 테이블이 없으면 자동 생성
# Spring의 spring.jpa.hibernate.ddl-auto: create와 같은 역할

app = FastAPI(lifespan=lifespan) # lifespan 등록
app.include_router(traffic_router)

@app.get("/")  # Spring의 @GetMapping("/")과 같음
def root():
    return {"message": "Seoul Traffic API"}
