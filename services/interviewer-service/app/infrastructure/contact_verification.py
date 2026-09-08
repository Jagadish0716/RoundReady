from typing import Protocol


class ContactVerificationProvider(Protocol):
    async def deliver_mobile_code(self, target: str, code: str) -> str | None: ...

    async def deliver_company_email_token(self, target: str, token: str) -> str | None: ...


class DevelopmentContactVerificationProvider:
    async def deliver_mobile_code(self, target: str, code: str) -> str:
        _ = target
        return code

    async def deliver_company_email_token(self, target: str, token: str) -> str:
        _ = target
        return token
