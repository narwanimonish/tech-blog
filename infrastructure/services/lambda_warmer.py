"""EventBridge warm schedules using L1 constructs and short Lambda permission IDs."""

from __future__ import annotations

from aws_cdk import aws_events as events, aws_lambda as _lambda, Stack
from constructs import Construct


class LambdaWarmer(Construct):
    """One EventBridge rule per function; permission statement IDs stay under AWS limits."""

    def __init__(
        self,
        scope: Construct,
        id: str,
        functions: list[_lambda.IFunction],
        interval_minutes: int = 5,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)
        stack_name = Stack.of(scope).stack_name

        for index, function in enumerate(functions):
            rule = events.CfnRule(
                scope,
                f"WarmRule{index}",
                name=f"{stack_name}-warm-{index}"[:64],
                schedule_expression=f"rate({interval_minutes} minutes)",
                state="ENABLED",
                description=f"Keep Lambda warm every {interval_minutes} minutes",
                targets=[
                    events.CfnRule.TargetProperty(
                        arn=function.function_arn,
                        id=f"T{index}",
                    )
                ],
            )

            _lambda.CfnPermission(
                scope,
                f"WarmPerm{index}",
                action="lambda:InvokeFunction",
                function_name=function.function_name,
                principal="events.amazonaws.com",
                source_arn=rule.attr_arn,
            )
