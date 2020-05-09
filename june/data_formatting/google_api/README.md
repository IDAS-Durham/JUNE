# Distributions

This directory is for run-once simulations that may need to be initialised to generate the data and distributions required.

## Google Maps API

We use the Google Maps API to scrape data from across the UK for various statistics. To run this you will need an API key to run this which must be saved in a `.txt` file.

### Setting up an API key

To set up an API key, go to the [Getting Started](https://developers.google.com/maps/gmp-get-started) page and follow this instructions. You will need a Places API key.


### Running over MSOAs

`msoa_search.py` will run a search over all MSOAs by using the centroids of the MSOA and search over all nearby locations. Run `msoa_seach.py --help` to find out hot to run this. The search works by searching over types. Find out which types can be selected [here](https://developers.google.com/places/supported_types)