# LoopringAPI (Work in progress)

An API Wrapper for Loopring, made with Python.

Please feel free to contribute if you feel so inclined to do so - every little helps!  
Whether this is in the form of a spelling mistake, a redesign of a class, or a new endpoint, anything and everything is useful.

I'll be adding a `CONTRIBUTING.md` file soon, but will aim to finish the bulk of the wrapper first.

# PROGRESS: 22/38 REST API Endpoints done!

- Measuring progress by the [official docs](https://docs.loopring.io/en/)' REST API endpoints.
- I have yet to start on the websocket API!

# [API Reference](https://diggydev.co.uk/loopring/index.html) being updated almost daily!

# TODO:

- [x] Support datetime objects for timestamps.
- [ ] Look into turning prices into floats instead of strings.
- [ ] Figure out why `keySeed` isn't being returned from the account query endpoint.
- [ ] Finish off REST API endpoints.
- [ ] Start and finish the websocket API.
- [ ] Make some sense out of [how storage IDs work](https://github.com/Loopring/protocols/blob/master/packages/loopring_v3/DESIGN.md#storage).
- [ ] Load in client config/account export from a file instead of pasting it directly into a python script.
- [ ] Finish documentation for all the endpoints.
- [ ] Add loads of examples!

## Honourable mentions:

A big, big thank you to the following people:

- BanthaFupa: Helping to test the different endpoints!
- Taranasus: His [LoopringSharp](https://github.com/taranasus/LoopringSharp) package gave me the little boost of motivation to get started on this API wrapper!
