"""Inspección/reconciliación segura de llamadas del piloto, sin iniciar llamadas.

Ejecute desde la raíz con:
    python -m scripts.reconcile_calls             # solo lectura local
    python -m scripts.reconcile_calls --check     # GET Twilio y actualización terminal

Nunca elimina datos ni elimina unilateralmente reservas sin Call SID.
"""
from __future__ import annotations

import argparse

from src.telephony import CallPolicyError, _active_calls, refresh_call_status


def main() -> int:
    parser = argparse.ArgumentParser(description='Revisar estados telefónicos locales y Twilio')
    parser.add_argument('--check', action='store_true',
                        help='Consultar estados remotos y actualizar solo confirmados por Twilio')
    args = parser.parse_args()
    calls = _active_calls()
    if not calls:
        print('No existen llamadas que SQLite considere activas.')
        return 0
    failures = 0
    for item in calls:
        call_id = item['id']
        state = item['status']
        if args.check and item['call_sid']:
            try:
                state = refresh_call_status(call_id)['status']
            except CallPolicyError:
                failures += 1
                print(f'{call_id}: estado no verificable; se conserva el bloqueo.')
                continue
        elif args.check and not item['call_sid']:
            failures += 1
            print(f'{call_id}: sin Call SID; requiere revisión manual en Twilio Console.')
            continue
        print(f'{call_id}: {state} (SID {"asociado" if item["call_sid"] else "pendiente"})')
    if failures:
        print('No borre SQLite ni fuerce estados sin confirmar la llamada en Twilio.')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
