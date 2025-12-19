# Unit tests

Run from your project root:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Notes:
- Tests focus on non-GUI modules (state/temp paths/validator).
- `test_passport_photo_helpers.py` is optional and will auto-skip if cv2/mediapipe aren't installed.
