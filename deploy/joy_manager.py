import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
import subprocess
import os
import signal

class JoyManager(Node):
    def __init__(self):
        super().__init__('joy_manager')
        self.create_subscription(Joy, '/joy', self.joy_cb, 10)
        self.last_buttons = None
        self.rma_process = None
        self.event_log = os.path.expanduser('~/session_events.log')
        self.get_logger().info("Joy Manager active. Waiting for inputs...")

    def log_event(self, event_type):
        timestamp = self.get_clock().now().nanoseconds
        self.get_logger().info(f"Recorded: {event_type}")
        with open(self.event_log, 'a') as f:
            f.write(f"{timestamp},{event_type}\n")

    def joy_cb(self, msg):
        if self.last_buttons is None:
            self.last_buttons = list(msg.buttons)
            return
        
        # Trigger on rising edge (button press, not release)
        for i in range(len(msg.buttons)):
            if msg.buttons[i] == 1 and self.last_buttons[i] == 0:
                self.handle_press(i)
        
        self.last_buttons = list(msg.buttons)

    def handle_press(self, idx):
        if idx == 1:  # Circle
            self.log_event('TRIAL_START')
        elif idx == 2:  # Triangle
            self.log_event('TRIAL_PASS')
        elif idx == 0:  # X
            self.log_event('TRIAL_FAIL')
        elif idx == 3:  # Square
            self.log_event('NEW_METHOD_STARTED')

    def toggle_rma(self):
        if self.rma_process is None or self.rma_process.poll() is not None:
            self.get_logger().info("Starting RMA Node...")
            # Spawns the node just like typing it in the terminal
            self.rma_process = subprocess.Popen(
                ['/home/ncchong/start_rma.sh']
            )
            self.log_event('RMA_NODE_START')
        else:
            self.get_logger().info("Sending Ctrl+C to RMA Node...")
            # Sends SIGINT (Ctrl+C) so the node cleanly closes its CSV
            self.rma_process.send_signal(signal.SIGINT)
            self.rma_process.wait()
            self.log_event('RMA_NODE_STOP')

def main():
    rclpy.init()
    node = JoyManager()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node.rma_process and node.rma_process.poll() is None:
            node.rma_process.send_signal(signal.SIGINT)
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
