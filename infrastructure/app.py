#!/usr/bin/env python3
import aws_cdk as cdk
from config import env_config
from stacks.tech_blog_data_stack import TechBlogDataStack
from stacks.tech_blog_auth_stack import TechBlogAuthStack
from stacks.tech_blog_lambda_stack import TechBlogLambdaStack
from stacks.tech_blog_api_stack import TechBlogApiStack

app = cdk.App()

# 1. DynamoDB tables only
data_stack = TechBlogDataStack(app, "TechBlogDataStack", config=env_config)

# 2. Cognito User Pool + App Client
auth_stack = TechBlogAuthStack(app, "TechBlogAuthStack", config=env_config)

# 3. Lambdas (layer, authorizer, handlers) – depends on Data
lambda_stack = TechBlogLambdaStack(
    app, "TechBlogLambdaStack",
    config=env_config,
    data_stack=data_stack,
)
lambda_stack.add_dependency(data_stack)

# 4. API Gateway + custom Lambda authorizer – depends on Lambda
api_stack = TechBlogApiStack(
    app, "TechBlogApiStack",
    config=env_config,
    lambda_stack=lambda_stack,
)
api_stack.add_dependency(lambda_stack)

app.synth()