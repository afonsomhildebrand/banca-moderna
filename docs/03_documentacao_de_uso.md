# Documentacao de Uso - Banca Moderna

## 1. Acessar o sistema

Abra o navegador e acesse:

```text
http://localhost:8000
```

Login inicial:

```text
E-mail: admin@bancamoderna.local
Senha: admin123
```

## 2. Entrar como administrador

1. Acesse `/login`.
2. Informe o e-mail do administrador.
3. Informe a senha.
4. Clique em `Entrar`.

O administrador sera direcionado para o Dashboard.

## 3. Entrar como funcionario

1. Acesse `/login`.
2. Informe e-mail e senha do funcionario.
3. Clique em `Entrar`.

O funcionario sera direcionado diretamente para Vendas.

## 4. Cadastrar usuario funcionario

Somente administrador.

1. Acesse `Usuarios`.
2. Preencha nome, e-mail e senha.
3. Em perfil, selecione `Funcionario`.
4. Deixe `Ativo` marcado.
5. Clique em `Salvar usuario`.

## 5. Cadastrar produto

Somente administrador.

1. Acesse `Produtos`.
2. Informe SKU.
3. Opcionalmente, clique em `Codigo de barras` e bipe o produto com o leitor.
4. Informe nome do produto.
5. Escolha o tipo.
6. Informe preco de venda.
7. Informe estoque inicial.
8. Informe estoque minimo.
9. Clique em `Salvar produto`.

## 6. Registrar compra

Somente administrador.

1. Acesse `Compras`.
2. Escolha fornecedor.
3. Escolha produto.
4. Informe quantidade.
5. Informe custo unitario.
6. Informe documento, se houver.
7. Clique em `Confirmar compra`.

O sistema aumenta automaticamente o estoque.

## 7. Registrar venda

Administrador ou funcionario.

1. Acesse `Vendas`.
2. Localize o produto usando busca ou filtro.
3. Clique no produto para adicionar ao carrinho ou use o campo `Leitor de codigo de barras` e bipe o item.
4. Ajuste a quantidade no carrinho, se necessario.
5. Adicione outros itens, se necessario.
6. Informe cliente, se houver.
7. Informe vendedor.
8. Informe desconto, se houver.
9. Escolha forma de pagamento.
10. Clique em `Finalizar venda`.

O sistema baixa automaticamente o estoque dos produtos vendidos.

Leitores USB que funcionam como teclado nao precisam de configuracao extra. Deixe o cursor no campo `Leitor de codigo de barras`, bipe o produto e o item sera adicionado ao carrinho quando o leitor enviar Enter.

## 8. Emitir NF interna

Administrador ou funcionario.

1. Acesse `Vendas`.
2. Localize a venda no historico.
3. Clique em `Emitir NF`.
4. O sistema abrira a pagina da NF.
5. Clique em `Imprimir` se quiser gerar impressao ou PDF pelo navegador.

Se a NF ja tiver sido emitida, a tela exibira o link da NF existente.

## 9. Consultar estoque

Somente administrador.

1. Acesse `Estoque`.
2. Consulte saldo atual.
3. Verifique status baixo ou ok.
4. Consulte movimentacoes.

## 10. Sair do sistema

Clique em `Sair` no menu lateral.
