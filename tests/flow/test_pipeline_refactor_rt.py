
import unittest
from retriever.flow import Pipeline, Flow, io
from retriever.flow.builder import PipelineBuilder

@io
class IntData:
    value: int

@io
class Void:
    pass

class Producer(Flow[Void, IntData]):
    def step(self, inp):
        return IntData(value=1)

class Consumer(Flow[IntData, Void]):
    def step(self, inp):
        print(f"Consumed: {inp.value}")
        return Void()

class TestPipelineComposition(unittest.TestCase):
    def test_pipeline_composition(self):
        """Verify Pipeline uses composition and connects nodes correctly."""
        print("\n--- Testing Pipeline Composition ---")
        
        # 1. Instantiate Pipeline
        pipe = Pipeline("test_pipe")
        
        # Verify it has a builder but is NOT a PipelineBuilder instance (inheritance check)
        self.assertFalse(isinstance(pipe, PipelineBuilder), "Pipeline should NOT inherit PipelineBuilder")
        self.assertTrue(hasattr(pipe, "_builder"), "Pipeline should have _builder")
        self.assertIsInstance(pipe._builder, PipelineBuilder, "_builder should be PipelineBuilder")
        self.assertEqual(pipe._builder.owner, pipe, "_builder.owner should point to Pipeline")
        
        # 2. Add Flows
        from retriever.flow import Rate
        p = Producer() @ Rate(hz=10)
        c = Consumer() @ Rate(hz=10)
        
        # 3. Connect (this exercises the delegation and owner check in connect())
        # Using pipe instance method (Pipeline.connect requires strict sync or default)
        from retriever.flow import Latest
        pipe.connect(p, c, sync=Latest())
        
        # Verify connections in builder
        conns = pipe.get_connections()
        self.assertEqual(len(conns), 1, "Should have 1 connection")
        print(f"Connection registered: {conns[0]}")
        
        # 4. Context Manager usage
        with Pipeline("ctx_pipe") as ctx_pipe:
            p2 = Producer() @ Rate(hz=10)
            c2 = Consumer() @ Rate(hz=10)
            # This uses the global connect() which should find the active builder -> owner pipeline
            from retriever.flow import connect
            connect(p2, c2, sync=Latest())
            
            # Verify
            self.assertEqual(len(ctx_pipe.get_connections()), 1)
            print("Context manager connection verified")

        print("✅ Pipeline Composition Verified")

if __name__ == "__main__":
    unittest.main()
