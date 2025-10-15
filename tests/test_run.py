import json

import azure_blob_run


def test_run(
    azure_blob_name: str, temp_azure_blob: None, settings: azure_blob_run.Settings
):
    assert temp_azure_blob is None

    result = azure_blob_run.run(
        settings.get_blob_url(azure_blob_name),
        "run",
        "--test",
        "test",
        "--test2",
        "test2",
        "--verbose",
        "-e",
        "env1=value1",
        "-e",
        "env2=value2",
        settings=settings,
    )
    parsed_result = json.loads(result)
    print(parsed_result)

    # Verify the result
    assert parsed_result["arguments"] == ["run"]
    assert parsed_result["keyword_arguments"]["test"] == "test"
    assert parsed_result["keyword_arguments"]["test2"] == "test2"
    assert parsed_result["keyword_arguments"]["verbose"] is True
    assert parsed_result["keyword_arguments"]["e"] == ["env1=value1", "env2=value2"]
