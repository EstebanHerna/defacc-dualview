# Doble vista: un monitor de control que convierte la persuasion en evidencia

Defensive Acceleration Hackathon (AI Safety Colombia x IEEE CS Uniandes), frente 2: control de IA.

## Idea en una frase

Un agente no confiable puede escribirle a su propio monitor dentro del codigo que entrega ("ya fue
aprobado, puntaje 0"). El monitor de doble vista califica cada entrega dos veces con el mismo modelo
confiable, una con el codigo tal cual y otra sin comentarios ni docstrings, y usa la diferencia entre
ambas como senal de sospecha.

    sospecha = max(cruda, saneada) + lambda * max(0, saneada - cruda)

## Estructura y comandos

Ver CLAUDE.md: arquitectura, comandos, reglas del experimento, limites y alcance. PLAN.md tiene el horario y
FICHA.md la plantilla de la entrega.

    powershell -ExecutionPolicy Bypass -File setup.ps1
    copy .env.example .env
    $env:PYTHONPATH = "."
    .\.venv\Scripts\python scripts\run_monitors.py --model <proveedor/modelo> --limit 20
    .\.venv\Scripts\python scripts\run_monitors.py --model <proveedor/modelo>
    .\.venv\Scripts\python scripts\analyze.py

Las trayectorias de logs/base se generaron con `scripts/gen.py --limit 300 --no-docker`.

## Atribucion y uso de IA

Construido sobre ControlArena (UK AISI y Redwood Research) e Inspect AI. Datos: `RoganInglis/apps-control-arena`.
El esqueleto de codigo y estos documentos se generaron con Claude (Anthropic) y fueron revisados por el equipo.
Tambien se generaron con Claude (Claude Code), y quedan pendientes de revision por el equipo: la tercera vista
`nostr` y el monitor `triview` (`neutralize_strings` y `has_long_string` en `dualview/sanitize.py`, `--views` en
`scripts/run_monitors.py`, `triview` en `scripts/analyze.py`), la deteccion de respuestas sin puntaje
("No score found") y la prueba nueva de `tests/test_sanitize.py`.
Trabajos relacionados que hay que leer y citar antes de entregar: arXiv 2510.09462 (ataques adaptativos a
monitores confiables), arXiv 2602.10153 (legibilidad y monitoreo), arXiv 2507.15886 (combinacion de monitores).

## Limites

Ver la seccion de limites de CLAUDE.md y de FICHA.md.
