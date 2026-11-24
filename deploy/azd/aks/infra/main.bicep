// AKS for AI App Server: a small cluster with a system pool, a registry the
// kubelet can pull from, and the managed Premium SSD storage class the chart's
// volume uses. The Helm release is installed by scripts/deploy.sh.
targetScope = 'resourceGroup'

@minLength(1)
@maxLength(40)
param environmentName string
param location string = resourceGroup().location
param nodeSize string = 'Standard_D4s_v5'
param nodeCount int = 2

var token = toLower(uniqueString(subscription().id, resourceGroup().id, environmentName))
var tags = { 'azd-env-name': environmentName }

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'log-${token}'
  location: location
  tags: tags
  properties: { sku: { name: 'PerGB2018' }, retentionInDays: 30 }
}

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: 'cr${token}'
  location: location
  tags: tags
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: false }
}

resource aks 'Microsoft.ContainerService/managedClusters@2024-09-01' = {
  name: 'aks-${token}'
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: {
    dnsPrefix: 'aiapp-${token}'
    enableRBAC: true
    aadProfile: { managed: true, enableAzureRBAC: true }
    disableLocalAccounts: true
    agentPoolProfiles: [
      { name: 'system', mode: 'System', count: nodeCount, vmSize: nodeSize, osType: 'Linux', osSKU: 'AzureLinux' }
    ]
    addonProfiles: {
      omsagent: { enabled: true, config: { logAnalyticsWorkspaceResourceID: logs.id } }
    }
    oidcIssuerProfile: { enabled: true }
    securityProfile: { workloadIdentity: { enabled: true } }
  }
}

var acrPull = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
resource pull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, aks.id, acrPull)
  scope: registry
  properties: { roleDefinitionId: acrPull, principalId: aks.properties.identityProfile.kubeletidentity.objectId, principalType: 'ServicePrincipal' }
}

output AZURE_CONTAINER_REGISTRY_NAME string = registry.name
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = registry.properties.loginServer
output AZURE_AKS_CLUSTER_NAME string = aks.name
output AZURE_RESOURCE_GROUP string = resourceGroup().name
