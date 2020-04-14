from unittest import TestCase


from askwiz import Wizard

class TestPresenter:
    def __init__(self, answer):
        self.answer = answer
    def __call__(self):
        return self.answer


class TestWizard(TestCase):

    def test_ask(self):
        wiz = Wizard()
        self.assertEqual(
            wiz.ask(
                question="A",
                presenter=TestPresenter("value")
            ),
            "value")

    def test_asnwer(self):
        wiz = Wizard()
        wiz.ask(question="...", name="A", presenter=TestPresenter("response"))
        self.assertEqual(wiz['A'], "response")


    def test_error_duplicate_name(self):
        wiz = Wizard()
        wiz.ask(question="...", name="A", presenter=TestPresenter("response"))
        with self.assertRaises(ValueError):
            wiz.ask(question="...", name="A", presenter=TestPresenter("response"))


    def test_can_ask_question_twice(self):
        try:
            wiz = Wizard()
            wiz.ask(question="...", name="A", presenter=TestPresenter("response"))
            wiz.ask(question="...", name="A", presenter=TestPresenter("response"))
        except:
            self.fail()
