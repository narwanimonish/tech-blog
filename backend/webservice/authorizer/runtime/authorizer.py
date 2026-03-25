"""
Custom Lambda authorizer for API Gateway.
Validates Cognito Access Token via GetUser; returns IAM policy allow/deny.
Expects env: USER_POOL_REGION (e.g. us-east-1). Token from Authorization: Bearer <access_token>.
"""
import logging
import os

import boto3

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

REGION = os.environ.get("USER_POOL_REGION", os.environ.get("AWS_REGION", "us-east-1"))
COGNITO = boto3.client("cognito-idp", region_name=REGION)


def lambda_handler(event, context):
    """Validate token and return API Gateway policy."""
    request_id = getattr(context, "aws_request_id", "unknown")
    method_arn = event.get("methodArn") or ""
    LOGGER.info("authorizer start request_id=%s methodArn=%s", request_id, method_arn)

    token = _get_token(event)
    if not token:
        LOGGER.warning("authorizer missing/invalid bearer token request_id=%s", request_id)
        return _deny(event, "Unauthorized", "Missing or invalid Authorization")

    try:
        LOGGER.info("authorizer validating token with Cognito request_id=%s", request_id)
        resp = COGNITO.get_user(AccessToken=token)
        principal_id = next(
            (a["Value"] for a in resp.get("UserAttributes", []) if a["Name"] == "sub"),
            resp["Username"],
        )
        ctx = context_attrs(resp)
        LOGGER.info(
            "authorizer allow request_id=%s principalId=%s context_keys=%s",
            request_id,
            principal_id,
            list(ctx.keys()),
        )
        return _allow(event, principal_id, ctx)
    except COGNITO.exceptions.NotAuthorizedException as e:
        LOGGER.warning("authorizer token invalid/expired request_id=%s error=%s", request_id, e)
        return _deny(event, "Unauthorized", "Invalid or expired token")
    except Exception as e:
        LOGGER.exception("authorizer unexpected error request_id=%s error=%s", request_id, e)
        return _deny(event, "Unauthorized", "Authorization failed")


def _get_token(event):
    LOGGER.info("authorizer extracting Authorization header")
    auth = (event.get("headers") or {}).get("Authorization") or (event.get("headers") or {}).get("authorization")
    if not auth or not auth.startswith("Bearer "):
        LOGGER.warning("authorizer Authorization header missing or malformed")
        return None
    token = auth[7:].strip()
    LOGGER.info("authorizer extracted bearer token length=%s", len(token))
    return token


def _allow(event, principal_id, context_attrs=None):
    method_arn = event.get("methodArn") or ""
    # Allow invoke on this method (and optionally stage/path)
    resource = _resource_arn(method_arn)
    LOGGER.info("authorizer building allow policy principalId=%s resource=%s", principal_id, resource)
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
    LOGGER.warning("authorizer building deny policy principalId=%s resource=%s reason=%s", principal_id, resource, reason)
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
    LOGGER.info("authorizer calculating resource ARN from methodArn=%s", method_arn)
    parts = method_arn.split("/")
    if len(parts) >= 2:
        resource = f"{parts[0]}/{parts[1]}/*"
        LOGGER.info("authorizer resource ARN resolved=%s", resource)
        return resource
    LOGGER.info("authorizer fallback resource ARN=%s", method_arn)
    return method_arn


def context_attrs(get_user_response):
    """Build context map (string values only) from Cognito GetUser."""
    LOGGER.info("authorizer building context from Cognito attributes")
    out = {}
    for a in get_user_response.get("UserAttributes", []):
        name, value = a.get("Name"), a.get("Value")
        if name and value is not None:
            out[name] = str(value)
    LOGGER.info("authorizer context built keys=%s", list(out.keys()))
    return out
