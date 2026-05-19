# Banca Moderna

Aplicativo web em Python com MySQL para gestao de banca: produtos editoriais, colecionaveis, albuns, figurinhas, jogos, comidas, bebidas, doces, chicletes, compras, vendas, servicos, estoque, leitura de codigo de barras, notas internas e cobrancas.

## Como rodar em modo standalone

1. Instale Docker Desktop.
2. Extraia a pasta do pacote em qualquer local do computador.
3. Confira as variaveis no arquivo `.env`.
4. Execute um dos comandos abaixo dentro da pasta:

```bash
docker compose up --build -d
```

Ou, no Windows, clique em `START.bat`.

5. Acesse:

- Aplicacao: http://localhost:8000
- Adminer: http://localhost:8080

Para parar:

```bash
docker compose down
```

Ou, no Windows, clique em `STOP.bat`.

## Dados e persistencia

O MySQL roda em container Docker com volume persistente `mysql_data`. Os dados continuam salvos mesmo se os containers forem parados e iniciados novamente.

Para apagar todos os dados e recomecar do zero:

```bash
docker compose down -v
docker compose up --build -d
```

## Acesso ao banco pelo Adminer

- Sistema: `MySQL`
- Servidor: `db`
- Usuario: `banca_user`
- Senha: `banca_password`
- Banco: `banca_moderna`

## Login e acesso

O sistema cria um usuario administrador inicial:

- E-mail: `admin@bancamoderna.local`
- Senha: `admin123`

Perfis disponiveis:

- Administrador: acesso total a todos os itens do aplicativo.
- Funcionario: acesso somente ao menu Vendas.

## Documentacao

Os documentos completos ficam na pasta `docs/`:

- `docs/01_documentacao_funcional.md`: regras, modulos, perfis e fluxos do sistema.
- `docs/02_documentacao_tecnica.md`: arquitetura, arquivos, banco, tabelas e Docker.
- `docs/03_documentacao_de_uso.md`: guia de uso para administrador e funcionario.
- `docs/04_documentacao_de_testes.md`: cenarios de teste manuais e tecnicos.
- `docs/05_instalacao_standalone.md`: instalacao pelo pacote standalone.
- `docs/06_instalacao_docker.md`: instalacao e operacao via Docker Compose.

## Testes automaticos

Para rodar todos os testes unitarios e funcionais com um comando:

```bash
docker compose run --rm app pytest
```

No Windows, tambem e possivel clicar em:

```text
TEST.bat
```

Ou executar:

```powershell
.\test.ps1
```

## Modulos implementados no MVP

- Dashboard com indicadores de vendas, compras e estoque.
- Cadastro de produtos, clientes e fornecedores.
- Registro de compras com entrada automatica em estoque.
- Interface de venda de balcao com busca de itens, leitura de codigo de barras, filtros, carrinho multi-item, desconto, pagamento e baixa automatica em estoque.
- Emissao de NF interna por venda, com numero, serie, chave interna e tela imprimivel.
- Registro de servicos concluidos com emissao de NF interna de servico.
- Cobrancas internas por boleto, Pix, debito e credito para vendas e servicos.
- Consulta de estoque e movimentacoes.
- Seed inicial de categorias e usuario administrador.

## Observacoes

Esta versao e um MVP operacional standalone em Docker. As proximas evolucoes naturais sao relatorios exportaveis, fechamento de caixa completo e permissoes detalhadas configuraveis por tela.
