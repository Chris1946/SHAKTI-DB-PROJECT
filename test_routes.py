import sys
import os
sys.path.insert(0, os.path.abspath('backend'))
from app.main import app

for route in app.routes:
    print(getattr(route, "path", route.name))
