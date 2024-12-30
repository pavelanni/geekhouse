#!/bin/bash
# ./deploy/deploy.sh
set -e

# Get the project root directory (parent of deploy dir)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_DIR="$PROJECT_ROOT/deploy"
CONFIG_DIR="$PROJECT_ROOT/config"

echo "Deploying from project root: $PROJECT_ROOT"

# Convert TOML to JSON
echo "Converting config.toml to JSON..."
python "$DEPLOY_DIR/toml_to_json.py" --output "$CONFIG_DIR/config.json" "$CONFIG_DIR/config.toml"

if [ $? -ne 0 ]; then
    echo "Error: TOML conversion failed"
    exit 1
fi

# Change to project root for relative paths in requirements.txt
cd "$PROJECT_ROOT" || exit 1

# Install dependencies from requirements.txt
echo "Installing dependencies..."
while IFS= read -r lib || [ -n "$lib" ]; do
    # Skip empty lines and comments
    [[ $lib =~ ^[[:space:]]*$ || $lib =~ ^#.*$ ]] && continue
    echo "Installing $lib..."
    mpremote mip install "$lib"
done <mp_requirements.txt

# Copy the lcd1602 library
echo "Copying lcd1602 library..."
mpremote cp -r lib/lcd1602.py :

# Copy source files
echo "Copying source files..."
mpremote cp -r src/server/* :

# Copy converted config
echo "Copying config..."
mpremote cp "$CONFIG_DIR/config.json" :
rm "$CONFIG_DIR/config.json"

# Reset device
echo "Resetting device..."
mpremote reset

echo "Deployment complete!"
