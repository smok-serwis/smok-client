Welcome to SMOK Client's documentation!
=======================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   how-to-start
   slave_devices
   orders
   predicates
   extras
   logging
   exceptions
   baob
   glossary

SMOK devices are devices that consist of a bunch of pathpoints (eg. a single MODBUS register)
that can be queried and written to by SMOK_.

.. _SMOK: https://smok.co

What `smok-client` does for you is:

* Automate pathpoint management
* Client-side archiving and macro execution
* Ability to create events locally and later sync them with server.
* Cache and alter plain metadata

.. note:: set metadata is not supported right now

Generally `smok-client` is fully prepared to work offline.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
