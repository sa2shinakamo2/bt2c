from setuptools import setup, find_packages

setup(
    name="bt2c",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "pydantic",
        "pydantic-settings",
        "structlog",
        "redis",
        "psycopg2-binary",
        "sqlalchemy",
        "alembic",
        "cryptography",
        "pycryptodome",
        "mnemonic",
        "hdwallet"
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "bt2c-validator=blockchain.validator:main",
        ],
    }
)
