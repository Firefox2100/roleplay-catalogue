from pydantic import Field, model_validator
from typing_extensions import Self

from roleplay_catalogue.models.roleplay_resource.resource import ResourceDataDocument
from .card_v3 import SillyTavernCardV3Data, SillyTavernCardV3LoreBook


class SillyTavernCharacterData(SillyTavernCardV3Data):
    @model_validator(mode='after')
    def disallow_embedded_lorebook(self) -> Self:
        if self.character_book is not None:
            raise ValueError('Character lorebooks must be managed as separate resources')
        return self


class SillyTavernCharacterDataDocument(ResourceDataDocument):
    data: SillyTavernCharacterData = Field(
        ...,
        description='Canonical SillyTavern V3 character data',
    )


class SillyTavernLorebookDataDocument(ResourceDataDocument):
    data: SillyTavernCardV3LoreBook = Field(
        ...,
        description='Canonical SillyTavern V3 lorebook data',
    )
