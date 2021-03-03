Changelog
=========

v0.14.3
~~~~~~~

* _TBA_

v0.14.2
~~~~~~~

* fixed `SMOKDevice.reset_predicates`

v0.14.1
~~~~~~~

* hotfix for a critical bug in 0.14

v0.14
~~~~~

API breaking change:

* registering statistics overhauled

Non-API breaking changes:

* added `SMOKDevice.on_baob_updated`
* added `SMOKDevice.allow_sync`
* remove an useless `* 1.1` in `CommunicatorThread`
* added `on_failed_sync` and `on_successful_sync`
* certificates given with CRLF line ends will be processed successfully
* fixed a bug in `DataSyncDict`
* added `SMOKDevice.reset_predicates`
* added predicate databasing
* added name mangling to `PicklingDatabases`
* fixed pickle to use highest protocol in `PicklingDatabases`
* Pathpoint will try to read it's previous current value upon startup
* refactored `Pathpoint.get`

v0.13
~~~~~

* `OrderExecutorThread` will now wait `startup_delay` seconds as well
* added `Predicate.on_group_changed`
* statistic name in `BaseStatistic` is no longer mandatory to override

v0.12
~~~~~

* changed the parameter name in `SMOKClient.execute_sysctl` to match order fields
* added support for Sensor Writes
* improved exception handling
* added `on_verbose_name_changed` to Predicate
* added an extra parameter to `register_statistic`

v0.11
~~~~~

* better exception messages for invalid certs
* added support for SysctlOrders
* added support for BAOB updates via sysctls
* failure to send a Message will be retried up to 3 times
* fixed a bug with querying for macros using a float
* fixed pickling macros
* fixed a bug with syncing pathpoint data
* fixed a bug with PicklingMacroDatabase

v0.9
~~~~

Following **API breaking changes** were introduced:

* added a termination detector to `sync_sections`

Following non-breaking changes were introduced:

* added caching for plain metadata
* added `Sensor.write`
* failing writes will be treated the same way as failing reads - they will be logged
* added automatic order retry
* smarter waiting (time spent executing read/write/message orders counts into that too)
* added a proofing against appending a pathpoint value with lower timestamp than current
* syncing invalid data (HTTP 4xx instead of 5xx) will mark it as synchronized correctly
* made `Pathpoint.set_new_value`'s usage more ubiquitous
    * since Executor will now use it to write new Pathpoint's values
* added an option to register a callable to be fired each time Pathpoint value changes
* added an option to limit the frequency of Pathpoint's reads
* added an option to read without spawning a Thread and a Future
* added an option to retrieve SMOK's master certificate
* added `NullEventDatabase`

v0.8
~~~~

* patched raising exceptions from the API on staging environment
* certs will be used in conjunction with HTTPS only in production
* removed debug logging before data sync
* no API call will be dispatched if there's no data to sync
* adjusted macro update interval
* removed extra logging from `smok.threads.executor`

v0.7
~~~~

* add support for reparse pathpoints
* add support for getting archive data from sensors
* fixed a bug with downloading BAOBS
* fixed a bug with reading sensors via on_read
* fixed a bug with reporting exceptions
* BAOBs will be marked as downloaded after 3 attempts were made
* fixed different exception that OperationFailedError raised during a read to be logged

v0.6
~~~~

* add BAOBs
* Sensor class is now eq-able and hashable
* added option to disable pathpoints and predicates
* added archiving data extra DB

v0.5
~~~~

* added automatic log compression
* superficial print() removed
* added sensor database
* increased the startup delay to begin communication by 5 seconds to 10 seconds
    * this delay is now programmable
* fixed a bug with updating metadata
* removed a debug log upon syncing pathpoints

v0.4
~~~~

* fixed a bug where `LogPublisherThread` would throw during shutdown
* API will return a `ResponseError` if something fails
* fixed a bug where log records sent to the server were not formatted correctly
* logging was adjusted
* when formatting the log record fails, it's message will be appended along with it's args
* fixed a critical bug with storing pathpoint values
* fixed a bug with executor not recognizing the default `execute_a_section`
* fixed a bug wherein timestamps were written 1000 times larger than necessary
* pathpoints will be uploaded as soon as there's new data

v0.3
~~~~

* added `SMOKDevice._execute_message_order`
* log publisher has now a timeout
* clarified Pathpoint.get_archive
* improving handling error messages from the API

v0.2
~~~~

* renamed from smok-client to smok

v0.0.11
~~~~~~~

* fixed closing `Event`s
* added pickling `Event` and `Macro`
* `on_read` Future can now return `None`

v0.0.10
~~~~~~~

* added `Pathpoint.get_archive`
* definitively removed set metadata
* added custom `SMOKDevice.execute_section`

v0.0.9
~~~~~~

* added `PicklingMetadataDatabase`
* added `SMOKDevice.sync_sections`
* added `SMOKDevice.open_event` and `SMOKDevice.close_event`
    and `SMOKDevice.get_all_open_events`

v0.0.8
~~~~~~

* added support for plain metadata

v0.0.7
~~~~~~

* added logging

v0.0.6
~~~~~~

* renamed `BaseEventDatabase.get_data_to_sync` to
`BaseEventDatabase.get_events_to_sync`

v0.0.5
~~~~~~

* added an option not to start macros and archives
* added __slots__ to BaseDatabases

v0.0.4
~~~~~~

* added setting and reading linkstate and instrumentation metadata for slave devices
* added a true macro database

v0.0.3
~~~~~~

* added pluggable pathpoint value databases
* `Section` is now a `Future`
* **bugfix**: timestamp from restored data would be needlessly bumped up
* added option to create `Events`


