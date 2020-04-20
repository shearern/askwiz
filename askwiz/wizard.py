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


class QuestionContextManager:
    def __init__(self, wizard, context_name):
        self.wizard = wizard
        self.context = context_name
    def __enter__(self):
        self.wizard._open_q_context(self.context)
    def __exit__(self, *args):
        self.wizard._close_q_context(self.context)


class Wizard:

    def __init__(self, saveto=None):
        self.__path = None
        self.__history = dict()
        self.__auto_accept_prior_answers = False
        self.__answsers = dict()
        self.__q_context = list()


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


    def _check_name_unique(self, name):
        '''Check to see if question name (or context name) is already used'''
        # Use prior answers history as we always set that
        try:
            history = self.__history['questions']
            for context in self.__q_context:
                history = history[context]
        except KeyError:
            return
        if name in history:
            raise KeyError("Name %s already used" % (name))


    def _get_prior_answer(self, name):
        '''Find the prior answer for a question'''
        try:
            history = self.__history['questions']
            for context in self.__q_context:
                history = history[context]
            return history[name]
        except KeyError:
            return None


    def _make_unique_name(self, name):
        '''Make name unique'''
        try:
            history = self.__history['questions']
            for context in self.__q_context:
                history = history[context]

            orig = name
            i = 0
            while name in history:
                i += 1
                name = orig + '.%d' % (i)
            return name

        except KeyError:
            return name


    def _save_answer(self, name, autonamed, input_answer, valid_answer):
        '''
        Save the answer the user provided

        :param name: The name of the question
        :param autonamed: Was the question name generated aautomatically
        :param input_answer: The text version of the answer the user typed in
        :param valid_answer: The validated version of the answer
        '''

        # Save input answer for repeat runs
        if 'questions' not in self.__history:
            self.__history['questions'] = dict()
        history = self.__history['questions']
        for context in self.__q_context:
            if context not in history:
                history[context] = dict()
            history = history[context]
        history[name] = input_answer

        # Save validated answer to be accessed in this session
        if not autonamed:
            answers = self.__answsers
            for context in self.__q_context:
                if context not in answers:
                    answers[context] = dict()
                answers = answers[context]
            answers[name] = valid_answer

        if self.path is not None:
            self.save(self.path)


    def ask(self, question, default=None, required=True, name=None, presenter=None, validators=None):
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
        :return: value after validation and cleaned
        '''

        # Calc name to store question answer under
        if name is None:
            name = self._make_unique_name('__auto__.'+question)
            autoname = True
            prior_answer = None
        else:
            self._check_name_unique(name)
            autoname = False
            prior_answer = self._get_prior_answer(name)

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
        # if required:
        #     validators.insert(0, AnswerRequiredValidator())

        # Start presenting question
        valid_answer = None
        while True:

            # Present question
            try:
                input_answ = presenter()

                if input_answ is None or len(input_answ.strip()) == 0:
                    input_answ = None

                # Check required
                if not input_answ:
                    if required:
                        raise AnswerRequired()
                    else:
                        input_answ = default

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
        self._save_answer(name, autoname, input_answ, valid_answer)

        # Return cleaned value
        return valid_answer


    def inform_user(self, info):
        print(info)


    def ask_yn(self, question, default=None, required=True, name=None, presenter=None, validators=None):
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
        :return: value after validation and cleaned
        '''

        if default is not None:
            if default:
                default = 'yes'
            else:
                default = 'no'
            required = False

        return self.ask(
            question = question,
            default = default,
            required = required,
            name = name,
            presenter = presenter,
            validators = add_validator(validators, YesNoAnswerValidator()),
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


    def __getitem__(self, name):
        '''Access saved question answers'''
        return self.__answsers[name]


    def context(self, context_name):
        '''
        Define a context that the next queastions fit under

        This is to support the need to sometimes ask the same question multiple
        times for different objects.  For example, you may ask the name of 5 different
        people.  This has two effects:

         1) Question names are stored within the context and don't conflict with
            the non-context questions or other contexts.
         2) Answers are also stored within the context and accessed by:
            wiz['context']['question_name']

        :param context_name: The name to identify the context (can't reuse)
        '''
        return QuestionContextManager(self, context_name)


    def _open_q_context(self, context_name):
        '''
        Open a new context

        :param context_name: Name of context being opened
        '''
        self._check_name_unique(context_name)
        self.__q_context.append(context_name)


    def _close_q_context(self, context_name=None):
        '''
        Close the context opened by add_q_context()

        :param context_name: If specified, check that named context is actualy open
        '''
        if context_name is not None:
            if len(self.__q_context) == 0 or self.__q_context[-1] != context_name:
                raise ValueError("Context %s is the current context" % (context_name))
        self.__q_context.pop()