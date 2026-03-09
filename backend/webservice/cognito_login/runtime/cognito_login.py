"""
POST /auth/login
Authenticate against Cognito and return tokens.

Warning: this handler intentionally logs full token payload as requested.
"""
import json
import logging
import os

import boto3

from common import simple_api_util

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

REGION = os.environ.get("USER_POOL_REGION", os.environ.get("AWS_REGION", "us-east-1"))
CLIENT_ID = os.environ.get("USER_POOL_CLIENT_ID", "")
COGNITO = boto3.client("cognito-idp", region_name=REGION)


def lambda_handler(event, context):
    request_id = getattr(context, "aws_request_id", "unknown")
    LOGGER.info("auth_login start request_id=%s", request_id)

    if not CLIENT_ID:
        LOGGER.error("auth_login missing USER_POOL_CLIENT_ID request_id=%s", request_id)
        return simple_api_util.build_response(500, {"message": "Missing USER_POOL_CLIENT_ID"})

    try:
        LOGGER.info("auth_login reading request body request_id=%s", request_id)
        body = event.get("body")
        if not body:
            LOGGER.warning("auth_login body missing request_id=%s", request_id)
            return simple_api_util.build_response(400, {"message": "Body required"})

        try:
            LOGGER.info("auth_login parsing JSON body request_id=%s", request_id)
            data = json.loads(body)
        except json.JSONDecodeError:
            LOGGER.warning("auth_login invalid JSON request_id=%s", request_id)
            return simple_api_util.build_response(400, {"message": "Invalid JSON"})

        LOGGER.info("auth_login validating payload request_id=%s", request_id)
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        if not username or not password:
            LOGGER.warning("auth_login missing username/password request_id=%s", request_id)
            return simple_api_util.build_response(400, {"message": "username and password are required"})

        LOGGER.info("auth_login initiating Cognito auth request_id=%s username=%s", request_id, username)
        resp = COGNITO.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": password,
            },
        )
        LOGGER.info("auth_login Cognito auth returned request_id=%s username=%s", request_id, username)

        auth = resp.get("AuthenticationResult") or {}
        if not auth:
            LOGGER.warning("auth_login challenge required request_id=%s username=%s", request_id, username)
            return simple_api_util.build_response(401, {"message": "Authentication challenge required", "data": resp})

        # Intentional full token logging per request.
        LOGGER.info("auth_login token payload request_id=%s username=%s tokens=%s", request_id, username, json.dumps(auth))
        LOGGER.info("auth_login success request_id=%s username=%s", request_id, username)
        return simple_api_util.build_response(
            200,
            {
                "accessToken": auth.get("AccessToken"),
                "idToken": auth.get("IdToken"),
                "refreshToken": auth.get("RefreshToken"),
                "expiresIn": auth.get("ExpiresIn"),
                "tokenType": auth.get("TokenType"),
            },
        )
    except COGNITO.exceptions.NotAuthorizedException:
        LOGGER.warning("auth_login invalid credentials request_id=%s", request_id)
        return simple_api_util.build_response(401, {"message": "Invalid username or password"})
    except COGNITO.exceptions.UserNotConfirmedException:
        LOGGER.warning("auth_login user not confirmed request_id=%s", request_id)
        return simple_api_util.build_response(403, {"message": "User not confirmed"})
    except Exception as e:
        LOGGER.exception("auth_login unexpected error request_id=%s error=%s", request_id, e)
        return simple_api_util.build_response(500, {"message": "Internal server error"})
