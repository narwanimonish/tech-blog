"""
Lambdas: shared layer + unified users/posts handlers + auth login.
Requires TechBlogDataStack (table names + IAM grants).
Deploy after Data: cdk deploy TechBlogLambdaStack
"""
from __future__ import annotations

from aws_cdk import Stack
from aws_cdk import aws_iam as iam
from constructs import Construct
from config.dev import DevConfig
from config.prod import ProdConfig
from constructs.dynamodb_table import DynamoDBTable
from constructs.lambda_function import LambdaFunction
from constructs.shared_layer import SharedLayer

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
            self, "SharedLayer",
            asset_path="../backend/layer_bundle",
        )
        layer = shared_layer.get_layer()

        users_env = {"usersStoreTable": users_table.table.table_name}
        posts_env = {"postsTable": posts_table.table.table_name}

        # Users Lambda – single handler for all users routes (GET /users, GET/PUT/DELETE /users/{userId})
        self.users_api = LambdaFunction(
            self, "UsersApi",
            function_name=f"{app_name}-users-api",
            entry_path="../backend/webservice/users",
            handler="runtime.users.lambda_handler",
            layers=[layer],
            timeout_seconds=30,
            memory_size=256,
            environment=users_env,
        )

        # Posts Lambda – single handler for all posts routes (GET/POST /posts, GET/PUT/DELETE /posts/{postId})
        self.posts_api = LambdaFunction(
            self, "PostsApi",
            function_name=f"{app_name}-posts-api",
            entry_path="../backend/webservice/posts",
            handler="runtime.posts.lambda_handler",
            layers=[layer],
            timeout_seconds=30,
            memory_size=256,
            environment=posts_env,
        )

        # Auth login (public)
        self.auth_login = LambdaFunction(
            self, "AuthLogin",
            function_name=f"{app_name}-auth-login",
            entry_path="../backend/webservice/cognito_login",
            handler="runtime.cognito_login.lambda_handler",
            layers=[layer],
            timeout_seconds=30,
            memory_size=256,
            environment={
                "USER_POOL_REGION": self.region,
                "USER_POOL_CLIENT_ID": auth_stack.user_pool_client.user_pool_client_id,
                "usersStoreTable": users_table.table.table_name,
            },
        )

        # IAM: grant Lambdas access to DynamoDB
        users_table.table.grant_read_write_data(self.users_api.function)
        posts_table.table.grant_read_write_data(self.posts_api.function)
        users_table.table.grant_read_write_data(self.auth_login.function)
        self.auth_login.function.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["cognito-idp:InitiateAuth", "cognito-idp:GetUser"],
                resources=["*"],
            )
        )
