class AppError(Exception):
    """业务异常，由全局错误处理中间件转换为统一 JSON。"""

    def __init__(self, status_code: int, code: str, message: str, detail: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.detail = detail
