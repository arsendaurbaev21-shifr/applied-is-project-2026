class AppError(Exception):
    def __init__(self, code, status=400, field=None):
        super().__init__(code)
        self.code, self.status, self.field = code, status, field


def require(condition, code='invalid', status=400, field=None):
    if not condition:
        raise AppError(code, status, field)
