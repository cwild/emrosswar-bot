import logging
import re

from lib.ordered_dict import OrderedDict

logger = logging.getLogger(__name__)

try:
    import shlex
    _split = shlex.split
except ImportError:
    _split = lambda x: x.split()


def _parse_args(arg_strs):
    args, kwargs = [], OrderedDict()

    for s in _split(arg_strs):
        if s.count('=') == 1:
            key, value = s.split('=', 1)
            kwargs[key] = value
        else:
            args.append(s)

    return args, kwargs


class MessageParsingError(Exception):
    pass

class SkipMessage(MessageParsingError):
    pass

class MessageParser(object):
    COMMAND_OPERATOR = '!'
    NAME_OPERATOR = '@'
    SELF_OPERATOR = '/'

    @classmethod
    def parse_message(cls, message, targets=[], myself=False):

        if myself:
            # Talking to yourself again huh?
            if message.startswith(cls.SELF_OPERATOR):
                parts = message[len(cls.SELF_OPERATOR):].split(' ', 1)
                method_name, arg_strs = parts[0], parts[1:]
            else:
                raise SkipMessage('Talking to ourself requires the SELF_OPERATOR')

        elif message.startswith(cls.COMMAND_OPERATOR):
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
            arg_strs = arg_strs.pop()
        except (AttributeError, IndexError):
            arg_strs = ''

        args, kwargs = _parse_args(arg_strs)

        return method_name, args, kwargs

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    messages = ['item=ring\ of\ king 123 456', '!spam 1 2 spam=3']

    for message in messages:
        logger.info(_parse_args(message))
