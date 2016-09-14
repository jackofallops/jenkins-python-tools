# ArtifactTools module

## Sections
* ArtifactConfig
* ArtifactUploader
* ArtifactDownloader

## ArtifactConfig
This class safely loads an processes a named yml file (artifact-deploy.yml by default) into upload and download jobs.
The objects created by the config load can then be used to retrieve and deploy artifacts from/to remote (or local) locations
### Example Config

```yaml
    ---
    download:
      artifact: test.tgz
      url: http://localhost:55581/
      username: test
      password: test
      apikey: 1234567890
      checksum: True
    
    upload:
      artifact: test.tgz
      target_type: server
      username: test
      password: test
      identity_file: .ssh/id_rsa
      target: localhost
      target_port: 22
        
```

## ArtifactUploader
This class performs the upload functions, based on the options and supporting information in the yml config file

## ArtifactDownloaded
This class performs the download functions, based on the options and supporting information in the yml config file