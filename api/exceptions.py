class SentinelAPIError(Exception):
    def __init__(self, detail: str, error_code: str, status_code: int = 400):
        self.detail = detail
        self.error_code = error_code
        self.status_code = status_code


class CompanyNotFound(SentinelAPIError):
    def __init__(self, detail: str = "Company not found"):
        super().__init__(detail=detail, error_code="COMPANY_NOT_FOUND", status_code=404)


class CompanyDeleted(SentinelAPIError):
    def __init__(self, detail: str = "Company has been deleted"):
        super().__init__(detail=detail, error_code="COMPANY_DELETED", status_code=403)


class UserNotFound(SentinelAPIError):
    def __init__(self, detail: str = "User not found"):
        super().__init__(detail=detail, error_code="USER_NOT_FOUND", status_code=404)


class Unauthorized(SentinelAPIError):
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(detail=detail, error_code="UNAUTHORIZED", status_code=401)


class SeatLimitReached(SentinelAPIError):
    def __init__(self, detail: str = "Seat limit reached for current plan"):
        super().__init__(detail=detail, error_code="SEAT_LIMIT_REACHED", status_code=403)
