#!/bin/sh
data_release="westeros_tutorial_data.zip"
wget --user=access --password=d0wn10@d$  "http://virgodb.dur.ac.uk/downloads/dc-quer1/$data_release"
unzip $data_release
rm $data_release
