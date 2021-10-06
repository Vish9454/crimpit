#!/bin/bash
source /home/ubuntu/jenkins/workspace/Crimpit-backend-python-dev/venv/bin/activate && cd /home/ubuntu/jenkins/workspace/Crimpit-backend-python-dev && python daily_check.py >> cronjobreport
source /home/ubuntu/jenkins/workspace/Crimpit-backend-python-dev/venv/bin/activate && cd /home/ubuntu/jenkins/workspace/Crimpit-backend-python-dev && python remove_expo_file.py >> cronexpojobreport