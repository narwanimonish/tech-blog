"""
Lambdas: shared layer, custom authorizer Lambda, and all 9 handler Lambdas.
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
    """All Lambdas: authorizer + users + posts handlers. IAM and env from Data stack."""

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

        # Users Lambdas – env and IAM
        self.users_get = LambdaFunction(
            self, "UsersGet",
            function_name=f"{app_name}-users-get",
            entry_path="../backend/webservice/users_get",
            handler="runtime.users_get.lambda_handler",
            layers=[layer],
            timeout_seconds=30,
            memory_size=256,
            environment={
                "usersStoreTable": users_table.table.table_name,
            },
        )
        self.users_list = LambdaFunction(
            self, "UsersList",
            function_name=f"{app_name}-users-list",
            entry_path="../backend/webservice/users_list",
            handler="runtime.users_list.lambda_handler",
            layers=[layer],
            timeout_seconds=30,
            memory_size=256,
            environment={
                "usersStoreTable": users_table.table.table_name,
            },
        )
        self.users_put = LambdaFunction(
            self, "UsersPut",
            function_name=f"{app_name}-users-put",
            entry_path="../backend/webservice/users_put",
            handler="runtime.users_put.lambda_handler",
            layers=[layer],
            timeout_seconds=30,
            memory_size=256,
            environment={
                "usersStoreTable": users_table.table.table_name,
            },
        )
        self.users_delete = LambdaFunction(
            self, "UsersDelete",
            function_name=f"{app_name}-users-delete",
            entry_path="../backend/webservice/users_delete",
            handler="runtime.users_delete.lambda_handler",
            layers=[layer],
            timeout_seconds=30,
            memory_size=256,
            environment={
                "usersStoreTable": users_table.table.table_name,
            },
        )

        # Posts Lambdas – env and IAM
        self.posts_get = LambdaFunction(
            self, "PostsGet",
            function_name=f"{app_name}-posts-get",
            entry_path="../backend/webservice/posts_get",
            handler="runtime.posts_get.lambda_handler",
            layers=[layer],
            timeout_seconds=30,
            memory_size=256,
            environment={
                "postsTable": posts_table.table.table_name,
            },
        )
        self.posts_list = LambdaFunction(
            self, "PostsList",
            function_name=f"{app_name}-posts-list",
            entry_path="../backend/webservice/posts_list",
            handler="runtime.posts_list.lambda_handler",
            layers=[layer],
            timeout_seconds=30,
            memory_size=256,
            environment={
                "postsTable": posts_table.table.table_name,
            },
        )
        self.posts_post = LambdaFunction(
            self, "PostsPost",
            function_name=f"{app_name}-posts-post",
            entry_path="../backend/webservice/posts_post",
            handler="runtime.posts_post.lambda_handler",
            layers=[layer],
            timeout_seconds=30,
            memory_size=256,
            environment={
                "postsTable": posts_table.table.table_name,
            },
        )
        self.posts_put = LambdaFunction(
            self, "PostsPut",
            function_name=f"{app_name}-posts-put",
            entry_path="../backend/webservice/posts_put",
            handler="runtime.posts_put.lambda_handler",
            layers=[layer],
            timeout_seconds=30,
            memory_size=256,
            environment={
                "postsTable": posts_table.table.table_name,
            },
        )
        self.posts_delete = LambdaFunction(
            self, "PostsDelete",
            function_name=f"{app_name}-posts-delete",
            entry_path="../backend/webservice/posts_delete",
            handler="runtime.posts_delete.lambda_handler",
            layers=[layer],
            timeout_seconds=30,
            memory_size=256,
            environment={
                "postsTable": posts_table.table.table_name,
            },
        )

        # Public auth Lambda: exchanges username/password for Cognito tokens
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
            },
        )

        # IAM: grant Lambdas access to DynamoDB
        users_table.table.grant_read_write_data(self.users_get.function)
        users_table.table.grant_read_write_data(self.users_list.function)
        users_table.table.grant_read_write_data(self.users_put.function)
        users_table.table.grant_read_write_data(self.users_delete.function)
        posts_table.table.grant_read_write_data(self.posts_get.function)
        posts_table.table.grant_read_write_data(self.posts_list.function)
        posts_table.table.grant_read_write_data(self.posts_post.function)
        posts_table.table.grant_read_write_data(self.posts_put.function)
        posts_table.table.grant_read_write_data(self.posts_delete.function)
        self.auth_login.function.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["cognito-idp:InitiateAuth"],
                resources=["*"],
            )
        )
