#!/bin/sh

# https://drive.google.com/open?id=1L-qX_2vFxv-XTQ9FRbViCIYCVcYNAm-9
fileId=1L-qX_2vFxv-XTQ9FRbViCIYCVcYNAm-9
fileName=data.zip
curl -sc /tmp/cookie "https://drive.google.com/uc?export=download&id=${fileId}" > /dev/null
code="$(awk '/_warning_/ {print $NF}' /tmp/cookie)"  
curl -Lb /tmp/cookie "https://drive.google.com/uc?export=download&confirm=${code}&id=${fileId}" -o ${fileName} 

unzip data.zip
rm data.zip
