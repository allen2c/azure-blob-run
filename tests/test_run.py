import azure_blob_run


def test_run(
    azure_blob_name: str, temp_azure_blob: None, settings: azure_blob_run.Settings
):
    assert temp_azure_blob is None

    result = azure_blob_run.run(
        settings.get_blob_url(azure_blob_name), settings=settings
    )
    print(result)
    print(result)
    print(result)
    print(result)
