# PyTorch PR Listener

This is a Flask app deployed at https://pytorch-pr-web-service.azurewebsites.net that can listen for PyTorch PR updates.

To run locally:
```bash
# Create and start virtual environment
python3 -m venv venv
source venv/bin/activate
# Install dependencies
pip install -r requirements.txt
# Run Flaskapp locally
FLASK_APP=app:app flask run
```