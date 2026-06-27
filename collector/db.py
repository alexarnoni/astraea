import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL não está definida. Configure a variável de ambiente "
        "(veja .env.example) antes de iniciar o collector."
    )

# pool_pre_ping evita erros de conexão ociosa encerrada pelo Postgres.
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
