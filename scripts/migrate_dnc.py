"""Migración interactiva de DNC anterior a VANTRA_PHONE_HASH_KEY.

Ejecutar antes de rotar TWILIO_AUTH_TOKEN. No admite teléfonos/token en CLI
para evitar exposición en historial del shell y lista de procesos.
"""
from __future__ import annotations

from getpass import getpass

from src.telephony import legacy_dnc_count, migrate_legacy_dnc


def main() -> int:
    remaining = legacy_dnc_count()
    print(f"Entradas DNC heredadas sin migrar: {remaining}")
    if remaining == 0:
        return 0
    print("Se requieren TODOS los teléfonos DNC conocidos, uno por línea; termine con línea vacía.")
    print("Si quedan hashes sin correspondencia, las llamadas permanecerán bloqueadas.")
    phones = []
    while True:
        number = getpass("Número E.164 (oculto): ").strip()
        if not number:
            break
        phones.append(number)
    old_token = getpass("Auth Token Twilio ANTERIOR (oculto): ").strip()
    result = migrate_legacy_dnc(phones, old_token)
    print(f"Migrados: {result['migrated']}; pendientes: {result['unresolved_legacy_dnc']}")
    return 0 if result['unresolved_legacy_dnc'] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
