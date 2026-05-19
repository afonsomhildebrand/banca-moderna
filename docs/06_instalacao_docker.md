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
MYSQL_PASSWORD=gere-uma-senha-forte-para-o-mysql
MYSQL_ROOT_PASSWORD=gere-uma-senha-forte-para-root
DATABASE_URL=mysql+pymysql://banca_user:gere-uma-senha-forte-para-o-mysql@db:3306/banca_moderna
APP_SECRET_KEY=gere-uma-chave-longa-e-aleatoria-antes-de-usar
SECURE_COOKIES=false
INITIAL_ADMIN_EMAIL=admin@bancamoderna.local
INITIAL_ADMIN_PASSWORD=gere-uma-senha-admin-forte
```

Recomendacao:

- Gerar valores fortes para `APP_SECRET_KEY`, `MYSQL_PASSWORD`, `MYSQL_ROOT_PASSWORD` e `INITIAL_ADMIN_PASSWORD`.
- Em producao com HTTPS, usar `SECURE_COOKIES=true`.
- Definir `INITIAL_ADMIN_EMAIL` e `INITIAL_ADMIN_PASSWORD` antes da primeira subida para criar o administrador inicial.
- A senha inicial de administrador deve ter pelo menos 10 caracteres e nao pode ser uma senha comum.

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

No `docker-compose.yml` padrao, o Adminer e publicado em `127.0.0.1:8080`, portanto fica acessivel apenas pela propria maquina onde o Docker esta rodando.

Dados:

```text
Sistema: MySQL
Servidor: db
Usuario: banca_user
Senha: valor definido em `MYSQL_PASSWORD`
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
docker compose exec db sh -c 'mysqldump -ubanca_user -p"$MYSQL_PASSWORD" banca_moderna' > backup_banca_moderna.sql
```

Restaurar backup:

```bash
docker compose exec -T db sh -c 'mysql -ubanca_user -p"$MYSQL_PASSWORD" banca_moderna' < backup_banca_moderna.sql
```

## 13. Observacoes de producao

Para uso em producao real:

- Trocar todas as senhas e nao reutilizar os valores de exemplo.
- Usar `APP_SECRET_KEY` forte.
- Usar `SECURE_COOKIES=true` atras de HTTPS.
- Configurar backup automatico.
- Configurar HTTPS via proxy reverso.
- Remover o Adminer ou manter acesso restrito por localhost, VPN ou proxy autenticado.
- Avaliar integracao fiscal oficial se houver emissao NF-e/NFC-e.
