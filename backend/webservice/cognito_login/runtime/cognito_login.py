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
from core.users.service import UsersService

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

REGION = os.environ.get("USER_POOL_REGION", os.environ.get("AWS_REGION", "us-east-1"))
CLIENT_ID = os.environ.get("USER_POOL_CLIENT_ID", "")
USERS_TABLE_NAME = os.environ.get("usersStoreTable", "")
COGNITO = boto3.client("cognito-idp", region_name=REGION)
TABLE = boto3.resource("dynamodb").Table(USERS_TABLE_NAME) if USERS_TABLE_NAME else None
SERVICE = UsersService(TABLE) if TABLE else None


def lambda_handler(event, context):
    request_id = getattr(context, "aws_request_id", "unknown")
    LOGGER.info("auth_login start request_id=%s", request_id)

    if not CLIENT_ID:
        LOGGER.error("auth_login missing USER_POOL_CLIENT_ID request_id=%s", request_id)
        return simple_api_util.build_error_response("CONFIG_ERROR", "Missing USER_POOL_CLIENT_ID", 500, request_id=request_id)

    try:
        LOGGER.info("auth_login reading request body request_id=%s", request_id)
        body = event.get("body")
        if not body:
            LOGGER.warning("auth_login body missing request_id=%s", request_id)
            return simple_api_util.build_error_response("BAD_REQUEST", "Body required", 400, request_id=request_id)

        try:
            LOGGER.info("auth_login parsing JSON body request_id=%s", request_id)
            data = json.loads(body)
        except json.JSONDecodeError:
            LOGGER.warning("auth_login invalid JSON request_id=%s", request_id)
            return simple_api_util.build_error_response("BAD_REQUEST", "Invalid JSON", 400, request_id=request_id)

        LOGGER.info("auth_login validating payload request_id=%s", request_id)
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        if not username or not password:
            LOGGER.warning("auth_login missing username/password request_id=%s", request_id)
            return simple_api_util.build_error_response("BAD_REQUEST", "username and password are required", 400, request_id=request_id)

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
            return simple_api_util.build_error_response(
                "AUTH_CHALLENGE_REQUIRED",
                "Authentication challenge required",
                401,
                details={"data": resp},
                request_id=request_id,
            )

        # Intentional full token logging per request.
        LOGGER.info("auth_login token payload request_id=%s username=%s tokens=%s", request_id, username, json.dumps(auth))
        _upsert_user_from_access_token(auth.get("AccessToken"), request_id)
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
        return simple_api_util.build_error_response("UNAUTHORIZED", "Invalid username or password", 401, request_id=request_id)
    except COGNITO.exceptions.UserNotConfirmedException:
        LOGGER.warning("auth_login user not confirmed request_id=%s", request_id)
        return simple_api_util.build_error_response("USER_NOT_CONFIRMED", "User not confirmed", 403, request_id=request_id)
    except Exception as e:
        LOGGER.exception("auth_login unexpected error request_id=%s error=%s", request_id, e)
        return simple_api_util.build_error_from_exception(e, request_id=request_id)


def _upsert_user_from_access_token(access_token, request_id):
    if not access_token:
        LOGGER.warning("auth_login skip user upsert: no access token request_id=%s", request_id)
        return
    if not SERVICE:
        LOGGER.warning("auth_login skip user upsert: usersStoreTable missing request_id=%s", request_id)
        return

    try:
        LOGGER.info("auth_login fetching user profile from Cognito request_id=%s", request_id)
        resp = COGNITO.get_user(AccessToken=access_token)
        attrs = {a.get("Name"): a.get("Value") for a in resp.get("UserAttributes", [])}
        user_id = attrs.get("sub")
        if not user_id:
            LOGGER.warning("auth_login skip user upsert: missing sub request_id=%s", request_id)
            return

        data = {"email": attrs.get("email", "")}
        name = attrs.get("name") or attrs.get("given_name") or attrs.get("preferred_username")
        if name:
            data["name"] = name

        SERVICE.put_user(user_id, data)
        LOGGER.info("auth_login upserted user in DynamoDB request_id=%s userId=%s", request_id, user_id)
    except Exception as e:
        LOGGER.exception("auth_login failed to upsert user request_id=%s error=%s", request_id, e)
