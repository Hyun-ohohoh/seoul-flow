import httpx   # HTTP 요청 라이브러리 (Spring의 RestTemplate과 같은 역할)
import os
import time
import xml.etree.ElementTree as ET  # XML 파싱 내장 라이브러리
from dotenv import load_dotenv
from app.database import SessionLocal
from sqlalchemy import text  # SQL 쿼리 문자열을 SQLAlchemy가 인식하게 감싸는 것

load_dotenv()
API_KEY = os.getenv("SEOUL_API_KEY")

def get_target_links():
    db = SessionLocal()  # DB 세션 열기 (Spring의 EntityManager와 비슷)
    result = db.execute(text("""
        SELECT DISTINCT service_link_id FROM service_link
    """))                # DISTINCT로 중복 제거한 서비스링크 ID 조회
    link_ids = [row[0] for row in result]
    # [row[0] for row in result] 는 Java의 stream().map().collect()와 같은 의미
    db.close()
    return link_ids   # 5,065개 링크 ID 리스트 반환

def fetch_traffic(link_id):
    try:
        url = f"http://openapi.seoul.go.kr:8088/{API_KEY}/xml/TrafficInfo/1/1/{link_id}" # f-string: 변수를 문자열 안에 넣는 Python 방식
        response = httpx.get(url, timeout=10.0) # GET 요청

        root = ET.fromstring(response.text) # XML 문자열을 파싱해서 트리 구조로 변환
        row = root.find('row') # <row> 태그 찾기
        if row is None:      # 데이터 없으면 None 반환
            return None

        return {         # 딕셔너리로 반환 (Java의 Map과 같은 자료구조)
        'link_id': row.find('link_id').text,  # .text로 태그 안의 값 추출
        'speed': row.find('prcs_spd').text,
        'travel_time': row.find('prcs_trv_time').text
        }
    except Exception as e:
        print(f"에러 {link_id}: {e}")
        return None
    


def save_traffic_speed(data):  # data는 딕셔너리 (Python은 타입 명시 불필요)
    db = SessionLocal()
    db.execute(text("""
        INSERT INTO traffic_speed (link_id, speed, travel_time, collected_at)
        VALUES (:link_id, :speed, :travel_time, NOW())
    """), data)
    # :link_id → data['link_id'] 값이 자동으로 바인딩됨
    # Spring MyBatis의 #{linkId}와 같은 개념
    # NOW()는 PostgreSQL 함수, 현재 시간 자동 입력

    db.commit() # 트랜잭션 커밋 (없으면 저장 안 됨)
    db.close()


import time

links = get_target_links()
print(f"수집 시작: {len(links)}개 링크")

start = time.time()
count = 0

for link_id in links:
    result = fetch_traffic(link_id)
    if result:
        save_traffic_speed(result)
        count += 1

elapsed = time.time() - start
print(f"수집 완료: {count}개 저장, 소요 시간: {elapsed:.1f}초")