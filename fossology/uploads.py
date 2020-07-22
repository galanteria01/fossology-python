# Copyright 2020 Siemens AG
# SPDX-License-Identifier: MIT

import json
import time
import logging

from tenacity import retry, retry_if_exception_type, stop_after_attempt, TryAgain
from fossology.obj import Upload, Summary, Licenses, get_options
from fossology.exceptions import AuthorizationError, FossologyApiError

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Uploads:
    """Class dedicated to all "uploads" related endpoints"""

    # Retry until the unpack agent is finished
    @retry(retry=retry_if_exception_type(TryAgain), stop=stop_after_attempt(10))
    def detail_upload(self, upload_id, group=None):
        """Get detailled information about an upload

        API Endpoint: GET /uploads/{id}

        :param upload_id: the id of the upload
        :param group: the group the upload shall belong to
        :type: int
        :type group: string
        :return: the upload data
        :rtype: Upload
        :raises FossologyApiError: if the REST call failed
        :raises AuthorizationError: if the user can't access the group
        """
        headers = {}
        if group:
            headers["groupName"] = group
        response = self.session.get(f"{self.api}/uploads/{upload_id}", headers=headers)

        if response.status_code == 200:
            logger.debug(f"Got details for upload {upload_id}")
            return Upload.from_json(response.json())

        elif response.status_code == 403:
            description = f"Getting details for upload {upload_id} {get_options(group)}not authorized"
            raise AuthorizationError(description, response)

        elif response.status_code == 503:
            logger.debug(
                f"Unpack agent for {upload_id} didn't start yet, is the scheduler running?"
            )
            time.sleep(20)
            raise TryAgain

        else:
            description = f"Error while getting details for upload {upload_id}"
            raise FossologyApiError(description, response)

    def upload_file(  # noqa: C901
        self,
        folder,
        file=None,
        vcs=None,
        url=None,
        description=None,
        access_level=None,
        ignore_scm=False,
        group=None,
    ):
        """Upload a package to FOSSology

        API Endpoint: POST /uploads

        :Example for a file upload:

        >>> from fossology import Fossology
        >>> from fossology.obj import AccessLevel
        >>> foss = Fossology(FOSS_URL, FOSS_TOKEN, username)
        >>> my_upload = foss.upload_file(
                foss.rootFolder,
                file="my-package.zip",
                description="My product package",
                access_level=AccessLevel.PUBLIC,
            )

        :Example for a VCS upload:

        >>> vcs = {
                "vcsType": "git",
                "vcsUrl": "https://github.com/fossology/fossology-python",
                "vcsName": "fossology-python-github-master",
                "vcsUsername": "",
                "vcsPassword": "",
            }
        >>> vcs_upload = foss.upload_file(
                foss.rootFolder,
                vcs=vcs,
                description="Upload from VCS",
                access_level=AccessLevel.PUBLIC,
            )

        :Example for a URL upload:

        >>> url = {
                "url": "https://github.com/fossology/fossology-python/archive/master.zip",
                "name": "fossology-python-master.zip",
                "accept": "zip",
                "reject": "",
                "maxRecursionDepth": "1",
            }
        >>> url_upload = foss.upload_file(
                foss.rootFolder,
                url=url,
                description="Upload from URL",
                access_level=AccessLevel.PUBLIC,
            )

        :param folder: the upload Fossology folder
        :param file: the local path of the file to be uploaded
        :param vcs: the VCS specification to upload from an online repository
        :param url: the URL specification to upload from a url
        :param description: description of the upload (default: None)
        :param access_level: access permissions of the upload (default: protected)
        :param ignore_scm: ignore SCM files (Git, SVN, TFS) (default: True)
        :param group: the group name to chose while uploading the file (default: None)
        :type folder: Folder
        :type file: string
        :type vcs: dict()
        :type url: dict()
        :type description: string
        :type access_level: AccessLevel
        :type ignore_scm: boolean
        :type group: string
        :return: the upload data
        :rtype: Upload
        :raises FossologyApiError: if the REST call failed
        :raises AuthorizationError: if the user can't access the group
        """
        headers = {"folderId": str(folder.id)}
        if description:
            headers["uploadDescription"] = description
        if access_level:
            headers["public"] = access_level.value
        if ignore_scm:
            headers["ignoreScm"] = "false"
        if group:
            headers["groupName"] = group

        if file:
            headers["uploadType"] = "server"
            with open(file, "rb") as fp:
                files = {"fileInput": fp}
                response = self.session.post(
                    f"{self.api}/uploads", files=files, headers=headers
                )
        elif vcs or url:
            if vcs:
                headers["uploadType"] = "vcs"
                data = json.dumps(vcs)
            else:
                headers["uploadType"] = "url"
                data = json.dumps(url)
            headers["Content-Type"] = "application/json"
            response = self.session.post(
                f"{self.api}/uploads", data=data, headers=headers
            )
        else:
            logger.debug(
                "Neither VCS, or Url or filename option given, not uploading anything"
            )
            return

        if file:
            source = f"{file}"
        elif vcs:
            source = vcs.get("vcsName")
        else:
            source = url.get("name")

        if response.status_code == 201:
            try:
                upload = self.detail_upload(response.json()["message"])
                logger.info(
                    f"Upload {upload.uploadname} ({upload.hash.size}) "
                    f"has been uploaded on {upload.uploaddate}"
                )
                return upload
            except TryAgain:
                description = f"Upload of {source} failed"
                raise FossologyApiError(description, response)

        elif response.status_code == 403:
            description = (
                f"Upload of {source} {get_options(group, folder)}not authorized"
            )
            raise AuthorizationError(description, response)

        else:
            description = f"Upload {description} could not be performed"
            raise FossologyApiError(description, response)

    @retry(retry=retry_if_exception_type(TryAgain), stop=stop_after_attempt(3))
    def upload_summary(self, upload, group=None):
        """Get clearing information about an upload

        API Endpoint: GET /uploads/{id}/summary

        :param upload: the upload to gather data from
        :param group: the group name to chose while accessing an upload (default: None)
        :type: Upload
        :type group: string
        :return: the upload summary data
        :rtype: Summary
        :raises FossologyApiError: if the REST call failed
        :raises AuthorizationError: if the user can't access the group
        """
        headers = {}
        if group:
            headers["groupName"] = group
        response = self.session.get(
            f"{self.api}/uploads/{upload.id}/summary", headers=headers
        )

        if response.status_code == 200:
            return Summary.from_json(response.json())

        elif response.status_code == 403:
            description = f"Getting summary of upload {upload.id} {get_options(group)}not authorized"
            raise AuthorizationError(description, response)

        elif response.status_code == 503:
            logger.debug(
                f"Unpack agent for {upload.uploadname} (id={upload.id}) didn't start yet"
            )
            time.sleep(3)
            raise TryAgain
        else:
            description = f"No summary for upload {upload.uploadname} (id={upload.id})"
            raise FossologyApiError(description, response)

    @retry(retry=retry_if_exception_type(TryAgain), stop=stop_after_attempt(3))
    def upload_licenses(self, upload, agent=None, containers=False, group=None):
        """Get clearing information about an upload

        API Endpoint: GET /uploads/{id}/licenses

        The response does not generate Python objects yet, the plain JSON data is simply returned.

        :param upload: the upload to gather data from
        :param agent: the license agents to use (e.g. "nomos,monk,ninka,ojo,reportImport", default: "nomos")
        :param containers: wether to show containers or not (default: False)
        :param group: the group name to chose while accessing the upload (default: None)
        :type upload: Upload
        :type agent: string
        :type containers: boolean
        :type group: string
        :return: the list of licenses findings for the specified agent
        :rtype: list of Licenses
        :raises FossologyApiError: if the REST call failed
        :raises AuthorizationError: if the user can't access the group
        """
        params = {}
        headers = {}
        if group:
            headers["groupName"] = group
        if agent:
            params["agent"] = agent
        else:
            params["agent"] = agent = "nomos"
        if containers:
            params["containers"] = "true"
        response = self.session.get(
            f"{self.api}/uploads/{upload.id}/licenses", headers=headers, params=params
        )

        if response.status_code == 200:
            all_licenses = []
            scanned_files = response.json()
            for file_with_findings in scanned_files:
                file_licenses = Licenses.from_json(file_with_findings)
                all_licenses.append(file_licenses)
            return all_licenses

        elif response.status_code == 403:
            description = f"Getting license for upload {upload.id} {get_options(group)}not authorized"
            raise AuthorizationError(description, response)

        elif response.status_code == 412:
            description = f"Unable to get licenses from {agent} for {upload.uploadname} (id={upload.id})"
            raise FossologyApiError(description, response)

        elif response.status_code == 503:
            logger.debug(
                f"Unpack agent for {upload.uploadname} (id={upload.id}) didn't start yet"
            )
            time.sleep(3)
            raise TryAgain

        else:
            description = f"No licenses for upload {upload.uploadname} (id={upload.id})"
            raise FossologyApiError(description, response)

    def delete_upload(self, upload, group=None):
        """Delete an upload

        API Endpoint: DELETE /uploads/{id}

        :param upload: the upload to be deleted
        :param group: the group name to chose while deleting the upload (default: None)
        :type upload: Upload
        :type group: string
        :raises FossologyApiError: if the REST call failed
        :raises AuthorizationError: if the user can't access the group
        """
        headers = {}
        if group:
            headers["groupName"] = group
        response = self.session.delete(
            f"{self.api}/uploads/{upload.id}", headers=headers
        )

        if response.status_code == 202:
            logger.info(f"Upload {upload.id} has been scheduled for deletion")

        elif response.status_code == 403:
            description = (
                f"Deleting upload {upload.id} {get_options(group)}not authorized"
            )
            raise AuthorizationError(description, response)

        else:
            description = f"Unable to delete upload {upload.id}"
            raise FossologyApiError(description, response)

    def list_uploads(
        self, folder=None, group=None, recursive=True, page_size=20, page=1
    ):
        """Get all uploads available to the registered user

        API Endpoint: GET /uploads

        :param folder: only list uploads from the given folder
        :param group: list uploads from a specific group (not only your own uploads) (default: None)
        :param recursive: wether to list uploads from children folders or not (default: True)
        :param page_size: limit the number of uploads per page (default: 20)
        :param page: the number of the page to fetch uploads from (default: 1)
        :type folder: Folder
        :type group: string
        :type recursive: boolean
        :type page_size: int
        :type page: int
        :return: a list of uploads
        :rtype: list of Upload
        :raises FossologyApiError: if the REST call failed
        :raises AuthorizationError: if the user can't access the group
        """
        params = {}
        headers = {"limit": str(page_size), "page": str(page)}
        if group:
            headers["groupName"] = group
        if folder:
            params["folderId"] = folder.id
        if not recursive:
            params["recursive"] = "false"

        response = self.session.get(
            f"{self.api}/uploads", headers=headers, params=params
        )

        if response.status_code == 200:
            uploads_list = list()
            for upload in response.json():
                uploads_list.append(Upload.from_json(upload))
            logger.info(
                f"Retrieved page {page} of uploads, {response.headers.get('X-TOTAL-PAGES', 'Unknown')} pages are in total available"
            )
            return uploads_list

        elif response.status_code == 403:
            description = (
                f"Retrieving list of uploads {get_options(group, folder)}not authorized"
            )
            raise AuthorizationError(description, response)

        else:
            description = "Unable to retrieve the list of uploads"
            raise FossologyApiError(description, response)

    def move_upload(self, upload, folder, group=None):
        """Move an upload to another folder

        API Endpoint: PATCH /uploads/{id}

        :param upload: the Upload to be copied in another folder
        :param folder: the destination Folder
        :param group: the group name to chose while changing the upload (default: None)
        :type upload: Upload
        :type folder: Folder
        :type group: string
        :raises FossologyApiError: if the REST call failed
        :raises AuthorizationError: if the user can't access the group or folder
        """
        headers = {"folderId": str(folder.id)}
        if group:
            headers["groupName"] = group
        response = self.session.patch(
            f"{self.api}/uploads/{upload.id}", headers=headers
        )

        if response.status_code == 202:
            logger.info(f"Upload {upload.uploadname} has been moved to {folder.name}")

        elif response.status_code == 403:
            description = (
                f"Moving upload {upload.id} {get_options(group, folder)}not authorized"
            )
            raise AuthorizationError(description, response)

        else:
            description = f"Unable to move upload {upload.uploadname} to {folder.name}"
            raise FossologyApiError(description, response)

    def copy_upload(self, upload, folder):
        """Copy an upload in another folder

        API Endpoint: PUT /uploads/{id}

        :param upload: the Upload to be copied in another folder
        :param folder: the destination Folder
        :type upload: Upload
        :type folder: Folder
        :raises FossologyApiError: if the REST call failed
        """
        headers = {"folderId": str(folder.id)}
        response = self.session.put(f"{self.api}/uploads/{upload.id}", headers=headers)

        if response.status_code == 202:
            logger.info(f"Upload {upload.uploadname} has been copied to {folder.name}")

        elif response.status_code == 403:
            description = f"Copy upload {upload.id} {get_options(folder)}not authorized"
            raise AuthorizationError(description, response)

        else:
            description = f"Unable to copy upload {upload.uploadname} to {folder.name}"
            raise FossologyApiError(description, response)
