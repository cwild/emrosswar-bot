from client_errors import (CoolDownHandler, InvalidKeyHandler,
    PvPEliminationHandler, VisitTooOftenHandler
)
from http_errors import ServiceUnavailableHandler

handlers = {
    2: client_errors.InvalidKeyHandler,
    7415: PvPEliminationHandler,
    8903: CoolDownHandler
}

HTTP_handlers = {
    503: ServiceUnavailableHandler
}
