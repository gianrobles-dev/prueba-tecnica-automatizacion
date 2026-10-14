# Prueba técnica — Desarrollador de Automatización e Integraciones

**Tiempo sugerido: 3 horas.** No buscamos que esté perfecto. Buscamos ver cómo piensas, qué decides y qué dejas fuera a propósito.

## Sobre el uso de IA

**Puedes y debes usar asistentes de IA** (Claude, Copilot, ChatGPT, lo que uses a diario). No es trampa, es la herramienta de trabajo.

Dicho eso: **vas a sustentar tu solución en una sesión de 30 minutos**, donde te pediremos explicar decisiones puntuales y modificar el código en vivo. Entregar algo que no entiendes es la forma más rápida de no pasar.

## El caso

Operamos procesos de atención para clientes del sector financiero. Cada día llega un lote de solicitudes de clientes en texto libre, desde distintos canales. Hoy un equipo las lee y clasifica a mano. Tu tarea es automatizar ese triage.

**Entrada:** `data/solicitudes_oct.jsonl` — 40 solicitudes reales (anonimizadas), una por línea.

**Salida esperada:** un `salida.jsonl` donde cada registro procesado tenga esta forma:

```json
{
  "id": "SOL-01042",
  "categoria": "consulta_saldo",
  "urgencia": "media",
  "codigo_referencia": null,
  "confianza": 0.91,
  "requiere_revision_humana": false,
  "motivo_revision": null
}
```

**Categorías válidas** (y solo estas): `consulta_saldo` · `reclamo_cobro` · `bloqueo_tarjeta` · `actualizacion_datos` · `solicitud_producto` · `no_clasificable`

**Urgencia:** `alta` · `media` · `baja`

**`codigo_referencia`:** si la solicitud menciona un código con formato `REF-AAAA-NNNN`, extráelo. Si no, `null`.

## Requisitos

1. **Debe correr con un solo comando** documentado en este README. Si no arranca en el primer intento, se evalúa como no entregado.
2. **Python.**
3. **Debe usar un modelo de lenguaje** para la parte que lo amerite. Cuál proveedor es tu decisión.
4. **Ningún secreto en el repositorio.** Incluye un `.env.example`; nunca un `.env` con valores reales.
5. **Debe poder ejecutarse sin API key**, en modo simulado, para que podamos correrlo nosotros. Cómo lo resuelves es parte de lo que evaluamos.
6. **Historial de commits real.** Queremos ver el avance, no un único commit al final.
7. **Además de `salida.jsonl`**, imprime al terminar un resumen: registros leídos, procesados, descartados, enviados a revisión humana, y llamadas al modelo realizadas.

## Entregable adicional: `DECISIONES.md`

Máximo una página. Es la parte más importante de la entrega. Responde, en tus palabras:

1. **¿Qué resolviste con el modelo de lenguaje y qué resolviste sin él?** ¿Por qué trazaste la línea ahí?
2. **¿Qué encontraste en los datos que te obligó a tomar una decisión?** Sé específico.
3. **¿Qué hiciste con la información personal de los clientes, y por qué?**
4. **¿Cómo desplegarías esto en Azure** para que corra todos los días a las 6:00 AM? Dónde viven los secretos, qué servicio usarías, cómo sabrías que falló. No necesitas desplegarlo — solo explicarlo.
5. **¿Qué se rompe si mañana el lote pasa de 40 a 50.000 registros?**
6. **¿Qué dejaste fuera por tiempo y qué harías con dos días más?**

## Entrega

Repositorio Git (GitHub, GitLab) o un `.zip` con el historial `.git` incluido. Envíalo al contacto que te compartió esta prueba.

## Cómo se evalúa

| Criterio | Peso |
|---|---|
| Criterio técnico: qué va al modelo y qué no | 25% |
| Manejo de los datos reales y sus casos borde | 20% |
| Despliegue y manejo de secretos | 20% |
| Calidad y claridad del código | 15% |
| `DECISIONES.md` | 10% |
| Sustentación en vivo | 10% |

**Descalifica automáticamente:** un secreto commiteado al repositorio.

¿Dudas sobre el enunciado? Pregunta. Saber qué preguntar también es parte del trabajo.




# Prueba Técnica: Automatización de Triage de Solicitudes

## Descripción
Automatización del proceso de clasificación y triage de solicitudes de clientes del sector financiero. El sistema procesa un lote de solicitudes en formato JSONL, extrae patrones, enmascara datos sensibles y utiliza un modelo de lenguaje (con fallback a modo simulado) para categorizar y priorizar cada caso.

## Requisitos Previos
- Python 3.9 o superior.
- (Opcional) Una API Key de OpenAI si se desea ejecutar con el modelo real.

## Instalación y Ejecución

1. Clona este repositorio y navega a la carpeta del proyecto.
2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
