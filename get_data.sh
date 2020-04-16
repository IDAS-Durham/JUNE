#!/bin/sh

#https://drive.google.com/open?id=1pEUYQ0X8mctP7q5pWtOOxaqf4W-IxaLf
fileId=1pEUYQ0X8mctP7q5pWtOOxaqf4W-IxaLf
fileName=data
curl -sc cookie "https://drive.google.com/uc?export=download&id=${fileId}" > /dev/null
code="$(awk '/_warning_/ {print $NF}' cookie)"  
curl -Lb cookie "https://drive.google.com/uc?export=download&confirm=${code}&id=${fileId}" -o ${fileName}

unzip ${fileName} || tar -zxvf ${fileName}
rm cookie
