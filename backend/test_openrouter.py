from app.services.openrouter_service import (
    OpenRouterService
)

service = OpenRouterService()

response = service.call(
    "What is product market fit?"
)

print(response)