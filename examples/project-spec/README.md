# Project-spec example

Retained public fixtures for independent-product item 19.6.

A clean host copies this directory, runs `veriformis spec-run spec.json`,
and compares the sealed bundle's `manifest.json` SHA-256 to
`expected-fingerprint.json`. Dry-run writes nothing. The lock pins spec
digest, versions, and extras; it is not `uv.lock`.

This example does not upload. There are no secrets.
