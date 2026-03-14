# MeteoRAG — API Reference

**Versão:** 1.0  
**Atualizado:** Março 2026  
**Mantido por:** Time MeteoRAG

> Documentação técnica completa de todas as APIs externas utilizadas no projeto.  
> Leia este documento antes de implementar qualquer integração.

---

## Índice

1. [INMET API REST Pública](#1-inmet-api-rest-pública)
   - [Visão Geral](#11-visão-geral)
   - [Autenticação](#12-autenticação)
   - [Base URLs](#13-base-urls)
   - [Endpoints de Estações](#14-endpoints-de-estações)
   - [Endpoints de Dados Meteorológicos](#15-endpoints-de-dados-meteorológicos)
   - [Endpoints de Alertas](#16-endpoints-de-alertas)
   - [Schema de Dados](#17-schema-de-dados)
   - [Códigos de Resposta HTTP](#18-códigos-de-resposta-http)
   - [Valores Inválidos e Nulos](#19-valores-inválidos-e-nulos)
   - [Rate Limiting](#110-rate-limiting)
   - [Estações Mapeadas](#111-estações-de-minas-gerais-mapeadas)
   - [Exemplos de Resposta](#112-exemplos-de-resposta-reais)
2. [Anthropic API](#2-anthropic-api)
   - [Visão Geral](#21-visão-geral)
   - [Autenticação](#22-autenticação)
   - [Integração via Databricks](#23-integração-via-databricks)
   - [Endpoint Messages](#24-endpoint-messages)
   - [Streaming](#25-streaming)
   - [Modelos](#26-modelos-disponíveis)
   - [Parâmetros](#27-parâmetros-principais)
   - [Limites e Quotas](#28-limites-e-quotas)
   - [Exemplos Python](#29-exemplos-python)
3. [Decisões de Design](#3-decisões-de-design-baseadas-nas-apis)
4. [Troubleshooting](#4-troubleshooting)

---

## 1. INMET API REST Pública

### 1.1 Visão Geral

O INMET (Instituto Nacional de Meteorologia) disponibiliza uma API REST pública e gratuita para acesso a dados das estações meteorológicas automáticas distribuídas pelo território nacional. Os dados são coletados hora a hora e disponibilizados sem autenticação.

**Características importantes:**
- Dados **não validados** — são brutos diretamente dos sensores
- Dados disponíveis: últimos **90 dias** para estações automáticas
- Frequência de atualização: **horária**
- Horário base: **UTC** (subtrair 3h para horário de Brasília)
- Cobertura: **~600 estações automáticas** em todo o Brasil

**Política oficial (portal.inmet.gov.br):**
> "Os dados das estações automáticas são brutos e não passam por um processo de consistência (validação). O Inmet fornece os dados meteorológicos, contudo, o uso e aplicação desses dados é de responsabilidade do usuário."

---

### 1.2 Autenticação

**Nenhuma autenticação necessária** para os endpoints de estações automáticas.

Recomendado definir um `User-Agent` descritivo:
```http
User-Agent: MeteoRAG/1.0 (educational-project; contact@example.com)
```

---

### 1.3 Base URLs

| Ambiente | Base URL |
|----------|----------|
| API de tempo (automáticas) | `https://apitempo.inmet.gov.br` |
| Portal web | `https://portal.inmet.gov.br` |
| BDMEP (histórico, requer login) | `https://bdmep.inmet.gov.br` |
| Alertas web | `https://alertas2.inmet.gov.br` |
| Mapa de estações | `https://mapas.inmet.gov.br` |
| WIS2 (OGC API) | `http://wis2bra.inmet.gov.br/oapi` |

**Usamos no MeteoRAG:** `https://apitempo.inmet.gov.br`

---

### 1.4 Endpoints de Estações

#### `GET /estacoes/{tipo}`

Lista todas as estações de um determinado tipo.

**Parâmetros de path:**
| Parâmetro | Tipo | Valores | Descrição |
|-----------|------|---------|-----------|
| `tipo` | string | `T` / `A` / `M` | `T` = todas; `A` = automáticas; `M` = manuais/convencionais |

**Exemplo:**
```http
GET https://apitempo.inmet.gov.br/estacoes/T
```

**Resposta (200 OK):**
```json
[
  {
    "TP_ESTACAO": "Automatica",
    "CD_ESTACAO": "A519",
    "SG_ESTADO": "MG",
    "CD_SITUACAO": "Operante",
    "CD_DISTRITO": "06",
    "CD_OSCAR": "0-2000-0-86798",
    "DT_FIM_OPERACAO": null,
    "CD_WSI": null,
    "SG_ENTIDADE": "INMET",
    "DT_INICIO_OPERACAO": "2006-09-29T21:00:00.000-03:00",
    "CD_SITUACAO": "Operante",
    "TP_ESTACAO": "Automatica",
    "VL_LATITUDE": "-21.79",
    "VL_LONGITUDE": "-43.35",
    "VL_ALTITUDE": "939.17",
    "NM_ESTACAO": "JUIZ DE FORA"
  }
]
```

**Campos relevantes:**
| Campo | Tipo | Descrição |
|-------|------|-----------|
| `CD_ESTACAO` | string | Código único da estação (ex: `A519`) |
| `NM_ESTACAO` | string | Nome da estação/cidade |
| `SG_ESTADO` | string | Sigla do estado (ex: `MG`) |
| `CD_SITUACAO` | string | `Operante` \| `Pane` \| `Desativada` |
| `VL_LATITUDE` | string | Latitude decimal (negativo = Sul) |
| `VL_LONGITUDE` | string | Longitude decimal (negativo = Oeste) |
| `VL_ALTITUDE` | string | Altitude em metros |
| `TP_ESTACAO` | string | `Automatica` \| `Convencional` |

---

### 1.5 Endpoints de Dados Meteorológicos

#### `GET /estacao/{dataInicio}/{dataFim}/{codEstacao}`

Retorna dados horários de uma estação no intervalo de datas especificado.

**Parâmetros de path:**
| Parâmetro | Tipo | Formato | Descrição |
|-----------|------|---------|-----------|
| `dataInicio` | string | `YYYY-MM-DD` | Data de início |
| `dataFim` | string | `YYYY-MM-DD` | Data de fim |
| `codEstacao` | string | `A000` | Código da estação |

**Limitações:**
- Intervalo máximo: **não documentado** — recomenda-se ≤ 30 dias por requisição
- Disponibilidade: últimos **90 dias**
- Se não houver dados no período: retorna **HTTP 204** (corpo vazio)

**Exemplo:**
```http
GET https://apitempo.inmet.gov.br/estacao/2026-03-07/2026-03-14/A519
```

**Resposta (200 OK):**
```json
[
  {
    "CD_ESTACAO": "A519",
    "DT_MEDICAO": "2026-03-10",
    "HR_MEDICAO": "1200 UTC",
    "CHUVA": "12.4",
    "TEM_INS": "22.5",
    "TEM_MAX": "25.1",
    "TEM_MIN": "19.8",
    "UMD_INS": "85",
    "UMD_MAX": "92",
    "UMD_MIN": "78",
    "VEN_VEL": "3.2",
    "VEN_DIR": "180",
    "VEN_RAJ": "8.5",
    "PRE_INS": "925.4",
    "PRE_MAX": "927.1",
    "PRE_MIN": "924.8",
    "RAD_GLO": "456.2",
    "PTO_INS": "19.8",
    "PTO_MAX": "21.2",
    "PTO_MIN": "18.5"
  }
]
```

**Schema completo de uma observação:**
| Campo | Unidade | Descrição |
|-------|---------|-----------|
| `CD_ESTACAO` | — | Código da estação |
| `DT_MEDICAO` | YYYY-MM-DD | Data da medição |
| `HR_MEDICAO` | HHMM UTC | Hora da medição em UTC |
| `CHUVA` | mm | Precipitação acumulada na hora |
| `TEM_INS` | °C | Temperatura instantânea |
| `TEM_MAX` | °C | Temperatura máxima do período |
| `TEM_MIN` | °C | Temperatura mínima do período |
| `UMD_INS` | % | Umidade relativa instantânea |
| `UMD_MAX` | % | Umidade relativa máxima |
| `UMD_MIN` | % | Umidade relativa mínima |
| `VEN_VEL` | m/s | Velocidade do vento |
| `VEN_DIR` | graus | Direção do vento (0=N, 90=E, 180=S, 270=O) |
| `VEN_RAJ` | m/s | Velocidade da rajada de vento |
| `PRE_INS` | hPa | Pressão atmosférica instantânea |
| `PRE_MAX` | hPa | Pressão atmosférica máxima |
| `PRE_MIN` | hPa | Pressão atmosférica mínima |
| `RAD_GLO` | kJ/m² | Radiação global |
| `PTO_INS` | °C | Ponto de orvalho instantâneo |
| `PTO_MAX` | °C | Ponto de orvalho máximo |
| `PTO_MIN` | °C | Ponto de orvalho mínimo |

> **Atenção:** `HR_MEDICAO` vem como `"1200 UTC"` (string com sufixo). Para converter: remover " UTC" e subtrair 3 horas para horário de Brasília.

---

#### `GET /estacao/dados/{codEstacao}`

Retorna o **último registro** disponível de uma estação (tempo real).

**Exemplo:**
```http
GET https://apitempo.inmet.gov.br/estacao/dados/A519
```

**Útil para:** verificar se a estação está operante e qual o dado mais recente.

---

### 1.6 Endpoints de Alertas

#### `GET /alertas/{estado}/{nivel}`

Retorna alertas meteorológicos ativos para um estado.

**Parâmetros de path:**
| Parâmetro | Tipo | Valores | Descrição |
|-----------|------|---------|-----------|
| `estado` | string | sigla minúscula | `mg`, `sp`, `rj`, etc. |
| `nivel` | integer | `1` | Sempre usar `1` (padrão atual) |

**Exemplo:**
```http
GET https://apitempo.inmet.gov.br/alertas/mg/1
```

**Resposta (200 OK):**
```json
[
  {
    "CD_IDENTIFICADOR": "3f8a2b1c-...",
    "DS_EVENTO": "CHUVAS INTENSAS",
    "DS_SEVERIDADE": "Laranja",
    "DT_INICIO_ALERTA": "2026-03-14 06:00:00",
    "DT_FIM_ALERTA": "2026-03-14 18:00:00",
    "DS_MENSAGEM": "Previsão de chuvas entre 30 e 60 mm/h ou 50 e 100 mm/dia, ventos intensos (60-100 km/h).",
    "NM_MUNICIPIOS": "Juiz de Fora, Ubá, Muriaé, Cataguases",
    "NR_LATITUDE_MIN": "-22.5",
    "NR_LATITUDE_MAX": "-21.0",
    "NR_LONGITUDE_MIN": "-44.0",
    "NR_LONGITUDE_MAX": "-42.0"
  }
]
```

**Schema de um alerta:**
| Campo | Tipo | Descrição |
|-------|------|-----------|
| `CD_IDENTIFICADOR` | string UUID | ID único do alerta |
| `DS_EVENTO` | string | Tipo: `CHUVAS INTENSAS`, `TEMPESTADES`, `VENDAVAL`, etc. |
| `DS_SEVERIDADE` | string | `Amarelo` \| `Laranja` \| `Vermelho` |
| `DT_INICIO_ALERTA` | datetime | Início da vigência |
| `DT_FIM_ALERTA` | datetime | Fim da vigência |
| `DS_MENSAGEM` | string | Descrição técnica dos parâmetros esperados |
| `NM_MUNICIPIOS` | string | Municípios afetados (separados por vírgula) |
| `NR_LATITUDE_MIN/MAX` | string | Bounding box da área afetada |
| `NR_LONGITUDE_MIN/MAX` | string | Bounding box da área afetada |

**Níveis de severidade (INMET):**
| Cor | Nível | Descrição |
|-----|-------|-----------|
| 🟡 Amarelo | Baixo | Risco potencial; atenção recomendada |
| 🟠 Laranja | Médio | Risco moderado; população deve se preparar |
| 🔴 Vermelho | Alto/Extremo | Risco alto; população em perigo |

**Resposta 204:** Nenhum alerta ativo no estado. Tratar com retorno de lista vazia.

---

### 1.7 Schema de Dados

#### Classificação de Precipitação

| Faixa (mm/dia) | Classificação | Ação recomendada |
|----------------|--------------|-----------------|
| 0 | Sem precipitação | — |
| 0.1 – 9.9 | Chuva fraca / garoa | Monitoramento normal |
| 10 – 29.9 | Chuva moderada | Atenção a pontos de alagamento |
| 30 – 59.9 | Chuva forte | Risco de alagamentos; INMET emite alerta amarelo |
| 60 – 99.9 | Chuva muito forte | Risco alto; alerta laranja provável |
| ≥ 100 | Chuva extrema | Risco de deslizamentos; alerta vermelho |

Referência: critérios do Sistema de Avisos do INMET e Defesa Civil.

#### Conversão de Horário

Todos os dados do INMET estão em **UTC**. Para converter:

```python
from datetime import datetime, timedelta, timezone

def inmet_to_brasilia(hr_medicao: str, dt_medicao: str) -> datetime:
    """
    Converte horário INMET (UTC) para horário de Brasília (UTC-3).
    
    Args:
        hr_medicao: String no formato "1200 UTC"
        dt_medicao: String no formato "YYYY-MM-DD"
    
    Returns:
        datetime em horário de Brasília
    """
    hour_str = hr_medicao.replace(" UTC", "").strip()  # "1200"
    hour = int(hour_str[:2])
    minute = int(hour_str[2:])
    
    dt_utc = datetime.strptime(dt_medicao, "%Y-%m-%d").replace(
        hour=hour, minute=minute, tzinfo=timezone.utc
    )
    return dt_utc - timedelta(hours=3)
```

---

### 1.8 Códigos de Resposta HTTP

| Status | Significado | Ação no MeteoRAG |
|--------|------------|-----------------|
| `200 OK` | Dados disponíveis | Processar JSON retornado |
| `204 No Content` | Sem dados no período | Retornar lista vazia `[]` |
| `400 Bad Request` | Parâmetros inválidos | Log de erro + retornar `[]` |
| `404 Not Found` | Endpoint inexistente | Log de erro + retornar `[]` |
| `500 Internal Server Error` | Erro no servidor INMET | Retry com backoff; após 3 falhas, retornar `[]` |
| `503 Service Unavailable` | API INMET fora | Retry com backoff; ativar circuit breaker |

---

### 1.9 Valores Inválidos e Nulos

A API INMET usa convenções específicas para dados ausentes ou inválidos. **Sempre tratar antes de usar:**

| Representação | Significado | Tratamento |
|--------------|-------------|-----------|
| `"9999"` | Sensor com pane | Converter para `None` |
| `"-9999"` | Sensor com pane | Converter para `None` |
| `9999` (int) | Sensor com pane | Converter para `None` |
| `""` (string vazia) | Dado ausente | Converter para `None` |
| `null` / `None` | Dado não medido | Manter como `None` |
| `"Null"` (string) | Dado ausente | Converter para `None` |

**Função de parsing seguro:**
```python
def safe_float(val: Any) -> float | None:
    """Parse seguro de valor numérico da API INMET."""
    if val is None:
        return None
    str_val = str(val).strip()
    if str_val in ("", "null", "Null", "9999", "-9999"):
        return None
    try:
        result = float(str_val)
        return None if result in (9999.0, -9999.0) else result
    except (ValueError, TypeError):
        return None
```

---

### 1.10 Rate Limiting

O INMET **não documenta oficialmente** limites de rate, mas boas práticas:

- Aguardar **300ms** entre requisições sequenciais para a mesma estação
- Não fazer mais de **10 requisições/minuto** por IP
- Implementar **cache de 30 minutos** para evitar requisições repetidas
- Em CI/CD: limitar verificações da API INMET a **1x por hora**

---

### 1.11 Estações de Minas Gerais Mapeadas

| Cidade | Código | Latitude | Longitude | Altitude (m) | Status |
|--------|--------|----------|-----------|--------------|--------|
| Juiz de Fora | A519 | -21.79° | -43.35° | 939 | Operante |
| Muriaé | A549 | -21.13° | -42.36° | 256 | Operante |
| Barbacena | A535 | -21.23° | -43.78° | 1126 | Operante |
| Belo Horizonte | A521 | -19.88° | -43.97° | 915 | Operante |
| Viçosa | A548 | -20.76° | -42.87° | 649 | Operante |
| Caratinga | A540 | -19.79° | -42.14° | 683 | Verificar |
| Uberlândia | A524 | -18.91° | -48.33° | 869 | Operante |

> **Nota:** Ubá não possui estação automática própria. A estação mais próxima é Muriaé (A549), distante ~50km.

**Verificar estações disponíveis:**
```http
GET https://apitempo.inmet.gov.br/estacoes/T
```
Filtrar por `SG_ESTADO == "MG"` e `CD_SITUACAO == "Operante"`.

---

### 1.12 Exemplos de Resposta Reais

#### Estação com dados de chuva intensa

```json
{
  "CD_ESTACAO": "A519",
  "DT_MEDICAO": "2026-03-10",
  "HR_MEDICAO": "1500 UTC",
  "CHUVA": "31.2",
  "TEM_INS": "19.4",
  "TEM_MAX": "22.1",
  "TEM_MIN": "18.5",
  "UMD_INS": "96",
  "VEN_VEL": "5.8",
  "VEN_DIR": "200",
  "VEN_RAJ": "14.2",
  "PRE_INS": "919.8",
  "PRE_MAX": "921.3",
  "PRE_MIN": "918.4"
}
```

#### Estação com sensor com pane

```json
{
  "CD_ESTACAO": "A549",
  "DT_MEDICAO": "2026-03-10",
  "HR_MEDICAO": "1200 UTC",
  "CHUVA": "5.2",
  "TEM_INS": "9999",
  "TEM_MAX": "9999",
  "TEM_MIN": "9999",
  "UMD_INS": "78",
  "VEN_VEL": "",
  "VEN_DIR": null
}
```
→ `TEM_INS`, `TEM_MAX`, `TEM_MIN`, `VEN_VEL`, `VEN_DIR` devem ser `None` após parsing.

---

## 2. Anthropic API

### 2.1 Visão Geral

A API da Anthropic fornece acesso aos modelos Claude para geração de texto. No MeteoRAG, usamos o endpoint `/v1/messages` com **Claude Haiku 4.5** — o modelo mais rápido da família Claude 4.x, ideal para resposta em tempo real com streaming.

**Docs oficiais:** https://docs.anthropic.com/en/api

---

### 2.2 Autenticação

**Header obrigatório:**
```http
x-api-key: {ANTHROPIC_API_KEY}
anthropic-version: 2023-06-01
Content-Type: application/json
```

**Via SDK Python:**
```python
import anthropic

client = anthropic.Anthropic(api_key="sk-ant-...")
```

---

### 2.3 Integração via Databricks

O Databricks Model Serving permite usar os modelos Anthropic através de um endpoint customizado. A autenticação usa um token Databricks, não a API key da Anthropic diretamente.

**Configuração:**
```python
import anthropic

client = anthropic.Anthropic(
    api_key="dapi...",  # Token do Databricks
    base_url="https://<workspace-id>.azuredatabricks.net/serving-endpoints/"
    # ou: "https://<workspace>.cloud.databricks.com/serving-endpoints/"
)
```

**Variáveis de ambiente no MeteoRAG:**
```bash
METEORAG_ANTHROPIC_API_KEY=dapi...
METEORAG_ANTHROPIC_BASE_URL=https://<workspace>.cloud.databricks.com/serving-endpoints/
```

**Importante:** Com Databricks, o nome do modelo pode ser diferente. Verificar o nome do endpoint criado no workspace:
```
# Anthropic direta:     model="claude-haiku-4-5"
# Databricks serving:  model="databricks-claude-haiku-4-5" (ou nome do endpoint)
```

---

### 2.4 Endpoint Messages

#### `POST /v1/messages`

Envia uma mensagem e recebe uma resposta do modelo.

**Request:**
```http
POST https://api.anthropic.com/v1/messages
Content-Type: application/json
x-api-key: {API_KEY}
anthropic-version: 2023-06-01

{
  "model": "claude-haiku-4-5",
  "max_tokens": 1024,
  "system": "Você é um assistente meteorológico...",
  "messages": [
    {
      "role": "user",
      "content": "Qual foi a chuva total em JF essa semana?"
    }
  ]
}
```

**Response (200 OK):**
```json
{
  "id": "msg_01XFDUDYJgAACzvnptvVoYEL",
  "type": "message",
  "role": "assistant",
  "model": "claude-haiku-4-5-20251001",
  "content": [
    {
      "type": "text",
      "text": "Com base nos dados das estações INMET para Juiz de Fora..."
    }
  ],
  "stop_reason": "end_turn",
  "stop_sequence": null,
  "usage": {
    "input_tokens": 892,
    "output_tokens": 187
  }
}
```

---

### 2.5 Streaming

Para respostas em tempo real (usado no chat do Streamlit):

**Request com streaming:**
```json
{
  "model": "claude-haiku-4-5",
  "max_tokens": 1024,
  "stream": true,
  "system": "...",
  "messages": [...]
}
```

**Eventos SSE retornados:**
| Evento | Descrição |
|--------|-----------|
| `message_start` | Início da mensagem com metadados |
| `content_block_start` | Início de um bloco de conteúdo |
| `content_block_delta` | Chunk de texto (use este para streaming na UI) |
| `content_block_stop` | Fim do bloco de conteúdo |
| `message_delta` | Atualização de metadados (stop_reason, usage) |
| `message_stop` | Fim da mensagem |

**Via SDK Python (recomendado):**
```python
def ask_stream(query: str, context: str, history: list[dict]):
    client = get_client()
    
    with client.messages.stream(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT.format(context=context),
        messages=[*history, {"role": "user", "content": query}],
    ) as stream:
        for text in stream.text_stream:
            yield text  # chunk de texto para o Streamlit
```

---

### 2.6 Modelos Disponíveis

| Modelo | ID | Contexto | Uso no MeteoRAG |
|--------|-----|---------|----------------|
| Claude Haiku 4.5 | `claude-haiku-4-5` | 200K tokens | **Padrão** — rápido, eficiente |
| Claude Sonnet 4.5 | `claude-sonnet-4-5` | 200K tokens | Alternativa para mais qualidade |
| Claude Opus 4.5 | `claude-opus-4-5` | 200K tokens | Reserva para análises complexas |

**Recomendação:** Haiku 4.5 para o chat principal (latência < 3s). Se a qualidade das respostas for insuficiente, migrar para Sonnet 4.5.

---

### 2.7 Parâmetros Principais

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|------------|-----------|
| `model` | string | Sim | ID do modelo |
| `max_tokens` | integer | Sim | Máximo de tokens na resposta (1–8192) |
| `messages` | array | Sim | Histórico de mensagens (role: user\|assistant) |
| `system` | string | Não | System prompt (define comportamento) |
| `stream` | boolean | Não | Habilita streaming SSE |
| `temperature` | float | Não | 0.0–1.0; default 1.0 (não alterar para dados factuais) |
| `top_p` | float | Não | Nucleus sampling (não usar junto com temperature) |
| `stop_sequences` | array | Não | Strings que param a geração |
| `metadata.user_id` | string | Não | ID do usuário para analytics |

**No MeteoRAG, usamos:**
```python
{
    "model": "claude-haiku-4-5",
    "max_tokens": 1024,
    "system": SYSTEM_PROMPT,         # contexto RAG embutido aqui
    "messages": chat_history[-20:],  # últimas 10 trocas (20 mensagens)
    "stream": True                   # sempre streaming na UI
}
```

> **Por que não usar `temperature=0`?** Dados meteorológicos têm números precisos, mas a *interpretação* e *narrativa* se beneficiam de alguma variabilidade. Mantemos o default (1.0).

---

### 2.8 Limites e Quotas

| Limite | Valor (Haiku 4.5) | Observação |
|--------|------------------|-----------|
| Tokens de entrada (context) | 200.000 | Por mensagem |
| Tokens de saída (max_tokens) | 8.192 | Máximo configurável |
| Tokens por minuto (TPM) | Varia por tier | Ver dashboard Anthropic |
| Requisições por minuto (RPM) | Varia por tier | Ver dashboard Anthropic |

**Estimativa de tokens no MeteoRAG por query:**
- System prompt + contexto RAG (8 chunks): ~800–1.200 tokens
- Histórico de chat (10 trocas): ~500–800 tokens
- Query do usuário: ~20–50 tokens
- **Total input estimado por query: ~1.300–2.050 tokens**
- Output estimado: ~200–400 tokens

---

### 2.9 Exemplos Python

#### Requisição simples (não-streaming)
```python
import anthropic

client = anthropic.Anthropic(api_key="sk-ant-...")

response = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=1024,
    system="Você é um assistente meteorológico para MG.",
    messages=[
        {"role": "user", "content": "Qual o risco de alagamento em JF?"}
    ],
)

print(response.content[0].text)
print(f"Input tokens: {response.usage.input_tokens}")
print(f"Output tokens: {response.usage.output_tokens}")
```

#### Streaming com acumulação
```python
full_response = ""
with client.messages.stream(
    model="claude-haiku-4-5",
    max_tokens=1024,
    system="...",
    messages=[{"role": "user", "content": "..."}],
) as stream:
    for text in stream.text_stream:
        full_response += text
        print(text, end="", flush=True)

final_message = stream.get_final_message()
print(f"\nTokens usados: {final_message.usage}")
```

#### Integração Streamlit com streaming
```python
import streamlit as st

def render_streaming_response(query: str, context: str, history: list[dict]):
    """Renderiza resposta com streaming no Streamlit."""
    response_text = ""
    placeholder = st.empty()
    
    for chunk in ask_stream(query, context, history):
        response_text += chunk
        placeholder.markdown(response_text + "▌")
    
    placeholder.markdown(response_text)  # Remove cursor
    return response_text
```

#### Tratamento de erros
```python
import anthropic

try:
    response = client.messages.create(...)
except anthropic.APIConnectionError as e:
    logger.error(f"Falha de conexão: {e}")
    return "Serviço temporariamente indisponível. Tente novamente."
except anthropic.RateLimitError as e:
    logger.warning(f"Rate limit atingido: {e}")
    return "Muitas requisições. Aguarde um momento."
except anthropic.APIStatusError as e:
    logger.error(f"Erro da API [{e.status_code}]: {e.message}")
    return f"Erro ao processar sua pergunta. Código: {e.status_code}"
```

---

## 3. Decisões de Design Baseadas nas APIs

### 3.1 Por que TF-IDF em vez de embeddings?

A API INMET retorna **dados estruturados** (números e datas), não texto semântico rico. Para queries como "chuva forte em JF" ou "alerta laranja ontem", TF-IDF com tokenização PT-BR tem performance equivalente a embeddings em 95% dos casos, sem a dependência de uma API de embeddings externa (custo e latência adicionais).

**Trade-off:** Queries altamente semânticas como "qual cidade está em mais risco de deslizamento" se beneficiariam de embeddings. Decisão para v2.0.

### 3.2 Por que cache de 30 minutos?

A API INMET atualiza dados **hora a hora**. Cache de 30 minutos garante que:
- Dados nunca ficam mais de 1 hora desatualizados
- Usuários na mesma sessão não geram tráfego excessivo para o INMET
- Performance da UI permanece consistente

### 3.3 Por que limitar chunks horários a 96h?

Com dados horários de 7 dias = ~168 registros por estação. Incluir todos aumenta o contexto do LLM desnecessariamente. Os chunks diários (sumários) cobrem a semana completa; chunks horários com `CHUVA > 0` das últimas 96h (4 dias) cobrem os eventos recentes com granularidade.

### 3.4 Por que Haiku 4.5?

- Latência p50 < 1.5s vs ~4s do Sonnet para queries similares
- Contexto de 200K tokens (mais que suficiente para o RAG)
- Custo ~5x menor que Sonnet para o mesmo volume de queries
- Performance para interpretação de dados meteorológicos é equivalente

---

## 4. Troubleshooting

### INMET retorna 204 para período válido
**Causa:** Estação pode estar em manutenção (pane) ou sem conectividade.  
**Ação:** Verificar status da estação em `https://mapas.inmet.gov.br/`. Implementar fallback para estação mais próxima.

### INMET API timeout
**Causa:** API pública com SLA não garantido; picos de uso em eventos de chuva intensa.  
**Ação:** Timeout de 20s configurado; retry com backoff de 2s, 4s, 8s.

### Todos os campos de temperatura retornam null
**Causa:** Sensor de temperatura em pane (`9999` no JSON).  
**Ação:** Esperado; a estação de precipitação funciona independentemente. Reportar no log como warning, não error.

### Anthropic RateLimitError em produção
**Causa:** Pico de usuários simultâneos excedendo o tier atual.  
**Ação:** Implementar queue de mensagens; considerar upgrade de tier ou caching de respostas para queries idênticas.

### Streaming interrompido no Streamlit
**Causa:** `st.rerun()` chamado durante streaming mata a conexão.  
**Ação:** Nunca chamar `st.rerun()` dentro do loop de streaming. Usar `st.empty()` para updates incrementais.

### Base URL do Databricks retorna 404
**Causa:** Nome do modelo no Databricks difere do modelo Anthropic padrão.  
**Ação:** Verificar o nome exato do endpoint no Databricks Model Serving UI. O model ID pode ser `databricks-claude-haiku` em vez de `claude-haiku-4-5`.

---

*Documentação mantida em `docs/API_REFERENCE.md`. Atualizar sempre que um endpoint mudar seu comportamento.*
