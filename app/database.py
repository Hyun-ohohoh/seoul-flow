from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

load_dotenv()

DATABSE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABSE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()