import aws_cdk as cdk
from aws_cdk import (
    Duration,
    aws_lambda as _lambda,
    aws_logs as logs,
)

from constructs import Construct


class LambdaFunction(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        function_name: str,
        entry_path: str,
        handler: str = "index.handler",
        environment: dict[str, str] | None = None,
        layers: list[_lambda.ILayerVersion] | None = None,
        timeout_seconds: int = 30,
        memory_size: int = 128,
        reserved_concurrent_executions: int | None = None,
        **kwargs,
    ):
        super().__init__(scope, id)

        log_group = logs.LogGroup(
            self,
            f"{function_name}LogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_WEEK,  # Set your desired retention
            removal_policy=cdk.RemovalPolicy.DESTROY,  # Optional: policy when stack is destroyed
        )

        fn_kwargs = {
            "function_name": function_name,
            "runtime": _lambda.Runtime.PYTHON_3_12,
            "handler": handler,
            "code": _lambda.Code.from_asset(entry_path),
            "timeout": Duration.seconds(timeout_seconds),
            "memory_size": memory_size,
            "environment": environment or {},
            "layers": layers or [],
            "log_group": log_group,
        }
        if reserved_concurrent_executions is not None:
            fn_kwargs["reserved_concurrent_executions"] = reserved_concurrent_executions
        fn_kwargs.update(kwargs)

        self.function = _lambda.Function(self, f"{id}Function", **fn_kwargs)

    def get_lambda_function(self) -> _lambda.Function:
        return self.function
