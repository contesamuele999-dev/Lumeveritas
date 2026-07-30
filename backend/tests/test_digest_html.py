"""Self-check del template email del digest. Si lancia con:  python tests/test_digest_html.py

Stubba maileroo/db/config/models così il test gira senza credenziali né dipendenze di rete.
"""
import os, sys, types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_maileroo = types.ModuleType("maileroo")
_maileroo.MailerooClient = lambda *a, **k: None
_maileroo.EmailAddress = lambda *a, **k: None
sys.modules["maileroo"] = _maileroo

_config = types.ModuleType("config")
_config.MAILEROO_API_KEY = ""
_config.SENDER_EMAIL = "news@example.com"
_config.SENDER_NAME = "Lume Veritas"
_config.PUBLIC_APP_URL = "https://lume-veritas.onrender.com/"  # con slash finale di proposito
sys.modules["config"] = _config

_db = types.ModuleType("db")
_db.db = None
sys.modules["db"] = _db

_models = types.ModuleType("models")
_models.BriefingIn = object
_models.DEFAULT_TOPICS = [{"key": "mercati", "label_it": "Mercati", "label_en": "Markets"}]
sys.modules["models"] = _models

from services.digest import _digest_html, _article_url, _digest_topic_keys


def main():
    # niente doppio slash anche se PUBLIC_APP_URL finisce con "/"
    assert _article_url("abc-123") == "https://lume-veritas.onrender.com/s/abc-123", _article_url("abc-123")

    sections = [{"topic": "Mercati", "items": [
        {"id": "id-1", "headline": "Titolo con <b> & simboli", "summary": "Riassunto uno."},
        {"id": "id-2", "headline": "Secondo titolo", "summary": "Riassunto due."},
    ]}]
    html = _digest_html("Samuele", "it", sections)

    # ogni notizia ha il titolo cliccabile verso la sua pagina di approfondimento
    for i in ("id-1", "id-2"):
        assert f'href="https://lume-veritas.onrender.com/s/{i}"' in html, i
    assert html.count("Approfondisci") == 2, html.count("Approfondisci")

    # il titolo non deve poter iniettare HTML nell'email
    assert "<b>" not in html and "&lt;b&gt;" in html
    assert "&amp; simboli" in html

    # argomenti: i personalizzati vengono prima e non cadono fuori dal taglio
    user = {
        "custom_topics": [{"key": "custom-topic-nucleare"}, {"key": "custom-topic-cile"}],
        "preferred_topics": ["mercati", "scienza", "leggi", "salute", "ambiente", "cripto", "ia"],
    }
    keys = _digest_topic_keys(user)
    assert keys[:2] == ["custom-topic-nucleare", "custom-topic-cile"], keys
    assert len(keys) == 6, keys

    # senza preferenze si ricade sui default
    assert _digest_topic_keys({}) == ["mercati"]

    print("OK - link agli articoli, escaping del titolo e priorità agli argomenti personalizzati")


if __name__ == "__main__":
    main()
