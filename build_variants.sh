#!/bin/bash
set -e

rm -rf build dist build_work
mkdir -p dist build_work
mkdir -p build_logs

# Determine Python interpreter
PYTHON_EXE=python3

if [ -z "$GITHUB_ACTIONS" ] && [ ! -f /.dockerenv ]; then
    # Ensure dependencies locally
    if [ ! -d "node_modules" ]; then
        echo "Installing Node.js dependencies..."
        npm install
    fi

    if [ ! -d "venv" ]; then
        echo "Creating virtual environment and installing Python dependencies..."
        python3 -m venv venv
        ./venv/bin/pip install -r requirements.txt
    fi
    
    if [ -d "venv" ]; then
        PYTHON_EXE=./venv/bin/python3
    fi
else
    echo "Running in GitHub Actions, using system Python."
fi

# Define Paths
ABS_PROJECT_ROOT=$(pwd)
SOURCE_FONTS_SRC="${ABS_PROJECT_ROOT}/source_fonts"
WORK_ROOT="${ABS_PROJECT_ROOT}/build_work"
DIST_DIR="${ABS_PROJECT_ROOT}/dist"

# Helper for preparing source
prepare_source() {
    local name=$1
    local features=$2
    echo "Preparing shared source for type '${name}'..."
    
    local src_dir="${WORK_ROOT}/source_${name}"
    mkdir -p "${src_dir}"
    
    # Copy all source fonts (read-only base)
    cp -r "${SOURCE_FONTS_SRC}/"* "${src_dir}/"
    
    node customize_commit_mono.js \
        --input-dir "${src_dir}/fontlab" \
        --output-dir "${src_dir}/commit-mono" \
        --features "${features}" \
        --letter-spacing 0 --line-height 1.0 > "build_logs/prepare_source_${name}.log" 2>&1
        
    echo "  > Shared source '${name}' ready."
}

# 1. Prepare shared sources (Parallel)
echo "=== Step 1: Pre-generating shared assets ==="
FEAT_DEFAULT="ss03,ss04,ss05"
FEAT_LIGATURE="ss01,ss02,ss03,ss04,ss05"

pids=""
(prepare_source "default" "$FEAT_DEFAULT") &
pids="$pids $!"

(prepare_source "ligature" "$FEAT_LIGATURE") &
pids="$pids $!"

# Wait for source prep
failed=0
for pid in $pids; do
    wait $pid || failed=1
done
if [ $failed -ne 0 ]; then
    echo "Error: Source preparation failed. Check build_logs/."
    exit 1
fi

echo "All shared sources prepared."

# Function to build a variant
build_variant_job() {
    local variant_name=$1
    local source_type=$2
    local ff_options=$3
    
    local my_source="${WORK_ROOT}/source_${source_type}"
    local my_build="${WORK_ROOT}/build_${variant_name}"
    local log_file="${ABS_PROJECT_ROOT}/build_logs/${variant_name}.log"
    
    mkdir -p "${my_build}"
    
    echo "  [Started] ${variant_name}"
    
    # Execute in subshell to trap errors and redirect output
    (
        set -e
        # Set Env Vars for Python scripts
        export SOURCE_FONTS_DIR="${my_source}"
        export BUILD_FONTS_DIR="${my_build}"
        
        # 1. Build with FontForge
        fontforge -script fontforge_script.py ${ff_options}
        
        # 2. Post-process with FontTools
        $PYTHON_EXE fonttools_script.py
        
        # 3. Rename and Move to Dist
        for f in ${my_build}/*.ttf; do
            style=""
            if [[ "$f" == *"Regular.ttf" ]]; then style="Regular"; fi
            if [[ "$f" == *"Bold.ttf" ]]; then style="Bold"; fi
            if [[ "$f" == *"Italic.ttf" ]]; then style="Italic"; fi
            if [[ "$f" == *"BoldItalic.ttf" ]]; then style="BoldItalic"; fi
            
            if [ -n "$style" ]; then
                new_name="${variant_name}-${style}.ttf"
                cp "$f" "${DIST_DIR}/${new_name}"
            fi
        done
        
        $PYTHON_EXE -c "import zipfile, glob, os; \
            z = zipfile.ZipFile('${DIST_DIR}/${variant_name}.zip', 'w', zipfile.ZIP_DEFLATED); \
            files = glob.glob('${DIST_DIR}/${variant_name}-*.ttf'); \
            [z.write(f, os.path.basename(f)) for f in files]; \
            z.close()"
            
    ) > "${log_file}" 2>&1
    
    if [ $? -eq 0 ]; then
        echo "  [Success] ${variant_name}"
    else
        echo "  [FAILED ] ${variant_name} (See ${log_file})"
        return 1
    fi
}

echo "=== Step 2: Running parallel builds ==="
build_pids=""

# --- Group A: Default (No Ligatures) ---
(build_variant_job "StagedMono35NF" "default" "--nerd-font --jpdoc") &
build_pids="$build_pids $!"

(build_variant_job "StagedMono35NFConsole" "default" "--nerd-font") &
build_pids="$build_pids $!"

(build_variant_job "StagedMonoNF" "default" "--nerd-font --half-width --jpdoc") &
build_pids="$build_pids $!"

(build_variant_job "StagedMonoNFConsole" "default" "--nerd-font --half-width") &
build_pids="$build_pids $!"

# --- Group B: Ligature (With Ligatures) ---
(build_variant_job "StagedMono35LigNF" "ligature" "--nerd-font --jpdoc") &
build_pids="$build_pids $!"

(build_variant_job "StagedMono35LigNFConsole" "ligature" "--nerd-font") &
build_pids="$build_pids $!"

(build_variant_job "StagedMonoLigNF" "ligature" "--nerd-font --half-width --jpdoc") &
build_pids="$build_pids $!"

(build_variant_job "StagedMonoLigNFConsole" "ligature" "--nerd-font --half-width") &
build_pids="$build_pids $!"

# Wait for all builds
failed_builds=0
for pid in $build_pids; do
    wait $pid || failed_builds=$((failed_builds + 1))
done

if [ $failed_builds -eq 0 ]; then
    echo "=== Step 3: All builds completed successfully! ==="
    echo "Artifacts in dist/:"
    ls -1 dist/*.zip
    
    # Cleanup work dir
    rm -rf build_work
else
    echo "=== Step 3: Build completed with ${failed_builds} failures. ==="
    echo "Please check build_logs/ for details."
    exit 1
fi
