import pytest
from glob import glob
import os


examplesGlobPattern = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Examples", "*.py")
examplePaths = glob(examplesGlobPattern)


@pytest.fixture(params=examplePaths)
def examplePath(request):
    return request.param


def test_example(examplePath):
    with open(examplePath) as f:
        src = f.read()
    exec(src, {"__name__": "__main__", "__file__": examplePath})
