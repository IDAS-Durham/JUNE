import csv
import datetime
from collections import defaultdict
import os
from typing import Dict, Optional, Any
import logging
import tables
import numpy as np
from pathlib import Path

from june.global_context import GlobalContext

# Configure logger
logger = logging.getLogger("event_recording")

class TTEvent:
    """
    Class to represent Test and Trace events.
    """
    def __init__(
        self, 
        event_type: str, 
        person_id: int, 
        timestamp: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a Test and Trace event.
        
        Parameters
        ----------
        event_type : str
            Type of event (e.g., 'test', 'trace', 'quarantine', 'isolation')
        person_id : int
            ID of the person involved in the event
        timestamp : float
            Time when the event occurred (days from simulation start)
        metadata : Dict[str, Any], optional
            Additional event-specific data
        """
        self.event_type = event_type
        self.person_id = person_id
        self.timestamp = timestamp
        self.metadata = metadata or {}
        self.creation_time = datetime.datetime.now()
    
    def __repr__(self):
        return (f"TTEvent(type={self.event_type}, "
                f"person_id={self.person_id}, "
                f"timestamp={self.timestamp}, "
                f"metadata={self.metadata})")


class TTEventRecorder:
    """
    Records and aggregates Test and Trace events, writing to HDF5 incrementally.
    """
    def __init__(self, output_dir="./output"):
        # Create output directory if it doesn't exist
        self.output_dir = Path(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Define the HDF5 filename with timestamp to avoid conflicts
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filename = self.output_dir / f"tt_events_{timestamp}.h5"
        
        # Total counters for different event types (counts all occurrences)
        self.total_counters = {
            'tested': 0,
            'test_positive': 0,
            'test_negative': 0,
            'traced': 0,
            'quarantined': 0,
            'isolated': 0,
        }
        
        # Detailed counters by day
        self.daily_counters = defaultdict(lambda: defaultdict(int))
        
        # Set of unique IDs for each category (counts unique people)
        self.unique_ids = {
            'tested': set(),
            'test_positive': set(),
            'test_negative': set(),
            'traced': set(),
            'quarantined': set(),
            'isolated': set(),
        }
        
        # Current status
        self.currently = {
            'quarantined': set(),  # People currently in quarantine
            'isolated': set(),     # People currently in isolation
        }
        
        # Deltas for the current time step
        self.deltas = {
            'tested': 0,
            'test_positive': 0,
            'test_negative': 0,
            'traced': 0,
            'unique_quarantined': 0,
            'total_quarantined': 0,
            'unique_isolated': 0,
            'total_isolated': 0,
        }
        
        # Timestamp for the last reset of deltas
        self.last_delta_reset = 0
        
        # Event buffer for batch processing
        self._event_buffer = []
        self._buffer_size = 100  # Adjust based on your needs
        
        # Initialize HDF5 file and tables
        self._initialize_tables()
        
        logger.info(f"TTEventRecorder initialized with HDF5 file: {self.filename}")
    
    def _initialize_tables(self):
        """Initialize the HDF5 tables for storing Test and Trace events."""
        with tables.open_file(str(self.filename), mode="a") as file:
            # Create table for events with all fields we'll need
            event_description = {
                'timestamp': tables.StringCol(itemsize=10, pos=0),  # YYYY-MM-DD format
                'event_type': tables.StringCol(itemsize=20, pos=1), 
                'person_id': tables.Int32Col(pos=2),
                'sim_time': tables.Float32Col(pos=3),  # Simulation time in days
                'infected': tables.Int8Col(pos=4),     # Boolean as int8
                'hospitalised': tables.Int8Col(pos=5), # Boolean as int8
                'age': tables.Int32Col(pos=6),         # Person's age
                'sex': tables.StringCol(itemsize=10, pos=7),  # Person's sex
                'tracer_id': tables.Int32Col(pos=8),   # ID of person who caused tracing (-1 if none)
                'contact_reason': tables.StringCol(itemsize=20, pos=9)  # Reason for contact
            }
            
            # Create the events table
            file.create_table(
                file.root, 
                'test_and_trace_events', 
                event_description, 
                "Test and Trace Events"
            )
            
            # Create a table for daily counters
            counter_description = {
                'day': tables.Int32Col(pos=0),
                'date': tables.StringCol(itemsize=10, pos=1),
                'event_type': tables.StringCol(itemsize=20, pos=2),
                'count': tables.Int32Col(pos=3)
            }
            
            # Create the daily counters table
            file.create_table(
                file.root,
                'daily_counters',
                counter_description,
                "Daily Test and Trace Counters"
            )
            
            # Create a table for current status (snapshots)
            status_description = {
                'timestamp': tables.StringCol(itemsize=10, pos=0),
                'sim_time': tables.Float32Col(pos=1),
                'status_type': tables.StringCol(itemsize=20, pos=2),
                'person_id': tables.Int32Col(pos=3)
            }
            
            # Create the status table
            file.create_table(
                file.root,
                'current_status',
                status_description,
                "Current Quarantine/Isolation Status"
            )
    
    def record_event(self, event: TTEvent):
        """
        Record a Test and Trace event.
        Updates counters and adds event to buffer for batch processing.
        
        Parameters
        ----------
        event : TTEvent
            The event to record
        """
        
        # Add event to buffer
        self._event_buffer.append(event)
        
        # Reset deltas if we're in a new time step
        current_day = int(event.timestamp)
        if current_day > self.last_delta_reset:
            self.deltas = {k: 0 for k in self.deltas}
            self.last_delta_reset = current_day
        
        # Update appropriate counter based on event type
        if event.event_type == 'test':
            self.total_counters['tested'] += 1
            self.deltas['tested'] += 1
            self.unique_ids['tested'].add(event.person_id)
            self.daily_counters[current_day]['tested'] += 1
            
        elif event.event_type == 'test_positive':
            self.total_counters['test_positive'] += 1
            self.deltas['test_positive'] += 1
            self.unique_ids['test_positive'].add(event.person_id)
            self.daily_counters[current_day]['test_positive'] += 1
            
        elif event.event_type == 'test_negative':
            self.total_counters['test_negative'] += 1
            self.deltas['test_negative'] += 1
            self.unique_ids['test_negative'].add(event.person_id)
            self.daily_counters[current_day]['test_negative'] += 1
            
        elif event.event_type == 'trace':
            self.total_counters['traced'] += 1
            self.deltas['traced'] += 1
            self.unique_ids['traced'].add(event.person_id)
            self.daily_counters[current_day]['traced'] += 1
            
        elif event.event_type == 'quarantine_start':
            # Total quarantine events (all occurrences)
            self.total_counters['quarantined'] += 1
            self.deltas['total_quarantined'] += 1
            self.daily_counters[current_day]['quarantined'] += 1
            
            # Unique quarantined people
            if event.person_id not in self.unique_ids['quarantined']:
                self.unique_ids['quarantined'].add(event.person_id)
                self.deltas['unique_quarantined'] += 1
            
            # Add to currently quarantined set
            self.currently['quarantined'].add(event.person_id)
            
        elif event.event_type == 'quarantine_end':
            # Remove from currently quarantined set
            if event.person_id in self.currently['quarantined']:
                self.currently['quarantined'].remove(event.person_id)
            
        elif event.event_type == 'isolation_start':
            # Total isolation events (all occurrences)
            self.total_counters['isolated'] += 1
            self.deltas['total_isolated'] += 1
            self.daily_counters[current_day]['isolated'] += 1
            
            # Unique isolated people
            if event.person_id not in self.unique_ids['isolated']:
                self.unique_ids['isolated'].add(event.person_id)
                self.deltas['unique_isolated'] += 1
            
            # Add to currently isolated set
            self.currently['isolated'].add(event.person_id)
            
        elif event.event_type == 'isolation_end':
            # Remove from currently isolated set
            if event.person_id in self.currently['isolated']:
                self.currently['isolated'].remove(event.person_id)
        
        # Process buffer if it reaches the threshold
        if len(self._event_buffer) >= self._buffer_size:
            self._process_event_buffer()
            
        logger.debug(f"Recorded event: {event}")

    
    def _process_event_buffer(self):
        """Process and write the current event buffer to HDF5 file."""
        if not self._event_buffer:
            return
            
        with tables.open_file(str(self.filename), mode="a") as file:
            # Get the events table
            events_table = file.root.test_and_trace_events
            
            # Create a numpy record array for the events
            event_data = []
            for event in self._event_buffer:
                # Convert simulation time to date string
                simulator = GlobalContext.get_simulator()
                sim_timer = simulator.timer if simulator else None
                
                if sim_timer:
                    days_whole = int(event.timestamp)
                    sim_date = sim_timer.initial_date + datetime.timedelta(days=days_whole)
                    date_str = sim_date.strftime("%Y-%m-%d")
                else:
                    # Fallback if simulator not available
                    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
                
                # Get metadata values with defaults
                infected = event.metadata.get('infected', False)
                hospitalised = event.metadata.get('hospitalised', False)
                age = event.metadata.get('age', -1)  # Default to -1 if age not available
                sex = event.metadata.get('sex', 'unknown')  # Default to 'unknown' if sex not available
                tracer_id = event.metadata.get('tracer_id', -1)  # Default to -1 if no tracer
                contact_reason = event.metadata.get('contact_reason', 'unknown')  # Default reason
                
                # Add to data array
                event_data.append((
                    date_str.encode('utf-8'),  # Convert to bytes for HDF5
                    event.event_type.encode('utf-8'),
                    event.person_id,
                    float(event.timestamp),
                    1 if infected else 0,
                    1 if hospitalised else 0,
                    age,
                    sex.encode('utf-8'),  # Convert to bytes for HDF5
                    tracer_id,
                    contact_reason.encode('utf-8')  # Convert to bytes for HDF5
                ))
            
            # Convert to numpy record array and append to table
            if event_data:
                data = np.array(
                    event_data,
                    dtype=[
                        ('timestamp', 'S10'),
                        ('event_type', 'S20'),
                        ('person_id', np.int32),
                        ('sim_time', np.float32),
                        ('infected', np.int8),
                        ('hospitalised', np.int8),
                        ('age', np.int32),
                        ('sex', 'S10'),
                        ('tracer_id', np.int32),
                        ('contact_reason', 'S20')
                    ]
                )
                
                events_table.append(data)
                events_table.flush()
            
            # Clear the buffer after successful write
            self._event_buffer = []
            
    
    def time_step(self, timestamp: float):
        """
        Process events for the current time step.
        Writes daily counters and current status to HDF5.
        
        Parameters
        ----------
        timestamp : float
            Current simulation timestamp (days from start)
        """
        
        # First process any events in the buffer
        self._process_event_buffer()
        
        # Get simulator and format timestamp
        simulator = GlobalContext.get_simulator()
        sim_timer = simulator.timer if simulator else None
        
        if sim_timer:
            current_day = int(timestamp)
            sim_date = sim_timer.initial_date + datetime.timedelta(days=current_day)
            date_str = sim_date.strftime("%Y-%m-%d")
        
        with tables.open_file(str(self.filename), mode="a") as file:
            # Update daily counters table
            daily_table = file.root.daily_counters
            daily_data = []
            
            # Get counts from daily_counters for current day
            if current_day in self.daily_counters:
                # Find rows to delete (matching current day)
                condition = f'(day == {current_day})'
                
                # Get the indices of rows to delete
                indices = daily_table.get_where_list(condition)
                if len(indices) > 0:
                    # Remove rows using start and stop indices
                    daily_table.remove_rows(indices[0], indices[-1]+1)
                    daily_table.flush()

                # Prepare new data
                for event_type, count in self.daily_counters[current_day].items():
                    daily_data.append((
                        current_day,
                        date_str.encode('utf-8'),
                        event_type.encode('utf-8'),
                        count
                    ))
                
                # Convert to numpy array and append
                if daily_data:
                    data = np.array(
                        daily_data,
                        dtype=[
                            ('day', np.int32),
                            ('date', 'S10'),
                            ('event_type', 'S20'),
                            ('count', np.int32)
                        ]
                    )
                    
                    # Add new data
                    daily_table.append(data)
                    daily_table.flush()
            
            # Update current status table (people in quarantine/isolation)
            status_table = file.root.current_status
            status_data = []
            
            # Delete existing status data for this timestamp
            condition = f'(sim_time == {float(timestamp)})'

            # Get the indices of rows to delete
            indices = status_table.get_where_list(condition)
            if len(indices) > 0:
                # Remove rows using start and stop indices
                status_table.remove_rows(indices[0], indices[-1]+1)
                status_table.flush()

            # Add current quarantine status
            for person_id in self.currently['quarantined']:
                status_data.append((
                    date_str.encode('utf-8'),
                    float(timestamp),
                    'quarantined'.encode('utf-8'),
                    person_id
                ))
            
            # Add current isolation status
            for person_id in self.currently['isolated']:
                status_data.append((
                    date_str.encode('utf-8'),
                    float(timestamp),
                    'isolated'.encode('utf-8'),
                    person_id
                ))
            
            # Convert to numpy array and append
            if status_data:
                data = np.array(
                    status_data,
                    dtype=[
                        ('timestamp', 'S10'),
                        ('sim_time', np.float32),
                        ('status_type', 'S20'),
                        ('person_id', np.int32)
                    ]
                )
                
                status_table.append(data)
                status_table.flush()
        
        logger.info(f"Processed time step data for day {current_day}")

    def get_stats(self):
        """
        Return current statistics.
        
        Returns
        -------
        Dict
            Dictionary with various statistics
        """
        # Process any pending events first
        self._process_event_buffer()
        
        return {
            'total_events': sum(len(self._get_events_for_type(event_type)) for event_type in 
                             ['test', 'test_positive', 'test_negative', 'trace', 
                              'quarantine_start', 'quarantine_end', 'isolation_start', 'isolation_end']),
            'total_counters': self.total_counters,
            'unique_counts': {k: len(v) for k, v in self.unique_ids.items()},
            'daily_counters': dict(self.daily_counters),
            'currently': {k: len(v) for k, v in self.currently.items()},
            'deltas': self.deltas
        }
    
    def _get_events_for_type(self, event_type):
        """
        Retrieve events of a specific type from HDF5.
        
        Parameters
        ----------
        event_type : str
            Type of events to retrieve
            
        Returns
        -------
        List
            List of matching events
        """
        
        results = []
        with tables.open_file(str(self.filename), mode="r") as file:
            if hasattr(file.root, 'test_and_trace_events'):
                # Query events table for this event type
                for row in file.root.test_and_trace_events.where(f'event_type == b"{event_type}"'):
                    results.append(row)
        return results

        
    def get_daily_stats(self, day: int):
        """
        Return statistics for a specific day.
        
        Parameters
        ----------
        day : int
            Day from simulation start
            
        Returns
        -------
        Dict
            Dictionary with statistics for the specified day
        """
        return dict(self.daily_counters[day])
    
    def export_data(self, output_dir="./temp_tt_output", export_csv=True, export_hdf5=True):
        """
        Export the recorded data to CSV and/or HDF5 files.
        
        Parameters
        ----------
        output_dir : str
            Directory where output files will be saved
        export_csv : bool
            Whether to export CSV files
        export_hdf5 : bool
            Whether to export HDF5 file
            
        Returns
        -------
        dict
            Paths to the exported files
        """
        # Process any remaining events in the buffer
        self._process_event_buffer()
        
        from june.records.event_recording import export_tt_data
        return export_tt_data(
            recorder=self,
            output_dir=output_dir,
            export_csv=export_csv,
            export_hdf5=export_hdf5
        )
    
def emit_test_event(person, timestamp, result=None):
    """
    Emit a test event.
    
    Parameters
    ----------
    person : Person
        The person being tested
    timestamp : float
        The time of the event
    result : str, optional
        Test result if available
    """
    metadata = {
        'age': person.age,
        'sex': person.sex,
        'infected': person.infected if hasattr(person, 'infected') else False,
        'hospitalised': person.hospitalised if hasattr(person, 'hospitalised') else False,
    }
    
    # Add tracer information if person was contacted for testing
    if (hasattr(person, 'test_and_trace') and person.test_and_trace is not None and 
        hasattr(person.test_and_trace, 'tracer_id') and person.test_and_trace.tracer_id is not None):
        metadata['tracer_id'] = person.test_and_trace.tracer_id
        metadata['contact_reason'] = getattr(person.test_and_trace, 'contact_reason', 'unknown')
    
    recorder = GlobalContext.get_tt_event_recorder()
    
    # Result-specific events
    if result is not None:
        metadata['result'] = result
        result_type = result.lower()  # Convert to lowercase for consistency
        result_event = TTEvent(f'test_{result_type}', person.id, timestamp, metadata)
        recorder.record_event(result_event)
    else:
        # Basic test event
        event = TTEvent('test', person.id, timestamp, metadata)
        recorder.record_event(event)

def emit_trace_event(person_id, total_mates, timestamp):
    """
    Emit a trace event.
    
    Parameters
    ----------
    person : Person
        The person whose contacts are being traced
    contact_ids : List[int]
        IDs of the contacts being traced
    timestamp : float
        The time of the event
    """
    metadata = {
        'contact_count': total_mates,
    }
    
    event = TTEvent('trace', person_id, timestamp, metadata)
    recorder = GlobalContext.get_tt_event_recorder()
    recorder.record_event(event)

def emit_quarantine_event(person, timestamp, is_start=True):
    """
    Emit a quarantine event.
    
    Parameters
    ----------
    person : Person
        The person quarantining
    timestamp : float
        The time of the event
    is_start : bool
        Whether this is the start or end of quarantine
    """

    metadata = {
        'age': person.age,
        'sex': person.sex,
        'infected': person.infected if hasattr(person, 'infected') else False
    }

    event_type = 'quarantine_start' if is_start else 'quarantine_end'
    
    event = TTEvent(event_type, person.id, timestamp, metadata)
    recorder = GlobalContext.get_tt_event_recorder()
    recorder.record_event(event)

def emit_isolation_event(person, timestamp, is_start=True):
    """
    Emit an isolation event.
    
    Parameters
    ----------
    person : Person
        The person isolating
    timestamp : float
        The time of the event
    is_start : bool
        Whether this is the start or end of isolation
    """
    metadata = {
        'age': person.age,
        'sex': person.sex,
        'infected': person.infected if hasattr(person, 'infected') else False
    }

    event_type = 'isolation_start' if is_start else 'isolation_end'
    
    event = TTEvent(event_type, person.id, timestamp, metadata)
    recorder = GlobalContext.get_tt_event_recorder()
    recorder.record_event(event)

def are_test_and_trace_policies_active():
    """
    Check if test and trace policies are active based on both:
    1. Configuration setting
    2. Active policies in the current date
    
    Returns:
    --------
    bool
        True if test and trace is enabled and active, False otherwise
    """
    
    # Check if enabled in config
    from june.global_context import GlobalContext
    simulator = GlobalContext.get_simulator()
    if not hasattr(simulator, 'test_and_trace_enabled') or not simulator.test_and_trace_enabled:
        return False
        
    # If enabled in config, check if any policies are configured for the current date
    date = simulator.timer.date
    policies = simulator.activity_manager.policies.medical_care_policies
    active_policies = policies.get_active(date)
    
    # Check if there are any actual testing or tracing policies active
    from june.policy.medical_care_policies import Testing, Tracing

    has_testing = any(isinstance(policy, Testing) for policy in active_policies.policies)
    has_tracing = any(isinstance(policy, Tracing) for policy in active_policies.policies)
    
    return has_testing or has_tracing

def export_tt_data(recorder, output_dir="./output", export_csv=True, export_hdf5=True):
    """
    Export Test and Trace data to CSV and/or HDF5 files.
    Optimized to avoid recreating HDF5 data during export.
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    from june.mpi_wrapper import mpi_rank, mpi_available, mpi_size
    
    if mpi_available and mpi_size > 1:
        simulation_id = f"sim_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_rank{mpi_rank}"
    else:
        simulation_id = f"sim_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Process any remaining events in the buffer before export
    if hasattr(recorder, '_process_event_buffer') and callable(getattr(recorder, '_process_event_buffer')):
        recorder._process_event_buffer()
    
    # Get statistics from recorder
    stats = recorder.get_stats()
    total_counters = stats['total_counters']
    unique_counts = stats['unique_counts']
    daily_data = stats['daily_counters']
    currently = stats['currently']
    
    # Get simulator and timer for metadata
    simulator = GlobalContext.get_simulator()
    timer = simulator.timer
    days_simulated = timer.total_days
    time_now = timer.now
    
    # Helper function to format date as string
    def format_date(date_obj):
        if isinstance(date_obj, datetime.datetime):
            return date_obj.strftime('%Y-%m-%d %H:%M:%S')
        else:
            return date_obj.strftime('%Y-%m-%d')
    
    # Prepare summary data
    summary_data = {
        'simulation_start_date': format_date(timer.initial_date),
        'days_simulated': days_simulated,
        'simulation_time': str(time_now),
        'total_tests': total_counters['tested'],
        'unique_tested': unique_counts['tested'],
        'positive_tests': total_counters.get('test_positive', 0),
        'negative_tests': total_counters.get('test_negative', 0),
        'people_traced': unique_counts['traced'],
        'total_quarantined': total_counters['quarantined'],
        'unique_quarantined': unique_counts['quarantined'],
        'total_isolated': total_counters['isolated'],
        'unique_isolated': unique_counts['isolated'],
        'currently_quarantined': currently['quarantined'],
        'currently_isolated': currently['isolated'],
    }
    
    # Calculate positive rate
    positive_tests = total_counters.get('test_positive', 0)
    negative_tests = total_counters.get('test_negative', 0)
    total_tests_with_results = positive_tests + negative_tests
    summary_data['positive_rate'] = positive_tests / max(total_tests_with_results, 1) if total_tests_with_results > 0 else 0
    
    # Prepare daily data for CSV
    daily_records = []
    for day in range(int(days_simulated)):
        # Get simulation date for this day (just the date part)
        sim_date = timer.initial_date + datetime.timedelta(days=day)
        sim_date_str = format_date(sim_date)
        
        day_data = daily_data.get(day, {})
        record = {
            'date': sim_date_str,  # Use simulation date
            'positive_tests': day_data.get('test_positive', 0),
            'negative_tests': day_data.get('test_negative', 0),
            'quarantining': day_data.get('quarantined', 0),
            'isolating': day_data.get('isolated', 0),
        }
        daily_records.append(record)
    
    # Prepare cumulative data
    cumulative_records = []
    cum_tests = 0
    cum_pos_tests = 0
    cum_neg_tests = 0
    cum_traced = 0
    cum_quarantined = 0
    cum_isolated = 0
    
    for day in range(int(days_simulated)):
        sim_date = timer.initial_date + datetime.timedelta(days=day)
        sim_date_str = format_date(sim_date)
        
        day_data = daily_data.get(day, {})
        
        # Update cumulative counts
        cum_tests += day_data.get('tested', 0)
        cum_pos_tests += day_data.get('test_positive', 0)
        cum_neg_tests += day_data.get('test_negative', 0)
        cum_traced += day_data.get('traced', 0)
        cum_quarantined += day_data.get('quarantined', 0)
        cum_isolated += day_data.get('isolated', 0)
        
        record = {
            'date': sim_date_str,
            'cumulative_positive_tests': cum_pos_tests,
            'cumulative_negative_tests': cum_neg_tests,
            'cumulative_quarantined': cum_quarantined,
            'cumulative_isolated': cum_isolated,
        }
        cumulative_records.append(record)
    
    # Export files
    daily_file = None
    cumulative_file = None
    hdf5_file = None
    
    # Export CSV files if requested
    if export_csv:
        # Save daily data
        daily_file = os.path.join(output_dir, f"{simulation_id}_daily.csv")
        with open(daily_file, 'w', newline='') as f:
            if daily_records:
                writer = csv.DictWriter(f, fieldnames=daily_records[0].keys())
                writer.writeheader()
                writer.writerows(daily_records)
        
        # Save cumulative data
        cumulative_file = os.path.join(output_dir, f"{simulation_id}_cumulative.csv")
        with open(cumulative_file, 'w', newline='') as f:
            if cumulative_records:
                writer = csv.DictWriter(f, fieldnames=cumulative_records[0].keys())
                writer.writeheader()
                writer.writerows(cumulative_records)
                
        print(f"CSV data exported to {output_dir}")
    
    # Export HDF5 file if requested (using optimized approach - just copy the existing one)
    if export_hdf5 and hasattr(recorder, 'filename') and os.path.exists(recorder.filename):
        hdf5_file = os.path.join(output_dir, f"{simulation_id}.h5")
        
        # Update metadata in the original file before copying
        with tables.open_file(str(recorder.filename), mode="a") as source_file:
            # Create or get metadata group
            if not hasattr(source_file.root, 'metadata'):
                metadata = source_file.create_group(source_file.root, 'metadata', 'Simulation Metadata')
            
            # Add simulation metadata as attributes to the root
            for key, value in summary_data.items():
                if isinstance(value, (int, float, str)):
                    source_file.root._v_attrs[key] = value
                    
            # Add additional metadata
            source_file.root._v_attrs['export_timestamp'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
        import shutil
        shutil.copy2(recorder.filename, hdf5_file)
        print(f"HDF5 data exported to {hdf5_file} (optimized copy)")

    
    return {
        'daily_file': daily_file,
        'cumulative_file': cumulative_file,
        'hdf5_file': hdf5_file
    }

def export_simulation_results(output_dir="./output"):
    """
    Export all simulation results at the end of a run and cleanup temporary files.
    In MPI mode, each rank writes to its own files within a test_and_trace folder.
    
    Parameters
    ----------
    output_dir : str
        Directory where output files will be saved
    """
    from june.mpi_wrapper import mpi_rank, mpi_available, mpi_size
    import shutil
    
    recorder = GlobalContext.get_tt_event_recorder()
    
    # Create test_and_trace directory structure
    base_output_dir = os.path.join(output_dir, "test_and_trace")
    
    # Create rank-specific output directory path within test_and_trace
    if mpi_available and mpi_size > 1:
        rank_specific_dir = os.path.join(base_output_dir, f"rank_{mpi_rank}")
    else:
        rank_specific_dir = base_output_dir
    
    # Create the directory
    os.makedirs(rank_specific_dir, exist_ok=True)
    
    # Get the current timestamp for final processing
    current_timestamp = GlobalContext.get_simulator().timer.now
    
    # Ensure all events are processed and saved before the final export
    recorder.time_step(current_timestamp)
    
    # Store the temp directory path before export (in case it gets modified)
    temp_output_dir = str(recorder.output_dir)
    
    # Export data to files (each rank writes to its own directory)
    exported_files = recorder.export_data(
        output_dir=rank_specific_dir,
        export_csv=True,
        export_hdf5=True
    )
    
    # MPI Barrier - wait for all ranks to complete export before any cleanup
    if mpi_available and mpi_size > 1:
        try:
            from mpi4py import MPI
            MPI.COMM_WORLD.Barrier()
            logger.info(f"Rank {mpi_rank}: Export completed, synchronized with other ranks")
        except ImportError:
            logger.warning("mpi4py not available, proceeding without synchronization")
        except Exception as e:
            logger.warning(f"MPI barrier failed: {e}, proceeding with cleanup")
    
    # Verify export was successful before cleanup
    export_successful = all(
        file_path and os.path.exists(file_path) 
        for file_path in exported_files.values() 
        if file_path is not None
    )
    
    # Now cleanup - only after all ranks have finished
    if export_successful:
        # Only rank 0 does the cleanup to avoid race conditions
        if not mpi_available or mpi_rank == 0:
            if os.path.exists(temp_output_dir):
                try:
                    shutil.rmtree(temp_output_dir)
                    logger.info(f"Cleaned up temporary directory: {temp_output_dir}")
                    print(f"✓ Cleaned up temporary directory: {temp_output_dir}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup {temp_output_dir}: {e}")
                    print(f"⚠ Warning: Failed to cleanup {temp_output_dir}: {e}")
        else:
            logger.info(f"Rank {mpi_rank}: Cleanup delegated to rank 0")
    else:
        if not mpi_available or mpi_rank == 0:
            logger.warning("Export verification failed - keeping temporary files for debugging")
            print("⚠ Warning: Export verification failed - keeping temporary files for debugging")
    
    # Print export information (optionally only on rank 0 for cleaner output)
    if not mpi_available or mpi_rank == 0:
        print(f"\nExported test and trace data:")
        if mpi_available and mpi_size > 1:
            print(f"- Base directory: {base_output_dir}")
            print(f"- Rank-specific folders: rank_0, rank_1, ..., rank_{mpi_size-1}")
        else:
            print(f"- Directory: {rank_specific_dir}")
        
        print(f"\nFiles created for rank {mpi_rank}:")
        for file_type, file_path in exported_files.items():
            if file_path:
                print(f"- {file_type}: {file_path}")

def print_tt_simulation_report(days_simulated=20):
    """
    Print a comprehensive report of Test and Trace statistics.
    
    Parameters
    ----------
    days_simulated : int
        Number of days the simulation ran
    """
    import datetime
    from colorama import init, Fore, Style, Back
    
    # Initialize colorama
    init()
    
    # Get the recorder
    recorder = GlobalContext.get_tt_event_recorder()
    
    # Get overall statistics
    stats = recorder.get_stats()
    total_counters = stats['total_counters']
    unique_counts = stats['unique_counts']
    daily_data = stats['daily_counters']
    currently = stats['currently']
    deltas = stats['deltas']
    
    # Get simulator for time information
    simulator = GlobalContext.get_simulator()
    time = simulator.timer.now
    
    # Calculate derived statistics with error checking
    avg_tests_per_day = total_counters['tested'] / max(days_simulated, 1) if days_simulated > 0 else 0
    avg_tests_per_person = total_counters['tested'] / max(unique_counts['tested'], 1) if unique_counts['tested'] > 0 else 0
    
    # Calculate positive rate based on actual positive tests with error checking
    positive_tests = total_counters.get('test_positive', 0)
    negative_tests = total_counters.get('test_negative', 0)
    total_tests_with_results = (positive_tests + negative_tests)
    positive_rate = positive_tests / max(total_tests_with_results, 1) if total_tests_with_results > 0 else 0
    
    # Calculate isolation rate with error checking
    isolation_rate = 0
    if unique_counts['tested'] > 0:
        isolation_rate = (unique_counts['isolated'] / unique_counts['tested']) * 100
    
    # Calculate trace efficiency with error checking
    trace_efficiency = 0
    if unique_counts['tested'] > 0:
        trace_efficiency = unique_counts['traced'] / unique_counts['tested']
    
    # Calculate isolations per day with error checking
    isolations_per_day = 0
    if days_simulated > 0:
        isolations_per_day = total_counters['isolated'] / days_simulated
    
    # Calculate false positives and negatives by reading from HDF5
    false_positives = 0
    false_negatives = 0
    
 
    # Access events from HDF5 file instead of in-memory list
    if hasattr(recorder, 'filename') and os.path.exists(recorder.filename):
        with tables.open_file(str(recorder.filename), mode="r") as file:
            if hasattr(file.root, 'test_and_trace_events'):
                # Count false positives
                for row in file.root.test_and_trace_events.where('event_type == b"test_positive"'):
                    if row['infected'] == 0:  # Not infected but positive test
                        false_positives += 1
                
                # Count false negatives
                for row in file.root.test_and_trace_events.where('event_type == b"test_negative"'):
                    if row['infected'] == 1:  # Infected but negative test
                        false_negatives += 1
    
    # Calculate rates with error checking
    fp_rate = false_positives / max(total_counters['test_positive'], 1) if total_counters['test_positive'] > 0 else 0
    fn_rate = false_negatives / max(total_counters['test_negative'], 1) if total_counters['test_negative'] > 0 else 0
    
    # Print header
    print("\n" + "=" * 80)
    print(f"{Back.BLUE}{Fore.WHITE} TEST AND TRACE SIMULATION REPORT {Style.RESET_ALL}")
    print(f"{Fore.BLUE}Simulation duration: {days_simulated} days{Style.RESET_ALL}")
    print(f"{Fore.BLUE}Simulation time: {time} {Style.RESET_ALL}")
    print(f"{Fore.BLUE}Report generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}")
    print("=" * 80)
    
    print(f"\n{Fore.GREEN}▓▓▓ ALL-TIME SUMMARY ▓▓▓{Style.RESET_ALL}")
     # Testing statistics
    print(f"{Fore.CYAN}┌───────────────────────┬───────────────────────┐{Style.RESET_ALL}")
    print(f"{Fore.CYAN}│ {Fore.WHITE}Testing{Fore.CYAN}               │ {Fore.WHITE}Tracing & Isolation{Fore.CYAN}    │{Style.RESET_ALL}")
    print(f"{Fore.CYAN}├───────────────────────┼───────────────────────┤{Style.RESET_ALL}")
    
    # Helper function to format values with deltas
    def format_with_delta(value, delta, width=8):
        """Format a value with its delta in parentheses"""
        if delta > 0:
            delta_str = f" (+{delta})"
            # If the formatted string gets too long, use shorter formats
            if len(f"{value:,}{delta_str}") > width + 10:
                if value >= 1000000:  # Millions
                    return f"{value/1000000:.1f}M{delta_str}"
                elif value >= 1000:  # Thousands
                    return f"{value/1000:.1f}K{delta_str}"
                else:
                    return f"{value}{delta_str}"
            return f"{value:,}{delta_str}"
        return f"{value:,}"
    
    print(f"{Fore.CYAN}│ {Fore.WHITE}Total tests:{Fore.YELLOW} {format_with_delta(total_counters['tested'], deltas['tested'])}{Fore.CYAN}      │ {Fore.WHITE}People traced:{Fore.YELLOW} {format_with_delta(unique_counts['traced'], deltas['traced'])}{Fore.CYAN}     │{Style.RESET_ALL}")
    print(f"{Fore.CYAN}│ {Fore.WHITE}Unique people:{Fore.YELLOW} {unique_counts['tested']:,}{Fore.CYAN}   │ {Fore.WHITE}                  {Fore.CYAN}     │{Style.RESET_ALL}")
    print(f"{Fore.CYAN}│ {Fore.WHITE}Positive tests:{Fore.YELLOW} {format_with_delta(total_counters['test_positive'], deltas['test_positive'])}{Fore.CYAN}   │ {Fore.WHITE}Contacts per case:{Fore.YELLOW} {trace_efficiency:.2f}{Fore.CYAN}   │{Style.RESET_ALL}")
    print(f"{Fore.CYAN}│ {Fore.WHITE}Negative tests:{Fore.YELLOW} {format_with_delta(total_counters['test_negative'], deltas['test_negative'])}{Fore.CYAN}   │ {Fore.WHITE}Isolation rate:{Fore.YELLOW} {isolation_rate:.1f}%{Fore.CYAN} │{Style.RESET_ALL}")
    print(f"{Fore.CYAN}│ {Fore.WHITE}Positive rate:{Fore.YELLOW} {positive_rate*100:.1f}%{Fore.CYAN}   │ {Fore.WHITE}                  {Fore.CYAN}     │{Style.RESET_ALL}")
    print(f"{Fore.CYAN}│ {Fore.WHITE}Avg tests/day:{Fore.YELLOW} {avg_tests_per_day:.1f}{Fore.CYAN}   │ {Fore.WHITE}                  {Fore.CYAN}     │{Style.RESET_ALL}")
    print(f"{Fore.CYAN}│ {Fore.WHITE}Avg tests/person:{Fore.YELLOW} {avg_tests_per_person:.2f}{Fore.CYAN}│ {Fore.WHITE}                  {Fore.CYAN}     │{Style.RESET_ALL}")
    print(f"{Fore.CYAN}└───────────────────────┴───────────────────────┘{Style.RESET_ALL}")
    
    # Quarantine and Isolation details
    print(f"\n{Fore.GREEN}▓▓▓ QUARANTINE & ISOLATION DETAILS ▓▓▓{Style.RESET_ALL}")
    print(f"{Fore.CYAN}┌────────────────────────────┬───────────┬───────────┐{Style.RESET_ALL}")
    print(f"{Fore.CYAN}│ {Fore.WHITE}Metric{Fore.CYAN}                     │ {Fore.WHITE}Total{Fore.CYAN}     │ {Fore.WHITE}Unique{Fore.CYAN}    │{Style.RESET_ALL}")
    print(f"{Fore.CYAN}├────────────────────────────┼───────────┼───────────┤{Style.RESET_ALL}")
    print(f"{Fore.CYAN}│ {Fore.WHITE}Quarantined{Fore.CYAN}                │ {Fore.YELLOW}{format_with_delta(total_counters['quarantined'], deltas['total_quarantined'])}{Fore.CYAN} │ {Fore.YELLOW}{format_with_delta(unique_counts['quarantined'], deltas['unique_quarantined'])}{Fore.CYAN} │{Style.RESET_ALL}")
    print(f"{Fore.CYAN}│ {Fore.WHITE}Isolated{Fore.CYAN}                   │ {Fore.YELLOW}{format_with_delta(total_counters['isolated'], deltas['total_isolated'])}{Fore.CYAN} │ {Fore.YELLOW}{format_with_delta(unique_counts['isolated'], deltas['unique_isolated'])}{Fore.CYAN} │{Style.RESET_ALL}")
    print(f"{Fore.CYAN}└────────────────────────────┴───────────┴───────────┘{Style.RESET_ALL}")
    
    # Current status
    print(f"\n{Fore.GREEN}▓▓▓ CURRENT STATUS ▓▓▓{Style.RESET_ALL}")
    print(f"{Fore.CYAN}┌─────────────────────────────┬───────────┐{Style.RESET_ALL}")
    print(f"{Fore.CYAN}│ {Fore.WHITE}Metric{Fore.CYAN}                    │ {Fore.WHITE}Count{Fore.CYAN}     │{Style.RESET_ALL}")
    print(f"{Fore.CYAN}├─────────────────────────────┼───────────┤{Style.RESET_ALL}")
    print(f"{Fore.CYAN}│ {Fore.WHITE}Currently quarantining{Fore.CYAN}      │ {Fore.YELLOW}{currently['quarantined']:,}{Fore.CYAN}     │{Style.RESET_ALL}")
    print(f"{Fore.CYAN}│ {Fore.WHITE}Currently isolating{Fore.CYAN}        │ {Fore.YELLOW}{currently['isolated']:,}{Fore.CYAN}     │{Style.RESET_ALL}")
    print(f"{Fore.CYAN}│ {Fore.WHITE}Total restricted{Fore.CYAN}           │ {Fore.YELLOW}{currently['quarantined'] + currently['isolated']:,}{Fore.CYAN}     │{Style.RESET_ALL}")
    print(f"{Fore.CYAN}└─────────────────────────────┴───────────┘{Style.RESET_ALL}")
    
    # Only print test results analysis if we have test results
    if total_tests_with_results > 0:
        # Print extended test result analysis
        print(f"\n{Fore.GREEN}▓▓▓ TEST RESULTS ANALYSIS ▓▓▓{Style.RESET_ALL}")
        
        false_positives = 0
        false_negatives = 0

        # Access events from HDF5 file instead of in-memory list
        if hasattr(recorder, 'filename') and os.path.exists(recorder.filename):
            with tables.open_file(str(recorder.filename), mode="r") as file:
                if hasattr(file.root, 'test_and_trace_events'):
                    # Count false positives
                    for row in file.root.test_and_trace_events.where('event_type == b"test_positive"'):
                        if row['infected'] == 0:  # Not infected but positive test
                            false_positives += 1
                    
                    # Count false negatives
                    for row in file.root.test_and_trace_events.where('event_type == b"test_negative"'):
                        if row['infected'] == 1:  # Infected but negative test
                            false_negatives += 1

        
        # Calculate rates with error checking
        fp_rate = false_positives / max(total_counters['test_positive'], 1) if total_counters['test_positive'] > 0 else 0
        fn_rate = false_negatives / max(total_counters['test_negative'], 1) if total_counters['test_negative'] > 0 else 0
        
        print(f"{Fore.CYAN}┌─────────────────────────────┬───────────┐{Style.RESET_ALL}")
        print(f"{Fore.CYAN}│ {Fore.WHITE}Metric{Fore.CYAN}                    │ {Fore.WHITE}Value{Fore.CYAN}     │{Style.RESET_ALL}")
        print(f"{Fore.CYAN}├─────────────────────────────┼───────────┤{Style.RESET_ALL}")
        print(f"{Fore.CYAN}│ {Fore.WHITE}Total positive tests{Fore.CYAN}        │ {Fore.YELLOW}{total_counters['test_positive']:,}{Fore.CYAN}     │{Style.RESET_ALL}")
        print(f"{Fore.CYAN}│ {Fore.WHITE}Total negative tests{Fore.CYAN}        │ {Fore.YELLOW}{total_counters['test_negative']:,}{Fore.CYAN}     │{Style.RESET_ALL}")
        print(f"{Fore.CYAN}│ {Fore.WHITE}Positive test rate{Fore.CYAN}          │ {Fore.YELLOW}{positive_rate*100:.1f}%{Fore.CYAN}    │{Style.RESET_ALL}")
        print(f"{Fore.CYAN}│ {Fore.WHITE}False positive count{Fore.CYAN}        │ {Fore.YELLOW}{false_positives:,}{Fore.CYAN}     │{Style.RESET_ALL}")
        print(f"{Fore.CYAN}│ {Fore.WHITE}False positive rate{Fore.CYAN}         │ {Fore.YELLOW}{fp_rate*100:.1f}%{Fore.CYAN}    │{Style.RESET_ALL}")
        print(f"{Fore.CYAN}│ {Fore.WHITE}False negative count{Fore.CYAN}        │ {Fore.YELLOW}{false_negatives:,}{Fore.CYAN}     │{Style.RESET_ALL}")
        print(f"{Fore.CYAN}│ {Fore.WHITE}False negative rate{Fore.CYAN}         │ {Fore.YELLOW}{fn_rate*100:.1f}%{Fore.CYAN}    │{Style.RESET_ALL}")
        print(f"{Fore.CYAN}└─────────────────────────────┴───────────┘{Style.RESET_ALL}")
    
    print("\n" + "=" * 80)