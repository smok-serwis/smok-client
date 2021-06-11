NGTT
====


Standing for **Next Generation TransporT protocol** it is a better way to poll for orders
and upload data than polling over a HTTP API.

It establishes a TLS session, over which data (logs, pathpoints and orders) fly in the form of
excellent minijson_ JSON binary representation. It it a better way to transmit data and orders
if there's a limit on
the amount of data that can be sent. This way orders arrive precisely when they arrive,
and the device does not have to poll for them over HTTP.

.. _minijson: https://github.com/Dronehub/minijson

:code:`smok-client` can use one of two ways to fetch orders:

* polling via HTTPS API
* persistent TLS connection to the server

Note that choosing NGTT will not mean that HTTP API will be unused. It will be still used for all
things, except for:

* sending logs
* sending pathpoint data
* receiving orders

These three positions are fully supported by NGTT, and if it's chosen then HTTP API will be still
used for other things, such as obtaining device configuration.

.. note:: :code:`smok-client` will create temporary files to host it's public certificate chain.

If a connection is broken, smok-client will try to reestablish it using an exponential backoff algorithm
with starting size of 1 second and maximum time of 60 seconds.

NGTT has also an other important advantage. When querying via HTTP, all orders are acknowledged
as soon as they are presented to the client, which leaves open the possibility of order loss.
The connection may fail and the orders may be lost in transit. In NGTT the client has to manually
acknowledge the execution of every order, and will not load more than
the amount which server will send it. So it will process orders more safely. So orders will be
buffered on the server, which is nice.

Since authentication is done via certificates, only frames fly.

.. autoclass:: ngtt.protocol.NGTTFrame
    :members:

NGTT is disabled by default. If you want to enable it, use a flag in the constructor
of :class:`~smok.client.SMOKDevice`.
