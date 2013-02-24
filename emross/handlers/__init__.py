from client_errors import InvalidKeyHandler, PvPEliminationHandler
from http_errors import ServiceUnavailableHandler

handlers = {
    2: InvalidKeyHandler,
    7415: PvPEliminationHandler
}

HTTP_handlers = {
    503: ServiceUnavailableHandler
}
