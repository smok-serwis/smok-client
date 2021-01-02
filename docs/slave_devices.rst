Slave devices
=============

One device has at least one :term:`slave device`. Slave devices are devices
that are attached to their master (:term:`master controller`), and write to pathpoints
on behalf of their master controller, however, they are their own entities.

For example, the **RAPID** platform uses slave devices as means to configure network.
Consider such a device

.. code-block:: yaml

    device_id: rapid
        slave1: rapideth0
        configuration: static ip 192.168.224.200/24 192.168.224.1
        slave2: rapiduart
        configuration: modbus 9600 8n1

Obtaining further info
----------------------

To get the list of slave devices, use :meth:`smok.client.SMOKDevice.get_device_info`.
It will return you such a class:

.. autoclass:: smok.basics.DeviceInfo
    :members:

Which attribute :attr:`~smok.basics.DeviceInfo.slaves` will contain a list of such classes:

.. autoclass:: smok.basics.SlaveDeviceInfo
    :members:

Interfacing with slave devices
-------------------------------


You can get your interface to slave devices via :meth:`smok.client.SMOKDevice.get_slaves`.
This will return you a list of this class:

.. autoclass:: smok.client.SlaveDevice
    :members:

