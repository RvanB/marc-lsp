#!/usr/bin/env python3
"""Setup script for MARC LSP Server."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="marc-lsp-server",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Language Server Protocol implementation for MARC MRK files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/marc-lsp",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Text Editors :: Integrated Development Environments (IDE)",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "lsprotocol>=2023.0.0",
        "pygls>=1.0.0",
    ],
    package_data={
        "": ["data/*.json"],
    },
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "marc-lsp-server=marc_lsp_server:main",
        ],
    },
    py_modules=[
        "marc_lsp_server",
        "marc_static_data",
        "mrk_parser",
        "line_parser",
    ],
)