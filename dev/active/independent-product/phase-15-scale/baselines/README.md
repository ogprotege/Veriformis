# Named-hardware baseline reports

These JSON files are **measurement evidence**. They are not support
tiers, throughput SLAs, or product guarantees. `sla_claim` is false.

Tiny-fixture amplification is workspace overhead, not a storage claim.
Larger ladder points exist so amplification and RSS can be read against
source size.

`measure-markdown-duplicates-10-40` did not seal: the coverage gate
failed with `coverage-blocker-present` after default `full_text`
curation. That refusal is retained beside the passing reports.

`scale-baseline --corpus-id ci-tiny-jsonl` still refuses dataset-row.
That refusal is retained. Dataset-row compile was measured with the
existing CLI path on a two-row JSONL fixture. Peak RSS there is the
max of separate processes, not the 15.3b single-process number. That
run is not a support tier.

Hardware in each file is the machine that produced that run.
