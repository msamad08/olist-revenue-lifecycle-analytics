#!/usr/bin/env bash
# Downloads the Olist datasets into data/raw/.
# Preferred: Kaggle CLI (requires ~/.kaggle/kaggle.json).
#   - Brazilian E-Commerce Public Dataset by Olist
#   - Marketing Funnel by Olist
# Both are released by Olist under CC BY-NC-SA 4.0.
set -euo pipefail
mkdir -p data/raw
if command -v kaggle >/dev/null 2>&1; then
  kaggle datasets download -d olistbr/brazilian-ecommerce -p data/raw --unzip
  kaggle datasets download -d olistbr/marketing-funnel-olist -p data/raw --unzip
else
  echo "Kaggle CLI not found. Install with 'pip install kaggle' and add your API token,"
  echo "or download both datasets manually from kaggle.com/olistbr and unzip into data/raw/."
  exit 1
fi
ls -1 data/raw
