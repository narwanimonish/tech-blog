"""
Shared backend error types.
"""


class AppError(Exception):
    """
    Application-level error that carries frontend-facing code and HTTP status.
    """

    def __init__(self, code, message, status_code=400, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
