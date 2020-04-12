import json
import os

from hashlib import md5

from .utils import merge_dicts, add_validator
from .exceptions import AnswerRequired, ValidationFailed

from .presenters import ConsoleQuestionPresenter
from .presenters import ConsoleOptionPresenter

from .validators import AnswerRequiredValidator
from .validators import YesNoAnswerValidator
from .validators import OptionsValidators

class Wizard:

    def __init__(self, saveto=None):
        self.__path = None
        self.__history = dict()
        self.__auto_accept_prior_answers = False
        # Question context to restreict all answers to a specified domain
        self.__q_context = None
        self.__names_already_asked = set()


    @property
    def path(self):
        return self.__path


    def set_path(self, path, load_if_exists=False, prompt_if_exists=True):
        '''
        Set the file that's used to store the answer history

        :param path: Path to save answers to.  (JSON)
        :param load_if_exists: If file already exists, load prior answers
        :param prompt_if_exists: If file already exists, ask to load prior answers
        '''

        self.__path = path

        if os.path.exists(path):
            if load_if_exists:
                self.load_prior_answers(path)
            elif prompt_if_exists:
                if self.ask_yn("Load prior answers from %s?" % (path)):
                    self.load_prior_answers(path)


    def load_prior_answers(self, path):
        '''Load prior answer from history file'''
        with open(path, 'rt') as fh:
            merge_dicts(self.__history, json.load(fh))


    def save(self, path):
        with open(path, 'wt') as fh:
            json.dump(self.__history, fh)


    def ask(self, question, default=None, required=True, name=None, presenter=None, validators=None, q_context=None):
        '''
        Ask a simple question of the user

        :param question: Question to present to the user
        :param default: Default value to return if user doesn't provide an answer
        :param required: If true, user must provide an answer (or use historical value)
        :param name: Name to uniquely identify question in history for recalling prior value
        :param presenter: Callable to present question
        :param validators:
            List of callables to validate answer and clean/convert.
            value = validate(value)
        :param q_context:
            If specified (or self.q_context is set), then name is restricted to that domain
        :return: value after validation and cleaned
        '''

        # Calc name to store question answer under
        if name is None:
            name = question
        if q_context is None:
            q_context = self.__q_context

        # Get prior answer
        try:
            history = self.__history['questions']
            if q_context is not None:
                history = history[q_context]
            prior_answer = history[name]
        except KeyError:
            prior_answer = None

        # Calculate default value
        if prior_answer is not None:
            default = prior_answer

        # Calculate question prompt
        if presenter is None:
            prompt = question
            if default is not None:
                question += ' [%s]' % (str(default))
            if not question.endswith(' '):
                question += ' '
            presenter = ConsoleQuestionPresenter(prompt)

        # Validators
        if validators is None:
            validators = list()
        else:
            validators = list(validators)
        validators.insert(0, AnswerRequiredValidator())

        # Start presenting question
        valid_answer = None
        while True:

            # Present question
            try:
                input_answ = presenter()

                # Check required
                if required and len(input_answ.strip()) == 0:
                    raise AnswerRequired()

                # Validate and clean answer
                value = input_answ
                for validator in validators:
                    value = validator(value)
                valid_answer = value
                break

            except AnswerRequired:
                self.inform_user("Answer required")

            except ValidationFailed as e:
                self.inform_user("Problem with answer: " + str(e))

        # Save answer
        if 'questions' not in self.__history:
            self.__history['questions'] = dict()
        history = self.__history['questions']
        if q_context is not None:
            if q_context not in self.__history['questions']:
                self.__history['questions'][q_context] = dict()
                history = self.__history['questions'][q_context]
        history[name] = input_answ

        if self.path is not None:
            self.save(self.path)

        # Return cleaned value
        return valid_answer


    def ask_yn(self, question, default=None, required=True, name=None, presenter=None, validators=None, q_context=None):
        '''
        Ask a question that needs to be yes or no

        :param question: Question to present to the user
        :param default: Default value to return if user doesn't provide an answer
        :param required: If true, user must provide an answer (or use historical value)
        :param name: Name to uniquely identify question in history for recalling prior value
        :param presenter: Callable to present question
        :param validators:
            List of callables to validate answer and clean/convert.
            value = validate(value)
        :param q_context:
            If specified (or self.q_context is set), then name is restricted to that domain
        :return: value after validation and cleaned
        '''

        if default is not None:
            if default:
                default = 'yes'
            else:
                default = 'no'

        return self.ask(
            question = question,
            default = default,
            required = required,
            name = name,
            presenter = presenter,
            validators = add_validator(validators, YesNoAnswerValidator()),
            q_context = q_context
        )


    def ask_choose(self, question, options, default=None, required=True, name=None, presenter=None,
                   validators=None, q_context=None):
        '''
        Ask user to chose among options

        :param question: Question to request
        :param options:
            Options user can choice from
            Either dictionary of {code: value} where value is presented and code is returned, or
            list of [value, ] where value is returned
        :param default: Default option (0 based index, or full option text)
        :param required: If true, user must provide an answer (or use historical value)
        :param name: Name to uniquely identify question in history for recalling prior value
        :param presenter: Callable to present question (see ConsoleOptionPresenter)
        :param validators: List of validators
        :param q_context:
        :return:
        '''

        presenter = presenter or ConsoleOptionPresenter()
        option_validator = OptionsValidators()

        try:
            options = list(options.items())
        except AttributeError:
            options = [(v, v) for v in options]

        for code, desc in options:
            presenter.add_option(code, desc)
            option_validator.add_option(code, desc)

        return self.ask(
            question = question,
            default = default,
            required = required,
            name = name,
            presenter = presenter,
            validators = add_validator(validators, option_validator),
            q_context = q_context
        )
