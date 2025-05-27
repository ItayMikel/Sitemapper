# Sitemapper
Python web site mapper that extracts links from a given page's HTML content.
Then crawls to these links to get their HTMl content and look for additional links.
Handy for when you want to look for sensitive paths/files on a website.

I recommend limiting the tool with "-d" and "-m" when targetting large web sites or ones that are protected by WAF.

Usage: Sitemapper.py [-h] [-v] [-t THREADS] [-m MAX] [-d DEPTH] [-f] url

positional arguments:
  url                   Starting URL to crawl

options:
  -h, --help            show this help message and exit
  -v, --verbose         Enable verbose output
  -t THREADS, --threads THREADS
                        Number of threads to use
  -m MAX, --max MAX     Maximum number of internal links to crawl (0 = no limit)
  -d DEPTH, --depth DEPTH
                        Maximum crawl depth (0 = no limit)
  -f, --full-links      Print full internal links instead of just directories
