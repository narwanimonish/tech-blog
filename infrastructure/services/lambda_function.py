import aws_cdk as cdk
from aws_cdk import (
    Duration,
    aws_lambda as _lambda,
    aws_logs as logs,
)
from aws_cdk.aws_lambda_python_alpha import PythonFunction
from constructs import Construct


class LambdaFunction(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        function_name: str,
        entry_path: str,
        index_file: str,
        handler: str = "index.handler",
        environment: dict[str, str] | None = None,
        timeout_seconds: int = 30,
        memory_size: int = 128,
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

        self.function = PythonFunction(
            self,
            f"{id}Function",
            function_name=function_name,
            runtime=_lambda.Runtime.PYTHON_3_12,  # Standardized runtime
            entry=entry_path,
            index=index_file,
            handler=handler,
            timeout=Duration.seconds(timeout_seconds),
            memory_size=memory_size,
            environment=environment or {},
            log_group=log_group,
            **kwargs,
        )

    def get_lambda_function(self) -> _lambda.Function:
        return self.function
