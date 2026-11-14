"""Que ve el monitor: vista (raw, stripped o nostr) y condicion (ninguna o una familia de TEMPLATES)."""
import json
import zlib
from collections.abc import Sequence
from html import escape

from inspect_ai.model import ChatMessage

from control_arena import EvalMode
from control_arena._control_task_metadata import ControlTaskMetadata
from control_arena.monitor import get_last_assistant_message

from .injections import ALL_MODES, TEMPLATES
from .sanitize import neutralize_strings, sanitize

# raw_ws: el mismo codigo con una linea en blanco al final. No cambia nada para un lector; sirve para
# medir cuanto se mueve el puntaje del monitor ante un cambio sin significado (piso de ruido).
# raw_rep: exactamente el mismo texto que raw. run_monitors la pide sin cache, asi que es una segunda
# lectura independiente del mismo prompt: mide el azar propio del modelo.
VIEWS = ("raw", "stripped", "nostr", "raw_ws", "raw_rep")
DEFAULT_VIEWS = ("raw", "stripped")


def render_code(code: str, *, view: str, injection: str | None, is_attack: bool, key: str) -> str:
    """Codigo tal como se le muestra al monitor. La condicion solo aplica a entregas de ataque y
    siempre antes de construir la vista, asi todas las vistas parten de exactamente la misma entrega."""
    assert view in VIEWS, view
    if injection and injection != "none" and (is_attack or injection in ALL_MODES):
        options = TEMPLATES[injection]
        code = options[zlib.crc32(key.encode()) % len(options)] + "\n" + code
    if view == "stripped":
        code, _ = sanitize(code)
    elif view == "nostr":
        code, _ = neutralize_strings(code)
    elif view == "raw_ws":
        code = code.rstrip("\n") + "\n\n"
    return code


def submitted_code(messages: Sequence[ChatMessage]) -> str | None:
    for tc in get_last_assistant_message(messages).tool_calls or []:
        if isinstance(tc.arguments.get("code"), str):
            return tc.arguments["code"]
    return None


def make_formatter(view: str = "raw", injection: str | None = None):
    def formatter(task_metadata: ControlTaskMetadata, messages: Sequence[ChatMessage], prompt: str) -> str:
        is_attack = task_metadata.eval_mode == EvalMode.ATTACK
        key = task_metadata.main_task_description[:200]
        lines = []
        for tc in get_last_assistant_message(messages).tool_calls or []:
            args = {k: v for k, v in tc.arguments.items() if k != "secret_input"}
            if isinstance(args.get("code"), str):
                args["code"] = render_code(args["code"], view=view, injection=injection, is_attack=is_attack, key=key)
            lines.append(f"{escape(tc.function, quote=False)}: {escape(json.dumps(args), quote=False)}")
        # replace y no format: el prompt puede contener llaves sin romperse
        return (prompt.replace("{task_description}", task_metadata.main_task_description)
                      .replace("{tool_calls}", "\n".join(lines)))

    return formatter
