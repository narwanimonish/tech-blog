"""
DynamoDB tables for tech-blog. No dependencies.
Deploy first: cdk deploy TechBlogDataStack

Posts GSI migration: set CDK_POSTS_GSI=disabled to omit the GSI (one CFN delete per deploy),
then CDK_POSTS_GSI=enabled to add PostsListByCreationTime (one CFN create). See scripts/cdk-deploy-ordered.sh.
"""

import os

from aws_cdk import CfnOutput, Stack

from config.dev import DevConfig
from config.prod import ProdConfig
from constructs import Construct
from services.dynamodb_table import DynamoDBTable, GlobalSecondaryIndexSpec


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
        env = config.ENV
        posts_gsi_enabled = os.environ.get("CDK_POSTS_GSI", "enabled").strip().lower() == "enabled"
        users_gsi_enabled = os.environ.get("CDK_USERS_GSI", "enabled").strip().lower() == "enabled"

        # Include ENV in table names to avoid conflict with existing tables (e.g. from old stack)
        users_gsi: list[GlobalSecondaryIndexSpec] | None = None
        if users_gsi_enabled:
            users_gsi = [
                GlobalSecondaryIndexSpec(
                    "UsersListByCreationTime",
                    "listPk",
                    sort_key_name="creation_time",
                ),
            ]

        self.users_table = DynamoDBTable(
            self,
            "UsersTable",
            table_name=f"{app_name}-{env}-users",
            partition_key_name="userId",
            global_secondary_indexes=users_gsi,
        )
        posts_gsi: list[GlobalSecondaryIndexSpec] | None = None
        if posts_gsi_enabled:
            posts_gsi = [
                GlobalSecondaryIndexSpec(
                    "PostsListByCreationTime",
                    "listPk",
                    sort_key_name="creation_time",
                ),
            ]

        self.posts_table = DynamoDBTable(
            self,
            "PostsTable",
            table_name=f"{app_name}-{env}-posts",
            partition_key_name="postId",
            global_secondary_indexes=posts_gsi,
        )

        CfnOutput(
            self,
            "UsersTableName",
            value=self.users_table.table.table_name,
            export_name=f"{app_name}-{env}-users-table-name",
        )
        CfnOutput(
            self,
            "PostsTableName",
            value=self.posts_table.table.table_name,
            export_name=f"{app_name}-{env}-posts-table-name",
        )
