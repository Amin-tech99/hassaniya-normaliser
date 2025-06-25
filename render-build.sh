#!/bin/bash
# Render build script with package verification

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Verify package installation
python - <<'PY'
import importlib.util, pkg_resources, json, pathlib, sys
spec = importlib.util.find_spec("hassy_normalizer")
print("✅ hassy_normalizer found at:", spec.origin, file=sys.stderr)
data_dir = pathlib.Path(spec.origin).parent / "data"
print("📂 data files:", list(data_dir.iterdir()), file=sys.stderr)
PY

echo "Build completed successfully!"