import requests
import datetime
import json
import pandas as pd
import xml.etree.ElementTree as ET
import os


def checkPipelines():
    
    #Input and output file names 
    #file_path = 
    #output_file = 

    try:
        with open(file_path, "r") as file:
            pipeline_urls = [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        pipeline_urls = []

    with open (output_file, 'a') as file:
        for url in pipeline_urls:
            is_in_range = checkIfPipelineHasLastBuild(url)
            if is_in_range and checkIfJobIsUnderJJB(url):
                lastDate = getLastBuildDate(url)
                print(f"{lastDate}")
                print(f"{url}")
                file.write(f'{url}\n')
                file.write(f'Last Build:{lastDate}\n')


def getLastBuildDate(url):

    last_build_info = f"{url}/lastBuild/api/json"
    response = requests.get(last_build_info)

    response_data = json.loads(response.text)
    timestamp = response_data.get("timestamp")
    timestamp_seconds = timestamp / 1000
    readable_date_utc = datetime.datetime.fromtimestamp(timestamp_seconds, tz=datetime.timezone.utc)
    return readable_date_utc

def checkIfPipelineHasLastBuild(job_url):

    last_build_info = f"{job_url}/lastBuild/api/json"
    response = requests.get(last_build_info)
    status_code = response.status_code
    lastBuild_inrange = False
    if status_code == 404:
        return False

    response_data = json.loads(response.text)
    timestamp = response_data.get("timestamp")
    timestamp_seconds = timestamp / 1000
    readable_date_utc = datetime.datetime.fromtimestamp(timestamp_seconds, tz=datetime.timezone.utc)
    today = datetime.datetime.now(tz=datetime.timezone.utc)
    one_year_ago = today - datetime.timedelta(days=730)

    if one_year_ago <= readable_date_utc:
        lastBuild_inrange = True

    return lastBuild_inrange


def checkIfJobIsUnderJJB(job_url):

    
    config_xml = f"{job_url}/config.xml"
    response = requests.get(config_xml)
    response.raise_for_status()
    check1 = "Jenkins Job Builder"
    check2 = "JJB"

    root = ET.fromstring(response.text)
    description_tag = root.find("description")
    if description_tag.text and (check1 in description_tag.text or check2 in description_tag.text):
        return True
    return False
    

def checkIfJobDisabled(job_url):
    
    config_xml = f"{job_url}/config.xml"
    response = requests.get(config_xml)

    response.raise_for_status()

    root = ET.fromstring(response.text)
    disabled_tag = root.find("disabled")
    
    if disabled_tag is not None and disabled_tag.text == "true":
        return True

    return False

def checkIfJobUsesDind(job_url):
    
    pipeline_code_url = f"{job_url}/config.xml"
    string_to_search = "docker push"
    response = requests.get(pipeline_code_url)
    
    if response.status_code != 200:
        raise Exception(f"Failed to fecth pipeline code for {job_url}")
    
    if string_to_search in response.text:
        return True
    return False

def fetch_all_jobs_simplified(base_url, auth=None):
    
    url = f"{base_url}/api/json?tree=jobs[name,url,jobs[name,url,jobs[name,url,jobs[name,url,jobs[name,url,jobs[name,url,jobs[name,url,jobs[name,url,jobs[name,url,jobs[name,url]]]]]]]]]]"
    # Supports 10 levels of folder nesting, as i saw that is the highest
    
    print(f"Fetching jobs from: {url}")
    
    response = requests.get(url, auth=auth)
    
    if response.status_code != 200:
        raise Exception(f"Failed to fetch jobs: {response.status_code} - {response.text}")
    
    # Parse the jobs from the response
    return parse_jobs(response.json().get("jobs", []))
    
def parse_jobs(jobs):
    all_jobs = []
    output_file = "dindPipelines.txt"
    with open (output_file, 'a') as file:
        for job in jobs:
            if "jobs" in job:  # Indicates a folder
                all_jobs.extend(parse_jobs(job["jobs"]))
            else:
                all_jobs.append({"name": job["name"], "url": job["url"]})
                uses_dind = checkIfJobUsesDind(job["url"])
                job_disabled = checkIfJobDisabled(job["url"])
                if uses_dind and not job_disabled:
                    print (f'{job["url"]}')
                    file.write(f'{job["url"]}\n')
            
    return all_jobs


JENKINS_URL = os.getenv("JENKINS_URL")
USER = os.getenv("JENKINS_USER")
API_TOKEN = os.getenv("JENKINS_API_TOKEN")