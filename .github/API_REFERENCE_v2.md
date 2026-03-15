# MeteoRAG — API Reference

**Versão:** 2.0  
**Atualizado:** Março 2026  
**Status das fontes:**
- ✅ **Open-Meteo** — fonte principal (operacional, sem auth, sem delay)
- 🟡 **INMET** — fonte secundária para alertas (instável, best-effort)

> Documento técnico completo de todas as APIs externas do projeto.  
> Leia antes de implementar qualquer integração ou alterar o `weather_client.py`.

---

## Índice

1. [Estratégia de Fontes](#1-estratégia-de-fontes)
2. [Open-Meteo — Fonte Principal](#2-open-meteo--fonte-principal)
3. [INMET — Fonte Secundária](#3-inmet--fonte-secundária-alertas)
4. [Anthropic API](#4-anthropic-api)
5. [Decisões de Design](#5-decisões-de-design)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. Estratégia de Fontes

```
┌─────────────────────────────────────────────────────────────┐
│                     MeteoRAG Data Sources                   │
├──────────────────────────┬──────────────────────────────────┤
│  DADOS METEOROLÓGICOS    │  Open-Meteo (PRINCIPAL)          │
│  • Últimos 7 dias        │  Forecast API + past_days=N      │
│  • Histórico > 7 dias    │  Archive API (ERA5/ECMWF IFS)    │
│  • Previsão 7–16 dias    │  Forecast API + forecast_days=N  │
│  • Condição atual        │  Forecast API + current=...      │
├──────────────────────────┬──────────────────────────────────┤
│  ALERTAS OFICIAIS        │  INMET (SECUNDÁRIO / best-effort)│
│  • Alertas amarelo/      │  /alertas/{estado}/1             │
│    laranja/vermelho      │  → retorna [] se indisponível    │
└──────────────────────────┴──────────────────────────────────┘
```

**Diagnóstico INMET (março/2026):** Testado contra 14 dias de histórico — todos os endpoints de dados retornam HTTP 204. Alertas também fora. Causa não documentada pelo INMET. Mantido no projeto exclusivamente para quando os alertas voltarem.

| Critério | Open-Meteo | INMET |
|----------|-----------|-------|
| Disponibilidade (mar/2026) | ✅ 100% operacional | ❌ indisponível |
| Delay de dados | ✅ Zero (atualiza 1x/hora) | ❌ 5–14 dias confirmado |
| Autenticação | ✅ Nenhuma | ✅ Nenhuma |
| Cobertura | ✅ Qualquer lat/lon no Brasil | ❌ Apenas ~600 cidades com estação |
| Rate limit | ✅ 10.000 req/dia documentado | ❌ Não documentado |
| SLA | ✅ Multi-region GeoDNS | ❌ Servidor único |
| Histórico | ✅ Desde 1940 | ⚠️ 90 dias (quando ativo) |
| Alertas oficiais | ❌ Não disponível | ✅ Fonte oficial brasileira |

---

## 2. Open-Meteo — Fonte Principal

### 2.1 Visão Geral

Open-Meteo é uma API meteorológica open-source que agrega dados de múltiplos serviços nacionais (NOAA, ECMWF, DWD, UK Met Office, JMA, etc.). Sem registro, sem API key, sem cartão para uso não-comercial.

- **Licença de dados:** CC BY 4.0 — atribuição obrigatória
- **Código-fonte:** https://github.com/open-meteo/open-meteo
- **Status operacional:** https://status.open-meteo.com
- **Documentação oficial:** https://open-meteo.com/en/docs

### 2.2 Autenticação & Limites

```
Uso não-comercial: sem auth, sem header, chamada direta.
Limite oficial: 10.000 requisições/dia por IP.
Fair use: não fazer burst de centenas de requests simultâneos.

Uso comercial (>10k req/dia):
  Requer plano pago + prefixo customer- na URL base:
  https://customer-api.open-meteo.com/v1/forecast?apikey=SUA_KEY
```

Header recomendado (boa prática, não obrigatório):
```
User-Agent: MeteoRAG/1.0 (open-source educational project)
```

### 2.3 URLs Base

| API | URL Base | Uso |
|-----|----------|-----|
| **Forecast** | `https://api.open-meteo.com/v1/forecast` | Dados recentes + previsão |
| **Archive** | `https://archive-api.open-meteo.com/v1/archive` | Histórico ERA5/ECMWF desde 1940 |
| **Geocoding** | `https://geocoding-api.open-meteo.com/v1/search` | Cidade → lat/lon |
| **Elevation** | `https://api.open-meteo.com/v1/elevation` | Altitude por coordenada |
| **Air Quality** | `https://air-quality-api.open-meteo.com/v1/air-quality` | Qualidade do ar (futuro) |
| **Flood** | `https://flood-api.open-meteo.com/v1/flood` | Previsão de cheias (futuro) |

### 2.4 Parâmetros Comuns a Todos os Endpoints

| Parâmetro | Tipo | Obrigatório | Default | Descrição |
|-----------|------|:-----------:|---------|-----------|
| `latitude` | float | ✅ | — | Latitude WGS84. Ex: `-21.7609` |
| `longitude` | float | ✅ | — | Longitude WGS84. Ex: `-43.3496` |
| `timezone` | string | ⚠️ Recomendado | `GMT` | TZ database name. **Sempre usar `America/Sao_Paulo` para MG** |
| `temperature_unit` | string | | `celsius` | `celsius` ou `fahrenheit` |
| `wind_speed_unit` | string | | `kmh` | `kmh`, `ms`, `mph`, `kn` |
| `precipitation_unit` | string | | `mm` | `mm` ou `inch` |
| `timeformat` | string | | `iso8601` | `iso8601` ou `unixtime` |
| `cell_selection` | string | | `land` | `land`, `sea`, `nearest` — usar `land` para evitar grid cell sobre oceano |
| `format` | string | | `json` | `json`, `csv`, `xlsx` |

> **Sobre timezone:** Sem este parâmetro, todos os timestamps vêm em UTC. Com `America/Sao_Paulo`, vêm em UTC-3 com horário de verão automático. A omissão causa timestamps errados nos chunks RAG.

---

### 2.5 Forecast API — Dados Recentes + Previsão

**URL:** `GET https://api.open-meteo.com/v1/forecast`

Endpoint principal do MeteoRAG. Cobre:
- Dados históricos recentes via `past_days` (sem delay — usa archives de model runs inicializados com observações reais)
- Previsão para até 16 dias via `forecast_days`
- Condição instantânea via `current` (resolução 15 min)

#### Parâmetros Específicos

| Parâmetro | Tipo | Default | Descrição |
|-----------|------|---------|-----------|
| `past_days` | int | `0` | Dias passados a incluir (0–92). Dados de model archives, sem delay. |
| `forecast_days` | int | `7` | Dias futuros (1–16) |
| `past_hours` | int | — | Alternativa em horas (0–2208) |
| `forecast_hours` | int | — | Horas futuras (0–240) |
| `start_date` / `end_date` | string | — | Intervalo explícito `YYYY-MM-DD` (alternativa a past/forecast days) |
| `hourly` | string | — | Variáveis horárias, separadas por vírgula |
| `daily` | string | — | Variáveis diárias, separadas por vírgula |
| `current` | string | — | Variáveis para condição atual |
| `models` | string | `best_match` | Modelo específico (ver seção 2.14) |

#### URL Canônica do MeteoRAG

```
GET https://api.open-meteo.com/v1/forecast
  ?latitude=-21.7609
  &longitude=-43.3496
  &hourly=precipitation,temperature_2m,relative_humidity_2m,
          wind_speed_10m,wind_direction_10m,surface_pressure,weather_code
  &daily=precipitation_sum,precipitation_hours,temperature_2m_max,
         temperature_2m_min,wind_speed_10m_max,weather_code
  &current=precipitation,temperature_2m,relative_humidity_2m,
           wind_speed_10m,weather_code,surface_pressure
  &past_days=7
  &forecast_days=1
  &timezone=America%2FSao_Paulo
```

#### Exemplo Python

```python
import requests

def fetch_recent_weather(lat: float, lon: float, days_back: int = 7) -> dict:
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": [
            "precipitation", "temperature_2m", "relative_humidity_2m",
            "wind_speed_10m", "wind_direction_10m", "surface_pressure",
            "weather_code", "rain", "showers",
        ],
        "daily": [
            "precipitation_sum", "precipitation_hours",
            "temperature_2m_max", "temperature_2m_min",
            "wind_speed_10m_max", "weather_code",
        ],
        "current": [
            "precipitation", "temperature_2m", "relative_humidity_2m",
            "wind_speed_10m", "weather_code", "surface_pressure",
        ],
        "past_days": days_back,
        "forecast_days": 1,
        "timezone": "America/Sao_Paulo",
        "cell_selection": "land",
    }
    r = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params=params,
        timeout=20,
        headers={"User-Agent": "MeteoRAG/1.0"},
    )
    r.raise_for_status()
    return r.json()
```

---

### 2.6 Archive API — Histórico ERA5

**URL:** `GET https://archive-api.open-meteo.com/v1/archive`

Acessa histórico desde 1940 usando reanalysis (ERA5, ERA5-Land, ECMWF IFS). Usar quando precisar de dados com mais de 7 dias de histórico e maior consistência temporal.

**Delay:** ~5–7 dias para ERA5; ~2 dias para ECMWF IFS.

#### Parâmetros Específicos

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|:-----------:|-----------|
| `start_date` | string | ✅ | Data início `YYYY-MM-DD` |
| `end_date` | string | ✅ | Data fim `YYYY-MM-DD` |
| `hourly` | string | Não | Variáveis horárias |
| `daily` | string | Não | Variáveis diárias |
| `models` | string | Não | Default `best_match` (combina ERA5 + ECMWF IFS 9km) |

#### Modelos de Reanalysis Disponíveis

| Modelo | Resolução | Cobertura Temporal | Delay |
|--------|-----------|-------------------|-------|
| `best_match` (default) | 9–25 km | 1940–hoje | 2–7 dias |
| `era5` | 25 km (0.25°) | 1940–hoje | 5 dias |
| `era5_land` | 11 km (0.1°) | 1950–hoje | 5 dias |
| `ecmwf_ifs` | 9 km | 2017–hoje | 2 dias |
| `era5_seamless` | 11–25 km | 1940–hoje | 5 dias |
| `era5_ensemble` | 55 km (0.5°) | 1940–hoje | 5 dias, 3-horário |
| `cerra` | 5 km | 1985–jun/2021 | Encerrado (somente Europa) |

#### Disponibilidade de Variáveis por Modelo

| Variável | ERA5 | ERA5-Land | ECMWF IFS 9km |
|----------|:----:|:---------:|:-------------:|
| Temperatura, Umidade | ✅ | ✅ | ✅ |
| Precipitação, Chuva | ✅ | ⚠️¹ | ✅ |
| Vento (10m, 100m) | ✅ | ⚠️¹ | ✅ |
| Radiação solar | ✅ | ⚠️¹ | ✅ |
| Temperatura do solo | ✅ | ✅ | ✅ |
| Umidade do solo | ✅ | ✅ | ✅ |
| Espessura de neve | ❌ | ✅ | ❌ |
| Rajadas de vento | ❌ | ✅ | ✅ |

¹ Disponível via `era5_seamless`.

#### Exemplo Python

```python
def fetch_historical_weather(
    lat: float, lon: float,
    start_date: str, end_date: str,
) -> dict:
    """Histórico ERA5. start/end_date formato YYYY-MM-DD."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": [
            "precipitation_sum", "temperature_2m_max",
            "temperature_2m_min", "weather_code",
            "wind_speed_10m_max",
        ],
        "timezone": "America/Sao_Paulo",
        "cell_selection": "land",
    }
    r = requests.get(
        "https://archive-api.open-meteo.com/v1/archive",
        params=params,
        timeout=30,
        headers={"User-Agent": "MeteoRAG/1.0"},
    )
    r.raise_for_status()
    return r.json()
```

---

### 2.7 Geocoding API

**URL:** `GET https://geocoding-api.open-meteo.com/v1/search`

Resolve nome de cidade para coordenadas lat/lon. Baseado em GeoNames. Permite buscas em qualquer idioma.

#### Parâmetros

| Parâmetro | Tipo | Obrigatório | Default | Descrição |
|-----------|------|:-----------:|---------|-----------|
| `name` | string | ✅ | — | Nome da cidade. Mín. 2 chars; ≥3 chars = fuzzy match |
| `count` | int | | `10` | Nº de resultados (máx. 100) |
| `language` | string | | `en` | Idioma dos resultados. Usar `pt` para português |
| `country_code` | string | | — | Filtrar por país ISO-3166-1 alpha2. Ex: `BR` |

#### Exemplo de Uso

```python
def resolve_city(name: str) -> dict | None:
    r = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": name, "count": 3, "language": "pt", "country_code": "BR"},
        timeout=10,
    )
    results = r.json().get("results", [])
    return results[0] if results else None

# resultado:
# {
#   "id": 3459467,
#   "name": "Juiz de Fora",
#   "latitude": -21.76167,
#   "longitude": -43.34667,
#   "elevation": 939.0,
#   "timezone": "America/Sao_Paulo",
#   "country": "Brasil",
#   "admin1": "Minas Gerais",
#   "population": 516247
# }
```

#### Campos Retornados

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | int | ID único GeoNames |
| `name` | string | Nome localizado |
| `latitude`, `longitude` | float | Coordenadas WGS84 |
| `elevation` | float | Altitude (metros) |
| `timezone` | string | Ex: `America/Sao_Paulo` |
| `country_code` | string | Ex: `BR` |
| `admin1` | string | Estado (ex: `Minas Gerais`) |
| `admin2` | string | Mesorregião |
| `population` | int | Habitantes |
| `postcodes` | string[] | CEPs (quando disponível) |

---

### 2.8 Elevation API

**URL:** `GET https://api.open-meteo.com/v1/elevation`

Altitude precisa por coordenadas. Baseado no Copernicus DEM 2021 GLO-90 (resolução 90m, licença aberta).

```python
# Múltiplas cidades em uma requisição (até 100 pontos)
r = requests.get(
    "https://api.open-meteo.com/v1/elevation",
    params={
        "latitude":  "-21.7609,-21.1183,-21.2258",
        "longitude": "-43.3496,-42.9404,-43.7736",
    },
    timeout=10,
)
elevations = r.json()["elevation"]
# [-21.7609 → 939.0m (JF), -21.1183 → 251.0m (Ubá), -21.2258 → 1126.0m (Barbacena)]
```

---

### 2.9 Variáveis Horárias — Referência Completa

Usadas em `&hourly=`. Cada valor = estado instantâneo no início da hora, **exceto precipitação** (soma/média da hora anterior).

#### Precipitação e Condição

| Variável | Unidade | Descrição | MeteoRAG |
|----------|---------|-----------|:--------:|
| `precipitation` | mm | Total (chuva + neve + granizo) | ✅ |
| `rain` | mm | Chuva estratiforme | ✅ |
| `showers` | mm | Pancadas convectivas | ✅ |
| `snowfall` | cm | Neve | — |
| `snow_depth` | m | Neve acumulada | — |
| `weather_code` | WMO | Condição (ver seção 2.12) | ✅ |
| `precipitation_probability` | % | Probabilidade de precipitação | — |

#### Temperatura

| Variável | Unidade | Descrição | MeteoRAG |
|----------|---------|-----------|:--------:|
| `temperature_2m` | °C | Temperatura a 2m | ✅ |
| `apparent_temperature` | °C | Sensação térmica | — |
| `dewpoint_2m` | °C | Ponto de orvalho | — |
| `temperature_80m` | °C | Temperatura a 80m | — |
| `soil_temperature_0cm` | °C | Temperatura superficial do solo | — |

#### Umidade e Pressão

| Variável | Unidade | Descrição | MeteoRAG |
|----------|---------|-----------|:--------:|
| `relative_humidity_2m` | % | Umidade relativa a 2m | ✅ |
| `surface_pressure` | hPa | Pressão ao nível da superfície | ✅ |
| `sea_level_pressure` | hPa | Pressão ao nível do mar | — |
| `cloud_cover` | % | Cobertura de nuvens total | — |
| `visibility` | m | Visibilidade horizontal | — |
| `vapour_pressure_deficit` | kPa | Déficit de pressão de vapor | — |

#### Vento

| Variável | Unidade | Descrição | MeteoRAG |
|----------|---------|-----------|:--------:|
| `wind_speed_10m` | km/h | Velocidade do vento a 10m | ✅ |
| `wind_direction_10m` | ° | Direção (0=N, 90=E, 180=S, 270=O) | ✅ |
| `wind_gusts_10m` | km/h | Rajadas a 10m | — |
| `wind_speed_80m` | km/h | Vento a 80m | — |

#### Convecção e Radiação (úteis para risco)

| Variável | Unidade | Descrição |
|----------|---------|-----------|
| `cape` | J/kg | CAPE — Energia Potencial Convectiva (>1000 = risco de tempestade) |
| `lifted_index` | — | Instabilidade atmosférica (negativo = instável) |
| `uv_index` | — | Índice UV (0–11+) |
| `sunshine_duration` | s | Segundos de sol na hora |
| `shortwave_radiation` | W/m² | Radiação solar total |

---

### 2.10 Variáveis Diárias — Referência Completa

Usadas em `&daily=`. Agregações de 00:00 às 23:59 no timezone configurado.

| Variável | Unidade | Descrição | MeteoRAG |
|----------|---------|-----------|:--------:|
| `precipitation_sum` | mm | Chuva total do dia | ✅ |
| `rain_sum` | mm | Chuva estratiforme total | — |
| `showers_sum` | mm | Pancadas total | — |
| `precipitation_hours` | h | Horas com precipitação > 0 | ✅ |
| `precipitation_probability_max` | % | Probabilidade máxima do dia | — |
| `temperature_2m_max` | °C | Temperatura máxima | ✅ |
| `temperature_2m_min` | °C | Temperatura mínima | ✅ |
| `temperature_2m_mean` | °C | Temperatura média | — |
| `apparent_temperature_max` | °C | Sensação térmica máxima | — |
| `wind_speed_10m_max` | km/h | Velocidade máxima do vento | ✅ |
| `wind_gusts_10m_max` | km/h | Rajada máxima do dia | — |
| `wind_direction_10m_dominant` | ° | Direção dominante | — |
| `weather_code` | WMO | Condição dominante do dia | ✅ |
| `sunrise` / `sunset` | ISO8601 | Nascer/pôr do sol | — |
| `daylight_duration` | s | Duração do dia (segundos) | — |
| `sunshine_duration` | s | Horas de sol efetivo | — |
| `uv_index_max` | — | Índice UV máximo | — |
| `shortwave_radiation_sum` | MJ/m² | Radiação solar total | — |
| `et0_fao_evapotranspiration` | mm | Evapotranspiração FAO | — |
| `mean_sea_level_pressure` | hPa | Pressão média ao nível do mar | — |
| `mean_cape` / `maximum_cape` | J/kg | CAPE médio e máximo do dia | — |

---

### 2.11 Variáveis Current — Condição Atual

Usadas em `&current=`. Retorna um único objeto (não array). Qualquer variável hourly pode ser usada como current. Resolução: 15 minutos.

```json
"current": {
  "time": "2026-03-14T15:00",
  "interval": 900,
  "precipitation": 2.4,
  "temperature_2m": 22.1,
  "relative_humidity_2m": 88,
  "wind_speed_10m": 12.5,
  "weather_code": 61,
  "surface_pressure": 921.3
}
```

`interval: 900` = resolução de 15 minutos (900 segundos).

---

### 2.12 WMO Weather Codes

Open-Meteo usa a tabela WMO 4677 ordenada por severidade crescente (0 = céu limpo, 99 = tempestade com granizo forte). Apenas um subconjunto dos 100 códigos possíveis é reportado.

| Código | Condição PT-BR | Condição EN | Risco MG |
|:------:|----------------|-------------|:--------:|
| 0 | Céu limpo | Clear sky | — |
| 1 | Majoritariamente limpo | Mainly clear | — |
| 2 | Parcialmente nublado | Partly cloudy | — |
| 3 | Nublado / encoberto | Overcast | — |
| 45 | Neblina | Fog | Baixo |
| 48 | Neblina com geada | Depositing rime fog | Baixo |
| 51 | Garoa fraca | Light drizzle | — |
| 53 | Garoa moderada | Moderate drizzle | — |
| 55 | Garoa intensa | Dense drizzle | — |
| 56 | Garoa congelante fraca | Light freezing drizzle | — |
| 57 | Garoa congelante intensa | Dense freezing drizzle | — |
| 61 | Chuva fraca | Slight rain | — |
| 63 | Chuva moderada | Moderate rain | Monitorar |
| 65 | Chuva forte | Heavy rain | ⚠️ Alto |
| 66 | Chuva congelante fraca | Light freezing rain | — |
| 67 | Chuva congelante intensa | Heavy freezing rain | — |
| 71 | Nevada fraca | Slight snowfall | — |
| 73 | Nevada moderada | Moderate snowfall | — |
| 75 | Nevada forte | Heavy snowfall | — |
| 77 | Grãos de neve | Snow grains | — |
| 80 | Pancadas fracas | Slight rain showers | — |
| 81 | Pancadas moderadas | Moderate rain showers | Monitorar |
| 82 | Pancadas violentas | Violent rain showers | ⚠️ Alto |
| 85 | Pancadas de neve fracas | Slight snow showers | — |
| 86 | Pancadas de neve fortes | Heavy snow showers | — |
| 95 | Trovoada leve/moderada | Thunderstorm slight/moderate | ⚠️ Alto |
| 96 | Trovoada com granizo fraco | Thunderstorm with slight hail | 🚨 Extremo |
| 99 | Trovoada com granizo forte | Thunderstorm with heavy hail | 🚨 Extremo |

**Função utilitária para chunking RAG:**

```python
WMO_PT = {
    0: "céu limpo", 1: "majoritariamente limpo", 2: "parcialmente nublado",
    3: "nublado", 45: "neblina", 48: "neblina com geada",
    51: "garoa fraca", 53: "garoa moderada", 55: "garoa intensa",
    61: "chuva fraca", 63: "chuva moderada", 65: "chuva forte",
    80: "pancadas fracas", 81: "pancadas moderadas", 82: "pancadas violentas",
    95: "trovoada", 96: "trovoada com granizo", 99: "trovoada com granizo forte",
}

WMO_RISK = {63: "moderado", 65: "alto", 81: "moderado", 82: "alto",
            95: "alto", 96: "extremo", 99: "extremo"}

def wmo_to_text(code: int | None) -> str:
    if code is None:
        return "condição desconhecida"
    return WMO_PT.get(int(code), f"código WMO {code}")

def wmo_risk(code: int | None) -> str | None:
    if code is None:
        return None
    return WMO_RISK.get(int(code))
```

---

### 2.13 Schema de Resposta JSON

Estrutura completa retornada por um endpoint com `hourly + daily + current`:

```json
{
  "latitude": -21.75,
  "longitude": -43.375,
  "generationtime_ms": 1.482,
  "utc_offset_seconds": -10800,
  "timezone": "America/Sao_Paulo",
  "timezone_abbreviation": "BRT",
  "elevation": 939.0,
  "current_units": {
    "time": "iso8601",
    "interval": "seconds",
    "precipitation": "mm",
    "temperature_2m": "°C",
    "weather_code": "wmo code"
  },
  "current": {
    "time": "2026-03-14T15:00",
    "interval": 900,
    "precipitation": 0.0,
    "temperature_2m": 24.3,
    "weather_code": 2
  },
  "hourly_units": {
    "time": "iso8601",
    "precipitation": "mm",
    "temperature_2m": "°C"
  },
  "hourly": {
    "time": ["2026-03-07T00:00", "2026-03-07T01:00", "..."],
    "precipitation": [0.0, 0.0, 2.4, 8.1, "..."],
    "temperature_2m": [21.3, 20.8, 20.1, "..."]
  },
  "daily_units": {
    "time": "iso8601",
    "precipitation_sum": "mm",
    "temperature_2m_max": "°C"
  },
  "daily": {
    "time": ["2026-03-07", "2026-03-08", "..."],
    "precipitation_sum": [0.0, 5.2, 48.7, 72.3, "..."],
    "temperature_2m_max": [30.1, 25.4, 22.1, "..."],
    "temperature_2m_min": [19.8, 18.2, 17.9, "..."]
  }
}
```

**Campos de metadados:**

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `latitude`, `longitude` | float | Grid cell efetivamente usado (pode diferir do solicitado em até ~5km) |
| `elevation` | float | Altitude do grid cell retornado (metros) |
| `generationtime_ms` | float | Latência de geração no servidor |
| `utc_offset_seconds` | int | `-10800` = UTC-3 (Brasília) |
| `timezone_abbreviation` | string | `BRT` (inverno) ou `BRST` (horário de verão) |
| `*_units` | object | Unidades de cada variável retornada |

**Regra de indexação:** `hourly.time[i]` corresponde a `hourly.<variavel>[i]`. Iterar com `zip()`:
```python
for ts, precip in zip(data["hourly"]["time"], data["hourly"]["precipitation"]):
    print(f"{ts}: {precip} mm")
```

**Ausência de nulos:** Open-Meteo não retorna `null` em arrays. Precipitação ausente vem como `0.0`. Não é necessário tratamento de valores sentinela como o `9999` do INMET.

---

### 2.14 Modelos Meteorológicos Disponíveis

| Modelo (`models=`) | Resolução | Atualização | Previsão | Qualidade para MG |
|--------------------|-----------|------------|----------|--------------------|
| `best_match` (default) | 2–25 km | Varia | 16 dias | ✅ Recomendado |
| `ecmwf_ifs_hres` | 9 km | A cada 6h | 10 dias | ✅ Melhor para precipitação extrema |
| `ecmwf_ifs025` | 25 km | A cada 6h | 15 dias | ✅ |
| `gfs_seamless` | 3–25 km | A cada hora | 16 dias | ✅ Atualização mais frequente |
| `gfs025` | 25 km | A cada 6h | 16 dias | ✅ |
| `icon_seamless` | 2–11 km | A cada 3h | 7.5 dias | ✅ Bom para curto prazo |
| `icon_global` | 11 km | A cada 6h | 7.5 dias | ✅ |

Para eventos de chuva extrema (contexto JF/Ubá): preferir `ecmwf_ifs_hres` ou `best_match`.

**Verificar status e horário de atualização dos modelos:**
```
GET https://api.open-meteo.com/v1/forecast?...&models=ecmwf_ifs_hres
# ou consultar:
https://open-meteo.com/en/docs/model-updates
```

---

### 2.15 Erros e HTTP Codes

| Status | Situação | Resposta | Ação |
|--------|---------|----------|------|
| `200 OK` | Sucesso | JSON completo | Processar |
| `400 Bad Request` | Parâmetro inválido | `{"error": true, "reason": "..."}` | Log + raise ValueError |
| `429 Too Many Requests` | Rate limit | Headers com `Retry-After` | Backoff exponencial + retry |
| `500 Internal Server Error` | Erro no servidor | Corpo pode ser vazio | Retry; 3 tentativas max |
| `503 Service Unavailable` | Servidor sobrecarregado | — | Retry; verificar status.open-meteo.com |

**Resposta de erro 400:**
```json
{
  "error": true,
  "reason": "Cannot initialize WeatherVariable from invalid String value 'tempeture_2m' for key hourly"
}
```

---

### 2.16 Cidades Mapeadas para o MeteoRAG

| Cidade | Latitude | Longitude | Altitude | Mesorregião |
|--------|:--------:|:---------:|:--------:|-------------|
| Juiz de Fora | -21.7609 | -43.3496 | 939m | Zona da Mata |
| Ubá | -21.1183 | -42.9404 | 251m | Zona da Mata |
| Barbacena | -21.2258 | -43.7736 | 1126m | Campo das Vertentes |
| Muriaé | -21.1322 | -42.3670 | 256m | Zona da Mata |
| Belo Horizonte | -19.9167 | -43.9345 | 915m | Metropolitana |
| Viçosa | -20.7546 | -42.8825 | 649m | Zona da Mata |
| Cataguases | -21.3917 | -42.6961 | 215m | Zona da Mata |

> Vantagem sobre INMET: qualquer cidade MG pode ser adicionada por lat/lon, sem dependência de estação física.

---

## 3. INMET — Fonte Secundária (Alertas)

### 3.1 Status Atual (Março 2026)

> ❌ **INMET completamente indisponível** para dados de estações.  
> Endpoints de dados horários retornam HTTP 204 para qualquer intervalo testado, incluindo 14 dias atrás.  
> Alertas também indisponíveis no momento de escrita.

**Regra de implementação:** O app nunca deve falhar por causa do INMET. Toda chamada é best-effort, capturada em try/except, retorna `[]` silenciosamente.

### 3.2 Endpoint de Alertas

```
GET https://apitempo.inmet.gov.br/alertas/{estado}/{nivel}
```

| Parâmetro | Valores | Descrição |
|-----------|---------|-----------|
| `estado` | `mg`, `sp`, `rj`... | Sigla minúscula do estado |
| `nivel` | `1` | Sempre `1` |

**HTTP 204:** Nenhum alerta ativo → retornar `[]`.

```python
def get_inmet_alerts(state: str = "mg") -> list[dict]:
    try:
        r = requests.get(
            f"https://apitempo.inmet.gov.br/alertas/{state}/1",
            headers={"User-Agent": "MeteoRAG/1.0"},
            timeout=10,
        )
        if r.status_code == 204:
            return []
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning(f"[INMET] Alertas indisponíveis: {e}")
        return []
```

### 3.3 Schema de um Alerta

```json
{
  "CD_IDENTIFICADOR": "uuid",
  "DS_EVENTO": "CHUVAS INTENSAS",
  "DS_SEVERIDADE": "Laranja",
  "DT_INICIO_ALERTA": "2026-03-14 06:00:00",
  "DT_FIM_ALERTA": "2026-03-14 18:00:00",
  "DS_MENSAGEM": "Previsão de chuvas entre 30 e 60 mm/h...",
  "NM_MUNICIPIOS": "Juiz de Fora, Ubá, Muriaé"
}
```

| Severidade | Cor | Limiar típico de chuva |
|-----------|-----|----------------------|
| Amarelo | 🟡 | 20–30 mm/h ou 30–60 mm/dia |
| Laranja | 🟠 | 30–60 mm/h ou 50–100 mm/dia |
| Vermelho | 🔴 | >60 mm/h ou >100 mm/dia |

---

## 4. Anthropic API

### Configuração

```python
import anthropic

# API direta:
client = anthropic.Anthropic(api_key="sk-ant-...")

# Via Databricks:
client = anthropic.Anthropic(
    api_key="dapi...",
    base_url="https://<workspace>.cloud.databricks.com/serving-endpoints/",
)
# Atenção: o model ID pode ser diferente no Databricks.
# Verificar em: Workspace → Serving → Endpoints
```

### Chamada Padrão

```python
response = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=1024,
    system=SYSTEM_PROMPT,          # contexto RAG embutido
    messages=[
        *chat_history[-20:],       # últimas 10 trocas (20 mensagens)
        {"role": "user", "content": query}
    ],
)
text = response.content[0].text
input_tokens = response.usage.input_tokens
output_tokens = response.usage.output_tokens
```

### Streaming (Streamlit)

```python
def ask_stream(query: str, context: str, history: list[dict]):
    with client.messages.stream(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT.format(context=context),
        messages=[*history[-20:], {"role": "user", "content": query}],
    ) as stream:
        for text_chunk in stream.text_stream:
            yield text_chunk
```

### Estimativa de Tokens por Query

| Componente | Tokens (estimativa) |
|-----------|:------------------:|
| System prompt base | ~300 |
| Contexto RAG (8 chunks Open-Meteo) | ~600–900 |
| Histórico de chat (10 trocas) | ~500–800 |
| Query do usuário | ~20–50 |
| **Total input** | **~1.400–2.050** |
| Output típico | ~200–400 |

### Modelos

| Modelo | Contexto | Uso no MeteoRAG |
|--------|----------|----------------|
| `claude-haiku-4-5` | 200K | **Padrão** — rápido, custo baixo |
| `claude-sonnet-4-5` | 200K | Fallback para respostas mais elaboradas |

### Tratamento de Erros

```python
try:
    response = client.messages.create(...)
except anthropic.APIConnectionError:
    return "Serviço temporariamente indisponível."
except anthropic.RateLimitError:
    return "Muitas requisições. Aguarde um momento."
except anthropic.APIStatusError as e:
    return f"Erro ao processar [código {e.status_code}]."
```

---

## 5. Decisões de Design

**`past_days` na Forecast API vs Archive API para dados recentes:**
Archive API tem delay de 2–7 dias. Para eventos de chuva em andamento (JF/Ubá hoje), precisamos de dados sem delay. A Forecast API com `past_days` usa archives de model runs inicializados com observações reais — precisão equivalente para o nosso caso de uso.

**`timezone=America/Sao_Paulo` obrigatório:**
Sem timezone, timestamps vêm em UTC. Chunks RAG como "às 15h choveu 30mm" ficariam deslocados 3h. A API aplica offset e horário de verão automaticamente.

**`best_match` como modelo default:**
Seleciona automaticamente o melhor modelo disponível por localização, frequentemente combinando ECMWF IFS com modelos regionais. Forçar `ecmwf_ifs_hres` pode ser preferível em eventos convectivos extremos.

**INMET mantido como best-effort:**
Alertas oficiais têm valor legal e comunicacional únicos — emitidos pela Defesa Civil, calibrados para risco à população. Custo de manutenção zero, retorna `[]` se falhar.

**TF-IDF vs embeddings:**
Open-Meteo retorna dados estruturados (números + datas), não texto semântico rico. TF-IDF com tokenização PT-BR cobre 95% das queries meteorológicas sem dependência de API de embeddings externa.

---

## 6. Troubleshooting

| Sintoma | Causa | Solução |
|---------|-------|---------|
| `precipitation` zerado para cidade na costa | Grid cell sobre oceano | Adicionar `&cell_selection=land` |
| Timestamps em UTC com timezone configurado | Parâmetro mal codificado | Usar dict no `requests.get(params=...)` em vez de URL manual |
| Archive API retorna 400 | `start_date` muito recente (dentro do delay) | Usar Forecast API com `past_days` para dados recentes |
| `generationtime_ms` > 500ms | Muitas variáveis ou intervalo longo | Reduzir variáveis; dividir em múltiplas requests |
| Precipitação Open-Meteo diferente de medições locais | É reanalysis/model, não estação física | Esperado; acurácia ±20% para eventos convectivos locais |
| INMET retorna qualquer erro | API instável | Silenciar; retornar `[]`; logar como WARNING |
| Databricks 404 no model | Nome do endpoint diferente do padrão Anthropic | Verificar nome exato no Databricks Serving UI |
| `RateLimitError` Anthropic em pico | Muitos usuários simultâneos | Implementar queue; considerar upgrade de tier |
