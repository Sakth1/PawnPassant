from pathlib import Path
import os


def test_path():
    # Mocking the structure:
    # project_root/
    #   src/
    #     utils/
    #       logging_config.py

    # Since we are in project_root, let's assume we are in src/utils/
    # But we'll just use the actual file path if possible.

    # Let's just use the current directory as a proxy for project_root
    # and simulate being in src/utils

    current_dir = Path.cwd()
    # Simulate being in src/utils/
    simulated_file = current_dir / "src" / "utils" / "logging_config.py"

    print(f"Simulated file: {simulated_file}")

    parent = simulated_file.parent
    print(f"Parent: {parent}")
    parent2 = parent.parent
    print(f"Parent 2: {parent2}")
    parent3 = parent2.parent
    print(f"Parent 3 (Project Root): {parent3}")

    if parent3 == current_dir:
        print("SUCCESS: Parent 3 is Project Root")
    else:
        print(f"FAILURE: Parent 3 is {parent3}, expected {current_dir}")


if __name__ == "__main__":
    test_path()
