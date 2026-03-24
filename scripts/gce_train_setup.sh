#!/usr/bin/env bash
set -euo pipefail

# === DiffSinger GCE/Cloud Training Setup ===
# All singer-specific values are configurable via environment variables.
# Example:
#   SINGER_NAME=my_singer BINARY_ZIP=~/my_singer_binary.zip bash scripts/gce_train_setup.sh

SINGER_NAME="${SINGER_NAME:?Set SINGER_NAME (e.g. my_singer)}"
BINARY_ZIP="${BINARY_ZIP:-/home/$USER/${SINGER_NAME}_binary.zip}"
DIFFSINGER_DIR="${DIFFSINGER_DIR:-/home/$USER/DiffSinger}"
CONFIG_FILE="${CONFIG_FILE:-}"
DICTIONARY_FILE="${DICTIONARY_FILE:-}"

echo "=== DiffSinger GCE Training Setup ==="
echo "Singer: ${SINGER_NAME}"

# Clone DiffSinger
if [ ! -d "${DIFFSINGER_DIR}" ]; then
  git clone https://github.com/openvpi/DiffSinger.git "${DIFFSINGER_DIR}"
fi
cd "${DIFFSINGER_DIR}"

# Install dependencies
pip install -q lightning~=2.3.0 librosa==0.9.2 scipy>=1.10.0 pyworld==0.3.4 \
    praat-parselmouth==0.4.3 einops>=0.7.0 onnx~=1.16.0 tensorboardX \
    torchmetrics click tqdm PyYAML h5py MonkeyType==23.3.0

# Unzip binary data
if [ ! -f "${BINARY_ZIP}" ]; then
  echo "ERROR: Binary zip not found at ${BINARY_ZIP}"
  echo "Upload your binarized dataset first."
  exit 1
fi
mkdir -p "data/${SINGER_NAME}"
unzip -o "${BINARY_ZIP}" -d "data/${SINGER_NAME}/"

# Download vocoder
VOCODER_DIR="checkpoints/pc_nsf_hifigan_44.1k_hop512_128bin_2025.02"
if [ ! -d "$VOCODER_DIR" ]; then
  echo "Downloading vocoder..."
  python3 - <<'PY'
import json, urllib.request, zipfile, os
api_url = 'https://api.github.com/repos/openvpi/vocoders/releases/tags/pc-nsf-hifigan-44.1k-hop512-128bin-2025.02'
with urllib.request.urlopen(api_url) as resp:
    release = json.loads(resp.read())
asset = [a for a in release['assets']
         if 'onnx' not in a['name'].lower()
         and 'openutau' not in a['name'].lower()
         and 'oudep' not in a['name'].lower()][0]
zip_path = f"/tmp/{asset['name']}"
urllib.request.urlretrieve(asset['browser_download_url'], zip_path)
with zipfile.ZipFile(zip_path, 'r') as z:
    z.extractall('checkpoints/')
os.remove(zip_path)
print('Vocoder downloaded.')
PY
fi

# Copy dictionary if provided, otherwise expect it in the binary zip
if [ -n "${DICTIONARY_FILE}" ] && [ -f "${DICTIONARY_FILE}" ]; then
  mkdir -p dictionaries
  cp "${DICTIONARY_FILE}" dictionaries/
  echo "Dictionary copied from ${DICTIONARY_FILE}"
fi

# Copy training config if provided
if [ -n "${CONFIG_FILE}" ] && [ -f "${CONFIG_FILE}" ]; then
  cp "${CONFIG_FILE}" "configs/${SINGER_NAME}_acoustic.yaml"
  echo "Config copied from ${CONFIG_FILE}"
else
  echo "No CONFIG_FILE provided — write your config to configs/${SINGER_NAME}_acoustic.yaml"
fi

echo "=== Setup complete ==="
echo "Binary data:"
ls -lh "data/${SINGER_NAME}/binary/" 2>/dev/null || echo "  (no binary/ subdirectory found)"
echo "Vocoder:"
ls checkpoints/pc_nsf_hifigan_44.1k_hop512_128bin_2025.02/
