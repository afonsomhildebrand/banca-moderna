# Instalacao Docker - Banca Moderna

## 1. Objetivo

Este guia explica como rodar o Banca Moderna diretamente com Docker Compose.

## 2. Requisitos

- Docker Desktop ou Docker Engine.
- Docker Compose v2.
- Terminal PowerShell, CMD, Windows Terminal, Bash ou equivalente.

Verificar Docker:

```bash
docker --version
docker compose version
```

## 3. Configuracao

Arquivo principal:

```text
docker-compose.yml
```

Arquivo de variaveis:

```text
.env
```

Exemplo:

```text
MYSQL_DATABASE=banca_moderna
MYSQL_USER=banca_user
MYSQL_PASSWORD=banca_password
MYSQL_ROOT_PASSWORD=root_password
DATABASE_URL=mysql+pymysql://banca_user:banca_password@db:3306/banca_moderna
APP_SECRET_KEY=gere-uma-chave-longa-e-aleatoria-antes-de-usar
```

Recomendacao:

- Trocar `APP_SECRET_KEY`.
- Trocar senhas antes de usar em ambiente real.

## 4. Subir ambiente

Na pasta do projeto:

```bash
docker compose up --build -d
```

## 5. Verificar containers

```bash
docker compose ps
```

Resultado esperado:

- `banca_moderna_app`: healthy.
- `banca_moderna_db`: healthy.
- `banca_moderna_adminer`: up.

## 6. Acessar aplicacao

```text
http://localhost:8000
```

## 7. Acessar Adminer

```text
http://localhost:8080
```

Dados:

```text
Sistema: MySQL
Servidor: db
Usuario: banca_user
Senha: banca_password
Banco: banca_moderna
```

## 8. Ver logs

Logs da aplicacao:

```bash
docker compose logs -f app
```

Logs do banco:

```bash
docker compose logs -f db
```

## 9. Parar ambiente

```bash
docker compose down
```

## 10. Parar e apagar volume

Atencao: apaga o banco.

```bash
docker compose down -v
```

## 11. Rebuild completo

```bash
docker compose build --no-cache
docker compose up -d
```

## 12. Backup simples do banco

Criar backup:

```bash
docker compose exec db mysqldump -ubanca_user -pbanca_password banca_moderna > backup_banca_moderna.sql
```

Restaurar backup:

```bash
docker compose exec -T db mysql -ubanca_user -pbanca_password banca_moderna < backup_banca_moderna.sql
```

## 13. Observacoes de producao

Para uso em producao real:

- Trocar todas as senhas.
- Usar `APP_SECRET_KEY` forte.
- Configurar backup automatico.
- Configurar HTTPS via proxy reverso.
- Restringir acesso ao Adminer.
- Avaliar integracao fiscal oficial se houver emissao NF-e/NFC-e.
