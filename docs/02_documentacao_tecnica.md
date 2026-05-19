# Documentacao Tecnica - Banca Moderna

## 1. Visao geral

O sistema Banca Moderna e uma aplicacao web Python conteinerizada com Docker.

Principais tecnologias:

- Python 3.12.
- FastAPI.
- Jinja2.
- SQLAlchemy ORM.
- MySQL 8.4.
- PyMySQL.
- Docker Compose.
- Adminer para administracao do banco.

## 2. Estrutura de pastas

```text
Banca Moderna/
  app/
    auth.py
    bootstrap.py
    config.py
    database.py
    invoices.py
    main.py
    models.py
    security.py
    services.py
    static/
      styles.css
    templates/
      base.html
      customers.html
      dashboard.html
      error.html
      invoice.html
      charge.html
      login.html
      products.html
      purchases.html
      sales.html
      service_invoice.html
      services.html
      stock.html
      suppliers.html
      users.html
  docs/
  docker-compose.yml
  Dockerfile
  requirements.txt
  .env
  .env.example
  START.bat
  STOP.bat
  start.ps1
  stop.ps1
  logs.ps1
```

## 3. Componentes principais

### `app/main.py`

Arquivo principal da aplicacao FastAPI.

Responsabilidades:

- Registrar rotas.
- Configurar sessao.
- Servir arquivos estaticos.
- Renderizar templates.
- Inicializar banco no startup.
- Proteger rotas por permissao.

### `app/models.py`

Define os modelos SQLAlchemy:

- `User`.
- `Employee`.
- `Customer`.
- `Supplier`.
- `Category`.
- `Product`.
- `Purchase`.
- `PurchaseItem`.
- `Sale`.
- `SaleItem`.
- `StockMovement`.
- `FiscalInvoice`.
- `ServiceOrder`.
- `ServiceInvoice`.
- `PaymentCharge`.

### `app/auth.py`

Controla perfis e permissoes.

Perfis:

- `admin`.
- `funcionario`.

Permissoes:

- `admin`: possui `*`.
- `funcionario`: possui `sales.view` e `sales.create`.

Tambem define o menu visivel por usuario.

### `app/services.py`

Contem regras de compra, venda, servico, cobranca e estoque.

Funcoes principais:

- `money`.
- `register_purchase`.
- `register_sale`.
- `register_sale_items`.
- `register_completed_service`.
- `create_payment_charge`.

### `app/invoices.py`

Contem a emissao de NF interna de venda e servico.

Funcoes:

- `generate_access_key`.
- `issue_invoice`.
- `issue_service_invoice`.

### `app/bootstrap.py`

Cria dados iniciais:

- Categorias padrao.
- Usuario administrador inicial.
- Migracao de perfis antigos para `funcionario`.

### `app/security.py`

Controla hash e verificacao de senha com `passlib` e `bcrypt`.

## 4. Banco de dados

Banco: MySQL.

Driver: PyMySQL.

URL padrao:

```text
mysql+pymysql://banca_user:banca_password@db:3306/banca_moderna
```

O schema e criado automaticamente no startup com:

```python
Base.metadata.create_all(bind=engine)
```

## 5. Tabelas principais

### `users`

Usuarios do sistema.

Campos importantes:

- `id`.
- `name`.
- `email`.
- `password_hash`.
- `role`.
- `active`.
- `created_at`.

### `products`

Cadastro de produtos.

Campos importantes:

- `sku`.
- `barcode`.
- `name`.
- `kind`.
- `category_id`.
- `supplier_id`.
- `cost_price`.
- `sale_price`.
- `min_quantity`.
- `quantity_on_hand`.

### `sales`

Venda principal.

Campos importantes:

- `customer_id`.
- `employee_name`.
- `subtotal`.
- `discount`.
- `total`.
- `payment_method`.
- `status`.
- `created_at`.

### `sale_items`

Itens de venda.

Campos importantes:

- `sale_id`.
- `product_id`.
- `quantity`.
- `unit_price`.
- `total`.

### `fiscal_invoices`

NF interna.

Campos importantes:

- `sale_id`.
- `number`.
- `series`.
- `access_key`.
- `status`.
- `issuer_name`.
- `issued_at`.

### `service_orders`

Servicos concluidos.

Campos importantes:

- `customer_id`.
- `description`.
- `employee_name`.
- `amount`.
- `payment_method`.
- `status`.
- `completed_at`.

### `service_invoices`

NF interna de servico.

Campos importantes:

- `service_order_id`.
- `number`.
- `series`.
- `access_key`.
- `status`.
- `issuer_name`.
- `issued_at`.

### `payment_charges`

Cobrancas internas de vendas e servicos.

Campos importantes:

- `sale_id`.
- `service_order_id`.
- `method`.
- `status`.
- `amount`.
- `due_date`.
- `reference`.
- `digitable_line`.
- `pix_copy_paste`.
- `card_brand`.
- `installments`.

## 6. Autenticacao e sessao

A aplicacao usa `SessionMiddleware` do Starlette.

Chave:

```text
APP_SECRET_KEY
```

Fluxo:

1. Usuario informa e-mail e senha em `/login`.
2. Sistema valida hash da senha.
3. Sistema grava `user_id` na sessao.
4. Rotas protegidas usam `require_permission`.

## 7. Autorizacao

As rotas usam:

```python
Depends(require_permission("permissao"))
```

Exemplo:

```python
current_user: User = Depends(require_permission("sales.view"))
```

Se o usuario nao tiver permissao:

- O sistema retorna erro 403.

Se nao estiver logado:

- O sistema redireciona para `/login`.

## 8. Docker

Servicos:

- `app`: aplicacao FastAPI.
- `db`: MySQL 8.4.
- `adminer`: interface web para banco.

Portas:

- App: `8000`.
- Adminer: `8080`.

O MySQL nao e exposto diretamente no host por padrao. Ele fica acessivel internamente no Docker pelo host `db`.

## 9. Variaveis de ambiente

Arquivo `.env`:

```text
MYSQL_DATABASE=banca_moderna
MYSQL_USER=banca_user
MYSQL_PASSWORD=banca_password
MYSQL_ROOT_PASSWORD=root_password
DATABASE_URL=mysql+pymysql://banca_user:banca_password@db:3306/banca_moderna
APP_SECRET_KEY=troque-esta-chave
```

## 10. Observacao sobre NF e cobranca oficial

A NF atual e interna. Para emitir NF-e, NFC-e ou NFS-e oficial no Brasil, sera necessario implementar:

- Cadastro fiscal da empresa.
- Certificado digital A1 ou A3.
- Ambiente homologacao/producao.
- Comunicacao com webservices SEFAZ.
- Regras por UF.
- NCM, CFOP, CST/CSOSN, aliquotas.
- Assinatura XML.
- Autorizacao, cancelamento e inutilizacao.

As cobrancas de boleto, Pix, debito e credito tambem sao internas. Para cobranca real, sera necessario integrar:

- Banco ou gateway para boleto registrado.
- PSP Pix para QR Code dinamico/copia e cola valido.
- Adquirente/maquininha para debito e credito.
- Webhooks de liquidacao e conciliacao.
