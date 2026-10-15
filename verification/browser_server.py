import os
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1]
os.environ['BMC_WEB_UI_WORKSPACE_DIR']=str(root/'verification'/'browser-workspace')
os.environ['BMC_MAIN_PROGRAM_DIR']=str(root/'verification'/'browser-main')
sys.path.insert(0,str(root/'web_ui'))
from app import app
app.run(host='127.0.0.1',port=5127,debug=False,use_reloader=False)
