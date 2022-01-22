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

   NOT READY FOR USE YET!
   Any testing done is to be done at your own discretion.

   If you run into something broken, please submit an `issue`_
   so I can be notified of it and fix it ASAP :^)

.. seealso:: Some `Examples`_ to get started!


Client
------
Please note that some of the client's methods have the possibility of raising some
error codes that in theory shouldn't be raised.  Instead of removing these, I've kept
true to the Official Documentation and made notes of all possible errors from each
endpoint.

In the future these unnecessary errors may be removed from this documentation to
minimise any confusion and irrelevant information.

.. automodule:: loopring.client
   :members:
   :undoc-members: handle_errors





Market
------
.. autoclass:: loopring.market.Market
   :members:






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





Price
-----
.. autoclass:: loopring.token.Price
   :members:






Token
-----
.. autoclass:: loopring.token.Token
   :members:
   :undoc-members:

GasAmount
~~~~~~~~~
.. autoclass:: loopring.token.GasAmount
   :members:

OrderAmount
~~~~~~~~~~~
.. autoclass:: loopring.token.OrderAmount
   :members:

TokenConfig
~~~~~~~~~~~
.. autoclass:: loopring.token.TokenConfig
   :members: