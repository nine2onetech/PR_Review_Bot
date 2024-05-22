import json
from github import Github
from github import Auth
import os
import requests

G_ACCESS_TOKEN = os.getenv("G_ACCESS_TOKEN")
TARGET_GITHUB_REPO = os.getenv("TARGET_GITHUB_REPO")
IS_DDAY_AUTO_DECREASE = os.getenv("IS_DDAY_AUTO_DECREASE")
ORGANIZATION = os.getenv("ORGANIZATION")

def need_review_pr_count():
    pull_requests_list = []

    for pull in repo.get_pulls(
        state="open",
        sort="updated"
    ):
        dday_label = [label.name for label in pull.labels if label.name.startswith("D-") or label.name == "OverDue"]
        if not pull.draft and any(label in dday_label for label in [label.name for label in pull.labels]):
            pull_requests_list.append(pull)
    return pull_requests_list

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
    elif label == 'OverDue':
        return 'OverDue'
    return label

def set_changed_label(pull, before_label, after_label):
    if not after_label or after_label == '':  # 변경점 없음
        return

    # 현재 라벨들을 가져와서 디데이 라벨만 제거
    current_labels = [label.name for label in pull.labels if not label.name.startswith("D-") and label.name != "OverDue"]
    
    if before_label in current_labels:
        current_labels.remove(before_label)
    
    # 새로운 디데이 라벨 추가
    if after_label:
        current_labels.append(after_label)
    
    # 라벨 업데이트
    pull.set_labels(*current_labels)

def switch_is_d_day_auto_decrease():
    repo.delete_variable(variable_name="IS_DDAY_AUTO_DECREASE")
    if IS_DDAY_AUTO_DECREASE == "true":
        repo.create_variable(variable_name="IS_DDAY_AUTO_DECREASE", value="false")
    else:
        repo.create_variable(variable_name="IS_DDAY_AUTO_DECREASE", value="true")

def app():
    pulls = need_review_pr_count()

    for pull in pulls:
        pr_link = make_pr_link(pull.number)

        dday_label = [label.name for label in pull.labels if label.name.startswith("D-") or label.name == "OverDue"]

        before_label = dday_label[0] if len(dday_label) > 0 else ''
        after_label = decreased_label(before_label)

        if IS_DDAY_AUTO_DECREASE == 'true':
            set_changed_label(pull, before_label, after_label)

    switch_is_d_day_auto_decrease()

if __name__ == "__main__":
    auth = Auth.Token(G_ACCESS_TOKEN)
    g = Github(auth=auth)
    repo = g.get_repo(ORGANIZATION + "/" + TARGET_GITHUB_REPO)
    labels = repo.get_labels()

    app()

    g.close()
