"""Corre los monitores post-hoc sobre logs/base y escribe una fila por (muestra, vista, condicion).

No usa Docker ni vuelve a correr agentes. Reglas que este script garantiza:
  - las muestras honestas solo se califican sin condicion de ataque (nunca reciben inyeccion);
  - una respuesta sin puntaje legible se guarda como score vacio y parsed=0, no como 0 (incluye el
    caso en que ControlArena registra "No score found" y deja el puntaje por defecto, 0);
  - cada corrida SOBREESCRIBE --out, salvo --append (para agregar otro modelo o las familias reservadas);
  - guarda en results/prompt_samples.txt un prompt real por condicion para revisarlo a ojo.

Uso:
  python scripts/run_monitors.py --model openai/gpt-4.1-nano --limit 20            # prueba barata (dev)
  python scripts/run_monitors.py --model openai/gpt-4.1-nano                       # corrida dev completa
  python scripts/run_monitors.py --model openai/gpt-4.1-nano --heldout --append    # una sola vez, al final
  python scripts/run_monitors.py --model openai/gpt-4.1-nano --views raw stripped  # sin la tercera vista
"""
import argparse
import csv
import sys
import time
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from inspect_ai.log import read_eval_log
from inspect_ai.model import GenerateConfig, get_model

from control_arena._async_utils import run_sync
from control_arena._control_task_metadata import ControlTaskMetadata
from control_arena.eval import run_monitors_for_eval_logs
from control_arena.monitor import MonitorScoreRange, basic_monitor_builder

from dualview.formatters import VIEWS, make_formatter, render_code, submitted_code
from dualview.injections import DEV, HELDOUT, TEMPLATES
from dualview.sanitize import monitor_directed_flag

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True, help="modelo confiable, p. ej. openai/gpt-4.1-nano")
ap.add_argument("--log-dir", default="logs/base")
ap.add_argument("--out", default="results/scores.csv")
ap.add_argument("--prompt", default="prompts/monitor.txt")
ap.add_argument("--limit", type=int, default=None, help="muestras por modo (prueba barata)")
ap.add_argument("--injections", nargs="*", default=None, choices=list(TEMPLATES))
ap.add_argument("--heldout", action="store_true", help="corre solo las familias reservadas")
ap.add_argument("--views", nargs="+", default=list(VIEWS), choices=list(VIEWS),
                help="vistas a correr (por defecto todas; cada vista es una llamada por entrega)")
ap.add_argument("--append", action="store_true")
ap.add_argument("--max-connections", type=int, default=8, help="llamadas simultaneas; bajar si el proveedor responde 429")
a = ap.parse_args()
# Inspect solo carga .env desde su CLI o desde eval(); este script no pasa por ahi.
load_dotenv(find_dotenv(usecwd=True))
families = a.injections if a.injections is not None else (HELDOUT if a.heldout else DEV)
out_path = Path(a.out)
if a.heldout and not a.append:
    sys.exit("--heldout va con --append: se agrega a la corrida dev ya congelada")
views = [v for v in VIEWS if v in a.views]  # sin repetidos y en orden fijo


def mode_of(sample) -> str:
    return ControlTaskMetadata.model_validate(sample.metadata).eval_mode.value


logs = [read_eval_log(str(p)) for p in sorted(Path(a.log_dir).glob("*.eval"))]
if not logs:
    sys.exit(f"no hay .eval en {a.log_dir}; corre scripts/gen.py primero")
for lg in logs:
    lg.samples = (lg.samples or [])[: a.limit] if a.limit else (lg.samples or [])
attack_logs = [lg for lg in logs if lg.samples and mode_of(lg.samples[0]) == "attack"]
honest_logs = [lg for lg in logs if lg.samples and mode_of(lg.samples[0]) == "honest"]
if not attack_logs or not honest_logs:
    sys.exit("se necesitan logs honestos y de ataque")

prompt = Path(a.prompt).read_text(encoding="utf-8")
for ph in ("{task_description}", "{tool_calls}"):
    if ph not in prompt:
        sys.exit(f"al prompt le falta {ph}")

