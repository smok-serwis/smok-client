
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

### v0.8

* patched raising exceptions from the API on staging environment 
* certs will be used in conjunction with HTTPS only in production
* removed debug logging before data sync
* no API call will be dispatched if there's no data to sync

### v0.7

* add support for reparse pathpoints
* add support for getting archive data from sensors
* fixed a bug with downloading BAOBS
* fixed a bug with reading sensors via on_read
* fixed a bug with reporting exceptions
* BAOBs will be marked as downloaded after 3 attempts were made
* fixed different exception that OperationFailedError raised during a read to be logged

### v0.6

* add BAOBs
* Sensor class is now eq-able and hashable
* added option to disable pathpoints and predicates 
* added archiving data extra DB

### v0.5

* added automatic log compression
* superficial print() removed
* added sensor database
* increased the startup delay to begin communication by 5 seconds to 10 seconds
    * this delay is now programmable
* fixed a bug with updating metadata
* removed a debug log upon syncing pathpoints

### v0.4

* fixed a bug where `LogPublisherThread` would throw during shutdown
* API will return a `ResponseError` if something fails
* fixed a bug where log records sent to the server were not formatted correctly
* logging was adjusted
* when formatting the log record fails, it's message will be appended along with it's args
* fixed a critical bug with storing pathpoint values
* fixed a bug with executor not recognizing the default `execute_a_section`
* fixed a bug wherein timestamps were written 1000 times larger than necessary
* pathpoints will be uploaded as soon as there's new data

### v0.3

* added `SMOKDevice._execute_message_order`
* log publisher has now a timeout
* clarified Pathpoint.get_archive
* improving handling error messages from the API

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


