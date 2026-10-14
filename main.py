import json
import os
import re
import logging
from dotenv import load_dotenv

# Configuración
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()

INPUT_FILE = "data/solicitudes_oct.jsonl"
OUTPUT_FILE = "salida.jsonl"

VALID_CATEGORIES = [
    "consulta_saldo", "reclamo_cobro", "bloqueo_tarjeta", 
    "actualizacion_datos", "solicitud_producto", "no_clasificable"
]
VALID_URGENCIES = ["alta", "media", "baja"]

# Regex para código de referencia (Case-insensitive para atrapar 'ref-2026-1033')
REF_REGEX = re.compile(r"(?i)\bREF-[A-Z0-9]{4}-[0-9]{4}\b")

# Palabras clave para detectar inyección de prompts (Jailbreak)
INJECTION_KEYWORDS = [
    "nuevas instrucciones", "ignora las reglas", "nota para el asistente", 
    "ignora las instrucciones anteriores", "nuevas instrucciones del sistema"
]

def extract_reference_code(text: str) -> str | None:
    """Extrae el código de referencia si existe, normalizado a mayúsculas."""
    match = REF_REGEX.search(text)
    return match.group(0).upper() if match else None

def detect_prompt_injection(text: str) -> bool:
    """Detecta intentos de manipular el comportamiento del LLM."""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in INJECTION_KEYWORDS)

def mask_pii(text: str) -> str:
    """Enmascara datos sensibles (Cédulas de 10 dígitos, Celulares, Tarjetas de 16) antes de enviar al LLM."""
    # Enmascarar secuencias de 10 dígitos (cédula/celular típico de Ecuador/Latam por el contexto de los datos)
    text = re.sub(r'\b\d{10}\b', '[DATOS_PERSONALES_OCULTOS]', text)
    # Enmascarar números de tarjeta (con o sin espacios)
    text = re.sub(r'\b\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b', '[TARJETA_OCULTA]', text)
    return text


class MockLLM:
    """Clasificador heurístico local para modo simulado (sin API Key)."""
    def classify(self, text: str) -> dict:
        text_lower = text.lower()
        
        # Heurística básica basada en palabras clave
        if any(w in text_lower for w in ["saldo", "cupo", "balance", "disponible", "debo pagar"]):
            cat = "consulta_saldo"
        elif any(w in text_lower for w in ["cobro", "reclamo", "reversión", "duplicado", "mora", "interés"]):
            cat = "reclamo_cobro"
        elif any(w in text_lower for w in ["bloqueo", "perdí", "robaron", "clonaron", "no reconozco"]):
            cat = "bloqueo_tarjeta"
        elif any(w in text_lower for w in ["actualizar", "cambiar", "dirección", "domicilio", "correo", "celular"]):
            cat = "actualizacion_datos"
        elif any(w in text_lower for w in ["solicito", "requisitos", "tarjeta adicional", "aumento de cupo"]):
            cat = "solicitud_producto"
        else:
            cat = "no_clasificable"
            
        urg = "alta" if any(w in text_lower for w in ["urgente", "ya", "inmediato", "robaron"]) else "media"
        
        return {"categoria": cat, "urgencia": urg, "confianza": 0.75}

