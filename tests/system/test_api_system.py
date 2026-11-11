"""Black-box system tests for a running Maharych stack.

The suite talks only to the public entry point (Nginx, default
http://localhost:8090) exactly as the browser does, so it exercises
Nginx -> Go API -> PostgreSQL (and Go -> gRPC -> voice_ai_service for
``/end``). It needs no third-party packages.

Run (stack must be up, e.g. ``docker compose up -d``):

    python -m unittest discover -s tests/system -v

Optional environment:
    MAHARYCH_BASE_URL       entry point (default http://127.0.0.1:8090)
    MAHARYCH_LIVE_EMAIL     account that owns a completed interview
    MAHARYCH_LIVE_PASSWORD  its password
    MAHARYCH_LIVE_INTERVIEW id of that completed interview

Each test id carries the requirement it validates (FR-x / NFR-x from
laboratory work No. 1) so the run log doubles as a traceability record.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import statistics
import time
import unittest
import urllib.error
import urllib.request
import uuid

# 127.0.0.1, not "localhost": on Windows Python first tries ::1 and adds ~2 s
# per request, which would distort the latency measurements below.
BASE = os.environ.get("MAHARYCH_BASE_URL", "http://127.0.0.1:8090").rstrip("/")
API = BASE + "/api/v1"
STRONG_PASSWORD = "Sys7emTest!"


def call(method, path, body=None, token=None, headers=None, raw=False):
    """Perform an HTTP request and return (status, parsed body, headers)."""
    data = None
    hdrs = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    hdrs.update(headers or {})
    url = path if path.startswith("http") else API + path
    req = urllib.request.Request(url, data=data, method=method, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            status, payload, rh = resp.status, resp.read(), resp.headers
    except urllib.error.HTTPError as err:
        status, payload, rh = err.code, err.read(), err.headers
    if raw:
        return status, payload, rh
    try:
        parsed = json.loads(payload.decode("utf-8")) if payload else None
    except ValueError:
        parsed = payload.decode("utf-8", "replace")
    return status, parsed, rh


def new_email(tag="user"):
    return f"st-{tag}-{uuid.uuid4().hex[:10]}@example.com"


def register(email=None, password=STRONG_PASSWORD):
    email = email or new_email()
    status, body, _ = call("POST", "/auth/register", {"email": email, "password": password})
    assert status == 201, (status, body)
    return email, body["token"]


VALID_PROFILE = {
    "name": "System",
    "surname": "Tester",
    "phoneNumber": "+380671234567",
    "linkedinUrl": "https://linkedin.com/in/system-tester",
    "githubUrl": "https://github.com/system-tester",
    "yearsOfExperience": 3,
    "techStack": ["Go", "PostgreSQL", "go", "Docker"],
    "resume": "Backend engineer: Go services, PostgreSQL, RabbitMQ, Docker.",
}
VALID_START = {"level": "middle", "position": "backend", "focus": "behavioral",
               "language": "en", "voiceId": "anna"}


def user_with_profile():
    email, token = register()
    status, body, _ = call("PUT", "/profile", VALID_PROFILE, token)
    assert status == 200, (status, body)
    return email, token


def forge_jwt(payload, secret=b"definitely-not-the-server-secret", alg="HS256"):
    def b64(obj):
        raw = obj if isinstance(obj, bytes) else json.dumps(obj, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
    head = b64({"alg": alg, "typ": "JWT"})
    body = b64(payload)
    if alg == "none":
        return f"{head}.{body}."
    sig = hmac.new(secret, f"{head}.{body}".encode(), hashlib.sha256).digest()
    return f"{head}.{body}.{b64(sig)}"


def percentile(samples, pct):
    ordered = sorted(samples)
    index = max(0, min(len(ordered) - 1, round(pct / 100 * len(ordered)) - 1))
    return ordered[index]


class T01_Availability(unittest.TestCase):
    """NFR-8: the gateway routes to every component."""

    def test_health_through_nginx(self):
        status, body, headers = call("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok"})
        self.assertIn("application/json", headers.get("Content-Type", ""))

    def test_frontend_pages_served(self):
        for page in ("/", "/login", "/register"):
            with self.subTest(page=page):
                status, html, _ = call("GET", BASE + page, raw=True)
                self.assertEqual(status, 200)
                self.assertIn(b"<html", html.lower())

    def test_swagger_documentation_served(self):
        status, html, _ = call("GET", BASE + "/swagger/index.html", raw=True)
        self.assertEqual(status, 200)
        self.assertIn(b"swagger", html.lower())

    def test_interview_options_catalog(self):
        """FR-4: role, level, interview type and language are selectable."""
        status, body, _ = call("GET", "/interview-options")
        self.assertEqual(status, 200)
        keys = {group: {item["key"] for item in items} for group, items in body.items()}
        self.assertTrue({"junior", "middle", "senior"} <= keys.get("levels", set()), keys)
        self.assertIn("backend", keys.get("positions", set()), keys)
        focus_group = next((g for g in keys if g.startswith("focus") or g == "types"), None)
        self.assertIsNotNone(focus_group, keys)
        self.assertTrue({"algorithms", "behavioral"} <= keys[focus_group], keys)


class T02_Registration(unittest.TestCase):
    """FR-1 and NFR-7: account creation and credential handling."""

    def test_register_returns_jwt_and_hides_secrets(self):
        email = new_email("reg")
        status, body, _ = call("POST", "/auth/register", {"email": email, "password": STRONG_PASSWORD})
        self.assertEqual(status, 201)
        self.assertEqual(body["user"]["email"], email)
        self.assertEqual(body["user"]["role"], "user")
        self.assertEqual(body["token"].count("."), 2, "token must be a JWT")
        dumped = json.dumps(body).lower()
        for secret in ("password", "$2a$", "$2b$", STRONG_PASSWORD.lower()):
            self.assertNotIn(secret, dumped)

    def test_duplicate_email_is_conflict_case_insensitive(self):
        email, _ = register()
        status, body, _ = call("POST", "/auth/register",
                               {"email": email.upper(), "password": STRONG_PASSWORD})
        self.assertEqual(status, 409, body)

    def test_malformed_email_rejected(self):
        status, _, _ = call("POST", "/auth/register", {"email": "not-an-email", "password": STRONG_PASSWORD})
        self.assertEqual(status, 400)

    def test_server_enforces_password_policy(self):
        """The UI requires 8+ chars, an upper-case letter and a digit; the API must too."""
        status, body, _ = call("POST", "/auth/register", {"email": new_email("weak"), "password": "1"})
        self.assertEqual(status, 400, f"weak password accepted by API: {status} {body}")

    def test_overlong_password_is_client_error(self):
        """bcrypt accepts at most 72 bytes; longer input must be a 4xx, not a server fault."""
        status, body, _ = call("POST", "/auth/register",
                               {"email": new_email("long"), "password": "Aa1" + "x" * 80})
        self.assertLess(status, 500, f"overlong password caused {status} {body}")


class T03_Login(unittest.TestCase):
    """FR-1: password sign-in."""

    @classmethod
    def setUpClass(cls):
        cls.email, _ = register()

    def test_login_success_returns_new_token(self):
        status, body, _ = call("POST", "/auth/login", {"email": self.email, "password": STRONG_PASSWORD})
        self.assertEqual(status, 200)
        self.assertTrue(body["token"])

    def test_login_email_is_case_insensitive(self):
        status, _, _ = call("POST", "/auth/login", {"email": self.email.upper(), "password": STRONG_PASSWORD})
        self.assertEqual(status, 200)

    def test_wrong_password_and_unknown_user_are_indistinguishable(self):
        s1, b1, _ = call("POST", "/auth/login", {"email": self.email, "password": "Wrong123!"})
        s2, b2, _ = call("POST", "/auth/login", {"email": new_email("ghost"), "password": "Wrong123!"})
        self.assertEqual((s1, s2), (401, 401))
        self.assertEqual(b1, b2, "responses must not reveal which accounts exist")

    def test_google_login_requires_id_token(self):
        status, _, _ = call("POST", "/auth/google", {})
        self.assertEqual(status, 400)


class T04_AccessControl(unittest.TestCase):
    """NFR-7: authentication and owner isolation."""

    PROTECTED = [("GET", "/profile"), ("PUT", "/profile"), ("GET", "/interviews"),
                 ("POST", "/interviews"), ("GET", f"/interviews/{uuid.uuid4()}")]

    @classmethod
    def setUpClass(cls):
        _, cls.owner = user_with_profile()
        _, cls.intruder = user_with_profile()
        status, body, _ = call("POST", "/interviews", VALID_START, cls.owner)
        assert status == 201, (status, body)
        cls.interview_id = body["id"]

    def test_protected_routes_require_token(self):
        for method, path in self.PROTECTED:
            with self.subTest(route=f"{method} {path}"):
                status, _, _ = call(method, path, {} if method in ("POST", "PUT") else None)
                self.assertEqual(status, 401)

    def test_forged_and_unsigned_tokens_rejected(self):
        claims = {"sub": 1, "user_id": 1, "email": "admin@example.com", "role": "admin",
                  "exp": int(time.time()) + 3600}
        for label, token in (("wrong-key", forge_jwt(claims)), ("alg-none", forge_jwt(claims, alg="none")),
                             ("garbage", "abc.def.ghi")):
            with self.subTest(token=label):
                status, _, _ = call("GET", "/profile", token=token)
                self.assertEqual(status, 401)

    def test_regular_user_cannot_use_admin_api(self):
        for path in ("/admin/interview-options", "/admin/questions", "/admin/feedback-outbox"):
            with self.subTest(path=path):
                status, _, _ = call("GET", path, token=self.owner)
                self.assertEqual(status, 403)

    def test_foreign_interview_is_invisible(self):
        iid = self.interview_id
        for method, path in (("GET", f"/interviews/{iid}"), ("GET", f"/interviews/{iid}/feedback"),
                             ("GET", f"/interviews/{iid}/report.pdf"), ("POST", f"/interviews/{iid}/audio-ticket"),
                             ("POST", f"/interviews/{iid}/end")):
            with self.subTest(route=f"{method} {path}"):
                status, _, _ = call(method, path, token=self.intruder)
                self.assertEqual(status, 404, "a stranger must not learn the interview exists")

    def test_foreign_interview_absent_from_list(self):
        status, body, _ = call("GET", "/interviews", token=self.intruder)
        self.assertEqual(status, 200)
        self.assertNotIn(self.interview_id, [item["id"] for item in body["items"]])

    def test_audio_websocket_requires_valid_ticket(self):
        """FR-6: the WebSocket upgrade is refused without a one-time ticket."""
        path = f"/interviews/{self.interview_id}/audio"
        status, _, _ = call("GET", path)
        self.assertEqual(status, 401)
        status, _, _ = call("GET", path + "?ticket=forged-ticket")
        self.assertEqual(status, 401)

    def test_owner_receives_audio_ticket(self):
        status, body, _ = call("POST", f"/interviews/{self.interview_id}/audio-ticket", token=self.owner)
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(body["ticket"]), 16)


class T05_Profile(unittest.TestCase):
    """FR-2: candidate profile and validation (NFR-2)."""

    def setUp(self):
        _, self.token = register()

    def test_new_account_has_no_profile(self):
        status, _, _ = call("GET", "/profile", token=self.token)
        self.assertEqual(status, 404)

    def test_profile_round_trip_normalises_stack(self):
        status, saved, _ = call("PUT", "/profile", VALID_PROFILE, self.token)
        self.assertEqual(status, 200)
        status, loaded, _ = call("GET", "/profile", token=self.token)
        self.assertEqual(status, 200)
        self.assertEqual(saved, loaded)
        self.assertEqual(loaded["yearsOfExperience"], 3)
        lowered = [t.lower() for t in loaded["techStack"]]
        self.assertEqual(len(lowered), len(set(lowered)), "duplicate technologies must be merged")

    def test_invalid_profiles_rejected(self):
        cases = {
            "missing name": {**VALID_PROFILE, "name": ""},
            "short phone": {**VALID_PROFILE, "phoneNumber": "123"},
            "no experience": {k: v for k, v in VALID_PROFILE.items() if k != "yearsOfExperience"},
            "bad url": {**VALID_PROFILE, "githubUrl": "javascript:alert(1)"},
            "31 technologies": {**VALID_PROFILE, "techStack": [f"t{i}" for i in range(31)]},
            "resume over 10000 chars": {**VALID_PROFILE, "resume": "x" * 10001},
        }
        for label, payload in cases.items():
            with self.subTest(case=label):
                status, _, _ = call("PUT", "/profile", payload, self.token)
                self.assertEqual(status, 400)
        status, _, _ = call("GET", "/profile", token=self.token)
        self.assertEqual(status, 404, "rejected payloads must not be persisted")


class T06_InterviewLifecycle(unittest.TestCase):
    """FR-4, FR-7, FR-12: starting, listing and ending interviews."""

    def test_start_requires_completed_profile(self):
        _, token = register()
        status, _, _ = call("POST", "/interviews", VALID_START, token)
        self.assertEqual(status, 409)

    def test_start_validates_options(self):
        _, token = user_with_profile()
        cases = {
            "language": {**VALID_START, "language": "de"},
            "voice": {**VALID_START, "voiceId": "robot"},
            "unknown level": {**VALID_START, "level": "guru"},
            "missing focus": {k: v for k, v in VALID_START.items() if k != "focus"},
            "retired taskId": {**VALID_START, "taskId": str(uuid.uuid4())},
        }
        for label, payload in cases.items():
            with self.subTest(case=label):
                status, _, _ = call("POST", "/interviews", payload, token)
                self.assertEqual(status, 400)

    def test_start_get_list_and_end(self):
        _, token = user_with_profile()
        status, started, _ = call("POST", "/interviews", VALID_START, token)
        self.assertEqual(status, 201)
        self.assertEqual(started["status"], "in_progress")
        self.assertEqual(started["scenarioVersion"], 2, "new sessions use the adaptive contract")
        self.assertEqual((started["level"], started["position"], started["focus"], started["language"]),
                         ("middle", "backend", "behavioral", "en"))
        iid = started["id"]

        status, fetched, _ = call("GET", f"/interviews/{iid}", token=token)
        self.assertEqual((status, fetched["id"]), (200, iid))

        status, page, _ = call("GET", "/interviews?page=1&pageSize=5", token=token)
        self.assertEqual(status, 200)
        self.assertEqual(page["total"], 1)
        self.assertEqual(page["items"][0]["id"], iid)

        for path in (f"/interviews/{iid}/feedback", f"/interviews/{iid}/report.pdf"):
            with self.subTest(before_end=path):
                status, _, _ = call("GET", path, token=token)
                self.assertEqual(status, 404, "no report exists before any answer")

        status, ended, _ = call("POST", f"/interviews/{iid}/end", token=token)
        self.assertIn(status, (200, 202))
        # 202 means finalisation runs asynchronously (status "finalizing"); wait for the terminal state.
        deadline = time.monotonic() + 30
        while True:
            status, final, _ = call("GET", f"/interviews/{iid}", token=token)
            self.assertEqual(status, 200)
            if final["status"] != "finalizing" or time.monotonic() > deadline:
                break
            time.sleep(0.5)
        self.assertEqual(final["status"], "abandoned", "ending without answers must not produce a score")
        self.assertIsNotNone(final["endedAt"])

        status, _, _ = call("POST", f"/interviews/{iid}/end", token=token)
        self.assertLess(status, 500, "repeating End must be safe")
        status, _, _ = call("GET", f"/interviews/{iid}/report.pdf", token=token)
        self.assertEqual(status, 404, "abandoned interviews have no PDF")

    def test_pagination_bounds(self):
        _, token = register()
        for query in ("page=0", "page=abc", "pageSize=0", "pageSize=51"):
            with self.subTest(query=query):
                status, _, _ = call("GET", f"/interviews?{query}", token=token)
                self.assertEqual(status, 400)


@unittest.skipUnless(os.environ.get("MAHARYCH_LIVE_INTERVIEW"), "needs a completed live interview")
class T07_CompletedInterviewArtifacts(unittest.TestCase):
    """FR-10, FR-11, FR-12, FR-13: transcript, scores, recommendations, PDF."""

    @classmethod
    def setUpClass(cls):
        status, body, _ = call("POST", "/auth/login", {"email": os.environ["MAHARYCH_LIVE_EMAIL"],
                                                       "password": os.environ["MAHARYCH_LIVE_PASSWORD"]})
        assert status == 200, status
        cls.token = body["token"]
        cls.iid = os.environ["MAHARYCH_LIVE_INTERVIEW"]

    def test_interview_marked_completed(self):
        status, body, _ = call("GET", f"/interviews/{self.iid}", token=self.token)
        self.assertEqual((status, body["status"]), (200, "completed"))

    def test_feedback_contains_transcript_scores_and_advice(self):
        status, fb, _ = call("GET", f"/interviews/{self.iid}/feedback", token=self.token)
        self.assertEqual(status, 200)
        self.assertEqual(fb["score_scale"], 100)
        self.assertTrue(0 <= fb["overall_score"] <= 100)
        self.assertTrue(fb["summary"].strip() and fb["recommendation"].strip())
        self.assertTrue(fb["top_strengths"] and fb["top_weaknesses"])
        answered = [q for q in fb["questions"] if q.get("answer")]
        self.assertTrue(answered, "at least one transcribed answer is stored")
        for q in answered:
            self.assertTrue(q["question"].strip())
            self.assertTrue(0 <= q["score"] <= 100)
            self.assertTrue(q["comment"].strip())
        self.assertTrue(any(q.get("clarification") for q in fb["questions"]),
                        "the adaptive dialogue asked at least one follow-up")
        expected = round(sum(t["score"] for t in fb["topic_scores"]) / len(fb["topic_scores"]), 1)
        self.assertAlmostEqual(fb["overall_score"], expected, places=1,
                               msg="overall score is the mean of topic scores")

    def test_pdf_report_downloadable(self):
        status, pdf, headers = call("GET", f"/interviews/{self.iid}/report.pdf", token=self.token, raw=True)
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Content-Type"), "application/pdf")
        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertGreater(len(pdf), 2048)


class T08_Performance(unittest.TestCase):
    """NFR-1/NFR-6 (responsiveness): latency budgets measured through Nginx."""

    def measure(self, fn, runs):
        samples = []
        for _ in range(runs):
            start = time.perf_counter()
            fn()
            samples.append((time.perf_counter() - start) * 1000)
        return samples

    def report(self, name, samples):
        print(f"\n    {name}: n={len(samples)} median={statistics.median(samples):.1f}ms "
              f"p95={percentile(samples, 95):.1f}ms max={max(samples):.1f}ms", end="")

    def test_health_latency_budget(self):
        samples = self.measure(lambda: call("GET", "/health"), 50)
        self.report("health", samples)
        self.assertLess(percentile(samples, 95), 150)

    def test_catalog_latency_budget(self):
        samples = self.measure(lambda: call("GET", "/interview-options"), 30)
        self.report("interview-options", samples)
        self.assertLess(percentile(samples, 95), 300)

    def test_login_latency_budget(self):
        email, _ = register()
        samples = self.measure(lambda: call("POST", "/auth/login",
                                            {"email": email, "password": STRONG_PASSWORD}), 10)
        self.report("login (bcrypt)", samples)
        self.assertLess(percentile(samples, 95), 1000)

    def test_start_interview_latency_budget(self):
        _, token = user_with_profile()
        samples = self.measure(lambda: call("POST", "/interviews", VALID_START, token), 10)
        self.report("start interview", samples)
        self.assertLess(percentile(samples, 95), 1000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
