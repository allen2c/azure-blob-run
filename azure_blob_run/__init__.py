import functools
import pathlib
import re

import pydantic
import pydantic_settings
import yarl
from azure.storage.blob import BlobServiceClient, ContainerClient
from str_or_none import str_or_none

__version__ = pathlib.Path(__file__).parent.joinpath("VERSION").read_text().strip()

# Azure Blob Storage URL Example:
# Account name must be lowercase and alphanumeric only.
EXAMPLE_AZURE_BLOB_URL = (
    "https://mystorageaccount.blob.core.windows.net/mycontainer/myblob.txt"
)


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

    @property
    def account_name(self) -> str:
        if str_or_none(self.AZURE_BLOB_RUN_CONNECTION_STRING) is None:
            raise ValueError("AZURE_BLOB_RUN_CONNECTION_STRING is not set")

        return get_account_name(self.blob_service_client.url)


def get_account_name(url: yarl.URL | str) -> str:
    url = yarl.URL(url) if isinstance(url, str) else url

    if url.host is None:
        raise ValueError(f"Invalid blob URL, valid example: {EXAMPLE_AZURE_BLOB_URL}")

    might_account_name = re.match(
        r"^(?P<account_name>[a-z0-9]+)\.blob\.core\.windows\.net$", url.host
    )
    if might_account_name is None:
        raise ValueError(f"Invalid blob URL, valid example: {EXAMPLE_AZURE_BLOB_URL}")

    return might_account_name.group("account_name")


def get_container_and_blob_name(url: yarl.URL | str) -> tuple[str, str]:
    url = yarl.URL(url) if isinstance(url, str) else url
    path_parts = url.path.lstrip("/").split("/", 1)
    if len(path_parts) != 2:
        raise ValueError(f"Invalid blob URL, valid example: {EXAMPLE_AZURE_BLOB_URL}")
    return path_parts[0], path_parts[1]


def run(blob_url: str, *, settings: Settings | None = None) -> str:
    url = yarl.URL(blob_url)
    settings = Settings() if settings is None else settings

    account_name = get_account_name(url)
    container_name, blob_name = get_container_and_blob_name(url)

    if account_name != settings.account_name:
        raise ValueError(
            f"Account name mismatch, got {account_name} "
            + f"but expected settings {settings.account_name}"
        )
    if container_name != settings.AZURE_BLOB_RUN_CONTAINER_NAME:
        raise ValueError(
            f"Container name mismatch, got {container_name} "
            + f"but expected settings {settings.AZURE_BLOB_RUN_CONTAINER_NAME}"
        )

    return (
        settings.container_client.get_blob_client(blob_name)
        .download_blob()
        .readall()
        .decode("utf-8")
    )
