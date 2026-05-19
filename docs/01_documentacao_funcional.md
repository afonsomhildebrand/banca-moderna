# Documentacao Funcional - Banca Moderna

## 1. Objetivo

O aplicativo Banca Moderna tem como objetivo controlar a operacao de uma banca que vende jornais, revistas, livros, revistinhas, colecoes, albuns, figurinhas, jogos, bebidas, comidas, doces e chicletes, com suporte a itens nacionais e internacionais.

O sistema centraliza cadastros, vendas, compras, servicos, estoque, usuarios, cobrancas e emissao de NF interna para vendas e servicos.

## 2. Perfis de acesso

### Administrador

O usuario administrador possui acesso total ao aplicativo:

- Dashboard.
- Produtos.
- Clientes.
- Fornecedores.
- Compras.
- Vendas.
- Servicos.
- Estoque.
- Usuarios.
- Emissao e visualizacao de NF interna.

### Funcionario

O funcionario possui acesso somente ao modulo de vendas:

- Menu Vendas.
- Registro de venda.
- Consulta de vendas.
- Emissao e visualizacao de NF interna das vendas.

O funcionario nao acessa dashboard, produtos, clientes, fornecedores, compras, estoque ou cadastro de usuarios.

## 3. Modulos funcionais

### Login

Permite acesso ao sistema por e-mail e senha.

Regras:

- Usuario inativo nao acessa.
- Senha invalida bloqueia o login.
- Administrador entra no dashboard.
- Funcionario entra diretamente na tela de vendas.

### Dashboard

Disponivel somente para administrador.

Mostra:

- Total de produtos.
- Total de clientes.
- Total de fornecedores.
- Unidades em estoque.
- Total vendido.
- Total comprado.
- Produtos com estoque baixo.
- Ultimas movimentacoes de estoque.

### Produtos

Disponivel somente para administrador.

Permite cadastrar e consultar produtos da banca.

Campos principais:

- SKU.
- Codigo de barras.
- Nome.
- Tipo.
- Categoria.
- Fornecedor.
- Pais de origem.
- Custo.
- Preco de venda.
- Estoque inicial.
- Estoque minimo.

O campo Codigo de barras aceita leitura por leitor USB configurado como teclado. Ao bipar o produto no cadastro, o codigo fica vinculado ao item para uso rapido na venda de balcao.

Tipos de produto:

- Editorial.
- Colecionavel.
- Jogo.
- Comida.
- Bebida.
- Doce.
- Chiclete.
- Outro.

### Clientes

Disponivel somente para administrador.

Permite cadastrar clientes para vendas identificadas.

Campos:

- Nome.
- Telefone.
- E-mail.
- Documento.
- Observacoes.

### Fornecedores

Disponivel somente para administrador.

Permite cadastrar fornecedores nacionais e internacionais.

Campos:

- Nome.
- Documento.
- Pais.
- Moeda.
- Telefone.
- E-mail.

### Compras

Disponivel somente para administrador.

Permite registrar entrada de mercadorias.

Ao confirmar uma compra:

- A compra e gravada.
- O item comprado e registrado.
- O estoque do produto aumenta.
- Uma movimentacao de estoque do tipo `purchase` e criada.

### Vendas

Disponivel para administrador e funcionario.

Funcionalidades:

- Busca de produtos por nome, SKU, categoria ou codigo.
- Leitura de codigo de barras ou SKU para adicionar item diretamente ao carrinho.
- Filtro por categoria.
- Carrinho multi-item.
- Controle de quantidade por item.
- Remocao de item do carrinho.
- Desconto geral da venda.
- Forma de pagamento.
- Geracao de cobranca interna para boleto, Pix, debito e credito.
- Cliente identificado ou nao identificado.
- Vendedor.
- Baixa automatica de estoque.
- Historico de vendas.
- Emissao de NF interna.

Ao confirmar a venda:

- A venda e gravada.
- Os itens da venda sao gravados.
- O estoque de cada produto vendido e reduzido.
- Uma movimentacao de estoque do tipo `sale` e criada para cada produto.

### Servicos

Disponivel somente para administrador.

Permite registrar servicos concluidos, por exemplo encadernacao, plastificacao, entrega, assinatura, montagem de colecao ou outro atendimento prestado pela banca.

Campos principais:

- Descricao do servico.
- Cliente.
- Responsavel.
- Valor.
- Forma de pagamento.
- Vencimento.
- Bandeira do cartao.
- Parcelas.

Ao registrar o servico:

- O servico e gravado como concluido.
- Uma cobranca interna e gerada quando a forma for boleto, Pix, debito ou credito.
- O historico permite emitir uma NF interna de servico.

### Cobrancas

Disponivel a partir de vendas e servicos.

Permite:

- Gerar boleto interno com linha digitavel.
- Gerar Pix copia e cola interno.
- Registrar cobranca de debito para conciliacao.
- Registrar cobranca de credito com parcelas.
- Imprimir a cobranca pelo navegador.

Observacao: boletos, Pix e cobrancas de cartao sao controles internos. Para cobranca bancaria real, e necessario integrar banco, PSP Pix ou adquirente de cartoes.

### Estoque

Disponivel somente para administrador.

Permite consultar:

- Produtos.
- Tipo.
- Saldo atual.
- Estoque minimo.
- Status do saldo.
- Movimentacoes de entrada e saida.

### Usuarios

Disponivel somente para administrador.

Permite:

- Cadastrar usuario.
- Definir perfil `Administrador` ou `Funcionario`.
- Ativar usuario.
- Desativar usuario.

O administrador nao pode desativar o proprio usuario.

### NF interna

Disponivel a partir do historico de vendas e servicos.

Permite:

- Emitir uma NF interna para uma venda.
- Emitir uma NF interna para um servico concluido.
- Gerar numero sequencial.
- Gerar serie.
- Gerar chave interna.
- Abrir pagina da NF.
- Imprimir a NF pelo navegador.

Observacao: a NF implementada e um documento interno/imprimivel do sistema. Nao e uma NF-e, NFC-e ou NFS-e oficial autorizada pela SEFAZ ou prefeitura.

## 4. Regras de negocio

- Venda nao pode ser confirmada sem itens.
- Quantidade vendida deve ser maior que zero.
- O sistema bloqueia venda com estoque insuficiente.
- Desconto nao pode ser maior que o subtotal da venda.
- Compra deve possuir quantidade maior que zero.
- Produto inexistente bloqueia compra ou venda.
- Cada venda pode ter no maximo uma NF interna.
- Cada servico pode ter no maximo uma NF interna de servico.
- Se a NF ja existir, o sistema reabre a NF existente.

## 5. Fluxo operacional principal

1. Administrador cadastra produtos.
2. Administrador registra compras para abastecer estoque.
3. Funcionario acessa o sistema.
4. Funcionario entra em Vendas.
5. Funcionario adiciona itens ao carrinho.
6. Funcionario informa pagamento e desconto, se houver.
7. Funcionario finaliza a venda.
8. Sistema baixa estoque.
9. Funcionario ou administrador emite NF interna da venda.
