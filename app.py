# This is a PyThon Flask app to listen for PR updates in the GitHub
# PyTorch repository. Webhooks PRs that satisfy the conditions set
# below trigger an Azure Pipelines run for running PyTorch custom
# tests on the PR's appropriate artifact(s).

import os
import sys
import requests
import json
from flask import Flask, request, abort, jsonify, render_template
from datetime import datetime
app = Flask(__name__)

# Azure DevOps WebHook trigger variables
AZURE_DEVOPS_BASE_WEBHOOK_URL = "https://dev.azure.com/aiinfra/_apis/public/distributedtask/webhooks/"
AZURE_DEVOPS_TRIGGER_NAME = "GitHubPyTorchPRTrigger"
AZURE_DEVOPS_TRIGGER_ADD_ON = "?api-version=6.0-preview"
TRIGGER_URL = AZURE_DEVOPS_BASE_WEBHOOK_URL + AZURE_DEVOPS_TRIGGER_NAME + AZURE_DEVOPS_TRIGGER_ADD_ON

# List of GitHub PyTorch branches we are currently tracking for custom tests
GITHUB_PYTORCH_TRACKED_BRANCHES = ("master")

# Submitted payloads to Azure DevOps
submitted_payloads_history = []
jsons_of_triggered_prs = {}

@app.route("/")
def index():
    return "Running..."

@app.route("/prwebhook", methods=['POST'])
def github_webhook_endpoint():
    # Parse GitHub WebHook data, check if received JSON is valid.
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
    # If the payload is not of an updated or newly opened PR, ignore.
    if github_webhook_data["action"] != "opened" and github_webhook_data["action"] != "synchronize":
        return "PR WebHook update is not that of a new opened or updated PR. Exiting..."
    # If the payload is of a PR that is marked as draft, ignore.
    if github_webhook_data["pull_request"]["draft"] == True:
        return "PR is marked as draft. Exiting..."
    pr_base_ref = github_webhook_data["pull_request"]["base"]["ref"]
    pr_number = github_webhook_data["pull_request"]["number"]
    target_commit = github_webhook_data["pull_request"]["head"]["sha"]
    # If the payload is of a PR not targeted tracked branches, ignore.
    if pr_base_ref not in GITHUB_PYTORCH_TRACKED_BRANCHES:
        return "PR does not target a targeted PyTorch branch. Exiting..."

    # If the PR is an internal PR (pytorch/pytorch branch --> pytorch/pytorch master),
    # then report full branch name as target branch to check. Else, report PR number
    # in CircleCI format (i.e. refs/pull/12345/head)
    if github_webhook_data["pull_request"]["head"]["repo"]["full_name"] == "pytorch/pytorch":
        target_branch_to_check = github_webhook_data["pull_request"]["head"]["ref"]
    else:
        target_branch_to_check = "refs/pull/{0}/head".format(pr_number)

    # Build and send HTTP POST Trigger
    s = requests.Session()
    s.headers.update({"Authorization": "None"})
    run_build_raw = s.post(TRIGGER_URL, json={
        "repositoryName": "pytorch_tests",
        "PR_NUMBER": pr_number,
        "TARGET_COMMIT": target_commit,
        "TARGET_BRANCH_TO_CHECK_AZ_DEVOPS_PR": target_branch_to_check
    })

    # Add trigger to submitted payloads history list
    submitted_payloads_history.append({"datetime": datetime.now().strftime("%m/%d/%Y %H:%M:%S")+" PDT", "pr_number": pr_number, "target_branch": target_branch_to_check, "target_commit": target_commit})
    jsons_of_triggered_prs[pr_number] = github_webhook_data

    return "Build submitted for PR #{0} for CircleCI branch: {1} and commit {2}.".format(pr_number, target_branch_to_check, target_commit[:7])

@app.route("/pulls", methods=['GET'])
def display_submitted_payloads_history():
    return render_template('pulls_view.html', submitted_payloads_history=submitted_payloads_history)

@app.route("/jsons/<int:pr_number>", methods=['GET'])
def display_submitted_jsons_history(pr_number):
    if pr_number not in jsons_of_triggered_prs:
        return "JSON of PR #{0} not found".format(pr_number)
    return jsons_of_triggered_prs[pr_number]
