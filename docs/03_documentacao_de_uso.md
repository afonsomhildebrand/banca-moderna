# Documentacao de Uso - Banca Moderna

## 1. Acessar o sistema

Abra o navegador e acesse:

```text
http://localhost:8000
```

Login inicial:

```text
E-mail: valor de INITIAL_ADMIN_EMAIL no .env
Senha: valor de INITIAL_ADMIN_PASSWORD no .env
```

Se o login inicial nao funcionar, confirme se `INITIAL_ADMIN_EMAIL` e `INITIAL_ADMIN_PASSWORD` foram definidos antes de subir a aplicacao. A senha deve ter pelo menos 10 caracteres e nao pode ser uma senha comum.

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
2. Preencha nome, e-mail e uma senha com pelo menos 10 caracteres.
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

## 6. Alterar cadastros

Somente administrador.

1. Acesse `Produtos`, `Clientes`, `Fornecedores` ou `Usuarios`.
2. Na tabela de cadastrados, edite os campos diretamente na linha desejada.
3. Clique em `Salvar` na propria linha.

Em `Usuarios`, deixe `Nova senha` em branco para manter a senha atual. Ao alterar o proprio usuario, o sistema mantem a conta ativa.

## 7. Registrar compra

Somente administrador.

1. Acesse `Compras`.
2. Escolha fornecedor.
3. Escolha produto.
4. Informe quantidade.
5. Informe custo unitario.
6. Informe documento, se houver.
7. Clique em `Confirmar compra`.

O sistema aumenta automaticamente o estoque.

## 8. Registrar venda

Administrador ou funcionario.

1. Acesse `Vendas`.
2. Localize o produto usando busca ou filtro.
3. Clique no produto para adicionar ao carrinho ou use o campo `Leitor de codigo de barras` e bipe o item.
4. Ajuste a quantidade no carrinho, se necessario.
5. Adicione outros itens, se necessario.
6. Informe cliente, se houver.
7. Informe vendedor.
8. Informe desconto, se houver.
9. Escolha forma de pagamento: dinheiro, Pix, boleto, debito, credito, fiado ou vale.
10. Clique em `Finalizar venda`.

O sistema baixa automaticamente o estoque dos produtos vendidos.

Leitores USB que funcionam como teclado nao precisam de configuracao extra. Deixe o cursor no campo `Leitor de codigo de barras`, bipe o produto e o item sera adicionado ao carrinho quando o leitor enviar Enter.

Quando a venda for Pix, boleto, debito ou credito, o sistema gera uma cobranca interna. O link da cobranca aparece no historico da venda.

## 9. Registrar servico concluido

Somente administrador.

1. Acesse `Servicos`.
2. Informe a descricao do servico.
3. Informe cliente, se houver.
4. Informe responsavel.
5. Informe valor.
6. Escolha pagamento: Pix, boleto, debito, credito ou dinheiro.
7. Informe vencimento, bandeira ou parcelas quando aplicavel.
8. Clique em `Registrar servico`.

O sistema registra o servico como concluido. Para Pix, boleto, debito ou credito, uma cobranca interna fica disponivel no historico.

## 10. Abrir cobranca

Administrador ou funcionario quando a cobranca for de venda; administrador quando for de servico.

1. Acesse o historico de `Vendas` ou `Servicos`.
2. Clique no link da cobranca.
3. Verifique boleto, Pix copia e cola ou dados de conciliacao de cartao.
4. Clique em `Imprimir`, se necessario.

Boletos, Pix e cartoes sao controles internos. Para cobranca bancaria real, integre o sistema a banco, PSP Pix ou adquirente.

## 11. Emitir NF interna

Administrador ou funcionario.

1. Acesse `Vendas`.
2. Localize a venda no historico.
3. Clique em `Emitir NF`.
4. O sistema abrira a pagina da NF.
5. Clique em `Imprimir` se quiser gerar impressao ou PDF pelo navegador.

Se a NF ja tiver sido emitida, a tela exibira o link da NF existente.

Para emitir NF interna de servico:

1. Acesse `Servicos`.
2. Localize o servico concluido.
3. Clique em `Emitir NF`.
4. O sistema abrira a pagina da NF de servico.

## 12. Consultar estoque

Somente administrador.

1. Acesse `Estoque`.
2. Consulte saldo atual.
3. Verifique status baixo ou ok.
4. Consulte movimentacoes.

## 13. Sair do sistema

Clique em `Sair` no menu lateral.

## 14. Seguranca no uso diario

- Nao compartilhe a conta de administrador.
- Crie usuarios individuais para funcionarios.
- Desative usuarios que nao devem mais acessar o sistema.
- Use senhas fortes e diferentes das senhas de outros sistemas.
- Em caso de muitas tentativas de login incorretas, aguarde alguns minutos antes de tentar novamente.
