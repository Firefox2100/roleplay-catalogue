class RoleplayCatalogueException(Exception):
    def __init__(self,
                 message: str,
                 status_code: int = 500,
                 ):
        super().__init__(message)

        self._message = message
        self._status_code = status_code


class UserNotFound(RoleplayCatalogueException):
    def __init__(self,
                 message: str,
                 status_code: int = 404,
                 ):
        super().__init__(message, status_code)


class UserCredentialMismatch(RoleplayCatalogueException):
    def __init__(self,
                 message: str,
                 status_code: int = 401,
                 ):
        super().__init__(message, status_code)
