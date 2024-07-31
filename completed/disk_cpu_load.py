import subprocess
import sys

# Script to test cpu load imposed by a simple disk read operation
# using subprocess to run the commands implemented in disk_spu_load.sh In a class DiskCPULoadTester
#
# Usage:
#   python disk_cpu_load.py [ --max-load <load> ] [ --xfer <mebibytes> ]
#                    [ --verbose ] [ <device_filename> ]
#
# Parameters:
#  --max-load <load> -- Max CPU load percentage (default 30).
#  --xfer <mebibytes> -- Amount of data to read from disk, in MiB (default 4096).
#  --verbose -- Flag for verbose output (default False).
#  <device-filename> -- This is the WHOLE-DISK device filename (with or
#                       without "/dev/"), e.g. "sda" or "/dev/sda". The
#                       script finds a filesystem on that device, mounts
#                       it if necessary, and runs the tests on that mounted
#                       filesystem. Defaults to /dev/sda.

class DiskCPULoadTester:
    """
    A class to test CPU load imposed by a simple disk read operation.
    """
    def __init__(self, max_load=30, xfer=4096, verbose=False, device_filename='/dev/sda'):
        self.max_load = max_load
        self.xfer = xfer
        self.verbose = verbose
        self.device_filename = device_filename

    def compute_cpu_load(self, start_use, end_use):
        """
        Computes the CPU load between two points in time.

        Args:
            start_use (list[int]): CPU statistics from /proc/stat at the START point.
            end_use (list[int]): CPU statistics from /proc/stat at the END point.

        Returns:
            int: The CPU load over the two measurements, as a percentage (0-100).
        """
        diff_idle = end_use[3] - start_use[3]
        diff_total = sum(end_use) - sum(start_use)
        diff_used = diff_total - diff_idle
        
        if self.verbose:
            print(f"Start CPU time = {sum(start_use)}")
            print(f"End CPU time = {sum(end_use)}")
            print(f"CPU time used = {diff_used}")
            print(f"Total elapsed time = {diff_total}")
        
        if diff_total != 0:
            return int(diff_used * 100 / diff_total)
        return 0

    def get_cpu_stats(self):
        """
        Retrieves the current CPU statistics from /proc/stat.

        Returns:
            list[int]: A list of integers representing the CPU usage statistics.
        """
        # Convert /proc/stat byte data to list of ints 
        cpu_stats = subprocess.check_output("grep 'cpu ' /proc/stat | tr -s ' ' | cut -d ' ' -f 2-", shell=True).decode().split()
        return [int(x) for x in cpu_stats]

    def flush_buffers(self):
        """
        Flushes the buffers of the specified disk device.
        """
        try:
            subprocess.run(['blockdev', '--flushbufs', self.device_filename], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error flushing buffers: {e}", file=sys.stderr)
            sys.exit(1)

    def perform_disk_read(self):
        """
        Performs the disk read operation.
        """
        try:
            subprocess.run(['dd', f'if={self.device_filename}', 'of=/dev/null', 'bs=1048576', f'count={self.xfer}'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error reading from disk: {e}", file=sys.stderr)
            sys.exit(1)

    def run_test(self):
        """
        Runs the disk CPU load test and prints the results.
        """
        print(f"Testing CPU load when reading {self.xfer} MiB from {self.device_filename}")
        print(f"Maximum acceptable CPU load is {self.max_load}")

        self.flush_buffers()
        
        start_load = self.get_cpu_stats()

        if self.verbose:
            print("Beginning disk read....")

        self.perform_disk_read()
        
        if self.verbose:
            print("Disk read complete!")

        end_load = self.get_cpu_stats()

        cpu_load = self.compute_cpu_load(start_load, end_load)
        
        print(f"Detected disk read CPU load is {cpu_load}")

        if cpu_load > self.max_load:
            print("*** DISK CPU LOAD TEST HAS FAILED! ***")
            sys.exit(1)
        else:
            print("Disk CPU load test passed.")


def parse_params():
    """
    Parses command-line arguments and returns them as a dictionary.

    Returns:
        dict: A dictionary containing the parsed command-line arguments.
    """
    params = {
        'max_load': 30,
        'xfer': 4096,
        'verbose': False,
        'device_filename': '/dev/sda'
    }
    
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--max-load':
            params['max_load'] = int(args[i + 1])
            i += 2
        elif args[i] == '--xfer':
            params['xfer'] = int(args[i + 1])
            i += 2
        elif args[i] == '--verbose':
            params['verbose'] = True
            i += 1
        else:
            params['device_filename'] = args[i]
            if "/dev" not in params['device_filename']:
                params['device_filename'] = "/dev/" + args[i]
            i += 1

    return params


def main():
    """
    Main function to test CPU load imposed by a simple disk read operation.
    """
    params = parse_params()
    tester = DiskCPULoadTester(**params)
    tester.run_test()


if __name__ == "__main__":
    main()
