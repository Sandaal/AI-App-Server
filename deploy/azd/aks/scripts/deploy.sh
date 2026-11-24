#!/bin/sh
# Builds the server image with your apps in the registry, then installs or
# upgrades the Helm release. Needs the az CLI, kubectl, kubelogin and helm.
# SERVER_IMAGE is the AI App Server image (built from the repository and
# pushed to this registry, e.g. "$AZURE_CONTAINER_REGISTRY_ENDPOINT/aiapp-server:1.0.0").
set -eu
: "${SERVER_IMAGE:?set SERVER_IMAGE (azd env set SERVER_IMAGE <registry>/aiapp-server:<tag>)}"
CHART=${CHART:-../../helm/aiapp-server}
TAG=$(date +%Y%m%d%H%M%S)
az acr build --registry "$AZURE_CONTAINER_REGISTRY_NAME" --image "aiapp-apps:$TAG" --build-arg "AIAPP_IMAGE=$SERVER_IMAGE" .
az aks get-credentials --resource-group "$AZURE_RESOURCE_GROUP" --name "$AZURE_AKS_CLUSTER_NAME" --overwrite-existing
kubelogin convert-kubeconfig -l azurecli
helm upgrade --install aiapp "$CHART" --wait --timeout 10m \
  --set image.repository="$AZURE_CONTAINER_REGISTRY_ENDPOINT/aiapp-apps" --set image.tag="$TAG" \
  --set persistence.storageClass=managed-csi-premium --set persistence.size=32Gi
kubectl get pods -l app.kubernetes.io/instance=aiapp
