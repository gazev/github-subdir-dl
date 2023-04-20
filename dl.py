#
# Author: vugonz @ GitHub
# Python version: 3.10.10
#

import asyncio
from urllib.parse import urlparse, unquote
from dataclasses import dataclass
from os.path import basename, relpath
from os import sys, mkdir

import aiohttp

API_VERSION = "2022-11-28"
NAME = "Github subdir downloader"
VERSION = "0.1.0"

@dataclass
class TargetDir:
    name:     str
    path:     str
    endpoint: str
    
    @classmethod
    def from_github_url(cls, url):
        parsed_url = urlparse(url)

        if parsed_url.netloc != "github.com":
            raise ValueError("Not a GitHub repo!")

        name = basename(parsed_url.path)

        # get info from the url's path
        # parsed_url format:
        # { /owner/repo/tree|blob/branch/this/is/rel/path }
        owner, repo, _, branch, *dir_path = parsed_url.path[1:].split("/")
        dir_path = "/".join(dir_path)

        return cls(name, dir_path, cls._build_endpoint(owner, repo, dir_path, branch))
    
    @staticmethod
    def _build_endpoint(owner, repo, dir_path, branch):
        return f"https://api.github.com/repos/{owner}/{repo}/contents/{dir_path}?ref={branch}"


class Downloader:
    def __init__(self, target_dir: TargetDir, token=None):
        self.session = self.init_session(token)
        self.target_dir = target_dir

    def init_session(self, token):
        return aiohttp.ClientSession(
                    headers = {
                                "X-GitHub-Api-Version": API_VERSION, 
                                "Authorization":        f"token {token}" if token else "",
                                "User-Agent":           f"{NAME}/{VERSION}" 
                            })
        
    async def run(self):
        async with self.session.get(self.target_dir.endpoint) as resp:
            if resp.status != 200:
                print("Unsuccesful request\n")
                print(f"Server message: {await resp.json()}\n")
                print(f"Response headers: {resp.headers}\n")
                await self._close_session()
                exit(0)

            objects = await resp.json()

        # if we didn't receive a json list of objects
        if not isinstance(objects, list):
            return
            print("Either this URL is not valid/supported or this program is outdaded (check if GitHub API verison equals {API_VERSION})")
            print("Note: If you are trying to download a single file just do it yourself! (or nested directories with a single file)")

        # create directory we are downloading 
        mkdir(self.target_dir.name)

        tasks = []

        for object in objects:
            tasks.append(self.fetch(object))

        await asyncio.gather(*tasks)

        await self._close_session()


    async def fetch(self, object):
        if object["type"] == "file":
            await self.download_file(object)
            return

        mkdir(self._relative_path(object["path"]))

        async with self.session.get(object["url"]) as resp:
            if resp.status != 200:
                print(f"Unsuccesful request to {object['url']}")
                # Log this with logging
                #print(f"Server message: {await resp.json()}")
                #print(f"Response headers: {str(resp.headers)}")
                return

            objects = await resp.json()
        
        tasks = [] 

        for object in objects:
            tasks.append(self.fetch(object))

        await asyncio.gather(*tasks)


    async def download_file(self, object):
        async with self.session.get(object["download_url"]) as resp:
            try:
                content = await resp.content.read()
            except UnicodeDecodeError:
                # unsure how this might happen but it is safeguarded here 
                print(f"Failed downloading file {object['path']}")
                return
                ...

        with open(self._relative_path(object["path"]), "wb+") as fp:
            fp.write(content)
        
        print(f"Got: {self._relative_path(object['path'])}")


    async def _close_session(self):
        await self.session.close()

    def _relative_path(self, path):
        return f"{self.target_dir.name}/{relpath(path, self.target_dir.path)}"
    

async def run_it(target,  *, token=None):
    dl =  Downloader(target, token)
    await dl.run()


if __name__ == '__main__':
    # TODO use argparser
    if sys.argv[1] == "--help" or sys.argv[1] == "-h":
        print("usage: python dl.py <github repo sub folder url> [personal acess token]")
        exit(0)

    target = TargetDir.from_github_url(sys.argv[1])

    try:
        token = sys.argv[2]
    except IndexError:
        token = None
    
    asyncio.run(run_it(target, token=token))



