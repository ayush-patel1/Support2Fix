"""Domain-level errors, mapped to RFC 9457 problem+json responses by the

exception handler registered in app/main.py. Services and repositories
raise these; routes don't need to know HTTP status codes. See
system-design.md §7.1.
"""


class AppError(Exception):
    status_code: int = 400
    code: str = "error"

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class AuthenticationRequiredError(AppError):
    status_code = 401
    code = "authentication_required"


class InvalidCredentialsError(AppError):
    status_code = 401
    code = "invalid_credentials"


class AlreadyExistsError(AppError):
    status_code = 409
    code = "already_exists"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"


class NoActiveOrganizationError(AppError):
    status_code = 409
    code = "no_active_organization"


class InvalidConfigError(AppError):
    status_code = 400
    code = "invalid_config"
