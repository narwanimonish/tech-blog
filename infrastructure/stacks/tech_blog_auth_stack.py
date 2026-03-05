"""
Cognito User Pool and App Client for tech-blog. No dependencies.
Deploy: cdk deploy TechBlogAuthStack
"""
from aws_cdk import CfnOutput, Stack
from constructs import Construct
from config.dev import DevConfig
from config.prod import ProdConfig
from constructs.cognito_auth import CognitoAuth


class TechBlogAuthStack(Stack):
    """Cognito User Pool + App Client only."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: DevConfig | ProdConfig,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)
        app_name = config.APP_NAME

        self.cognito_auth = CognitoAuth(self, "CognitoAuth", app_name=app_name)
        self.user_pool = self.cognito_auth.get_user_pool()
        self.user_pool_client = self.cognito_auth.user_pool_client

        CfnOutput(self, "UserPoolId", value=self.user_pool.user_pool_id, export_name=f"{app_name}-user-pool-id")
        CfnOutput(self, "UserPoolClientId", value=self.user_pool_client.user_pool_client_id, export_name=f"{app_name}-user-pool-client-id")
