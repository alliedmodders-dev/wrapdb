#!/usr/bin/env python3

import os
import shutil
import sys
import json
import subprocess
import tempfile
import hashlib
import requests

from configparser import ConfigParser


class CreateRelease:
    def __init__(self, package: str, ver: str, tag: str, git_repo: str, git_token: str, root_dir: any):
        print(f'{tag}...', end=' ')

        self.tag = tag
        self.ver = ver
        self.package = package
        self.git_repo = git_repo
        self.git_token = git_token
        self.root_dir = root_dir
        self.temp_dir = None
        self.wrap = None
        self.wrap_section = None
        self.upload_url = None

        self.create_release()
        self.load_wrap()
        with tempfile.TemporaryDirectory() as self.temp_dir:
            self.create_pack()
            self.create_wrap()

        print('done!')

    def create_release(self):
        api = f'https://api.github.com/repos/{self.git_repo}/releases'
        headers = {'Authorization': f'token {self.git_token}'}

        response = requests.get(api, headers=headers)
        response.raise_for_status()

        for r in response.json():
            if r['tag_name'] == self.tag:
                self.upload_url = r['upload_url'].replace(u'{?name,label}', '')
                return

        content = {
            'tag_name': self.tag,
            'name': self.tag,
        }

        response = requests.post(api, headers=headers, json=content)
        response.raise_for_status()
        self.upload_url = response.json()['upload_url'].replace(u'{?name,label}', '')

    def upload(self, path: str, mimetype: str):
        headers = {
            'Authorization': f'token {self.git_token}',
            'Content-Type': mimetype,
        }
        params = {'name': os.path.basename(path)}
        with open(path, 'rb') as f:
            response = requests.post(self.upload_url, headers=headers, params=params, data=f.read())
            response.raise_for_status()

    def load_wrap(self):
        self.wrap = ConfigParser(interpolation=None)
        self.wrap.read(os.path.join(self.root_dir, 'subprojects', f'{self.package}.wrap'))
        self.wrap_section = self.wrap[self.wrap.sections()[0]]

    def create_pack(self):
        patch_dir = self.wrap_section.get('patch_directory')
        if patch_dir is None:
            return
        patch_dir = os.path.join(self.root_dir, 'subprojects', 'packagefiles', patch_dir)

        dest_dir = os.path.join(self.temp_dir, self.tag)

        archive = shutil.make_archive(
            f'{dest_dir}-patch',
            'zip',
            root_dir=self.temp_dir,
            base_dir=os.path.basename(shutil.copytree(os.path.normpath(patch_dir), os.path.normpath(dest_dir)))
        )

        with open(archive, 'rb') as f:
            sha_hash = hashlib.sha256(f.read()).hexdigest()

        filename = os.path.basename(archive)

        self.wrap_section['directory'] = self.tag
        self.wrap_section['wrapdb_version'] = self.ver

        self.wrap_section['patch_url'] = f'https://github.com/{self.git_repo}/releases/download/{self.tag}/{filename}'
        self.wrap_section['patch_hash'] = sha_hash
        self.wrap_section['patch_filename'] = filename

        del self.wrap_section['patch_directory']

        self.upload(archive, 'application/zip')

    def create_wrap(self):
        wrap_file = os.path.join(self.temp_dir, f'{self.package}.wrap')
        with open(wrap_file, 'w') as f:
            self.wrap.write(f)
        self.upload(wrap_file, 'text/plain')


def run(git_repo: str, git_token: str, root_dir: any):
    if not os.path.isdir(os.path.join(root_dir, 'subprojects')):
        raise Exception('Unable to locate subprojects dir.')

    with open('wrapdb.json', 'r') as f:
        db = json.load(f)

    tags = [t.strip() for t in subprocess.check_output(['git', 'tag']).decode().splitlines()]

    for package, versions in db.items():
        ver = versions[-1]
        tag = f'{package}-{ver}'
        if tag not in tags:
            CreateRelease(package, ver, tag, git_repo, git_token, root_dir)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        raise Exception("Usage: wrapdb.py <repository> <token>")

    run(sys.argv[1], sys.argv[2], os.getcwd())
