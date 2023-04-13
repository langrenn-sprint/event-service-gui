"""Nox sessions."""
import sys

import nox
from nox_poetry import Session, session

package = "event_service_gui"
locations = "event_service_gui", "tests", "noxfile.py"
nox.options.stop_on_first_error = True
nox.options.sessions = (
    "black",
    "lint",
    "mypy",
    "pytype",
    "integration_tests",
    "contract_tests",
)


@session(python=["3.11"])
def clean(session: Session) -> None:
    """Clean the project."""
    session.run(
        "py3clean",
        ".",
        external=True,
    )
    session.run(
        "rm",
        "-rf",
        ".cache",
        external=True,
    )
    session.run(
        "rm",
        "-rf",
        ".pytest_cache",
        external=True,
    )
    session.run(
        "rm",
        "-rf",
        ".pytype",
        external=True,
    )
    session.run(
        "rm",
        "-rf",
        "dist",
        external=True,
    )
    session.run(
        "rm",
        "-rf",
        ".mypy_cache",
        external=True,
    )
    session.run(
        "rm",
        "-f",
        ".coverage",
        external=True,
    )


@session(python=["3.10", "3.11"])
def integration_tests(session: Session) -> None:
    """Run the integration test suite."""
    args = session.posargs or ["--cov"]
    session.install(".")
    session.install(
        "coverage[toml]",
        "pytest",
        "pytest-cov",
        "pytest-mock",
        "pytest-aiohttp",
        "aioresponses",
        "requests",
    )
    session.run(
        "pytest",
        "-m integration",
        "-rF",
        *args,
        env={
            "CONFIG": "test",
            "JWT_SECRET": "secret",
            "ADMIN_USERNAME": "admin",
            "ADMIN_PASSWORD": "password",
        },
    )


@session(python="3.11")
def contract_tests(session: Session) -> None:
    """Run the contract test suite."""
    args = session.posargs
    session.install(".")
    session.install(
        "pytest",
        "pytest-docker",
        "pytest_mock",
        "pytest-asyncio",
        "requests",
    )
    session.run(
        "pytest",
        "-m contract",
        "-rA",
        *args,
        env={
            "CONFIG": "test",
            "ADMIN_USERNAME": "admin",
            "ADMIN_PASSWORD": "password",
            "EVENTS_HOST_SERVER": "localhost",
            "EVENTS_HOST_PORT": "8080",
            "USERS_HOST_SERVER": "localhost",
            "USERS_HOST_PORT": "8081",
            "JWT_EXP_DELTA_SECONDS": "60",
            "DB_USER": "event-service",
            "DB_PASSWORD": "password",
            "LOGGING_LEVEL": "DEBUG",
        },
    )


@session(python=["3.10", "3.11"])
def black(session: Session) -> None:
    """Run black code formatter."""
    args = session.posargs or locations
    session.install("black")
    session.run("black", *args)


@session(python=["3.10", "3.11"])
def lint(session: Session) -> None:
    """Lint using flake8."""
    args = session.posargs or locations
    session.install(
        "flake8",
        "flake8-annotations",
        "flake8-bandit",
        "flake8-black",
        "flake8-bugbear",
        "flake8-docstrings",
        "flake8-import-order",
        "darglint",
        "flake8-assertive",
    )
    session.run("flake8", *args)


@session(python=["3.10", "3.11"])
def safety(session: Session) -> None:
    """Scan dependencies for insecure packages."""
    requirements = session.poetry.export_requirements()
    session.install("safety")
    session.run("safety", "check", "--full-report", f"--file={requirements}")


@session(python=["3.10", "3.11"])
def mypy(session: Session) -> None:
    """Type-check using mypy."""
    args = session.posargs or [
        "--install-types",
        "--non-interactive",
        "event_service_gui",
        "tests",
    ]
    session.install(".")
    session.install("mypy", "pytest")
    session.run("mypy", *args)
    if not session.posargs:
        session.run("mypy", f"--python-executable={sys.executable}", "noxfile.py")


@session(python=["3.10"])
def pytype(session: Session) -> None:
    """Run the static type checker using pytype."""
    args = session.posargs or ["--disable=import-error", *locations]
    session.install("pytype")
    session.run("pytype", *args)


@session(python=["3.10", "3.11"])
def xdoctest(session: Session) -> None:
    """Run examples with xdoctest."""
    args = session.posargs or ["all"]
    session.install(".")
    session.install("xdoctest")
    session.run("python", "-m", "xdoctest", package, *args)


@session(python=["3.10", "3.11"])
def docs(session: Session) -> None:
    """Build the documentation."""
    session.install(".")
    session.install("sphinx", "sphinx_autodoc_typehints")
    session.run("sphinx-build", "docs", "docs/_build")


@session(python=["3.10", "3.11"])
def coverage(session: Session) -> None:
    """Upload coverage data."""
    session.install("coverage[toml]", "codecov")
    session.run("coverage", "xml", "--fail-under=0")
    session.run("codecov", *session.posargs)
