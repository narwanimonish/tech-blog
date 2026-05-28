from unittest.mock import MagicMock, patch

import jwt
import pytest
from common import cognito_jwt_util


@patch("common.cognito_jwt_util._jwks_client")
def test_validate_access_token_returns_claims(mock_jwks_client):
    signing_key = MagicMock()
    signing_key.key = "public-key"
    mock_jwks_client.return_value.get_signing_key_from_jwt.return_value = signing_key

    claims = {"sub": "user-1", "email": "a@example.com", "token_use": "access"}
    with patch("common.cognito_jwt_util.jwt.decode", return_value=claims) as mock_decode:
        result = cognito_jwt_util.validate_access_token(
            "token",
            region="us-east-1",
            user_pool_id="pool-1",
            client_id="client-1",
        )

    assert result == claims
    mock_decode.assert_called_once()


def test_claims_to_authorizer_context_maps_known_fields():
    context = cognito_jwt_util.claims_to_authorizer_context(
        {
            "sub": "user-1",
            "email": "a@example.com",
            "name": "Ada",
            "cognito:username": "ada",
        }
    )
    assert context["sub"] == "user-1"
    assert context["email"] == "a@example.com"
    assert context["name"] == "Ada"
    assert context["cognitoUsername"] == "ada"


@patch("common.cognito_jwt_util.jwt.decode", side_effect=jwt.InvalidTokenError("bad token"))
@patch("common.cognito_jwt_util._jwks_client")
def test_validate_access_token_rejects_invalid_token(mock_jwks_client, _mock_decode):
    mock_jwks_client.return_value.get_signing_key_from_jwt.return_value = MagicMock(key="key")
    with pytest.raises(jwt.InvalidTokenError):
        cognito_jwt_util.validate_access_token(
            "token",
            region="us-east-1",
            user_pool_id="pool-1",
            client_id="client-1",
        )
