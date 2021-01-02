Welcome to SMOK Client's documentation!
=======================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   how-to-start
   slave_devices
   orders
   sensors
   predicates
   extras
   logging
   exceptions
   baob
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


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
