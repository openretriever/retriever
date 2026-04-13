# Perception Types v1

`retriever.types.perception` is the canonical package for reusable media and
perception payloads.

Use it for:
- decoded 2D image frames,
- compressed image frames,
- encoded video artifacts,
- camera intrinsics,
- point clouds,
- 2D detections,
- 2D segmentation masks,
- normalized 2D pointing targets.

## Canonical imports

```python
from retriever.types.perception import (
    BBox2D,
    CameraIntrinsics,
    CompressedImage2D,
    Detection2D,
    DetectionBatch,
    EncodedVideo,
    Image2D,
    PointCloud3D,
    PointTarget2D,
    SegmentationMask2D,
)
```

Pinned import when you want an explicit version boundary:

```python
from retriever.types.perception.v1 import Image2D
```

## Frame, compressed frame, and video

Retriever keeps these separate on purpose:

- `Image2D`: one decoded frame
- `CompressedImage2D`: one compressed frame
- `EncodedVideo`: one encoded multi-frame artifact or payload

For frame-centric payloads, use the optional `frame_index` field when you need a
stream-local integer frame counter. Do not overload `Header.frame_id` for that:
`Header.frame_id` names the coordinate/source frame, while `frame_index` names a
position in an image/video sequence.

At the stream level, a stream of `Image2D` frames is semantically a video.
That does **not** make `Image2D` and `EncodedVideo` interchangeable.

Use:
- `Image2D` for frame transforms, overlays, and step-by-step debugging
- `CompressedImage2D` when a single frame should cross a compressed boundary
- `EncodedVideo` for long-run artifact packaging or transport-oriented replay

## Relationship to other type families

- `retriever.types`: shared schema/stream identity primitives
- `retriever.types.spatial`: geometry and stamped spatial payloads
- `retriever.types.data`: event/stream/dataset contracts
- `retriever.types.symbolic`: object-centric planning structures

`retriever.types.perception` should stay media/perception-centric. Do not use it
for memory-state or symbolic planning payloads.

## Composite Flow IO rule

Prefer shared primitives plus structural composition:

```python
from retriever.flow import Flow
from retriever.types.perception import Image2D, DetectionBatch, PointTarget2D

class PointingFlow(Flow[(Image2D, DetectionBatch), PointTarget2D]):
    def step(self, inp):
        frame = inp.Image2D
        detections = inp.DetectionBatch
        ...
```

Use a named `@io` envelope only when the grouped boundary is itself a stable,
reused contract.

## Transformation rules

Make media/perception transforms explicit:
- `Image2D -> CompressedImage2D`
- `CompressedImage2D -> Image2D`
- `Image2D + CameraIntrinsics -> PointCloud3D` for depth-like encodings
- `DetectionBatch + Image2D -> overlay view` is a helper, not a primitive type
- `SegmentationMask2D -> summary tables` is a helper, not a primitive type
- `frame_index` should stay aligned across `Image2D`, `DetectionBatch`, `SegmentationMask2D`, and `PointTarget2D` when they describe the same frame

## Current non-goals

Keep these out of `retriever.types.perception` for now:
- memory-state payloads like `SceneBelief`
- local example summaries
- model-specific request/response packets
- future text / caption / prompt payloads

If text-grounded payloads stabilize later, they should use a separate
`retriever.types.language` family instead of a broad `semantic` bucket.
