"""
Cuenta cuántas veces NGINX enrutó la petición a cada nodo (app1/app2/app3).
Sirve como evidencia de que el balanceo por pesos (3:2:1) se respeta.

Ejecutar:
    pip install requests
    python check_balance.py
"""
import requests
from collections import Counter

TOTAL_REQUESTS = 200
counts = Counter()

for _ in range(TOTAL_REQUESTS):
    r = requests.get("http://localhost/health")
    counts[r.json()["node"]] += 1

print(f"Total de peticiones: {TOTAL_REQUESTS}\n")
for node, count in sorted(counts.items()):
    porcentaje = (count / TOTAL_REQUESTS) * 100
    print(f"{node}: {count} peticiones ({porcentaje:.1f}%)")
