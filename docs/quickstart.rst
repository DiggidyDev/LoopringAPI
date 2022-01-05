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

.. code-block:: python

    import asyncio

    import loopring
    from loopring.util.enums import Endpoints


    cfg = {
        "account_id": 12345,
        "api_key": "",
        "endpoint": Endpoints.MAINNET
    }

    client = loopring.Client(config=cfg)


    async def main():
        resp = await client.get_next_storage_id(0)
        print(resp)


    if __name__ == "__main__":
        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
        finally:
            # Prevents errors complaining about unclosed client sessions
            asyncio.ensure_future(client.close())