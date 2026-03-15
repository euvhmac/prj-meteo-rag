"""Script de teste rápido para a API Open-Meteo."""
from meteorag.api.openmeteo_client import OpenMeteoClient, MG_CITIES

client = OpenMeteoClient()

print("=== Teste Open-Meteo API ===\n")

for city in ["Juiz de Fora", "Barbacena"]:
    print(f"📍 {city}:")
    summaries = client.get_daily_summaries(city, 3)
    if not summaries:
        print("  ❌ Sem dados!\n")
        continue
    for d in summaries:
        print(
            f"  {d['date']}: {d['total_rain_mm']}mm, "
            f"{d['min_temp_c']}-{d['max_temp_c']}°C, "
            f"{d['weather_description']}"
        )
    print()

    current = client.get_current(city)
    if current:
        print(
            f"  🕐 Agora: {current['temp_c']}°C, "
            f"{current['humidity_pct']}%, "
            f"{current['weather_description']}\n"
        )

print("=== Pipeline RAG ===\n")
from meteorag.rag.pipeline import MeteoRAG

rag = MeteoRAG()
total = rag.index_city("Juiz de Fora", days_back=3)
print(f"✅ Chunks indexados: {total}")

results = rag.retrieve("chuva em Juiz de Fora")
print(f"🔍 Resultados para 'chuva em Juiz de Fora': {len(results)}")
for r in results[:3]:
    print(f"  [{r['score']:.3f}] {r['text'][:120]}...")

print("\n✅ Tudo funcionando!")
