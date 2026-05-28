"""EventBridge schedule that pings Lambdas periodically to reduce cold starts."""

from __future__ import annotations

from aws_cdk import Duration, aws_events as events, aws_events_targets as targets
from aws_cdk import aws_lambda as _lambda
from constructs import Construct


class LambdaWarmer(Construct):
    """One schedule rule with a target per function (default: every 5 minutes)."""

    def __init__(
        self,
        scope: Construct,
        id: str,
        functions: list[_lambda.IFunction],
        interval_minutes: int = 5,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        rule = events.Rule(
            self,
            "ScheduleRule",
            schedule=events.Schedule.rate(Duration.minutes(interval_minutes)),
            description=(
                f"Ping Lambda functions every {interval_minutes} minutes to keep containers warm"
            ),
        )

        for function in functions:
            rule.add_target(
                targets.LambdaFunction(
                    function,
                    retry_attempts=0,
                )
            )
