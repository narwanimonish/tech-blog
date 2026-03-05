"""
Simple API response helpers for Lambda + API Gateway.
Use for basic REST APIs that return JSON with CORS.
"""
import json

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
