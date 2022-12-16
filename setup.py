from setuptools import setup, find_packages
from utype import __version__

with open("README.md", "r", encoding="UTF-8") as fh:
    long_description = fh.read()

setup(
    name="utype",
    version=__version__,
    description="Declare & parse types / dataclasses / functions based on Python type annotations",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="XuLin Zhou",
    author_email="zxl@utilmeta.com",
    keywords="utype type schema meta-type validation data-model type-transform parser json-schema",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Internet',
    ],
    install_requires=[
        'typing-extensions>=4.1.0',
    ],
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
