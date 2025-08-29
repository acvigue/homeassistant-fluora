"""Simple test script to validate the Fluora component structure."""

import sys
from pathlib import Path

# Add the custom_components path to sys.path to test imports
component_path = Path(__file__).parent
sys.path.insert(0, str(component_path))

def test_imports():
    """Test that all modules can be imported without errors."""
    try:
        # Test basic imports (these should work even without Home Assistant)
        import const
        print("✓ const.py imports successfully")
        
        print(f"✓ Domain: {const.DOMAIN}")
        print(f"✓ Manufacturer: {const.MANUFACTURER}")
        print(f"✓ Model: {const.MODEL}")
        
        # Check if libfluora is available (this might fail in some environments)
        try:
            import libfluora
            print("✓ libfluora is available")
            print(f"✓ libfluora version: {libfluora.__version__}")
        except ImportError as e:
            print(f"⚠ libfluora not available (expected in some environments): {e}")
        
        print("\n✅ Basic component structure validation passed!")
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

def test_file_structure():
    """Test that all required files exist."""
    required_files = [
        "__init__.py",
        "config_flow.py", 
        "const.py",
        "coordinator.py",
        "light.py",
        "manifest.json",
        "strings.json",
        "translations/en.json"
    ]
    
    missing_files = []
    for file in required_files:
        if not (component_path / file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files present!")
        return True

if __name__ == "__main__":
    print("🔧 Fluora Component Validation")
    print("=" * 40)
    
    structure_ok = test_file_structure()
    import_ok = test_imports()
    
    if structure_ok and import_ok:
        print("\n🎉 Component validation completed successfully!")
        print("\nNext steps:")
        print("1. Install libfluora: pip install libfluora>=0.1.1")
        print("2. Copy this component to your Home Assistant custom_components/fluora/")
        print("3. Restart Home Assistant")
        print("4. Add Fluora integration via UI")
    else:
        print("\n❌ Component validation failed!")
        sys.exit(1)
