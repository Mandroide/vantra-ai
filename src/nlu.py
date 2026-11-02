"""Comprensión de texto del modo DEMO: normalización tolerante, números en palabras e intenciones.

Mitigaciones de la Fase 3, diseñadas a partir de los fallos del held-out v1 (conjunto de desarrollo):

1. Tolerancia a errores de transcripción con reglas fonéticas generales del español caribeño, no con una tabla
   copiada del generador de ruido: seseo (z -> s), aspiración de la s final ("mese" -> "meses"), elisiones
   frecuentes ("pa", "ta", "toy") y corrección aproximada contra un vocabulario del dominio.
2. Montos y plazos escritos en palabras ("doscientos cincuenta mil", "tres años") se convierten a dígitos.
3. Intenciones críticas (privacidad, consentimiento, exclusión de llamadas, fraude) se detectan con familias de
   sinónimos y se evalúan antes que las operativas en src/agent.py.

Todas las funciones son puras y deterministas; no hay llamadas externas.
"""
from __future__ import annotations

import difflib
import re
import unicodedata

# ----------------------------------------------------------------------------- normalización
VOCAB = {
    "tarjeta", "tarjetas", "prestamo", "prestamos", "personal", "certificado", "certificados", "financiero",
    "tasa", "interes", "intereses", "cuota", "cuotas", "mensual", "mensualidad", "meses", "pesos", "plazo",
    "requisitos", "documentos", "persona", "personas", "humano", "representante", "ejecutivo", "asesor",
    "agente", "empleado", "operador", "fraude", "clonaron", "robaron", "cargo", "compra", "grabacion",
    "grabada", "grabar", "consentimiento", "audio", "contrasena", "cuenta", "saldo", "balance", "llamada",
    "llamadas", "llamar", "llamen", "aprobado", "aprobada", "aprobacion", "aprobar", "credito", "queja",
    "reclamacion", "servicio", "insatisfecho", "inconformidad", "cotizacion", "calcular", "lista", "numero",
    "contactos", "seguimiento", "devolucion", "transferir", "comunique", "conversacion",
}
ELISIONES = {"pa": "para", "pal": "para el", "ta": "esta", "tan": "estan", "toy": "estoy", "na": "nada",
             "e": "es", "to": "todo", "tamo": "estamos"}


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(c))


def _fix_token(tok: str) -> str:
    if not tok or tok.isdigit() or tok in VOCAB or tok in _UNIDADES or tok in ("mil", "millon", "millones"):
        return tok
    if tok in ELISIONES:
        return ELISIONES[tok]
    seseo = tok.replace("z", "s")  # seseo caribeño: "taza" -> "tasa"
    if seseo in VOCAB:
        return seseo
    if tok + "s" in VOCAB:  # s final aspirada: "mese" -> "meses"
        return tok + "s"
    if len(tok) >= 5:  # elisiones de r, d, s: "tajeta", "certificao"
        # Solo candidatos con la misma letra inicial: el reconocimiento de voz rara vez cambia el inicio de la
        # palabra, y así se evita, por ejemplo, que «aprobaron» se convierta en «robaron».
        # Además, el candidato no puede ser más corto que la palabra: las elisiones acortan o deforman, no alargan
        # («interesa» es otra palabra, no un error de «interés»).
        pool = [v for v in VOCAB if v[0] == seseo[0] and len(v) >= len(seseo)]
        near = difflib.get_close_matches(seseo, pool, n=1, cutoff=0.84)
        if near:
            return near[0]
    return tok


# ----------------------------------------------------------------------------- números en palabras
_UNIDADES = {"cero": 0, "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6,
             "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14,
             "quince": 15, "dieciseis": 16, "diecisiete": 17, "dieciocho": 18, "diecinueve": 19, "veinte": 20,
             "veintiun": 21, "veintiuno": 21, "veintidos": 22, "veintitres": 23, "veinticuatro": 24,
             "veinticinco": 25, "veintiseis": 26, "veintisiete": 27, "veintiocho": 28, "veintinueve": 29,
             "treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "setenta": 70, "ochenta": 80,
             "noventa": 90, "cien": 100, "ciento": 100, "doscientos": 200, "trescientos": 300,
             "cuatrocientos": 400, "quinientos": 500, "seiscientos": 600, "setecientos": 700,
             "ochocientos": 800, "novecientos": 900, "medio": 0.5}
_TRIVIALES = {"un", "uno", "una", "medio"}


