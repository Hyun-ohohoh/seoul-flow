# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# 가상환경 활성화
source venv/bin/activate

# FastAPI 서버 실행 (개발 모드)
uvicorn app.main:app --reload

# MCP 서버 실행 (Claude Desktop 연동)
python app/mcp_server.py

# 서비스링크 매핑 데이터 초기 적재 (일회성)
python app/load_service_link.py
```

## Architecture

두 개의 독립 프로세스로 구성됩니다.

**FastAPI 서버** (`app/main.py`): APScheduler가 10분마다 `collect_all_async()`를 실행해 서울 Open API에서 5,065개 링크의 교통 속도를 수집·저장합니다. REST 엔드포인트 3개를 외부에 노출합니다.

**MCP 서버** (`app/mcp_server.py`): stdio 전송 방식으로 Claude Desktop에 연결됩니다. 내부적으로 `localhost:8000`의 FastAPI 서버에 HTTP 요청을 보내는 방식이므로, **MCP 서버 사용 시 FastAPI 서버가 먼저 실행 중이어야 합니다.**

## DB Schema

PostgreSQL + PostGIS 사용. 테이블 관계:

```
road_link (PostGIS)          service_link              traffic_speed
─────────────────            ─────────────             ─────────────────────
link_id (PK)      ←──────── std_link_id               id (PK)
road_name                    service_link_id ←───────── link_id
geom (LineString)            seq                        speed (km/h)
                                                        travel_time (초)
                                                        collected_at
```

- `road_link`는 외부에서 사전 적재된 테이블 (PostGIS geometry 포함, 15,924개 링크)
- `service_link`는 `load_service_link.py`로 엑셀에서 일회성 적재
- `traffic_speed`는 `Base.metadata.create_all()`로 서버 시작 시 자동 생성

## Key Patterns

**링크 ID 타입 캐스팅**: `traffic_speed.link_id`는 `String(20)`, `service_link.service_link_id`는 `BIGINT`이므로 JOIN 시 `ts.link_id::BIGINT = sl.service_link_id` 캐스팅이 필요합니다.

**최신 데이터 조회**: 링크별 최근 1건은 `DISTINCT ON (link_id) ... ORDER BY link_id, collected_at DESC`로 가져옵니다. 수집 주기가 10분이므로 조회 윈도우는 `NOW() - INTERVAL '15 minutes'`입니다.

**비동기 수집**: 서울 Open API는 링크 ID 1개당 요청 1회 필요. 20개씩 `asyncio.gather()`로 배치 병렬 처리합니다.

## Environment Variables

`.env` 파일에 설정:
- `DATABASE_URL` — PostgreSQL 연결 문자열
- `SEOUL_API_KEY` — 서울 열린데이터광장 API 키
- `MAPPING_FILE_PATH` — 서비스링크 매핑 엑셀 파일 경로
