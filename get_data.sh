#!/bin/sh

#https://drive.google.com/open?id=1e96f63wgZ6cFxOZ1HGjm7o4mSm3Wegj0
fileId=1e96f63wgZ6cFxOZ1HGjm7o4mSm3Wegj0
fileName=data.zip
curl -sc cookie "https://drive.google.com/uc?export=download&id=${fileId}" > /dev/null
code="$(awk '/_warning_/ {print $NF}' cookie)"  
curl -Lb cookie "https://drive.google.com/uc?export=download&confirm=${code}&id=${fileId}" -o ${fileName}

unzip ${fileName} || tar -zxvf ${fileName}
rm cookie
rm data.zip
