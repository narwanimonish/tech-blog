#!/usr/bin/env python3
import aws_cdk as cdk

from config import env_config
from stacks.api_gateway_stack import ApiGatewayStack
from stacks.user_service_stack import UserServiceStack

app = cdk.App()

api_gw = ApiGatewayStack(app, f"{env_config.APP_NAME}-api-gateway", config=env_config)

UserServiceStack(app, "UserServiceStack", config=env_config, api_gw=api_gw.api)

app.synth()
