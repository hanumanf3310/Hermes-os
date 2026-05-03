#!/bin/bash
# Template: Create RAG Tools Venv for Hermes OS
# Usage: rtk run "bash create-rag-venv.sh"

set -e

echo "🚀 Creating RAG Tools Venv for Hermes OS"
echo "=========================================="

VENV_PATH="${HOME}/.hermes/rag-venv"

echo ""
echo "📦 Step 1: Creating venv at ${VENV_PATH}..."
python3 -m venv "${VENV_PATH}" --system-site-packages

echo ""
echo "✅ Step 2: Verifying venv..."
"${VENV_PATH}/bin/python" --version
"${VENV_PATH}/bin/pip" --version

echo ""
echo "📥 Step 3: Installing LanceDB..."
"${VENV_PATH}/bin/pip" install -q lancedb

echo ""
echo "📥 Step 4: Installing Sentence-Transformers..."
"${VENV_PATH}/bin/pip" install -q sentence-transformers

echo ""
echo "🧪 Step 5: Verifying installations..."
"${VENV_PATH}/bin/python" -c "import lancedb; print(f'✅ LanceDB: {lancedb.__version__}')"
"${VENV_PATH}/bin/python" -c "import sentence_transformers; print(f'✅ Sentence-Transformers: {sentence_transformers.__version__}')"

echo ""
echo "=========================================="
echo "✅ RAG venv ready at: ${VENV_PATH}"
echo ""
echo "Usage:"
echo "  ${VENV_PATH}/bin/python script.py"
echo "  source ${VENV_PATH}/bin/activate && python script.py"
echo "=========================================="
