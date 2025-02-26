from setuptools import setup, find_packages

setup(
    name="revolut-edavki",
    version="1.0.0",
    author="OpenHands",
    author_email="openhands@all-hands.dev",
    description="Tax report generator for Slovenian eDavki from Revolut data",
    packages=find_packages(),
    install_requires=[
        "flask>=3.1.0",
        "pandas>=2.2.3",
        "openpyxl>=3.1.5",
        "requests>=2.32.3",
        "python-dotenv>=1.0.1",
        "cryptography>=42.0.2",
        "click>=8.1.3",
    ],
    entry_points={
        "console_scripts": [
            "revolut-edavki=revolut_edavki.cli:main",
        ],
    },
    include_package_data=True,
)
