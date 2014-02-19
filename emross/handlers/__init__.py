from client_errors import VisitTooOftenHandler

import client_errors
import http_errors

handlers = {
    2: client_errors.InvalidKeyHandler,
    2541: client_errors.DevilArmyGone,
    7415: client_errors.PvPEliminationHandler,
    8903: client_errors.CoolDownHandler,
    20000: client_errors.CaptchaHandler,
    21011: client_errors.CaptchaHandler,
    30016: client_errors.DevilArmyAttackedTooOften
}

HTTP_handlers = {
    503: http_errors.ServiceUnavailableHandler
}
