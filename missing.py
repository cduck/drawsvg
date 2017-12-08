
class MissingModule:
    def __init__(self, errorMsg):
        self.errorMsg = errorMsg
    def __getattr__(self, name):
        raise RuntimeError(self.errorMsg)

