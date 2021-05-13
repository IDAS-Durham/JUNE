from june.infection import Immunity

class TestImmunity:
    def test_immunity(self):
        immunity = Immunity(susceptibility=0.3)
        assert immunity.susceptibility == 0.3
        assert len(immunity.recovered_infections_ids) == 0
        immunity.add_immunity(123)
        assert immunity.is_immune(123) is True
