import itertools
import string
import yaml
from june import paths
import numpy as np
import logging

default_config_filename = paths.configs_path / "defaults/interaction/interaction.yaml"

logger = logging.getLogger("subgroup maker")


def get_defaults(spec):
    if spec in [
        "pub",
        "grocery",
        "cinema",
        "city_transport",
        "inter_city_transport",
        "gym",
    ]:
        return [0, 100], "Age"

    elif spec in ["care_home"]:
        return ["workers", "residents", "visitors"], "Discrete"

    elif spec in ["university"]:
        return ["1", "2", "3", "4", "5"], "Discrete"
    elif spec in ["school"]:
        return ["teachers", "students"], "Discrete"
    elif spec in ["household"]:
        return ["kids", "young_adults", "adults", "old_adults"], "Discrete"
    elif spec in ["company"]:
        return ["workers"], "Discrete"

    # Cox defaults
    elif spec in [
        "communal",
        "distribution_center",
        "e_voucher",
        "female_communal",
        "isolation_unit",
        "n_f_distribution_center",
        "pump_latrine",
        "religious",
    ]:
        return [0, 18, 60], "Age"
    elif spec in ["play_group"]:
        return [3, 7, 12, 18], "Age"
    elif spec in ["learning_center"]:
        return ["students", "teachers"], "Discrete"
    elif spec in ["hospital"]:
        return ["workers", "patients", "icu_patients"], "Discrete"
    elif spec in ["shelter"]:
        return ["inter", "intra"], "Discrete"
    elif spec in ["informal_work"]:
        return [0, 100], "Age"

    else:
        return ["defualt"], "Discrete"


class SubgroupParams:
    """
    Class to read and collect Interaction matrix information. Allows for reading of subgroups from generic bins

    Parameters
    ----------
        bins_groups:
            list of bin edges or categories
        bins_type:
            str, "Age" for bin ages, or "Discrete" for categorical bins

    Returns
    -------
        SubgroupParams class
    """

    AgeYoungAdult = 18
    AgeAdult = 18
    AgeOldAdult = 65

    PossibleLocs = [
        "pub",
        "grocery",
        "cinema",
        "city_transport",
        "inter_city_transport",
        "gym",
        "care_home",
        "university",
        "school",
        "household",
        "company",
        "communal",
        "distribution_center",
        "e_voucher",
        "female_communal",
        "isolation_unit",
        "n_f_distribution_center",
        "pump_latrine",
        "religious",
        "play_group",
        "learning_center",
        "hospital",
        "shelter",
        "informal_work",
    ]

    def __init__(self, params=None) -> None:

        if params is None:
            self.params = params
            self.specs = None
        else:
            self.params = params
            self.specs = params.keys()

    def subgroup_bins(self, spec):
        return self.params[spec]["bins"]

    def subgroup_type(self, spec):
        return self.params[spec]["type"]

    def subgroup_labels(self, spec):
        if spec not in self.params.keys():

            if spec not in self.PossibleLocs:
                print(f"{spec} not defined in interaction yaml or defualt options")
                return list(["default"])
            else:
                Bins, Type = Get_Defaults(spec)
                logger.info(
                    f"{spec} interaction bins not specified. Using default values {Bins}"
                )
                self.params[spec] = {"bins": Bins, "type": Type}

        if (
            "bins" not in self.params[spec].keys()
            or "type" not in self.params[spec].keys()
        ):
            Bins, Type = Get_Defaults(spec)
            logger.info(
                f"{spec} interaction bins not specified. Using default values {Bins}"
            )
            self.params[spec]["bins"] = Bins
            self.params[spec]["type"] = Type
        elif spec in [
            "learning_center",
            "hospital",
            "shelter",
            "university",
            "school",
            "care_home",
            "household",
            "company",
        ]:
            Bins, Type = Get_Defaults(spec)
            if self.params[spec]["bins"] != Bins:
                logger.info(f"{spec} interaction bins need default values for methods.")
                self.params[spec]["bins"] = Bins
                self.params[spec]["type"] = Type

        if self.subgroup_type(spec) == "Age":  # Make dummy names for N age bins
            Nbins = len(self.params[spec]["bins"]) - 1
            return list(itertools.islice(self.excel_cols(), Nbins))
        elif self.subgroup_type(spec) == "Discrete":
            return list(self.params[spec]["bins"])  # Already have our names!

    # def kids_indexes(self, spec):
    #     if self.subgroup_type(spec) == "Age": #Make dummy names for N age bins
    #         index = sum(np.array(self.params[spec]["bins"]) < self.AgeAdult)
    #         return np.arange(0, index, 1)
    #     else:
    #         return np.array([]) #Empty list of bin indexes

    # def adults_indexes(self, spec):
    #     if self.subgroup_type(spec) == "Age": #Make dummy names for N age bins
    #         index = sum(np.array(self.params[spec]["bins"]) < self.AgeAdult)
    #         return np.arange(index, len(self.params[spec]["bins"])-1, 1)
    #     else:
    #         return np.array([]) #Empty list of bin indexes

    def excel_cols(self):
        """
        Generate generic string labels in form ["A", "B", "C", ... , "Z", "AA", "AB", .... ]

        Parameters
        ----------
            None

        Returns
        -------
            List of unique strings
        """
        n = 1
        while True:
            yield from (
                "".join(group)
                for group in itertools.product(string.ascii_uppercase, repeat=n)
            )
            n += 1

    @classmethod
    def from_file(cls, config_filename=default_config_filename) -> "SubgroupParams":
        """
        Read from interaction yaml and extract information on bins and bin types. Returning instance of SubgroupParams

        Parameters
        ----------
            config_filename:
                yaml location

        Returns
        -------
            SubgroupParams class instance
        """
        if config_filename is None:
            config_filename = default_config_filename
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return SubgroupParams(params=config["contact_matrices"])
