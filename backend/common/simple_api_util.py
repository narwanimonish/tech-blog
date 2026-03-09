"""
Simple API response helpers for Lambda + API Gateway.
Use for basic REST APIs that return JSON with CORS.
"""
import json

from common.error_mapper import map_exception

# CORS headers for simple GET/PUT/POST/DELETE APIs
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,PUT,POST,OPTIONS,DELETE",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
}


def build_response(status_code, body):
    """
    Build API Gateway response with status code, CORS headers, and JSON body.

    :param status_code: int, e.g. 200, 400, 404, 500
    :param body: dict or any JSON-serializable value; if not dict, wrapped as {"message": str(body)}
    :return: dict with statusCode, headers, body (JSON string)
    """
    if not isinstance(body, dict):
        body = {"message": str(body)}
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body),
    }


def build_error_response(code, message, status_code, details=None, request_id=None):
    body = {"errorCode": code, "message": message}
    if details is not None:
        body["details"] = details
    if request_id:
        body["requestId"] = request_id
    return build_response(status_code, body)


def build_error_from_exception(exc, default_message="Internal server error", request_id=None):
    mapped = map_exception(exc, default_message=default_message)
    return build_error_response(
        code=mapped.code,
        message=mapped.message,
        status_code=mapped.status_code,
        details=mapped.details,
        request_id=request_id,
    )
