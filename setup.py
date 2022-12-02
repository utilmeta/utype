from setuptools import setup, find_packages
from utype import __version__

with open("README.md", "r", encoding="UTF-8") as fh:
    long_description = fh.read()

setup(
    name="utype",
    version=__version__,
    description="Declare & parse data types & schemas",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="XuLin Zhou",
    author_email="zxl@utilmeta.com",
    keywords="utype type schema meta-type validation data-model type-transform parser json-schema",
    python_requires=">=3.7",
    license="Apache 2.0",
    url="https://utype.io",
    project_urls={
        "Project Home": "https://utype.io",
        "Documentation": "https://utype.io",
        "Source Code": "https://github.com/utilmeta/utype",
    },
    packages=find_packages(exclude=["tests.*", "tests", "docs.*"]),
)
