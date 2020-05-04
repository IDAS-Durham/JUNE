#!/bin/sh

#https://drive.google.com/open?id=1-sRXy-uuAFRpKBIVz6fBn6as4jJ9enVV
fileId=1-sRXy-uuAFRpKBIVz6fBn6as4jJ9enVV

fileName=data.zip
curl -sc cookie "https://drive.google.com/uc?export=download&id=${fileId}" > /dev/null
code="$(awk '/_warning_/ {print $NF}' cookie)"  
curl -Lb cookie "https://drive.google.com/uc?export=download&confirm=${code}&id=${fileId}" -o ${fileName}

unzip ${fileName} || tar -zxvf ${fileName}
rm cookie
rm data.zip
