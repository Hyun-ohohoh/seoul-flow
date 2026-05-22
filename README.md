# 🚦 Seoul Flow

서울시 실시간 교통 데이터를 수집·저장·분석하고, MCP(Model Context Protocol)를 통해 AI 에이전트에 교통 정보를 제공하는 백엔드 시스템입니다.

---

## 🎯 프로젝트 배경

네이버지도·카카오맵은 지금 막히는 구간을 시각적으로 보여주지만, **"왜 막히는지", "언제 풀리는지"를 자연어로 질문할 수는 없습니다.**

Seoul Flow는 실시간 교통 데이터를 시계열로 수집·저장하고, MCP를 통해 Claude 같은 AI가 자연어로 교통 데이터를 조회할 수 있도록 합니다.

> "지금 올림픽대로 어때?" → Claude가 실제 DB 데이터 기반으로 답변

---

## 🏗️ Architecture

```
Seoul Open API (XML)
        ↓ (10분마다 비동기 수집 - asyncio.gather)
  FastAPI + APScheduler
        ↓
  PostgreSQL + PostGIS          Redis
  (15,924개 도로 링크)    ←→   (API 응답 10분 캐싱)
        ↓
  FastAPI REST Endpoints
        ↓
  MCP Server (stdio)
        ↓
  Claude / AI Agent
```

---

## ⚙️ Tech Stack

| 분류 | 기술 |
|------|------|
| API 서버 | FastAPI |
| ORM | SQLAlchemy |
| DB | PostgreSQL + PostGIS |
| 비동기 HTTP | httpx (asyncio) |
| 스케줄러 | APScheduler |
| 캐싱 | Redis |
| AI 연동 | MCP (fastmcp) |
| 환경변수 | python-dotenv |

---

## 📁 Project Structure

```
seoul-flow/
├── app/
│   ├── models/
│   │   └── traffic_speed.py      # SQLAlchemy 모델
│   ├── routers/
│   │   └── traffic.py            # FastAPI 엔드포인트 (Redis 캐싱 포함)
│   ├── scheduler/
│   │   └── collector.py          # 비동기 데이터 수집 파이프라인
│   ├── load_service_link.py      # 서비스링크 매핑 데이터 적재
│   ├── database.py               # DB 연결 설정
│   ├── redis_client.py           # Redis 연결 설정
│   ├── main.py                   # FastAPI 앱 진입점 + 스케줄러
│   └── mcp_server.py             # MCP 서버
├── requirements.txt
└── .env
```

---

## 🗄️ Data Model

```
road_link (PostGIS)          service_link              traffic_speed
─────────────────            ─────────────             ─────────────────────
link_id (PK)      ←──────── std_link_id               id (PK, autoincrement)
road_name                    service_link_id ←───────── link_id
road_rank                    seq                        speed (km/h)
geom (LineString)                                       travel_time (초)
                                                        collected_at (DateTime)
```

- **road_link**: 서울시 표준 도로 링크 15,924개 (PostGIS geometry 포함)
- **service_link**: 서울 Open API 서비스링크 ↔ 표준링크 매핑 테이블
- **traffic_speed**: 10분 주기로 수집된 실시간 속도 데이터

---

## 🔑 핵심 기능 구현

### 1. 비동기 수집 파이프라인 (collector.py)

서울 Open API는 링크 ID 1개당 요청 1회가 필요합니다. 5,065개 링크를 동기로 순차 호출하면 약 **887초**가 걸립니다.

`asyncio.gather()`로 20개씩 병렬 요청하여 **145초로 단축** (약 6배 개선)

```python
async def collect_all_async():
    links = get_target_links()  # service_link에서 5,065개 조회
    BATCH_SIZE = 20

    async with httpx.AsyncClient() as client:
        for i in range(0, len(links), BATCH_SIZE):
            batch = links[i:i+BATCH_SIZE]
            results = await asyncio.gather(
                *[fetch_traffic_async(client, link_id) for link_id in batch]
            )
            for result in results:
                if result:
                    save_traffic_speed(result)
```

> 배치 크기를 20으로 제한한 이유: 50개 동시 요청 시 API 서버 부하로 오히려 느려짐 (테스트로 확인)

### 2. 링크 ID 체계 불일치 해결

서울 Open API의 서비스링크 ID와 국가표준노드링크 SHP의 링크 ID가 **다른 체계**를 사용합니다.

| 구분 | 링크 ID 예시 | 출처 |
|------|------------|------|
| 전국표준노드링크 (SHP) | 1230025607 | ITS 국가교통정보센터 |
| 서울시 실시간소통 API | 1220003800 | 서울시 TOPIS |

서울 열린데이터광장의 **교통소통 표준링크 매핑정보** 엑셀로 두 ID 체계를 연결하는 `service_link` 테이블을 구성했습니다.

### 3. PostGIS 공간 쿼리

링크의 도로명과 시작/끝 좌표를 PostGIS 함수로 추출합니다.

