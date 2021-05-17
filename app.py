import os
import sys
import requests
import json
from flask import Flask, request, abort, jsonify
app = Flask(__name__)

# Azure DevOps WebHook trigger variables
AZURE_DEVOPS_BASE_WEBHOOK_URL = "https://dev.azure.com/aiinfra/_apis/public/distributedtask/webhooks/"
AZURE_DEVOPS_TRIGGER_NAME = "GitHubPyTorchPRTrigger"
AZURE_DEVOPS_TRIGGER_ADD_ON = "?api-version=6.0-preview"
TRIGGER_URL = AZURE_DEVOPS_BASE_WEBHOOK_URL + AZURE_DEVOPS_TRIGGER_NAME + AZURE_DEVOPS_TRIGGER_ADD_ON

# List of GitHub PyTorch branches we are currently tracking for custom tests
GITHUB_PYTORCH_TRACKED_BRANCHES = ("master")

@app.route("/")
def index():
    return "Running..."

@app.route("/prwebhook", methods=['POST'])
def github_webhook_endpoint():
    # Parse GitHub WebHook data
    github_webhook_data = request.get_json()
    if github_webhook_data is None:
        abort(400, "Received JSON is NoneType")
    if "pull_request" not in github_webhook_data:
        abort(400, "JSON does not contain PR details")
    if "number" not in github_webhook_data["pull_request"]:
        abort(400, "JSON does not contain PR number details")
    if "base" not in github_webhook_data["pull_request"]:
        abort(400, "JSON does not contain PR base details")
    if "ref" not in github_webhook_data["pull_request"]["base"]:
        abort(400, "JSON does not contain PR base ref details")
    # Upon setting a WebHook in a GitHub repo, GitHub sends a first
    # test payload. The test payload does not have an 'action' field.
    if "action" not in github_webhook_data:
        return "JSON does not contain PR action data. This may be a GitHub test payload. Exiting..."

    # Obtain PyTorch PR information
    pr_base_ref = github_webhook_data["pull_request"]["base"]["ref"]
    pr_number = github_webhook_data["pull_request"]["number"]
    if github_webhook_data["action"] != "opened" and github_webhook_data["action"] != "synchronize":
        return "PR WebHook update is not that of a new opened or updated PR. Exiting..."
    if pr_base_ref not in GITHUB_PYTORCH_TRACKED_BRANCHES:
        return "PR does not target a targeted PyTorch branch. Exiting..."

    # Build and send HTTP POST Trigger
    s = requests.Session()
    s.headers.update({"Authorization": "None"})
    run_build_raw = s.post(TRIGGER_URL, json={
        "repositoryName": "pytorch_tests",
        "TARGET_BRANCH_TO_CHECK_AZ_DEVOPS_PR": "refs/pull/{0}/head".format(pr_number)
    })
    return "Build submitted"
