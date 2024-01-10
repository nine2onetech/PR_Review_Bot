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

def need_review_pr_count():
    count = 0
    pull_requests_list = []

    for pull in repo.get_pulls(
        state="open",
        sort="updated"
    ):
        dday_label = [label.name for label in pull.labels if label.name.startswith("D-") or label.name == "OverDue"]
        if not pull.draft and any(label in dday_label for label in [label.name for label in pull.labels]):
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

def _pr_message_to_slack(pr_link, label, title):
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

def switch_is_d_day_auto_decrease():
    repo.delete_variable(variable_name="IS_DDAY_AUTO_DECREASE")
    if IS_DDAY_AUTO_DECREASE == "true":
        repo.create_variable(variable_name="IS_DDAY_AUTO_DECREASE", value="false")
    else:
        repo.create_variable(variable_name="IS_DDAY_AUTO_DECREASE", value="true")

def get_reviewed(pull):
    # Pull Request 작성자 가져오기
    pr_author = pull.user.login

    # 리뷰를 한 사람 리스트 가져오기
    reviews = pull.get_reviews()
    reviewed = [review.user.login for review in reviews if review.user.login != pr_author]

    # 리스트를 set으로 변환하여 중복 제거
    reviewed = list(set(reviewed))

    return reviewed

def get_not_reviewed(pull):
    # Pull Request 작성자 가져오기
    pr_author = pull.user.login

    # 개인 리뷰어와 팀 리뷰어 리스트 가져오기
    requested_reviewers, requested_teams = pull.get_review_requests()
    not_reviewed = [reviewer.login for reviewer in requested_reviewers]

    # 팀 리뷰어의 멤버 추가
    for team in requested_teams:
        team_members = [member.login for member in team.get_members()]
        not_reviewed.extend(team_members)

    # 리스트를 set으로 변환하여 중복 제거
    not_reviewed = list(set(not_reviewed))

    return [reviewer for reviewer in not_reviewed if reviewer != pr_author]

def app():
    count, pulls = need_review_pr_count()
    pr_message_to_slack = (
        f"🥶 [<https://github.com/{ORGANIZATION}/{TARGET_GITHUB_REPO}|{TARGET_GITHUB_REPO}>] 에 총 {count}개의 Pull Request가 리뷰를 기다리고 있어요!\n"
    ) if count > 0 else (
        f":sparkles: [<https://github.com/{ORGANIZATION}/{TARGET_GITHUB_REPO}|{TARGET_GITHUB_REPO}>] 에 남아 있는 PR이 없어요! :robot_face:\n"
    )

    if count > 0:
        for pull in pulls:
            pr_link = make_pr_link(pull.number)

            dday_label = [label.name for label in pull.labels if label.name.startswith("D-") or label.name == "OverDue"]

            if any(label in dday_label for label in [label.name for label in pull.labels]):
                if get_not_reviewed(pull):
                    message_reviewers = f"  리뷰 해주세요! {get_not_reviewed(pull)}"
                else:
                    message_reviewers = f"  리뷰가 완료되었어요. 확인해주세요! {pull.user.login}"    

            before_label = dday_label[0] if len(dday_label) > 0 else ''
            after_label = decreased_label(before_label)

            if IS_DDAY_AUTO_DECREASE == 'true':
                set_changed_label(pull, before_label, after_label)
                pr_message_to_slack += _pr_message_to_slack(pr_link, after_label, pull.title)
            else:
                pr_message_to_slack += _pr_message_to_slack(pr_link, before_label, pull.title)
            pr_message_to_slack += message_reviewers + "\n"

    send_slack(pr_message_to_slack)
    switch_is_d_day_auto_decrease()

if __name__ == "__main__":
    auth = Auth.Token(G_ACCESS_TOKEN)
    g = Github(auth=auth)
    repo = g.get_repo(ORGANIZATION + "/" + TARGET_GITHUB_REPO)
    labels = repo.get_labels()

    app()

    g.close()
