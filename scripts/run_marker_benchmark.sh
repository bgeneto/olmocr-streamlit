#!/bin/bash

# Runs marker benchmark, measuring both olmOCR-bench performance and per document processing performance
#   ./scripts/run_marker_benchmark.sh
#   ./scripts/run_marker_benchmark.sh 1.7.5

set -e

# Parse command line arguments
MARKER_VERSION="${1:-1.7.5}"
echo "Using marker version: $MARKER_VERSION"

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo "Error: There are uncommitted changes in the repository."
    echo "Please commit or stash your changes before running the benchmark."
    echo ""
    echo "Uncommitted changes:"
    git status --short
    exit 1
fi

# Use conda environment Python if available, otherwise use system Python
if [ -n "$CONDA_PREFIX" ]; then
    PYTHON="$CONDA_PREFIX/bin/python"
    echo "Using conda Python from: $CONDA_PREFIX"
else
    PYTHON="python"
    echo "Warning: No conda environment detected, using system Python"
fi

# Get version from version.py
VERSION=$($PYTHON -c 'import olmocr.version; print(olmocr.version.VERSION)')
echo "OlmOCR version: $VERSION"

# Get first 10 characters of git hash
GIT_HASH=$(git rev-parse HEAD | cut -c1-10)
echo "Git hash: $GIT_HASH"

# Get current git branch name
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "Git branch: $GIT_BRANCH"

# Create full image tag
IMAGE_TAG="olmocr-benchmark-${VERSION}-${GIT_HASH}"
echo "Building Docker image with tag: $IMAGE_TAG"

# Build the Docker image
echo "Building Docker image..."
docker build --platform linux/amd64 -f ./Dockerfile -t $IMAGE_TAG .

# Get Beaker username
BEAKER_USER=$(beaker account whoami --format json | jq -r '.[0].name')
echo "Beaker user: $BEAKER_USER"

# Push image to beaker
echo "Trying to push image to Beaker..."
if ! beaker image create --workspace ai2/oe-data-pdf --name $IMAGE_TAG $IMAGE_TAG 2>/dev/null; then
    echo "Warning: Beaker image with tag $IMAGE_TAG already exists. Using existing image."
fi

# Create Python script to run beaker experiment
cat << 'EOF' > /tmp/run_benchmark_experiment.py
import sys
from beaker import Beaker, ExperimentSpec, TaskSpec, TaskContext, ResultSpec, TaskResources, ImageSource, Priority, Constraints, EnvVar

# Get image tag, beaker user, git branch, git hash, and marker version from command line
image_tag = sys.argv[1]
beaker_user = sys.argv[2]
git_branch = sys.argv[3]
git_hash = sys.argv[4]
marker_version = sys.argv[5]

# Initialize Beaker client
b = Beaker.from_env(default_workspace="ai2/olmocr")


# Check if AWS credentials secret exists
aws_creds_secret = f"{beaker_user}-AWS_CREDENTIALS_FILE"
try:
    # Try to get the secret to see if it exists
    b.secret.get(aws_creds_secret, workspace="ai2/olmocr")
    has_aws_creds = True
    print(f"Found AWS credentials secret: {aws_creds_secret}")
except:
    has_aws_creds = False
    print(f"AWS credentials secret not found: {aws_creds_secret}")

# First experiment: Original benchmark job
commands = []
if has_aws_creds:
    commands.extend([
        "mkdir -p ~/.aws",
        'echo "$AWS_CREDENTIALS_FILE" > ~/.aws/credentials'
    ])
commands.extend([
    "git clone https://huggingface.co/datasets/allenai/olmOCR-bench",
    "cd olmOCR-bench && git lfs pull && cd ..",
    f"pip install marker-pdf=={marker_version}",
    "pip install --upgrade torchvision",
    "python -m olmocr.bench.convert marker --dir ./olmOCR-bench/bench_data",
    "python -m olmocr.bench.benchmark --dir ./olmOCR-bench/bench_data"
])

