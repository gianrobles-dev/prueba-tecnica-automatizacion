# Decisiones y justificaciones de lo encontrado para el Desarrollo de la automatizacion solicitada

### 1. ¿Qué resolviste con el modelo de lenguaje y qué resolviste sin él? ¿Por qué?
- **Sin LLM (Preprocesamiento)**: Validación de nulos/vacíos, extracción del código `REF-AAAA-NNNN` (vía Regex case-insensitive), detección de inyección de prompts (búsqueda de keywords) y enmascaramiento de PII. 
- **Con LLM**: Clasificación semántica (categoría) y determinación de urgencia basada en el tono del mensaje.
- **Por qué**: El LLM es costoso, no determinista y lento. Usarlo para extraer un patrón fijo como un código de referencia o filtrar textos vacíos es un anti-patrón. El LLM solo debe intervenir donde la semántica y la ambigüedad del lenguaje natural lo requieran.

### 2. ¿Qué encontraste en los datos que te obligó a tomar una decisión? (Casos borde)
- **PII Real no anonimizado**: El registro `SOL-01042` contiene una cédula (`1719384756`) y un celular, a pesar de que el enunciado indicaba "anonimizadas".
- **Prompt Injection**: Los registros `SOL-01063` y `SOL-01071` contienen instrucciones maliciosas del tipo *"ignora las reglas anteriores"*.
- **Ataque por longitud/DoS**: El registro `SOL-01110` es un bloque de texto repetitivo gigante. 
- **Duplicados y formatos**: IDs duplicados (`SOL-01042`, `SOL-01077`) y códigos de referencia en minúsculas (`ref-2026-1033` en `SOL-01080`).

### 3. ¿Qué hiciste con la información personal de los clientes, y por qué?
Implementé un enmascaramiento (PII Masking) mediante expresiones regulares *antes* de que el texto llegue al prompt del LLM. En un entorno de producción real, esto se delegaría a una herramienta especializada como *Microsoft Presidio* o *Azure AI Language PII*. Esto es crítico para cumplir con normativas de protección de datos y evitar que el proveedor del LLM almacene o entrene con información sensible.

### 4. ¿Cómo desplegarías esto en Azure para que corra todos los días a las 6:00 AM?
- **Orquestación**: Azure Data Factory (ADF) o Logic Apps para disparar el proceso a las 6:00 AM.
- **Cómputo**: Azure Container Instances (ACI) o Azure Functions (Python) que ejecutan el script.
- **Secretos**: Almacenados exclusivamente en **Azure Key Vault**. La función/contenedor accede a ellos mediante *Managed Identity*, eliminando la necesidad de credenciales en el código o variables de entorno planas.
- **Monitoreo**: Application Insights para trazas y métricas. Si la tasa de error supera un umbral o el script falla, Azure Monitor dispara una alerta a un canal de Teams o PagerDuty.

### 5. ¿Qué se rompe si mañana el lote pasa de 40 a 50.000 registros?
El cuello de botella sería la API del LLM: límites de tasa (Rate Limits), latencia acumulada y costo explosivo. 
**Solución**: Migrar a la **Batch API de OpenAI** (que reduce el costo en un 50% y está diseñada para trabajos asíncronos de gran volumen) o implementar un sistema de colas con **Azure Service Bus** y múltiples workers escalables para procesar en paralelo.

### 6. ¿Qué dejaste fuera por tiempo y qué harías con dos días más?
Dejé fuera: pruebas unitarias exhaustivas con `pytest` (mockeando las respuestas del LLM), un pipeline de CI/CD en GitHub Actions que bloquee commits con secretos, y el uso de *Structured Outputs* (JSON Mode estricto) de OpenAI para garantizar el esquema de salida sin necesidad de parseo defensivo. Con dos días más, también implementaría un dashboard de monitoreo para medir la "deriva" del modelo y la tasa de falsos positivos en la revisión humana.

### 7. Notas adicionales
- El script fue diseñado para ser ejecutado con un solo comando: `python main.py`.
- En modo simulado, el clasificador heurístico (MockLLM) utiliza reglas basadas en palabras clave para emular el comportamiento de un LLM real.
- Todos los archivos de salida (`salida.jsonl`) están excluidos del repositorio vía `.gitignore` para mantener el repo limpio.