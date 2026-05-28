"""Detect EventBridge scheduled pings used to keep Lambda containers warm."""


def is_warmup_event(event: dict) -> bool:
    """True when invoked directly by EventBridge on a schedule (not API Gateway)."""
    return (
        event.get("source") == "aws.events"
        and event.get("detail-type") == "Scheduled Event"
    )


def api_warmup_response():
    """Minimal API Gateway-style response for scheduled warm pings."""
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": '{"warmed": true}',
    }


def authorizer_warmup_response():
    """Minimal authorizer response for scheduled warm pings."""
    return {
        "principalId": "warmer",
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "execute-api:Invoke",
                    "Effect": "Allow",
                    "Resource": "*",
                }
            ],
        },
    }
