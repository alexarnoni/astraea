import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL não está definida. Configure a variável de ambiente "
        "(veja .env.example) antes de iniciar a API."
    )

# pool_pre_ping evita erros de 'connection already closed' ao reutilizar
# conexões ociosas do pool após o Postgres encerrar a sessão.
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