# Build task spec with optional env vars
task_spec_args = {
    "name": "marker-benchmark",
    "image": ImageSource(beaker=f"{beaker_user}/{image_tag}"),
    "command": [
        "bash", "-c",
        " && ".join(commands)
    ],
    "context": TaskContext(
        priority=Priority.normal,
        preemptible=True,
    ),
    "resources": TaskResources(gpu_count=1),
    "constraints": Constraints(cluster=["ai2/ceres-cirrascale", "ai2/jupiter-cirrascale-2"]),
    "result": ResultSpec(path="/noop-results"),
}

# Add env vars if AWS credentials exist
if has_aws_creds:
    task_spec_args["env_vars"] = [
        EnvVar(name="AWS_CREDENTIALS_FILE", secret=aws_creds_secret)
    ]

# Create first experiment spec
experiment_spec = ExperimentSpec(
    description=f"Marker {marker_version} Benchmark Run - Branch: {git_branch}, Commit: {git_hash}",
    budget="ai2/oe-data",
    tasks=[TaskSpec(**task_spec_args)],
)

# Create the first experiment
experiment = b.experiment.create(spec=experiment_spec, workspace="ai2/olmocr")
print(f"Created benchmark experiment: {experiment.id}")
print(f"View at: https://beaker.org/ex/{experiment.id}")
print("-------")
print("")


perf_commands = []
if has_aws_creds:
    perf_commands.extend([
        "mkdir -p ~/.aws",
        'echo "$AWS_CREDENTIALS_FILE" > ~/.aws/credentials'
    ])
perf_commands.extend([
    f"pip install marker-pdf=={marker_version}",
    "pip install --upgrade torchvision",
    "pip install awscli",
    "aws s3 cp --recursive s3://ai2-oe-data/jakep/olmocr/olmOCR-mix-0225/benchmark_set/ /root/olmOCR-mix-0225_benchmark_set/",
    # Tried with workers 8, but it was taking a really huge amount of time
    #"time marker --force_ocr /root/olmOCR-mix-0225_benchmark_set/ --output_dir /root/olmOCR-mix-0225_benchmark_set_marker --workers 8"
    "time marker --force_ocr /root/olmOCR-mix-0225_benchmark_set/ --output_dir /root/olmOCR-mix-0225_benchmark_set_marker"
])

# Build performance task spec
perf_task_spec_args = {
    "name": "marker-performance",
    "image": ImageSource(beaker=f"{beaker_user}/{image_tag}"),
    "command": [
        "bash", "-c",
        " && ".join(perf_commands)
    ],
    "context": TaskContext(
        priority=Priority.normal,
        preemptible=True,
    ),
    "resources": TaskResources(gpu_count=1),
    "constraints": Constraints(cluster=["ai2/ceres-cirrascale", "ai2/jupiter-cirrascale-2"]),
    "result": ResultSpec(path="/noop-results"),
}

# Add env vars if AWS credentials exist
if has_aws_creds:
    perf_task_spec_args["env_vars"] = [
        EnvVar(name="AWS_CREDENTIALS_FILE", secret=aws_creds_secret)
    ]

# Create performance experiment spec
perf_experiment_spec = ExperimentSpec(
    description=f"Marker {marker_version} Performance Test - Branch: {git_branch}, Commit: {git_hash}",
    budget="ai2/oe-data",
    tasks=[TaskSpec(**perf_task_spec_args)],
)

# Create the performance experiment
perf_experiment = b.experiment.create(spec=perf_experiment_spec, workspace="ai2/olmocr")
print(f"Created performance experiment: {perf_experiment.id}")
print(f"View at: https://beaker.org/ex/{perf_experiment.id}")
EOF

# Run the Python script to create the experiments
echo "Creating Beaker experiments..."
$PYTHON /tmp/run_benchmark_experiment.py $IMAGE_TAG $BEAKER_USER $GIT_BRANCH $GIT_HASH $MARKER_VERSION

# Clean up temporary file
rm /tmp/run_benchmark_experiment.py

echo "Benchmark experiments submitted successfully!"