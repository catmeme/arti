"""Extract package information from the pyproject.toml file."""

import toml


def get_package_info(filepath="../../pyproject.toml"):
    """
    Retrieve package information from the pyproject.toml file.

    This function extracts details such as the
    package name, version, and GitHub repository information from the specified pyproject.toml file.

    Args:
    - filepath (str): The path to the pyproject.toml file. Defaults to "../../pyproject.toml".

    Returns:
    - dict: A dictionary containing the package name, version, GitHub organization, and GitHub repository name.
    """
    data = toml.load(filepath)

    # Extract package name
    version_info = data.get("tool", {}).get("setuptools", {}).get("dynamic", {}).get("version", {})
    attr_path = version_info.get("attr", "")
    package_name = attr_path.split(".")[0] if attr_path else None

    # Extract version from __init__.py
    version = None
    if package_name:
        with open(f"../../src/{package_name}/__init__.py", "r", encoding="utf-8") as file:
            lines = file.readlines()
            for line in lines:
                if line.startswith("__version__"):
                    version = line.split("=")[1].strip().strip('"')
                    break

    # Extract GitHub repository information
    repo_url = data.get("project", {}).get("urls", {}).get("repository", "")
    github_repo = repo_url.rstrip("/").split("/")[-2:] if repo_url else []

    return {
        "package_name": package_name if package_name else "unknown",
        "version": version if version else "unknown",
        "github_org": github_repo[0] if len(github_repo) > 1 else "unknown",
        "github_repo": github_repo[1] if len(github_repo) > 1 else "unknown",
    }
