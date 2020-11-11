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
