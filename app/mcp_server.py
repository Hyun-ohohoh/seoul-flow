from mcp.server.fastmcp import FastMCP
import httpx
import sys
print("mcp_server.py 시작", file=sys.stderr)

mcp = FastMCP("seoul-traffic")

BASE_URL = "http://localhost:8000"

@mcp.tool()
def get_worst_traffic() -> str:
    """서울에서 현재 가장 막히는  도로 구간 10개를 반환합니다."""
    response = httpx.get(f"{BASE_URL}/traffic/worst")
    return str(response.json())

@mcp.tool()
def get_road_traffic(road_name: str) -> str:
    """특정 도로의 현재 교통 상황을 반환합니다. 예) 올림픽대로, 강남대로"""
    response = httpx.get(f"{BASE_URL}/traffic/road", params={"name": road_name})
    return str(response.json())

@mcp.tool()
def get_traffic_pattern(road_name: str) -> str:
    """특정 도로의 시간대별 평균 속도 패턴을 반환합니다. 예) 올림픽대로, 강남대로"""
    response = httpx.get(f"{BASE_URL}/traffic/pattern", params={"name": road_name})
    return str(response.json())

if __name__ == "__main__":
    mcp.run(transport="stdio")
