name: Build site data

on:
  push:
    branches:
      - main
  workflow_dispatch:

permissions:
  contents: write

jobs:
  build:
    if: github.actor != 'github-actions[bot]'
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Build site data
        run: python3 Erdosproblems-llm-hunter/build_site.py

      - name: Commit generated data
        run: |
          git status --porcelain
          if [ -z "$(git status --porcelain)" ]; then
            echo "No changes to commit."
            exit 0
          fi
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add Erdosproblems-llm-hunter/docs/data
          git commit -m "Auto-build site data [skip ci]"
          git push
