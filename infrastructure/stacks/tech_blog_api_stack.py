"""
API Gateway + custom Lambda authorizer. All routes protected by authorizer.
Uses backend/config.json for authorizer Lambda timeout, memory, concurrency.
Requires TechBlogLambdaStack (handler Lambdas). Authorizer Lambda lives here to avoid circular deps.
Deploy last: cdk deploy TechBlogApiStack
"""

from __future__ import annotations

from aws_cdk import CfnOutput, Duration, Stack, aws_apigateway as apigw, aws_iam as iam

from config.dev import DevConfig
from config.prod import ProdConfig
from constructs import Construct
from lambda_config import get_lambda_settings
from services.lambda_function import LambdaFunction
from services.rest_api_gateway import RestApiGateway
from stacks.tech_blog_auth_stack import TechBlogAuthStack
from stacks.tech_blog_data_stack import TechBlogDataStack
from stacks.tech_blog_lambda_stack import TechBlogLambdaStack


class TechBlogApiStack(Stack):
    """REST API with custom Lambda authorizer. Depends on TechBlogLambdaStack."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: DevConfig | ProdConfig,
        lambda_stack: TechBlogLambdaStack,
        data_stack: TechBlogDataStack,
        auth_stack: TechBlogAuthStack,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)
        app_name = config.APP_NAME
        auth_cfg = get_lambda_settings("authorizer")
        users_table = data_stack.users_table

        # Authorizer Lambda in this stack (avoids circular dependency with Lambda stack)
        authorizer_lambda = LambdaFunction(
            self,
            "Authorizer",
            function_name=f"{app_name}-api-authorizer",
            entry_path="../backend/webservice/authorizer",
            handler="runtime.authorizer.lambda_handler",
            layers=[lambda_stack.shared_layer],
            timeout_seconds=auth_cfg["timeout_seconds"],
            memory_size=auth_cfg["memory_size"],
            reserved_concurrent_executions=auth_cfg["reserved_concurrent_executions"],
            environment={
                "USER_POOL_REGION": self.region,
                "USER_POOL_ID": auth_stack.user_pool.user_pool_id,
                "USER_POOL_CLIENT_ID": auth_stack.user_pool_client.user_pool_client_id,
                "usersStoreTable": users_table.table.table_name,
            },
        )
        users_table.table.grant_read_data(authorizer_lambda.function)
        self.authorizer = authorizer_lambda

        api = RestApiGateway(
            self,
            "Api",
            api_name=f"{app_name}-api",
            allowed_origins=["*"],
        )

        authorizer = apigw.RequestAuthorizer(
            self,
            "CustomAuthorizer",
            handler=authorizer_lambda.function,
            identity_sources=[apigw.IdentitySource.header("Authorization")],
            authorizer_name=f"{app_name}-custom-auth",
            results_cache_ttl=Duration.minutes(15),
        )

        authorizer_lambda.function.add_permission(
            "AllowApiGwInvoke",
            principal=iam.ServicePrincipal("apigateway.amazonaws.com"),
            source_arn=api.api.arn_for_execute_api("*"),
        )

        # All users routes → single users Lambda
        api.add_lambda_resource(
            "users", "GET", lambda_stack.users_api.function, authorizer=authorizer
        )
        api.add_lambda_resource(
            "users/{userId}", "GET", lambda_stack.users_api.function, authorizer=authorizer
        )
        api.add_lambda_resource(
            "users/{userId}", "PUT", lambda_stack.users_api.function, authorizer=authorizer
        )
        api.add_lambda_resource(
            "users/{userId}", "DELETE", lambda_stack.users_api.function, authorizer=authorizer
        )
        api.add_lambda_resource(
            "users/{userId}/role",
            "PUT",
            lambda_stack.users_api.function,
            authorizer=authorizer,
        )
        # All posts routes → single posts Lambda
        api.add_lambda_resource(
            "posts", "GET", lambda_stack.posts_api.function, authorizer=authorizer
        )
        api.add_lambda_resource(
            "posts", "POST", lambda_stack.posts_api.function, authorizer=authorizer
        )
        api.add_lambda_resource(
            "posts/{postId}", "GET", lambda_stack.posts_api.function, authorizer=authorizer
        )
        api.add_lambda_resource(
            "posts/{postId}", "PUT", lambda_stack.posts_api.function, authorizer=authorizer
        )
        api.add_lambda_resource(
            "posts/{postId}", "DELETE", lambda_stack.posts_api.function, authorizer=authorizer
        )
        api.add_lambda_resource("auth/login", "POST", lambda_stack.auth_login.function)

        self.api_url = api.api.url

        CfnOutput(
            self,
            "ApiUrl",
            value=self.api_url,
            export_name=f"{app_name}-{config.ENV}-api-url",
            description="API Gateway URL",
        )
