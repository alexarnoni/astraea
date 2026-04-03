"""
Test that ml/requirements.txt declares exact pinned versions for all required packages.
Validates: Requirements 1.2
"""
import os

REQUIREMENTS_PATH = os.path.join(os.path.dirname(__file__), "..", "requirements.txt")

EXPECTED_PACKAGES = {
    "scikit-learn": "1.5.2",
    "pandas": "2.2.2",
    "sqlalchemy": "2.0.30",
    "psycopg2-binary": "2.9.9",
    "python-dotenv": "1.0.1",
    "joblib": "1.4.2",
    "numpy": "1.26.4",
}


def parse_requirements(path: str) -> dict[str, str]:
    packages = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "==" in line:
                name, version = line.split("==", 1)
                packages[name.strip()] = version.strip()
    return packages


def test_requirements_txt_versions():
    assert os.path.exists(REQUIREMENTS_PATH), "ml/requirements.txt not found"
    packages = parse_requirements(REQUIREMENTS_PATH)
    for pkg, expected_version in EXPECTED_PACKAGES.items():
        assert pkg in packages, f"Package '{pkg}' not found in ml/requirements.txt"
        assert packages[pkg] == expected_version, (
            f"Package '{pkg}' has version '{packages[pkg]}', expected '{expected_version}'"
        )
