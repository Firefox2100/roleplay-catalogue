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
    temperature: float = 1
    frequency_penalty: float = 0
    presence_penalty: float = 0
    top_p: float = 1
    top_k: float = 0
    top_a: float = 0
    min_p: float = 0
    repetition_penalty: float = 1
    openai_max_context: int = Field(4095, ge=1)
    openai_max_tokens: int = Field(300, ge=1)
    seed: int = -1
    n: int = Field(1, ge=1)
    stream_openai: bool = True
    prompts: list[SillyTavernPresetPrompt] = Field(default_factory=list)
    prompt_order: list[SillyTavernPresetPromptOrder] = Field(default_factory=list)

    @field_validator('temperature', 'frequency_penalty', 'presence_penalty', 'top_p',
                     'top_k', 'top_a', 'min_p', 'repetition_penalty')
    @classmethod
    def finite_number(cls, value: float) -> float:
        if value != value or value in (float('inf'), float('-inf')):
            raise ValueError('Sampling values must be finite')
        return value

    @model_validator(mode='after')
    def unique_prompt_identifiers(self):
        identifiers = [prompt.identifier for prompt in self.prompts]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError('Preset prompt identifiers must be unique')
        return self


class SillyTavernPresetDataDocument(ResourceDataDocument):
    data: SillyTavernPresetData
