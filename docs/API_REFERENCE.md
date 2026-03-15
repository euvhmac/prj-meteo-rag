# MeteoRAG — API Reference

> Referência das APIs externas utilizadas pelo projeto.

---

## Open-Meteo — Fonte Principal de Dados

Base URL: `https://api.open-meteo.com/v1`

API pública, gratuita para uso não-comercial, sem autenticação necessária.
Dados baseados em reanálise **ERA5** (histórico) e previsão **GFS** (futuro).

### Forecast API

```
GET /forecast?latitude={lat}&longitude={lon}&hourly={vars}&daily={vars}&current={vars}&past_days={n}&forecast_days=1&timezone=America/Sao_Paulo
```

**Parâmetros:**

| Parâmetro | Tipo | Exemplo | Descrição |
|-----------|------|---------|-----------|
| `latitude` | float | -21.7609 | Latitude do ponto |
| `longitude` | float | -43.3496 | Longitude do ponto |
| `hourly` | string | precipitation,temperature_2m | Variáveis horárias (separadas por vírgula) |
| `daily` | string | precipitation_sum,temperature_2m_max | Variáveis diárias |
| `current` | string | precipitation,temperature_2m | Variáveis atuais |
| `past_days` | int | 7 | Dias retroativos (max: 92) |
| `forecast_days` | int | 1 | Dias de previsão (max: 16) |
| `timezone` | string | America/Sao_Paulo | Fuso horário para timestamps |

**Variáveis Horárias Utilizadas:**

| Variável | Unidade | Descrição |
|----------|---------|-----------|
| `precipitation` | mm | Precipitação na última hora |
| `temperature_2m` | °C | Temperatura a 2 metros |
| `relative_humidity_2m` | % | Umidade relativa a 2 metros |
| `wind_speed_10m` | km/h | Velocidade do vento a 10m (convertido para m/s no app) |
| `wind_direction_10m` | ° | Direção do vento a 10 metros |
| `surface_pressure` | hPa | Pressão atmosférica na superfície |
| `weather_code` | WMO code | Código de condição meteorológica (ISO 4677) |

**Variáveis Diárias Utilizadas:**

| Variável | Unidade | Descrição |
|----------|---------|-----------|
| `precipitation_sum` | mm | Precipitação total do dia |
| `precipitation_hours` | h | Horas com precipitação |
| `temperature_2m_max` | °C | Temperatura máxima do dia |
| `temperature_2m_min` | °C | Temperatura mínima do dia |
| `wind_speed_10m_max` | km/h | Velocidade máxima do vento |
| `weather_code` | WMO code | Condição predominante do dia |

**Variáveis Current:**

| Variável | Unidade | Descrição |
|----------|---------|-----------|
| `precipitation` | mm | Precipitação atual |
| `temperature_2m` | °C | Temperatura atual |
| `relative_humidity_2m` | % | Umidade atual |
| `wind_speed_10m` | km/h | Velocidade do vento atual |
| `weather_code` | WMO code | Condição atual |
| `surface_pressure` | hPa | Pressão atual |

**Códigos WMO (ISO 4677):**

| Código | Descrição |
|--------|-----------|
| 0 | Céu limpo |
| 1-3 | Majoritariamente limpo a nublado |
| 45, 48 | Neblina |
| 51-55 | Garoa (fraca a intensa) |
| 61-65 | Chuva (fraca a forte) |
| 66-67 | Chuva congelante |
| 80-82 | Pancadas (fracas a violentas) |
| 95-99 | Trovoada (com possível granizo) |

**Exemplo de resposta (simplificada):**

```json
{
  "latitude": -21.75,
  "longitude": -43.375,
  "timezone": "America/Sao_Paulo",
  "current": {
    "time": "2024-01-18T14:00",
    "precipitation": 0.0,
    "temperature_2m": 25.3,
    "weather_code": 2
  },
  "hourly": {
    "time": ["2024-01-15T00:00", "2024-01-15T01:00"],
    "precipitation": [0.0, 2.4],
    "temperature_2m": [19.5, 19.0]
  },
  "daily": {
    "time": ["2024-01-15"],
    "precipitation_sum": [18.0],
    "temperature_2m_max": [24.5],
    "temperature_2m_min": [19.0]
  }
}
```

> **Referência completa:** [open-meteo.com/en/docs](https://open-meteo.com/en/docs)

---

## INMET — Alertas Meteorológicos (Best-Effort)

Base URL: `https://apitempo.inmet.gov.br`

> **Nota:** A API INMET é usada apenas para alertas meteorológicos (best-effort).
> Dados de estações automáticas foram substituídos pelo Open-Meteo na Sprint 2
> devido a instabilidade crônica da API. O cliente INMET implementa circuit breaker
> e cache offline para resiliência.

### Alertas Ativos

```
GET /alertas/ativos
```

**Resposta:** HTTP 200 com lista de alertas ou HTTP 204 (sem alertas vigentes).

**Campos relevantes:**

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `descricao` | string | Descrição do alerta |
| `severidade` | string | Nível de severidade (Observação, Perigo Potencial, Perigo, Grande Perigo) |
| `inicio` | string | Início da vigência (ISO datetime) |
| `fim` | string | Fim da vigência (ISO datetime) |
| `evento` | string | Tipo do evento (Chuvas Intensas, Tempestade, etc) |
| `municipios` | string | Lista de municípios afetados |
| `estado` | string | UF do alerta |

### Listar Estações Automáticas (legado)

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

### Dados Horários por Estação (legado)

```
GET /estacao/{data_inicio}/{data_fim}/{codigo_estacao}
```

**Parâmetros:**

| Parâmetro | Formato | Exemplo |
|-----------|---------|---------|
| `data_inicio` | YYYY-MM-DD | 2024-01-01 |
| `data_fim` | YYYY-MM-DD | 2024-01-07 |
| `codigo_estacao` | string | A518 |

**Valores especiais (sentinela):**
- `null`, `""`, `9999`, `-9999` → dado indisponível

---

## Cidades Monitoradas (Open-Meteo)

| Cidade | Latitude | Longitude | Altitude | Região |
|--------|----------|-----------|----------|--------|
| Juiz de Fora | -21.7609 | -43.3496 | 939m | Zona da Mata |
| Ubá | -21.1183 | -42.9404 | 251m | Zona da Mata |
| Barbacena | -21.2258 | -43.7736 | 1126m | Campo das Vertentes |
| Muriaé | -21.1322 | -42.3670 | 256m | Zona da Mata |
| Viçosa | -20.7546 | -42.8825 | 649m | Zona da Mata |
| Cataguases | -21.3917 | -42.6961 | 215m | Zona da Mata |
| Belo Horizonte | -19.9167 | -43.9345 | 915m | Metropolitana |

## Estações INMET Legadas (Zona da Mata MG)

| Cidade | Código | Nome Estação |
|--------|--------|-------------|
| Juiz de Fora | A518 | JUIZ DE FORA |
| Barbacena | A519 | BARBACENA |
| Viçosa | A520 | VIÇOSA |
| Belo Horizonte | A521 | BELO HORIZONTE |
| Caratinga | A527 | CARATINGA |
| Muriaé | A555 | MURIAÉ |

> **Nota:** Estações INMET mantidas apenas para referência. Dados meteorológicos agora vêm do Open-Meteo.
