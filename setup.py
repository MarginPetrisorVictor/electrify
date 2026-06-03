from setuptools import setup, find_packages

def read_requirements():
    with open('requirements.txt', 'r') as req:
        return req.read().splitlines()

setup(
    name="electrify",
    version="0.1.0",
    packages=find_packages(),
    install_requires=read_requirements(),
    entry_points={
        'console_scripts': [
            'arise=cli.main:app',
        ],
    },
)