# Risks

| # | Risk | Control |
| --- | --- | --- |
| 1 | Regenerated frozen fixtures hide an unintended canonical-stream change. | Every fixture diff is reviewed cell by cell and recorded in `progress.md`; only cells whose input family the parser fix touches may change. |
| 2 | An unnecessary fingerprint change breaks existing sealed bundles. | D-07 was withdrawn after source verification. Keep the algorithm unchanged and retain NFC/NFD and pre-taxonomy bundle regressions. |
| 3 | A stricter JSON loader refuses inputs a previous run accepted. | Refusals are typed and named; the change is recorded in `docs/migration.md`; no silent normalization remains. |
| 4 | Performance memoization returns stale verified state after a concurrent commit. | Memo is keyed by HEAD revision id and invalidated when HEAD is re-read under the lock; commit still re-reads HEAD. |
| 5 | Review ingestion turns a fail-closed path into an unreviewed promotion. | Reviews bind by candidate id and decision digest; a bundle for another recipe or result is refused; default policy stays `none`. |
| 6 | An unsigned Mac test pass is mistaken for public distribution evidence. | The takeover runs the full Debug suite on the local Mac and requires the GitHub Debug job to pass. Signing, notarization, and public readiness remain outside this packet. |
| 7 | Doc reconciliation overwrites a statement that was correct. | The audit's list of accurate documents is left untouched; only quoted stale statements change. |
| 8 | Splitting the stage validator changes accepted or refused workspaces. | Per-stage validators are extracted mechanically with the existing regression suite as the oracle; refusal messages keep their codes. |
