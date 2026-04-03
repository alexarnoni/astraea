# Deploy na Oracle VM

## 1. Clonar o repositório

```bash
cd /opt
git clone https://github.com/alexarnoni/astraea.git
cd astraea
```

## 2. Configurar variáveis de ambiente

```bash
cp .env.example .env
nano .env
```

Preencher:
- `POSTGRES_PASSWORD`: senha forte (não usar `changeme`)
- `NASA_API_KEY`: sua key da NASA

## 3. Subir os containers

```bash
docker compose up -d
```

## 4. Verificar

```bash
docker compose ps
docker logs astraea-collector-1 --tail 20
curl http://localhost:8002/health
```

## 5. Configurar Cloudflare

No painel da Cloudflare, adicionar registro DNS:
- Tipo: A
- Nome: astraea
- Conteúdo: IP da VM
- Proxy: ativado (laranja)

## 6. Configurar Nginx (proxy reverso)

Adicionar ao arquivo de configuração do Nginx na VM:

```nginx
server {
    listen 80;
    server_name astraea.alexarnoni.com;

    location /api/ {
        proxy_pass http://localhost:8002/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Ou se usar Cloudflare Tunnel, configurar o tunnel para apontar `astraea.alexarnoni.com` → `localhost:8002`.

## 7. Deploy do frontend no Cloudflare Pages

No painel do Cloudflare Pages:
1. Conectar ao repositório `github.com/alexarnoni/astraea`
2. Build settings:
   - Framework: None
   - Build command: (vazio)
   - Build output directory: `dashboard`
3. Deploy
