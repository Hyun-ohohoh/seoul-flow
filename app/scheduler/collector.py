import httpx
import os
import time
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from app.database import SessionLocal
from sqlalchemy import text

load_dotenv()
API_KEY = os.getenv("SEOUL_API_KEY")

def get_target_links():
    db = SessionLocal()
    result = db.execute(text("""
        SELECT DISTINCT service_link_id FROM service_link
    """))
    link_ids = [row[0] for row in result]
    db.close()
    return link_ids

def fetch_traffic(link_id):
    url = f"http://openapi.seoul.go.kr:8088/{API_KEY}/xml/TrafficInfo/1/1/{link_id}"
    response = httpx.get(url, timeout=10.0)

    root = ET.fromstring(response.text)
    row = root.find('row')
    if row is None:
        return None

    return {
        'link_id': row.find('link_id').text,
        'speed': row.find('prcs_spd').text,
        'travel_time': row.find('prcs_trv_time').text
    }

# 테스트
links = get_target_links()
print(f"수집 대상 링크 수: {len(links)}")

result = fetch_traffic(links[0])
print(result)