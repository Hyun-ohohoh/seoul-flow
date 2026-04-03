from fastapi import FastAPI
from app.database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Seoul Traffic API"}
