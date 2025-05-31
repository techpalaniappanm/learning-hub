
## Find the python bash directory
```bash
  which python3.12
```

## Write the pip installations to requirements.txt in a virtual environment
```bash
  source .venv/bin/activate
  pip freeze > requirements.txt
  deactivate
```

## Verify installation
```bash
 source .venv/bin/activate
 pip list | grep -i whisper
 deactivate
```

## Set the virtual environment
```bash
  python3.12 -m venv .venv
```

