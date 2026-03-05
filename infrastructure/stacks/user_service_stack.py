from aws_cdk import Stack, aws_apigateway as apigw
from constructs import Construct

from config.dev import DevConfig
from config.prod import ProdConfig
from services.dynamodb_table import DynamoDBTable
from services.lambda_function import LambdaFunction


class UserServiceStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: DevConfig | ProdConfig,
        api_gw: apigw.IRestApi,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        # 1. Database
        users_table_name = f"{config.APP_NAME}_users"
        users_table = DynamoDBTable(
            self, id=users_table_name, table_name=users_table_name, partition_key_name="userId"
        )

        # 2. Define the Methods (The "Micro-Lambda" way)
        methods = ["GET", "POST", "PUT", "DELETE"]

        # 3. Create the /users resource on the SHARED API
        user_resource = api_gw.root.add_resource("user")

        for method in methods:
            function_name = f"{config.APP_NAME}-{method}UserHandler"
            handler = LambdaFunction(
                self,
                id=function_name,
                function_name=function_name,
                entry_path="lambda/users",
                handler=f"{method.lower()}.handler",
                environment={"TABLE_NAME": users_table.table.table_name},
            )

            # Grant specific permissions based on method
            if method == "GET":
                users_table.table.grant_read_data(handler.function)
            else:
                users_table.table.grant_read_write_data(handler.function)

            # Attach to the shared resource
            user_resource.add_method(method, apigw.LambdaIntegration(handler.function))
