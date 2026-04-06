"""
Full tech-blog stack: Cognito, DynamoDB (users + posts), shared layer,
all Lambdas, API Gateway with Cognito authorizer.
Run `python build.py` from backend/ before deploy.
"""

from aws_cdk import CfnOutput, Stack, aws_apigateway as apigw

from config.dev import DevConfig
from config.prod import ProdConfig
from constructs import Construct
from services.cognito_auth import CognitoAuth
from services.dynamodb_table import DynamoDBTable
from services.lambda_function import LambdaFunction
from services.rest_api_gateway import RestApiGateway
from services.shared_layer import SharedLayer


class TechBlogStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: DevConfig | ProdConfig,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        app_name = config.APP_NAME

        # 1. Cognito – user authentication
        cognito_auth = CognitoAuth(
            self,
            "CognitoAuth",
            app_name=app_name,
        )
        user_pool = cognito_auth.get_user_pool()

        # 2. DynamoDB tables
        users_table = DynamoDBTable(
            self,
            "UsersTable",
            table_name=f"{app_name}-users",
            partition_key_name="userId",
        )
        posts_table = DynamoDBTable(
            self,
            "PostsTable",
            table_name=f"{app_name}-posts",
            partition_key_name="postId",
        )

        # 3. Shared Lambda layer (common + core)
        shared_layer = SharedLayer(
            self,
            "SharedLayer",
            asset_path="../backend/layer_bundle",
        )
        layer = shared_layer.get_layer()

        # 4. Users Lambdas
        users_get = LambdaFunction(
            self,
            "UsersGet",
            function_name=f"{app_name}-users-get",
            entry_path="../backend/webservice/users_get",
            handler="runtime.users_get.lambda_handler",
            layers=[layer],
            environment={"usersStoreTable": users_table.table.table_name},
        )
        users_list = LambdaFunction(
            self,
            "UsersList",
            function_name=f"{app_name}-users-list",
            entry_path="../backend/webservice/users_list",
            handler="runtime.users_list.lambda_handler",
            layers=[layer],
            environment={"usersStoreTable": users_table.table.table_name},
        )
        users_put = LambdaFunction(
            self,
            "UsersPut",
            function_name=f"{app_name}-users-put",
            entry_path="../backend/webservice/users_put",
            handler="runtime.users_put.lambda_handler",
            layers=[layer],
            environment={"usersStoreTable": users_table.table.table_name},
        )
        users_delete = LambdaFunction(
            self,
            "UsersDelete",
            function_name=f"{app_name}-users-delete",
            entry_path="../backend/webservice/users_delete",
            handler="runtime.users_delete.lambda_handler",
            layers=[layer],
            environment={"usersStoreTable": users_table.table.table_name},
        )

        # 5. Posts Lambdas
        posts_get = LambdaFunction(
            self,
            "PostsGet",
            function_name=f"{app_name}-posts-get",
            entry_path="../backend/webservice/posts_get",
            handler="runtime.posts_get.lambda_handler",
            layers=[layer],
            environment={"postsTable": posts_table.table.table_name},
        )
        posts_list = LambdaFunction(
            self,
            "PostsList",
            function_name=f"{app_name}-posts-list",
            entry_path="../backend/webservice/posts_list",
            handler="runtime.posts_list.lambda_handler",
            layers=[layer],
            environment={"postsTable": posts_table.table.table_name},
        )
        posts_post = LambdaFunction(
            self,
            "PostsPost",
            function_name=f"{app_name}-posts-post",
            entry_path="../backend/webservice/posts_post",
            handler="runtime.posts_post.lambda_handler",
            layers=[layer],
            environment={"postsTable": posts_table.table.table_name},
        )
        posts_put = LambdaFunction(
            self,
            "PostsPut",
            function_name=f"{app_name}-posts-put",
            entry_path="../backend/webservice/posts_put",
            handler="runtime.posts_put.lambda_handler",
            layers=[layer],
            environment={"postsTable": posts_table.table.table_name},
        )
        posts_delete = LambdaFunction(
            self,
            "PostsDelete",
            function_name=f"{app_name}-posts-delete",
            entry_path="../backend/webservice/posts_delete",
            handler="runtime.posts_delete.lambda_handler",
            layers=[layer],
            environment={"postsTable": posts_table.table.table_name},
        )

        # Grant table access
        users_table.table.grant_read_write_data(users_get.function)
        users_table.table.grant_read_write_data(users_list.function)
        users_table.table.grant_read_write_data(users_put.function)
        users_table.table.grant_read_write_data(users_delete.function)
        posts_table.table.grant_read_write_data(posts_get.function)
        posts_table.table.grant_read_write_data(posts_list.function)
        posts_table.table.grant_read_write_data(posts_post.function)
        posts_table.table.grant_read_write_data(posts_put.function)
        posts_table.table.grant_read_write_data(posts_delete.function)

        # 6. API Gateway + Cognito authorizer
        api = RestApiGateway(
            self,
            "Api",
            api_name=f"{app_name}-api",
            allowed_origins=["*"],  # Restrict in prod to your frontend origin
        )

        authorizer = apigw.CognitoUserPoolsAuthorizer(
            self,
            "CognitoAuthorizer",
            cognito_user_pools=[user_pool],
            authorizer_name=f"{app_name}-cognito-auth",
        )

        # Routes (all protected by Cognito)
        api.add_lambda_resource("users", "GET", users_list.function, authorizer=authorizer)
        api.add_lambda_resource("users/{userId}", "GET", users_get.function, authorizer=authorizer)
        api.add_lambda_resource("users/{userId}", "PUT", users_put.function, authorizer=authorizer)
        api.add_lambda_resource(
            "users/{userId}", "DELETE", users_delete.function, authorizer=authorizer
        )
        api.add_lambda_resource("posts", "GET", posts_list.function, authorizer=authorizer)
        api.add_lambda_resource("posts", "POST", posts_post.function, authorizer=authorizer)
        api.add_lambda_resource("posts/{postId}", "GET", posts_get.function, authorizer=authorizer)
        api.add_lambda_resource("posts/{postId}", "PUT", posts_put.function, authorizer=authorizer)
        api.add_lambda_resource(
            "posts/{postId}", "DELETE", posts_delete.function, authorizer=authorizer
        )

        # Outputs for frontend
        self.api = api.api
        self.user_pool = user_pool
        self.user_pool_client = cognito_auth.user_pool_client

        CfnOutput(self, "ApiUrl", value=api.api.url, description="API Gateway URL")
        CfnOutput(
            self, "UserPoolId", value=user_pool.user_pool_id, description="Cognito User Pool ID"
        )
        CfnOutput(
            self,
            "UserPoolClientId",
            value=cognito_auth.user_pool_client.user_pool_client_id,
            description="Cognito App Client ID",
        )
