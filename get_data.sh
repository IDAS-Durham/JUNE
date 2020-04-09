#!/bin/sh

#https://drive.google.com/open?id=12HTIFPa9oe053xTVuLB2zXTDYfquLXhC
fileId=12HTIFPa9oe053xTVuLB2zXTDYfquLXhC
fileName=data.zip
curl -sc cookie "https://drive.google.com/uc?export=download&id=${fileId}" > /dev/null
code="$(awk '/_warning_/ {print $NF}' cookie)"  
curl -Lb cookie "https://drive.google.com/uc?export=download&confirm=${code}&id=${fileId}" -o ${fileName} 

unzip data.zip
rm data.zip
rm cookie
