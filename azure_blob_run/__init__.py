import functools
import json
import logging
import os
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
INVALID_AZURE_BLOB_URL_MSG = (
    f"Invalid blob URL, valid example: {EXAMPLE_AZURE_BLOB_URL}"
)
AZURE_BLOB_URL_RE = re.compile(
    r"https://(?P<account_name>[a-z0-9]+)\.blob\.core\.windows\.net/(?P<container_name>[a-z0-9-]{3,63}+)/(?P<blob_name>.+)"  # noqa: E501
)
AZURE_BLOB_URL_PATTERN = (
    "https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}"
)

AZURITE_ACCOUNT_NAME = "devstoreaccount1"


def get_blob_url(account_name: str, container_name: str, blob_name: str) -> str:
    url = AZURE_BLOB_URL_PATTERN.format(
        account_name=account_name, container_name=container_name, blob_name=blob_name
    )
    valid_url = AZURE_BLOB_URL_RE.match(url)
    if valid_url is None:
        raise ValueError(INVALID_AZURE_BLOB_URL_MSG)
    return url


def get_account_name(url: yarl.URL | str) -> str:
    url = yarl.URL(url) if isinstance(url, str) else url

    if url.host is None:
        raise ValueError(INVALID_AZURE_BLOB_URL_MSG)

    if is_azurite_url(url):
        return AZURITE_ACCOUNT_NAME

    might_account_name = re.match(
        r"^(?P<account_name>[a-z0-9]+)\.blob\.core\.windows\.net$", url.host
    )
    if might_account_name is None:
        raise ValueError(INVALID_AZURE_BLOB_URL_MSG)

    return might_account_name.group("account_name")


def get_blob_parts(url: yarl.URL | str) -> tuple[str, str, str]:
    url = yarl.URL(url) if isinstance(url, str) else url

    if is_azurite_url(url):
        _path_parts = (
            url.path.removeprefix(f"/{AZURITE_ACCOUNT_NAME}").lstrip("/").split("/", 1)
        )
        if len(_path_parts) != 2:
            raise ValueError(INVALID_AZURE_BLOB_URL_MSG)
        return AZURITE_ACCOUNT_NAME, _path_parts[0], _path_parts[1]

    match = AZURE_BLOB_URL_RE.match(str(url))
    if match is None:
        raise ValueError(INVALID_AZURE_BLOB_URL_MSG)

    return (
        match.group("account_name"),
        match.group("container_name"),
        match.group("blob_name"),
    )


def is_azurite_url(url: yarl.URL | str) -> bool:
    url = yarl.URL(url) if isinstance(url, str) else url
    if url.host in ["127.0.0.1", "localhost"] and url.port == 10000:
        return True
    return False


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
        url = yarl.URL(self.blob_service_client.url)
        if is_azurite_url(url):
            return "azurite"
        else:
            return get_account_name(self.blob_service_client.url)

    def get_blob_url(self, blob_name: str) -> str:
        return get_blob_url(
            account_name=self.account_name,
            container_name=self.AZURE_BLOB_RUN_CONTAINER_NAME,
            blob_name=blob_name,
        )


def run_executable(
    exec_filepath: pathlib.Path | str,
    *arguments: pydantic.BaseModel | typing.Dict | typing.Text,
    default: typing.Text = "",
) -> typing.Text:
    run_arguments = [exec_filepath]
    for argument in arguments:
        if isinstance(argument, pydantic.BaseModel):
            run_arguments.append(argument.model_dump_json())
        elif isinstance(argument, typing.Text):
            run_arguments.append(argument)
        elif isinstance(argument, typing.Dict):
            run_arguments.append(json.dumps(argument))
        else:
            raise ValueError(f"Invalid arguments type: {type(argument)}")

    try:
        result = subprocess.run(run_arguments, capture_output=True, text=True)

        if str_or_none(result.stderr):
            logger.error(f"Error: {result.stderr}")

        if result.returncode != 0:
            logger.error(
                "Execution returns non-zero code, "
                + f"return default: {pretty_repr(default, max_string=1000)}"
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

    account_name, container_name, blob_name = get_blob_parts(url)

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
    target_file_path.parent.mkdir(parents=True, exist_ok=True)

    if not target_file_path.is_file():
        logger.debug(f"Downloading blob '{blob_name}' to '{target_file_path}'")
        blob_client = settings.container_client.get_blob_client(blob_name)
        with open(target_file_path, "wb") as download_file:
            download_stream = blob_client.download_blob()
            download_stream.readinto(download_file)
        os.chmod(target_file_path, 0o755)
        logger.info(f"Downloaded blob '{blob_name}' to '{target_file_path}'")
    else:
        logger.debug(f"Blob '{blob_name}' already exists in '{target_file_path}'")

    return run_executable(target_file_path, *arguments, default=default)
