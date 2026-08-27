from uuid import uuid4

from app.domain.providers import ProviderMessage


class DevelopmentEmailProvider:
    channel = "email"

    async def send(self, message: ProviderMessage) -> str:
        _ = message
        return f"dev-email-{uuid4()}"


class DevelopmentWhatsAppProvider:
    channel = "whatsapp"

    async def send(self, message: ProviderMessage) -> str:
        _ = message
        return f"dev-whatsapp-{uuid4()}"
