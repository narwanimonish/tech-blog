"""
Unit tests for common.error_mapper (exception → FrontendError).
"""
import json

import pytest
from botocore.exceptions import ClientError

from common.errors import AppError
from common.error_mapper import map_exception, FrontendError


def test_app_error_maps_to_frontend_error():
    exc = AppError("VALIDATION_FAILED", "Invalid field", status_code=400, details={"field": "email"})
    result = map_exception(exc)
    assert result.code == "VALIDATION_FAILED"
    assert result.message == "Invalid field"
    assert result.status_code == 400
    assert result.details == {"field": "email"}


def test_json_decode_error_maps_to_bad_request():
    exc = json.JSONDecodeError("Expecting value", "doc", 0)
    result = map_exception(exc)
    assert result.code == "BAD_REQUEST"
    assert result.message == "Invalid JSON"
    assert result.status_code == 400


def test_value_error_maps_to_bad_request():
    result = map_exception(ValueError("invalid id"))
    assert result.code == "BAD_REQUEST"
    assert result.status_code == 400


def test_client_error_resource_not_found_maps_to_not_found():
    resp = {"Error": {"Code": "ResourceNotFoundException", "Message": "Requested resource not found"}}
    exc = ClientError(resp, "GetItem")
    result = map_exception(exc)
    assert result.code == "NOT_FOUND"
    assert result.status_code == 404


def test_client_error_not_authorized_maps_to_401():
    resp = {"Error": {"Code": "NotAuthorizedException", "Message": "Token expired"}}
    exc = ClientError(resp, "GetUser")
    result = map_exception(exc)
    assert result.code == "UNAUTHORIZED"
    assert result.status_code == 401


def test_unknown_exception_maps_to_internal_error():
    result = map_exception(RuntimeError("something broke"))
    assert result.code == "INTERNAL_ERROR"
    assert result.status_code == 500
    assert result.message == "Internal server error"


def test_unknown_exception_uses_custom_default_message():
    result = map_exception(RuntimeError("x"), default_message="Custom message")
    assert result.message == "Custom message"