class OpenAILLM:
    """Cliente para OpenAI con fallback a MockLLM si falla o no hay librería."""
    def __init__(self, api_key: str):
        self.available = False
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
            self.available = True
        except ImportError:
            logging.warning("Paquete 'openai' no instalado. Usando MockLLM.")
        except Exception as e:
            logging.warning(f"Error inicializando OpenAI: {e}. Usando MockLLM.")

    def classify(self, text: str) -> dict:
        if not self.available:
            return MockLLM().classify(text)
        
        prompt = f"""Eres un asistente de triage bancario. Clasifica la siguiente solicitud.
Categorías permitidas: {', '.join(VALID_CATEGORIES)}
Urgencias permitidas: {', '.join(VALID_URGENCIES)}
Texto del cliente: "{text}"

Responde ÚNICAMENTE con un objeto JSON válido con este formato exacto:
{{"categoria": "...", "urgencia": "...", "confianza": 0.95}}"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini", # Modelo rápido y económico
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            
            # Validación de defensa en profundidad
            if result.get("categoria") not in VALID_CATEGORIES:
                result["categoria"] = "no_clasificable"
            if result.get("urgencia") not in VALID_URGENCIES:
                result["urgencia"] = "media"
                
            return result
        except Exception as e:
            logging.error(f"Error llamando a OpenAI: {e}. Fallback a MockLLM.")
            return MockLLM().classify(text)

def get_llm_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and api_key.startswith("sk-"):
        logging.info(" Modo REAL: Usando OpenAI LLM.")
        return OpenAILLM(api_key), True
    logging.info("Modo SIMULADO: No hay API Key válida. Usando MockLLM (Heurístico).")
    return MockLLM(), False


if __name__ == "__main__":
    llm_client, is_real_llm = get_llm_client()
    
    stats = {
        "leidos": 0, "procesados": 0, "descartados": 0, 
        "revision_humana": 0, "llamadas_modelo": 0
    }
    seen_ids = set()
    
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as infile, \
             open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
            
            for line in infile:
                stats["leidos"] += 1
                try:
                    record = json.loads(line.strip())
                except json.JSONDecodeError:
                    stats["descartados"] += 1
                    continue
                    
                req_id = record.get("id")
                texto = record.get("texto")
                
                # 1. Descartar nulos o vacíos
                if not texto or not str(texto).strip():
                    stats["descartados"] += 1
                    continue
                texto = str(texto).strip()
                
                # 2. Detectar duplicados
                es_duplicado = req_id in seen_ids
                seen_ids.add(req_id)
                
                # 3. Extraer REF (Sin LLM)
                codigo_ref = extract_reference_code(texto)
                
                # 4. Banderas de Revisión Humana
                requiere_revision = False
                motivo_revision = None
                
                if detect_prompt_injection(texto):
                    requiere_revision = True
                    motivo_revision = "Posible inyección de prompt detectada"
                elif len(texto) > 1000: # Caso SOL-01110 (texto gigante)
                    requiere_revision = True
                    motivo_revision = "Texto anómalo o excesivamente largo"
                elif es_duplicado:
                    requiere_revision = True
                    motivo_revision = "ID duplicado en el lote"
                    
                # 5. Preparar texto para el LLM (Truncar si es muy largo para ahorrar tokens)
                texto_para_llm = texto[:800] if len(texto) > 1000 else texto
                texto_seguro = mask_pii(texto_para_llm) # Enmascarar PII
                
                # 6. Llamar al LLM
                stats["llamadas_modelo"] += 1
                clasificacion = llm_client.classify(texto_seguro)
                
                # Si requiere revisión, bajamos la confianza artificialmente
                if requiere_revision:
                    clasificacion["confianza"] = 0.15 
                
                # 7. Generar Salida
                output_record = {
                    "id": req_id,
                    "categoria": clasificacion["categoria"],
                    "urgencia": clasificacion["urgencia"],
                    "codigo_referencia": codigo_ref,
                    "confianza": round(clasificacion["confianza"], 2),
                    "requiere_revision_humana": requiere_revision,
                    "motivo_revision": motivo_revision
                }
                outfile.write(json.dumps(output_record, ensure_ascii=False) + "\n")
                stats["procesados"] += 1
                if requiere_revision:
                    stats["revision_humana"] += 1

        # Resumen final (Requisito del enunciado)
        print("\n" + "="*40)
        print("RESUMEN DE PROCESAMIENTO")
        print("="*40)
        print(f"Registros leídos:           {stats['leidos']}")
        print(f"Registros procesados:       {stats['procesados']}")
        print(f"Registros descartados:      {stats['descartados']}")
        print(f"Enviados a revisión humana: {stats['revision_humana']}")
        print(f"Llamadas al modelo:         {stats['llamadas_modelo']} (Reales: {stats['llamadas_modelo'] if is_real_llm else 0})")
        print("="*40 + "\n")
        print(f"Archivo de salida generado: {OUTPUT_FILE}")

    except FileNotFoundError:
        logging.error(f"No se encontró el archivo de entrada: {INPUT_FILE}")
        print("Asegúrate de que la carpeta 'data/' y el archivo 'solicitudes_oct.jsonl' existan.")