:orphan:


.. _quickstart:


Quickstart
==========

Assuming you've set up your Layer 2 wallet and account, you'll
be able to access your API details by visiting the `security tab
<https://loopring.io/#/layer2/security>`_ in your account.

.. note::
    See `here <https://medium.loopring.io/guide-how-to-use-loopring-l2-a267d005255b>`_
    for more information on how to set up and use your L2 wallet.

.. image:: https://i.imgur.com/DY4muk8.png

Click `Export Account`, verify the signature on your device, and you'll
then be able to copy your account details.

Hello world!
------------

Once you've copied your account details, paste them into a file like so (feel free to \
remove the ``level`` key):

``account.json``
~~~~~~~~~~~~~~~~

.. code-block:: json

    {
    "account_id": 12345,
    "address": "0x...",
    "api_key": "abc...",
    "nonce": 1,
    "private_key": "0x...",
    "publicX": "0x...",
    "publicY": "0x..."
    }


``hello_world.py``
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import asyncio
    import json
    from datetime import timedelta

    import loopring
    from loopring.util import Endpoints


    with open("account.json", "r") as fp:
        cfg = json.load(fp)

    cfg["endpoint"] = Endpoints.MAINNET

    client = loopring.Client(handle_errors=True, config=cfg)

    async def main():
        
        # Get orders made in the past 8 days
        rt = await client.get_relayer_time()
        start = rt - timedelta(8)

        orders = await client.get_multiple_orders(start=start)
        print(orders)

        client.stop()  # Exit the program


    if __name__ == "__main__":
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(main())
            loop.run_forever()
        except KeyboardInterrupt:
            print("Exiting...")
        finally:
            # Prevents errors complaining about unclosed client sessions
            asyncio.ensure_future(client.close())
    

Order submissions
-----------------

``buy_example.py``
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import asyncio
    import json

    import loopring
    from loopring import Token
    from loopring.util import Endpoints, fetch


    with open("account.json", "r") as fp:
        cfg = json.load(fp)

    cfg["endpoint"] = Endpoints.MAINNET

    client = loopring.Client(handle_errors=True, config=cfg)


    async def main():
        """Submit a buy order for LRC @ 0.01 ETH/LRC"""
        
        symbols = ["LRC", "ETH"]

        # Load the cached `TokenConfig` for each symbol above
        configs = [fetch(client.tokens, symbol=s) for s in symbols]

        # Update the cached storage IDs for local handling
        await asyncio.gather(*[client.get_next_storage_id(token=tc) for tc in configs])

        lrc_cfg, eth_cfg = configs

        # Define the token quantities
        LRC = Token.from_quantity(100, lrc_cfg)
        ETH = Token.from_quantity(1, eth_cfg)

        # Request to submit the order
        submitted = await client.submit_order("buy", token=LRC, using=ETH, max_fee_bips=50)

        # See the order's status
        print(repr(submitted))

        client.stop()


    if __name__ == "__main__":
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(main())
            loop.run_forever()
        except KeyboardInterrupt:
            print("Exiting...")
        finally:
            # Prevents errors complaining about unclosed client sessions
            asyncio.ensure_future(client.close())