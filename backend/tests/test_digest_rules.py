"""Self-check delle regole di invio del digest. Si lancia con:  python tests/test_digest_rules.py"""
import os, sys
from datetime import date, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from services.digest_rules import is_due, DIGEST_HOUR, MAX_ATTEMPTS_PER_DAY, rotate_topics, rotation_period

MON = datetime(2026, 7, 27, 7, 0)   # lunedì 07:00
TUE = datetime(2026, 7, 28, 7, 0)   # martedì 07:00


def main():
    # prima dell'ora: non si manda niente
    assert is_due(TUE.replace(hour=DIGEST_HOUR - 1), "daily", None) is False

    # dopo l'ora e mai inviato: si manda
    assert is_due(TUE, "daily", None) is True

    # già inviato oggi: non si duplica, nemmeno se il job rigira 10 minuti dopo
    assert is_due(TUE, "daily", TUE.date()) is False
    assert is_due(TUE.replace(hour=23), "daily", TUE.date()) is False

    # inviato ieri: oggi tocca di nuovo
    assert is_due(TUE, "daily", date(2026, 7, 27)) is True

    # recupero: l'istanza dormiva alle 06:00 e si sveglia alle 11:40 → parte lo stesso
    assert is_due(TUE.replace(hour=11, minute=40), "daily", date(2026, 7, 27)) is True

    # settimanale: solo lunedì
    assert is_due(TUE, "weekly", None) is False
    assert is_due(MON, "weekly", None) is True
    assert is_due(MON, "weekly", MON.date()) is False

    # troppi tentativi falliti oggi: si smette di ritentare
    assert is_due(TUE, "daily", None, attempts_today=MAX_ATTEMPTS_PER_DAY) is False
    assert is_due(TUE, "daily", None, attempts_today=MAX_ATTEMPTS_PER_DAY - 1) is True

    # rotazione: pochi argomenti restano tutti; tanti scorrono e prima o poi escono tutti
    assert rotate_topics(["a", "b"], 5, size=3) == ["a", "b"]
    keys = list("abcdefg")
    seen = set()
    for p in range(len(keys)):
        win = rotate_topics(keys, p, size=3)
        assert len(win) == 3 and len(set(win)) == 3
        seen.update(win)
    assert seen == set(keys)
    assert rotate_topics(keys, 0, size=3) != rotate_topics(keys, 1, size=3)
    # il turno avanza ogni giorno (daily) o ogni settimana (weekly)
    assert rotation_period(TUE.date(), "daily") == rotation_period(MON.date(), "daily") + 1
    assert rotation_period(MON.date(), "weekly") + 1 == rotation_period(date(2026, 8, 3), "weekly")

    print("OK - orario, anti-duplicato, recupero dopo il risveglio, settimanale, limite tentativi e rotazione")


if __name__ == "__main__":
    main()
