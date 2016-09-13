#!/usr/bin/env python
from ArtifactTools import *


def main():
    dc = ArtifactConfig()
    if 'download' in dc.config:
        ad = ArtifactDownloader(dc.config, 'download')
        ad.download()
        if 'checksum' in dc.config:
            if dc.config['checksum']:
                ad.download(ArtifactDownloader.CHECKSUM)
                ad.check_checksum()
    if 'upload' in dc.config:
        au = ArtifactUploader(dc.config, 'upload')
        au.upload()


if __name__ == '__main__':
    main()
