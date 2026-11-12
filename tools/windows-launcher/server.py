from pathlib import Path
import sys
root = Path(__file__).resolve().parents[1] / 'BMCAgent'
sys.path.insert(0, str(root / 'web_ui'))
from app import app
app.run(host='0.0.0.0' if '--lan' in sys.argv else '127.0.0.1', port=5000, debug=False, use_reloader=False, threaded=True)
