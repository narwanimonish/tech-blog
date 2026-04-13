"""
Lambdas: shared layer + unified users/posts handlers + auth login.
Uses backend/config.json for timeout, memory_size, reserved_concurrency per function.
Requires TechBlogDataStack (table names + IAM grants).
Deploy after Data: cdk deploy TechBlogLambdaStack
"""

from __future__ import annotations

from aws_cdk import Stack, aws_iam as iam

from config.dev import DevConfig
from config.prod import ProdConfig
from constructs import Construct
from lambda_config import get_lambda_settings
from services.dynamodb_table import DynamoDBTable
from services.lambda_function import LambdaFunction
from services.shared_layer import SharedLayer
from stacks.tech_blog_auth_stack import TechBlogAuthStack
from stacks.tech_blog_data_stack import TechBlogDataStack


class TechBlogLambdaStack(Stack):
    """App Lambdas: unified users_api, posts_api, auth_login. IAM and env from Data/Auth stacks."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: DevConfig | ProdConfig,
        data_stack: TechBlogDataStack,
        auth_stack: TechBlogAuthStack,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)
        app_name = config.APP_NAME
        users_table: DynamoDBTable = data_stack.users_table
        posts_table: DynamoDBTable = data_stack.posts_table

        # Shared layer (common + core)
        shared_layer = SharedLayer(
            self,
            "SharedLayer",
            asset_path="../backend/layer_bundle",
        )
        layer = shared_layer.get_layer()

        users_env = {
            "usersStoreTable": users_table.table.table_name,
            "USER_POOL_ID": auth_stack.user_pool.user_pool_id,
            "USER_POOL_REGION": self.region,
        }
        posts_env = {
            "postsTable": posts_table.table.table_name,
            "usersStoreTable": users_table.table.table_name,  # for RBAC role lookup
        }

        u_cfg = get_lambda_settings("users_api")
        p_cfg = get_lambda_settings("posts_api")
        auth_cfg = get_lambda_settings("cognito_login")

        # Users Lambda – single handler for all users routes (GET /users, GET/PUT/DELETE /users/{userId})
        self.users_api = LambdaFunction(
            self,
            "UsersApi",
            function_name=f"{app_name}-users-api",
            entry_path="../backend/webservice/users",
            handler="runtime.users.lambda_handler",
            layers=[layer],
            environment=users_env,
            timeout_seconds=u_cfg["timeout_seconds"],
            memory_size=u_cfg["memory_size"],
            reserved_concurrent_executions=u_cfg["reserved_concurrent_executions"],
        )

        # Posts Lambda – single handler for all posts routes (GET/POST /posts, GET/PUT/DELETE /posts/{postId})
        self.posts_api = LambdaFunction(
            self,
            "PostsApi",
            function_name=f"{app_name}-posts-api",
            entry_path="../backend/webservice/posts",
            handler="runtime.posts.lambda_handler",
            layers=[layer],
            environment=posts_env,
            timeout_seconds=p_cfg["timeout_seconds"],
            memory_size=p_cfg["memory_size"],
            reserved_concurrent_executions=p_cfg["reserved_concurrent_executions"],
        )

        # Auth login (public)
        self.auth_login = LambdaFunction(
            self,
            "AuthLogin",
            function_name=f"{app_name}-auth-login",
            entry_path="../backend/webservice/cognito_login",
            handler="runtime.cognito_login.lambda_handler",
            layers=[layer],
            timeout_seconds=auth_cfg["timeout_seconds"],
            memory_size=auth_cfg["memory_size"],
            reserved_concurrent_executions=auth_cfg["reserved_concurrent_executions"],
            environment={
                "USER_POOL_REGION": self.region,
                "USER_POOL_CLIENT_ID": auth_stack.user_pool_client.user_pool_client_id,
                "usersStoreTable": users_table.table.table_name,
            },
        )

        # IAM: grant Lambdas access to DynamoDB (posts_api needs users read for RBAC role lookup)
        users_table.table.grant_read_write_data(self.users_api.function)
        self.users_api.function.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["cognito-idp:AdminDeleteUser"],
                resources=[auth_stack.user_pool.user_pool_arn],
            )
        )
        posts_table.table.grant_read_write_data(self.posts_api.function)
        users_table.table.grant_read_data(self.posts_api.function)
        users_table.table.grant_read_write_data(self.auth_login.function)
        self.auth_login.function.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["cognito-idp:InitiateAuth", "cognito-idp:GetUser"],
                resources=["*"],
            )
        )
