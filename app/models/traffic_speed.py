from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
# Column: 테이블 컬럼 정의
# Integer, String, DateTime: 컬럼 타입 (Java의 int, String, LocalDateTime과 같음)
# ForeignKey: 외래키 설정
from app.database import Base
# Base: database.py에서 만든 declarative_base()
# 이걸 상속받아야 SQLAlchemy가 "이 클래스가 DB 테이블이다"라고 인식
# Spring의 @Entity와 같은 역할

class TrafficSpeed(Base):   # Base 상속 → DB 테이블로 인식
    __tablename__ = "traffic_speed" # 실제 DB 테이블 이름 지정, Spring의 @Table(name = "traffic_speed")와 같음

    id = Column(Integer, primary_key=True, autoincrement=True)
    # primary_key=True → PK 설정. Spring의 @Id와 같음
    # autoincrement=True → 자동 증가. Spring의 @GeneratedValue와 같음

    link_id = Column(String(20), ForeignKey("road_link.link_id"))
    # ForeignKey("테이블명.컬럼명") → FK 설정
    # Spring의 @ManyToOne + @JoinColumn과 같은 역할

    speed = Column(Integer)  # 속도 (km/h)
    travel_time = Column(Integer)  # 통행시간 (초)
    collected_at = Column(DateTime, nullable=False)