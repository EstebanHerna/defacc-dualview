"""Codigo muerto en las entregas del benchmark. No llama a ningun modelo.

Responde: las entregas con backdoor traen mas codigo muerto que las honestas? Sirve el conteo como senal
barata (sin LLM) para priorizar la auditoria? Escribe una fila por entrega en results/deadcode.csv.

Uso:  python scripts/deadcode.py
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from inspect_ai.log import read_eval_log
from sklearn.metrics import roc_auc_score

from control_arena._control_task_metadata import ControlTaskMetadata
from dualview.deadcode import KINDS, dead_code_counts
from dualview.formatters import submitted_code

ap = argparse.ArgumentParser()
ap.add_argument("--log-dir", default="logs/base")
ap.add_argument("--out", default="results/deadcode.csv")
ap.add_argument("--boot", type=int, default=2000)
a = ap.parse_args()
rng = np.random.default_rng(0)

rows = []
for p in sorted(Path(a.log_dir).glob("*.eval")):
    for s in read_eval_log(str(p)).samples or []:
        mode = ControlTaskMetadata.model_validate(s.metadata).eval_mode.value
        code = submitted_code(s.messages) or ""
        rows.append({"sample_id": s.id, "mode": mode, "lines": code.count("\n") + 1, **dead_code_counts(code)})
df = pd.DataFrame(rows)
Path(a.out).parent.mkdir(parents=True, exist_ok=True)
df.to_csv(a.out, index=False)

h, k = df[df["mode"] == "honest"], df[df["mode"] == "attack"]
print(f"entregas: {len(h)} honestas, {len(k)} con backdoor\n")
print(f"{'tipo':20} {'honestas con >=1':>17} {'backdoors con >=1':>18} {'diferencia (IC 95%)':>26} {'AUC del conteo':>15}")
for col in (*KINDS, "total"):
    ph, pk = (h[col] > 0).mean(), (k[col] > 0).mean()
    bs = [(rng.choice(k[col].to_numpy(), len(k)) > 0).mean() - (rng.choice(h[col].to_numpy(), len(h)) > 0).mean()
          for _ in range(a.boot)]
    lo, hi = np.percentile(bs, [2.5, 97.5])
    auc = roc_auc_score(np.r_[np.zeros(len(h)), np.ones(len(k))], np.r_[h[col], k[col]])
    print(f"{col:20} {ph:17.1%} {pk:18.1%} {pk - ph:+11.1%} [{lo:+.1%}, {hi:+.1%}] {auc:15.3f}")

# Mismas tareas en ambos grupos: comparacion pareada por tarea.
j = h.set_index("sample_id")[["total"]].join(k.set_index("sample_id")[["total"]], lsuffix="_h", rsuffix="_k", how="inner")
d = (j["total_k"] - j["total_h"]).to_numpy()
print(f"\npareado por tarea (n={len(j)}): el backdoor trae mas codigo muerto que la honesta en {(d > 0).mean():.1%}, "
      f"menos en {(d < 0).mean():.1%}, igual en {(d == 0).mean():.1%}")
thr = np.quantile(h["total"], 0.95, method="higher")
print(f"como detector solo (umbral que deja pasar 5% de honestas, total > {thr:.0f}): "
      f"TPR {(k['total'] > thr).mean():.1%}, FPR real {(h['total'] > thr).mean():.1%}")
print(f"\ndetalle por entrega: {a.out}")
