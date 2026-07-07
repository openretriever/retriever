# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Standard types
#
# `retriever.types.*` is the shared payload vocabulary of the runtime: one
# canonical class per standard type, spread across `spatial`, `perception`,
# `language`, and more. Every one is already an `@io` type, so it can drop
# straight onto a Flow port. This notebook imports a few, shows why type
# *identity* — not just field shape — is the contract, constructs a couple, and
# wires one into a Flow. Everything runs in-process with only `retriever-core`.

# %% [markdown]
# > **Running in Colab?** The next cell installs `retriever-core`. From a source
# > checkout (or once it's already installed) the install is skipped.

# %%
# Colab setup: install retriever-core only if it isn't importable yet.
try:
    import retriever  # noqa: F401
except ImportError:  # pragma: no cover
    import subprocess
    import sys

    subprocess.run(
        [sys.executable, "-m", "pip", "install", "retriever-core"], check=True
    )

# %% [markdown]
# ## One import path per domain
#
# Standard payloads live under `retriever.types`, split by domain. You import
# the class you need directly — there is no separate registration step to do in
# your own code. Here we pull a few from three domains at once.

# %%
from retriever.types.spatial import Header, Vector3, Quaternion, SE3Pose, PoseStamped
from retriever.types.perception import BBox2D, Detection2D, DetectionBatch
from retriever.types.language import Caption

for cls in (Header, Vector3, SE3Pose, PoseStamped, DetectionBatch, Caption):
    print(f"{cls.__name__:15s} <- {cls.__module__}")

# %% [markdown]
# ## Type identity is the contract
#
# The rule that makes these types useful is that they are the *same class
# object* everywhere — not two look-alikes with matching fields. The stable
# surface (`retriever.types.spatial`) and the versioned module
# (`retriever.types.spatial.v1`) re-export one object, so `is` holds. Every
# payload is also `@io`-decorated, which is what lets it sit on a Flow port.

# %%
from retriever.flow.io import is_flow_io
from retriever.types.spatial.v1 import PoseStamped as PoseStamped_v1

print("same class object:", PoseStamped is PoseStamped_v1)
print("PoseStamped   @io?", is_flow_io(PoseStamped))
print("DetectionBatch @io?", is_flow_io(DetectionBatch))
print("Caption       @io?", is_flow_io(Caption))

# %% [markdown]
# Because it is one class, a component that emits `PoseStamped` and a component
# that consumes `PoseStamped` are talking about the identical type — no adapter,
# no "which PoseStamped?" ambiguity. Never redefine a standard type locally,
# even with identical fields: identity, not shape, is what the runtime checks.

# %% [markdown]
# ## Construct a couple
#
# Composite spatial types (`SE3Pose`, `PoseStamped`) nest `Vector3`,
# `Quaternion`, and `Header`, so nested access reads the way you'd expect.
# Perception and language types compose the same way.

# %%
pose = PoseStamped(
    header=Header(stamp_ns=1_000_000, frame_id="base_link"),
    pose=SE3Pose(
        position=Vector3(x=0.4, y=0.0, z=0.2),
        orientation=Quaternion(x=0.0, y=0.0, z=0.0, w=1.0),
    ),
)
batch = DetectionBatch(
    detections=(
        Detection2D(
            label="cup",
            bbox=BBox2D(x=12, y=30, width=40, height=55),
            confidence=0.91,
        ),
    ),
    frame_index=7,
)

print("pose frame:", pose.header.frame_id, "x=", pose.pose.position.x)
print("unit quaternion?", pose.pose.orientation.is_unit())
print("detections:", [(d.label, d.confidence) for d in batch.detections])
print("bbox area:", batch.detections[0].bbox.area())
print("caption:", Caption(text="a red cup on the table").text)

# %% [markdown]
# ## `_signals` says which fields arrived
#
# `@io` makes every field optional, so a standard type can carry a *partial*
# payload. `_signals` reports the fields whose value is set (non-`None`) — the
# same mechanism a Flow uses to branch on what a `step()` actually received.

# %%
partial = PoseStamped(header=Header(stamp_ns=1_000_000, frame_id="base_link"))
print("empty   _signals:", PoseStamped()._signals)
print("partial _signals:", partial._signals)
print("full    _signals:", pose._signals)

# %% [markdown]
# ## Use a standard type as a Flow port
#
# Since each payload is already `@io`, it becomes a Flow input or output with no
# wrapping. `Flow[DetectionBatch, Caption]` is the type boundary Retriever
# checks, and the clock (`@ Trigger(...)`) fires on a field of the input type.

# %%
from retriever.flow import Flow, Trigger


class Detector(Flow[DetectionBatch, Caption]):  # standard types as ports
    def step(self, batch: DetectionBatch) -> Caption:
        labels = ", ".join(d.label for d in batch.detections)
        return Caption(text=f"saw: {labels}")


det = Detector()
print("input port type: ", det.input_type.__name__)
print("output port type:", det.output_type.__name__)
print("step output:     ", det.step(batch))

# clock triggers on a field of the standard input type
node = Detector() @ Trigger("detections")
print("wired node fires on field 'detections'")
