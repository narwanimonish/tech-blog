"""
Custom Lambda authorizer for API Gateway.
Validates Cognito access tokens locally via JWKS (no GetUser round trip).
Expects env: USER_POOL_REGION, USER_POOL_ID, USER_POOL_CLIENT_ID, usersStoreTable.
Token from Authorization: Bearer <access_token>.
"""

import logging
import os

import jwt
from common import cognito_jwt_util, role_cache, role_util, warmup_util

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

REGION = os.environ.get("USER_POOL_REGION", os.environ.get("AWS_REGION", "us-east-1"))
USER_POOL_ID = os.environ.get("USER_POOL_ID", "").strip()
CLIENT_ID = os.environ.get("USER_POOL_CLIENT_ID", "").strip()
USERS_TABLE = os.environ.get("usersStoreTable", "")


def lambda_handler(event, context):
    """Validate token and return API Gateway policy."""
    if warmup_util.is_warmup_event(event):
        return warmup_util.authorizer_warmup_response()

    token = _get_token(event)
    if not token:
        return _deny(event, "Unauthorized", "Missing or invalid Authorization")

    if not USER_POOL_ID or not CLIENT_ID:
        LOGGER.error("authorizer missing USER_POOL_ID or USER_POOL_CLIENT_ID")
        return _deny(event, "Unauthorized", "Authorization misconfigured")

    try:
        claims = cognito_jwt_util.validate_access_token(
            token,
            region=REGION,
            user_pool_id=USER_POOL_ID,
            client_id=CLIENT_ID,
        )
        principal_id = str(claims.get("sub") or claims.get("username") or "")
        if not principal_id:
            return _deny(event, "Unauthorized", "Missing subject in token")

        ctx = cognito_jwt_util.claims_to_authorizer_context(claims)
        if USERS_TABLE:
            ctx["role"] = role_cache.get_cached_role(
                principal_id,
                lambda: role_util.get_user_role(principal_id, USERS_TABLE),
            )
        return _allow(event, principal_id, ctx)
    except jwt.ExpiredSignatureError:
        return _deny(event, "Unauthorized", "Invalid or expired token")
    except jwt.InvalidTokenError:
        return _deny(event, "Unauthorized", "Invalid or expired token")
    except Exception:
        LOGGER.exception("authorizer unexpected error")
        return _deny(event, "Unauthorized", "Authorization failed")


def _get_token(event):
    auth = (event.get("headers") or {}).get("Authorization") or (event.get("headers") or {}).get("authorization")
    if not auth or not auth.startswith("Bearer "):
        return None
    return auth[7:].strip()


def _allow(event, principal_id, context_attrs=None):
    method_arn = event.get("methodArn") or ""
    resource = _resource_arn(method_arn)
    return {
        "principalId": principal_id,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "execute-api:Invoke",
                    "Effect": "Allow",
                    "Resource": resource,
                }
            ],
        },
        "context": context_attrs or {},
    }


def _deny(event, principal_id, reason):
    method_arn = event.get("methodArn") or ""
    resource = _resource_arn(method_arn)
    LOGGER.warning("authorizer deny principalId=%s reason=%s", principal_id, reason)
    return {
        "principalId": principal_id,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "execute-api:Invoke",
                    "Effect": "Deny",
                    "Resource": resource,
                }
            ],
        },
    }


def _resource_arn(method_arn):
    parts = method_arn.split("/")
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}/*"
    return method_arn
