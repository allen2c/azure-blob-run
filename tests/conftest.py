import logging
import pathlib
import tempfile
import typing

import logging_bullet_train as lbt
import pytest

if typing.TYPE_CHECKING:
    from azure_blob_run import Settings

logger = logging.getLogger(__name__)

lbt.set_logger(logger)


@pytest.fixture(scope="module")
def temp_dir():
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture(scope="module")
def azure_blob_container_name():
    return "test-container"


@pytest.fixture(scope="module")
def azure_blob_name():
    return "/utils/test.sh"


@pytest.fixture(scope="module")
def settings(azure_blob_container_name: str, temp_dir: str) -> "Settings":
    from azure_blob_run import Settings

    return Settings(
        AZURE_BLOB_RUN_CONTAINER_NAME=azure_blob_container_name,
        AZURE_BLOB_RUN_CACHE_PATH=temp_dir,
    )


@pytest.fixture(scope="module")
def azure_blob(settings: "Settings", azure_blob_name: str):
    blob_client = settings.container_client.get_blob_client(azure_blob_name)
    with open(pathlib.Path(__file__).parent.joinpath("utils/test.sh"), "rb") as data:
        blob_client.upload_blob(data)

    yield

    # Clean up
    blob_client.delete_blob()
