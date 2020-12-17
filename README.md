
# SMOK

[![PyPI](https://img.shields.io/pypi/pyversions/smok.svg)](https://pypi.python.org/pypi/smok)
[![PyPI version](https://badge.fury.io/py/smok.svg)](https://badge.fury.io/py/smok)
[![PyPI](https://img.shields.io/pypi/implementation/smok.svg)](https://pypi.python.org/pypi/smok)
[![Documentation Status](https://readthedocs.org/projects/smok-client/badge/?version=latest)](http://smok-client.readthedocs.io/en/latest/?badge=latest)
[![Maintainability](https://api.codeclimate.com/v1/badges/657b03d115f6e001633c/maintainability)](https://codeclimate.com/github/smok-serwis/smok-client/maintainability)
[![Test Coverage](https://api.codeclimate.com/v1/badges/657b03d115f6e001633c/test_coverage)](https://codeclimate.com/github/smok-serwis/smok-client/test_coverage)
[![Wheel](https://img.shields.io/pypi/wheel/smok.svg)](https://pypi.org/project/smok/)

`smok` is a definitive library to write programs that behave as SMOK devices.
It is principally a consumer of [the SMOK API](https://api.smok.co/).

## Change log

### v0.3

* added `SMOKDevice._execute_message_order`
* log publisher has now a timeout
* clarified Pathpoint.get_archive

### v0.2

* renamed from smok-client to smok

### v0.0.11

* fixed closing `Event`s
* added pickling `Event` and `Macro`
* `on_read` Future can now return `None`

### v0.0.10

* added `Pathpoint.get_archive`
* definitively removed set metadata
* added custom `SMOKDevice.execute_section`

### v0.0.9

* added `PicklingMetadataDatabase`
* added `SMOKDevice.sync_sections`
* added `SMOKDevice.open_event` and `SMOKDevice.close_event`
    and `SMOKDevice.get_all_open_events`

### v0.0.8

* added support for plain metadata

### v0.0.7

* added logging

### v0.0.6

* renamed `BaseEventDatabase.get_data_to_sync` to
`BaseEventDatabase.get_events_to_sync`

### v0.0.5

* added an option not to start macros and archives
* added __slots__ to BaseDatabases

### v0.0.4

* added setting and reading linkstate and instrumentation metadata for slave devices
* added a true macro database

### v0.0.3

* added pluggable pathpoint value databases
* `Section` is now a `Future`
* **bugfix**: timestamp from restored data would be needlessly bumped up
* added option to create `Events`


