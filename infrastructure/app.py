#!/usr/bin/env python3
import os
import subprocess

import aws_cdk as cdk
from config import env_config
from stacks.tech_blog_data_stack import TechBlogDataStack
from stacks.tech_blog_auth_stack import TechBlogAuthStack
from stacks.tech_blog_lambda_stack import TechBlogLambdaStack
from stacks.tech_blog_api_stack import TechBlogApiStack

app = cdk.App()


def _resolve_env():
    """Resolve account/region from env vars, else from default AWS CLI profile."""
    account = os.environ.get("CDK_DEFAULT_ACCOUNT") or os.environ.get("AWS_ACCOUNT_ID")
    region = os.environ.get("CDK_DEFAULT_REGION") or os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
    if account and region:
        return cdk.Environment(account=account, region=region)
    try:
        account = subprocess.check_output(
            ["aws", "sts", "get-caller-identity", "--query", "Account", "--output", "text"],
            text=True,
        ).strip()
        region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
        if not region:
            region = subprocess.check_output(["aws", "configure", "get", "region"], text=True).strip() or "us-east-1"
        return cdk.Environment(account=account, region=region)
    except Exception as e:
        raise RuntimeError(
            "Unable to resolve AWS account/region. Run 'aws configure' or set AWS_ACCOUNT_ID and AWS_REGION."
        ) from e


cdk_env = _resolve_env()

# 1. DynamoDB tables only
data_stack = TechBlogDataStack(app, "TechBlogDataStack", config=env_config, env=cdk_env)

# 2. Cognito User Pool + App Client + Post-confirmation trigger (depends on Data for users table)
auth_stack = TechBlogAuthStack(app, "TechBlogAuthStack", config=env_config, data_stack=data_stack, env=cdk_env)
auth_stack.add_dependency(data_stack)

# 3. Lambdas (layer, authorizer, handlers) – depends on Data
lambda_stack = TechBlogLambdaStack(
    app, "TechBlogLambdaStack",
    config=env_config,
    data_stack=data_stack,
    env=cdk_env,
)
lambda_stack.add_dependency(data_stack)

# 4. API Gateway + custom Lambda authorizer – depends on Lambda
api_stack = TechBlogApiStack(
    app, "TechBlogApiStack",
    config=env_config,
    lambda_stack=lambda_stack,
    env=cdk_env,
)
api_stack.add_dependency(lambda_stack)

app.synth()