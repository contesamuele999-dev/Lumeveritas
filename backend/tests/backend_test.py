"""
Backend tests for Lume Veritas API.
Covers: root/topics, auth (register/login/me/preferences), news briefing/deep-dive, ask,
saved add/list/delete. Uses public REACT_APP_BACKEND_URL.
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
API = f"{BASE_URL}/api"

# Longer timeout for AI endpoints
AI_TIMEOUT = 90
DEFAULT_TIMEOUT = 20


# ---------------- Fixtures ----------------
@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def new_user_creds():
    ts = int(time.time())
    return {
        "email": f"test+{ts}_{uuid.uuid4().hex[:6]}@lume.dev",
        "password": "LumeTest2026!",
        "name": "Lume Tester",
    }


@pytest.fixture(scope="module")
def auth_data(client, new_user_creds):
    r = client.post(f"{API}/auth/register", json=new_user_creds, timeout=DEFAULT_TIMEOUT)
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    data = r.json()
    assert "token" in data and "user" in data
    return data


@pytest.fixture(scope="module")
def auth_headers(auth_data):
    return {"Authorization": f"Bearer {auth_data['token']}"}


# ---------------- Basic ----------------
class TestBasic:
    def test_root(self, client):
        r = client.get(f"{API}/", timeout=DEFAULT_TIMEOUT)
        assert r.status_code == 200
        j = r.json()
        assert j.get("ok") is True
        assert j.get("app") == "Lume Veritas"

    def test_topics(self, client):
        r = client.get(f"{API}/topics", timeout=DEFAULT_TIMEOUT)
        assert r.status_code == 200
        topics = r.json()
        assert isinstance(topics, list)
        assert len(topics) == 16
        first = topics[0]
        for k in ("key", "label_it", "label_en"):
            assert k in first


# ---------------- Auth ----------------
class TestAuth:
    def test_register_duplicate(self, client, new_user_creds, auth_data):
        # auth_data already created the account; now duplicate register should fail
        r = client.post(f"{API}/auth/register", json=new_user_creds, timeout=DEFAULT_TIMEOUT)
        assert r.status_code == 400

    def test_login_valid(self, client, new_user_creds):
        r = client.post(f"{API}/auth/login", json={
            "email": new_user_creds["email"],
            "password": new_user_creds["password"],
        }, timeout=DEFAULT_TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert "token" in data
        assert data["user"]["email"] == new_user_creds["email"].lower()

    def test_login_wrong_password(self, client, new_user_creds):
        r = client.post(f"{API}/auth/login", json={
            "email": new_user_creds["email"],
            "password": "WrongPass123!",
        }, timeout=DEFAULT_TIMEOUT)
        assert r.status_code == 401

    def test_me_without_token(self, client):
        r = client.get(f"{API}/auth/me", timeout=DEFAULT_TIMEOUT)
        assert r.status_code == 401

    def test_me_with_token(self, client, auth_headers, new_user_creds):
        r = client.get(f"{API}/auth/me", headers=auth_headers, timeout=DEFAULT_TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == new_user_creds["email"].lower()
        assert isinstance(data.get("preferred_topics"), list)
        assert data.get("language") in ("it", "en")

    def test_update_preferences(self, client, auth_headers):
        new_prefs = {"preferred_topics": ["mercati", "guerre", "salute"], "language": "en"}
        r = client.put(f"{API}/auth/preferences", json=new_prefs, headers=auth_headers, timeout=DEFAULT_TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["preferred_topics"] == new_prefs["preferred_topics"]
        assert data["language"] == "en"
        # verify persistence via GET /me
        r2 = client.get(f"{API}/auth/me", headers=auth_headers, timeout=DEFAULT_TIMEOUT)
        assert r2.status_code == 200
        assert r2.json()["language"] == "en"
        # switch back to it for other tests
        client.put(f"{API}/auth/preferences", json={"language": "it"}, headers=auth_headers, timeout=DEFAULT_TIMEOUT)


# ---------------- News: briefing / deep-dive / ask ----------------
class TestNews:
    briefing_item_id = None

    def test_briefing_it(self, client):
        r = client.post(f"{API}/news/briefing", json={"topic": "Mercati", "language": "it"}, timeout=AI_TIMEOUT)
        assert r.status_code == 200, f"briefing failed: {r.status_code} {r.text[:400]}"
        data = r.json()
        assert data["topic"] == "Mercati"
        assert data["language"] == "it"
        items = data["items"]
        assert isinstance(items, list) and len(items) >= 3, f"got {len(items)} items"
        first = items[0]
        for k in ("id", "headline", "summary", "key_facts"):
            assert k in first, f"missing field {k} in item: {first}"
        assert isinstance(first["headline"], str) and len(first["headline"]) > 3
        assert isinstance(first["summary"], str) and len(first["summary"]) > 10
        assert isinstance(first["key_facts"], list)
        TestNews.briefing_item_id = first["id"]

    def test_briefing_cache(self, client):
        # second call should return cached items - same ids as first
        r = client.post(f"{API}/news/briefing", json={"topic": "Mercati", "language": "it"}, timeout=AI_TIMEOUT)
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) >= 3
        ids = {i["id"] for i in items}
        # Should include the id we stored (cache retrieved)
        if TestNews.briefing_item_id:
            assert TestNews.briefing_item_id in ids, "cache did not return the previously generated item"

    def test_briefing_en(self, client):
        r = client.post(f"{API}/news/briefing", json={"topic": "Technology", "language": "en"}, timeout=AI_TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["language"] == "en"
        items = data["items"]
        assert len(items) >= 3
        # rough check that content is english-ish: at least one headline has ascii letters and no italian-heavy accents
        joined = " ".join(i["summary"] for i in items).lower()
        # Basic heuristic: english words present
        assert any(w in joined for w in [" the ", " and ", " of ", " to ", " is ", " are ", " for "]), \
            f"English content not detected: {joined[:200]}"

    def test_deep_dive(self, client):
        assert TestNews.briefing_item_id, "no briefing id captured"
        r = client.post(f"{API}/news/deep-dive/{TestNews.briefing_item_id}", timeout=AI_TIMEOUT)
        assert r.status_code == 200, f"deep-dive failed: {r.status_code} {r.text[:400]}"
        data = r.json()
        assert data["id"] == TestNews.briefing_item_id
        assert data.get("real_reasons"), "real_reasons missing/empty"
        assert isinstance(data.get("data_points"), list)
        assert data.get("context"), "context missing"

    def test_deep_dive_not_found(self, client):
        r = client.post(f"{API}/news/deep-dive/nonexistent-id-xyz", timeout=DEFAULT_TIMEOUT)
        assert r.status_code == 404

    def test_ask(self, client):
        r = client.post(f"{API}/ask", json={
            "question": "Perché i tassi di natalità stanno calando in Italia?",
            "language": "it",
        }, timeout=AI_TIMEOUT)
        assert r.status_code == 200, f"ask failed: {r.status_code} {r.text[:400]}"
        data = r.json()
        assert isinstance(data.get("answer"), str) and len(data["answer"]) > 20
        assert isinstance(data.get("key_points"), list)
        assert isinstance(data.get("caveats"), list)


# ---------------- Saved ----------------
@pytest.fixture(scope="module")
def briefing_for_save(client):
    """Fetch (from cache) or generate a briefing to obtain a valid briefing id for save tests."""
    r = client.post(f"{API}/news/briefing", json={"topic": "Mercati", "language": "it"}, timeout=AI_TIMEOUT)
    assert r.status_code == 200
    items = r.json()["items"]
    assert items, "no briefing items returned"
    return items[0]["id"]


class TestSaved:
    def test_save_add_list_delete(self, client, auth_headers, briefing_for_save):
        bid = briefing_for_save

        # add
        r = client.post(f"{API}/saved/add", json={"briefing_id": bid}, headers=auth_headers, timeout=DEFAULT_TIMEOUT)
        assert r.status_code == 200
        assert r.json().get("ok") is True

        # list
        r = client.get(f"{API}/saved", headers=auth_headers, timeout=DEFAULT_TIMEOUT)
        assert r.status_code == 200
        lst = r.json()
        assert any(i["id"] == bid for i in lst), "saved item not in list"

        # delete
        r = client.delete(f"{API}/saved/{bid}", headers=auth_headers, timeout=DEFAULT_TIMEOUT)
        assert r.status_code == 200

        # list again -> should not contain
        r = client.get(f"{API}/saved", headers=auth_headers, timeout=DEFAULT_TIMEOUT)
        assert r.status_code == 200
        assert not any(i["id"] == bid for i in r.json())

    def test_save_requires_auth(self, client):
        r = client.post(f"{API}/saved/add", json={"briefing_id": "x"}, timeout=DEFAULT_TIMEOUT)
        assert r.status_code == 401

    def test_save_nonexistent_briefing(self, client, auth_headers):
        r = client.post(f"{API}/saved/add", json={"briefing_id": "does-not-exist"}, headers=auth_headers, timeout=DEFAULT_TIMEOUT)
        assert r.status_code == 404


# ---------------- Explain (NEW) ----------------
class TestExplain:
    """Tests for POST /api/explain (word/term explainer)."""

    def test_explain_it(self, client):
        r = client.post(f"{API}/explain", json={"word": "idrogeno", "language": "it"}, timeout=AI_TIMEOUT)
        assert r.status_code == 200, f"explain IT failed: {r.status_code} {r.text[:400]}"
        d = r.json()
        assert d["word"] == "idrogeno"
        assert isinstance(d["explanation"], str)
        assert len(d["explanation"]) > 5, f"explanation too short: {d['explanation']!r}"

    def test_explain_cache(self, client):
        """Second call with same word+language should return same explanation (cached)."""
        r1 = client.post(f"{API}/explain", json={"word": "idrogeno", "language": "it"}, timeout=AI_TIMEOUT)
        assert r1.status_code == 200
        first = r1.json()["explanation"]
        t0 = time.time()
        r2 = client.post(f"{API}/explain", json={"word": "idrogeno", "language": "it"}, timeout=AI_TIMEOUT)
        elapsed = time.time() - t0
        assert r2.status_code == 200
        second = r2.json()["explanation"]
        assert first == second, "cached explanation differs from first"
        # Cache should be fast (< 5s round trip)
        assert elapsed < 5, f"cached response took {elapsed:.1f}s — cache likely not used"

    def test_explain_en(self, client):
        r = client.post(f"{API}/explain", json={"word": "quorum", "language": "en"}, timeout=AI_TIMEOUT)
        assert r.status_code == 200, f"explain EN failed: {r.status_code} {r.text[:400]}"
        d = r.json()
        assert d["word"] == "quorum"
        expl = d["explanation"]
        assert isinstance(expl, str) and len(expl) > 5
        # Heuristic: English explanation should contain English stopwords or be plainly non-Italian
        low = expl.lower()
        assert any(w in low for w in [" the ", " a ", " is ", " to ", " that ", " when ", " of "]) or "quorum" in low, \
            f"EN explanation may not be in English: {expl[:180]}"

    def test_explain_empty_word_400(self, client):
        r = client.post(f"{API}/explain", json={"word": "", "language": "it"}, timeout=DEFAULT_TIMEOUT)
        assert r.status_code == 400, f"expected 400 for empty word, got {r.status_code}: {r.text}"

    def test_explain_whitespace_only_400(self, client):
        r = client.post(f"{API}/explain", json={"word": "   ", "language": "it"}, timeout=DEFAULT_TIMEOUT)
        assert r.status_code == 400, f"expected 400 for whitespace-only word, got {r.status_code}: {r.text}"

    def test_explain_too_long_400(self, client):
        long_word = "a" * 121
        r = client.post(f"{API}/explain", json={"word": long_word, "language": "it"}, timeout=DEFAULT_TIMEOUT)
        assert r.status_code == 400, f"expected 400 for word > 120 chars, got {r.status_code}: {r.text}"
