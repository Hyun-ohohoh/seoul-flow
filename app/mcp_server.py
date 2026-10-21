from mcp.server.fastmcp import FastMCP
import httpx
import sys
print("mcp_server.py 시작", file=sys.stderr)

mcp = FastMCP("seoul-traffic")

BASE_URL = "http://localhost:8000"

@mcp.tool()
def get_worst_traffic() -> str:
    """서울 전체에서 최근 15분 내 수집된 최신 속도 기준, 가장 느린 구간 10개를 반환합니다."""
    response = httpx.get(f"{BASE_URL}/traffic/worst")
    return str(response.json())

@mcp.tool()
def get_road_traffic(road_name: str) -> str:
    """도로명으로 최근 15분 내 가장 느린 구간 10개를 반환합니다(도로 전체 평균이 아님).
    road_name은 도로명만 받습니다. 예) 올림픽대로, 강남대로
    '강남'처럼 지역명으로 질문받으면, 해당 지역의 주요 도로명으로 나눠 각각 호출하세요.
    이름이 포함된 이면도로(예: 테헤란로114길)도 함께 나올 수 있습니다."""
    response = httpx.get(f"{BASE_URL}/traffic/road", params={"name": road_name})
    return str(response.json())

@mcp.tool()
def get_traffic_pattern(road_name: str) -> str:
    """도로명으로 '오늘' 수집된 데이터의 시간대별 평균 속도를 반환합니다.
    과거 여러 날의 평균(평소 패턴)이 아니므로, '평소에' 같은 질문에는 오늘 기준임을 밝혀 답하세요.
    예) 올림픽대로, 강남대로"""
    response = httpx.get(f"{BASE_URL}/traffic/pattern", params={"name": road_name})
    return str(response.json())

if __name__ == "__main__":
    mcp.run(transport="stdio")