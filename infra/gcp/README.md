# Experiment 2 on a GPU machine in GCP

`uv run inv gcp.run --run <name>` runs the whole Experiment 2 (six conditions,
1,200 trials) on a GPU machine in `kodama-500509` and brings the sealed bundles
and telemetry back to `results/<name>/`. Everything it creates is destroyed at
the end.

```bash
uv run inv gcp.estimate --run e2-gcp-g4          # prints the estimate, creates nothing
uv run inv gcp.plan --run e2-gcp-g4              # terraform validate + plan, creates nothing
uv run inv gcp.run --run e2-gcp-g4               # estimate, confirmation, run, teardown
```

Options: `--machine g2-standard-8` (L4), `--spot`, `--max-hours 4` (hard
lifetime), `--args="--model gemma4:31b"` with `--models=gemma4:31b,nomic-embed-text`.

## What the job does

1. Estimate and confirmation (machine time for start-up, run and teardown; the
   worst case at the hard lifetime). `--yes` skips the question.
2. `git archive HEAD` (the working tree must be clean). Nothing is pushed; the
   archive is uploaded to the job's bucket.
3. `terraform apply`: a bucket, a service account that may write to that bucket
   and delete only its own machine, a network with no ingress, and the machine.
4. On the machine (`startup.sh.tftpl`): check the GPU driver, install Ollama
   0.40.13 with the laptop's settings (flash attention, q8_0 KV cache), pull the
   models, install uv, `uv sync --frozen`, `inv e2.run`, upload `results/<run>`.
5. The task follows the status markers (BOOTED, MODELS_READY, RUN_STARTED,
   RUN_FINISHED, DONE or FAILED) and copies the results back.
6. `terraform destroy`, then `machine.json` (hours and cost), the telemetry
   summary and `estimate_vs_actual.md`.

Three independent stops keep a hung run from billing:

- the startup script's EXIT trap uploads what exists and deletes the machine,
  on success and on failure (and a reboot deletes it instead of running again);
- Compute Engine's `max_run_duration` deletes the machine at the hard lifetime
  (default 4 h), even if the laptop is off;
- the task runs `terraform destroy` in a `finally` block, also on timeout and
  Ctrl-C. The bucket (force-destroyed) and service account go with it; if the
  task dies, they remain until the next `terraform destroy` (the bucket's
  objects expire after 14 days).

State is local (`infra/gcp/terraform.tfstate`, gitignored). Kodama's
Terraform is not touched; this module uses its project, region and naming.

## Before the first apply

- `gcloud auth login` and `gcloud auth application-default login` (Terraform
  and the job use them).
- APIs: Compute Engine, IAM, Cloud Storage. Kodama's Terraform enables all
  three in `kodama-500509`.
- Quota in europe-west1 for one machine: for G4, one NVIDIA RTX PRO 6000 GPU
  and 48 vCPUs of the G4 family (on-demand, or the preemptible quotas for
  `--spot`); for G2, one L4 GPU and 8 or 16 G2 vCPUs. New projects often have
  zero GPU quota; request it in the console (IAM & Admin → Quotas) before the run.
- Org policies that forbid external IPs on VMs
  (`constraints/compute.vmExternalIpAccess`) would block the machine's egress;
  the plan uses an ephemeral external IP and no ingress rule.
- The boot image family (`common-cu129-ubuntu-2404-nvidia-580`) has to exist:
  `gcloud compute images describe-from-family common-cu129-ubuntu-2404-nvidia-580 --project deeplearning-platform-release`.
  G4 needs NVIDIA driver R580 or later.

## Machine choice (DGX Spark comparison)

NVIDIA DGX Spark: GB10 Grace Blackwell, Blackwell GPU with 6,144 CUDA cores and
5th-generation tensor cores, up to 1 PFLOP FP4 with sparsity, 20 Arm cores,
128 GB LPDDR5X unified memory at 273 GB/s, models up to 200B parameters
(nvidia.com/products/workstations/dgx-spark, docs.nvidia.com/dgx/dgx-spark/hardware.html).

| | DGX Spark | g4-standard-48 | g2-standard-8 |
|---|---|---|---|
| GPU | GB10 (Blackwell) | RTX PRO 6000 Blackwell Server | L4 (Ada) |
| GPU memory | 128 GB unified (shared with CPU) | 96 GB GDDR7 | 24 GB GDDR6 |
| Memory bandwidth | 273 GB/s | 1,597 GB/s | 300 GB/s |
| CPU / RAM | 20 Arm cores / same 128 GB | 48 vCPU x86 / 180 GB | 8 vCPU / 32 GB |
| europe-west1 on-demand / spot | — | $4.95 / $2.22 per h | $0.94 / $0.56 per h |

No GCP machine matches the Spark on both counts. G4 matches the architecture
and roughly the model capacity, but its memory bandwidth is 5.8× the Spark's,
and token generation is bandwidth-bound, so G4 will be much faster than a Spark:
its latencies are a lower bound for Spark-class hardware, not an estimate of
it. L4 has about the Spark's bandwidth (300 vs 273 GB/s), so its decode speed
on a small model is the closer stand-in for the latency question, but it has a
fifth of the memory and an older architecture. Neither has unified memory.
