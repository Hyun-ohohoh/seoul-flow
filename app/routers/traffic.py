from fastapi import APIRouter
from app.database import SessionLocal
from sqlalchemy import text

import json
from app.redis_client import redis_client

router = APIRouter() # Spring의 @RestController와 같은 역할

@router.get("/traffic/worst")
def get_worst_traffic():
    # 1. Redis에서 캐시 확인
    cached = redis_client.get("traffic:worst")
    if cached:
        return json.loads(cached)

    # 2. 캐시 없으면 DB 쿼리
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

    # 3. Redis에 10분간 캐싱
    redis_client.setex("traffic:worst", 600, json.dumps(rows, default=str))

    return rows
    
@router.get("/traffic/road")
def get_road_taffic(name: str):

    # 1. Redis에서 캐시 확인
    cache_key = f"traffic:road:{name}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # 2. 캐시 없으면 DB 쿼리
    db = SessionLocal()
    result = db.execute(text("""
        SELECT ts.link_id, ts.speed, ts.travel_time, rl.road_name,
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
        WHERE rl.road_name LIKE '%' || :name || '%'
        ORDER BY ts.speed ASC
        LIMIT 10
    """), {"name": name})
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

    # 3. Redis에 저장(10분)
    redis_client.setex(cache_key, 600, json.dumps(rows, default=str))
    return rows


@router.get("/traffic/pattern")
def get_traffic_pattern(name: str) :

    # 1. Redis에서 캐시 확인
    cache_key = f"traffic:pattern:{name}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # 2. 캐시 없으면 DB 쿼리
    db = SessionLocal()
    result = db.execute(text("""
        SELECT
            EXTRACT(HOUR FROM ts.collected_at) as hour,
            AVG(ts.speed) as avg_speed,
            AVG(ts.travel_time) as avg_travel_time
        FROM traffic_speed ts
        LEFT JOIN service_link sl ON ts.link_id::BIGINT = sl.service_link_id
        LEFT JOIN road_link rl ON sl.std_link_id::VARCHAR = rl.link_id
        WHERE rl.road_name LIKE '%' || :name || '%'
        AND DATE(ts.collected_at) = CURRENT_DATE
        GROUP BY hour
        ORDER BY hour
    """), {"name": name})
    rows = [{
        "hour": row[0],
        "avg_speed": round(row[1], 1),
        "avg_travel_time": round(row[2], 1)
        } for row in result]
    db.close()
    
    # 3. Redis에 저장(10분)
    redis_client.setex(cache_key, 600, json.dumps(rows, default=str))
    return rows