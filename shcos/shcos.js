module.exports = function(RED) {
    const IBM = require('ibm-cos-sdk');
    const fs = require('fs');
    const async = require('async');
    let cos ;

    function ShCosNode(config) {
    
        RED.nodes.createNode(this,config);
        var node = this;
        this.cfg = RED.nodes.getNode(config.configname)
        this.configname = this.cfg.configname
        this.endpoint = this.cfg.endpoint
        this.apikeyid = this.cfg.apikeyid
        this.serviceInstanceId = this.cfg.serviceInstanceId
        this.signatureVersion = this.cfg.signatureVersion

        node.on('input', function(msg) {

            var nodeContext = this.context();

            var flowContext = this.context().flow;
            var globalContext = this.context().global;     

            var config = {
                endpoint: this.endpoint,
                apiKeyId: this.apikeyid,
                serviceInstanceId: this.serviceInstanceId,
                signatureVersion: this.signatureVersion
            };

            try{
                cos = new IBM.S3(config);
                console.log( `Upload  into bucketName= ${msg.bucketName}  itemName= ${msg.itemName} length of data = ${ msg.payload.length}`  )
                return multiPartUpload2(msg.bucketName, msg.itemName, msg.payload)
                .then((data) =>{
                    console.log(`upload result` + JSON.stringify(data));
                    msg.payload={};
                    msg.payload.ok=true;
                    msg.payload.uploadresult={};
                    msg.payload.uploadresult=data;
                    node.send(msg);
                });

               
            } catch (e) {
                this.status({});
                this.error(e.message, msg)
                node.send(msg);

            }
          
        });
    }

    RED.nodes.registerType("shibmcos", ShCosNode);

    // config node
    function ShibmcosConfigNode(config) {
		RED.nodes.createNode(this,config)

        this.configname = config.configname;
        this.endpoint = config.endpoint;
        this.apikeyid = config.apikeyid;
        this.serviceInstanceId = config.serviceInstanceId;
        this.signatureVersion = config.signatureVersion;


	}

	RED.nodes.registerType("shibmcos-config", ShibmcosConfigNode)

    async function multiPartUpload2(bucketName, itemName, fileData) {
        return new Promise(function (resolve, reject) {
                var uploadID = null;
                return cos.createMultipartUpload({
                    Bucket: bucketName,
                    Key: itemName
                }).promise()
                .then( (data) =>{
                    uploadID = data.UploadId;
                    console.log(`Starting multi-part upload for ${itemName} to bucket: ${bucketName}`);
                    return cos.createMultipartUpload({
                        Bucket: bucketName,
                        Key: itemName
                    }).promise()
                })    
                .then((data) => {
                    uploadID = data.UploadId;
                    //begin the file upload
                    //min 5MB part
                    var partSize = 1024 * 1024 * 5;
                    var partCount = Math.ceil(fileData.length / partSize);

                    async.timesSeries(partCount, (partNum, next) => {
                        var start = partNum * partSize;
                        var end = Math.min(start + partSize, fileData.length);

                        partNum++;

                        console.log(`Uploading to ${itemName} (part ${partNum} of ${partCount})`);

                        cos.uploadPart({
                            Body: fileData.slice(start, end),
                            Bucket: bucketName,
                            Key: itemName,
                            PartNumber: partNum,
                            UploadId: uploadID
                        }).promise()
                        .then((data) => {
                            next(null, {ETag: data.ETag, PartNumber: partNum});
                        })
                        .catch((e) => {
                            cancelMultiPartUpload(bucketName, itemName, uploadID);
                            console.error(`ERROR: ${e.code} - ${e.message}\n`);
                        });
                    }, (e, dataPacks) => {
                        cos.completeMultipartUpload({
                            Bucket: bucketName,
                            Key: itemName,
                            MultipartUpload: {
                                Parts: dataPacks
                            },
                            UploadId: uploadID
                        }).promise()
                        .then( () => {
                            console.log(`Upload of all ${partCount} parts of ${itemName} successful.`);
                            var uploadresult = {bucketName: bucketName, itemName: itemName, uploadID: uploadID};
                            console.log("!!!!upploded result= " + JSON.stringify(uploadresult));
                            return resolve( uploadresult);
                        })
                        .catch((e) => {
                            cancelMultiPartUpload(bucketName, itemName, uploadID);
                            console.error(`ERROR: ${e.code} - ${e.message}\n`);
                            return reject(e);
                        });
                    });
                
                })
                .catch((e) => {
                    console.error(`ERROR: ${e.code} - ${e.message}\n`);
                    throw new Error(`ERROR: ${e.code} - ${e.message}\n`)
                });
        });        
    }

    function cancelMultiPartUpload(bucketName, itemName, uploadID) {
        return cos.abortMultipartUpload({
            Bucket: bucketName,
            Key: itemName,
            UploadId: uploadID
        }).promise()
        .then(() => {
            console.log(`Multi-part upload aborted for ${itemName}`);
        })
        .catch((e)=>{
            console.error(`ERROR: ${e.code} - ${e.message}\n`);
        });
    }

}

