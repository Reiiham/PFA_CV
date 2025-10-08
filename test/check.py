import sys

print("=" * 60)
print("Checking PyTorch installation...")
print("=" * 60)

try:
    import torch
    print(f"\n✅ PyTorch IS installed")
    print(f"   Version: {torch.__version__}")
    print(f"   CUDA available: {torch.cuda.is_available()}")
    print(f"   Installation path: {torch.__file__}")
    
    # Test simple
    tensor = torch.rand(3, 3)
    print(f"\n✅ PyTorch works correctly!")
    print(f"   Test tensor shape: {tensor.shape}")
    
except ImportError:
    print("\n❌ PyTorch is NOT installed")
    print("   Installation in progress or needed")

print("\n" + "=" * 60)