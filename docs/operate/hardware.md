# Hardware

At startup the server reads the machine's capabilities and sizes itself from them:

- CPU cores and instruction sets;
- memory and NUMA nodes;
- CXL memory;
- disks;
- GPUs, and memory the CPU and GPU share;
- data processors (DPUs) such as NVIDIA BlueField.

`aiapp hardware` shows what it found, where each kind of data goes, and what was applied.

```text
$ aiapp hardware
Hardware: the running server

CPU     Intel Xeon Gold 6430: 2 sockets, 64 cores, 128 threads (avx2 fma avx512f avx512_vnni amx_tile)
Memory  512.0 GB
NUMA    node 0 256.0 GB (64 CPUs); node 1 256.0 GB (64 CPUs)
Disk    nvme0n1 nvme 3.5 TB  <- data folder

Placement:
DATA          TIER  DETAIL                                                  NOTE
sessions      dram  8.0 GB block cache over the data folder (512.0 GB RAM)  -
hot-vectors   dram  dram (512.0 GB RAM); float32 up to 128.0 GB, …          -
cold-vectors  nvme  data folder on nvme0n1                                  -
logs          nvme  data folder on nvme0n1                                  -
inference     cpu   llama.cpp on 64 cores, 64 threads, spread over NUMA     -

Applied: key-value cache 8.0 GB; vector budget 128.0 GB; llama.cpp 64 threads over NUMA nodes; CPU kernels avx512-capable.
```

## What is applied

| Setting | From the hardware | Override |
|---|---|---|
| Key-value cache (sessions, app data) | a sixteenth of memory, 64 MB to 8 GB | — |
| Vector precision | vectors stay float32 while they fit in a quarter of memory, and are kept as int8 above that (scores within about 0.01) | `--vector-quantization none` or `int8` |
| llama.cpp threads | one NUMA node's physical cores; on multi-socket machines, all cores with `--numa distribute` | `threads:` on the local model |
| Local models' GPUs | the GPUs found (`nvidia-smi`) | `AIAPP_GPUS` |

The server also warns when the data folder is on a spinning disk, or when its disk can't be identified, as in containers. Fsyncs and the vector snapshot depend on disk speed, so put the data folder on SSD or NVMe.

## Where data goes

Each kind of data has a preferred list of tiers. The server picks the first one the machine has and records why it skipped the others:

| Data | Preferred tiers |
|---|---|
| Sessions and app key-value data | DRAM (cache) over the data folder's disk |
| Hot vectors | GPU memory, coherent CPU-GPU memory, DRAM, CXL memory, NVMe |
| Warm vectors | CXL memory (through the kernel's memory tiering), DRAM |
| Cold vectors (snapshot, collections out of memory), files, logs | NVMe, SSD, HDD (the data folder's disk) |
| Local inference | GPUs, coherent memory, CPU |

In this version, hot vectors stay in DRAM. A GPU vector index comes later, and the plan's notes say so on machines that have GPUs.

### Vector collections move by use

Each vector collection (an app's documents, a tenant's notes) is in memory or on disk, depending on how recently it was used:

- **Memory budget:** vector collections may take half of DRAM. Machines whose kernel moves cold pages to CXL memory (Linux memory tiering, `/sys/kernel/mm/numa/demotion_enabled`) add half of their CXL memory.
- **Over the budget:** the collections used longest ago go to their own encrypted file in the data folder. Collections used in the last 10 minutes stay in memory.
- **Coming back:** a collection on disk loads back on its next search or write. That one request waits for the load, typically milliseconds to a second for a large collection; later ones don't.
- **Restarts:** collections on disk stay there; the server starts with only the ones in memory.
- **Backups and new cluster nodes** receive every collection in full.
- **Quotas:** vector quotas count records wherever they are.

`--vector-cold-after 24h` also moves collections unused for a day out of memory when it isn't short. `aiapp hardware` shows the split:

```text
Vector collections: 12 in memory (3.1 GB), 40 on disk (9.8 GB); memory budget 64.0 GB; 41 moved to disk, 1 loaded back (last load 180 ms).
```

## Data plane

The server's data path runs behind one driver:

- encryption of stored data (AES-256-GCM);
- checksums of files, deployed versions and models (SHA-256);
- TLS for the Redis-protocol listener and between cluster nodes;
- the KV-cache tier of local inference engines;
- cluster replication traffic.

The **host driver**, the default, does this work on the CPUs, using their AES and SHA instructions. A DPU driver moves it onto a data processor. The server uses one when it finds a supported DPU, and checks first that it gives exactly the host driver's results. Otherwise it falls back to the host and says why. `aiapp hardware` shows which driver runs each function and how much work it has done:

```text
Data plane: host driver (no data processor (DPU) found; the host CPUs do the data path)
FUNCTION     RUNS ON  OPERATIONS  BYTES
encryption   host     1204        2.1 MB
checksum     host     3           18.4 KB
tls          host     0           0 B
kv-cache     host     1           0 B
replication  host     0           0 B
```

| `--data-plane` | Meaning |
|---|---|
| `auto` (default) | a DPU when one is found and this build has a working driver for it, the host otherwise |
| `host` | always the host CPUs |
| `dpu` | a DPU, or refuse to start |

This version detects BlueField, BlueField-2 and BlueField-3 cards, and has only the host driver. The BlueField driver comes next. Data written with one driver stays readable with any other, because every driver must produce the same ciphertext and digests.

## Try other machines

Emulated profiles show what the server would do on hardware you don't have:

```bash
aiapp hardware --profile gpu-server        # 8 GPUs, 2 sockets, 2 TB
aiapp hardware --profile grace-hopper      # Arm CPU with coherent GPU memory
aiapp hardware --profile cxl-server        # CXL memory on a CPU-less NUMA node
aiapp hardware --profile dpu-server        # a BlueField-3 DPU
aiapp hardware --profile laptop            # also: cpu-server, edge-arm
```

`aiapp hardware --save box.json` writes this machine's profile. Then `AIAPP_HAL_PROFILE=box.json aiapp serve` (or a built-in name) makes a server use it, for example to test placement in CI. Sizes are still capped by the memory the machine really has.
