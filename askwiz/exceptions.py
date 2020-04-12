
class ValidationFailed(Exception): pass

class AnswerRequired(ValidationFailed):
    def __init__(self):
        super().__init__("An answer is required")

class NotAValidOption(ValidationFailed):
    def __init__(self):
        super().__init__("Not an option")
