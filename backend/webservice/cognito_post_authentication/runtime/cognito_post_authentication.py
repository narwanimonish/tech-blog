"""
Cognito Post-authentication trigger.
Runs after successful user authentication and logs a login audit record.

Important: Cognito trigger events do not include access/id/refresh tokens.
"""

import json
import logging

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


def lambda_handler(event, context):
    attrs = (event.get("request") or {}).get("userAttributes") or {}
    log_record = {
        "triggerSource": event.get("triggerSource"),
        "userName": event.get("userName"),
        "sub": attrs.get("sub"),
        "email": attrs.get("email"),
        "clientId": event.get("callerContext", {}).get("clientId"),
    }
    LOGGER.info("Cognito login audit: %s", json.dumps(log_record))
    return event
