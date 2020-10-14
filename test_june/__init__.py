from glob import glob
from pathlib import Path
import pytest

test_path = Path(__file__).parent
def run_all_tests():
    pytest.main(["-x", f"{test_path}"])

