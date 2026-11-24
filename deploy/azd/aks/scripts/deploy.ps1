# Windows version of deploy.sh.
$ErrorActionPreference = "Stop"
if (-not $env:SERVER_IMAGE) { throw "set SERVER_IMAGE (azd env set SERVER_IMAGE <registry>/aiapp-server:<tag>)" }
$chart = if ($env:CHART) { $env:CHART } else { "../../helm/aiapp-server" }
$tag = Get-Date -Format "yyyyMMddHHmmss"
az acr build --registry $env:AZURE_CONTAINER_REGISTRY_NAME --image "aiapp-apps:$tag" --build-arg "AIAPP_IMAGE=$env:SERVER_IMAGE" .
az aks get-credentials --resource-group $env:AZURE_RESOURCE_GROUP --name $env:AZURE_AKS_CLUSTER_NAME --overwrite-existing
kubelogin convert-kubeconfig -l azurecli
helm upgrade --install aiapp $chart --wait --timeout 10m `
  --set image.repository="$env:AZURE_CONTAINER_REGISTRY_ENDPOINT/aiapp-apps" --set image.tag=$tag `
  --set persistence.storageClass=managed-csi-premium --set persistence.size=32Gi
kubectl get pods -l app.kubernetes.io/instance=aiapp
