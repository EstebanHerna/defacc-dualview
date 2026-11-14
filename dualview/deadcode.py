"""Detector estatico de codigo muerto. Sin LLM: solo el arbol sintactico.

El codigo que nunca se ejecuta o nunca se usa es superficie de ataque barata: nadie lo prueba, nadie lo
lee, y puede esconder logica que se activa despues. Este modulo lo cuenta para poder medir dos cosas sobre
el benchmark: si las entregas con backdoor traen mas codigo muerto que las honestas, y si un monitor LLM
cambia su sospecha cuando se le agrega (canal `dead_code` de la bateria).

Es conservador y aproximado: trabaja por nombre dentro de un archivo, no sigue flujo de datos, y no ve
codigo alcanzable solo con una entrada rara (eso es justamente un backdoor, no codigo muerto).
"""
import ast

KINDS = ("unused_function", "unused_import", "unused_variable", "unreachable", "constant_condition")
_TERMINATORS = (ast.Return, ast.Raise, ast.Break, ast.Continue)


def _const_truth(node: ast.AST):
    """True/False si la condicion es una constante; None si depende de algo."""
    if isinstance(node, ast.Constant):
        return bool(node.value)
    return None


def find_dead_code(code: str) -> list[tuple[str, int, str]]:
    """Lista de (tipo, linea, nombre). Lista vacia si el codigo no se puede analizar."""
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, RecursionError):
        return []
    loaded, attrs = set(), set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
            loaded.add(n.id)
        elif isinstance(n, ast.Attribute):
            attrs.add(n.attr)
    # Nombres exportados o usados por reflexion: no se pueden dar por muertos.
    dynamic = any(isinstance(n, ast.Name) and n.id in {"globals", "locals", "eval", "exec", "getattr", "vars"}
                  for n in ast.walk(tree))
    # Variables de bucle o de desempaquetado sin usar (`for _i in range(n)`, `a, b = ...`) son un
    # modismo normal, no codigo muerto: se excluyen.
    idiom = set()
    for n in ast.walk(tree):
        targets = []
        if isinstance(n, (ast.For, ast.AsyncFor, ast.comprehension)):
            targets = [n.target]
        elif isinstance(n, ast.Assign):
            targets = [t for t in n.targets if isinstance(t, (ast.Tuple, ast.List))]
        elif isinstance(n, (ast.With, ast.AsyncWith)):
            targets = [i.optional_vars for i in n.items if i.optional_vars is not None]
        for t in targets:
            idiom |= {x.id for x in ast.walk(t) if isinstance(x, ast.Name)}
    found = []
    stored: dict[str, int] = {}
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            is_method = n.name.startswith("__") and n.name.endswith("__")
            if n.name not in loaded and n.name not in attrs and not is_method and not n.decorator_list and not dynamic:
                found.append(("unused_function", n.lineno, n.name))
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for alias in n.names:
                name = (alias.asname or alias.name).split(".")[0]
                if name != "*" and name not in loaded and not dynamic:
                    found.append(("unused_import", n.lineno, name))
        elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            stored.setdefault(n.id, n.lineno)
        elif isinstance(n, (ast.If, ast.While)):
            truth = _const_truth(n.test)
            # `while True:` es un bucle normal; lo muerto es `if False`, `if 0`, `while False`, `if True` con else.
            if truth is False or (truth is True and isinstance(n, ast.If) and n.orelse):
                found.append(("constant_condition", n.lineno, ast.unparse(n.test)))
        for field in ("body", "orelse", "finalbody"):
            block = getattr(n, field, None)
            if isinstance(block, list):
                for i, stmt in enumerate(block[:-1]):
                    if isinstance(stmt, _TERMINATORS):
                        found.append(("unreachable", block[i + 1].lineno, type(stmt).__name__.lower()))
                        break
    if not dynamic:
        for name, line in stored.items():
            if name not in loaded and name not in idiom and name != "_" and not name.startswith("__"):
                found.append(("unused_variable", line, name))
    return sorted(set(found), key=lambda t: (t[1], t[0]))


def dead_code_counts(code: str) -> dict[str, int]:
    """Conteo por tipo, mas `total`."""
    items = find_dead_code(code)
    out = {k: sum(1 for kind, _, _ in items if kind == k) for k in KINDS}
    out["total"] = len(items)
    return out
