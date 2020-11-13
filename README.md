
# SMOK-Client

[![PyPI](https://img.shields.io/pypi/pyversions/smok-client.svg)](https://pypi.python.org/pypi/smok-client)
[![PyPI version](https://badge.fury.io/py/smok-client.svg)](https://badge.fury.io/py/smok-client)
[![PyPI](https://img.shields.io/pypi/implementation/smok-client.svg)](https://pypi.python.org/pypi/smok-client)
[![Documentation Status](https://readthedocs.org/projects/smok-client/badge/?version=latest)](http://smok-client.readthedocs.io/en/latest/?badge=latest)


`smok-client` is a definitive library to write programs that behave as SMOK devices.
It is principally a consumer of [the SMOK API](https://api.smok.co/).

## Change log

### v0.0.3

* added pluggable pathpoint value databases
* `Section` is now a `Future`
* **bugfix**: timestamp from restored data would be needlessly bumped up
* added option to create `Events`


