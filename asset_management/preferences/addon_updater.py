# -*- coding:utf-8 -*-

# Blender ASSET MANAGEMENT Add-on
# Copyright (C) 2018 Legigan Jeremy AKA Pistiwique and Pitiwazou
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# <pep8 compliant>

import os
import ssl
import urllib.request
import urllib
import json
import re

from datetime import datetime

from ..AmUtils import AmJson
from ..ressources.constants import AM_DATAS
from .. import bl_info


class AddonUpdater:
    def __init__(self):
        self._engine = GithubEngine()
        self._user = "pistiwique"
        self._repo = "asset_management_documentation"
        self._tags = []
        self._tag_latest = None
        self._tag_names = []
        self._use_releases = True
        self._latest_release = None
        self._include_branches = False
        self._include_branch_list = ['master']

        self._verbose = False  # for debugging
        self.skip_tag = None

        self._addon = __package__.split(".")[0].lower()
        self._addon_package = __package__.split(".")[0]
        self._updater_path = AM_DATAS

        self._json_path = os.path.join(
                self._updater_path,
                f"{self._addon_package}_updater_status.json")

        self._json = {}
        self._error = None
        self._error_msg = None
        self._prefiltered_tag_count = 0

        self.update_available = True

    @property
    def api_url(self):
        return self._engine.api_url

    @api_url.setter
    def api_url(self, value):
        if not self.check_is_url(value):
            raise ValueError("Not a valid URL: " + value)
        self._engine.api_url = value

    @property
    def error(self):
        return self._error

    @property
    def error_msg(self):
        return self._error_msg

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, value):
        try:
            self._user = str(value)
        except:
            raise ValueError("User must be a string value")

    @property
    def repo(self):
        return self._repo

    @repo.setter
    def repo(self, value):
        try:
            self._repo = str(value)
        except:
            raise ValueError("User must be a string")

    @property
    def tag_latest(self):
        if self._tag_latest is None:
            return None
        if self._use_releases:
            return self._tag_latest["tag_name"]
        else:
            return self._tag_latest["name"]

    @property
    def tags(self):
        if not self._tags:
            return []
        tag_names = []
        for tag in self._tags:
            tag_names.append(tag["name"])
        return tag_names

    @staticmethod
    def check_is_url(url):
        if not ("http://" in url or "https://" in url):
            return False
        if "." not in url:
            return False
        return True

    @property
    def use_releases(self):
        return self._use_releases

    @use_releases.setter
    def use_releases(self, value):
        try:
            self._use_releases = bool(value)
        except:
            raise ValueError("use_releases must be a boolean value")

    @staticmethod
    def get_simple_date(date):
        regex = r"\d{4}-\d{2}-\d{2}"
        valid_date = re.search(regex, str(date))
        if valid_date:
            return valid_date.group()

        return None

    def load_json_file(self):
        self._json = AmJson.load_json_file(self._json_path)

    def async_check_update(self, check_update=False, manual=False):
        """Perform update check, run as target of background thread"""

        self.load_json_file()

        if self._json is None:
            self._json = {
                "version": bl_info["version"],
                "last_check": self.get_simple_date(datetime.now()),
                "up_to_date": True,
                "release_note": ""
                }

            setattr(self, "update_available", False)
            AmJson.save_as_json_file(self._json_path, self._json)
            return

        if self._json.get("up_to_date") is None or self._json.get("version")\
                is None:
            self._json = {
                "version": "",
                "last_check": "",
                "up_to_date": False,
                "release_note": ""
                }
            self.check_for_update()
            return

        if manual:
            self.check_for_update()
            return

        if check_update:
            last = self.get_simple_date(self._json["last_check"])
            if last:
                now = self.get_simple_date(datetime.now())
                if now == last:
                    if bl_info["version"] == tuple(self._json["version"]):
                        setattr(self,
                                "update_available",
                                not self._json["up_to_date"]
                                )
                        print(f"{self._addon} already checked today")
                        return
                    else:
                        self.check_for_update()
                        return

            self.check_for_update()

        else:
            setattr(self, "update_available", False)

        if self._verbose:
            print(f"{self._addon} BG thread: Finished checking for update")

    def check_for_update(self):
        if self._verbose:
            print(f"{self._addon} BG thread: Checking for update now in "
                  "background")
        try:
            self._check_for_update()
        except Exception as exception:
            print("Encountered an error while checking for updates:")
            print(exception)

    def _check_for_update(self):
        if self._verbose:
            print("Checking for update function")

        self._error = None
        self._error_msg = None

        if self._repo is None:
            raise ValueError("repo not yet defined")
        if self._user is None:
            raise ValueError("username not yet defined")

        # primary internet call
        self.get_tags()  # sets self._tags and self._tag_latest

        # can be () or ('master') in addition to branches, and version tag
        last_version = self.version_tuple_from_text(self.tag_latest)
        if last_version:
            if self.is_update_available(last_version):
                setattr(self, "update_available", True)
                self._json["up_to_date"] = False
                print(f"A new version of {self._addon} is available")
            else:
                setattr(self, "update_available", False)
                self._json["up_to_date"] = True
                print(f"{self._addon} is up to date")

            self._json["version"] = bl_info["version"]
            self._json["last_check"] = str(datetime.now())
            self._json["release_note"] = self.get_description()
            AmJson.save_as_json_file(self._json_path, self._json)

    def is_update_available(self, last_version):
        current = bl_info["version"]
        if self._verbose:
            print(f"current version: {current}, last version: {last_version}")
        return current < last_version

    def form_tags_url(self):
        return self._engine.form_tags_url(self)

    def get_tags(self):
        request = self.form_tags_url()
        if self._verbose:
            print("Getting tags from server")

        # get all tags, internet call
        all_tags = self._engine.parse_tags(self.get_api(request), self)

        if all_tags is not None:
            self._prefiltered_tag_count = len(all_tags)
        else:
            self._prefiltered_tag_count = 0
            all_tags = []

        # pre-process to skip tags
        if self.skip_tag is not None:
            self._tags = [tg for tg in all_tags if not self.skip_tag(self, tg)]
        else:
            self._tags = all_tags

        # get additional branches too, if needed, and place in front
        # Does NO checking here whether branch is valid
        if self._include_branches:
            temp_branches = self._include_branch_list.copy()
            temp_branches.reverse()
            for branch in temp_branches:
                request = self._engine.form_branch_url(branch)
                include = {
                    "name": branch.title(),
                    "zipball_url": request
                    }
                self._tags = [include] + self._tags  # append to front

        if self._tags is None:
            # some error occurred
            self._tag_latest = None
            self._tags = []
            return
        elif self._prefiltered_tag_count == 0 and not self._include_branches:
            self._tag_latest = None
            if self._error is None:  # if not None, could have had no internet
                self._error = "No releases found"
                self._error_msg = "No releases or tags found on this repository"
            if self._verbose:
                print("No releases or tags found on this repository")
        elif self._prefiltered_tag_count == 0 and self._include_branches:
            if not self._error:
                self._tag_latest = self._tags[0]
            if self._verbose:
                branch = self._include_branch_list[0]
                print("{} branch found, no releases".format(branch),
                      self._tags[0])
        elif (len(self._tags) - len(
                self._include_branch_list) == 0 and self._include_branches == True) \
                or (len(self._tags) == 0 and self._include_branches == False) \
                and self._prefiltered_tag_count > 0:
            self._tag_latest = None
            self._error = "No releases available"
            self._error_msg = "No versions found within compatible version range"
            if self._verbose:
                print("No versions found within compatible version range")
        else:
            if self._include_branches == False:
                self._tag_latest = self._tags[0]
                if self._verbose:
                    print("Most recent tag found:", self._tags[0]['name'])
            else:
                # don't return branch if in list
                n = len(self._include_branch_list)
                self._tag_latest = self._tags[
                    n]  # guaranteed at least len()=n+1
                if self._verbose:
                    print("Most recent tag found:", self._tags[n]['name'])

    # all API calls to base url
    def get_raw(self, url):
        # print("Raw request:", url)
        request = urllib.request.Request(url)
        try:
            context = ssl._create_unverified_context()
        except:
            # some blender packaged python versions don't have this, largely
            # useful for local network setups otherwise minimal impact
            context = None

        # setup private request headers if appropriate
        if self._engine.token != None:
            if self._verbose:
                print("Tokens not setup for engine yet")

        # run the request
        try:
            if context:
                result = urllib.request.urlopen(request, context=context)
            else:
                result = urllib.request.urlopen(request)
        except urllib.error.HTTPError as e:
            if str(e.code) == "403":
                self._error = "HTTP error (access denied)"
                self._error_msg = str(e.code) + " - server error response"
                print(self._error, self._error_msg)
            else:
                self._error = "HTTP error"
                self._error_msg = str(e.code)
                print(self._error, self._error_msg)
            self._update_ready = None
        except urllib.error.URLError as e:
            reason = str(e.reason)
            if "TLSV1_ALERT" in reason or "SSL" in reason.upper():
                self._error = "Connection rejected, download manually"
                self._error_msg = reason
                print(self._error, self._error_msg)
            else:
                self._error = "URL error, check internet connection"
                self._error_msg = reason
                print(self._error, self._error_msg)
            self._update_ready = None
            return None
        else:
            result_string = result.read()
            result.close()
            return result_string.decode()

    # result of all AssetMCore calls, decoded into json format
    def get_api(self, url):
        # return the json version
        get = self.get_raw(url)
        if get != None:
            try:
                return json.JSONDecoder().decode(get)
            except Exception as e:
                self._error = "API response has invalid JSON format"
                self._error_msg = str(e.reason)
                self._update_ready = None
                print(self._error, self._error_msg)
                return None
        else:
            return None

    def get_description(self):
        return self._tags[0].get("body")

    def version_tuple_from_text(self, text):
        if text == None:
            return ()

        # should go through string and remove all non-integers,
        # and for any given break split into a different section
        segments = []
        tmp = ''
        for l in str(text):
            if l.isdigit() == False:
                if len(tmp) > 0:
                    segments.append(int(tmp))
                    tmp = ''
            else:
                tmp += l
        if len(tmp) > 0:
            segments.append(int(tmp))

        if len(segments) == 0:
            if self._verbose:
                print("No version strings found text: ", text)
            if self._include_branches == False:
                return ()
            else:
                return (text)
        return tuple(segments)


class GithubEngine(object):
	"""Integration to Github API"""

	def __init__(self):
		self.api_url = 'https://api.github.com'
		self.token = None
		self.name = "github"

	def form_repo_url(self, updater):
		return "{}{}{}{}{}".format(self.api_url,"/repos/",updater.user,
								"/",updater.repo)

	def form_tags_url(self, updater):
		if updater.use_releases:
			return "{}{}".format(self.form_repo_url(updater),"/releases")
		else:
			return "{}{}".format(self.form_repo_url(updater),"/tags")

	def form_branch_list_url(self, updater):
		return "{}{}".format(self.form_repo_url(updater),"/branches")

	def form_branch_url(self, branch, updater):
		return "{}{}{}".format(self.form_repo_url(updater),
							"/zipball/",branch)

	def parse_tags(self, response, updater):
		if response == None:
			return []
		return response

Updater = AddonUpdater()