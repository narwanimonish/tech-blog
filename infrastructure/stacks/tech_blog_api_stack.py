"""
API Gateway + custom Lambda authorizer. All routes protected by authorizer.
Requires TechBlogLambdaStack (handler Lambdas). Authorizer Lambda lives here to avoid circular deps.
Deploy last: cdk deploy TechBlogApiStack
"""
from __future__ import annotations

from aws_cdk import CfnOutput, Duration, Stack
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_iam as iam
from constructs import Construct
from config.dev import DevConfig
from config.prod import ProdConfig
from constructs.lambda_function import LambdaFunction
from constructs.rest_api_gateway import RestApiGateway

from stacks.tech_blog_lambda_stack import TechBlogLambdaStack


class TechBlogApiStack(Stack):
    """REST API with custom Lambda authorizer. Depends on TechBlogLambdaStack."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: DevConfig | ProdConfig,
        lambda_stack: TechBlogLambdaStack,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)
        app_name = config.APP_NAME

        # Authorizer Lambda in this stack (avoids circular dependency with Lambda stack)
        authorizer_lambda = LambdaFunction(
            self, "Authorizer",
            function_name=f"{app_name}-api-authorizer",
            entry_path="../backend/webservice/authorizer",
            handler="runtime.authorizer.lambda_handler",
            timeout_seconds=10,
            memory_size=128,
            environment={"USER_POOL_REGION": self.region},
        )
        authorizer_lambda.function.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["cognito-idp:GetUser"],
                resources=["*"],
            )
        )

        api = RestApiGateway(
            self, "Api",
            api_name=f"{app_name}-api",
            allowed_origins=["*"],
        )

        authorizer = apigw.RequestAuthorizer(
            self, "CustomAuthorizer",
            handler=authorizer_lambda.function,
            identity_sources=[apigw.IdentitySource.header("Authorization")],
            authorizer_name=f"{app_name}-custom-auth",
            results_cache_ttl=Duration.minutes(5),
        )

        authorizer_lambda.function.add_permission(
            "AllowApiGwInvoke",
            principal=iam.ServicePrincipal("apigateway.amazonaws.com"),
            source_arn=api.api.arn_for_execute_api("*"),
        )

        # All users routes → single users Lambda
        api.add_lambda_resource("users", "GET", lambda_stack.users_api.function, authorizer=authorizer)
        api.add_lambda_resource("users/{userId}", "GET", lambda_stack.users_api.function, authorizer=authorizer)
        api.add_lambda_resource("users/{userId}", "PUT", lambda_stack.users_api.function, authorizer=authorizer)
        api.add_lambda_resource("users/{userId}", "DELETE", lambda_stack.users_api.function, authorizer=authorizer)
        # All posts routes → single posts Lambda
        api.add_lambda_resource("posts", "GET", lambda_stack.posts_api.function, authorizer=authorizer)
        api.add_lambda_resource("posts", "POST", lambda_stack.posts_api.function, authorizer=authorizer)
        api.add_lambda_resource("posts/{postId}", "GET", lambda_stack.posts_api.function, authorizer=authorizer)
        api.add_lambda_resource("posts/{postId}", "PUT", lambda_stack.posts_api.function, authorizer=authorizer)
        api.add_lambda_resource("posts/{postId}", "DELETE", lambda_stack.posts_api.function, authorizer=authorizer)
        api.add_lambda_resource("auth/login", "POST", lambda_stack.auth_login.function)

        CfnOutput(self, "ApiUrl", value=api.api.url, description="API Gateway URL")
