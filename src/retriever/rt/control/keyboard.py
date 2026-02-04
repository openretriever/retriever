"""
Global keyboard controller for pipeline control.

Provides process-level keyboard shortcuts that work regardless of
which flow has focus.
"""

from typing import Callable, Dict, Optional


class GlobalKeyboardController:
    """
    Process-level keyboard handler for pipeline control.

    Default shortcuts:
    - Space: Toggle pause/resume
    - Shift+R: Reset all flows
    - Shift+Q: Stop pipeline
    - Shift+S: Print status

    Integrates with PipelineController for actual control operations.
    """

    DEFAULT_BINDINGS = {
        'space': 'toggle_pause',
        'r': 'reset',  # With shift modifier
        'q': 'stop',   # With shift modifier
        's': 'status', # With shift modifier
    }

    def __init__(
        self,
        controller: "PipelineController",
        bindings: Optional[Dict[str, str]] = None,
        enabled: bool = True,
    ):
        """
        Initialize keyboard controller.

        Args:
            controller: PipelineController to send commands to
            bindings: Custom key bindings (key -> action)
            enabled: Whether to start listening immediately
        """
        self._controller = controller
        self._bindings = bindings or self.DEFAULT_BINDINGS.copy()
        self._enabled = enabled
        self._listener = None
        self._paused = False
        self._shift_pressed = False

        # Custom action handlers
        self._actions: Dict[str, Callable] = {
            'toggle_pause': self._toggle_pause,
            'reset': self._reset,
            'stop': self._stop,
            'status': self._status,
            'pause': self._pause,
            'resume': self._resume,
        }

        if enabled:
            self.start()

    def start(self) -> None:
        """Start listening for keyboard events."""
        try:
            from pynput import keyboard
        except ImportError:
            print("[KeyboardController] pynput not installed, keyboard control disabled")
            print("[KeyboardController] Install with: pip install pynput")
            return

        def on_press(key):
            # Track shift state
            if key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r):
                self._shift_pressed = True

        def on_release(key):
            key_str = self._key_to_string(key)

            # Handle shift release
            if key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r):
                self._shift_pressed = False
                return

            if key_str and key_str in self._bindings:
                # For space, always execute
                # For others, only execute if shift is pressed
                if key_str == 'space' or self._shift_pressed:
                    action = self._bindings[key_str]
                    if action in self._actions:
                        self._actions[action]()

        self._listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self._listener.start()
        print("[KeyboardController] Listening...")
        print("[KeyboardController]   Space      = pause/resume")
        print("[KeyboardController]   Shift + R  = reset all")
        print("[KeyboardController]   Shift + S  = status")
        print("[KeyboardController]   Shift + Q  = quit")

    def stop(self) -> None:
        """Stop listening for keyboard events."""
        if self._listener:
            self._listener.stop()
            self._listener = None

    def _key_to_string(self, key) -> Optional[str]:
        """Convert pynput key to string representation."""
        try:
            from pynput import keyboard

            if key == keyboard.Key.space:
                return 'space'
            elif hasattr(key, 'char') and key.char:
                return key.char.lower()
        except Exception:
            pass
        return None

    def _toggle_pause(self) -> None:
        """Toggle pause/resume state."""
        if self._paused:
            self._resume()
        else:
            self._pause()

    def _pause(self) -> None:
        """Pause all flows."""
        print("[KeyboardController] Pausing...")
        self._controller.pause()
        self._paused = True

    def _resume(self) -> None:
        """Resume all flows."""
        print("[KeyboardController] Resuming...")
        self._controller.resume()
        self._paused = False

    def _reset(self) -> None:
        """Reset all flows."""
        print("[KeyboardController] Resetting...")
        self._controller.reset()

    def _stop(self) -> None:
        """Stop the pipeline."""
        print("[KeyboardController] Stopping pipeline...")
        self._controller.stop()

    def _status(self) -> None:
        """Print status to console."""
        status = self._controller.get_state()
        print(f"\n{'='*50}")
        print(f"Pipeline: {status.name} ({status.state})")
        for node_id, node in status.nodes.items():
            print(f"  {node_id}: {node.state.value} (steps={node.step_count})")
        print(f"{'='*50}\n")

    def register_action(self, name: str, handler: Callable) -> None:
        """Register a custom action handler."""
        self._actions[name] = handler

    def bind(self, key: str, action: str) -> None:
        """Bind a key to an action."""
        self._bindings[key] = action
