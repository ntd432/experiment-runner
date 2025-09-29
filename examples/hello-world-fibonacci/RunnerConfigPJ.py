import subprocess
import shlex
import pandas as pd
import time
import os, signal
from datetime import datetime
from EventManager.Models.RunnerEvents import RunnerEvents
from EventManager.EventSubscriptionController import EventSubscriptionController
from ConfigValidator.Config.Models.RunTableModel import RunTableModel
from ConfigValidator.Config.Models.FactorModel import FactorModel
from ConfigValidator.Config.Models.RunnerContext import RunnerContext
from ConfigValidator.Config.Models.OperationType import OperationType
from ProgressManager.Output.OutputProcedure import OutputProcedure as output

from typing import Dict, List, Any, Optional
from pathlib import Path
from os.path import dirname, realpath


class RunnerConfig:
    ROOT_DIR = Path(dirname(realpath(__file__)))
    timestamp_start  = None
    timestamp_end  = None

    # ================================ USER SPECIFIC CONFIG ================================
    """The name of the experiment."""
    name:                       str             = "new_runner_experiment"

    """The path in which Experiment Runner will create a folder with the name `self.name`, in order to store the
    results from this experiment. (Path does not need to exist - it will be created if necessary.)
    Output path defaults to the config file's path, inside the folder 'experiments'"""
    results_output_path:        Path             = ROOT_DIR / 'experiments'

    """Experiment operation type. Unless you manually want to initiate each run, use `OperationType.AUTO`."""
    operation_type:             OperationType   = OperationType.AUTO

    """The time Experiment Runner will wait after a run completes.
    This can be essential to accommodate for cooldown periods on some systems."""
    time_between_runs_in_ms:    int             = 1000

    # Dynamic configurations can be one-time satisfied here before the program takes the config as-is
    # e.g. Setting some variable based on some criteria
    def __init__(self):
        """Executes immediately after program start, on config load"""

        EventSubscriptionController.subscribe_to_multiple_events([
            (RunnerEvents.BEFORE_EXPERIMENT, self.before_experiment),
            (RunnerEvents.BEFORE_RUN       , self.before_run       ),
            (RunnerEvents.START_RUN        , self.start_run        ),
            (RunnerEvents.START_MEASUREMENT, self.start_measurement),
            (RunnerEvents.INTERACT         , self.interact         ),
            (RunnerEvents.STOP_MEASUREMENT , self.stop_measurement ),
            (RunnerEvents.STOP_RUN         , self.stop_run         ),
            (RunnerEvents.POPULATE_RUN_DATA, self.populate_run_data),
            (RunnerEvents.AFTER_EXPERIMENT , self.after_experiment )
        ])
        self.run_table_model = None  # Initialized later

        output.console_log("Custom config loaded")

    def create_run_table_model(self) -> RunTableModel:
        """Create and return the run_table model here. A run_table is a List (rows) of tuples (columns),
        representing each run performed"""
        factor1 = FactorModel("fib_type", ['iter', 'mem', 'rec'])
        factor2 = FactorModel("problem_size", [10])
        self.run_table_model = RunTableModel(
            factors=[factor1, factor2],
            # exclude_combinations=[
            #     {factor2: [10]},   # all runs having treatment "10" will be excluded
            #     {factor1: ['rec'], factor2: [5000, 10000]},
            #     {factor1: ['mem', 'iter'], factor2: [35, 40]},  # all runs having the combination ("iter", 30) will be excluded
            # ],
            repetitions = 1,
            data_columns=["energy", "runtime", "memory"]
        )
        return self.run_table_model

    def before_experiment(self) -> None:
        """Perform any activity required before starting the experiment here
        Invoked only once during the lifetime of the program."""
        pass

    def before_run(self) -> None:
        """Perform any activity required before starting a run.
        No context is available here as the run is not yet active (BEFORE RUN)"""
        self.timestamp_start = datetime.now()

    def start_run(self, context: RunnerContext) -> None:
        """Perform any activity required for starting the run here.
        For example, starting the target system to measure.
        Activities after starting the run should also be performed here."""
        fib_type = context.execute_run["fib_type"]
        problem_size = context.execute_run["problem_size"]
        self.target = subprocess.Popen(["python3", f"fibonacci_{fib_type}.py", str(problem_size)], cwd=self.ROOT_DIR)       

    def start_measurement(self, context: RunnerContext) -> None:
        """Perform any activity required for starting measurements."""
        # fib_type = context.execute_run["fib_type"]
        # problem_size = context.execute_run["problem_size"]
        
        # self.profiler = EnergiBridge(target_program=f"python3 examples/hello-world-fibonacci/fibonacci_{fib_type}.py {problem_size}",
        #                              out_file=context.run_dir / "energibridge.csv")

        # self.profiler.start()
        profiler_cmd = f'powerjoular -p {self.target.pid} -f {context.run_dir / "powerjoular.csv"}'

        time.sleep(1) # allow the process to run a little before measuring
        self.profiler = subprocess.Popen(shlex.split(profiler_cmd))

        performance_profiler_cmd = f"ps -p {self.target.pid} --noheader -o '%cpu,%mem'"
        timer_cmd = f"while true; do {performance_profiler_cmd}; sleep 1; done"
        self.performance_profiler = subprocess.Popen(['sh', '-c', timer_cmd],
                                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE
                                                     )

    def interact(self, context: RunnerContext) -> None:
        """Perform any interaction with the running target system here, or block here until the target finishes."""
        pass

    def stop_measurement(self, context: RunnerContext) -> None:
        """Perform any activity here required for stopping measurements."""
        # os.kill(self.profiler.pid, signal.SIGINT) # graceful shutdown of powerjoular
        # self.profiler.wait()
        # self.performance_profiler.kill()
        # self.performance_profiler.wait()

    def stop_run(self, context: RunnerContext) -> None:
        """Perform any activity here required for stopping the run.
        Activities after stopping the run should also be performed here."""
        # self.target.kill()
        # self.target.wait()
        self.timestamp_end = datetime.now()

    def populate_run_data(self, context: RunnerContext) -> Optional[Dict[str, Any]]:
        """Parse and process any measurement data here.
        You can also store the raw measurement data under `context.run_dir`
        Returns a dictionary with keys `self.run_table_model.data_columns` and their values populated"""
        
        psdf = pd.DataFrame(columns=['cpu_usage', 'memory_usage'])
        for i, l in enumerate(self.performance_profiler.stdout.readlines()):
             decoded_line = l.decode('ascii').strip()
             decoded_arr = decoded_line.split()
             cpu_usage = float(decoded_arr[0])
             memory_usage = float(decoded_arr[1])
             psdf.loc[i] = [cpu_usage, memory_usage]
        psdf.to_csv(context.run_dir / 'raw_data.csv', index=False)

        output_file = f'{context.run_dir}/powerjoular-filtered-data.csv-{self.target.pid}.csv'
        df = pd.read_csv(context.run_dir / f"powerjoular.csv-{self.target.pid}.csv")
        is_numeric = df.apply(lambda row: row['CPU Utilization'].replace('.', '', 1).isdigit() and row['CPU Power'].replace('.', '', 1).isdigit(), axis=1)
        filtered_df = df[is_numeric]
        for column in filtered_df.columns[1:]:
            filtered_df[column] = filtered_df[column].astype(float)
        filtered_df.to_csv(output_file, index=False)

        run_data = {
                    'execution_time': (self.timestamp_end - self.timestamp_start).total_seconds(),
                    'cpu_usage': round(psdf['cpu_usage'].mean(), 3),
                    'memory_usage': round(psdf['memory_usage'].mean(), 3),
                    'energy_usage': round(filtered_df['CPU Power'].sum(), 3)
                
                }
        return run_data

    def after_experiment(self) -> None:
        """Perform any activity required after stopping the experiment here
        Invoked only once during the lifetime of the program."""
        pass

    # ================================ DO NOT ALTER BELOW THIS LINE ================================
    experiment_path:            Path             = None