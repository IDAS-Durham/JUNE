#!/bin/sh

#https://drive.google.com/open?id=1GJKG46cWRkyUFXbd7SwYzaAW3d6vnA_I
fileId=1GJKG46cWRkyUFXbd7SwYzaAW3d6vnA_I
fileName=data.zip
curl -sc cookie "https://drive.google.com/uc?export=download&id=${fileId}" > /dev/null
code="$(awk '/_warning_/ {print $NF}' cookie)"  
curl -Lb cookie "https://drive.google.com/uc?export=download&confirm=${code}&id=${fileId}" -o ${fileName}

unzip ${fileName} || tar -zxvf ${fileName}
rm cookie
rm data.zip
