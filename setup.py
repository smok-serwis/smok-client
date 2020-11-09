from setuptools import find_packages
from distutils.core import setup
from smokclient import __version__


setup(name='smok-client',
      version=__version__,
      description='The definitive client library for SMOK',
      author='Piotr Maślanka',
      author_email='pmaslanka@smok.co',
      url='https://github.com/smok-serwis/smok-client/',
      packages=find_packages(include=['smokclient', 'smokclient.*']),
      package_data={'smokclient': ['certs/dev.crt', 'certs/root.crt']},
      install_requires=['requests', 'satella>=2.14.6',
                        'pyasn1', 'cryptography', 'pyopenssl'],
      python_requires='!=2.7.*,!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*,!=3.4.*,!=3.5.*',
      zip_safe=False
      )
