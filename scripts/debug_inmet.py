"""Diagnóstico: testar diferentes datas e estações na API INMET."""

import sys
sys.path.insert(0, "src")

import requests
from datetime import date, timedelta

base = "https://apitempo.inmet.gov.br"
end = date.today()

# Testar várias janelas de tempo
for days in [1, 3, 7, 14]:
    start = end - timedelta(days=days)
    url = f"{base}/estacao/{start}/{end}/A518"
    try:
        r = requests.get(url, timeout=20)
        print(f"A518 ({days}d) {start} a {end}: HTTP {r.status_code} ({len(r.text)} chars)")
    except Exception as e:
        print(f"A518 ({days}d): ERRO {e}")

# Testar outra estação
for code in ["A518", "A519", "A520", "A521"]:
    start = end - timedelta(days=7)
    url = f"{base}/estacao/{start}/{end}/{code}"
    try:
        r = requests.get(url, timeout=20)
        count = 0
        if r.status_code == 200:
            data = r.json()
            count = len(data) if isinstance(data, list) else -1
        print(f"{code} (7d): HTTP {r.status_code}, items={count}")
    except Exception as e:
        print(f"{code}: ERRO {e}")

# Testar endpoint de alertas com diferentes paths
for path in ["/alertas/ativos", "/alertas/MG/1", "/alertas/ativas"]:
    url = f"{base}{path}"
    try:
        r = requests.get(url, timeout=20)
        print(f"Alertas {path}: HTTP {r.status_code} ({len(r.text)} chars)")
    except Exception as e:
        print(f"Alertas {path}: ERRO {e}")
