// AI App Server on Azure Container Apps: one replica (the server keeps its
// data on one volume), /data on an Azure Files NFS share (block-like
// semantics the embedded store needs; SMB is not supported for it), images in
// a private registry pulled with a managed identity, logs in Log Analytics.
targetScope = 'resourceGroup'

@minLength(1)
@maxLength(40)
@description('azd environment name; used to name resources')
param environmentName string

param location string = resourceGroup().location

@description('Optional Azure OpenAI endpoint passed to apps as AZURE_OPENAI_ENDPOINT')
param openAiEndpoint string = ''

@description('Image for the server; azd deploy replaces it with the built one')
param serverImage string = 'mcr.microsoft.com/k8se/quickstart:latest'

@description('CPU cores and memory for the server')
param cpu string = '2.0'
param memory string = '4Gi'

var token = toLower(uniqueString(subscription().id, resourceGroup().id, environmentName))
var tags = { 'azd-env-name': environmentName }

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'log-${token}'
  location: location
  tags: tags
  properties: { sku: { name: 'PerGB2018' }, retentionInDays: 30 }
}

resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: 'vnet-${token}'
  location: location
  tags: tags
  properties: {
    addressSpace: { addressPrefixes: ['10.40.0.0/16'] }
    subnets: [
      {
        name: 'apps'
        properties: {
          addressPrefix: '10.40.0.0/23'
          delegations: [{ name: 'aca', properties: { serviceName: 'Microsoft.App/environments' } }]
          serviceEndpoints: [{ service: 'Microsoft.Storage' }]
        }
      }
    ]
  }
}

// NFS shares need a premium FileStorage account reachable from the subnet.
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'st${token}'
  location: location
  tags: tags
  kind: 'FileStorage'
  sku: { name: 'Premium_LRS' }
  properties: {
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: false // NFS v4.1 does not use HTTPS; access is limited to the subnet below
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    networkAcls: {
      defaultAction: 'Deny'
      virtualNetworkRules: [{ id: vnet.properties.subnets[0].id, action: 'Allow' }]
    }
  }
}

resource share 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-05-01' = {
  name: '${storage.name}/default/aiapp-data'
  properties: { enabledProtocols: 'NFS', rootSquash: 'NoRootSquash', shareQuota: 100 }
}

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: 'cr${token}'
  location: location
  tags: tags
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: false }
}

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-${token}'
  location: location
  tags: tags
}

var acrPull = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
resource pull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, identity.id, acrPull)
  scope: registry
  properties: { roleDefinitionId: acrPull, principalId: identity.properties.principalId, principalType: 'ServicePrincipal' }
}

resource env 'Microsoft.App/managedEnvironments@2025-01-01' = {
  name: 'cae-${token}'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: { customerId: logs.properties.customerId, sharedKey: logs.listKeys().primarySharedKey }
    }
    vnetConfiguration: { infrastructureSubnetId: vnet.properties.subnets[0].id }
    workloadProfiles: [{ name: 'Consumption', workloadProfileType: 'Consumption' }]
  }
}

resource envStorage 'Microsoft.App/managedEnvironments/storages@2025-01-01' = {
  parent: env
  name: 'aiapp-data'
  properties: {
    nfsAzureFile: { server: '${storage.name}.file.${environment().suffixes.storage}', shareName: '/${storage.name}/aiapp-data', accessMode: 'ReadWrite' }
  }
  dependsOn: [share]
}

resource server 'Microsoft.App/containerApps@2025-01-01' = {
  name: 'ca-aiapp-${token}'
  location: location
  tags: union(tags, { 'azd-service-name': 'server' })
  identity: { type: 'UserAssigned', userAssignedIdentities: { '${identity.id}': {} } }
  properties: {
    environmentId: env.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: { external: true, targetPort: 8080, transport: 'auto', allowInsecure: false }
      registries: [{ server: registry.properties.loginServer, identity: identity.id }]
    }
    template: {
      containers: [
        {
          name: 'server'
          image: serverImage
          resources: { cpu: json(cpu), memory: memory }
          env: concat([
            { name: 'AIAPP_DATA_DIR', value: '/data' }
          ], empty(openAiEndpoint) ? [] : [
            { name: 'AZURE_OPENAI_ENDPOINT', value: openAiEndpoint }
          ])
          volumeMounts: [{ volumeName: 'data', mountPath: '/data' }]
          probes: [
            { type: 'Startup', httpGet: { path: '/health', port: 8080 }, periodSeconds: 5, failureThreshold: 60 }
            { type: 'Liveness', httpGet: { path: '/health', port: 8080 }, periodSeconds: 15 }
            { type: 'Readiness', httpGet: { path: '/health', port: 8080 }, periodSeconds: 5 }
          ]
        }
      ]
      // One replica: two servers must never open the same data volume.
      scale: { minReplicas: 1, maxReplicas: 1 }
      volumes: [{ name: 'data', storageType: 'NfsAzureFile', storageName: envStorage.name }]
    }
  }
  dependsOn: [pull]
}

output AZURE_CONTAINER_REGISTRY_ENDPOINT string = registry.properties.loginServer
output SERVER_URL string = 'https://${server.properties.configuration.ingress.fqdn}'
