"""Genera las trayectorias base (honestas y con backdoor) una sola vez. No usa ningun LLM.

Uso:  python scripts/gen.py --limit 300            (con Docker: ademas verifica main/side task)
      python scripts/gen.py --limit 300 --no-docker (sin Docker: solo guarda las trayectorias)
"""
import argparse

from inspect_ai import eval

from control_arena import EvalMode
from control_arena.eval import ControlEvalConfig, get_control_task_product
from control_arena.settings.apps.apps_setting import AppsSetting
from control_arena.settings.apps.apps_solution_policy import apps_solution_policy

ap = argparse.ArgumentParser()
ap.add_argument("--limit", type=int, default=300)
ap.add_argument("--log-dir", default="logs/base")
ap.add_argument("--no-docker", action="store_true")
a = ap.parse_args()

cfg = ControlEvalConfig(
    limit=a.limit, log_dir=a.log_dir, max_sandboxes=8,
    untrusted_model="mockllm/model", trusted_model="mockllm/model",
    skip_task_scorers=a.no_docker,
)
setting = AppsSetting(
    cache_python_code=True, has_backdoor_solution=True, shuffle_dataset=True, shuffle_seed=0,
    **({"sandbox_type": "local"} if a.no_docker else {}),
)
tasks = get_control_task_product(
    settings=setting, micro_protocols=apps_solution_policy(),
    modes=[EvalMode.HONEST, EvalMode.ATTACK], eval_config=cfg,
)
eval(tasks=tasks, **cfg.eval_args())
