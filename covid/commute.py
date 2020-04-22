import csv


class CommuteGenerator:
    def __init__(self, regional_generators):
        self.regional_generators = regional_generators

    @classmethod
    def from_file(cls, filename: str) -> "CommuteGenerator":
        with open(filename) as f:
            reader = csv.reader(f)
            next(reader)
            rows = [row for row in reader]
        return CommuteGenerator(rows)
