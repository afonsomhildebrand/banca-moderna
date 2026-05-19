# Documentacao de Testes - Banca Moderna

## 1. Objetivo

Esta documentacao descreve cenarios manuais e tecnicos para validar o funcionamento do aplicativo.

## 2. Testes de infraestrutura

### Subir containers

Comando:

```bash
docker compose up --build -d
```

Resultado esperado:

- Container `banca_moderna_app` rodando e saudavel.
- Container `banca_moderna_db` rodando e saudavel.
- Container `banca_moderna_adminer` rodando.

### Verificar status

Comando:

```bash
docker compose ps
```

Resultado esperado:

- `app`: `healthy`.
- `db`: `healthy`.
- `adminer`: `Up`.

### Healthcheck

Comando:

```bash
curl http://localhost:8000/health
```

Resultado esperado:

```json
{"status":"ok"}
```

## 3. Testes de login

### Login administrador valido

Dados:

- E-mail: `admin@bancamoderna.local`.
- Senha: valor definido em `INITIAL_ADMIN_PASSWORD`.

Resultado esperado:

- Login realizado.
- Usuario direcionado ao Dashboard.
- Menu completo visivel.

### Login invalido

Dados:

- E-mail valido.
- Senha incorreta.

Resultado esperado:

- Sistema exibe `E-mail ou senha invalidos`.

## 4. Testes de permissao

### Administrador acessa tudo

Validar acesso a:

- Dashboard.
- Produtos.
- Clientes.
- Fornecedores.
- Compras.
- Vendas.
- Servicos.
- Estoque.
- Usuarios.

Resultado esperado:

- Todas as telas abrem.

### Funcionario acessa somente vendas

Criar usuario funcionario.

Resultado esperado:

- Menu mostra somente `Vendas`.
- Acesso direto a `/produtos` retorna erro 403.
- Acesso direto a `/` retorna erro 403.

## 5. Testes de produto

### Criar produto

1. Entrar como administrador.
2. Acessar `Produtos`.
3. Cadastrar produto com SKU unico e codigo de barras.

Resultado esperado:

- Produto aparece na lista.
- Produto aparece na tela de vendas.
- Codigo de barras aparece no cadastro e fica disponivel na tela de vendas.

## 6. Testes de compra e estoque

### Registrar compra

1. Entrar como administrador.
2. Acessar `Compras`.
3. Registrar compra de produto com quantidade 10.

Resultado esperado:

- Compra aparece na lista.
- Estoque do produto aumenta em 10.
- Movimentacao de estoque tipo `purchase` e criada.

## 7. Testes de venda

### Venda com um item

1. Entrar como administrador ou funcionario.
2. Acessar `Vendas`.
3. Adicionar um produto ao carrinho.
4. Finalizar venda.

Resultado esperado:

- Venda aparece no historico.
- Estoque baixa pela quantidade vendida.
- Movimentacao de estoque tipo `sale` e criada.

### Venda por codigo de barras

1. Entrar como administrador ou funcionario.
2. Acessar `Vendas`.
3. Clicar no campo `Leitor de codigo de barras`.
4. Bipar ou digitar o codigo de barras de um produto com estoque.

Resultado esperado:

- Produto correspondente e adicionado ao carrinho.
- Sistema informa sucesso na leitura.
- Codigo inexistente informa que nao foi encontrado ou esta sem estoque.

### Venda com dois itens

1. Adicionar dois produtos ao carrinho.
2. Ajustar quantidades.
3. Finalizar venda.

Resultado esperado:

- Venda aparece com dois itens.
- Estoque dos dois produtos e reduzido.
- Total da venda corresponde ao subtotal menos desconto.

### Venda com estoque insuficiente

1. Tentar vender quantidade maior que o estoque.

Resultado esperado:

- Sistema bloqueia a venda.
- Estoque nao e alterado.

### Venda com cobranca

1. Registrar venda com forma `boleto`, `pix`, `debito` ou `credito`.

Resultado esperado:

- Venda aparece no historico.
- Link de cobranca aparece na coluna `Cobranca`.
- Pagina da cobranca abre com dados da forma escolhida.

## 8. Testes de servicos

### Registrar servico concluido

1. Entrar como administrador.
2. Acessar `Servicos`.
3. Registrar servico com descricao, valor e pagamento Pix.

Resultado esperado:

- Servico aparece no historico.
- Cobranca Pix e criada.
- Link da cobranca abre a tela de Pix copia e cola.

### Emitir NF de servico

1. Criar ou localizar um servico.
2. Clicar em `Emitir NF`.

Resultado esperado:

- NF interna de servico e criada.
- Pagina `/notas-servico/{id}` abre.
- NF mostra numero, serie, chave interna, descricao e valor.

## 9. Testes de NF interna

### Emitir NF de venda

1. Criar ou localizar uma venda.
2. Clicar em `Emitir NF`.

Resultado esperado:

- NF e criada.
- Pagina `/notas/{id}` abre.
- NF mostra numero, serie, chave interna, itens e total.

### Emitir NF repetida

1. Emitir NF para uma venda.
2. Voltar em Vendas.
3. Abrir a NF novamente.

Resultado esperado:

- Sistema nao duplica NF.
- Link abre a NF ja existente.

## 10. Teste de impressao

1. Abrir uma NF.
2. Clicar em `Imprimir`.

Resultado esperado:

- Navegador abre janela de impressao.
- Layout de impressao nao exibe menu lateral.

## 11. Testes de regressao rapida

Executar:

```bash
python -m compileall app
```

Resultado esperado:

- Nenhum erro de sintaxe.

## 12. Testes automaticos

O projeto possui uma suite automatica com testes unitarios e funcionais usando `pytest`.

### Rodar tudo com um comando

```bash
docker compose run --rm app pytest
```

No Windows:

```text
TEST.bat
```

Ou:

```powershell
.\test.ps1
```

### Cobertura atual

Testes unitarios:

- Compra aumenta estoque e registra total.
- Venda multi-item baixa estoque e calcula total.
- Estoque insuficiente bloqueia venda.
- Emissao de NF e idempotente por venda.

Testes funcionais:

- Login de administrador.
- Menu completo para administrador.
- Funcionario acessa somente Vendas.
- Rotas protegidas exigem login.
- Cadastro de produto com codigo de barras, venda e cobranca via HTTP.
- Emissao e visualizacao de NF via HTTP.
- Registro de servico, cobranca Pix e NF de servico via HTTP.

### Resultado esperado

```text
10 passed
```
