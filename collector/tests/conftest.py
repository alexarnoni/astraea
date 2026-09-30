"""Configuracao dos testes do collector.

db.py exige DATABASE_URL ao ser importado; define-se um valor dummy. Nenhuma conexao
e aberta: o engine e lazy e os testes trocam httpx por mocks.
"""

import os
import sys

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
