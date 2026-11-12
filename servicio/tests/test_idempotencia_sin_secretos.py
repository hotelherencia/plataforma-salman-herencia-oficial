"""CE-HH-2026-001 C-01: el digest de idempotencia no depende de contraseñas."""
import hashlib
import json

from servicio import idempotencia


def _sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def test_digest_ignora_clave_y_clave_actual():
    a = idempotencia.hash_cuerpo({"usuario_id": "u1", "clave": "Secreta-1", "clave_actual": "Vieja-1"})
    b = idempotencia.hash_cuerpo({"usuario_id": "u1", "clave": "Otra-2", "clave_actual": "Otra-3"})
    assert a == b
    assert a == _sha({"usuario_id": "u1"})


def test_digest_no_es_brute_forceable_con_la_clave():
    cuerpo = {"nombre": "ana", "rol": "recepcion", "clave": "Secreta-1"}
    assert idempotencia.hash_cuerpo(cuerpo) != _sha(cuerpo)


def test_digest_sigue_distinguiendo_campos_no_secretos():
    assert idempotencia.hash_cuerpo({"nombre": "ana", "clave": "x"}) != idempotencia.hash_cuerpo({"nombre": "beto", "clave": "x"})


def test_secretos_anidados_tambien_se_excluyen():
    a = idempotencia.hash_cuerpo({"datos": [{"clave": "a", "n": 1}]})
    b = idempotencia.hash_cuerpo({"datos": [{"clave": "b", "n": 1}]})
    assert a == b
