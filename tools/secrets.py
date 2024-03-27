import json
import os

import requests
from decouple import config


def get_botcity_secret(label, key, access_token, organization):
    url = f"https://figueiredo.botcity.dev/api/v2/credential/{label}/key/{key}"
    headers = {
        "accept": "*/*",
        "organization": organization,
        "token": access_token,
    }
    response = requests.get(url, headers=headers)
    return response.text


def botcity_login():
    url = "https://figueiredo.botcity.dev/api/v2/workspace/login"
    headers = {"content-type": "application/json"}
    login = config("LOGIN")
    key = config("KEY")
    if login and key:
        data = {"login": login, "key": key}
        data_json = json.dumps(data)
        response = requests.post(url, headers=headers, data=data_json)
        os.environ["ACCESS_LOGIN_BOTCITY"] = response.json()["accessToken"]
        os.environ["ACCESS_ORGANIZATION_BOTCITY"] = response.json()["organizationLabel"]
        return response.json()["accessToken"], response.json()["organizationLabel"]
    else:
        raise ValueError("LOGIN or KEY not set")


def get_secret(vault, key, label=None):
    if vault == "botcity":
        access = os.environ.get("ACCESS_LOGIN_BOTCITY")
        if access:
            organization = os.environ.get("ACCESS_ORGANIZATION_BOTCITY")
        else:
            access, organization = botcity_login()
        return get_botcity_secret(
            label=label, key=key, access_token=access, organization=organization
        )
    else:
        raise ValueError("vault not supported")


if __name__ == "__main__":
    print(get_secret(vault="botcity", label="db_log", key="password"))
