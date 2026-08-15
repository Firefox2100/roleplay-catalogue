from pydantic import BaseModel, ConfigDict


class CommonModel(BaseModel):
    model_config = ConfigDict(
        serialize_by_alias=True,
    )
