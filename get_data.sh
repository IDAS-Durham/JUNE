#!/bin/sh

#https://drive.google.com/open?id=1BCie3RBr502XdYusXY2JcrU9xdGLw1FD
fileId=1BCie3RBr502XdYusXY2JcrU9xdGLw1FD
fileName=data.zip
curl -sc cookie "https://drive.google.com/uc?export=download&id=${fileId}" > /dev/null
code="$(awk '/_warning_/ {print $NF}' cookie)"  
curl -Lb cookie "https://drive.google.com/uc?export=download&confirm=${code}&id=${fileId}" -o ${fileName}

unzip ${fileName} || tar -zxvf ${fileName}
rm cookie
rm data.zip
