from setuptools import setup, find_packages
from utype import __version__


setup(
    name='uType',
    version=__version__,
    description='Declare & parse data types & schemas',
    author='XuLin Zhou',
    author_email='zxl@utilmeta.com',
    keywords="utype type schema meta-type validation data-model type-transform parser json-schema",
    python_requires='>=3.6',
    license="https://utilmeta.com/terms/license",
    url="https://utype.io",
    project_urls={
        "Project Home": "https://utype.io",
        "Documentation": "https://utype.io/docs",
        "Source Code": "https://github.com/utilmeta/utype",
    },
    packages=find_packages(exclude=["tests.*", "tests"]),
)
