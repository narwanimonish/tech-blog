"""Validate Cognito access tokens locally via JWKS (avoids GetUser round trip)."""

from __future__ import annotations

import jwt
from jwt import PyJWKClient

_jwk_clients: dict[str, PyJWKClient] = {}


def _issuer(region: str, user_pool_id: str) -> str:
    return f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}"


def _jwks_client(region: str, user_pool_id: str) -> PyJWKClient:
    url = f"{_issuer(region, user_pool_id)}/.well-known/jwks.json"
    client = _jwk_clients.get(url)
    if client is None:
        client = PyJWKClient(url, cache_keys=True)
        _jwk_clients[url] = client
    return client


def validate_access_token(
    token: str,
    *,
    region: str,
    user_pool_id: str,
    client_id: str,
) -> dict:
    """
    Verify RS256 signature, issuer, audience, expiry, and token_use=access.
    Returns JWT claims (sub, email, etc.).
    """
    issuer = _issuer(region, user_pool_id)
    signing_key = _jwks_client(region, user_pool_id).get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=client_id,
        issuer=issuer,
        options={"require": ["exp", "sub", "token_use"]},
    )
    if claims.get("token_use") != "access":
        raise jwt.InvalidTokenError("token_use must be access")
    return claims


def claims_to_authorizer_context(claims: dict) -> dict[str, str]:
    """Map JWT claims to API Gateway authorizer context (string values only)."""
    context: dict[str, str] = {}
    for key in ("sub", "email", "name", "username", "cognito:username"):
        value = claims.get(key)
        if value is not None and str(value).strip():
            context[key if key != "cognito:username" else "cognitoUsername"] = str(value)
    if "sub" not in context and claims.get("username"):
        context["sub"] = str(claims["username"])
    return context
