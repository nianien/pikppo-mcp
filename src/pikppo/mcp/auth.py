import secrets


class BearerAuthMiddleware:
    """校验 Authorization: Bearer <token>，token 不匹配返回 401。"""

    def __init__(self, app, token: str):
        self.app = app
        self._expected = f"Bearer {token}"

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            auth = ""
            for name, value in scope["headers"]:
                if name == b"authorization":
                    auth = value.decode("latin-1")
                    break
            if not secrets.compare_digest(auth, self._expected):
                await send({
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [
                        (b"content-type", b"text/plain"),
                        (b"www-authenticate", b"Bearer"),
                    ],
                })
                await send({"type": "http.response.body", "body": b"Unauthorized"})
                return
        await self.app(scope, receive, send)
