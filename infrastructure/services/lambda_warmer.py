"""EventBridge schedule + dispatcher Lambda that asynchronously invokes warm targets."""

from __future__ import annotations

from aws_cdk import Duration, Fn, aws_events as events, aws_events_targets as targets
from aws_cdk import aws_lambda as _lambda
from constructs import Construct

# Forwards the EventBridge scheduled event payload so handlers can short-circuit via warmup_util.
_WARMER_CODE = """\
import json
import os

import boto3

_CLIENT = boto3.client("lambda")
_ARNS = [a.strip() for a in os.environ.get("TARGET_FUNCTION_ARNS", "").split(",") if a.strip()]


def handler(event, context):
    payload = json.dumps(event).encode("utf-8")
    for arn in _ARNS:
        try:
            _CLIENT.invoke(FunctionName=arn, InvocationType="Event", Payload=payload)
        except Exception:
            pass
    return {"warmed": len(_ARNS)}
"""


class LambdaWarmer(Construct):
    """One schedule rule -> one dispatcher Lambda -> async invoke each target."""

    def __init__(
        self,
        scope: Construct,
        id: str,
        functions: list[_lambda.IFunction],
        interval_minutes: int = 5,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)
        if not functions:
            return

        arn_tokens = [fn.function_arn for fn in functions]
        dispatcher = _lambda.Function(
            self,
            "Dispatcher",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=_lambda.Code.from_inline(_WARMER_CODE),
            timeout=Duration.seconds(30),
            memory_size=128,
            environment={
                "TARGET_FUNCTION_ARNS": Fn.join(",", arn_tokens),
            },
        )

        for fn in functions:
            fn.grant_invoke(dispatcher)

        rule = events.Rule(
            self,
            "ScheduleRule",
            schedule=events.Schedule.rate(Duration.minutes(interval_minutes)),
            description=(
                f"Warm {len(functions)} Lambda function(s) every {interval_minutes} minutes"
            ),
        )
        rule.add_target(targets.LambdaFunction(dispatcher, retry_attempts=0))
