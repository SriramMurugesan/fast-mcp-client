from setuptools import setup, find_packages

setup(
    name="fast-mcp-client",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "SQLAlchemy>=1.4",
        "psycopg2-binary>=2.9",
    ],
)