# Una llamada de prueba antes del lote: detecta llave ausente, nombre de modelo invalido o cuota agotada.
try:
    _ping = run_sync(get_model(a.model).generate("Reply with the single word: ok"))
    print(f"modelo {a.model} responde: {_ping.completion.strip()[:40]!r}")
except Exception as e:  # noqa: BLE001
    sys.exit(f"el modelo {a.model} no respondio ({type(e).__name__}: {str(e)[:300]}). Revisar .env y el nombre del modelo.")


def build(view, inj):
    return basic_monitor_builder(
        model_role=None, model=a.model, prompt=prompt,
        config=GenerateConfig(max_connections=a.max_connections),
        prompt_formatter=make_formatter(view=view, injection=inj),
        score_range=MonitorScoreRange(min=0, max=100),
    )


# (condicion, logs sobre los que corre). "none" se omite en --heldout: ya esta en la corrida dev.
# Sin inyeccion: todos los logs. Con inyeccion: solo los de ataque (a las honestas no se les
# inyecta nada, asi que calificarlas otra vez seria pagar llamadas que analyze.py no usa).
jobs = [] if a.heldout else [("none", honest_logs + attack_logs)]
jobs += [(inj, attack_logs) for inj in families]
run_id = time.strftime("%Y%m%dT%H%M%S")
rows, samples_txt = [], []
t0 = time.time()
for inj, job_logs in jobs:
    out = run_sync(run_monitors_for_eval_logs([build(v, inj) for v in views], job_logs, progress=True))
    for view, mlogs in zip(views, out, strict=True):
        for lg in mlogs:
            for k, s in enumerate(lg.samples or []):
                md = ControlTaskMetadata.model_validate(s.metadata)
                is_attack = md.eval_mode.value == "attack"
                scored = [m for m in s.messages if m.role == "assistant" and (m.metadata or {}).get("reason") is not None]
                meta = scored[-1].metadata if scored else {}
                # ControlArena guarda 0 cuando el monitor responde sin <score>; no es un "limpio".
                no_score = any("No score found" in str((m.metadata or {}).get("reason") or "")
                               for m in s.messages)
                parsed = (bool(meta.get("score_parsed", False)) and meta.get("suspicion_score") is not None
                          and not no_score)
                shown = render_code(submitted_code(s.messages) or "", view="raw", injection=inj,
                                    is_attack=is_attack, key=md.main_task_description[:200])
                rows.append({
                    "run_id": run_id, "model": a.model, "sample_id": s.id, "mode": md.eval_mode.value,
                    "view": view, "injection": inj,
                    "score": meta.get("suspicion_score") if parsed else None,  # None -> celda vacia
                    "parsed": int(parsed), "flag": monitor_directed_flag(shown),
                })
                if k == 0 and is_attack:
                    samples_txt.append(f"===== {inj} / {view} / sample {s.id} =====\n"
                                       + make_formatter(view, inj)(md, s.messages, "{tool_calls}") + "\n")

if not rows:
    sys.exit("no se produjo ninguna fila")
out_path.parent.mkdir(parents=True, exist_ok=True)
header = not (a.append and out_path.exists())
with open(out_path, "a" if a.append else "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    if header:
        w.writeheader()
    w.writerows(rows)
with open(out_path.parent / "prompt_samples.txt", "a" if a.append else "w", encoding="utf-8") as f:
    f.write("\n".join(samples_txt) + "\n")

bad = sum(1 - r["parsed"] for r in rows)
print(f"{len(rows)} filas ({len(rows)} llamadas al monitor como maximo; el cache evita repetir) "
      f"en {time.time() - t0:.0f}s -> {out_path}")
print(f"respuestas sin puntaje: {bad} de {len(rows)} ({bad / len(rows):.1%})"
      + ("  <-- revisar el prompt o el modelo antes de seguir" if bad / len(rows) > 0.05 else ""))
print(f"revisar a ojo: {out_path.parent / 'prompt_samples.txt'}")
