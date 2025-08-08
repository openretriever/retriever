# Retriever Examples 🚀

Learn Retriever step-by-step through **clean, concise** examples.

## 📋 **STREAMLINED STRUCTURE** (Deduplicated Aug 2025)

```
examples/
├── 01_core_concepts/              # Essential Flow patterns (3 files)
├── 02_vision_processing/          # ⭐ Camera + detection (3 files - START HERE)
├── 03_state_management/           # State & Eff patterns (5 files)  
└── 04_backend_execution/          # Dora FRP backend execution
```

## 🎯 **Quick Start**

```bash
# Complete working camera demo in 2 minutes
python examples/02_vision_processing/01_simple_camera_demo.py  
```

## 📚 **Learning Progression** (10-15 minutes total)

### ⭐ **Start Here**: `02_vision_processing/01_simple_camera_demo.py`
- **One file** showing everything: camera → detection → live OpenCV window
- **Works immediately** (real MacBook camera with 'q' to quit)
- **All key concepts**: Class-based Flows, @flow decorators, >> composition
- **Time**: 2 minutes

### **Step 1**: `01_core_concepts/` (Essential patterns)
- `01_hello_flow.py` - Flow[I,O] basics + class patterns  
- `02_pipeline_composition.py` - >> operator and type safety
- `03_clean_class_flows.py` - PyTorch-like Flow modules (no boilerplate!)
- **Time**: 5 minutes

### **Step 2**: `02_vision_processing/` (Robotics vision)
- `02_camera_detection_window.py` - Real camera + matplotlib  
- `03_class_based_flows.py` - Vision modules like PyTorch
- **Time**: 5 minutes

### **Step 3**: `03_state_management/` (Robotics state)
- Complete tutorial: mutable problems → Eff monad → robotics patterns
- **Simplified patterns** (no confusing nested functions!)  
- **Clear explanations** of what `Eff[State, Result]` means
- **Time**: 5 minutes

### **Advanced**: `04_backend_execution/` (Production robotics)
- `02_dora_backend.py` - True Dora FRP backend with subprocess execution
- Real YAML generation and Dora operator compilation  
- Multi-rate coordination (30Hz → 10Hz via FRP timers)
- Production-ready backend execution patterns

## 💡 **Key Benefits After Deduplication**

✅ **No duplication** - Each concept taught once, clearly  
✅ **Quick success** - Working camera demo in 2 minutes  
✅ **Clean progression** - Logical order, no confusion  
✅ **Simplified patterns** - Clear explanations, no complex nesting  
✅ **PyTorch-like** - Class-based modules for real robotics  

## 🔧 **All Examples Work**

- ✅ Fixed import issues  
- ✅ Fixed @flow decorator support  
- ✅ Fixed data type issues  
- ✅ Removed confusing nested functions  
- ✅ Real camera support with test pattern fallback

## 🚀 **Ready for Real Robotics**

After these examples, you'll understand:
- **Flow composition** with >> and & operators
- **Class-based modules** like PyTorch for robotics  
- **State management** with Eff patterns
- **FRP integration** with @flow(rate='30ms') decorators
- **Real hardware** integration patterns

**Start with `simple_camera_demo.py` and progress through the folders!** 🎯