# LoopringAPI (Work in progress)

An API Wrapper for Loopring, made with Python.

Please feel free to contribute if you feel so inclined to do so - every little helps!  
Whether this is in the form of a spelling mistake, a redesign of a class, or a new endpoint, anything and everything is useful.

I'll be adding a `CONTRIBUTING.md` file soon, but will aim to finish the bulk of the wrapper first.

# PROGRESS: 29/38 REST API Endpoints done!

- Measuring progress by the [official docs](https://docs.loopring.io/en/)' REST API endpoints.
- I have yet to start on the websocket API!

# [API Reference](https://diggydev.co.uk/loopring/index.html) being updated almost daily!

# TODO:

- [x] Support datetime objects for timestamps.
- [x] Now that I understand where/when to use the EDDSA & EcDSA sigs, it's time to implement them to transfer submissions, withdrawal requests, and order submissions! ! IMPORTANT NOTE ! EcDSA key is the Ethereum L1 wallet private key - available to get from an external wallet such as metamask etc.
- [ ] Finish off REST API endpoints.
- [ ] Initialisation method for client to load in all token and storage info locally for fast access. This would improve QoL for directly passing objects into queries rather than splitting up mismatched attributes (Token obj vs. Token symbol, token volume)
- [ ] Look into turning prices into floats instead of strings.
- [ ] Make a helper for volume conversion.
- [ ] Make a `CONTRIBUTING.md`
- [ ] Add a mapping for request types (query_order_fee())
- [ ] Start and finish the websocket API.
- [ ] Finish documentation for all the endpoints.
- [ ] Figure out why `keySeed` isn't being returned from the account query endpoint.
- [ ] Load in client config/account export from a file instead of pasting it directly into a python script.
- [ ] Add loads of examples!
- [ ] Make some sense out of [how storage IDs work](https://github.com/Loopring/protocols/blob/master/packages/loopring_v3/DESIGN.md#storage).
- [ ] Ratelimits exist, but information is scarce... Work on implementing async ratelimiting anyway!
- [ ] Synchronous version of the wrapper?

## Honourable mentions:

A big, big thank you to the following people:

- BanthaFupa: Helping to test the different endpoints!
- Taranasus: His [LoopringSharp](https://github.com/taranasus/LoopringSharp) package gave me the little boost of motivation to get started on this API wrapper!
