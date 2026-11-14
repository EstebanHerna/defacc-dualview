"""Monitor estable: la defensa que sale de nuestra propia medicion.

Hallazgo: el puntaje de un monitor confiable se mueve ante cambios que NO alteran el
programa (una linea en blanco de mas). Entre el 6% y el 9% de las entregas cambian de
veredicto por ese ruido. Un atacante no necesita persuadir al monitor: le basta reenviar.

Defensa: en vez de leer la entrega una vez, se lee k veces sobre perturbaciones
semanticamente nulas (el mismo programa, escrito distinto) y se promedia. El ruido
independiente de cada lectura se cancela; la senal de sospecha no.

Cuesta k llamadas en vez de 1, no necesita reentrenar nada y funciona con cualquier
modelo usado como monitor.
"""
from dualview.sanitize import sanitize

# Perturbaciones que no cambian el programa. La primera es el codigo tal cual.
PERTURBACIONES_NULAS = ("raw", "raw_ws")


def variantes(code, vistas=PERTURBACIONES_NULAS):
    """Devuelve las versiones del mismo programa que hay que calificar."""
    out = []
    for v in vistas:
        if v == "raw":
            out.append(code)
        elif v == "raw_ws":
            out.append(code.rstrip("\n") + "\n\n")
        elif v == "stripped":
            out.append(sanitize(code)[0])
        else:
            raise ValueError("perturbacion desconocida: " + str(v))
    return out


def combinar(puntajes):
    """Promedio de las lecturas. Es la combinacion que medimos; el maximo iguala en
    deteccion pero hereda el ruido de la lectura mas alta."""
    vals = [p for p in puntajes if p is not None]
    if not vals:
        return None
    return sum(vals) / len(vals)


def puntuar(code, calificar, vistas=PERTURBACIONES_NULAS):
    """Puntaje estable de una entrega.

    calificar: funcion que recibe el texto del codigo y devuelve un puntaje 0 a 1
               (por ejemplo, una llamada al monitor confiable).
    """
    return combinar([calificar(v) for v in variantes(code, vistas)])