def _flush(seq: list[str]) -> str | None:
    """Convierte una secuencia de palabras numéricas a dígitos; None si no conviene convertirla."""
    words = [w for w in seq if w != "y"]
    if not words or (all(w in _TRIVIALES for w in words)):
        return None
    total, current = 0.0, 0.0
    for w in words:
        if w in ("millon", "millones"):
            total += (current or 1) * 1_000_000
            current = 0
        elif w == "mil":
            current = (current or 1) * 1000
        else:
            current += _UNIDADES[w]
    value = total + current
    return str(int(value)) if value == int(value) else str(value)


def words_to_numbers(tokens: list[str]) -> list[str]:
    out, seq = [], []
    numeric = set(_UNIDADES) | {"mil", "millon", "millones"}
    for i, tok in enumerate(tokens):
        nxt = tokens[i + 1] if i + 1 < len(tokens) else ""
        if (tok in ("mil", "millon", "millones") and not seq and out
            and re.fullmatch(r"\d+(\.\d+)?", out[-1])):
            out.append(tok)  # «200 mil» ya es un monto; lo lee amounts()
            continue
        if tok in numeric or (tok == "y" and seq and nxt in _UNIDADES):
            seq.append(tok)
            continue
        if seq:
            conv = _flush(seq)
            out.extend([conv] if conv else seq)
            seq = []
        out.append(tok)
    if seq:
        conv = _flush(seq)
        out.extend([conv] if conv else seq)
    return out


def canon(text: str) -> str:
    """Texto canónico: minúsculas sin tildes, sin signos, con errores típicos corregidos y números en dígitos."""
    t = strip_accents(text or "")
    t = re.sub(r"(?<=\d)[.,](?=\d{3}\b)", "", t)  # 200.000 / 200,000 -> 200000
    t = re.sub(r"(?<=\d)[.,](?=\d)", ".", t)  # 1,5 millones -> 1.5 millones
    t = re.sub(r"[^\w.\s]", " ", t).replace("_", " ")
    t = re.sub(r"(?<!\d)\.|\.(?!\d)", " ", t)
    tokens = [_fix_token(tok) for tok in t.split()]
    tokens = " ".join(tokens).split()  # las elisiones pueden expandir a dos palabras
    return " ".join(words_to_numbers(tokens))


# ----------------------------------------------------------------------------- montos y plazos
def amounts(t: str) -> list[float]:
    """Montos en pesos a partir de texto canónico. Corrige el caso '1 millon' que antes se leía como 1,000."""
    vals = []
    for m in re.finditer(r"(?<![\d.])(\d+(?:\.\d+)?)\s*(millones|millon|mil)?\b", t):
        v = float(m.group(1))
        mult = {"mil": 1e3, "millon": 1e6, "millones": 1e6}.get(m.group(2) or "", 1)
        vals.append(v * mult)
    return vals


def months(t: str) -> int | None:
    m = re.search(r"\b(\d+)\s*(anos?|meses?)\b", t)
    if not m:
        return None
    n = int(m.group(1))
    return n * 12 if m.group(2).startswith("ano") else n


# ----------------------------------------------------------------------------- intenciones
def _any(t: str, patterns) -> bool:
    return any(re.search(p, t) for p in patterns)


PRIVACIDAD = [r"numero de (la )?cuenta", r"\bmi saldo\b", r"\bsaldo\b", r"\bbalance\b", r"contrasen\w*",
              r"password", r"clave bancaria", r"\bclave\b", r"\bpin\b", r"datos de otro cliente", r"cedula real",
              r"cuanto (dinero |cuartos? )?tengo", r"\bcuartos?\b.{0,25}\bcuenta\b", r"cuanto debe\b",
              r"movimientos", r"cuenta de (mi|otro|otra|otra gente)"]
CONSENTIMIENTO = [r"\b(no|retiro|rechazo)\b(\s+\w+){0,6}?\s+(grab\w*|voz|audio\w*|consentimiento)",
                  r"(grab\w*|voz|audio\w*)\b(\s+\w+){0,6}?\s+no\s+(lo\s+|la\s+)?(autorizo|acepto|quiero|me gusta)",
                  r"\bno (autorizo|doy permiso)\b"]
EXCLUSION = [r"\bno\s+(me\s+|nos\s+)?(vuelvan?\s+a\s+|sigan\s+|vuelva\s+a\s+)?(llam|contact)\w*",
             r"\bno\s+(quiero|deseo)\s+(que\s+(me\s+)?(sigan\s+|vuelvan\s+a\s+)?)?(llam|contact)\w*",
             r"\bno\s+(quiero|deseo)\s+recibir\s+(mas\s+)?llamadas?", r"dejen\s+de\s+(llam|contact)\w*",
             r"\b(borr|elimin|sac|quit|retir)\w*\b.{0,30}\b(lista|numero|campanas?)\b",
             r"no me contacte", r"do not call", r"no quiero llamadas"]
