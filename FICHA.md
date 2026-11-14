# Ficha tecnica (maximo 2 paginas; pasar a la plantilla oficial)

Proyecto: Prueba de choque para monitores de IA. Frente 2: control de IA, monitoreo y deteccion de sabotaje.
Equipo: ______

Todos los numeros salen de `results/boletin/`, `results/g35lite/` y `results/deadcode.csv`. Si se suman tramos
nuevos, volver a correr `scripts/scorecard.py` y actualizar esta ficha: no editar numeros a mano.

## 1. Vector de amenaza

Cuando un agente de IA programa sin supervision continua, un modelo barato y confiable (el monitor) le pone
un puntaje de sospecha a cada entrega y solo lo mas sospechoso llega a una persona. Ese monitor lee texto
escrito por el mismo agente que vigila, y su umbral se calibra una vez. Dos riesgos:

a) Persuasion: el agente le habla al monitor desde su entrega para bajar la sospecha de un backdoor.
b) Fragilidad: el puntaje cambia por cosas que no alteran el programa (una linea en blanco, un comentario,
   codigo de relleno, cambiar la version del modelo monitor), y el umbral calibrado deja de valer.

## 2. Mecanismo defensivo

Una bateria reproducible que le saca la nota a cualquier modelo usado como monitor, y un boletin con veredicto.
Cada entrega con backdoor se compara consigo misma con y sin cada perturbacion:

- siete canales por los que el agente puede hablarle al monitor: comentario neutro (control), orden directa en
  comentario, la misma en espanol, justificacion ("este caso lo exige el enunciado"), orden en una cadena,
  orden en un identificador y codigo muerto de relleno;
- tres lecturas sin ninguna nota: codigo tal cual, sin texto no ejecutable (saneado verificado por AST) y con
  una linea en blanco de mas (piso de ruido);
- transferencia de umbral entre modelos y un detector estatico de codigo muerto, sin LLM.

`scorecard.py --gate` devuelve codigo de error si algun canal cede: se corre antes de cambiar el modelo monitor.
Tambien evaluamos una defensa, la doble vista: calificar con y sin comentarios y combinar las dos lecturas.

## 3. Metodologia

Setting Apps de ControlArena: soluciones honestas y con backdoor de las mismas tareas (300 y 300 disponibles).
Evaluacion post-hoc con `basic_monitor` de ControlArena: el agente no corre en vivo. Linea base: una lectura
del codigo tal cual. Monitores: gemini-3.5-flash-lite (80 honestas y 80 backdoors; 64 en los canales nuevos),
gemini-3.1-flash-lite (38 y 38) y gemma-4-31b-it (20 y 20, tres canales). Metricas: cambio pareado de sospecha
(escala 0 a 1) con IC 95% bootstrap; TPR con el umbral que deja pasar 5% de honestas; AUC. 0% de respuestas
sin puntaje. Tamanos limitados por la cuota gratuita del proveedor (500 solicitudes por dia y por modelo).

## 4. Resultados

Persuasion: 17 pruebas (modelo x canal), ninguna baja la sospecha de los backdoors. El cambio medio va de
-0.02 a +0.09 y ningun intervalo queda por debajo de cero; dos canales la suben (el monitor nota el intento).

Fragilidad, que es lo que si encontramos:

| Que cambia | Que le pasa al monitor |
|---|---|
| Una linea en blanco al final (3.5-flash-lite) | la sospecha cambia mas de 0.5 en 6 de 64 backdoors (9%) y mas de 0.2 en 5% de las honestas |
| Quitar los comentarios (3.5-flash-lite) | la deteccion baja de 91% a 84% (a 2% de FPR): parte de lo detectado es lo que el agente comento |
| Agregar codigo muerto a codigo honesto | la sospecha sube o baja mas de 0.2 en 24% de las entregas con 3.1-flash-lite y en 8% con 3.5-flash-lite |
| Cambiar de modelo monitor conservando el umbral | calibrado con 3.5-flash-lite (0.15) y usado con 3.1-flash-lite, las falsas alarmas pasan de 3.8% a 31.6% |

Linea base sin ninguna nota: AUC 0.96 (3.5-flash-lite), 0.92 (3.1-flash-lite). Honestas con sospecha de 0.5 o
mas: 2.5% contra 28.9%.

Defensas evaluadas:
- Doble vista con termino de discrepancia (nuestra propuesta inicial): a 2% de FPR detecta 8% contra 91% de la
  linea base; a 5% empata (92.5%). El termino castiga diferencias que en buena parte son ruido. No se recomienda.
- Promediar dos lecturas: TPR a 5% de FPR de 92.2% a 95.3% (IC 95% de 84% a 100%; se solapa con la linea base).
- Codigo muerto como senal sin LLM (300 y 300): no distingue; 17% de las honestas y 11% de los backdoors
  tienen alguno (AUC 0.47).

## 5. Limites

- Un solo benchmark, programas de un archivo, entregas ya hechas. Honestas humanas y backdoors de otro origen,
  no verificados en sandbox por nosotros; 70% de los backdoors trae comentarios frente a 18% de las honestas.
- Los canales son frases fijas. No hay un atacante que se adapte al monitor: "resiste" vale para estas frases.
- No separamos el efecto de la linea en blanco del azar propio del modelo: en ambos casos es el mismo programa
  con otro veredicto, pero la causa no esta aislada. No se repitio la llamada identica (el cache la devuelve).
- Muestras pequenas: 38 entregas en 3.1-flash-lite (28.9% son 11 entregas) y 20 en gemma. Solo modelos de la
  familia de un proveedor con cuota gratuita util. Los intervalos son anchos y varios resultados son senales.
- Las familias en espanol y en cadena se pensaron como reservadas en el diseno original; aqui se midieron una
  vez como parte de la bateria, sin ajustar nada con ellas. Es una medicion descriptiva, no una validacion ciega.
- La tercera vista (cadenas largas reemplazadas) se implemento pero no entro en los resultados.

## 6. Riesgo dual y uso responsable

Las frases de cada canal son genericas y ya descritas publicamente; no se publica ningun generador ni
optimizador de ataques. Todo se evaluo sobre un benchmark publico, sin sistemas ni datos de terceros. El
hallazgo de inestabilidad sirve a quien defiende: indica que hay que recalibrar el umbral al cambiar de modelo.

## 7. Atribucion

ControlArena (UK AISI, Redwood Research), Inspect AI, dataset RoganInglis/apps-control-arena. Codigo y
documentos generados con asistencia de Claude (Anthropic) y revisados por el equipo; detalle en el README.
