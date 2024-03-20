#!/usr/bin/env python3

import os
import sys
import json
import shutil
import hashlib
import requests
import subprocess

from tempfile import TemporaryDirectory
from dataclasses import dataclass
from configparser import ConfigParser


@dataclass
class UploadEntry:
    path: str
    mimetype: str = 'text/plain'


class Generate:
    def __init__(self, git_repo: str, git_token: str, root_dir: str):
        self.git_repo = git_repo
        self.git_token = git_token

        self.root_dir = root_dir
        self.base_dir = os.path.join(self.root_dir, 'subprojects')
        self.pack_dir = os.path.join(self.base_dir, 'packagefiles')

        with open(os.path.join(root_dir, 'releases.json'), 'r') as f:
            self.releases = json.load(f)

        self.run()

    def run(self):
        tags = [t.strip() for t in subprocess.check_output(['git', 'tag']).decode().splitlines()]

        for package, versions in self.releases.items():
            version = list(versions.keys())[0]

            tag = f'{package}-{version}'
            if tag not in tags:
                self.create_release(package, version, tag)

    def create_release(self, package, version, tag):
        wrap = ConfigParser(interpolation=None)
        wrap.read(os.path.join(self.base_dir, f'{package}.wrap'))
        wrap_section = wrap[wrap.sections()[0]]

        with TemporaryDirectory() as temp_dir:
            upload_queue: list[UploadEntry] = []

            # Generate patch
            patch_dir = wrap_section.get('patch_directory')
            if patch_dir is not None:
                patch_file = shutil.make_archive(
                    os.path.join(temp_dir, f'{package}-patch'),
                    'zip',
                    root_dir=self.pack_dir,
                    base_dir=patch_dir
                )

                with open(patch_file, 'rb') as f:
                    sha_hash = hashlib.sha256(f.read()).hexdigest()

                filename = os.path.basename(patch_file)

                wrap_section['patch_url'] = f'https://github.com/{self.git_repo}/releases/download/{tag}/{filename}'
                wrap_section['patch_hash'] = sha_hash
                wrap_section['patch_filename'] = filename

                wrap_section['wrapdb_version'] = version

                del wrap_section['patch_directory']

                upload_queue.append(UploadEntry(patch_file, 'application/zip'))

            # Generate wrap
            wrap_file = os.path.join(temp_dir, f'{package}.wrap')
            with open(wrap_file, 'w') as f:
                wrap.write(f)
            upload_queue.append(UploadEntry(wrap_file))

            # Upload all. This should be the last step, as errors are unlikely to occur here.
            self.upload_all(self.get_upload_url(tag), upload_queue)

    def upload_all(self, url: str, queue: list[UploadEntry]):
        for entry in queue:
            self.upload(url, entry)

    def upload(self, url: str, entry: UploadEntry):
        print(url, entry)

        headers = {
            'Authorization': f'token: {self.git_token}',
            'Content-Type': entry.mimetype
        }

        params = {
            'name': os.path.basename(entry.path)
        }

        with open(entry.path, 'rb') as f:
            response = requests.post(url, headers=headers, params=params, data=f.read())
            response.raise_for_status()

    def get_upload_url(self, tag: str):
        api = f'https://api.github.com/repos/{self.git_repo}/releases'

        headers = {
            'Authorization': f'token {self.git_token}'
        }

        response = requests.get(api, headers=headers)
        response.raise_for_status()

        for r in response.json():
            if r['tag_name'] == tag:
                return r['upload_url'].replace(u'{?name,label}', '')

        content = {
            'name': tag,
            'tag_name': tag
        }

        response = requests.post(api, headers=headers, json=content)
        response.raise_for_status()

        return response.json()['upload_url'].replace(u'{?name,label}', '')


if __name__ == '__main__':
    if len(sys.argv) < 3:
        raise Exception('Usage: generator.py <repo> <token>')
    Generate(sys.argv[1], sys.argv[2], os.getcwd())
