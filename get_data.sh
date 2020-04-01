#!/bin/sh

# https://drive.google.com/drive/folders/1A2rhq8JiCTOqOhUaSgFyIO01vDPnDUGj
fileId=1A2rhq8JiCTOqOhUaSgFyIO01vDPnDUGj 
fileName=data.zip
curl -sc /tmp/cookie "https://drive.google.com/uc?export=download&id=${fileId}" > /dev/null
code="$(awk '/_warning_/ {print $NF}' /tmp/cookie)"  
curl -Lb /tmp/cookie "https://drive.google.com/uc?export=download&confirm=${code}&id=${fileId}" -o ${fileName} 

unzip data.zip
rm data.zip
