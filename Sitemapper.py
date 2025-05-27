import argparse
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

parser = argparse.ArgumentParser(description="Python Web Site Mapper, extracts links from HTML -> Crwal to these links -> extract additional links to crawl")
parser.add_argument("url", help="Starting URL to crawl")
parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
parser.add_argument("-t", "--threads", type=int, default=1, help="Number of threads to use")
parser.add_argument("-m", "--max", type=int, default=0, help="Maximum number of internal links to crawl (0 = no limit)")
parser.add_argument("-d", "--depth", type=int, default=0, help="Maximum crawl depth (0 = no limit)")
parser.add_argument("-f", "--full-links", action="store_true", help="Print full internal links instead of just directories")

args = parser.parse_args()

# Function to pull links from page's HTML
def extract_links(url):
    # Custome UserAgent to pybass bot blockers
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=6) # Change timeout threshold if needed
    except requests.RequestException as e:
        print(f"Request failed for {url}: {e}")
        return set(), set(), set()
    
    # If HTTP status code not between 200-399 ignore this page
    if not (200 <= response.status_code < 400):
        if args.verbose:
            print(f"Skipped {url}: HTTP {response.status_code}")
        return set(), set(), set()

    # Do not crawl to pages that are not HTML
    content_type = response.headers.get("Content-Type", "")
    if "html" not in content_type:
        if args.verbose:
            print(f"Skipped {url}: Non-HTML content type ({content_type})")
        return set(), set(), set()

    soup = BeautifulSoup(response.text, 'html.parser')

    links = set()
    mailto_links = set()
    non_html_links = set()

    # How to extract the links from the page HTML
    for tag in soup.find_all(['a', 'link', 'script', 'img']):
        attr = 'href' if tag.name in ['a', 'link'] else 'src'
        link = tag.get(attr)
        if not link:
            continue
        
        # Ignore links that are not HTML
        if link.startswith(("SMS:", "tel:", "javascript:", "data:")) or link.startswith("#"):
            non_html_links.add(link)
            continue

        # Save mailto: links in case "-f" is used
        if link.startswith("mailto:"):
            mailto_links.add(link)
            continue
        
        full_link = urljoin(url, link)
        links.add(full_link)

    return links, mailto_links, non_html_links


# Used to help identify which links are internal/external based on hostname
# Same hostname = internal links
# Different hostname = external links (subdomains are considered external)
def get_hostname(url):
    hostname = urlparse(url).hostname or ""
    return hostname.lstrip("www.") if hostname.startswith("www.") else hostname


def split_links(base_url, links):
    internal_links = set()
    external_links = set()

    base_host = get_hostname(base_url)

    for link in links:
        host = get_hostname(link)
        if host == base_host:
            internal_links.add(link)
        else:
            external_links.add(link)

    return internal_links, external_links

# Depth measured  by "/" character in URL, example.com/1/2/3
def get_path_depth(url):
    path = urlparse(url).path
    return len([segment for segment in path.split("/") if segment])


# Crawl to links in the page HTML to get other page's HTML, leading to more links.
# Keeps track of which links were already crawled.
def crawl_website(start_url, thread_count=1):
    visited = set()
    to_visit = set([start_url])

    all_internal = set()
    all_external = set()
    mailto_links = set()
    non_html_links = set()

    # Ensure the tool only crawls internal links.
    def process_url(url):
        if get_hostname(url) != get_hostname(start_url):
            if args.verbose:
                print(f"Skipped {url}: external or subdomain")
            return url, set(), set(), set(), set()

        try:
            links, mailtos, non_htmls = extract_links(url)
            internal, external = split_links(start_url, links)
            return url, internal, external, mailtos, non_htmls
        except Exception as e:
            if args.verbose:
                print(f"Error crawling {url}: {e}")
            return url, set(), set(), set(), set()

    done = False

    # Threads
    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        while to_visit and not done:
            current_batch = set(to_visit)
            to_visit.clear()

            futures = {executor.submit(process_url, url): url for url in current_batch}

            for future in as_completed(futures):
                current_url, internal, external, mailtos, non_htmls = future.result()
                visited.add(current_url)
                 
                # Print number of visited URLs so far
                print(f"Crawled: {len(visited)} URLs", end="\r")

                # Stop when max number of links to crawl reached if "-m" is used.
                if args.max and len(visited) >= args.max:
                    if args.verbose:
                        print(f"Reached max limit of {args.max} internal links.")
                    done = True
                    break

                for link in internal:
                    if link not in visited and link not in to_visit:
                        if args.depth == 0 or get_path_depth(link) <= args.depth:
                            to_visit.add(link)

                all_internal.update(internal)
                all_external.update(external)
                mailto_links.update(mailtos)
                non_html_links.update(non_htmls)

    return all_internal, all_external, mailto_links, non_html_links


# Used to print only directories if "-f" is not supplied
def extract_directories(links):
    dirs = set()
    for url in links:
        parsed = urlparse(url)
        path = parsed.path
        if not path.endswith("/"):
            path = path.rsplit("/", 1)[0] + "/"
        else:
            path = path
        directory_url = f"{parsed.scheme}://{parsed.hostname}{path}"
        dirs.add(directory_url)
    return dirs


# Main function
if __name__ == "__main__":
    internal, external, mailtos, non_htmls = crawl_website(args.url, args.threads)

    if args.full_links:
        print(f"\nFound {len(internal)} internal links:")
        for link in sorted(internal):
            print(link)
    else:
        internal_dirs = extract_directories(internal)
        print(f"\nFound {len(internal_dirs)} internal directories:")
        for d in sorted(internal_dirs):
            print(d)

    if args.full_links:
        print(f"\nFound {len(external)} external links:")
        for link in sorted(external):
            print(link)
    else:
        external_dirs = extract_directories(external)
        print(f"\nFound {len(external_dirs)} external directories:")
        for d in sorted(external_dirs):
            print(d)

    if args.full_links:
        print(f"\nFound {len(mailtos)} email links:")
        for link in sorted(mailtos):
            print(link)

    if args.full_links:
        print(f"\nFound {len(non_htmls)} non-HTML links:")
        for link in sorted(non_htmls):
            print(link)