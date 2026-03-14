# MeteoRAG — API Reference

> Referência das APIs externas utilizadas pelo projeto.

## INMET — Instituto Nacional de Meteorologia

Base URL: `https://apitempo.inmet.gov.br`

### Listar Estações Automáticas

```
GET /estacoes/T
```

Retorna lista de todas as estações automáticas do Brasil.

**Campos relevantes:**
| Campo | Tipo | Descrição |
|-------|------|-----------|
| `CD_ESTACAO` | string | Código identificador da estação |
| `DC_NOME` | string | Nome da estação |
| `SG_ESTADO` | string | Sigla do estado (ex: MG) |
| `VL_LATITUDE` | string | Latitude |
| `VL_LONGITUDE` | string | Longitude |
| `VL_ALTITUDE` | string | Altitude em metros |
| `DT_INICIO_OPERACAO` | string | Data início operação |

### Dados Horários por Estação

```
GET /estacao/{data_inicio}/{data_fim}/{codigo_estacao}
```

**Parâmetros:**
| Parâmetro | Formato | Exemplo |
|-----------|---------|---------|
| `data_inicio` | YYYY-MM-DD | 2024-01-01 |
| `data_fim` | YYYY-MM-DD | 2024-01-07 |
| `codigo_estacao` | string | A518 |

**Campos de resposta relevantes:**
| Campo | Tipo | Unidade | Descrição |
|-------|------|---------|-----------|
| `DT_MEDICAO` | string | YYYY-MM-DD | Data da medição |
| `HR_MEDICAO` | string | HHmm UTC | Hora da medição |
| `CHUVA` | string/null | mm | Precipitação na última hora |
| `TEM_INS` | string/null | °C | Temperatura instantânea |
| `TEM_MAX` | string/null | °C | Temperatura máxima |
| `TEM_MIN` | string/null | °C | Temperatura mínima |
| `UMD_INS` | string/null | % | Umidade relativa instantânea |
| `VEN_VEL` | string/null | m/s | Velocidade do vento |
| `VEN_DIR` | string/null | graus | Direção do vento |
| `PRE_INS` | string/null | hPa | Pressão instantânea |
| `RAD_GLO` | string/null | kJ/m² | Radiação global |

**Valores especiais:**
- `null`, `""`, `9999`, `-9999` → dado indisponível

### Alertas Meteorológicos

```
GET /alertas/{estado}/1
```

**Parâmetros:**
| Parâmetro | Exemplo | Descrição |
|-----------|---------|-----------|
| `estado` | MG | Sigla do estado |

**Resposta:** HTTP 200 com lista de alertas ou HTTP 204 (sem alertas vigentes).

**Campos relevantes:**
| Campo | Tipo | Descrição |
|-------|------|-----------|
| `descricao` | string | Descrição do alerta |
| `severidade` | string | Nível de severidade |
| `inicio` | string | Início da vigência |
| `fim` | string | Fim da vigência |
| `evento` | string | Tipo do evento (chuvas intensas, etc) |
| `municipios` | string | Lista de municípios afetados |

---

## Estações Prioritárias (Zona da Mata MG)

| Cidade | Código | Nome Estação |
|--------|--------|-------------|
| Juiz de Fora | A518 | JUIZ DE FORA |
| Barbacena | A519 | BARBACENA |
| Viçosa | A520 | VIÇOSA |
| Ubá / Muriaé | A553 | CAPARAO |
| Belo Horizonte | A521 | BELO HORIZONTE |

> **Nota:** Códigos sujeitos a verificação na API `/estacoes/T`.
