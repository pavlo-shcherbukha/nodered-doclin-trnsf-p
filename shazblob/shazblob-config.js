module.exports = function(RED) {
    // config node
    function ShAzureBlobStorageConfigNode(config) {
		RED.nodes.createNode(this,config)
        this.name = config.configname;
        this.azure_tenant_id = config.azure_tenant_id;
        this.azure_client_id = config.azure_client_id;
        this.azure_client_secret = config.azure_client_secret;
        this.azure_storage_account_name = config.azure_storage_account_name;
	}

	RED.nodes.registerType("shazbstorage-config", ShAzureBlobStorageConfigNode)

    
}

