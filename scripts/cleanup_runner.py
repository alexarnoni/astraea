import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    result = conn.execute(text(
        "DELETE FROM raw.neo_feeds WHERE feed_date < CURRENT_DATE - INTERVAL '30 days'"
    ))
    conn.commit()
    print(f"[cleanup] Removidos {result.rowcount} registros de raw.neo_feeds")
