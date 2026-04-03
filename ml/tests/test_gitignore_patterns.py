"""
Test that .gitignore contains the required pattern for ML model files.
Validates: Requirements 4.3
"""
import os

GITIGNORE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", ".gitignore")


def read_gitignore_patterns(path: str) -> list[str]:
    patterns = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
    return patterns


def test_gitignore_contains_joblib_pattern():
    assert os.path.exists(GITIGNORE_PATH), ".gitignore not found at project root"
    patterns = read_gitignore_patterns(GITIGNORE_PATH)
    assert "ml/models/*.joblib" in patterns, (
        "Pattern 'ml/models/*.joblib' not found in .gitignore"
    )
