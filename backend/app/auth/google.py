"""Google ID-token verification (OIDC).

The frontend obtains an ID token from Google Identity Services and posts it to
/auth/google; we verify the signature against Google's published JWKS and check
the issuer/audience claims before trusting it.
"""
import requests
from authlib.jose import JsonWebToken
from authlib.jose.errors import JoseError

GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = ["https://accounts.google.com", "accounts.google.com"]

_jwks_cache: dict | None = None


class GoogleAuthError(Exception):
    """The ID token could not be verified."""


def _get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache is None:
        resp = requests.get(GOOGLE_JWKS_URL, timeout=10)
        resp.raise_for_status()
        _jwks_cache = resp.json()
    return _jwks_cache


def verify_google_id_token(credential: str, client_id: str) -> dict:
    """Verify a Google ID token and return its claims (sub, email, name, ...)."""
    jwt = JsonWebToken(["RS256"])
    try:
        claims = jwt.decode(
            credential,
            _get_jwks(),
            claims_options={
                "iss": {"essential": True, "values": GOOGLE_ISSUERS},
                "aud": {"essential": True, "value": client_id},
                "exp": {"essential": True},
            },
        )
        claims.validate()
    except (JoseError, ValueError) as exc:
        # Key rotation: refresh the JWKS once and retry before giving up.
        global _jwks_cache
        _jwks_cache = None
        try:
            claims = jwt.decode(
                credential,
                _get_jwks(),
                claims_options={
                    "iss": {"essential": True, "values": GOOGLE_ISSUERS},
                    "aud": {"essential": True, "value": client_id},
                    "exp": {"essential": True},
                },
            )
            claims.validate()
        except (JoseError, ValueError):
            raise GoogleAuthError("Invalid Google credential") from exc
    return dict(claims)
