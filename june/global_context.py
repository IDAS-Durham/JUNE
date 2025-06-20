# june/global_context.py


class GlobalContext:
    _disease_config = None
    _simulator = None
    _tt_event_recorder = None

    @classmethod
    def set_disease_config(cls, disease_config):
        """
        Sets the global disease configuration.
        """
        cls._disease_config = disease_config

    @classmethod
    def get_disease_config(cls):
        """
        Returns the global disease configuration.
        """
        if cls._disease_config is None:
            raise ValueError("DiseaseConfig has not been set.")
        return cls._disease_config
    
    @classmethod
    def set_simulator(cls, simulator):
        cls._simulator = simulator
    
    @classmethod
    def get_simulator(cls):
        if cls._simulator is None:
            raise ValueError("Simulator has not been set.")
        return cls._simulator
    
    @classmethod
    def set_tt_event_recorder(cls, recorder=None):
        """
        Register a Test and Trace event recorder.
        If None is provided, a new recorder is created.
        """
        if recorder is None:
            from june.records.event_recording import TTEventRecorder
            recorder = TTEventRecorder()
        cls._tt_event_recorder = recorder
        return recorder

    @classmethod
    def get_tt_event_recorder(cls):
        """
        Get the registered Test and Trace event recorder.
        If none is registered, a new one is created.
        """
        if not hasattr(cls, '_tt_event_recorder'):
            return cls.set_tt_event_recorder()
        return cls._tt_event_recorder