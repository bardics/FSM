import serial
import time
import sys
import re
from configs.phone_power_cycle_config import (
    total_wait,
    port,
    baudrate,
    num_power_cycles,
    fast_ethernet_port,
)


def power_cycle(ser, round_num, total_rounds, pass_count, fail_count):
    print(f"\n\n*** Power cycle round {round_num} ***\n\n")
    ser.write(b"\r")
    read_until(ser, b"Switch")

    ser.write(b"en\r")
    read_until(ser, b"Switch#")

    ser.write(b"conf t\r")
    read_until(ser, b"Switch(config)#")

    ethernet_port_1 = f"int fastEthernet 0/{fast_ethernet_port}\r"
    ser.write(ethernet_port_1.encode("ascii"))
    read_until(ser, b"Switch(config-if)#")

    print(" Turning off and on the POE port...")

    ser.write(b"shutdown\r")
    time.sleep(5)
    ser.write(b"no shutdown\r")

    read_until(ser, b"Switch(config-if)#")
    ser.write(b"end\r")
    read_until(ser, b"Switch#")

    print(time.ctime())
    print(f"Wait for {total_wait}s to boot - Power cycle round {round_num}")

    global original_stdout
    for k in range(total_wait, 0, -1):
        total_steps = total_rounds * total_wait
        current_step = (round_num - 1) * total_wait + (total_wait - k + 1)
        percent = (current_step / total_steps) * 100
        bar_len = 30
        filled = int(bar_len * current_step // total_steps)
        bar = "█" * filled + "-" * (bar_len - filled)
        original_stdout.write(
            f"\rProgress: [{bar}] {percent:5.1f}% | Round {round_num}/{total_rounds} | {k:3}s left"
        )
        original_stdout.flush()
        time.sleep(1)
    original_stdout.write("\r" + " " * 100 + "\r")
    original_stdout.flush()

    ser.write(b"\r")
    read_until(ser, b"Switch#")

    ser.write(b"term shell\r")
    read_until(ser, b"Switch#")

    ethernet_port_2 = (
        f"show cdp neighbors fastEthernet 0/{fast_ethernet_port} deta | grep address\r"
    )
    print(f"{ethernet_port_2}")
    ser.write(ethernet_port_2.encode("ascii"))
    response = read_until(ser, b"Switch#", timeout=20)

    response_str = response.decode("utf-8", errors="ignore")
    ip_pattern = r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
    match = re.search(ip_pattern, response_str)

    if match:
        ip_address = match.group(0)
        print(
            f"*** Port 1 - Phone successfully registered to the network with IP: {ip_address} ***\n\n"
        )
        pass_count += 1
    else:
        print("*** Port 1 - Phone could not register to the network ***\n\n")
        fail_count += 1
    return pass_count, fail_count


def read_until(ser, expected_bytes, timeout=10):
    start_time = time.time()
    buffer = b""
    while True:
        if ser.in_waiting > 0:
            buffer += ser.read(ser.in_waiting)
            if expected_bytes in buffer:
                return buffer
        if time.time() - start_time > timeout:
            raise serial.SerialTimeoutException(
                f"Timeout waiting for {expected_bytes} in serial response."
            )
        time.sleep(0.1)


class Tee:
    def __init__(self, *files):
        self.files = files

    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush()

    def flush(self):
        for f in self.files:
            f.flush()


if __name__ == "__main__":
    log_filename = time.strftime("power_cycle_log_%Y%b%d_%H%M%S.log")
    log_file = open(log_filename, "a")
    original_stdout = sys.stdout
    sys.stdout = Tee(original_stdout, log_file)

    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1,
        )
    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        sys.exit(1)

    pass_count = 0
    fail_count = 0

    num_power_cycles_input = num_power_cycles

    ser.write(b"\r")
    read_until(ser, b"Switch")

    ser.write(b"en\r")
    read_until(ser, b"Switch#")

    for i in range(1, num_power_cycles_input + 1):
        pass_count, fail_count = power_cycle(
            ser, i, num_power_cycles_input, pass_count, fail_count
        )

    print("\n\n")
    print("**************************************")
    print(f"***** POWER CYCLE PASSED {pass_count} times *****")
    print(f"***** POWER CYCLE FAILED {fail_count} times *****")
    print("**************************************")
    print("\n\n")

    ser.close()
    log_file.close()
    sys.stdout = original_stdout
