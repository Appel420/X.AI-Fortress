# X.AI Fortress v2.4

X.AI Fortress is a mixed Python, shell, JavaScript, and web project centered on the `FORTRESS.sh` entrypoint, the education UI under `src/edu/`, and the SSH gating scripts under `src/grok-ssh/`.

## Repository layout

- `FORTRESS.sh` — shell entrypoint that launches `src/edu/role.js`
- `src/edu/` — browser and Node-safe role handling for the education UI
- `src/grok-ssh/` — SSH sign-on, add-key, and verification scripts
- `src/crypto/` — native and JavaScript crypto helpers
- `core/` — security, daemon, encryption, and RAG modules
- `requirements.txt` — Python dependencies used by the project and deployment workflow

## Setup

1. Install Python 3.12.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Make the shell entrypoint executable if needed:

   ```bash
   chmod +x FORTRESS.sh src/grok-ssh/*.sh
   ```

4. Run the entrypoint:

   ```bash
   ./FORTRESS.sh
   ```

## Validation

The repository CI uses:

```bash
python -m py_compile Main.py Config.py Quantum_layer.py fullscan_cli.py Code-fix.py Ai-Self-Lie-Director.py AI-Defense-Module.py src/ai_defense_module.py
sh -n FORTRESS.sh src/grok-ssh/sign-on.sh src/grok-ssh/add-key.sh src/grok-ssh/verify.sh
```
