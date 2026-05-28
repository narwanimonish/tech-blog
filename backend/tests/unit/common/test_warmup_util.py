from common import warmup_util


def test_is_warmup_event_true_for_scheduled_event():
    event = {
        "source": "aws.events",
        "detail-type": "Scheduled Event",
        "detail": {},
    }
    assert warmup_util.is_warmup_event(event) is True


def test_is_warmup_event_false_for_api_gateway():
    event = {
        "httpMethod": "GET",
        "path": "/posts",
        "requestContext": {"authorizer": {"sub": "user-1"}},
    }
    assert warmup_util.is_warmup_event(event) is False


def test_api_warmup_response():
    response = warmup_util.api_warmup_response()
    assert response["statusCode"] == 200
    assert '"warmed": true' in response["body"]
