# Skipped: signed, notarized, and stapled Mac

**Date:** 2026-09-01

**Item:** 20.6

Public signed/notarized Mac is not in the frozen 1.0 support matrix.
The workbench is a local-dev thin CLI adapter. Group 9 automated gates
do not prove Developer ID signing, notarization, staple, or Gatekeeper
on a clean Mac.

This packet skips those artifacts with a record. The owner may later
supply signed, notarized, stapled evidence; that work is not started
here. GitHub remains the Python matrix. There is no `xcodebuild` job.

`support-matrix` `platforms.public_signed_mac` stays `false`.
`macos_workbench` stays `local-dev-thin-adapter`.
