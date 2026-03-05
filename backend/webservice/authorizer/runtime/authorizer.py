"""
Custom Lambda authorizer for API Gateway.
Validates Cognito Access Token via GetUser; returns IAM policy allow/deny.
Expects env: USER_POOL_REGION (e.g. us-east-1). Token from Authorization: Bearer <access_token>.
"""
import json
import logging
import os

import boto3

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

REGION = os.environ.get("USER_POOL_REGION", os.environ.get("AWS_REGION", "us-east-1"))
COGNITO = boto3.client("cognito-idp", region_name=REGION)


def lambda_handler(event, context):
    """Validate token and return API Gateway policy."""
    token = _get_token(event)
    if not token:
        return _deny(event, "Unauthorized", "Missing or invalid Authorization")

    try:
        resp = COGNITO.get_user(AccessToken=token)
        principal_id = next(
            (a["Value"] for a in resp.get("UserAttributes", []) if a["Name"] == "sub"),
            resp["Username"],
        )
        return _allow(event, principal_id, context_attrs(resp))
    except COGNITO.exceptions.NotAuthorizedException as e:
        LOGGER.warning("Token invalid or expired: %s", e)
        return _deny(event, "Unauthorized", "Invalid or expired token")
    except Exception as e:
        LOGGER.exception("Authorizer error: %s", e)
        return _deny(event, "Unauthorized", "Authorization failed")


def _get_token(event):
    auth = (event.get("headers") or {}).get("Authorization") or (event.get("headers") or {}).get("authorization")
    if not auth or not auth.startswith("Bearer "):
        return None
    return auth[7:].strip()


def _allow(event, principal_id, context_attrs=None):
    method_arn = event.get("methodArn") or ""
    # Allow invoke on this method (and optionally stage/path)
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
    # methodArn: arn:aws:execute-api:region:account:apiId/stage/method/path
    parts = method_arn.split("/")
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}/*"
    return method_arn


def context_attrs(get_user_response):
    """Build context map (string values only) from Cognito GetUser."""
    out = {}
    for a in get_user_response.get("UserAttributes", []):
        name, value = a.get("Name"), a.get("Value")
        if name and value is not None:
            out[name] = str(value)
    return out
