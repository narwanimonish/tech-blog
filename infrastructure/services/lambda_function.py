from aws_cdk import (
    Duration,
    aws_lambda as _lambda,
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

        # Do not set log_retention here — CDK's LogRetention custom resource often
        # fails stack updates when Lambdas/layers change (log group already exists).
        fn_kwargs: dict = {
            "function_name": function_name,
            "runtime": _lambda.Runtime.PYTHON_3_12,
            "handler": handler,
            "code": _lambda.Code.from_asset(entry_path),
            "timeout": Duration.seconds(timeout_seconds),
            "memory_size": memory_size,
            "environment": environment or {},
            "layers": layers or [],
        }
        if reserved_concurrent_executions is not None:
            fn_kwargs["reserved_concurrent_executions"] = reserved_concurrent_executions
        fn_kwargs.update(kwargs)

        self.function = _lambda.Function(self, f"{id}Function", **fn_kwargs)

    def get_lambda_function(self) -> _lambda.Function:
        return self.function
