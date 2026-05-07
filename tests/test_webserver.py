import unittest

from src.webserver import server


class FakeClient:
    region = "eu"
    puuid = "player-1"

    def party_join(self, party_id):
        return {"CurrentPartyID": party_id}

    def party_request_to_join(self, party_id, friend_id):
        return {"Requests": [{"RequestedBySubject": self.puuid}]}


class WebserverTests(unittest.TestCase):
    def setUp(self):
        server.configure(FakeClient(), {}, token="secret")
        self.client = server.app.test_client()

    def test_join_requires_post(self):
        response = self.client.get("/valorant/join/party-1?region=eu&token=secret")

        self.assertEqual(response.status_code, 405)

    def test_confirm_join_does_not_require_token_and_renders_post_form(self):
        response = self.client.get("/valorant/confirm/join/party-1?region=eu")

        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")
        self.assertIn('method="post"', html)
        self.assertIn('action="/valorant/join/party-1"', html)
        self.assertIn('name="token" value="secret"', html)
        self.assertNotIn("token=secret", html)

    def test_confirm_join_rejects_wrong_region(self):
        response = self.client.get("/valorant/confirm/join/party-1?region=na")

        self.assertEqual(response.status_code, 409)

    def test_confirm_join_rejects_unsafe_party_id(self):
        response = self.client.get("/valorant/confirm/join/party%201?region=eu")

        self.assertEqual(response.status_code, 400)

    def test_join_requires_token(self):
        response = self.client.post("/valorant/join/party-1?region=eu")

        self.assertEqual(response.status_code, 403)

    def test_join_rejects_wrong_region(self):
        response = self.client.post(
            "/valorant/join/party-1?region=na",
            headers={"X-Valorant-Rpc-Token": "secret"},
        )

        self.assertEqual(response.status_code, 409)

    def test_join_accepts_valid_token_and_region(self):
        response = self.client.post(
            "/valorant/join/party-1?region=eu",
            headers={"X-Valorant-Rpc-Token": "secret"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "ok")

    def test_join_accepts_confirmation_form_token(self):
        response = self.client.post(
            "/valorant/join/party-1",
            data={"region": "eu", "token": "secret"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "ok")

    def test_join_rejects_cross_origin_post(self):
        response = self.client.post(
            "/valorant/join/party-1?region=eu",
            headers={"X-Valorant-Rpc-Token": "secret", "Origin": "https://example.com"},
        )

        self.assertEqual(response.status_code, 403)

    def test_request_confirm_and_post_flow(self):
        confirm = self.client.get("/valorant/confirm/request/party-1/friend-1?region=eu")
        response = self.client.post(
            "/valorant/request/party-1/friend-1",
            data={"region": "eu", "token": "secret"},
        )

        self.assertEqual(confirm.status_code, 200)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "ok")

    def test_security_headers_are_set(self):
        response = self.client.get("/")

        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])
