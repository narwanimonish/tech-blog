"""
Cognito Post-confirmation trigger: after a user signs up and verifies (e.g. email),
writes the user into the DynamoDB users table so the app has a single source of users.
Only runs on PostConfirmation_ConfirmSignUp (not on password reset confirmation).
Uses boto3 only (no shared layer) so this Lambda can live in the Auth stack.
"""

import logging
import os
from datetime import datetime, timezone

import boto3

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

TABLE_NAME = os.environ.get("usersStoreTable", "")
USERS_LIST_PK = "listPk"
USERS_LIST_PK_VALUE = "USER"

# Only create/update users table on sign-up confirmation, not on ForgotPassword confirm
TRIGGER_SIGNUP = "PostConfirmation_ConfirmSignUp"


def _default_role_for_new_user(table) -> str:
    """First user in the table is admin; subsequent sign-ups default to reader."""
    try:
        resp = table.scan(Limit=1, Select="COUNT")
        return "admin" if resp.get("Count", 0) == 0 else "reader"
    except Exception:
        LOGGER.exception("Failed to count users for default role")
        return "reader"


def lambda_handler(event, context):
    if not TABLE_NAME:
        LOGGER.error("usersStoreTable not set")
        return event

    trigger_source = event.get("triggerSource", "")
    if trigger_source != TRIGGER_SIGNUP:
        LOGGER.info("Skipping trigger source: %s", trigger_source)
        return event

    attrs = event.get("request", {}).get("userAttributes", {})
    user_id = attrs.get("sub")
    if not user_id:
        LOGGER.warning("No sub in userAttributes")
        return event

    cognito_username = event.get("userName") or ""
    email = attrs.get("email", "")
    name = attrs.get("name") or attrs.get("given_name") or attrs.get("preferred_username") or ""

    try:
        table = boto3.resource("dynamodb").Table(TABLE_NAME)
        item = {
            "userId": user_id,
            "email": email,
            "role": _default_role_for_new_user(table),
            "creation_time": datetime.now(timezone.utc).isoformat(),
            USERS_LIST_PK: USERS_LIST_PK_VALUE,
        }
        if cognito_username:
            item["cognitoUsername"] = cognito_username
        if name:
            item["name"] = name
        table.put_item(Item=item)
        LOGGER.info("Created user in DynamoDB: %s (role=%s)", user_id, item["role"])
    except Exception as e:
        LOGGER.exception("Failed to write user to DynamoDB: %s", e)
        # Do not fail the confirmation; Cognito user is already created
    return event
