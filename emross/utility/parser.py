import logging
import re

logger = logging.getLogger(__name__)

class MessageParsingError(Exception):
    pass

class SkipMessage(MessageParsingError):
    pass

class MessageParser(object):
    COMMAND_OPERATOR = '!'
    NAME_OPERATOR = '@'

    @classmethod
    def parse_message(cls, message, targets=[]):

        if message.startswith(cls.COMMAND_OPERATOR):
            parts = message[len(cls.COMMAND_OPERATOR):].split(' ', 1)
            method_name, arg_strs = parts[0], parts[1:]
        elif message.startswith(cls.NAME_OPERATOR):
            parts = message[len(cls.NAME_OPERATOR):].split(' ', 2)
            target, method_name, arg_strs = parts[0], parts[1], parts[2:]

            for_us = False
            for t in targets:
                if re.match(target, t):
                    logger.debug('Matched target "{0}" with regex "{1}"'.format(t, target))
                    for_us = True
                    break

            if not for_us:
                raise SkipMessage('We are not the intended recipient of this message')
        else:
            raise MessageParsingError('No message parsed from here')

        try:
            arg_strs = arg_strs.pop().split()
        except IndexError:
            pass

        args = []
        kwargs = {}
        for s in arg_strs:
            if s.count('=') == 1:
                key, value = s.split('=', 1)
                kwargs[key] = value
            else:
                args.append(s)

        return method_name, args, kwargs
