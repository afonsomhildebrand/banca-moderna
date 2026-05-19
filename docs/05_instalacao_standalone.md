# Instalacao Standalone - Banca Moderna

## 1. Objetivo

Este guia explica como instalar o Banca Moderna usando o pacote standalone fornecido em `.zip`.

O pacote standalone contem:

- Aplicacao Python.
- Dockerfile.
- Docker Compose.
- Configuracoes.
- Scripts de iniciar e parar.
- Documentacao.

## 2. Requisitos

- Windows 10 ou superior.
- Docker Desktop instalado.
- Acesso a internet na primeira instalacao para baixar imagens Docker.
- Portas livres:
  - `8000` para o aplicativo.
  - `8080` para o Adminer.

## 3. Arquivo do pacote

Arquivo:

```text
BancaModerna_Docker_Standalone.zip
```

## 4. Instalar

1. Copie o arquivo `.zip` para o computador desejado.
2. Extraia o arquivo em uma pasta, por exemplo:

```text
C:\BancaModerna
```

3. Entre na pasta extraida.
4. Confira se existem os arquivos:

```text
docker-compose.yml
Dockerfile
.env
START.bat
STOP.bat
README.md
app/
docs/
```

## 5. Iniciar pelo Windows

Clique duas vezes em:

```text
START.bat
```

O script executa:

```bash
docker compose up --build -d
```

## 6. Acessar

Aplicativo:

```text
http://localhost:8000
```

Adminer:

```text
http://localhost:8080
```

## 7. Login inicial

```text
E-mail: admin@bancamoderna.local
Senha: admin123
```

## 8. Parar o sistema

Clique duas vezes em:

```text
STOP.bat
```

Ou execute:

```bash
docker compose down
```

## 9. Persistencia dos dados

Os dados ficam salvos em um volume Docker chamado `mysql_data`.

Parar e iniciar os containers nao apaga os dados.

## 10. Apagar tudo e recomecar

Atencao: este comando apaga o banco.

```bash
docker compose down -v
docker compose up --build -d
```

## 11. Atualizar versao

1. Pare o sistema:

```bash
docker compose down
```

2. Substitua os arquivos da aplicacao pela nova versao.
3. Suba novamente:

```bash
docker compose up --build -d
```

## 12. Solucao de problemas

### Porta 8000 ocupada

Altere a porta no `docker-compose.yml`:

```yaml
ports:
  - "8001:8000"
```

Depois acesse:

```text
http://localhost:8001
```

### Porta 8080 ocupada

Altere:

```yaml
ports:
  - "8081:8080"
```

Depois acesse:

```text
http://localhost:8081
```

