import math
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..resource import ResourceDataDocument


class SillyTavernPresetPrompt(BaseModel):
    model_config = ConfigDict(extra='allow')
    identifier: str = Field(..., min_length=1)
    name: str = ''
    system_prompt: bool = False
    marker: bool = False
    role: str | None = None
    content: str | None = None


class SillyTavernPresetOrderItem(BaseModel):
    model_config = ConfigDict(extra='allow')
    identifier: str = Field(..., min_length=1)
    enabled: bool = True


class SillyTavernPresetPromptOrder(BaseModel):
    model_config = ConfigDict(extra='allow')
    character_id: int | str = 100000
    order: list[SillyTavernPresetOrderItem] = Field(default_factory=list)


class SillyTavernPresetData(BaseModel):
    """Chat Completion preset JSON with provider-specific fields preserved."""

    model_config = ConfigDict(extra='allow')
    temperature: float | None = None
    frequency_penalty: float | None = None
    presence_penalty: float | None = None
    top_p: float | None = None
    top_k: float | None = None
    top_a: float | None = None
    min_p: float | None = None
    repetition_penalty: float | None = None
    openai_max_context: int | None = Field(None, ge=1)
    openai_max_tokens: int | None = Field(None, ge=1)
    seed: int | None = None
    n: int | None = Field(None, ge=1)
    stream_openai: bool | None = None
    prompts: list[SillyTavernPresetPrompt] = Field(default_factory=list)
    prompt_order: list[SillyTavernPresetPromptOrder] = Field(default_factory=list)

    @field_validator('temperature', 'frequency_penalty', 'presence_penalty', 'top_p',
                     'top_k', 'top_a', 'min_p', 'repetition_penalty')
    @classmethod
    def finite_number(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if not math.isfinite(value):
            raise ValueError("Sampling values must be finite")
        return value

    @model_validator(mode='after')
    def unique_prompt_identifiers(self):
        identifiers = [prompt.identifier for prompt in self.prompts]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError('Preset prompt identifiers must be unique')
        return self


class SillyTavernPresetDataDocument(ResourceDataDocument):
    data: SillyTavernPresetData
