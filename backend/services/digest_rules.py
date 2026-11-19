"""Regole pure di scheduling del digest (nessuna dipendenza da DB/mail: testabili da sole)."""
from datetime import date, datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

DIGEST_HOUR = 6            # 06:00 Europe/Rome
MAX_ATTEMPTS_PER_DAY = 3   # invii falliti: si riprova, ma non all'infinito


def rome_tz():
    """Europe/Rome, con fallback a UTC se manca il database dei fusi (pacchetto `tzdata`).
    Meglio un digest un'ora spostata che l'intera app che non parte."""
    try:
        return ZoneInfo("Europe/Rome")
    except Exception:
        return timezone.utc


def is_due(now: datetime, frequency: str, last_ok_day: Optional[date], attempts_today: int = 0) -> bool:
    """True se a questo utente il digest va inviato adesso.

    Il controllo è "è passata l'ora e oggi non è ancora partito", non "sono le 06:00 esatte":
    su Render free il processo dorme e un cron alle 06:00 in punto salterebbe la giornata.
    """
    if now.hour < DIGEST_HOUR:
        return False
    if frequency == "weekly" and now.weekday() != 0:  # lunedì
        return False
    if last_ok_day == now.date():
        return False
    if attempts_today >= MAX_ATTEMPTS_PER_DAY:
        return False
    return True


ROTATE_TOPICS_PER_DIGEST = 3  # con la rotazione attiva: argomenti per singola email


def rotation_period(day: date, frequency: str) -> int:
    """Indice del turno di rotazione: avanza di uno a ogni giorno (o settimana) di invio."""
    return day.toordinal() // 7 if frequency == "weekly" else day.toordinal()


def rotate_topics(keys: list, period: int, size: int = ROTATE_TOPICS_PER_DIGEST) -> list:
    """Finestra di `size` argomenti che scorre su tutta la lista, un turno dopo l'altro.
    Ogni argomento torna a rotazione, anche quelli oltre il limite fisso del digest."""
    if len(keys) <= size:
        return list(keys)
    start = (period * size) % len(keys)
    return [keys[(start + i) % len(keys)] for i in range(size)]
