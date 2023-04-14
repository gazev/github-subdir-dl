#! /usr/bin/env python3

#
# Python 3.10.10
# Author: vugz @ GitHub
#
# A GitHub repositories' subdirectories downloader.
#

import os
import asyncio

import aiohttp
from bs4 import BeautifulSoup

async def write_file(dir, name, url, session):
    """ Download file """
    async with session.get(url) as resp:
        try:
            content = await resp.text()
        except UnicodeDecodeError:
            print(f"Ignoring binary file: {name}")
            return
    
    with open(dir + "/" + name, mode ="w+") as f:
        f.write(content)
        f.flush()

    print(f"Fetched {dir}/{name}")

async def main(base_dir, dir_url, session):
    """ Recursively iterate through folders """
    files = []
    sub_dirs = []
    async with session.get(dir_url) as resp:
        content = await resp.text()

    # Make directory
    os.mkdir(base_dir)

    # Parse
    soup = BeautifulSoup(content, 'html.parser')
    # Hard coded webscraping, might change in the future
    body = soup.find_all("a", class_="js-navigation-open Link--primary")

    for anchor in body:
        # Files
        if "blob" in anchor['href']:
            new_url = "https://raw.githubusercontent.com" + anchor['href']
            files.append(new_url.replace("/blob", ""))
        # Directories
        else:
            sub_dirs.append("https://github.com" + anchor['href'])
    
    tasks = []

    # Rerun in subdirectories
    async with aiohttp.ClientSession() as session:
        for sub_dir in sub_dirs:
            tasks.append(main(base_dir + "/" + os.path.basename(sub_dir), sub_dir, session))
        # Fetch files
        for file in files:
            tasks.append(write_file(base_dir, os.path.basename(file), file, session))
        
        await asyncio.gather(*tasks)
    

# Give an aiohttp session to first iteration
async def entry_point(dir, url):
    async with aiohttp.ClientSession() as session:
        await main(dir, url, session)

def github_subdir_dl():
    if os.sys.argv[1] == "--help" or os.sys.argv[1] == "-h":
        print("usage: python3 grab.py <github_repo_sub_folder_url>")
        os.sys.exit(0)

    url = os.sys.argv[1] 
    asyncio.run(entry_point(os.path.basename(url), url))

    os.sys.exit(0)

if __name__ == '__main__':
    github_subdir_dl()
