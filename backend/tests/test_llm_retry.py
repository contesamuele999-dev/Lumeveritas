"""Self-check della logica di retry in llm.py. Si lancia con:  python tests/test_llm_retry.py"""
import asyncio, os, sys, types as pytypes

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("GEMINI_API_KEY", "fake-key-per-test")

import llm
from fastapi import HTTPException


class FakeResp:
    def __init__(self, text): self.text = text


def _install(side_effects):
    """Sostituisce generate_content: consuma side_effects, ognuno è un'eccezione o una risposta."""
    calls = {"n": 0}

    async def fake(**kwargs):
        i = calls["n"]
        calls["n"] += 1
        item = side_effects[i]
        if isinstance(item, Exception):
            raise item
        return FakeResp(item)

    llm._client.aio.models.generate_content = fake
    return calls


def main():
    llm.RETRY_BACKOFF = (0.0, 0.0)  # niente attese nei test

    # 1) errore transitorio poi successo: deve riprovare e restituire il testo
    calls = _install([Exception("503 UNAVAILABLE model overloaded"), "ok"])
    out = asyncio.run(llm.llm_text("s", "sys", "ciao"))
    assert out == "ok", out
    assert calls["n"] == 2, calls

    # 2) transitorio sempre: dopo RETRY_ATTEMPTS alza 429, non 502
    calls = _install([Exception("503 UNAVAILABLE")] * llm.RETRY_ATTEMPTS)
    try:
        asyncio.run(llm.llm_text("s", "sys", "ciao"))
        raise AssertionError("doveva alzare HTTPException")
    except HTTPException as e:
        assert e.status_code == 429, e.status_code
    assert calls["n"] == llm.RETRY_ATTEMPTS, calls

    # 3) errore permanente: nessun retry, 502 subito
    calls = _install([Exception("400 API key not valid"), "non-deve-arrivarci"])
    try:
        asyncio.run(llm.llm_text("s", "sys", "ciao"))
        raise AssertionError("doveva alzare HTTPException")
    except HTTPException as e:
        assert e.status_code == 502, e.status_code
    assert calls["n"] == 1, calls

    # 4) sources_from: estrae i link web del grounding, deduplica, ignora chunk senza uri
    class W:
        def __init__(self, uri, title=None): self.uri, self.title = uri, title
    class C:
        def __init__(self, web): self.web = web
    class GM:
        def __init__(self, chunks): self.grounding_chunks = chunks
    class Cand:
        def __init__(self, chunks): self.grounding_metadata = GM(chunks)
    class R:
        def __init__(self, chunks): self.candidates = [Cand(chunks)]

    got = llm.sources_from(R([C(W("https://a.it", "A")), C(W("https://a.it", "A")), C(W(None)), C(None)]))
    assert got == [{"title": "A", "url": "https://a.it"}], got
    assert llm.sources_from(FakeResp("nessun grounding")) == []

    # 5) grounding fallito con 502: ricade su una chiamata normale, senza fonti
    calls = _install([Exception("400 tool not supported"), '{"a": 1}'])
    data, sources = asyncio.run(llm.llm_json_grounded("s", "sys", "ciao"))
    assert (data, sources) == ({"a": 1}, []), (data, sources)
    assert calls["n"] == 2, calls

    print("OK - retry, esaurimento tentativi, errore permanente, fonti e fallback grounding")


if __name__ == "__main__":
    main()
