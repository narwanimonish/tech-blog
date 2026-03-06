"""
Cognito User Pool, App Client, and Post-confirmation Lambda (populates users table).
Depends on TechBlogDataStack for the users table.
Deploy: cdk deploy TechBlogAuthStack (after TechBlogDataStack)
"""
from __future__ import annotations

from aws_cdk import CfnOutput, Stack
from aws_cdk import aws_cognito as cognito
from constructs import Construct
from config.dev import DevConfig
from config.prod import ProdConfig
from constructs.cognito_auth import CognitoAuth
from constructs.lambda_function import LambdaFunction

from stacks.tech_blog_data_stack import TechBlogDataStack


class TechBlogAuthStack(Stack):
    """Cognito User Pool + App Client + Post-confirmation trigger to populate users table."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: DevConfig | ProdConfig,
        data_stack: TechBlogDataStack,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)
        app_name = config.APP_NAME
        users_table = data_stack.users_table

        self.cognito_auth = CognitoAuth(self, "CognitoAuth", app_name=app_name)
        self.user_pool = self.cognito_auth.get_user_pool()
        self.user_pool_client = self.cognito_auth.user_pool_client

        # Post-confirmation Lambda: write new Cognito user to DynamoDB users table (no layer needed)
        cognito_post_confirmation = LambdaFunction(
            self, "CognitoPostConfirmation",
            function_name=f"{app_name}-cognito-post-confirmation",
            entry_path="../backend/webservice/cognito_post_confirmation",
            handler="runtime.cognito_post_confirmation.lambda_handler",
            timeout_seconds=10,
            memory_size=128,
            environment={"usersStoreTable": users_table.table.table_name},
        )
        users_table.table.grant_read_write_data(cognito_post_confirmation.function)
        self.user_pool.add_trigger(
            cognito.UserPoolOperation.POST_CONFIRMATION,
            cognito_post_confirmation.function,
        )

        CfnOutput(self, "UserPoolId", value=self.user_pool.user_pool_id, export_name=f"{app_name}-user-pool-id")
        CfnOutput(self, "UserPoolClientId", value=self.user_pool_client.user_pool_client_id, export_name=f"{app_name}-user-pool-client-id")
        CfnOutput(
            self, "CognitoDomainUrl",
            value=self.cognito_auth.domain.base_url(),
            description="Cognito Hosted UI base URL – use for 'View login page' and OAuth redirects",
        )
