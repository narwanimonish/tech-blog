from aws_cdk import Stack

from config.dev import DevConfig
from config.prod import ProdConfig
from constructs import Construct
from constructs.rest_api_gateway import RestApiGateway


class ApiGatewayStack(Stack):
    def __init__(
        self, scope: Construct, construct_id: str, config: DevConfig | ProdConfig, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Initialize the base API construct
        api_gateway_name = f"{config.APP_NAME}-api-gateway"
        self.base_api = RestApiGateway(
            self, id=api_gateway_name, api_name=api_gateway_name, **kwargs
        )

        # Export the RestApi object so other stacks can use it
        self.api = self.base_api.api
