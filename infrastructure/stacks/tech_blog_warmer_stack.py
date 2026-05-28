"""
Optional EventBridge warm schedules (separate stack so main API deploy is not blocked).
Deploy after Lambda + API: cdk deploy TechBlogWarmerStack
"""

from __future__ import annotations

from aws_cdk import Stack

from config.dev import DevConfig
from config.prod import ProdConfig
from constructs import Construct
from services.lambda_warmer import LambdaWarmer
from stacks.tech_blog_api_stack import TechBlogApiStack
from stacks.tech_blog_lambda_stack import TechBlogLambdaStack


class TechBlogWarmerStack(Stack):
    """Ping Lambdas every 5 minutes to reduce cold starts."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: DevConfig | ProdConfig,
        lambda_stack: TechBlogLambdaStack,
        api_stack: TechBlogApiStack,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        LambdaWarmer(
            self,
            "Warmer",
            functions=[
                lambda_stack.users_api.function,
                lambda_stack.posts_api.function,
                lambda_stack.auth_login.function,
                api_stack.authorizer.function,
            ],
            interval_minutes=5,
        )
