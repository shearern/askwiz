
from .exceptions import ValidationFailed
from .exceptions import AnswerRequired
from .exceptions import NotAValidOption

class AnswerRequiredValidator:
    def __call__(self, value):
        if value is None or len(str(value).strip()) == 0:
            raise AnswerRequired()
        return value


class YesNoAnswerValidator:
    def __call__(self, value):
        if value is None:
            return None
        elif value.lower() in ('y', 'yes'):
            return True
        elif value.lower() in ('n', 'no'):
            return False
        raise ValidationFailed("Answer must be yes or no")


class OptionsValidators:

    def __init__(self):
        self.options = list()

    def add_option(self, code, desc):
        self.options.append((code, desc))

    def __call__(self, value):

        if value is None:
            return None

        for i, t in enumerate(self.options):
            i += 1
            code, desc = t

            # Check that exact answer was provided
            if value.strip() == desc:
                return code

            # Check if numeric answer was provided
            try:
                if int(value) == i:
                    return code
            except ValueError:
                pass

        # No valid value provided
        raise NotAValidOption()


