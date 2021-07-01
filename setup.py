from setuptools import find_packages
from distutils.core import setup
from smok import __version__

setup(version=__version__,
      packages=find_packages(include=['smok', 'smok.*', 'ngtt', 'ngtt.*']),
      install_requires=[line.strip() for line in open('requirements.txt', 'r').readlines() if
                        line.strip()],
      )
