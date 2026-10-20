"""Herramientas comprobables con catálogo ficticio y validación determinista."""
import inspect, json
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
from src.storage import insert

DATA = json.loads((Path(__file__).resolve().parents[1] / 'data/products.json').read_text(encoding='utf-8'))
CATALOG = {p['id']: p for p in DATA['products']}


def get_product_info(product):
    if product not in CATALOG: return {'error': 'Producto desconocido'}
    return {**CATALOG[product], 'simulated': True}


def get_interest_rate(product):
    if product not in CATALOG: return {'error': 'Producto desconocido'}
    return {'product': product, 'annual_rate_pct': CATALOG[product]['annual_rate_pct'], 'source': 'catálogo ficticio',
            'simulated': True}


def calculate_loan(amount, months):
    if isinstance(months, bool) or not isinstance(months, int) or not 1 <= months <= 60: raise ValueError(
        'Plazo: 1 a 60 meses enteros')
    try:
        p = Decimal(str(amount))
    except Exception as exc:
        raise ValueError('Monto inválido') from exc
    if not p.is_finite() or not Decimal('1000') <= p <= Decimal('2000000'): raise ValueError(
        'Monto fuera de rango (1,000 a 2,000,000 DOP)')
    annual = Decimal(str(CATALOG['prestamo']['annual_rate_pct']))
    r = annual / Decimal('1200');
    payment = p * r / (1 - (1 + r) ** (-months))
    payment = payment.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
    return {'amount_dop': float(p), 'months': months, 'annual_rate_pct': float(annual),
            'monthly_payment_dop': float(payment), 'total_dop': float(payment * months),
            'assumptions': 'Tasa nominal fija / 12; sin seguros ni comisiones.', 'simulated': True, 'binding': False}


def check_prequalification(): return {'status': 'ORIENTACION_NO_VINCULANTE', 'approved': False,
                                      'message': 'Solo orientación; sin aprobación o rechazo.'}


def create_lead(product, confirmed=False):
    if product not in CATALOG: return {'error': 'Producto desconocido'}
    if confirmed is not True: return {'status': 'REQUIERE_CONFIRMACION'}
    return {'status': 'REGISTRO_SIMULADO', 'id': insert('leads', product)}


def schedule_callback(confirmed=False, topic='consulta'):
    if confirmed is not True: return {'status': 'REQUIERE_CONFIRMACION'}
    return {'status': 'REGISTRO_SIMULADO', 'id': insert('callbacks', topic[:60])}


def request_human_transfer(reason='solicitud'):
    if reason not in {'solicitud', 'queja', 'fraude'}: reason = 'solicitud'
    return {'status': 'TRANSFERENCIA_SIMULADA', 'id': insert('transfers', reason), 'reason': reason}


def check_contact_policy(consented, do_not_call, local_hour=14):
    if do_not_call: return {'allowed': False, 'reason': 'DNC'}
    if not consented: return {'allowed': False, 'reason': 'SIN_CONSENTIMIENTO'}
    if not isinstance(local_hour, int) or local_hour < 9 or local_hour >= 18: return {'allowed': False,
                                                                                      'reason': 'FUERA_DE_HORARIO_DEMO'}
    return {'allowed': True, 'reason': 'SOLO_SIMULACION'}


TOOLS = {f.__name__: f for f in
         (get_product_info, get_interest_rate, calculate_loan, check_prequalification, create_lead, schedule_callback,
          request_human_transfer)}
# Esquemas minimalistas para la selección de herramientas por Claude.
SCHEMAS = [
    {'name': 'get_product_info', 'description': 'Consultar requisitos/productos ficticios',
     'input_schema': {'type': 'object',
                      'properties': {'product': {'type': 'string', 'enum': ['tarjeta', 'prestamo', 'certificado']}},
                      'required': ['product']}},
    {'name': 'get_interest_rate', 'description': 'Consultar tasa anual, no inventar', 'input_schema': {'type': 'object',
                                                                                                       'properties': {
                                                                                                           'product': {
                                                                                                               'type': 'string',
                                                                                                               'enum': [
                                                                                                                   'tarjeta',
                                                                                                                   'prestamo',
                                                                                                                   'certificado']}},
                                                                                                       'required': [
                                                                                                           'product']}},
    {'name': 'calculate_loan', 'description': 'Calcular cuota fija por fórmula con tasa ficticia',
     'input_schema': {'type': 'object', 'properties': {'amount': {'type': 'number'}, 'months': {'type': 'integer'}},
                      'required': ['amount', 'months']}},
    {'name': 'check_prequalification', 'description': 'Precalificación puramente informativa',
     'input_schema': {'type': 'object', 'properties': {}}},
    {'name': 'create_lead', 'description': 'Registrar lead ficticio solo tras confirmación explícita',
     'input_schema': {'type': 'object',
                      'properties': {'product': {'type': 'string', 'enum': ['tarjeta', 'prestamo', 'certificado']},
                                     'confirmed': {'type': 'boolean'}}, 'required': ['product', 'confirmed']}},
    {'name': 'schedule_callback', 'description': 'Registro ficticio de seguimiento, con confirmación',
     'input_schema': {'type': 'object', 'properties': {'confirmed': {'type': 'boolean'}, 'topic': {'type': 'string'}},
                      'required': ['confirmed']}},
    {'name': 'request_human_transfer', 'description': 'Solo registro de transferencia ficticia',
     'input_schema': {'type': 'object',
                      'properties': {'reason': {'type': 'string', 'enum': ['solicitud', 'queja', 'fraude']}},
                      'required': ['reason']}}
]


def execute(name, params):
    if name not in TOOLS: return {'error': 'Herramienta no autorizada'}
    try:
        allowed = inspect.signature(TOOLS[name]).parameters
        return TOOLS[name](**{k: v for k, v in params.items() if k in allowed})
    except (TypeError, ValueError, KeyError) as ex:
        return {'error': str(ex)}
