"""
DynamoDB tables for tech-blog. No dependencies.
Deploy first: cdk deploy TechBlogDataStack
"""
from aws_cdk import CfnOutput, Stack
from constructs import Construct
from config.dev import DevConfig
from config.prod import ProdConfig
from constructs.dynamodb_table import DynamoDBTable


class TechBlogDataStack(Stack):
    """DynamoDB tables only (users, posts)."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: DevConfig | ProdConfig,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)
        app_name = config.APP_NAME

        self.users_table = DynamoDBTable(
            self, "UsersTable",
            table_name=f"{app_name}-users",
            partition_key_name="userId",
        )
        self.posts_table = DynamoDBTable(
            self, "PostsTable",
            table_name=f"{app_name}-posts",
            partition_key_name="postId",
        )

        CfnOutput(self, "UsersTableName", value=self.users_table.table.table_name, export_name=f"{app_name}-users-table-name")
        CfnOutput(self, "PostsTableName", value=self.posts_table.table.table_name, export_name=f"{app_name}-posts-table-name")
