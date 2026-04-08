"""
Tutorial 017: Data Synchronization
Demonstrates how to bundle multiple disparate streams (e.g. Det and Seg) by timestamp using the Synchronizer node.
"""

import time
import random
from dataclasses import field as dc_field, fields

from retriever.flow import Flow, Rate, Pipeline, io, Latest, Trigger
from retriever.flow.sync import Synchronizer

# --- Data Definitions ---

@io
class Detection:
    label: str
    box: list[int]
    timestamp: float

@io
class Segmentation:
    mask_rle: str
    timestamp: float

@io
class SyncInput:
    # Flattened input to avoid nesting complexity in graph ports
    det_label: str = ""
    det_box: list[int] = dc_field(default_factory=lambda: [0, 0, 0, 0])
    det_timestamp: float = 0.0
    
    seg_mask_rle: str = ""
    seg_timestamp: float = 0.0

@io
class BundledResult:
    det: Detection
    seg: Segmentation
    timestamp: float

# --- Sources ---

@io
class Frame:
    id: int
    timestamp: float

class Camera(Flow[None, Frame]):
    def init(self):
        self.idx = 0
    def run(self, _):
        self.idx += 1
        now = time.time()
        return Frame(self.idx, now)

class Detector(Flow[Frame, Detection]):
    def run(self, frame: Frame):
        # Fast processing
        return Detection(f"obj_{frame.id}", [0,0,0,0], timestamp=frame.timestamp)

class Segmenter(Flow[Frame, Segmentation]):
    def run(self, frame: Frame):
        # Slow processing delay
        time.sleep(0.05) 
        return Segmentation(f"mask_{frame.id}", timestamp=frame.timestamp)

# --- The Synchronizer ---

# --- The Synchronizer (Native) ---

# We no longer need MySync or manual buffering! 
# We just define the output bundling node.

@io
class NativeResult:
    det: Detection
    seg: Segmentation
    # Note: Trigger time will be accurate, but we can also store timestamp
    timestamp: float

class SyncBundler(Flow[SyncInput, NativeResult]):
    """
    Receives synchronized inputs and bundles them.
    Because we use @Synchronized and Exact adapters, 
    input.det and input.seg are guaranteed to be from the same timestamp (approx).
    """
    def run(self, input: SyncInput) -> NativeResult:
        # print(f"DEBUG: SyncBundler.run t={input.det_timestamp}")
        
        # We can trust they are present and aligned!
        # Note: SyncInput has Optional fields, but since we Trigger on them 
        # with Synchronized clock, they SHOULD be present.
        
        # flattened inputs again
        det = Detection(input.det_label, input.det_box, input.det_timestamp)
        seg = Segmentation(input.seg_mask_rle, input.seg_timestamp)
        
        # print("DEBUG: Bundling result")
        return NativeResult(det, seg, input.det_timestamp)

# --- Pipeline ---

def main():
    pipe = Pipeline("sync_demo")
    
    # Sync Node: 
    # 1. Use Synchronized Clock -> Triggers only when timestamps match
    # 2. Use Exact Adapter -> Ensures we pull the matching sample
    from retriever.flow.clock import Trigger, Rate
    from retriever.flow.adapter import Exact

    with pipe:
        # Camera runs at 10Hz
        cam = Camera() @ Rate(2)
        
        # Detector/Segmenter need BOTH signals to be valid.
        # Use Synchronized to ensure we have id AND timestamp before running.
        det_node = Detector() @ Trigger("id", "timestamp")
        seg_node = Segmenter() @ Trigger("id", "timestamp")
        
        
        sync_node = SyncBundler() @ Trigger("det_timestamp", "seg_timestamp")
        
        # Fan out
        pipe.connect(cam, det_node, sync=Latest())
        pipe.connect(cam, seg_node, sync=Latest())
        
        # Fan in
        def get_map(cls, prefix):
            return {f.name: f"{prefix}_{f.name}" for f in fields(cls)}

        pipe.connect(det_node, sync_node, map=get_map(Detection, "det"), sync=Exact())
        pipe.connect(seg_node, sync_node, map=get_map(Segmentation, "seg"), sync=Exact())
        
        
        # Sink
        sink = Printer() @ Trigger("det")
        pipe.connect(sync_node, sink, sync=Latest())
        
    print("Running Native Sync Demo...")
    pipe.run(duration=3.0)

class Printer(Flow[NativeResult, None]):
    def run(self, res: NativeResult):
        print(f"[Native] Bundled! TS={res.det.timestamp:.3f}", flush=True)

if __name__ == "__main__":
    main()
