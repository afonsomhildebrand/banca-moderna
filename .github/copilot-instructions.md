# Copilot / Agentes — instruções específicas do repositório Banca Moderna

Propósito: fornecer ao agente informação prática e acionável para trabalhar neste projeto Python/FastAPI.

- **Stack principal**: FastAPI app em `app/` com templates Jinja2 (`app/templates`) e assets em `app/static`.
- **ORM / DB**: SQLAlchemy declarative em `app/models.py` + engine/Session em `app/database.py`. Variável de conexão vem de `app/config.py` (`database_url`).
- **Execução em produção/CI**: projetado para rodar via Docker Compose (veja `docker-compose.yml`). Comandos úteis:
  - `docker compose up --build -d`
  - `docker compose down`
  - Testes: `docker compose run --rm app pytest`

- **Config/segurança**: variáveis lidas do `.env` (via `pydantic-settings`). `APP_SECRET_KEY` é obrigatório e bloqueia startup se fraco (ver `app/config.py`).

Padrões e convenções específicas do projeto
- Sessões e autenticação: usa `starlette.middleware.sessions.SessionMiddleware` configurado em `app/main.py`. A sessão armazena `user_id` e `csrf_token`.
- CSRF: há um middleware custom em `app/main.py` que valida POSTs de formulário. Regras importantes:
  - Apenas `application/x-www-form-urlencoded` é aceito para POSTs de formulários.
  - O token CSRF está em `request.session['csrf_token']` e também é enviado em formulários como `csrf_token`.
  - O corpo do request é lido e re-armado no `request._receive` para roteamento posterior.
- Validação de senha: use `app/security.py` — senhas devem ter pelo menos 10 caracteres.
- Erros de domínio: o projeto usa `StockError` (em `app/services.py`) para sinalizar validações/erros de negócio e trata IntegrityError em pontos de emissão de nota/commit.

Arquitetura e fluxo de dados (alto nível)
- Rotas e views: definidas em `app/main.py`. As páginas usam templates Jinja2 via `templates.TemplateResponse(...)`.
- Fluxo de vendas/compras/estoque: as regras de negócio ficam em `app/services.py` (funções como `register_sale_items`, `register_purchase`, `create_payment_charge`). As models relacionadas estão em `app/models.py`.
- Emissão de documentos fiscais internos: `app/invoices.py` gera `FiscalInvoice`/`ServiceInvoice` e usa `generate_access_key` para `access_key`.
- Seed e bootstrap: `app/bootstrap.py` cria categorias padrão e admin inicial quando `INITIAL_ADMIN_*` estão definidos.

Testes e como eles usam o sistema
- Os testes usam `fastapi.testclient.TestClient` e sobrescrevem a dependência `get_db` (veja `tests/conftest.py`).
  - Em testes, `DATABASE_URL` é setado para `sqlite://` e `APP_SECRET_KEY` para `test-secret-key`.
  - Fixture `db_session` cria um engine SQLite em memória com `StaticPool` e chama `seed_database`.
- Para reproduzir um teste localmente sem Docker:
  - Exporte `APP_SECRET_KEY` e rode `pytest` (o `conftest.py` já define variáveis para o ambiente de teste).

Pontos de atenção para agentes de codificação
- Antes de alterar rotas POST baseadas em formulário, preserve a lógica de CSRF (ver `app/main.py`), especialmente o requisito de `content-type` e leitura do corpo.
- Não altere a forma como `request.session` é usada: `user_id`/`csrf_token` são esperados por autenticação e testes.
- Ao tocar no modelo `Product` / contagem de estoque, mantenha atomicidade — funções em `app/services.py` usam `with_for_update` e `db.flush()` para garantir consistência.
- Para criar seeds ou dados iniciais, use `seed_database(db)` em `app/bootstrap.py` para seguir convenções da aplicação.
- Trocar `APP_SECRET_KEY` é crítico: `get_settings()` lança `RuntimeError` se for fraca.

Exemplos rápidos (referências do código)
- Autenticação baseada em sessão: `app/main.py` — `login()` e `get_current_user()` (`app/auth.py`).
- CSRF middleware: `app/main.py` — função `csrf_middleware`.
- Regras de negócio de venda multi-item: `app/services.py` — `register_sale_items()` (ver verificação de estoque e movimentações).
- Test fixtures: tests/conftest.py.

O que evitar
- Não mude o mecanismo de CSRF para JSON sem atualizar todas as views e os testes.
- Evite substituir a sessão por JWT sem migração coerente (muitos lugares dependem de `request.session`).

Se algo não estiver claro
- Pergunte qual área quer modificar (rotas, modelos, templates, testes). Posso gerar patches focados e rodar os testes de unidade/funcionais.

Fim.
