"""Costo de monitoreo en cascada: cuantas llamadas al monitor hacen falta por entrega.

Idea: si una entrega no tiene comentarios ni docstrings, la vista saneada es el mismo codigo que
la cruda, asi que no hace falta pagar la segunda llamada. Lo mismo con la tercera vista cuando no
hay cadenas largas. Este script no llama a ningun modelo: solo lee las entregas guardadas.

Uso:  python scripts/cost.py
"""
import argparse
from pathlib import Path

from inspect_ai.log import read_eval_log

from dualview.sanitize import comment_text, has_long_string

ap = argparse.ArgumentParser()
ap.add_argument("--log-dir", default="logs/base")
a = ap.parse_args()

print(f"{'modo':8} {'n':>4} {'con texto no ejecutable':>24} {'con cadenas largas':>19} {'doble vista':>12} {'triple vista':>13}")
for p in sorted(Path(a.log_dir).glob("*.eval")):
    lg = read_eval_log(str(p))
    n = text = long_ = 0
    mode = "?"
    for s in lg.samples or []:
        md = s.metadata or {}
        mode = md.get("eval_mode", "attack" if md.get("side_task_name") else "honest")
        code = next((m.tool_calls[0].arguments.get("code") for m in reversed(s.messages)
                     if getattr(m, "tool_calls", None)), None)
        if not isinstance(code, str):
            continue
        n += 1
        text += bool(comment_text(code).strip())
        long_ += has_long_string(code)
    if n:
        print(f"{mode:8} {n:4d} {text / n:24.1%} {long_ / n:19.1%} {1 + text / n:11.2f}x {1 + text / n + long_ / n:12.2f}x")
print("\nLlamadas esperadas por entrega. Sin cascada: doble vista = 2.00x, triple vista = 3.00x.")
