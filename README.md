# 🚦 Seoul Flow

서울시 실시간 교통 데이터를 수집·저장·분석하고, MCP(Model Context Protocol)를 통해 AI 에이전트에 교통 정보를 제공하는 백엔드 시스템입니다.

## Architecture

```
Seoul Open API (XML)
        ↓ (10분마다 비동기 수집)
  FastAPI + APScheduler
        ↓
  PostgreSQL + PostGIS
  (15,924개 도로 링크)
        ↓
  FastAPI REST Endpoints
        ↓
  MCP Server (stdio)
        ↓
  Claude / AI Agent
```

## Tech Stack

| 분류 | 기술 |
|------|------|
| API 서버 | FastAPI |
| ORM | SQLAlchemy |
| DB | PostgreSQL + PostGIS |
| 비동기 HTTP | httpx (asyncio) |
| 스케줄러 | APScheduler |
| AI 연동 | MCP (fastmcp) |
| 환경변수 | python-dotenv |

## Project Structure

```
seoul-flow/
├── app/
│   ├── models/
│   │   └── traffic_speed.py
│   ├── routers/
│   │   └── traffic.py
│   ├── scheduler/
│   │   └── collector.py
│   ├── services/
│   │   └── database.py
│   ├── load_service_link.py
│   ├── main.py
│   └── mcp_server.py
├── requirements.txt
└── .env
```

## Data Model

### DB 테이블 관계

```
road_link (PostGIS)          service_link              traffic_speed
─────────────────            ─────────────             ─────────────────────
link_id (PK)      ←──────── std_link_id               id (PK, autoincrement)
road_name                    service_link_id ←───────── link_id (FK)
geom (LineString)            seq                        speed (km/h)
                                                        travel_time (초)
                                                        collected_at (DateTime)
```

- **road_link**: 서울시 표준 도로 링크 15,924개 (PostGIS geometry 포함)
- **service_link**: 서울 Open API 서비스링크 ↔ 표준링크 매핑 테이블
- **traffic_speed**: 10분 주기로 수집된 실시간 속도 데이터

## Key Logic

### 1. 비동기 수집 (collector.py)

서울 Open API는 링크 ID 1개당 요청 1회가 필요합니다. 5,065개 링크를 **20개씩 묶어 asyncio.gather()로 병렬 요청**하여 수집 시간을 대폭 단축합니다.

```python
for i in range(0, len(links), 20):
    batch = links[i:i+20]
    results = await asyncio.gather(
        *[fetch_traffic_async(client, link_id) for link_id in batch]
    )
```

### 2. PostGIS 공간 쿼리

링크의 시작/끝 좌표를 PostGIS 함수로 추출합니다.

```sql
ST_Y(ST_StartPoint(rl.geom)) as start_lat,
ST_X(ST_StartPoint(rl.geom)) as start_lng
```

### 3. 최신 데이터 조회 (DISTINCT ON)

링크별 가장 최근 데이터 1건만 가져올 때 PostgreSQL의 `DISTINCT ON`을 활용합니다.

```sql
SELECT DISTINCT ON (link_id) link_id, speed, travel_time
FROM traffic_speed
WHERE collected_at >= NOW() - INTERVAL '15 minutes'
ORDER BY link_id, collected_at DESC
```

### 4. MCP 서버 연동

FastAPI REST 서버를 그대로 활용해 MCP 툴에서 내부 HTTP 호출합니다. Claude 등 AI 에이전트가 자연어로 교통 정보를 조회할 수 있습니다.

```python
@mcp.tool()
def get_road_traffic(road_name: str) -> str:
    """특정 도로의 현재 교통 상황을 반환합니다."""
    response = httpx.get(f"{BASE_URL}/traffic/road", params={"name": road_name})
    return str(response.json())
```

## API Endpoints

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/traffic/worst` | 현재 가장 막히는 구간 TOP 10 |
| GET | `/traffic/road?name={도로명}` | 특정 도로 현재 교통 상황 |
| GET | `/traffic/pattern?name={도로명}` | 특정 도로 오늘 시간대별 평균 속도 |

## MCP Tools

| Tool | 설명 |
|------|------|
| `get_worst_traffic` | 서울에서 현재 가장 막히는 도로 구간 10개 |
| `get_road_traffic(road_name)` | 특정 도로의 현재 교통 상황 |
| `get_traffic_pattern(road_name)` | 특정 도로의 시간대별 평균 속도 패턴 |

## Getting Started

### 1. 환경변수 설정

```env
DATABASE_URL=postgresql://user:password@localhost:5432/seoul_flow
SEOUL_API_KEY=your_seoul_open_api_key
MAPPING_FILE_PATH=./서울특별시 교통소통 표준링크 매핑정보_20250306.xlsx 
```

### 2. DB 설정 (Docker PostGIS)

```bash
docker run -d \
  --name traffic-db \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  postgis/postgis:15-3.3
```

### 3. 의존성 설치 및 서버 실행

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 4. MCP 서버 실행

```bash
python mcp_server.py
```

Claude Desktop `claude_desktop_config.json` 설정:
```json
{
  "mcpServers": {
    "seoul-traffic": {
      "command": "python",
      "args": ["/path/to/seoul-flow/mcp_server.py"]
    }
  }
}
```

## Changelog

- 2025.05.13 — 실시간 교통 수집 및 MCP 서버 연동 초기 구현