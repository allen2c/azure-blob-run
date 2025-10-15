import functools
import json
import logging
import pathlib
import re
import subprocess
import typing

import pydantic
import pydantic_settings
import yarl
from azure.storage.blob import BlobServiceClient, ContainerClient
from rich.pretty import pretty_repr
from str_or_none import str_or_none

__version__ = pathlib.Path(__file__).parent.joinpath("VERSION").read_text().strip()


logger = logging.getLogger(__name__)


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


def run_executable(
    exec_filepath: pathlib.Path | str,
    *arguments: pydantic.BaseModel | typing.Dict | typing.Text,
    default: typing.Text = "",
) -> typing.Text:
    run_arguments = [exec_filepath]
    for argument in arguments:
        if isinstance(argument, pydantic.BaseModel):
            run_arguments.extend(argument.model_dump_json())
        elif isinstance(argument, typing.Text):
            run_arguments.extend(argument)
        elif isinstance(argument, typing.Dict):
            run_arguments.extend(json.dumps(argument))
        else:
            raise ValueError(f"Invalid arguments type: {type(argument)}")
    try:
        result = subprocess.run([exec_filepath], capture_output=True, text=True)

        if str_or_none(result.stderr):
            logger.error(f"Error: {result.stderr}")

        if result.returncode != 0:
            logger.error(
                "Execution returns non-zero code, "
                + f"return default: {pretty_repr(default, max_string=32)}"
            )
            return default

        return result.stdout

    except Exception as e:
        logger.error(f"Exception in run_executable_sync: {e!r}")
        return default


def run(
    blob_url: str,
    *arguments: pydantic.BaseModel | typing.Dict | typing.Text,
    default: typing.Text = "",
    settings: Settings | None = None,
) -> str:
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

    target_file_path = pathlib.Path(settings.AZURE_BLOB_RUN_CACHE_PATH).joinpath(
        blob_name.strip("/")
    )
    target_file_path.mkdir(parents=True, exist_ok=True)

    if not target_file_path.is_file():
        logger.debug(f"Downloading blob '{blob_name}' to '{target_file_path}'")
        blob_client = settings.container_client.get_blob_client(blob_name)
        with open(target_file_path, "wb") as download_file:
            download_stream = blob_client.download_blob()
            download_stream.readinto(download_file)
            logger.info(f"Downloaded blob '{blob_name}' to '{target_file_path}'")
    else:
        logger.debug(f"Blob '{blob_name}' already exists in '{target_file_path}'")

    return run_executable(target_file_path, *arguments, default=default)
