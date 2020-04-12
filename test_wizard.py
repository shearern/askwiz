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
