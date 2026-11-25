# Run on Kubernetes (Helm)

The Helm chart is in the [public repository](https://github.com/Sandaal/ai-app-server/tree/main/deploy/helm/aiapp-server), folder `deploy/helm/aiapp-server`.

## Install

```bash
git clone --depth 1 https://github.com/Sandaal/ai-app-server.git
helm install ai ./ai-app-server/deploy/helm/aiapp-server \
  --set image.repository=ghcr.io/sandaal/aiapp-server --set image.tag=3.0.0 \
  --set secretEnv.OPENAI_API_KEY=sk-...
kubectl exec -it ai-aiapp-server-0 -- aiapp apps
```

The chart runs **one** server as a StatefulSet with a persistent volume, because the server keeps its data on that volume. For more capacity, give it more CPU and memory, or run several releases.

## Recommended values

```yaml
# values.yaml
image: { repository: ghcr.io/sandaal/aiapp-server, tag: "3.0.0" }

masterKey:
  existingSecret: aiapp-master-key     # kubectl create secret generic aiapp-master-key --from-file=master.key
  key: master.key

secretEnv:
  OPENAI_API_KEY: sk-...               # or use your secret manager, see Secrets and vaults

ingress:
  enabled: true
  className: nginx
  annotations:
    nginx.ingress.kubernetes.io/proxy-buffering: "off"      # so answers stream
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
  hosts: [{ host: ai.example.com, paths: [{ path: /, pathType: Prefix }] }]
  tls: [{ secretName: ai-example-tls, hosts: [ai.example.com] }]

metrics:
  enabled: true                        # Prometheus metrics on port 9464
  serviceMonitor: { enabled: true }    # if you run the Prometheus Operator

apps:
  configMaps:                          # deploy apps from ConfigMaps at start
    - { name: hr-bot, configMap: hr-bot-app }

# Optional: operator model routing, hosted console with sign-in, audit export
gateway: ""        # see Server configuration files
console: ""
auditExport: ""
```

Keep the master key in a Secret (as above) so volume backups don't contain it.

## Apps from a ConfigMap

```bash
kubectl create configmap hr-bot-app --from-file=hr-bot/
```

Folders aren't supported by ConfigMaps; for apps with sub-folders, build your own image `FROM ghcr.io/sandaal/aiapp-server` with `COPY my-apps/ /apps/`.
