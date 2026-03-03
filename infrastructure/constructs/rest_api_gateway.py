from aws_cdk import (
    Duration,
)
from aws_cdk import (
    aws_apigateway as apigw,
)
from aws_cdk import (
    aws_lambda as _lambda,
)
from constructs import Construct


class RestApiGateway(Construct):
    def __init__(
        self, 
        scope: Construct, 
        id: str, 
        api_name: str,
        allowed_origins: list[str] | None = None,
        deploy_options: apigw.StageOptions | None = None,
        **kwargs
    ):
        super().__init__(scope, id)

        # If no origins provided, we default to none (strictest) 
        origins = allowed_origins or []

        self.api = apigw.RestApi(
            self, f"{id}RestApi",
            rest_api_name=api_name,
            deploy_options=deploy_options or apigw.StageOptions(stage_name="dev"),
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=origins,
                allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                allow_headers=[
                    "Content-Type", 
                    "X-Amz-Date", 
                    "Authorization", 
                    "X-Api-Key", 
                    "X-Amz-Security-Token"
                ],
                # Keeps the browser from re-checking CORS for 10 minutes
                max_age=Duration.minutes(10) 
            ),
            **kwargs
        )

    def add_lambda_resource(self, path: str, method: str, handler: _lambda.IFunction):
        resource = self.api.root.resource_for_path(path)
        resource.add_method(method, apigw.LambdaIntegration(handler))
        return resource