import httpx   # HTTP 요청 라이브러리 (Spring의 RestTemplate과 같은 역할)
import os
import time
import xml.etree.ElementTree as ET  # XML 파싱 내장 라이브러리
import asyncio
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

async def fetch_traffic_async(client, link_id):
    try:
        url = f"http://openapi.seoul.go.kr:8088/{API_KEY}/xml/TrafficInfo/1/1/{link_id}" # f-string: 변수를 문자열 안에 넣는 Python 방식
        response = await client.get(url, timeout=10.0) # GET 요청

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

async def collect_all_async():
    links = get_target_links()
    print(f"수집 시작: {len(links)}개 링크")

    start = time.time()
    count = 0

    db = SessionLocal()  # ★ 세션을 여기서 딱 한 번만 열어서 수집 내내 재사용

    try:
        async with httpx.AsyncClient() as client:
            # AsyncClient: 비동기 HTTP 클라이언트, 하나를 만들어서 여러 요청이 공유
            for i in range(0, len(links), 20):
                # 20개씩 묶어서 처리 (한번에 너무 많이 보내면 API 서버 부담)
                batch = links[i:i+20]
                results = await asyncio.gather(
                    # Asyncio.gather: 여러 비동기 함수를 동시에 실행하고 결과를 모음
                    # *[...]: 리스트를 개별 인자로 풀어서 전달
                    *[fetch_traffic_async(client, link_id) for link_id in batch]
                )
                for result in results:
                    if result:
                        save_traffic_speed(db, result)
                        count += 1
                db.commit()  # ★ 배치(20개)마다 한 번씩 커밋
    finally:
        db.close()  # ★ 전체 수집이 끝나면 딱 한 번만 닫음
    
    elapsed = time.time() - start
    print(f"수집 완료: {count}개 저장, 소요 시간: {elapsed:.1f}초")

    

def save_traffic_speed(db, data):  # data는 딕셔너리 (Python은 타입 명시 불필요)
    db.execute(text("""
        INSERT INTO traffic_speed (link_id, speed, travel_time, collected_at)
        VALUES (:link_id, :speed, :travel_time, NOW())
    """), data)
    # :link_id → data['link_id'] 값이 자동으로 바인딩됨
    # Spring MyBatis의 #{linkId}와 같은 개념
    # NOW()는 PostgreSQL 함수, 현재 시간 자동 입력

