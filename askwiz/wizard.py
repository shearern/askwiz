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


class QuestionData:

    def __init__(self, prior_answer = None):
        self.prior_answer = prior_answer
        self.input_answer = None
        self.answer = None
        self.asked = False

    def save_data(self):
        return {
            'type': 'question',
            'answer': self.prior_answer,
        }

    @staticmethod
    def from_save_data(data):
        assert(data['type'] == 'question')
        return QuestionData(prior_answer = data['answer'])


class QuestionContextAnswers:
    '''Wrap access to answers when indexing to answer outside Wizard'''
    def __init__(self, questions):
        self.__questions = questions
    def __getitem__(self, name):
        return self.__questions[name].answer
    def __contains__(self, name):
        return name in self.__questions


class QuestionContext:

    def __init__(self):
        self.__questions = dict()

    def save_data(self):
        return {
            'type': 'context',
            'questions': {name: child.save_data() for (name, child) in self.__questions.items()},
        }

    def __setitem__(self, name, obj):
        assert(obj.__class__ in (QuestionData, QuestionContext))
        if name in self.__questions:
            raise KeyError("Name already exists: " + name)
        self.__questions[name] = obj

    def __getitem__(self, name):
        return self.__questions[name]

    def __contains__(self, name):
        return name in self.__questions

    def merge_saved_data(self, data):
        assert(data['type'] == 'context')
        for name, obj in data['questions'].items():
            if obj['type'] == 'question':
                self.__questions[name] = QuestionData.from_save_data(obj)
            elif obj['type'] == 'context':
                if name not in self.__questions:
                    self.__questions[name] = QuestionContext()
                self.__questions[name].merge_saved_data(obj)
            else:
                raise ValueError("Unknown type code: " + obj['type'])


    @property
    def answer(self):
        '''If accessing answers, then return object to proxy access to .answer'''
        return QuestionContextAnswers(self.__questions)


class AllQuestions(QuestionContext): pass




class Wizard:

    def __init__(self, saveto=None, load_if_exists=False, prompt_if_exists=True):
        self.__path = None
        self.__questions = AllQuestions()
        self.__q_context = list()

        if saveto:
            self.set_path(saveto, load_if_exists, prompt_if_exists)


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
            data = json.load(fh)
            if 'questions' in data:
                self.__questions.merge_saved_data(data['questions'])


    def save(self, path=None):
        if path is None:
            path = self.__path
        if path is None:
            return
        with open(path, 'wt') as fh:
            json.dump({'questions': self.__questions.save_data()},
                      fh, indent=4)


    @property
    def _cur_context(self):
        '''Get the current QuestionContext'''
        context = self.__questions
        for context_name in self.__q_context:
            context = context[context_name]
        return context


    def _make_unique_name(self, name):
        '''Make name unique'''
        try:
            orig = name
            i = 0
            while name in self._cur_context and self._cur_context[name].asked:
                i += 1
                name = orig + '.%d' % (i)
            return name

        except KeyError:
            return name


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
            autonamed = True
        else:
            autonamed = False

        # Get question data
        if name in self._cur_context:
            qdata = self._cur_context[name]
        else:
            qdata = QuestionData()
            self._cur_context[name] = qdata

        if qdata.asked:
            raise KeyError("Question name already used: %s" % (name))

        # Calculate default value
        if qdata.prior_answer is not None:
            default = qdata.prior_answer

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

        # Start presenting question
        valid_answer = None
        while True:

            # Present question
            try:
                input_answ = presenter()

                if input_answ is None or len(input_answ.strip()) == 0:
                    input_answ = None

                if not input_answ:
                    input_answ = default

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
        qdata.prior_answer = input_answ
        if not autonamed:
            qdata.answer = valid_answer
        qdata.asked = True
        self.save()

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
        answers = self.__questions.answer
        return answers[name]


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
        if context_name in self._cur_context:
            raise KeyError("Already have a context or question named " + context_name)
        self._cur_context[context_name] = QuestionContext()
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