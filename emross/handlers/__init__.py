from .client_errors import VisitTooOftenHandler

from emross.handlers import client_errors
from emross.handlers import http_errors

handlers = {
    2: client_errors.InvalidKeyHandler,
    401: client_errors.PlayerRaceSelection,
    708: client_errors.InsufficientResources,
    709: client_errors.InsufficientResources,
    710: client_errors.InsufficientResources,
    711: client_errors.InsufficientResources,
    807: client_errors.InsufficientResources,
    1004: client_errors.InsufficientResources,
    1005: client_errors.InsufficientResources,
    1306: client_errors.InsufficientResources,
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
