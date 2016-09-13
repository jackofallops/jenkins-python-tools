# ArtifactTools module

## Sections
* ArtifactConfig
* ArtifactUploader
* ArtifactDownloader

## ArtifactConfig
This class safely loads an processes a named yml file (artifact-deploy.yml by default) into upload and download jobs.
The objects created by the config load can then be used to retrieve and deploy artifacts from/to remote (or local) locations

## ArtifactUploader
This class performs the upload functions, based on the options and supporting information in the yml config file

## ArtifactDownloaded
This class performs the download functions, based on the options and supporting information in the yml config file