from fastapi import APIRouter
from app.database import SessionLocal
from sqlalchemy import text

router = APIRouter() # Spring의 @RestController와 같은 역할

@router.get("/traffic/worst")
def get_worst_traffic():
    db = SessionLocal() # DB 세션 열기
    result = db.execute(text("""
        SELECT DISTINCT ts.link_id, ts.speed, ts.travel_time, rl.road_name
        FROM (
            SELECT DISTINCT ON (link_id) link_id, speed, travel_time
            FROM traffic_speed
            WHERE collected_at >= NOW() - INTERVAL '15 minutes'
            ORDER BY link_id, collected_at DESC
        ) AS ts
        LEFT JOIN service_link sl ON ts.link_id::BIGINT = sl.service_link_id
        LEFT JOIN road_link rl ON sl.std_link_id::VARCHAR = rl.link_id
        ORDER BY ts.speed ASC
        LIMIT 5
    """))

    # 결과를 딕셔너리 리스트로 변환
    # Spring의 List<Map<String, Object>>와 같은 형태
    rows = [{"link_id": row[0], "speed": row[1], "travel_time": row[2], "road_name": row[3]} for row in result]
    db.close()
    return rows
    