from pydantic import BaseModel
from datetime import datetime


class ConnectProviderRequest(BaseModel):
    api_key: str
    provider_name: str = "elevenlabs"


class ProviderAgentResponse(BaseModel):
    id: str
    provider_account_id: str
    provider_name: str
    provider_agent_id: str
    name: str
    is_default: bool


class ProviderConnectionResponse(BaseModel):
    id: str
    provider_name: str


class ProviderConnectionListItem(BaseModel):
    id: str
    provider_name: str
    created_at: datetime
