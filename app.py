import json
from github import Github
from github import Auth
import os
import requests

G_ACCESS_TOKEN = os.getenv("G_ACCESS_TOKEN")
SLACK_INCOMING_WEBHOOK = os.getenv("SLACK_INCOMING_WEBHOOK")
TARGET_GITHUB_REPO = os.getenv("TARGET_GITHUB_REPO")
IS_DDAY_AUTO_DECREASE = os.getenv("IS_DDAY_AUTO_DECREASE")
ORGANIZATION = os.getenv("ORGANIZATION")

def total_pull_requests():
    count = 0
    pull_requests_list = []

    for pull in repo.get_pulls(
        state="open",
        sort="updated"
    ):
        pull_requests_list.append(pull)
        count += 1
    return count, pull_requests_list

def make_pr_link(no):
    return f"https://github.com/{ORGANIZATION}/{TARGET_GITHUB_REPO}/pull/{no}"

def decreased_label(label):
    if label == '':
        return ''
    elif label == 'D-3':
        return 'D-2'
    elif label == 'D-2':
        return 'D-1'
    elif label == 'D-1':
        return 'D-0'
    elif label == 'D-0':
        return 'OverDue'

def set_changed_label(pull, before_label, after_label):
    if not after_label or after_label == '': # 변경점 없음
        return

    pull.remove_from_labels(before_label)
    pull.set_labels(after_label)

def pr_message_to_slack(pr_link, label, title):
    if not label or label == '':  # 변경점 없음
        return ''
    return f'[`{label}`] <{pr_link}|{title}>\n'

def send_slack(message):
    header = {'Content-type': 'application/json'}

    data = {
        "blocks": [
            {
                "type": "section",
                "text": {
                        "type": "mrkdwn",
                        "text": message
                }
            }
        ]
    }

    return requests.post(
        SLACK_INCOMING_WEBHOOK, 
        data=json.dumps(data),
        headers=header
    )

def app():
    count, pulls = total_pull_requests()
    pr_message_to_slack = (
        f"🥶 [<https://github.com/{ORGANIZATION}/{TARGET_GITHUB_REPO}|{TARGET_GITHUB_REPO}>] 에 총 {count}개의 Pull Request가 리뷰를 기다리고 있어요!\n"
    ) if count > 0 else (
        f":sparkles: [<https://github.com/{ORGANIZATION}/{TARGET_GITHUB_REPO}|{TARGET_GITHUB_REPO}>] 에 남아 있는 PR이 없어요! :robots:\n"
    )

    if count > 0:
        for pull in pulls:
            pr_link = make_pr_link(pull.number)

            dday_label = list(filter(lambda x: x.name.startswith("D-") or x.name == "OverDue", pull.labels))

            before_label = dday_label[0].name if len(dday_label) > 0 else ''
            after_label = decreased_label(before_label)

            if IS_DDAY_AUTO_DECREASE == 'true':
                set_changed_label(pull, before_label, after_label)
                pr_message_to_slack += pr_message_to_slack(pr_link, after_label, pull.title)
            else:
                pr_message_to_slack += pr_message_to_slack(pr_link, before_label, pull.title)

    send_slack(pr_message_to_slack)

if __name__ == "__main__":
    print(":warning:", G_ACCESS_TOKEN)
    print(":warning:", SLACK_INCOMING_WEBHOOK)
    print(":warning:", TARGET_GITHUB_REPO)
    print(":warning:", IS_DDAY_AUTO_DECREASE)
    print(":warning:", ORGANIZATION)

    auth = Auth.Token(G_ACCESS_TOKEN)
    g = Github(auth=auth)
    repo = g.get_repo(ORGANIZATION + "/" + TARGET_GITHUB_REPO)
    labels = repo.get_labels()

    app()

    # To close connections after use
    g.close()