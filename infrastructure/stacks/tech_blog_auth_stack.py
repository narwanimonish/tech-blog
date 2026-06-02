"""
Cognito User Pool, App Client, and Cognito triggers.
- Post-confirmation Lambda populates users table.
- Post-authentication Lambda logs login audits.
Uses backend/config.json for trigger Lambda timeout, memory, concurrency.
Depends on TechBlogDataStack for the users table.
Deploy: cdk deploy TechBlogAuthStack (after TechBlogDataStack)
"""

from __future__ import annotations

from aws_cdk import CfnOutput, Stack, aws_cognito as cognito

from config.dev import DevConfig
from config.prod import ProdConfig
from constructs import Construct
from lambda_config import get_lambda_settings, lambda_function_name
from services.cognito_auth import CognitoAuth
from services.lambda_function import LambdaFunction
from stacks.tech_blog_data_stack import TechBlogDataStack


class TechBlogAuthStack(Stack):
    """Cognito User Pool + App Client + Post-confirmation and Post-authentication triggers."""

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

        post_conf_cfg = get_lambda_settings("cognito_post_confirmation")
        post_auth_cfg = get_lambda_settings("cognito_post_authentication")

        # Post-confirmation Lambda: write new Cognito user to DynamoDB users table
        cognito_post_confirmation = LambdaFunction(
            self,
            "CognitoPostConfirmation",
            function_name=lambda_function_name(app_name, "cognito-post-confirmation"),
            service_name="cognito_post_confirmation",
            handler="runtime.cognito_post_confirmation.lambda_handler",
            timeout_seconds=post_conf_cfg["timeout_seconds"],
            memory_size=post_conf_cfg["memory_size"],
            reserved_concurrent_executions=post_conf_cfg["reserved_concurrent_executions"],
            environment={"usersStoreTable": users_table.table.table_name},
        )
        users_table.table.grant_read_write_data(cognito_post_confirmation.function)
        self.user_pool.add_trigger(
            cognito.UserPoolOperation.POST_CONFIRMATION,
            cognito_post_confirmation.function,
        )

        # Post-authentication Lambda: audit successful logins.
        # Cognito does not provide JWT/refresh tokens to trigger events.
        cognito_post_authentication = LambdaFunction(
            self,
            "CognitoPostAuthentication",
            function_name=lambda_function_name(app_name, "cognito-post-authentication"),
            service_name="cognito_post_authentication",
            handler="runtime.cognito_post_authentication.lambda_handler",
            timeout_seconds=post_auth_cfg["timeout_seconds"],
            memory_size=post_auth_cfg["memory_size"],
            reserved_concurrent_executions=post_auth_cfg["reserved_concurrent_executions"],
        )
        self.user_pool.add_trigger(
            cognito.UserPoolOperation.POST_AUTHENTICATION,
            cognito_post_authentication.function,
        )

        CfnOutput(
            self,
            "UserPoolId",
            value=self.user_pool.user_pool_id,
            export_name=f"{app_name}-user-pool-id",
        )
        CfnOutput(
            self,
            "UserPoolClientId",
            value=self.user_pool_client.user_pool_client_id,
            export_name=f"{app_name}-user-pool-client-id",
        )
        CfnOutput(
            self,
            "CognitoDomainUrl",
            value=self.cognito_auth.domain.base_url(),
            description="Cognito Hosted UI base URL – use for 'View login page' and OAuth redirects",
        )
