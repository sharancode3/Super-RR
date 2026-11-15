from pathlib import Path
from shutil import copyfile

import pytest


@pytest.fixture
def isolated_hardened_inputs(tmp_path):
    """Run pipeline tests against scratch copies of their published inputs."""
    def copy_inputs(*filenames):
        for filename in filenames:
            copyfile(Path("artifacts_hardened") / filename, tmp_path / filename)
        return tmp_path

    return copy_inputs
