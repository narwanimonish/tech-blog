from aws_cdk import Stack
from config.dev import DevConfig
from config.prod import ProdConfig
from constructs import Construct
from constructs.dynamodb_table import DynamoDBTable
from constructs.lambda_function import LambdaFunction
from constructs.rest_api_gateway import RestApiGateway


class UserServiceStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, config: DevConfig | ProdConfig, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. Create the DynamoDB Table
        # Standardizing on 'userId' as the Partition Key
        # todo create a config file
        table_name = f"{config.APP_NAME}-users"
        user_table = DynamoDBTable(
            self, table_name,
            table_name=table_name,
            partition_key_name="userId"
        )

        # 2. Create the Lambda Function
        # We pass the Table Name as an environment variable so the code knows where to write
        get_user_lambda = LambdaFunction(
            self, "GetUserHandler",
            function_name="get-users",
            entry_path="lambda/users",  # Points to your local code folder
            handler="get_user.handler",
            environment={
                "TABLE_NAME": user_table.table.table_name
            }
        )

        # 3. Grant Permissions
        # This is the 'glue' - allows the Lambda's IAM Role to read from DynamoDB
        user_table.table.grant_read_data(get_user_lambda.function)

        # 4. Create the API Gateway
        # Restricting origins to your frontend domain for security
        user_api = RestApiGateway(
            self, "UserApi",
            api_name="UserService",
            allowed_origins=["https://my-app-frontend.com"]
        )

        # 5. Connect Lambda to API
        # This creates the GET /users endpoint
        user_api.add_lambda_resource(
            path="users",
            method="GET",
            handler=get_user_lambda.function
        )
