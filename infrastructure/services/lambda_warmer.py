"""EventBridge schedule: one rule per Lambda (direct invoke, no dispatcher)."""

from __future__ import annotations

from aws_cdk import Duration, aws_events as events, aws_events_targets as targets
from aws_cdk import aws_lambda as _lambda
from constructs import Construct


class LambdaWarmer(Construct):
    """Separate schedule rule per function (reliable CloudFormation updates)."""

    def __init__(
        self,
        scope: Construct,
        id: str,
        functions: list[_lambda.IFunction],
        interval_minutes: int = 5,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)
        schedule = events.Schedule.rate(Duration.minutes(interval_minutes))

        for index, function in enumerate(functions):
            rule = events.Rule(
                self,
                f"WarmRule{index}",
                schedule=schedule,
                description=(
                    f"Keep Lambda warm every {interval_minutes} minutes "
                    f"({function.function_name})"
                ),
            )
            rule.add_target(targets.LambdaFunction(function))
