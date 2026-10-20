"""Opciones y credenciales suministradas por .env, nunca versionadas."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / '.env')


def env(name, default=''): return os.getenv(name, default).strip()


def key(name):
    value = env(name)
    if not value: raise RuntimeError(f'Falta {name}; configure .env según .env.example.')
    return value
