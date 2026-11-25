# Clusters

Several servers can form a cluster that keeps apps running when a server fails. Every write the cluster acknowledges is stored on a majority of its nodes before the caller gets an answer, so a three-node cluster survives losing any one node without losing data. The writes include app data, memory, jobs, events, vectors, files, deployed versions, keys and secrets.

## How it works

- **Membership and leadership:** a Raft group agrees on the members and elects a leader.
- **Every node has all the data:** writes go through the group's log, and each node applies them to its own stores.
- **Every node serves:** each node runs the apps' workers and answers their requests itself.
- **The leader runs what must run once:** jobs, schedules, subscriptions, Kafka bridges and connector syncs. A job enqueued or an event published on any node runs on the leader.
- **No lost updates:** writes that read and then change data (counters, sets, lists, locks, topic offsets, approvals, model spend) run on the leader, so requests on different nodes never overwrite each other. A node always reads its own writes. Plain reads stay on the node.
- **Failover:** if the leader fails, another node is elected in about a second. It already has every acknowledged write and starts the jobs and schedules. Clients that send requests to any node keep working, apart from a short pause during the election.

## Create one

Start every server with a cluster address (Raft listens on that port, the cluster API on the next one) and the same `--data-dir` path:

```bash
aiapp serve --addr 0.0.0.0:8080 --cluster-addr 10.0.0.1:7000 --data-dir /var/lib/aiapp
```

On the first node, which may already have apps:

```bash
aiapp cluster init
# Cluster created with node node1-3fa2c1.
# Join other servers with:
#   aiapp cluster join THIS-HOST:PORT --token aiappc1.…
```

The server restarts as the cluster's first member, and its data becomes the cluster's.

On each other node (a fresh server with no apps), give any member's cluster address and the token:

```bash
aiapp cluster join 10.0.0.1:7000 --token aiappc1.…
aiapp cluster status
```

The joining server receives a full copy of the data and the cluster's master key, and restarts as a member. It refuses to join if it has apps of its own, because joining replaces its data with the cluster's.

```text
Node node2-81bd04: Follower; leader node1-3fa2c1; term 2

NODE          ROLE      HEALTH  RAFT           HTTP           HARDWARE
node1-3fa2c1  leader    ok      10.0.0.1:7000  10.0.0.1:8080  16 cores, 0 GPUs
node2-81bd04  follower  ok      10.0.0.2:7000  10.0.0.2:8080  16 cores, 0 GPUs
node3-c09e77  follower  ok      10.0.0.3:7000  10.0.0.3:8080  16 cores, 0 GPUs
```

Put a load balancer in front of every node's `--addr`: any node answers, and followers forward to the leader. When a node listens on all interfaces (`--cluster-addr 0.0.0.0:7000`), say how the others reach it with `--cluster-advertise 10.0.0.1:7000`.

## Placement and routing

By default every node runs every app. To run an app on fewer nodes, say how many in its manifest:

```yaml
cluster:
  nodes: 2   # the leader and one other node
```

The other nodes are chosen by hashing the app name, so each app lands on the same nodes every time. A node that doesn't run an app forwards its requests to one that does.

- **Conversations:** requests with an `X-Session-Id` header always go to the same node, whichever node receives them. Repeated prompts then hit that node's context cache ([context memory](../install/local-models.md#faster-answers-for-long-contexts-context-memory)).
- **Other requests** are served by the node that receives them, when it runs the app.
- **Which node answered:** every app response has an `X-AIApp-Node` header.
- **Unreachable nodes:** if the chosen node can't be reached, the next one gets the request.
- **Body size:** request bodies forwarded between nodes are limited to 64 MB.

## Running a cluster

- **Deploy on the leader:** run `aiapp deploy`, `aiapp key …` and other app commands on the leader's machine. `aiapp cluster status` shows which node that is.
- **Majority:** the cluster needs a majority of its nodes up: 2 of 3, or 3 of 5.
- **Losing a node:** a stopped node shows as `unreachable`. When it restarts it rejoins by itself and catches up.
- **Losing the leader:** another node takes over. When the old leader comes back, it rejoins as a follower.
- **Leaving:** `aiapp cluster leave` takes a node out cleanly, and it restarts standalone with an empty cluster state. Remove a node that died for good with `aiapp cluster remove NODE`, so it no longer counts towards the majority.
- **New nodes:** a new node joins as a non-voter, catches up, and only then becomes a voter. So adding a node never puts the majority at risk, even while another node is down.

## Limits in this version

- **Writes that read and then change data go to the leader:** each costs a round trip between nodes. Plain reads and model calls don't.
- **Deploy and admin commands run on the leader.**
- **Same data folder path on every node:** deployments record their folder paths.
- **Files and uploads:** each is replicated up to 128 MB.
- **What stays per node:** the audit log, traces, the model store (`aiapp model pull`), and caches such as Python environments. Pull local models on each node that may lead.

## Security

- **Encryption:** traffic between nodes is TLS 1.3, pinned to the cluster's own certificate. `cluster init` creates it, and only nodes holding it can connect.
- **Joining:** a joining node proves the secret in the token, checks it is talking to the right cluster (the token carries the certificate's fingerprint), and then receives the certificate and the master key.
- **Treat the token like a password.** The cluster credentials are in `<data-dir>/cluster/`, readable only by the server's user.
- **Ports:** open the cluster port and the port after it between the nodes only.

| Port | What |
|---|---|
| `--cluster-addr` (e.g. 7000) | Raft: votes and replicated data |
| that port + 1 (7001) | cluster API: join, health, status |
