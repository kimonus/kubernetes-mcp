"""Validate Cloudflare Access assertions at the origin."""
import json
import re
import threading
import time
import urllib.error
import urllib.request

import jwt


class AccessDenied(Exception):
    pass


class AccessAuthenticator:
    def __init__(self, issuer, audience, emails, fetch=None):
        if not re.fullmatch(r"https://[a-z0-9-]+\.cloudflareaccess\.com", issuer):
            raise ValueError("Invalid Cloudflare Access issuer")
        if not audience or not emails:
            raise ValueError("Access audience and email allowlist are required")
        self.issuer = issuer
        self.audience = audience
        self.emails = {email.casefold() for email in emails}
        self.fetch = fetch or self._fetch
        self.keys = {}
        self.expires = 0.0
        self.last_fetch = float("-inf")
        self.lock = threading.Lock()

    def _fetch(self):
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        with opener.open(self.issuer + "/cdn-cgi/access/certs", timeout=5) as response:
            body = response.read(65537)
        if len(body) > 65536:
            raise ValueError("JWKS too large")
        return json.loads(body)

    def authenticate(self, assertion):
        try:
            if not assertion or len(assertion) > 8192:
                raise AccessDenied()
            header = jwt.get_unverified_header(assertion)
            kid = header.get("kid")
            if header.get("alg") != "RS256" or not isinstance(kid, str) or not kid:
                raise AccessDenied()
            with self.lock:
                now = time.monotonic()
                key = self.keys.get(kid) if now < self.expires else None
                if key is None:
                    if now - self.last_fetch < 30:
                        raise AccessDenied()
                    self.last_fetch = now
                    keyset = jwt.PyJWKSet.from_dict(self.fetch())
                    keys = [k for k in keyset.keys if k.key_id and k.algorithm_name == "RS256"
                            and k.public_key_use in (None, "sig")]
                    if len({k.key_id for k in keys}) != len(keys):
                        raise ValueError("Duplicate signing key ID")
                    self.keys = {k.key_id: k.key for k in keys}
                    self.expires = now + 300
                    key = self.keys.get(kid)
                    if key is None:
                        raise AccessDenied()
            claims = jwt.decode(assertion, key, algorithms=["RS256"], audience=self.audience,
                                issuer=self.issuer,
                                options={"require": ["aud", "email", "exp", "iat", "iss", "sub"]})
            email = claims.get("email")
            if not isinstance(email, str) or email.strip().casefold() not in self.emails:
                raise AccessDenied()
        except (jwt.PyJWTError, ValueError, TypeError, KeyError, AttributeError, OSError, urllib.error.URLError) as exc:
            raise AccessDenied() from exc
