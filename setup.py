from setuptools import find_packages
from distutils.core import setup
from smok import __version__


setup(version=__version__,
      packages=find_packages(include=['smok', 'smok.*', 'ngtt', 'ngtt.*']),
      package_data={'smok': ['certs/dev.crt', 'certs/root.crt', 'certs/rapid.crt']},
      install_requires=[line.strip() for line in open('requirements.txt', 'r').readlines() if line.strip()],
      python_requires='!=2.7.*,!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*,!=3.4.*,!=3.5.*',
      zip_safe=True
      )
