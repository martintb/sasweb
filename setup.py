from setuptools import setup, find_packages

setup(
    name='sasweb',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        # existing requirements...
        'click>=8.0.0',
    ],
    entry_points={
        'console_scripts': ['sasweb=sasweb.__main__:main'],
    },
