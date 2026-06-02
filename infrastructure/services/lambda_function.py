from aws_cdk import (
    Duration,
    aws_ecr_assets as ecr_assets,
    aws_lambda as _lambda,
)

from constructs import Construct


class LambdaFunction(Construct):
    """Lambda packaged as a container image (common + core + handler in one image)."""

    def __init__(
        self,
        scope: Construct,
        id: str,
        function_name: str,
        service_name: str,
        handler: str,
        environment: dict[str, str] | None = None,
        timeout_seconds: int = 30,
        memory_size: int = 128,
        reserved_concurrent_executions: int | None = None,
        install_authorizer_deps: bool = False,
        **kwargs,
    ):
        super().__init__(scope, id)

        # Do not set log_retention here — CDK's LogRetention custom resource often
        # fails stack updates when Lambdas change (log group already exists).
        code = _lambda.DockerImageCode.from_image_asset(
            "../backend",
            file="Dockerfile.lambda",
            build_args={
                "SERVICE": service_name,
                "INSTALL_AUTHORIZER_DEPS": "true" if install_authorizer_deps else "false",
            },
            cmd=[handler],
            platform=ecr_assets.Platform.LINUX_AMD64,
        )

        fn_kwargs: dict = {
            "function_name": function_name,
            "code": code,
            "architecture": _lambda.Architecture.X86_64,
            "timeout": Duration.seconds(timeout_seconds),
            "memory_size": memory_size,
            "environment": environment or {},
        }
        if reserved_concurrent_executions is not None:
            fn_kwargs["reserved_concurrent_executions"] = reserved_concurrent_executions
        fn_kwargs.update(kwargs)

        self.function = _lambda.DockerImageFunction(self, f"{id}Function", **fn_kwargs)

    def get_lambda_function(self) -> _lambda.IFunction:
        return self.function
