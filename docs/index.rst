Welcome to SMOK Client's documentation!
=======================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   changelog
   how-to-start
   slave_devices
   orders
   sensors
   metadata
   predicates
   extras
   logging
   exceptions
   baob
   ngtt
   glossary

SMOK devices are devices that consist of a bunch of pathpoints (ie. named variables, eg. a
single MODBUS register) that can be queried and written to by SMOK_.

.. _SMOK: https://smok.co

What `smok-client` does for you is:

* Automate pathpoint management
* Download Binary Any-size OBjects
* Client-side archiving and macro execution
* Ability to create events locally and later sync them with server.
* Cache and alter plain metadata
* Execute orders
* Access the values of particular sensors

.. note:: set metadata is not supported right now

Generally `smok-client` is fully prepared to work offline, but in order for it to work
to the best of it's capability, you might need to implement some :ref:`extras`, although
the solutions bundled with SMOK Client might suffice if you don't need very high performance.

Note that if you want your logs, data and orders to be synced over TLS, you can additionally
install the NGTT_ package.

Doing so will drastically reduce your data usage, as NGTT_ streams orders directly to the device,
skipping the need of the device to poll the API.

.. _NGTT: https://github.com/smok-serwis/ngtt

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
