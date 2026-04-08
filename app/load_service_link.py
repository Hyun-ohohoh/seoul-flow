import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os


load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))

df = pd.read_excel('/Users/hyun-oh/SideProject/서울특별시 교통소통 표준링크 매핑정보_20250306.xlsx')

df = df.rename(columns={
    '서비스링크': 'service_link_id',
    '표준링크순서': 'seq',
    '표준링크아이디': 'std_link_id'
})

df = df.drop_duplicates(subset=['service_link_id', 'seq'])
df = df.dropna(subset=['seq'])
df.to_sql('service_link', engine, if_exists='append', index=False)
print(f"적재 완료: {len(df)}행")

