from azure_blob_run import Settings


def test_run(azure_blob_name: str, azure_blob: None, settings: Settings):
    print(settings.model_dump_json())
