"""A failed provider execution retains its authentic event stream for diagnosis."""


class WorkerFailure(RuntimeError):
    def __init__(self, reason, log):
        super().__init__(reason)
        self.log = log


class ModelCompletionError(ValueError):
    """The executor supplied no structurally valid completed JSON answer."""

    def __init__(self, reason, log=b""):
        super().__init__(reason)
        self.log = log
