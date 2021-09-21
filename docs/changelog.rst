Changelog
=========

v0.20
~~~~~

* changed NGTT port to 2405

v0.19
~~~~~

* added option to clean all synced and closed events

v0.18.4
~~~~~~~

* enabled smok-client to successfully parse 204 as response

v0.18.3
~~~~~~~

* removed unused sync logs and pathpoints from NGTT
* fixed string interpolation syntax for Python 3.6
* code will behave better in HTTP 4xx situations
* changed maximum logging amount behaviour

v0.18.2
~~~~~~~

* fixed a bug with logging bad exceptions
* removed debug logging after syncing a pathpoint
* fixed a bug with writing a sensor

v0.18.1
~~~~~~~

* fixed a bug with initializing predicates
* fixed a bug with deleting predicates
* removed some abstractmethods' from checkpoints
* fixed a bug with opening events

v0.18
~~~~~~~

* removed unnecessary profiling with logs
* restored some debug-level logs
* increased communicator timeout to 60s
* increased logs timeout to 40s and added exponential backoff in case of failure
* log syncer will display the invalid logs if a 4xx is seen from the server
* most calls related to pathpoints and sensors will be available in the no-pathpoint mode
 (you still have to provide a sensor and a pathpoint database for it to work).
* fixed a bug with getting sensors locking up on
    dont_do_pathpoints=True

v0.17
~~~~~

* improved logging for NGTT
* improved behaviour of the logging subsystem on low memory conditions
* improved behaviour of connection resetting
* fixed a bug that wouldn't allow smok to run on Python 3.5
* HTTP API will use minijson everywhere
* logs won't be synced via NGTT anymore - they are dropped too often
* data won't be synced via NGTT anymore - they take too long
* SMOKDevice will raise RuntimeErrors on most calls if called after close
* new considerations for PPDatabase and EventDatabase

v0.16.2
~~~~~~~

* fixed reconnecting
* SMOKLogHandler will prune the log queue if on a low memory condition (severity condition 2)

v0.16.1
~~~~~~~

* removed redundant logging
* logging is mow more bulletproof
* bugfixes:
    * syncing data via NGTT can survive a connection reset
    * failing to sync data will not kill CommunicatorThread anymore

v0.16
~~~~~

* new feature: improved compression of data being sent
    * logs and pathpoint data will be compressed using MiniJSON
    * also used much shorter forms
* new feature: pathpoint and log upload via NGTT
* added NGTT module
* Section does not need to be confirmed by the custom executor
* orders now are str-able
* log entries won't be logged if that would overfill the buffer
* logs will wait for at least 1 second for more entries to become available to sync them

v0.15.1
~~~~~~~

* **bugfix release** added minijson to requirements
* v0.15 was pulled

v0.15
~~~~~

* added support for the NGTT protocol to this package
* fixed the bug with loading certificates

v0.14.7
~~~~~~~

* added alternate syntax to PathpointValue.set_new_value
* bugfix for setting new values to pathpoints

v0.14.6
~~~~~~~

* API endpoint changed to https for testing

v0.14.5
~~~~~~~

* added `get_all_events`
* added support for deleting BAOBs
* fixed a bug wherein metadata would still sync despite allow_sync being set to False
* fixed a bug with non-operational `PicklingMacroDatabase`

v0.14.4
~~~~~~~

* `SMOKDevice.open_event` will accept any dictable metadata
* fixed a bug about creating new events
* delayed_boot
* changed default provide_unknown_pathpoint to return a Pathpoint instead of raising a KeyError
    by default. I simply trust the user to provide a Pathpoint DB implementation sane enough
    to realize his aims.
* fixed a bug where `get_all_keys` returns a key that later is proven not to exist
* added consistency checked for `BaseBAOBDatabase`
* fixed a bug with synchronizing predicates

v0.14.3
~~~~~~~

* Predicate state will be preserved each tick if it changes
* changed the API of the predicate database
* added option to specify a timestamp for event close
* *bugfix* fixed certificate mess when connecting to production
* added the RAPID CA certificate
* *bugfix* updating a BAOB could trigger notification about BAOBs being synced for the first time

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


