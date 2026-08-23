# Phase 7 Risk Register

**Status:** Open

| ID | State | Likelihood | Impact | Risk | Control |
| --- | --- | --- | --- | --- | --- |
| P7-R1 | Controlled for 7.1 | High | High | A `.jsonl` suffix silently switches into import | Mode is explicit; default remains document-source; planned modes refuse |
| P7-R2 | Open | High | High | Mapping invents meaning from ambiguous columns | 7.4 requires confirmation; detectors propose only |
| P7-R3 | Open | Medium | High | Imported partitions are silently resplit | 7.7 requires authoritative/advisory/replaced; default replaced until then |
| P7-R4 | Controlled for 7.1 | Medium | High | Document recovery is reused for exact row mapping | ADR-0010 forbids `parsers/structured.py` on the dataset-row path |
| P7-R5 | Open | Medium | Medium | Surfaces advertise a planned mode as implemented | Tracking binds support-registry modes to packaged executable flags |
