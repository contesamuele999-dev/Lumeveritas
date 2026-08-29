"""Self-check del riconoscimento notizie ripetute. Si lancia con:  python tests/test_dedup.py"""
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from services.dedup import drop_duplicates, is_same_story, tokens_of

GIA_USCITE = [
    "Nuove sanzioni USA contro la flotta ombra russa: 183 navi colpite",
    "La Cina supera gli Stati Uniti nella capacita solare installata",
    "Il Parlamento europeo approva la legge sul ripristino della natura",
]


def main():
    generate = [
        # stessa notizia con altre parole: va scartata
        "Sanzioni americane sulla flotta ombra russa: colpite 183 navi",
        "Legge europea sul ripristino della natura approvata a Strasburgo",
        # stesso ambito ma fatti diversi: vanno tenute
        "Il Parlamento europeo boccia il regolamento sui pesticidi",
        "La Cina inaugura il piu grande impianto eolico offshore del mondo",
        # nuova, e subito dopo la sua riformulazione dentro la stessa risposta
        "Nuovo studio: il debito pubblico italiano supera il 140% del PIL",
        "Debito pubblico italiano oltre il 140% del PIL secondo Bankitalia",
    ]
    keep = drop_duplicates(generate, known=GIA_USCITE)
    assert keep == [2, 3, 4], keep

    # inglese: plurali e forme verbali diverse restano la stessa notizia
    assert is_same_story(
        tokens_of("US sanctions target 183 ships of the Russian shadow fleet"),
        tokens_of("Sanctions targeting the Russian shadow fleet hit 183 ships"),
    )

    # argomenti vicini che citano lo stesso paese non sono la stessa notizia
    assert not is_same_story(
        tokens_of("La Cina apre una base navale in Africa orientale"),
        tokens_of("La Cina taglia i tassi per sostenere il mercato immobiliare"),
    )

    # nessun titolo noto: si tiene tutto
    assert drop_duplicates(generate) == [0, 1, 2, 3, 4]  # l'ultimo replica il quinto

    # titoli vuoti non entrano mai nel risultato
    assert drop_duplicates(["", "   "]) == []

    print("OK - riformulazioni scartate, fatti distinti tenuti, doppioni interni rimossi")


if __name__ == "__main__":
    main()
