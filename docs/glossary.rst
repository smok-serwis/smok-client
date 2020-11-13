Glossary
========

.. glossary::

    Native
      A native pathpoint is a readable endpoint. It tells it's own value, it's value does not
      depend on other pathpoint

    Reparse
      A reparse pathpoint starts with a `r`, then goes it's type, and the remaining is an expression
      with other pathpoints taken in braces `{}`.
      The value of the reparse pathpoint is the result of the expression.
      Writing a reparse pathpoint is a no-op.
      You don't need to care about implementing and providing these, smok-client will demand
      you to provide only :term:`native` pathpoints.

    Statistic
      A base class for predicate. Generally the logic, that given some configuration watches
      over an aspect of the system, and reports events when something goes wrong (or just if
      a condition is reached).

    Predicate
      An instance of a statistic, identified by it's predicate ID.

    Slave device
      A slave device is a device that works under it's :term:`master controller`. Meaning
      it writes pathpoint values with the device ID of it's master controller.

    Master controller
      A single device, that is seen by the user as whole.
      Composed at least of a single :term:`slave`
