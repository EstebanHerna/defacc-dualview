"""Corre la bateria completa de la prueba de choque sobre un modelo monitor y un tramo de entregas.

Dos pasadas de scripts/run_monitors.py, en este orden (la primera es la que mas importa):
  canales   vista cruda con cada canal de BATTERY                     -> canales.csv
  vistas    sin nota: cruda, saneada y cruda con cambio trivial        -> vistas.csv

Con --limit 36 son como maximo 464 llamadas: cabe en la cuota gratuita de 500 por dia y por modelo.
Para sumar entregas entre varias llaves, cada persona usa un --offset distinto (0, 36, 72, ...).

Uso:  python scripts/bateria.py --model google/gemini-3.1-flash-lite --offset 0 --limit 36
Luego: python scripts/scorecard.py
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

from dualview.injections import BATTERY

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True)
ap.add_argument("--offset", type=int, default=0)
ap.add_argument("--limit", type=int, default=36)
ap.add_argument("--max-connections", type=int, default=6)
ap.add_argument("--prompt", default="prompts/monitor.txt")
ap.add_argument("--out", default="results/bateria")
ap.add_argument("--retries", type=int, default=6)
a = ap.parse_args()

out = Path(a.out) / f"{a.model.split('/')[-1]}__{a.offset:03d}"
out.mkdir(parents=True, exist_ok=True)
base = [sys.executable, "-W", "ignore", "scripts/run_monitors.py", "--model", a.model, "--prompt", a.prompt,
        "--offset", str(a.offset), "--limit", str(a.limit), "--max-connections", str(a.max_connections)]
passes = [
    ("canales", ["--views", "raw", "--out", str(out / "canales.csv"), "--injections", *BATTERY]),
    ("vistas", ["--views", "raw", "stripped", "raw_ws", "--out", str(out / "vistas.csv"), "--injections"]),
]
for name, extra in passes:
    print(f"=== {name}: {a.model}, entregas {a.offset} a {a.offset + a.limit - 1} por modo ===", flush=True)
    # Reintentos: un error pasajero del proveedor tumba la pasada, pero lo ya calificado queda en
    # el cache local, asi que repetirla solo paga las llamadas que faltan.
    for attempt in range(1, a.retries + 1):
        r = subprocess.run(base + extra)
        if r.returncode == 0:
            break
        print(f"la pasada '{name}' fallo (intento {attempt} de {a.retries}); reintento en 30 s", flush=True)
        time.sleep(30)
    else:
        sys.exit(f"la pasada '{name}' fallo {a.retries} veces; lo ya calificado queda en el cache local")
print(f"listo: {out}. Subir esa carpeta y correr scripts/scorecard.py")
