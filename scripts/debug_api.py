"""Script de diagnóstico para API INMET e LLM."""

import json
import sys
sys.path.insert(0, "src")

import requests
from datetime import date, timedelta

print("=" * 60)
print("DIAGNÓSTICO MeteoRAG")
print("=" * 60)

# 1. Testar API INMET diretamente
end = date.today()
start = end - timedelta(days=3)
url = f"https://apitempo.inmet.gov.br/estacao/{start}/{end}/A518"
print(f"\n[1] URL: {url}")
try:
    r = requests.get(url, timeout=20)
    print(f"    Status: {r.status_code}")
    print(f"    Content-Type: {r.headers.get('content-type')}")
    body = r.text[:500]
    print(f"    Body ({len(r.text)} chars): {body}")
    if r.status_code == 200:
        data = r.json()
        if isinstance(data, list):
            print(f"    Items: {len(data)}")
            if data:
                print(f"    Primeiro item keys: {list(data[0].keys())}")
                print(f"    Primeiro item: {json.dumps(data[0], indent=2, ensure_ascii=False)[:300]}")
        else:
            print(f"    Tipo resposta: {type(data)}")
except Exception as e:
    print(f"    ERRO: {e}")

# 2. Testar via INMETClient
print(f"\n[2] Testando INMETClient...")
from meteorag.api.inmet_client import INMETClient
client = INMETClient()
obs = client.get_observations("A518", start, end)
print(f"    Observações A518: {len(obs)}")
if obs:
    print(f"    Primeira obs: {obs[0]}")
else:
    # Testar resposta raw novamente com logging
    import logging
    logging.basicConfig(level=logging.DEBUG)
    print("    Tentando novamente com logging DEBUG...")
    client.clear_cache()
    obs2 = client.get_observations("A518", start, end)
    print(f"    Observações A518 (retry): {len(obs2)}")

# 3. Testar alertas
print(f"\n[3] Testando alertas...")
alerts = client.get_alerts("MG")
print(f"    Alertas MG: {len(alerts)}")

# 4. Testar pipeline RAG
print(f"\n[4] Testando pipeline RAG...")
from meteorag.rag.pipeline import MeteoRAG
rag = MeteoRAG()
total = rag.index_city("A518", "Juiz de Fora", start, end)
print(f"    Chunks indexados: {total}")
print(f"    Pipeline ready: {rag.is_ready}")

# 5. Testar LLM
print(f"\n[5] Testando LLM...")
from meteorag.config import Settings
s = Settings()
print(f"    API Key: {s.anthropic_api_key[:10]}...")
print(f"    Base URL: {s.anthropic_base_url}")
print(f"    Model: {s.llm_model}")

try:
    from meteorag.llm.client import get_client, ask
    llm_client = get_client(s)
    response = ask("Ola, me diga oi em uma frase curta", "Sem contexto", settings=s, client=llm_client)
    print(f"    LLM Response: {response[:200]}")
except Exception as e:
    print(f"    LLM ERRO: {e}")

print("\n" + "=" * 60)
print("FIM DIAGNÓSTICO")
print("=" * 60)
