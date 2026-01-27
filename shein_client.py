from curl_cffi import requests
import logging
import asyncio

class SheinClient:
    def __init__(self, cookies: str):
        self.url = "https://www.sheinindia.in/api/category/sverse-5939-37961"
        self.params = {
            "fields": "SITE",
            "currentPage": "0",
            "pageSize": "45",
            "format": "json",
            "query": ":relevance:genderfilter:Men",
            "gridColumns": "5",
            "segmentIds": "22,17,7,18",
            "cohortIds": "economy|men,TEMP_M3_RS_FG_NOV,TEMP_M3_LS_FG_NOV",
            "customerType": "Existing",
            "facets": "genderfilter:Men",
            "userClusterId": "supervalue|m1active,idle,unisex,lowasp,p_null",
            "customertype": "Existing",
            "advfilter": "true",
            "platform": "Desktop",
            "showAdsOnNextPage": "false",
            "is_ads_enable_plp": "false",
            "displayRatings": "true",
            "store": "shein"
        }
        self.headers = {
            "Host": "www.sheinindia.in",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Sec-Ch-Ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Brave";v="144"',
            "X-Tenant-Id": "SHEIN",
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Gpc": "1",
            "Accept-Language": "en-US,en;q=0.7",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Referer": "https://www.sheinindia.in/c/sverse-5939-37961",
            "Accept-Encoding": "gzip, deflate, br",
            "Priority": "u=1, i"
        }
        # curl_cffi Session for impersonation - Use 'chrome' to get latest TLS fingerprint
        self.session = requests.Session(impersonate="chrome")
        # CLEAR default headers - Akamai is extremely sensitive to library-injected headers
        self.session.headers.clear()
        
        # Add user-provided Burp headers in exact sequence from screenshot
        self.session.headers.update(self.headers)
        self.session.headers["Cookie"] = cookies.strip()

    async def close(self):
        # curl_cffi session close
        pass

    def _get_page(self, params):
        return self.session.get(self.url, params=params, timeout=30.0)

    def _get_detail(self, url):
        return self.session.get(url, timeout=10.0)

    async def fetch_page_0(self):
        try:
            current_params = self.params.copy()
            response = await asyncio.to_thread(self._get_page, current_params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Error fetching page 0: {e}")
            return None

    async def fetch_products(self):
        all_products = []
        data = await self.fetch_page_0()
        if not data:
            return []

        all_products.extend(data.get("products", []))
        pagination = data.get("pagination", {})
        total_pages = pagination.get("totalPages", 1)

        if total_pages > 1:
            # Concurrency control for multi-page fetches
            sem = asyncio.Semaphore(3)
            
            async def fetch_with_stagger(page):
                async with sem:
                    # Tiny staggering for stealth
                    await asyncio.sleep(page * 0.1)
                    page_params = self.params.copy()
                    page_params["currentPage"] = str(page)
                    return await asyncio.to_thread(self._get_page, page_params)

            tasks = [fetch_with_stagger(p) for p in range(1, total_pages)]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for resp in responses:
                if isinstance(resp, requests.Response):
                    try:
                        resp.raise_for_status()
                        page_data = resp.json()
                        all_products.extend(page_data.get("products", []))
                    except Exception as e:
                        logging.error(f"Error parsing page: {e}")
                elif isinstance(resp, Exception):
                    logging.error(f"Exception during page fetch: {resp}")
        return all_products
