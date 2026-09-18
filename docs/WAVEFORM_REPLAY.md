# Saved-waveform replay and independent review preparation

## Measured outcome

The offline adapter processed the recovered saved complex-IQ arrays. All source
bytes were preserved, both I and Q were retained, and no samples were discarded.
Two fresh Python processes produced byte-identical diagnostic output in this
environment. Raw test results, aggregate counts and code hashes are recorded in
`waveform_replay_checks.json`. This is a software replay result, not a new
measurement of the physical environment or an external accuracy score.

Targeted searches for reviewer, adjudication and annotation records did not
identify a compatible independently adjudicated reference set. This is a bounded
search finding, not proof that no such set exists. Provisional background labels
remain provisional. No original annotation was reconstructed from a prediction.

## Adapter contract

`waveform_replay.py` accepts one-dimensional complex64/complex128 NPY arrays.
It checks bounded file size and header-declared shape before loading the payload,
disables pickle, rejects unsupported types, malformed/trailing payloads and
nonfinite values, and hashes the exact loaded bytes. It performs no device,
network, RF or model calls.

The source summary and nonoverlapping windows contain RMS, peak, mean I/Q,
dominant AC frequency and its energy fraction. DC is removed before a complex
FFT. Frequency is reported in cycles per sample; the sample rate and center
frequency are left null. No assumed physical units or absolute RF frequency are
introduced. The spectrum uses a rectangular window; partial final windows are
retained and identified, with their own resolution. Constant/zero signals have
no reported dominant AC frequency. These are diagnostics, not anomaly decisions.

The adapter never discards Q or feeds these arrays into the fixed real-valued
synthetic detector. The previous off-bin and jointly wrong-context detector gates
remain failed and unretuned. Repeatability here is local to the tested software
environment; it is not a cross-platform numerical guarantee.

```bash
python waveform_replay.py saved_iq.npy replay_diagnostics.json
python -m unittest -v test_waveform_replay
```

Output creation is exclusive. The test suite uses known positive/negative complex
tones, DC, zero, Q-only inputs and partial windows. It also checks malformed or
oversized-declaration rejection, source preservation, empty reviewer fields,
packet hashes, duplicate-byte rejection and overwrite protection.

## Review packets

```bash
python prepare_review_packet.py new_review_directory saved_a.npy saved_b.npy
```

The generator validates inputs before creating a new directory. It copies the
original NPY bytes under neutral item names, writes diagnostics, and creates
separate **unfilled** reviewer worksheets. Reviewer files contain no previous
labels or original filenames. The coordinator-only mapping retains the filenames
and source hashes for traceability. All records initially share one conservative
source family; windows from one source are not independent examples.

The packet also includes an empty claim-evidence annotation template and review
guide. No reviewer identities, categories, actions, rationales or gold labels are
fabricated. A coordinator must define the rubric and ontology mapping, verify
permission and metadata, arrange independent reviews, freeze them, and resolve
disagreements through separate adjudication. Creating two templates does not
create two independent opinions or establish blinding.

Distribute only the appropriate reviewer worksheet, samples, diagnostics and
guide to each reviewer. Keep the coordinator mapping and the other reviewer's
answers withheld. The full archive is for the coordinator and is not itself a
blinded reviewer package. No reviewer has been contacted by this project.

`packet_manifest.json` is written last and lists SHA-256 hashes. Its absence means
the packet is incomplete. Verify the hashes before use; hashes alone do not
authenticate origin or chronology. Disk errors can leave an incomplete directory;
the generator does not silently overwrite it on retry.

## Remaining work

The recovered collection can support an offline adapter-development study with
explicit metadata assumptions. It cannot simultaneously become the final heldout
evaluation for choices tuned on that same collection. An external accuracy claim
needs compatible references, documented independent annotation, source-family
separation, a frozen target and an appropriate sampling plan. The claim-evidence
workbench needs its own category/action mapping and feature annotation; waveform
labels cannot substitute for that task.
