#!/usr/bin/env python3
"""Run the exact pre-APK native overlay sequence and stop after Xingtu Stage F."""
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/android.yml"
ARCHIVE = ROOT / "ShiWanJu-Android-deploy.zip"
SOURCE = ROOT / "source"
ERROR = ROOT / "xingtu_static_validation_error.txt"

def fail(message: str):
    ERROR.write_text(message + "\n", encoding="utf-8")
    raise SystemExit(message)

try:
    import yaml
except ImportError:
    fail("PyYAML is required; install it with: python3 -m pip install pyyaml")

if not ARCHIVE.is_file():
    fail("Missing ShiWanJu-Android-deploy.zip; cannot validate generated Android source")
if not WORKFLOW.is_file():
    fail("Existing Android workflow is missing; cannot mirror its patch order")

try:
    config = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = config["jobs"]["build"]["steps"]
except Exception as exc:
    fail(f"Unable to parse Android workflow steps: {exc}")

# Stop immediately before version finalization and the APK build. Every native
# overlay Python script before that boundary is executed in the original order.
commands = []
found_boundary = False
for step in steps:
    if step.get("name") == "Finalize Android resources and version":
        found_boundary = True
        break
    run = step.get("run")
    if isinstance(run, str):
        commands.extend(re.findall(r"(?m)^\s*python3\s+native-overlay/([A-Za-z0-9_.-]+\.py)\s*$", run))

if not found_boundary:
    fail("Could not find the pre-build boundary 'Finalize Android resources and version'")

expected = [
    "create_redesigned_xingtu_editor.py",
    "apply_redesigned_xingtu_stage_c.py",
    "apply_redesigned_xingtu_stage_d.py",
    "apply_redesigned_xingtu_stage_e.py",
    "audit_redesigned_xingtu_stage_f.py",
]
if len(commands) != len(set(commands)) or commands[-len(expected):] != expected:
    fail("Extracted patch sequence is duplicated or Stage C-F are not the final pre-build steps: " + repr(commands))
if not commands:
    fail("No native overlay patch scripts were discovered")

if SOURCE.exists():
    import shutil
    shutil.rmtree(SOURCE)
SOURCE.mkdir(parents=True)
with zipfile.ZipFile(ARCHIVE) as archive:
    archive.extractall(SOURCE)

project = SOURCE / "ShiWanJu-Android"
if not (project / "app/build.gradle.kts").is_file():
    fail("Extracted source does not contain source/ShiWanJu-Android/app/build.gradle.kts")

print(f"Extracted Android source. Executing {len(commands)} pre-APK overlay scripts.")
for index, name in enumerate(commands, 1):
    script = ROOT / "native-overlay" / name
    if not script.is_file():
        fail(f"Workflow references missing patch script: {name}")
    print(f"[{index}/{len(commands)}] {name}", flush=True)
    result = subprocess.run([sys.executable, str(script)], cwd=ROOT)
    if result.returncode:
        fail(f"Patch sequence stopped at {name} with exit code {result.returncode}")

editor = project / "app/src/main/java/com/shiwanju/app/ui/ArticleEditorRedesignedScreen.kt"
if not editor.is_file():
    fail("Stage F returned success but redesigned editor source was not generated")
ERROR.unlink(missing_ok=True)
print("PASS: all pre-APK patch scripts and Stage F static audit completed.")
print("STOP: no Gradle, Kotlin compilation, APK build, packaging, or upload was run.")
