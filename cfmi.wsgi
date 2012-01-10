import sys
import os

sys.stdin = sys.stdout

BASE_DIR = os.path.join(os.path.dirname(__file__))
sys.path.append(BASE_DIR)

import production_settings

from cfmi import create_app

application = create_app(production_settings)

if __name__ == '__main__':
   application.run()
