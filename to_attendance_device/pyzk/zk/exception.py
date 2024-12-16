class ZKError(Exception):
    pass


class ZKErrorConnection(ZKError):
    pass


class ZKErrorResponse(ZKError):
    pass


class ZKNetworkError(ZKError):
    pass


class ZKConnectionUnauthorized(ZKError):
    pass
