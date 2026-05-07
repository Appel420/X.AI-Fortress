# X.AI FORTRESS -- Internal Only

> One word: **FORTRESS ON**
> One rule: **All in or out**

## Build

```bash
git clone git@github.com:Appel420/X.AI-Fortress.git
cd X.AI-Fortress
pip install -r requirements.txt
./FORTRESS.sh
```

## Voice Gate

Run only after three voices say:

```
/mic on
FORTRESS ON
```

Auto-signs every commit.

## Roles

- `xai.cg` -- ops
- `future.invite` -- vision
- `Appel420` -- root
- `Ara` -- AI (no account -- signs via voice hash)

No merge until all say yes.
No archive. No delete. No leak.

## Project Structure

```
X.AI-Fortress/
├── Main.py                 # Ara Wake Word Detector entry point
├── Config.py               # Centralized configuration & logging
├── Quantum_layer.py        # Quantum-classical hybrid ML model
├── AI-Defense-Module.py     # AI lie detection with crypto alerts
├── Ai-Self-Lie-Director.py  # LLM truth probe / lie detector
├── Code-fix.py              # Self-healing code fixer
├── fullscan_cli.py          # Multi-source syllabic scanner CLI
├── FORTRESS.sh              # Root firewall entry script
├── deploy.yml               # Deployment workflow
├── requirements.txt         # Python dependencies
├── src/
│   ├── ai_defense_module.py # Clean AI defense module
│   ├── crypto/              # BLAKE3 & Argon2 key derivation
│   ├── edu/                 # Educational UI & role management
│   └── grok-ssh/            # Voice-gated SSH signing suite
└── docs/                    # Documentation
```
