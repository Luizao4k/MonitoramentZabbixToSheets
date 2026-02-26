📊 Monitoramento de Incidentes Zabbix → Google Sheets

Aplicação Python responsável por:

🔎 Buscar problemas ativos no Zabbix

🧠 Aplicar regras de negócio (severidade, grupo, prefixo, DRE)

📄 Registrar incidentes no Google Sheets

🔁 Atualizar automaticamente incidentes resolvidos

📊 Gerar estatísticas consolidadas de processamento


🆕 Versão 3.0 — Melhorias Implementadas
🔄 Sincronização de Status

Zabbix definido como fonte única de verdade

Incidentes resolvidos agora são detectados automaticamente

Atualização em lote do status e data de resolução no Google Sheets

📊 Estatísticas Consolidadas

Implementação de métricas de execução:

Total recebidos

Novos incidentes

Atualizados (resolvidos)

Ignorados (com detalhamento por motivo)

🛡️ Maior Robustez

Tratamento de erro específico para falhas de conexão com o Zabbix

Melhoria na consistência entre sistemas

## 📂 Estrutura do Projeto

monitoramento_zabbix/
├─ app/
│ ├─ main.py
│ ├─ domain/
│ │ ├─ models.py
│ │ └─ incident_processor.py
│ ├─ infrastructure/
│ │ ├─ zabbix_service.py
│ │ └─ google_sheets_service.py
│ ├─ tests/
│ │ ├─ test_incident_processor.py
│ │ ├─ test_google_sheets_service.py
│ │ └─ test_zabbix_conexao
│ ├─ utils/
│ │ ├─logger.py
│ │ └─ normalizar.py
│ ├─ config/ # arquivos JSON de configuração
│ │ ├─ config_groups.json
│ │ ├─ config_severity.json
│ │ ├─ dre_map.json
│ │ └─ settings.py
├─ logs/ # logs do container
├─ secrets/ # service_account.json do Google
├─ Dockerfile
├─ docker-compose.yml
├─ requirements.txt
└─ .env

🔹 Camadas
Camada	Responsabilidade
Application	Orquestra o fluxo principal
Domain	Regras de negócio e modelos
Infrastructure	Integrações externas (Zabbix + Google Sheets)
Config	Variáveis de ambiente e arquivos JSON
Utils	Logger e funções auxiliares

---

⚙️ Como Funciona

Fluxo do sistema:

1. Conecta ao Zabbix

2. Busca problemas ativos

3. Mapeia eventos → hosts → grupos

4. Aplica filtros:

* Severidade mínima

* Grupo permitido

* Prefixo permitido

5. Determina DRE pelo município

6. Evita duplicados

7. Insere novos incidentes na planilha

8. Detecta incidentes resolvidos

9. Atualiza status em lote

10. Gera relatório final no log


## ⚙️ Configuração

 **Variáveis de ambiente (.env)**

```env
GOOGLE_CREDS=secrets/service_account.json
ZABBIX_URL=https://www.sistemas.pa.gov.br/zabbix/api_jsonrpc.php
ZABBIX_TOKEN=seu_token_aqui
SPREADSHEET_NAME=Incidentes Zabbix - AUTO
HTTP_PROXY=http://usuario:senha@proxy:porta
HTTPS_PROXY=http://usuario:senha@proxy:porta
GOOGLE_CREDS: caminho para o arquivo do Service Account do Google.

ZABBIX_URL e ZABBIX_TOKEN: acesso à API do Zabbix.

SPREADSHEET_NAME: nome da planilha no Google Sheets.

HTTP_PROXY / HTTPS_PROXY: somente se precisar de proxy corporativo.

Arquivos de configuração JSON (na pasta config):

config_groups.json → grupos e prefixos permitidos.

dre_map.json → mapeamento de municípios → DRE.

config_severity.json → severidade mínima dos incidentes.


⚙️ Configurações JSON
config_groups.json
{
  "allowed_groups": [
    "Grupo A",
    "Grupo B"
  ],
  "allowed_prefixes": [
    "SRV",
    "RTR"
  ]
}
config_severity.json
{
  "min_severity": 3
}
dre_map.json
{
  "BELEM": "DRE - BELEM",
  "ANANINDEUA": "DRE - ANANINDEUA"
}
⚠️ Municípios não encontrados vão para "DRE - OUTROS"



📄 Configuração da Planilha

Antes de executar o sistema:

Criar uma planilha no Google Sheets

Criar uma aba chamada:

_TEMPLATE

Essa aba será usada como modelo para criar automaticamente as abas das DREs.

📌 Estrutura esperada da aba
   A	      B       C	        D	        E	        F   	 G	           H
EVENT_ID	DATA	HOST	MUNICIPIO	DESCRIÇÃO	SEVERIDADE	STATUS	DATA_RESOLUCAO

O sistema criará automaticamente abas com base nas DREs definidas no dre_map.json.



▶️ Como Executar 

1️⃣ Instalar dependências

pip install -r requirements.txt

2️⃣ Executar aplicação

python main.py

📦 Dependências

pyzabbix

gspread

oauth2client

python-dotenv

requests

google-auth

cryptography


📊 Regras de Negócio
🔹 Filtros aplicados

Severidade < min_severity → Ignorado

Grupo não permitido → Ignorado

Prefixo inválido → Ignorado

Duplicado → Ignorado

Host não encontrado → Ignorado

🔹 Status
Status	Significado
0	Pendente
1	Resolvido
📈 Relatório Final

Ao final da execução, o sistema gera:

Total recebidos

Novos incidentes

Atualizados (resolvidos)

Ignorados por:

Severidade

Grupo

Prefixo

Duplicidade

Host não encontrado

🔄 Atualização de Resolvidos

O sistema:

Compara incidentes ativos no Zabbix

Com os EVENT_ID existentes na planilha

Marca como resolvido aqueles que não estão mais ativos

Atualiza em lote (performance otimizada)

🧠 Conceitos Importantes
🔹 DRE

A DRE é determinada automaticamente com base no município extraído do nome do host.

🔹 Fonte Única de Verdade

As DREs válidas são derivadas automaticamente do dre_map.json.


👨‍💻 Autor
github.com/Luizao4k

Projeto desenvolvido para automação de monitoramento e consolidação de incidentes corporativos.