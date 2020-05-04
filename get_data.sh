#!/bin/sh

#https://drive.google.com/open?id=1tjxrxZJxRCd2moCqPE-swPiL8lb1l0CK
fileId=1tjxrxZJxRCd2moCqPE-swPiL8lb1l0CK
fileName=data.zip
curl -sc cookie "https://drive.google.com/uc?export=download&id=${fileId}" > /dev/null
code="$(awk '/_warning_/ {print $NF}' cookie)"  
curl -Lb cookie "https://drive.google.com/uc?export=download&confirm=${code}&id=${fileId}" -o ${fileName}

unzip ${fileName} || tar -zxvf ${fileName}
rm cookie
rm data.zip
