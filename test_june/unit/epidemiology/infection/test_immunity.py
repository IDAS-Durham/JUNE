from june.epidemiology.infection import Immunity

class TestImmunity:
    def test_immunity(self):
        susceptibility_dict = {1: 0.3}
        immunity = Immunity(susceptibility_dict)
        assert immunity.susceptibility_dict[1] == 0.3
        immunity.add_immunity([123])
        assert immunity.is_immune(123) is True
        assert immunity.susceptibility_dict[123] == 0.0
