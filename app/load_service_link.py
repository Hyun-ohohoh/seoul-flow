import pandas as pd
from sqlalchemy import create_engine # DB 연결 엔진 생성
from dotenv import load_dotenv
import os


load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))  # DB 연결 엔진 생성
# Spring의 application.yml DataSource 설정과 같은 역할
# SessionLocal과 차이: engine은 pandas 전용, SessionLocal은 쿼리 실행용

df = pd.read_excel('/Users/hyun-oh/SideProject/서울특별시 교통소통 표준링크 매핑정보_20250306.xlsx')

df = df.rename(columns={
    '서비스링크': 'service_link_id',
    '표준링크순서': 'seq',
    '표준링크아이디': 'std_link_id'
})

df = df.drop_duplicates(subset=['service_link_id', 'seq'])
# 엑셀에 중복 행이 있어서 PK 위반 에러 발생 → 중복 제거
# subset: 이 컬럼 기준으로 중복 판별

df = df.dropna(subset=['seq'])
# seq 컬럼에 null 값이 있어서 NOT NULL 위반 에러 발생 → null 행 제거

df.to_sql('service_link', engine, if_exists='append', index=False)
# to_sql: DataFrame을 DB 테이블에 저장하는 pandas 메서드
# if_exists='append': 테이블이 있으면 이어서 추가 (replace면 덮어쓰기)
# index=False: DataFrame의 자동 인덱스(0,1,2...)는 저장하지 않음

print(f"적재 완료: {len(df)}행")