```sql
SELECT DISTINCT ON (link_id) link_id, speed, travel_time,
    rl.road_name,
    ST_Y(ST_StartPoint(rl.geom)) as start_lat,
    ST_X(ST_StartPoint(rl.geom)) as start_lng,
    ST_Y(ST_EndPoint(rl.geom)) as end_lat,
    ST_X(ST_EndPoint(rl.geom)) as end_lng
FROM traffic_speed ts
LEFT JOIN service_link sl ON ts.link_id::BIGINT = sl.service_link_id
LEFT JOIN road_link rl ON sl.std_link_id::VARCHAR = rl.link_id
WHERE collected_at >= NOW() - INTERVAL '15 minutes'
ORDER BY link_id, collected_at DESC
```

### 4. Redis 캐싱

교통 데이터는 10분마다 갱신되므로, API 응답을 Redis에 **10분간 캐싱**합니다.
동일한 요청이 들어오면 DB 쿼리 없이 Redis에서 즉시 반환합니다.

```python
cached = redis_client.get("traffic:worst")
if cached:
    return json.loads(cached)

# DB 쿼리 후 캐싱
redis_client.setex("traffic:worst", 600, json.dumps(rows, default=str))
```

### 5. MCP 서버 연동

FastAPI REST 서버를 그대로 활용해 MCP 툴에서 내부 HTTP 호출합니다.
Claude 등 AI 에이전트가 자연어로 교통 정보를 조회할 수 있습니다.

```python
@mcp.tool()
def get_road_traffic(road_name: str) -> str:
    """특정 도로의 현재 교통 상황을 반환합니다. 예: 올림픽대로, 강남대로"""
    response = httpx.get(f"{BASE_URL}/traffic/road", params={"name": road_name})
    return str(response.json())
```

---

## 📡 API Endpoints

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/traffic/worst` | 현재 가장 막히는 구간 TOP 10 |
| GET | `/traffic/road?name={도로명}` | 특정 도로 현재 교통 상황 |
| GET | `/traffic/pattern?name={도로명}` | 특정 도로 오늘 시간대별 평균 속도 |

### 응답 예시 (/traffic/worst)

```json
[
  {
    "link_id": "1210027000",
    "speed": 2.0,
    "travel_time": 551,
    "road_name": "신반포로",
    "start_lat": 37.509,
    "start_lng": 127.014,
    "end_lat": 37.508,
    "end_lng": 127.012
  }
]
```

---

## 🤖 MCP Tools

| Tool | 설명 |
|------|------|
| `get_worst_traffic` | 서울에서 현재 가장 막히는 도로 구간 10개 |
| `get_road_traffic(road_name)` | 특정 도로의 현재 교통 상황 |
| `get_traffic_pattern(road_name)` | 특정 도로의 시간대별 평균 속도 패턴 |

---

## 🚀 Getting Started

### 1. 환경변수 설정 (.env)

```
DATABASE_URL=postgresql://traffic:traffic1234@localhost:5432/trafficdb
SEOUL_API_KEY=your_seoul_open_api_key
REDIS_URL=redis://localhost:6379
```

### 2. DB 설정 (Docker PostGIS)

```bash
docker run -d \
  --name traffic-db \
  -e POSTGRES_DB=trafficdb \
  -e POSTGRES_USER=traffic \
  -e POSTGRES_PASSWORD=traffic1234 \
  -p 5432:5432 \
  postgis/postgis:15-3.3
```

### 3. Redis 실행

```bash
docker run -d \
  --name traffic-redis \
  -p 6379:6379 \
  redis:7
```

### 4. 의존성 설치 및 서버 실행

```bash
pip install -r requirements.txt
uvicorn app.main:app
```

### 5. MCP 서버 설정 (Claude Desktop)

`~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "seoul-traffic": {
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/seoul-flow/app/mcp_server.py"]
    }
  }
}
```

---

## 📝 한계 및 개선 방향

- **도로명 매핑 불완전**: 서울시 서비스링크 ↔ 표준노드링크 ID 체계가 완전히 일치하지 않아 일부 링크의 도로명이 null로 반환됨
- **속도 기반 혼잡도**: 교통량(Volume) 데이터 미제공으로 V/C비 기반 LOS 산정 불가 → 속도 기반으로 대체
- **Redis 캐시 무효화**: 새 수집 완료 시 캐시를 자동으로 삭제하는 로직 미구현

---

## 📅 Changelog

- **2026.05.13** — Redis 캐싱 추가 (traffic:worst, road, pattern)
- **2026.05.08** — MCP 서버 연동, Claude 자연어 질의 구현
- **2026.04.10** — PostGIS 공간 쿼리 및 구간 좌표 API 추가
- **2026.04.09** — 비동기 수집 파이프라인 구현, APScheduler 연동
- **2026.04.08** — service_link 매핑 테이블 설계 및 적재
- **2026.04.03** — 초기 DB 설계, 도로 링크 데이터 적재
