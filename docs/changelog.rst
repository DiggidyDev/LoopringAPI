:tocdepth: 1

Changelog
=========

Any changes made to the Loopring API wrapper will be stated here. Any breaking
changes will be made obvious, though will try to be kept to a minimum once a
stable package is released.


v0.0.2a
-------

- Added a changelog!
- Added more docstrings to :class:`~loopring.client.Client`, along with warnings
  about certain untested methods
  ``accountId`` to ``account_id``
- Account importing now works with exported account keys.  E.g. No need to change
- Changed documentation structure - might change it back, but we'll see :^)
- Updated ``ExitPoolTokens.to_params()`` to return volume when handled in a request
- Updated examples (removed unnecessary `handle_errors` kwarg)


v0.0.1a
-------

- Big bang!