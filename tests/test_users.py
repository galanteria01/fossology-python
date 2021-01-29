# Copyright 2019-2021 Siemens AG
# SPDX-License-Identifier: MIT

import logging
import secrets
from datetime import date, timedelta
from unittest.mock import Mock

import pytest
import requests
import responses

from fossology import Fossology, fossology_token
from fossology.exceptions import AuthenticationError, FossologyApiError

logger = logging.getLogger("fossology-tests")
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s %(levelname)s\t%(name)s: %(message)s")
console.setFormatter(formatter)
logger.addHandler(console)
logging.getLogger("").addHandler(console)


def test_generate_token_wrong_date(foss_server: str):
    with pytest.raises(FossologyApiError) as excinfo:
        fossology_token(
            foss_server,
            "fossy",
            "fossy",
            secrets.token_urlsafe(8),
            token_expire=str(date.today() - timedelta(days=1)),
        )
        assert "Error while generating new token" in str(excinfo.value)


def test_generate_token_too_long(foss_server: str):
    with pytest.raises(FossologyApiError) as excinfo:
        fossology_token(
            foss_server,
            "fossy",
            "fossy",
            secrets.token_urlsafe(41),
            token_expire=str(date.today() + timedelta(days=1)),
        )
        assert "Error while generating new token" in str(excinfo.value)


@responses.activate
def test_generate_token_errors(foss_server: str):
    responses.add(
        responses.POST,
        f"{foss_server}/api/v1/tokens",
        body=requests.exceptions.ConnectionError(),
    )
    responses.add(
        responses.POST, f"{foss_server}/api/v1/tokens", status=404,
    )
    with pytest.raises(SystemExit) as excinfo:
        fossology_token(
            foss_server,
            "fossy",
            "fossy",
            secrets.token_urlsafe(8),
            token_expire=str(date.today() - timedelta(days=1)),
        )
        assert (
            f"Server {foss_server} does not seem to be running or is unreachable"
            in str(excinfo.value)
        )
    with pytest.raises(AuthenticationError) as excinfo:
        fossology_token(
            foss_server,
            "fossy",
            "nofossy",
            secrets.token_urlsafe(8),
            token_expire=str(date.today() + timedelta(days=1)),
        )
        assert "Authentication error" in str(excinfo.value)


def test_wrong_user(foss_server, foss_token):
    with pytest.raises(AuthenticationError):
        Fossology(foss_server, foss_token, "nofossy")


def test_unknown_user(foss: Fossology):
    with pytest.raises(FossologyApiError):
        foss.detail_user(30)


def test_list_users(foss: Fossology):
    users = foss.list_users()
    assert len(users) == 1


@responses.activate
def test_detail_user_with_agents(
    foss_server: str, foss: Fossology, foss_user: dict, foss_user_agents: dict
):
    user = foss_user
    responses.add(
        responses.GET, f"{foss_server}/api/v1/users/{user['id']}", status=200, json=user
    )
    user_from_api = foss.detail_user(user["id"])
    assert user_from_api.agents.to_dict() == foss_user_agents


@responses.activate
def test_list_users_with_agents(
    foss_server: str, foss: Fossology, foss_user: dict, foss_user_agents: dict
):
    users = [foss_user]
    responses.add(responses.GET, f"{foss_server}/api/v1/users", status=200, json=users)
    users_from_api = foss.list_users()
    assert users_from_api[0].agents.to_dict() == foss_user_agents


@responses.activate
def test_list_users_error(foss_server: str, foss: Fossology):
    responses.add(responses.GET, f"{foss_server}/api/v1/users", status=404)
    with pytest.raises(FossologyApiError) as excinfo:
        foss.list_users()
    assert f"Unable to get a list of users from {foss_server}" in str(excinfo.value)


def test_detail_user(foss: Fossology):
    assert foss.detail_user(foss.user.id)
    assert foss.user.email == "y"
    assert (
        f"User {foss.user.description} ({foss.user.id}), {foss.user.email}, "
        f"access level {foss.user.accessLevel} "
        f"and root folder {foss.user.rootFolderId}"
    ) in str(foss.user)


@responses.activate
def test_delete_user(foss_server: str, foss: Fossology):
    user = Mock(name="Test User", id=secrets.randbelow(1000))
    responses.add(responses.DELETE, f"{foss_server}/api/v1/users/{user.id}", status=202)
    responses.add(responses.DELETE, f"{foss_server}/api/v1/users/{user.id}", status=404)
    assert not foss.delete_user(user)
    with pytest.raises(FossologyApiError) as excinfo:
        foss.delete_user(user)
    assert f"Error while deleting user {user.name} ({user.id})" in str(excinfo.value)


@responses.activate
def test_noversion(foss_server: str, foss: Fossology):
    responses.add(responses.GET, f"{foss_server}/api/v1/version", status=404)
    with pytest.raises(FossologyApiError) as excinfo:
        foss.get_version()
    assert "Error while getting API version" in str(excinfo.value)
