#!/bin/sh

#https://drive.google.com/open?id=1yssNsQl15LqHYRFqIN_5bPyBAxS8zOvf
fileId=1yssNsQl15LqHYRFqIN_5bPyBAxS8zOvf
fileName=data.zip
curl -sc /tmp/cookie "https://drive.google.com/uc?export=download&id=${fileId}" > /dev/null
code="$(awk '/_warning_/ {print $NF}' /tmp/cookie)"  
curl -Lb /tmp/cookie "https://drive.google.com/uc?export=download&confirm=${code}&id=${fileId}" -o ${fileName} 

unzip data.zip
rm data.zip
