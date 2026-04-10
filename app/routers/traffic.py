from fastapi import APIRouter
from app.database import SessionLocal
from sqlalchemy import text

router = APIRouter() # Spring의 @RestController와 같은 역할

@router.get("/traffic/worst")
def get_worst_traffic():
    db = SessionLocal() # DB 세션 열기
    result = db.execute(text("""
        SELECT DISTINCT ts.link_id, ts.speed, ts.travel_time, rl.road_name,
            ST_Y(ST_StartPoint(rl.geom)) as start_lat,
            ST_X(ST_StartPoint(rl.geom)) as start_lng,
            ST_Y(ST_EndPoint(rl.geom)) as end_lat,
            ST_X(ST_EndPoint(rl.geom)) as end_lng
        FROM (
            SELECT DISTINCT ON (link_id) link_id, speed, travel_time
            FROM traffic_speed
            WHERE collected_at >= NOW() - INTERVAL '15 minutes'
            ORDER BY link_id, collected_at DESC
        ) AS ts
        LEFT JOIN service_link sl ON ts.link_id::BIGINT = sl.service_link_id
        LEFT JOIN road_link rl ON sl.std_link_id::VARCHAR = rl.link_id
        WHERE rl.road_name IS NOT NULL
        ORDER BY ts.speed ASC
        LIMIT 10
    """))

    # 결과를 딕셔너리 리스트로 변환
    # Spring의 List<Map<String, Object>>와 같은 형태
    rows = [{
        "link_id": row[0], 
        "speed": row[1], 
        "travel_time": row[2], 
        "road_name": row[3],
        "start_lat": row[4],
        "start_lng": row[5],
        "end_lat": row[6],
        "end_lng": row[7]
        } for row in result]
    db.close()
    return rows
    