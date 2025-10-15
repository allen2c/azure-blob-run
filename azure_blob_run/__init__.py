import functools
import pathlib

import pydantic
import pydantic_settings
from azure.storage.blob import BlobServiceClient, ContainerClient
from str_or_none import str_or_none

__version__ = pathlib.Path(__file__).parent.joinpath("VERSION").read_text().strip()

# Azure Blob Storage URL Example:
# https://mystorageaccount.blob.core.windows.net/mycontainer/myblob.txt
# Account name must be lowercase only.


class Settings(pydantic_settings.BaseSettings):
    AZURE_BLOB_RUN_CONNECTION_STRING: pydantic.SecretStr = pydantic.Field(
        default=pydantic.SecretStr("")
    )
    AZURE_BLOB_RUN_CONTAINER_NAME: str = pydantic.Field(default="")
    AZURE_BLOB_RUN_CACHE_PATH: str = pydantic.Field(default="./.cache")

    @functools.cached_property
    def blob_service_client(self) -> BlobServiceClient:
        __conn_str = self.AZURE_BLOB_RUN_CONNECTION_STRING.get_secret_value()
        if str_or_none(__conn_str) is None:
            raise ValueError("AZURE_BLOB_RUN_CONNECTION_STRING is not set")

        return BlobServiceClient.from_connection_string(__conn_str)

    @functools.cached_property
    def container_client(self) -> ContainerClient:
        if str_or_none(self.AZURE_BLOB_RUN_CONTAINER_NAME) is None:
            raise ValueError("AZURE_BLOB_RUN_CONTAINER_NAME is not set")

        container_client = self.blob_service_client.get_container_client(
            self.AZURE_BLOB_RUN_CONTAINER_NAME
        )
        if not container_client.exists():
            container_client.create_container()

        return container_client


def run(blob_url: str) -> str:
    pass
