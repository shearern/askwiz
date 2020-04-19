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
        with self.assertRaises(KeyError):
            wiz.ask(question="...", name="A", presenter=TestPresenter("response"))


    def test_can_ask_unnamed_question_twice(self):
        try:
            wiz = Wizard()
            wiz.ask(question="...", presenter=TestPresenter("response"))
            wiz.ask(question="...", presenter=TestPresenter("response2"))
        except:
            self.fail()


    def test_q_context(self):
        wiz = Wizard()
        wiz.ask(question='parent question', name="A", presenter=TestPresenter("A"))
        with wiz.context("child1"):
            wiz.ask(question='parent question', name="A", presenter=TestPresenter("B"))
        with wiz.context("child2"):
            wiz.ask(question='parent question', name="A", presenter=TestPresenter("C"))

        self.assertEqual(wiz['A'], 'A')
        self.assertEqual(wiz['child1']['A'], 'B')
        self.assertEqual(wiz['child2']['A'], 'C')


    def test_nested_context(self):
        wiz = Wizard()
        with wiz.context("child1"):
            with wiz.context("child2"):
                wiz.ask(question='parent question', name="A", presenter=TestPresenter("A"))

        self.assertEqual(wiz['child1']['child2']['A'], 'A')
