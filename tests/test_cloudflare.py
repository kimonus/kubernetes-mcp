import json
import time
import unittest

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from src.cloudflare import AccessAuthenticator, AccessDenied


class AccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(cls.key.public_key()))
        jwk.update({"kid": "test-key", "alg": "RS256", "use": "sig"})
        cls.jwks = {"keys": [jwk]}

    def setUp(self):
        self.auth = AccessAuthenticator("https://test.cloudflareaccess.com", "audience", {"user@example.com"},
                                        fetch=lambda: self.jwks)

    def token(self, **overrides):
        now = int(time.time())
        claims = {"iss": "https://test.cloudflareaccess.com", "aud": "audience",
                  "email": "user@example.com", "sub": "user", "iat": now, "exp": now + 60}
        claims.update(overrides)
        return jwt.encode(claims, self.key, algorithm="RS256", headers={"kid": "test-key"})

    def test_valid(self):
        self.auth.authenticate(self.token())

    def test_claims_rejected(self):
        for claims in ({"aud": "wrong"}, {"iss": "https://wrong.cloudflareaccess.com"},
                       {"email": "other@example.com"}, {"exp": int(time.time()) - 1}):
            with self.subTest(claims=claims), self.assertRaises(AccessDenied):
                self.auth.authenticate(self.token(**claims))

    def test_invalid_signature_rejected(self):
        other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        token = jwt.encode({"iss": "https://test.cloudflareaccess.com", "aud": "audience", "email": "user@example.com",
                            "sub": "user", "iat": int(time.time()), "exp": int(time.time()) + 60},
                           other, algorithm="RS256", headers={"kid": "test-key"})
        with self.assertRaises(AccessDenied):
            self.auth.authenticate(token)

    def test_bad_issuer_and_unavailable_keys_fail_closed(self):
        with self.assertRaises(ValueError):
            AccessAuthenticator("https://evil.example", "audience", {"user@example.com"})
        def unavailable():
            raise OSError("private details")
        self.auth.fetch = unavailable
        with self.assertRaises(AccessDenied):
            self.auth.authenticate(self.token())

    def test_unknown_key_refresh_is_rate_limited(self):
        fetches = []
        def fetch():
            fetches.append(1)
            return self.jwks
        self.auth.fetch = fetch
        unknown = jwt.encode({"sub": "x"}, self.key, algorithm="RS256", headers={"kid": "missing"})
        for _ in range(2):
            with self.assertRaises(AccessDenied):
                self.auth.authenticate(unknown)
        self.assertEqual(len(fetches), 1)

    def test_duplicate_key_id_fails_closed(self):
        self.auth.fetch = lambda: {"keys": self.jwks["keys"] * 2}
        with self.assertRaises(AccessDenied):
            self.auth.authenticate(self.token())


if __name__ == "__main__":
    unittest.main()
