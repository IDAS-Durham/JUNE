import logging
import traceback

from june.global_context import GlobalContext

logger = logging.getLogger("test_and_trace")

class TestAndTrace:
    """
    Class to track testing and contact tracing information for a person.
    This separates testing and tracing from the infection mechanics.
    """
    def __init__(self):
        self.disease_config = GlobalContext.get_disease_config()

        # Contact tracing information
        self.notification_time = None
        self.scheduled_test_time = None
        self.contacts_traced = False

        # Testing information
        self.time_of_testing = None
        self.time_of_result = None
        self.pending_test_result = None
        self.test_result = None

        #Event flags
        self.emited_quarantine_start_event = None 
        self.emited_quarantine_end_event = None 

        #Isolation information
        self.isolation_start_time = None
        self.isolation_end_time = None
        
        # Contact tracing source information
        self.tracer_id = None  # ID of the person who caused this person to be traced
        self.contact_reason = None  # Reason for contact (e.g., 'housemate', 'colleague', 'leisure')
        
        self.debug = False
        if self.debug:
            print(f"TestAndTrace.__init__ called ")
            print(f"Successfully created TestAndTrace object with scheduled_test_time={self.scheduled_test_time}")

        
    def __repr__(self):
        return (f"TestAndTrace(status={self.status}, "
                f"notified_at={self.notification_time}, "
                f"scheduled_test={self.scheduled_test_time}, "
                f"test_result={self.test_result})")









