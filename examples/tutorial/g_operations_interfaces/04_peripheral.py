"""Tutorial: Capture keyboard input"""

import argparse
import threading
from pynput import keyboard
from typing import Optional
from dataclasses import dataclass
from retriever.flow import Flow, Pipeline, Rate, Trigger, io


@io
@dataclass
class KeyboardText:
    text: Optional[str] = None


class KeyboardInputFlow(Flow[None, KeyboardText]):
    """Captures keyboard input in background thread, returns text on Enter."""
    def __init__(self):
        super().__init__()
        self.keyboard_thread: Optional[threading.Thread] = None
        self._running: bool = False
        self._buffer: list = []
        self._result: Optional[str] = None
        self._lock = None  # Created in init() - can't pickle locks

    def init(self):
        self._lock = threading.Lock()  # Create after process spawn
        self._running = True
        self.keyboard_thread = threading.Thread(
            target=self._listener,
            daemon=True
        )
        self.keyboard_thread.start()

    def _listener(self):
        def on_press(key):
            with self._lock:
                if key == keyboard.Key.enter:
                    self._result = ''.join(self._buffer)
                    self._buffer.clear()
                elif key == keyboard.Key.backspace:
                    if self._buffer:
                        self._buffer.pop()
                elif key == keyboard.Key.space:
                    self._buffer.append(' ')
                elif hasattr(key, 'char') and key.char:
                    self._buffer.append(key.char)

        with keyboard.Listener(on_press=on_press) as listener:
            while self._running:
                listener.join(0.1)

    def run(self, _: None) -> KeyboardText:
        with self._lock:
            if self._result is not None:
                text = self._result
                self._result = None
                return KeyboardText(text=text)
        return KeyboardText()

    def cleanup(self):
        self._running = False
        if self.keyboard_thread and self.keyboard_thread.is_alive():
            self.keyboard_thread.join(timeout=1.0)

class EchoFlow(Flow[KeyboardText, None]):                                                                                                                                                                                                
    def run(self, input: KeyboardText) -> None:                                                                                                                                                                                         
        if input.text is not None:                                                                                                                                                                                                       
            print(f"You typed: {input.text}")

def build_pipeline() -> Pipeline:
    pipe = Pipeline("keyboard_pipeline")
    keyboard = KeyboardInputFlow() @ Rate(hz=30)
    echo = EchoFlow() @ Trigger("text")
    pipe.connect(keyboard, echo)
    return pipe

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", default="multiprocessing", choices=["multiprocessing", "dora"])
    parser.add_argument("--buffer-engine", default="python", choices=["python", "native"])
    parser.add_argument("--duration", type=float, default=10.0)
    args = parser.parse_args()

    pipe = build_pipeline()
    pipe.run(
        backend=args.backend,
        duration=args.duration,
        backend_config={"buffer_engine": args.buffer_engine},
    )
    # Flush terminal input buffer to prevent typed chars from leaking
    import sys
    import termios
    termios.tcflush(sys.stdin, termios.TCIFLUSH)


if __name__ == "__main__":
    main()