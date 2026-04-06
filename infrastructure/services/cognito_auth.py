"""
Cognito User Pool and App Client for API authentication.
Frontend uses the App Client to sign in; API Gateway validates the JWT via authorizer.
Hosted UI domain is configured so "View login page" works in the console.
"""

from aws_cdk import RemovalPolicy, aws_cognito as cognito

from constructs import Construct


class CognitoAuth(Construct):
    """Cognito User Pool + App Client for tech-blog auth."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        app_name: str = "tech-blog",
        *,
        domain_prefix: str | None = None,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        self.user_pool = cognito.UserPool(
            self,
            "UserPool",
            user_pool_name=f"{app_name}-user-pool",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(email=True, username=False),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(required=True, mutable=True),
                fullname=cognito.StandardAttribute(required=False, mutable=True),
            ),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=False,
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.user_pool_client = self.user_pool.add_client(
            "AppClient",
            user_pool_client_name=f"{app_name}-web-client",
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True,
            ),
            generate_secret=False,
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(
                    authorization_code_grant=True,
                    implicit_code_grant=False,
                ),
                scopes=[
                    cognito.OAuthScope.EMAIL,
                    cognito.OAuthScope.OPENID,
                    cognito.OAuthScope.PROFILE,
                ],
                callback_urls=["http://localhost:3000/callback", "https://localhost:3000/callback"],
                logout_urls=["http://localhost:3000", "https://localhost:3000"],
            ),
            supported_identity_providers=[
                cognito.UserPoolClientIdentityProvider.COGNITO,
            ],
        )

        # Hosted UI domain – required for "View login page" in the console and OAuth redirects
        prefix = domain_prefix or f"{app_name}-auth"
        self.domain = self.user_pool.add_domain(
            "CognitoDomain",
            cognito_domain=cognito.CognitoDomainOptions(domain_prefix=prefix),
        )

    def get_user_pool(self) -> cognito.IUserPool:
        return self.user_pool
