# COVID Modelling

Repository for data and models built

Given the size of this team we should work in branches and merge regularly and separate folders for projects.

# Tests

Run the tests with

```
cd tests
pytest
```

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

[MVP Google Doc with testing strategy](https://docs.google.com/document/d/1O0v6O3rOlCDKFD66Y9KbZTfKLQPgmP1ScuwrFv4sspo/edit?usp=sharing)

[UML class diagram](https://drive.google.com/file/d/1YMUAePtUvx1xLVObjnz1n5IkDfJOkmD8/view)

[Epidem. Parameters of COVID-19](https://docs.google.com/document/d/1724PeV7bg9V0JRuQE1vpktB08bFWDmjHrd6HKyOG1Ns/edit#heading=h.xiukf7vmhszk)



# Setup

To install the package, install requisites

``pip install -r requirements.txt``

and

``pip install -e .``

# Quickstart

Refer to ``Notebooks/quickstart.ipynb``
