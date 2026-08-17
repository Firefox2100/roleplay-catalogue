from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

from .card_v2 import SillyTavernCardV2BookEntry, SillyTavernCardV2CharacterBook, SillyTavernCardV2Data


class SillyTavernRegexScript(BaseModel):
    model_config = ConfigDict(extra='allow', populate_by_name=True)

    id: str | int = ''
    script_name: str = Field('', alias='scriptName')
    find_regex: str = Field('', alias='findRegex')
    replace_string: str = Field('', alias='replaceString')
    trim_strings: list[str] = Field(default_factory=list, alias='trimStrings')
    placement: list[int] = Field(default_factory=list)
    disabled: bool = False
    markdown_only: bool = Field(False, alias='markdownOnly')
    prompt_only: bool = Field(False, alias='promptOnly')
    run_on_edit: bool = Field(False, alias='runOnEdit')
    substitute_regex: int | bool = Field(0, alias='substituteRegex')
    min_depth: int | None = Field(None, alias='minDepth')
    max_depth: int | None = Field(None, alias='maxDepth')


class SillyTavernScriptButton(BaseModel):
    model_config = ConfigDict(extra='allow')

    enabled: bool = False
    buttons: list[dict[str, Any]] = Field(default_factory=list)


class SillyTavernCharacterScript(BaseModel):
    model_config = ConfigDict(extra='allow')

    type: str = 'script'
    enabled: bool = True
    name: str = ''
    id: str | int = ''
    content: str = ''
    info: str = ''
    button: SillyTavernScriptButton = Field(default_factory=SillyTavernScriptButton)
    data: dict[str, Any] = Field(default_factory=dict)


class SillyTavernHelperExtension(BaseModel):
    model_config = ConfigDict(extra='allow')

    scripts: list[SillyTavernCharacterScript] = Field(default_factory=list)
    variables: dict[str, Any] = Field(default_factory=dict)


class SillyTavernCardV3Extensions(BaseModel):
    model_config = ConfigDict(extra='allow')

    regex_scripts: list[SillyTavernRegexScript] = Field(default_factory=list)
    tavern_helper: SillyTavernHelperExtension | None = None


class SillyTavernCardV3BookEntry(SillyTavernCardV2BookEntry):
    use_regex: bool = Field(
        ...,
        description="Whether to use regex for matching",
    )
    constant: bool = Field(
        ...,
        description="If true, always insert into the prompt",
    )


class SillyTavernCardV3LoreBook(SillyTavernCardV2CharacterBook):
    entries: list[SillyTavernCardV3BookEntry] = Field(
        default_factory=list,
        description="The entries inside the lore book",
    )


class SillyTavernCardV3Asset(BaseModel):
    type: str = Field(
        ...,
        description="The type of the asset",
    )
    uri: str = Field(
        ...,
        description="The URI of the asset",
    )
    name: str = Field(
        ...,
        description="The name of the asset",
    )
    ext: str = Field(
        ...,
        description="The extension of the asset",
    )


class SillyTavernCardV3Data(SillyTavernCardV2Data):
    extensions: SillyTavernCardV3Extensions = Field(
        default_factory=SillyTavernCardV3Extensions,
        description='Application extensions, including scoped regex and character scripts',
    )
    assets: Optional[list[SillyTavernCardV3Asset]] = Field(
        None,
        description="A list of assets used by this card"
    )
    nickname: Optional[str] = Field(
        None,
        description="The nickname of the character",
    )
    creator_notes_multilingual: Optional[dict[str, str]] = Field(
        None,
        description="The creator notes in different languages, the key being ISO 639-1 code, value being the "
                    "creator notes in that language",
    )
    source: Optional[list[str]] = Field(
        None,
        description="The source URL or IDs of this character card",
    )
    group_only_greetings: list[str] = Field(
        default_factory=list,
        description="A list of greetings used only in group chats"
    )
    creation_date: Optional[int] = Field(
        None,
        description="The creation time of this card, in Unix seconds",
    )
    modification_date: Optional[int] = Field(
        None,
        description="The modification time of this card, in Unix seconds",
    )

    character_book: Optional[SillyTavernCardV3LoreBook] = Field(
        None,
        description="A character-specific lore book",
    )


class SillyTavernCardV3(BaseModel):
    spec: Literal["chara_card_v3"]
    spec_version: Literal["3.0"]
    data: SillyTavernCardV3Data = Field(
        ...,
        description="The tavern card data",
    )


class SillyTavernLorebookV3(BaseModel):
    spec: Literal["lorebook_v3"]
    data: SillyTavernCardV3LoreBook = Field(
        ...,
        description="Standalone Character Card V3 lorebook payload",
    )
