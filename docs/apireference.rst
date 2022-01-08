:orphan:

.. _issue: https://github.com/DiggidyDev/LoopringAPI/issues
.. _Official API: https://docs.loopring.io/en
.. _Examples: quickstart.html
.. _apireference:


API Reference
=============

Here is the page with all the useful stuff you need to know for interacting
with Loopring's API.

.. warning:: This API wrapper is still work in progress, and doesn't
   currently support everything documented in the `Official API`_ docs.

   If you run into something broken, please submit an `issue`_
   so I can be notified of it and fix it ASAP :^)

.. seealso:: Some `Examples`_ to get started!


Client
------
.. automodule:: loopring.client
   :members:
   :undoc-members: handle_errors


Order
-----
.. autoclass:: loopring.order.Order
   :members:

PartialOrder
~~~~~~~~~~~~
.. autoclass:: loopring.order.PartialOrder
   :members:

Validity
~~~~~~~~
.. autoclass:: loopring.order.Validity
   :members:

Volume
~~~~~~
.. autoclass:: loopring.order.Volume
   :members:


Token
-----
.. autoclass:: loopring.token.Token
   :members:
   :undoc-members: