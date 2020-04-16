#!/bin/sh

#https://drive.google.com/open?id=1ths-W5DevesmiMoQ1WPunXNwGVI8CV1B
fileId=1ths-W5DevesmiMoQ1WPunXNwGVI8CV1B
fileName=data.zip
curl -sc cookie "https://drive.google.com/uc?export=download&id=${fileId}" > /dev/null
code="$(awk '/_warning_/ {print $NF}' cookie)"  
curl -Lb cookie "https://drive.google.com/uc?export=download&confirm=${code}&id=${fileId}" -o ${fileName} 

unzip data.zip
rm data.zip
rm cookie
