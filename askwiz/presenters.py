

class ConsoleQuestionPresenter:
    def __init__(self, prompt):
        self.prompt = prompt
    def __call__(self):
        return input(self.prompt)


class ConsoleOptionPresenter:
    def __init__(self, prompt):
        self.prompt = prompt
        self.options = list()
    def add_option(self, code, desc):
        self.options.append((code, desc))
    def __call__(self):
        print("Options:")
        choice_digits = len(str(len(self.options)))
        pat = '  [%%%dd] %s' % (choice_digits)
        for i, desc in enumerate([t[1] for t in self.options]):
            print(pat % (i+1, desc))
        return input(self.prompt)

