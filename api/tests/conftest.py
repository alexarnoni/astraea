"""Configuração compartilhada dos testes da API.

Define um DATABASE_URL dummy antes de qualquer import de `database`/`main`,
já que esses módulos agora exigem a variável (fail-fast de segurança).
Nenhuma conexão real é aberta nos testes — o engine é lazy e/ou mockado.
"""

import os
import sys

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
