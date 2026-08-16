from pydantic import Field

from roleplay_catalogue.models.roleplay_resource.resource import ResourceDataDocument
from .card_v3 import SillyTavernCardV3Data, SillyTavernCardV3LoreBook


class SillyTavernCharacterData(SillyTavernCardV3Data):
    """Canonical V3 character data, including its optional embedded lorebook."""


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
