import subprocess
import sys
from flask import Flask, render_template, request, redirect, url_for
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import pandas as pd
import asyncio
from rich.progress import track
from rich.table import Table

# Check and install required packages
def install_packages(package_list):
    for package in package_list:
        try:
            __import__(package)
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# List of required packages
required_packages = [
    "selenium",
    "beautifulsoup4",
    "pandas",
    "asyncio",
    "rich",
    "flask",
]

# Install required packages if not already installed
install_packages(required_packages)

app = Flask(__name__)

# Global variables
df = pd.DataFrame(columns=["Title", "Location", "Company", "Link", "Description"])

async def scrapeJobDescription(url):
    options = Options()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    try:
        jobDescription = soup.find("div", class_="show-more-less-html__markup").text.strip()
        driver.quit()
        return jobDescription
    except:
        driver.quit()
        return ""

async def scrapeLinkedin(jobTitle, jobLocation):
    global df
    counter = 0
    max_jobs = 1  # Maximum number of jobs to scrape

    while counter < max_jobs:
        try:
            driver = webdriver.Chrome()
            driver.get(f"https://www.linkedin.com/jobs/search/?&keywords={jobTitle}&location={jobLocation}&refresh=true&start={counter}")

            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            ulElement = soup.find("ul", class_="jobs-search__results-list")
            liElements = ulElement.find_all("li")

            for item in track(liElements, description=f"Linkedin - Page: {counter // 25 + 1}"):
                jobTitle = item.find("h3", class_="base-search-card__title").text.strip()
                jobLocation = item.find("span", class_="job-search-card__location").text.strip()
                jobCompany = item.find("h4", class_="base-search-card__subtitle").text.strip()
                jobLink = item.find_all("a")[0]["href"]

                jobDescription = await scrapeJobDescription(jobLink)

                if jobTitle and jobLocation and jobCompany and jobLink:
                    df = pd.concat([
                        df,
                        pd.DataFrame({
                            "Title": [jobTitle],
                            "Location": [jobLocation],
                            "Company": [jobCompany],
                            "Link": [jobLink],
                            "Description": [jobDescription],
                        }),
                    ])
                    counter += 1  # Increment counter for each scraped job

                if counter >= max_jobs:
                    break

            driver.quit()

        except:
            break

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        jobTitle = request.form.get('jobTitle')
        jobLocation = request.form.get('jobLocation')

        asyncio.run(scrapeLinkedin(jobTitle, jobLocation))

        return redirect(url_for('results'))

    return render_template('index.html')

@app.route('/results')
def results():
    global df
    if not df.empty:
        return render_template('result.html', table_data=df.to_html(index=False))
    else:
        return render_template('result.html', table_data="No jobs scraped.")

