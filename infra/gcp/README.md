# Experiment 2 as a Cloud Run job with a GPU

`uv run inv gcp.run --run <name>` runs Experiment 2 as a Cloud Run job with an
NVIDIA L4 in europe-west1 and brings the sealed bundles and telemetry back to
`results/<name>/`. Kodama's Terraform is not read or changed: this folder has its
own configuration and local state (`infra/gcp/terraform.tfstate`, gitignored).

```bash
uv run inv gcp.estimate --run e2-cloudrun-l4-subset --args="--max-cases 2"   # creates nothing
uv run inv gcp.plan --run e2-cloudrun-l4-subset                              # terraform plan, creates nothing
uv run inv gcp.run --run e2-cloudrun-l4-subset --args="--max-cases 2"        # estimate, confirm, run
uv run inv gcp.destroy                                                       # remove job, registry, account
```

## What it creates

| Resource | Bills |
|---|---|
| Artifact Registry repository `stale-but-on-time` (images tagged by commit; 5 kept) | storage, ≈ $0.10 per GiB-month (image ≈ 4–5 GiB) |
| Bucket `kodama-500509-stale-but-on-time`: `models/` (the Ollama blobs, ≈ 10 GB, checked against the local runs) and `results/<run>/` | ≈ $0.02 per GiB-month |
| Service account `sbot-e2-job` (object admin on that bucket only) | — |
| Cloud Run job `sbot-e2`: 1× L4, 6 vCPU, 24 GiB (24 GiB needs 6 vCPU), no retries, task timeout 1 h (longer is a Beta feature) | per second while running: ≈ $1.23/h |

The job bills only while an execution runs, and Cloud Run stops it at the task
timeout (`--max-hours`, default 1; up to 12 h for GPU jobs, but more than 1 h is a Beta feature), so a hung run cannot keep
billing past that. Ctrl-C in the task cancels the execution.

## What a run does

1. Estimate and confirmation (`--yes` skips it, `--estimate-only` stops).
2. `terraform apply` (idempotent).
3. Image (`Dockerfile`): `ollama/ollama:0.40.13` (the release of the stored
   runs) + uv 0.13.6 + `git archive HEAD` + `uv sync --frozen`, built by Cloud
   Build in GCP and tagged with the commit (only the ~25 MB source is uploaded;
   $0.006 per build-minute, 2,500 free minutes a month). Tracked files must have
   no uncommitted changes. Skipped when the tag exists. Kodama builds locally
   with `docker buildx`; over a home connection the 3 GB base image and the push
   took too long.
4. The models: the task uploads the local manifests
   (`~/.ollama/models/manifests/...`, about 1 KB each) and passes their SHA-256
   (`ollama list` shows its first 12 characters). The job takes each blob a
   manifest names from the bucket, or downloads it by digest from Ollama's
   registry and saves it to the bucket, and checks every hash: the weights are
   byte-identical to the local runs (`machine/models.txt`). Pulling by tag
   would not do: on 2026-11-13 the registry's `gemma4:e4b` tag pointed at
   different weights (manifest `ccd2e5…`, ~6.6 GB) from those of the stored
   runs (`c6eb39…`, 9.6 GB); the old blobs are still served by digest.
   `--stages models` uploads the local blobs instead.
5. `gcloud run jobs execute` with `RUN_NAME` and `RUN_ARGS`. The entrypoint
   (`job.sh`) starts Ollama with the
   laptop's settings (flash attention, q8_0 KV cache), runs `inv e2.run`, and
   copies `results/<run>` to the bucket on exit, success or not, with status
   markers (STARTED, OLLAMA_STARTED, MODELS_READY, DONE or FAILED).
6. Results are copied to `results/<run>/` with `machine.json` (billed seconds
   from the execution's start and completion, and their cost), the telemetry
   summary and `estimate_vs_actual.md`.

## Hardware (DGX Spark comparison)

| | DGX Spark | Cloud Run L4 (this job) | Cloud Run RTX PRO 6000 |
|---|---|---|---|
| GPU | GB10 (Blackwell) | L4 (Ada) | RTX PRO 6000 Blackwell |
| GPU memory | 128 GB unified (shared with CPU) | 24 GB GDDR6 | 96 GB GDDR7 |
| Memory bandwidth | 273 GB/s | 300 GB/s | 1,597 GB/s |
| europe-west1 | — | yes, ≈ $1.23/h at 6 vCPU / 24 GiB | not offered for jobs (europe-west4 is) |

The L4 is the cheaper option and has about the Spark's memory bandwidth, which
bounds token generation, so its decode speed on `gemma4:e4b` is a fair stand-in
for the latency question. It has a fifth of the memory and an older
architecture, and neither GPU has unified memory: models above ~20 GB (e.g.
`gemma4:31b` at 8 bits) need the RTX PRO 6000 in europe-west4.

## Quota

New projects get 3 L4 GPUs for Cloud Run jobs (without zonal redundancy) on the
first deployment, subject to availability. If the deployment fails for quota,
request "Total Nvidia L4 GPU allocation without zonal redundancy, per project
per region" for europe-west1 under IAM & Admin → Quotas & System Limits.