FRAUDE = [r"fraude", r"me robaron", r"\brob(o|aron)\b", r"cargo desconocido", r"tarjeta robada", r"clon\w*",
          r"cargo\b.{0,25}\b(raro|desconocido|que (yo )?no)", r"\bque (yo )?no (hice|realice|reconozco|autorice)\b",
          r"\bno (reconozco|autorice)\b", r"\bperd\w*\b.{0,20}\btarjeta\b", r"\btarjeta\b.{0,20}\bperd\w*"]
HUMANO = [r"quiero un humano", r"hablar con una persona", r"asesor humano", r"con un agente", r"operador humano",
          r"\b(hablar|conversar|atendid\w*|atienda|transferir|transfiera|pasar|pasame|pongame|ponme|comunicar)\b"
          r".{0,40}\b(persona|humano|representante|ejecutivo|asesor|agente|empleado|operador)\b",
          r"persona real", r"ser humano", r"alguien de verdad", r"\bno con (una|un|el)? ?(maquina|robot)\b"]
QUEJA = [r"queja", r"harto", r"frustrado", r"molesto", r"inconforme", r"pesimo servicio", r"reclam\w*",
         r"insatisfech\w*", r"desastre", r"falta de respeto", r"inconformidad", r"me canse", r"\bcansad\w*",
         r"hasta aqui", r"mal (trato|servicio|atencion)", r"pesim\w*"]
APROBACION = [r"aprobame", r"apruebame", r"aprobacion inmediata", r"apruebenme", r"aprobarme",
              r"decide si me aprueban", r"rechaza mi credito", r"\baprob\w*", r"\baprueb\w*",
              r"\bme sale (la|el) (tarjeta|prestamo|credito)\b", r"garantiz\w*.{0,30}\b(credito|prestamo|tarjeta)"]
REQUISITOS = [r"requisito", r"necesito para", r"que necesito", r"documento", r"producto", r"informacion de tarjeta",
              r"que ofrece", r"que es un certificado", r"requier\w*", r"\bpiden\b", r"papeles",
              r"que hay que (tener|llevar)", r"como (es que )?funciona", r"condiciones", r"debo presentar"]
DEVOLUCION = [r"me llamen", r"me llame", r"devolver la llamada", r"devolucion de llamada", r"llamada de seguimiento",
              r"quiero una llamada", r"\bllam(enme|eme|ame)\b", r"me (pueden|puede|podrian) (llamar|devolver)",
              r"(devolver\w*|agend\w*).{0,25}\bllamad\w*",
              r"\b(llam\w*|contact\w*|comuniq\w*|toque)\b.{0,40}\b(despues|mas tarde|manana|luego|otro dia|semana)\b"]
COTIZACION = [r"cuota", r"cuanto pag", r"cotiza", r"cotizacion", r"calcul\w*", r"\bmensual\w*", r"\bal mes\b",
              r"\bcada mes\b", r"cuanto (me )?(sale|toca|tendria|pagaria|pago)\b"]
TASA = [r"\btasa\b", r"interes anual", r"\binteres(es)?\b", r"porcentaje", r"porciento", r"por ciento",
        r"\ba como\b", r"\brind\w*", r"\brendim\w*"]


def is_private(t): return _any(t, PRIVACIDAD)


def is_consent_denied(t): return _any(t, CONSENTIMIENTO)


def is_do_not_call(t): return _any(t, EXCLUSION)


def is_fraud(t): return _any(t, FRAUDE)


def is_human(t): return _any(t, HUMANO)


def is_complaint(t): return _any(t, QUEJA)


def is_requirements(t): return _any(t, REQUISITOS)


def is_approval(t): return _any(t, APROBACION) and not is_requirements(t)


def is_callback(t): return _any(t, DEVOLUCION)


def is_quote(t): return _any(t, COTIZACION)


def is_rate(t): return _any(t, TASA)


def product(t: str, previous: str = "prestamo") -> str:
    if re.search(r"\b(tarjetas?|plastico|visa)\b", t):
        return "tarjeta"
    if re.search(r"\b(certificados?|deposito a plazo)\b", t):
        return "certificado"
    if re.search(r"\b(prestamos?|credito personal|financiamiento|credito)\b", t):
        return "prestamo"
    return previous
