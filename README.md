# COVID Modelling

Repository for data and models built

Given the size of this team we should work in branches and merge regularly and separate folders for projects.

# Data
## How to get the data

Use the ``get_data.sh`` script to fetch the latest data from google drive:

```
bash get_data.sh
```

If you are using Windows, or you want to downloaded it manually, go [here](https://drive.google.com/open?id=1A2rhq8JiCTOqOhUaSgFyIO01vDPnDUGj).

## How to add new data

To add new data, first add the new files into your existing data folder, then zip the folder and upload it [here](https://drive.google.com/open?id=1A2rhq8JiCTOqOhUaSgFyIO01vDPnDUGj). Then right click on the updated uploaded data.zip file and select 'get shareable link'. Copy the url, and edit the ``get_data.sh`` script appropriately (changing the fileId as it is shown inside the script). 

Remember to push the updated script!

# Ongoing documentation sources

[Main documentation](https://josephpb.github.io/covidmodelling)

[Working Google Doc with meeting notes](https://docs.google.com/document/d/1EwwHZ0s3uVWmkEdhiw94cqrhfoLsTu_Pay2H11LjVOw/edit)<br>

[UML class diagram](https://drive.google.com/file/d/1YMUAePtUvx1xLVObjnz1n5IkDfJOkmD8/view)



# Setup

To install the package, install requisites and

``pip install -e .``


# World class example

A testing example of a populated world class (where world means the North East) can be found here:

https://mega.nz/file/KjwXhYwL#AXiTRt8mEgwGiJeANGhtWwBLPmgoDWovx58ywnZQ1PM

The world can be loaded with

```
import pickle
with open("world.pkl", "rb") as f:
  world = pickle.load(f)
```

The people habiting the world is ``world.people``, and the output areas are in ``world.areas``, people live in houses found at ``world.areas.households``, each person also has an attirube ``people.household`` that points to the household they belong.
