#!/usr/bin/env python3
import aws_cdk as cdk
from config import env_config
from stacks.user_service_stack import UserServiceStack

app = cdk.App()

UserServiceStack(app, "UserServiceStack", config=env_config)

app.synth()
