from aws_cdk import Duration, aws_apigateway as apigw, aws_lambda as _lambda

from constructs import Construct

_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "'*'",
    "Access-Control-Allow-Headers": "'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token'",
    "Access-Control-Allow-Methods": "'GET,POST,PUT,DELETE,OPTIONS'",
}


def _add_cors_gateway_responses(api: apigw.RestApi) -> None:
    """Add CORS headers to API Gateway error responses (authorizer 401/403/502, etc.)."""
    for response_type in (
        apigw.ResponseType.DEFAULT_4_XX,
        apigw.ResponseType.DEFAULT_5_XX,
        apigw.ResponseType.UNAUTHORIZED,
        apigw.ResponseType.ACCESS_DENIED,
        apigw.ResponseType.AUTHORIZER_FAILURE,
        apigw.ResponseType.AUTHORIZER_CONFIGURATION_ERROR,
        apigw.ResponseType.INTEGRATION_FAILURE,
        apigw.ResponseType.INTEGRATION_TIMEOUT,
    ):
        api.add_gateway_response(
            f"Cors{response_type.response_type}",
            type=response_type,
            response_headers=_CORS_HEADERS,
        )


class RestApiGateway(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        api_name: str,
        allowed_origins: list[str] | None = None,
        deploy_options: apigw.StageOptions | None = None,
        **kwargs,
    ):
        super().__init__(scope, id)

        # If no origins provided, we default to none (strictest)
        origins = allowed_origins or ["*"]

        self.api = apigw.RestApi(
            self,
            f"{id}RestApi",
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
                    "X-Amz-Security-Token",
                ],
                # Keeps the browser from re-checking CORS for 10 minutes
                max_age=Duration.minutes(10),
            ),
            **kwargs,
        )
        _add_cors_gateway_responses(self.api)

    def add_lambda_resource(
        self,
        path: str,
        method: str,
        handler: _lambda.IFunction,
        authorizer: apigw.IAuthorizer | None = None,
    ):
        """Add a route; path can include params e.g. 'posts/{postId}'."""
        resource = self.api.root.resource_for_path(path)
        integration = apigw.LambdaIntegration(handler)
        if authorizer:
            resource.add_method(
                method,
                integration,
                authorizer=authorizer,
                authorization_type=apigw.AuthorizationType.CUSTOM,
            )
        else:
            resource.add_method(method, integration)
        return resource
