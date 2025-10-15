# Azure-Blob-Run

[![PyPI version](https://img.shields.io/pypi/v/azure-blob-run.svg)](https://pypi.org/project/azure-blob-run/)
[![Python Version](https://img.shields.io/pypi/pyversions/azure-blob-run.svg)](https://pypi.org/project/azure-blob-run/)
[![License](https://img.shields.io/pypi/l/ac-py-template.svg)](https://opensource.org/licenses/MIT)

Execute scripts stored in Azure Blob Storage with local caching. Perfect for distributing compiled executables (Rust/Go/WASM) across services without environment dependencies.

## Installation

```bash
pip install azure-blob-run
```

## Quick Start

```python
import azure_blob_run

# Execute a script from Azure Blob Storage
result = azure_blob_run.run(
    "https://mystorageaccount.blob.core.windows.net/mycontainer/myscript.sh",
    "arg1",
    "arg2",
    "--flag"
)
print(result)
```

The script is automatically downloaded and cached locally on first run.

## Configuration

Set these environment variables:

```bash
export AZURE_BLOB_RUN_CONNECTION_STRING="DefaultEndpointsProtocol=https;..."
export AZURE_BLOB_RUN_CONTAINER_NAME="mycontainer"
export AZURE_BLOB_RUN_CACHE_PATH="./.cache"  # Optional, defaults to ./.cache
```

## License

MIT License
