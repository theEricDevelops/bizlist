import os
import sys
from dotenv import load_dotenv
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
load_dotenv('.env')
from api.services.logger import Logger
from api.models import WebSearchCache
from api.dependencies import get_db_conn

log = Logger('searchapi')
db = next(get_db_conn())

class SearchAPI:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("SEARCHAPI_API_KEY")
        self.searchapi_url = "https://www.searchapi.io/api/v1/search"

        if not self.api_key:
            raise ValueError("API Key is required to use SearchAPI")

        log.debug(f"SearchAPI Key: {self.api_key[:3] + '*' * (len(self.api_key) - 3)}")

    def search(self, query: str, engine: str = "google"):
        params = {
            "engine": engine,
            "q": query,
            "api_key": self.api_key,
            "location": None,
            "device": "desktop",
            "hl": "en",
            "gl": "us"
        }

        cache = self._cached_search_results(params)
        if cache:
            log.debug(f"The search results for query: {query} are cached")
            return cache
        else:
            log.debug(f"The search results for query: {query} are not cached")
            
        try:
            response = requests.get(self.searchapi_url, params=params)
            response.raise_for_status()
            data = response.text

            if data:
                # Cache the search results for future use
                self._cache_search_results(params, data)

                log.debug(f"SearchAPI Response: {data}")
                log.info(f"SearchAPI Response Code: {response.status_code}")
                return data
            else:
                log.warning(f"Empty SearchAPI Response for query: {query}")
                return None
        except Exception as e:
            log.error(f"SearchAPI Error: {e}")
            return None

    def _cache_search_results(self, params: dict, data: dict):
        try:
            cache = WebSearchCache(
                params=params,
                data=data
            )
            db.add(cache)
            db.commit()
            db.refresh(cache)
            log.debug(f"Search results cached for query: {params.get('q')}")
            return cache
        except Exception as e:
            log.error(f"Error caching search results: {e}")
            db.rollback()
            return None

    def _cached_search_results(self, params: dict):
        try:
            cache = db.query(WebSearchCache).filter(
                WebSearchCache.params['q'].astext == params.get('q')
            ).first()
            
            if cache:
                log.debug(f"Found cached search results for query: {params.get('q')}")
                return cache.data
            else:
                log.debug(f"No cached search results found for query: {params.get('q')}")
                return None
        except Exception as e:
            log.error(f"Error fetching cached search results: {e}")
            return None



mock_response = {
  "search_metadata": {
    "id": "search_YQJGXn64VVWF6YrKM45l1jp7",
    "status": "Success",
    "created_at": "2025-03-24T22:17:00Z",
    "request_time_taken": 3.79,
    "parsing_time_taken": 0.05,
    "total_time_taken": 3.84,
    "request_url": "https://www.google.com/search?q=owner+of+peachtree+roofing+in+atlanta+ga&oq=owner+of+peachtree+roofing+in+atlanta+ga&gl=us&hl=en&ie=UTF-8",
    "html_url": "https://www.searchapi.io/api/v1/searches/search_YQJGXn64VVWF6YrKM45l1jp7.html",
    "json_url": "https://www.searchapi.io/api/v1/searches/search_YQJGXn64VVWF6YrKM45l1jp7"
  },
  "search_parameters": {
    "engine": "google",
    "q": "owner of peachtree roofing in atlanta ga",
    "device": "desktop",
    "google_domain": "google.com",
    "hl": "en",
    "gl": "us"
  },
  "search_information": {
    "query_displayed": "owner of peachtree roofing in atlanta ga",
    "total_results": 2730000,
    "time_taken_displayed": 0.4,
    "detected_location": "Fresno, California"
  },
  "answer_box": {
    "type": "organic_result",
    "answer": "Michael Johnson",
    "snippet": "My name is Michael Johnson, and I am the founder and CEO of Peachtree Restorations. My career in the roofing/restoration industry started over eight years ago as a Project Manager in Denver, Colorado.",
    "organic_result": {
      "title": "Michael Johnson - CEO - Peachtree Restorations | LinkedIn",
      "link": "https://www.linkedin.com/in/michael-johnson-9b6a629b#:~:text=My%20name%20is%20Michael%20Johnson,Project%20Manager%20in%20Denver%2C%20Colorado.",
      "source": "LinkedIn",
      "domain": "www.linkedin.com",
      "displayed_link": "https://www.linkedin.com › ...",
      "favicon": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAm0lEQVR4AWP4//8/RRhMyLfs3sNQvOk/KRikB24ATNB2yhEQJtoQuAEwzVAAYtPVAMJe4Cjf8l+0bsd/RkIGQAGc/ej9t/+TDt/7/+vPXzD/6Yfv/+2nHSXWAAT49P33/z9//4HZl559JM2Aqm3XwXyXGcfA/H///pFmgFj9DjCfp3IrTIgkA5ADbbAbQA6mKDPp9x7YBTOAIgwAVba5DGceMlQAAAAASUVORK5CYII="
    }
  },
  "organic_results": [
    {
      "position": 1,
      "title": "Meet Our Team - Peachtree Roofing & Exteriors",
      "link": "https://www.peachtreerestorations.com/our-team/",
      "source": "Peachtree Restorations",
      "domain": "www.peachtreerestorations.com",
      "displayed_link": "https://www.peachtreerestorations.com › our-team",
      "snippet": "Meet Our Team ; CertainTeed. Roofing Material Provider ; GAF. Roofing Material Provider ; Nick Gipson PA. Your Local Public Adjuster in the Metro Atlanta Area.",
      "snippet_highlighted_words": [
        "Roofing",
        "Roofing",
        "Atlanta"
      ],
      "rich_snippet": {
        "detected_extensions": {
          "rating": 5.0,
          "reviews": 5
        },
        "extensions": [
          "5.0",
          "(5)"
        ]
      },
      "favicon": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABwAAAAcCAMAAABF0y+mAAAAnFBMVEVHcEyNyEuQxEntXjDyWi7xWi/wWS3oYzCnr0TxWS+IzUz0VS2Qxkv0VC6LyUvxWS71Ui30VS3qXTCHzEz0VS2QxkrwWS/fbjGOyUrxWi6QxkuNykzvWi+G0E582lDyWC/xYC73kiH2iCT1gyeQxkvxUCTzajH4mh/zciv8Siv0din2nm30eyr6uXqQxUv6y5bze1P1j1R24FGSxErVAG5yAAAAH3RSTlMAkRjRNdudBQmjXtDG8HRtHVRCOoStjhdKLd38xOfcsS6FZAAAAOxJREFUKJG101dPwzAQAGAPwG727AS8nThNU8b//28kUiUkLjyA1Huy/Mnnu7OM0C04R78GT5I9uS0JwNbaJJq3eY0xSBJZa6cWEXy0mP1Ekthja/d4slMNb41OnxnOspcTzLro60e9I1kEjZUFqmgIIS53sJVn2qRBSClC/ABOPgnhZD/0Xoq4WEE/Gm1ML8UWoHu7GK2UNl4IiOeLVl2n9CD/jFejOqVMv5ZWXs9GaT1KQWG1zr8PZhzmeiqAKXVO+rnNNAdD2NCqScUccQ5ejG0eD+yQb5uyALbgMlIG5RvX407I/5927Tt8AYMlF9w0EpZLAAAAAElFTkSuQmCC"
    },
    {
      "position": 2,
      "title": "Peachtree Roofing, Inc. | BBB Business Profile",
      "link": "https://www.bbb.org/us/ga/alpharetta/profile/roofing-contractors/peachtree-roofing-inc-0443-11001009",
      "source": "Better Business Bureau",
      "domain": "www.bbb.org",
      "displayed_link": "https://www.bbb.org › ... › Roofing Contractors",
      "snippet": "BBB Accredited since 5/23/2024. Roofing Contractors in Alpharetta, GA. See BBB rating, reviews, complaints, get a quote and more.",
      "snippet_highlighted_words": [
        "Roofing",
        "GA"
      ],
      "favicon": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAMAAABEpIrGAAAAbFBMVEX////d5ery9fcAW4T2+Pl9nrMAUn4+dZXL198ATHoAX4a/zthLfZsATnt1mK4AV4EeZ4tGepkAWYKctMMAUHzW4OYAQXNjjKaLp7osbY/k6u4AR3e4yNNWhKCqvssAPXGUrr8ARXZ4mrBmjqeJhfooAAABCUlEQVR4AZ3PBYKFIBQF0KuUPLsVGXP/e5zfjROHbh7+yvOxj3HsElL52BFoYjKEW8SIKE7gxOgozTgc8vOOIoJDqOlE+3Aozzsqz7WOmorjP11RNgHQSpIlPktJC6CTuesCSZT2nDeuKM1wDLGtLVzEMYYUO2zF2Bf2+Er72FWPcDL1kXesDD6ppqaSB1UzMXzCAWJELDt2HTpGVMz4Dz9OKxqhZCwTzDLWuXnZsIx1N0EltW3Ckuoga183WDMzqNUEiynJeP38+kQ8NBuUHJbML+Uw6PBlQ+MB2qoZ2L7GDLCTGe3TE8m8NqHK5y5NxmKeVWVK6+OGt1u7WYitbWfYQy0MNwa/8Q2RghFlBR1TuAAAAABJRU5ErkJggg=="
    },
    {
      "position": 3,
      "title": "Peachtree Roofing Inc: Roofing Contractor | Marietta, GA",
      "link": "https://peachtreeroofing.com/",
      "source": "peachtreeroofing.com",
      "domain": "peachtreeroofing.com",
      "displayed_link": "https://peachtreeroofing.com",
      "snippet": "Speak with a knowledgeable roofing contractor based in Marietta, GA and servicing the Greater Atlanta Area ... Meet The Owner. Scott Chrismer ...",
      "snippet_highlighted_words": [
        "Scott Chrismer"
      ],
      "favicon": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB8AAAAfCAMAAAAocOYLAAAAOVBMVEVHcEwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADLcPMfAAAAE3RSTlMAEevW8/9voshYZyI1e4uF37VK+S+g4wAAARpJREFUeAHN0ldihDAMRdEnSzKycGX/i41xppfv5NC5M3T8LxQI71iCSDhp1HAhjIvNktPu7onnjJMvyTYsOZRasdfatNZzbHUpIa8uwczYTt7R3a6CYKpjz4tLVgCaxfOyjwqQcl9EsxLmMJcyt0PvrAQb7nFKPUuGiGAue4oJh/swHGVYmZQtolTUgmisJSLZKAcAb5iOqEDztaXxANbWKVbkUoDZo4rGtVZKRo3XLs0KFFeKYk0eO8pLL/jU6fS9Zz1fUcb21o/t7GkDsCUAZTvuvcHHoIeu2Mfwa3drhCPw7KNc+nLpNqKyUJ7d+EOXy1e1jv/eTTkoT5876Z5/KfmgnYaT0j7R1ohg3C+481w/Z2vXWjP8sR/6PQ//Hcx08wAAAABJRU5ErkJggg=="
    },
    {
      "position": 4,
      "title": "Scott Chrismer - Owner at Peachtree Roofing",
      "link": "https://www.zoominfo.com/p/Scott-Chrismer/9725133073",
      "source": "Zoominfo",
      "domain": "www.zoominfo.com",
      "displayed_link": "https://www.zoominfo.com › Scott-Chrismer",
      "snippet": "Scott Chrismer, the Owner of Peachtree Roofing, based in Marietta, United States. They were previously a Realtor at Chrismer Realty Group.",
      "snippet_highlighted_words": [
        "Scott Chrismer, the Owner of Peachtree Roofing"
      ],
      "favicon": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAA90lEQVR4AWMAgfcKEgqvpEX3v5YRfQ+k/9Mav5QSWw+yE245zGI64/dgR7yWEVkPF6Q/3s+AKkD/UBhoB/wf/A4YdQARAJ/a4eMAooLzrYXx/z+PH9HbAZiW/338kF4OwLT895VLQL4RBQ7AxCRZ/lpTmX7Z8J2bE9zyn8eOwiyntQMQlv/9+BFs+feVyyksByi3nH4O+FSYC09g32bPoFdRjGn5l94u+tYFn+trSLGcutnwa28XuuU0dABhy+nrAByAkPxQcsBoi2jUAcBu2UCHwP6BsvyFlNgGhucSEgoDEQqgDjHIbgYQADFAnVR6WQz08H6Y5QAohh4QgciXDwAAAABJRU5ErkJggg=="
    },
    {
      "position": 5,
      "title": "Scott Chrismer - Realtor",
      "link": "https://www.linkedin.com/in/scott-chrismer-1083002a",
      "source": "LinkedIn · Scott Chrismer",
      "domain": "www.linkedin.com",
      "displayed_link": "500+ followers",
      "snippet": "Scott Chrismer. Owner, Peachtree Roofing & Exteriors/ Realtor w/ Keller Williams/ The Chrismer Group. Chrismer Realty Group. Atlanta, Georgia, United States.",
      "snippet_highlighted_words": [
        "Owner, Peachtree Roofing & Exteriors"
      ],
      "favicon": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAm0lEQVR4AWP4//8/RRhMyLfs3sNQvOk/KRikB24ATNB2yhEQJtoQuAEwzVAAYtPVAMJe4Cjf8l+0bsd/RkIGQAGc/ej9t/+TDt/7/+vPXzD/6Yfv/+2nHSXWAAT49P33/z9//4HZl559JM2Aqm3XwXyXGcfA/H///pFmgFj9DjCfp3IrTIgkA5ADbbAbQA6mKDPp9x7YBTOAIgwAVba5DGceMlQAAAAASUVORK5CYII="
    },
    {
      "position": 6,
      "title": "Peachtree Roofing & Exteriors | BBB Business Profile",
      "link": "https://www.bbb.org/us/ga/roswell/profile/roofing-contractors/peachtree-roofing-exteriors-0443-27468703",
      "source": "Better Business Bureau",
      "domain": "www.bbb.org",
      "displayed_link": "https://www.bbb.org › ... › Roofing Contractors",
      "snippet": "Principal Contacts: Mr. Michael Johnson, CEO ; Fax numbers: Primary Fax: (855) 264-0207 ; Additional Email Addresses: Primary: Email this Business ...",
      "snippet_highlighted_words": [
        "Mr. Michael Johnson, CEO"
      ],
      "rich_snippet": {
        "detected_extensions": {
          "rating": 5.0,
          "reviews": 90
        },
        "extensions": [
          "5.0",
          "(90)"
        ]
      },
      "favicon": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAMAAABEpIrGAAAAbFBMVEX////d5ery9fcAW4T2+Pl9nrMAUn4+dZXL198ATHoAX4a/zthLfZsATnt1mK4AV4EeZ4tGepkAWYKctMMAUHzW4OYAQXNjjKaLp7osbY/k6u4AR3e4yNNWhKCqvssAPXGUrr8ARXZ4mrBmjqeJhfooAAABCUlEQVR4AZ3PBYKFIBQF0KuUPLsVGXP/e5zfjROHbh7+yvOxj3HsElL52BFoYjKEW8SIKE7gxOgozTgc8vOOIoJDqOlE+3Aozzsqz7WOmorjP11RNgHQSpIlPktJC6CTuesCSZT2nDeuKM1wDLGtLVzEMYYUO2zF2Bf2+Er72FWPcDL1kXesDD6ppqaSB1UzMXzCAWJELDt2HTpGVMz4Dz9OKxqhZCwTzDLWuXnZsIx1N0EltW3Ckuoga183WDMzqNUEiynJeP38+kQ8NBuUHJbML+Uw6PBlQ+MB2qoZ2L7GDLCTGe3TE8m8NqHK5y5NxmKeVWVK6+OGt1u7WYitbWfYQy0MNwa/8Q2RghFlBR1TuAAAAABJRU5ErkJggg=="
    },
    {
      "position": 7,
      "title": "Profile for Peachtree Restorations",
      "link": "https://www.facebook.com/peachtreerestorationsatl/",
      "source": "Facebook · Peachtree Restorations",
      "domain": "www.facebook.com",
      "displayed_link": "780+ followers",
      "snippet": "Don't be jealous of The Jones, Call 855-448-7663 for your free inspection from Peachtree Restorations and get your upgrade started today. # ...",
      "snippet_highlighted_words": [
        "Peachtree"
      ],
      "rich_snippet": {
        "detected_extensions": {
          "rating": 4.8,
          "reviews": 37
        },
        "extensions": [
          "4.8",
          "(37)"
        ]
      },
      "favicon": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAA+UlEQVR4AZ2TLwyCQBTGr4GNaLTZe7F3uwHBSLCY7ZOiFWYzSi8E81VN0GUzOPPnvTnfgMch89vexo57v/eHD9WWu8JsFCJ2AxQmQDEKoN0QiXk3UTZ5ETwnwI4S+oLueAt4Ipmq/Equd9SA2CqvT0BZgZXpZiffmSddyX4Cofzaumf2pcxD2gXIb2Cd9Qc4P7RGWSJWjmX28g7WOLLuo1DiUAD6FyoAxwus2mbdgGIoYL4XntDKMYuoH9KiqNLj1axMMd00AeRO5fqY/bsDtjZ3MRDAn5BlbEnzDAGwlaOalRliqBIgK8tkFls7rZ7QNUBBvzjtS7X0BtPFWgZg70LHAAAAAElFTkSuQmCC"
    },
    {
      "position": 8,
      "title": "PEACHTREE ROOFING & EXERIORS - Updated March 2025",
      "link": "https://www.yelp.com/biz/peachtree-roofing-and-exeriors-roswell",
      "source": "Yelp",
      "domain": "www.yelp.com",
      "displayed_link": "https://www.yelp.com › ... › Home Services › Roofing",
      "snippet": "In 2011, Michael sold American Roofing and Vinyl to his business partner and in 2012, M.W. Michael founded Peachtree Roofing & Exteriors in Atlanta, Georgia.",
      "snippet_highlighted_words": [
        "M"
      ],
      "rich_snippet": {
        "detected_extensions": {
          "rating": 4.3,
          "reviews": 30
        },
        "extensions": [
          "4.3",
          "(30)"
        ]
      },
      "favicon": "data:image/png;base64,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"
    },
    {
      "position": 9,
      "title": "Peachtree Roofing & Exteriors | Atlanta, GA Roof Company",
      "link": "https://www.peachtreerestorations.com/",
      "source": "Peachtree Restorations",
      "domain": "www.peachtreerestorations.com",
      "displayed_link": "https://www.peachtreerestorations.com",
      "snippet": "We opened our doors in 2012 and have proven to our customers that we'll always provide top-tier workmanship, high-quality products, and dependable customer ...",
      "sitelinks": {
        "inline": [
          {
            "title": "Atlanta, GA Roof Materials",
            "link": "https://www.peachtreerestorations.com/roofing/materials/"
          },
          {
            "title": "Atlanta, GA Gutter Guard...",
            "link": "https://www.peachtreerestorations.com/gutters/guards/"
          },
          {
            "title": "Roofing",
            "link": "https://www.peachtreerestorations.com/roofing/"
          },
          {
            "title": "Gutters",
            "link": "https://www.peachtreerestorations.com/gutters/"
          }
        ]
      },
      "favicon": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABwAAAAcCAMAAABF0y+mAAAAnFBMVEVHcEyNyEuQxEntXjDyWi7xWi/wWS3oYzCnr0TxWS+IzUz0VS2Qxkv0VC6LyUvxWS71Ui30VS3qXTCHzEz0VS2QxkrwWS/fbjGOyUrxWi6QxkuNykzvWi+G0E582lDyWC/xYC73kiH2iCT1gyeQxkvxUCTzajH4mh/zciv8Siv0din2nm30eyr6uXqQxUv6y5bze1P1j1R24FGSxErVAG5yAAAAH3RSTlMAkRjRNdudBQmjXtDG8HRtHVRCOoStjhdKLd38xOfcsS6FZAAAAOxJREFUKJG101dPwzAQAGAPwG727AS8nThNU8b//28kUiUkLjyA1Huy/Mnnu7OM0C04R78GT5I9uS0JwNbaJJq3eY0xSBJZa6cWEXy0mP1Ekthja/d4slMNb41OnxnOspcTzLro60e9I1kEjZUFqmgIIS53sJVn2qRBSClC/ABOPgnhZD/0Xoq4WEE/Gm1ML8UWoHu7GK2UNl4IiOeLVl2n9CD/jFejOqVMv5ZWXs9GaT1KQWG1zr8PZhzmeiqAKXVO+rnNNAdD2NCqScUccQ5ejG0eD+yQb5uyALbgMlIG5RvX407I/5927Tt8AYMlF9w0EpZLAAAAAElFTkSuQmCC"
    }
  ],
  "inline_images": {
    "images": [
      {
        "title": "PEACHTREE ROOFING & EXERIORS - Updated March 2025 - 39 ...",
        "source": {
          "name": "Yelp",
          "link": "https://m.yelp.com/biz/peachtree-roofing-and-exeriors-roswell"
        },
        "original": {
          "link": "https://s3-media0.fl.yelpcdn.com/bphoto/UbAZcPeNpPnptlAkees5LA/l.jpg",
          "height": 400,
          "width": 300,
          "size": "29KB"
        },
        "thumbnail": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTkKin2rmdxkiIuqFCL9b7wfEOJd0wROjSoEmzYqrKVlnjia1XiaqlpYLo&s"
      },
      {
        "title": "Scott Chrismer - Realtor - Chrismer Realty Group | LinkedIn",
        "source": {
          "name": "LinkedIn",
          "link": "https://www.linkedin.com/in/scott-chrismer-1083002a"
        },
        "original": {
          "link": "https://media.licdn.com/dms/image/v2/D4E03AQEH5Wtxf4mfmA/profile-displayphoto-shrink_200_200/profile-displayphoto-shrink_200_200/0/1718664950376?e=2147483647&v=beta&t=kABw3QjQ9goNdhnDD5LjqUve3CYcpkRS2o-b_9VwMo8",
          "height": 200,
          "width": 200,
          "size": "12KB"
        },
        "thumbnail": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQ4ysSFSileVxxtBplL_vWSwXNRUZnwVuWVFWD2duNKBTbY6b4fKll5VP8&s"
      },
      {
        "title": "Peachtree Roofing & Exteriors",
        "source": {
          "name": "www.peachtreerestorations.com",
          "link": "https://www.peachtreerestorations.com/"
        },
        "original": {
          "link": "https://cmsplatform.blob.core.windows.net/wwwpeachtreerestorationscom/gallery/original/ef633533-931d-4e49-bcb4-8b79d1a024df.jpg", 
          "height": 674,
          "width": 1000,
          "size": "289KB"
        },
        "thumbnail": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRN4GHKFruVZe39YhMhPv6KSl9FGpagVVZcschWdhF1Zr62uMVl-DMRvm0&s"
      }
    ]
  },
  "pagination": {
    "current": 1,
    "next": "https://www.google.com/search?q=owner+of+peachtree+roofing+in+atlanta+ga&oq=owner+of+peachtree+roofing+in+atlanta+ga&gl=us&hl=en&start=10&ie=UTF-8"
  }
}
{
  "search_metadata": {
    "id": "search_YQJGXn64VVWF6YrKM45l1jp7",
    "status": "Success",
    "created_at": "2025-03-24T22:17:00Z",
    "request_time_taken": 3.79,
    "parsing_time_taken": 0.05,
    "total_time_taken": 3.84,
    "request_url": "https://www.google.com/search?q=owner+of+peachtree+roofing+in+atlanta+ga&oq=owner+of+peachtree+roofing+in+atlanta+ga&gl=us&hl=en&ie=UTF-8",
    "html_url": "https://www.searchapi.io/api/v1/searches/search_YQJGXn64VVWF6YrKM45l1jp7.html",
    "json_url": "https://www.searchapi.io/api/v1/searches/search_YQJGXn64VVWF6YrKM45l1jp7"
  },
  "search_parameters": {
    "engine": "google",
    "q": "owner of peachtree roofing in atlanta ga",
    "device": "desktop",
    "google_domain": "google.com",
    "hl": "en",
    "gl": "us"
  },
  "search_information": {
    "query_displayed": "owner of peachtree roofing in atlanta ga",
    "total_results": 2730000,
    "time_taken_displayed": 0.4,
    "detected_location": "Fresno, California"
  },
  "answer_box": {
    "type": "organic_result",
    "answer": "Michael Johnson",
    "snippet": "My name is Michael Johnson, and I am the founder and CEO of Peachtree Restorations. My career in the roofing/restoration industry started over eight years ago as a Project Manager in Denver, Colorado.",
    "organic_result": {
      "title": "Michael Johnson - CEO - Peachtree Restorations | LinkedIn",
      "link": "https://www.linkedin.com/in/michael-johnson-9b6a629b#:~:text=My%20name%20is%20Michael%20Johnson,Project%20Manager%20in%20Denver%2C%20Colorado.",
      "source": "LinkedIn",
      "domain": "www.linkedin.com",
      "displayed_link": "https://www.linkedin.com › ...",
      "favicon": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAm0lEQVR4AWP4//8/RRhMyLfs3sNQvOk/KRikB24ATNB2yhEQJtoQuAEwzVAAYtPVAMJe4Cjf8l+0bsd/RkIGQAGc/ej9t/+TDt/7/+vPXzD/6Yfv/+2nHSXWAAT49P33/z9//4HZl559JM2Aqm3XwXyXGcfA/H///pFmgFj9DjCfp3IrTIgkA5ADbbAbQA6mKDPp9x7YBTOAIgwAVba5DGceMlQAAAAASUVORK5CYII="
    }
  },
  "organic_results": [
    {
      "position": 1,
      "title": "Meet Our Team - Peachtree Roofing & Exteriors",
      "link": "https://www.peachtreerestorations.com/our-team/",
      "source": "Peachtree Restorations",
      "domain": "www.peachtreerestorations.com",
      "displayed_link": "https://www.peachtreerestorations.com › our-team",
      "snippet": "Meet Our Team ; CertainTeed. Roofing Material Provider ; GAF. Roofing Material Provider ; Nick Gipson PA. Your Local Public Adjuster in the Metro Atlanta Area.",
      "snippet_highlighted_words": [
        "Roofing",
        "Roofing",
        "Atlanta"
      ],
      "rich_snippet": {
        "detected_extensions": {
          "rating": 5.0,
          "reviews": 5
        },
        "extensions": [
          "5.0",
          "(5)"
        ]
      },
      "favicon": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABwAAAAcCAMAAABF0y+mAAAAnFBMVEVHcEyNyEuQxEntXjDyWi7xWi/wWS3oYzCnr0TxWS+IzUz0VS2Qxkv0VC6LyUvxWS71Ui30VS3qXTCHzEz0VS2QxkrwWS/fbjGOyUrxWi6QxkuNykzvWi+G0E582lDyWC/xYC73kiH2iCT1gyeQxkvxUCTzajH4mh/zciv8Siv0din2nm30eyr6uXqQxUv6y5bze1P1j1R24FGSxErVAG5yAAAAH3RSTlMAkRjRNdudBQmjXtDG8HRtHVRCOoStjhdKLd38xOfcsS6FZAAAAOxJREFUKJG101dPwzAQAGAPwG727AS8nThNU8b//28kUiUkLjyA1Huy/Mnnu7OM0C04R78GT5I9uS0JwNbaJJq3eY0xSBJZa6cWEXy0mP1Ekthja/d4slMNb41OnxnOspcTzLro60e9I1kEjZUFqmgIIS53sJVn2qRBSClC/ABOPgnhZD/0Xoq4WEE/Gm1ML8UWoHu7GK2UNl4IiOeLVl2n9CD/jFejOqVMv5ZWXs9GaT1KQWG1zr8PZhzmeiqAKXVO+rnNNAdD2NCqScUccQ5ejG0eD+yQb5uyALbgMlIG5RvX407I/5927Tt8AYMlF9w0EpZLAAAAAElFTkSuQmCC"
    },
    {
      "position": 2,
      "title": "Peachtree Roofing, Inc. | BBB Business Profile",
      "link": "https://www.bbb.org/us/ga/alpharetta/profile/roofing-contractors/peachtree-roofing-inc-0443-11001009",
      "source": "Better Business Bureau",
      "domain": "www.bbb.org",
      "displayed_link": "https://www.bbb.org › ... › Roofing Contractors",
      "snippet": "BBB Accredited since 5/23/2024. Roofing Contractors in Alpharetta, GA. See BBB rating, reviews, complaints, get a quote and more.",
      "snippet_highlighted_words": [
        "Roofing",
        "GA"
      ],
      "favicon": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAMAAABEpIrGAAAAbFBMVEX////d5ery9fcAW4T2+Pl9nrMAUn4+dZXL198ATHoAX4a/zthLfZsATnt1mK4AV4EeZ4tGepkAWYKctMMAUHzW4OYAQXNjjKaLp7osbY/k6u4AR3e4yNNWhKCqvssAPXGUrr8ARXZ4mrBmjqeJhfooAAABCUlEQVR4AZ3PBYKFIBQF0KuUPLsVGXP/e5zfjROHbh7+yvOxj3HsElL52BFoYjKEW8SIKE7gxOgozTgc8vOOIoJDqOlE+3Aozzsqz7WOmorjP11RNgHQSpIlPktJC6CTuesCSZT2nDeuKM1wDLGtLVzEMYYUO2zF2Bf2+Er72FWPcDL1kXesDD6ppqaSB1UzMXzCAWJELDt2HTpGVMz4Dz9OKxqhZCwTzDLWuXnZsIx1N0EltW3Ckuoga183WDMzqNUEiynJeP38+kQ8NBuUHJbML+Uw6PBlQ+MB2qoZ2L7GDLCTGe3TE8m8NqHK5y5NxmKeVWVK6+OGt1u7WYitbWfYQy0MNwa/8Q2RghFlBR1TuAAAAABJRU5ErkJggg=="
    },
    {
      "position": 3,
      "title": "Peachtree Roofing Inc: Roofing Contractor | Marietta, GA",
      "link": "https://peachtreeroofing.com/",
      "source": "peachtreeroofing.com",
      "domain": "peachtreeroofing.com",
      "displayed_link": "https://peachtreeroofing.com",
      "snippet": "Speak with a knowledgeable roofing contractor based in Marietta, GA and servicing the Greater Atlanta Area ... Meet The Owner. Scott Chrismer ...",
      "snippet_highlighted_words": [
        "Scott Chrismer"
      ],
      "favicon": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB8AAAAfCAMAAAAocOYLAAAAOVBMVEVHcEwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADLcPMfAAAAE3RSTlMAEevW8/9voshYZyI1e4uF37VK+S+g4wAAARpJREFUeAHN0ldihDAMRdEnSzKycGX/i41xppfv5NC5M3T8LxQI71iCSDhp1HAhjIvNktPu7onnjJMvyTYsOZRasdfatNZzbHUpIa8uwczYTt7R3a6CYKpjz4tLVgCaxfOyjwqQcl9EsxLmMJcyt0PvrAQb7nFKPUuGiGAue4oJh/swHGVYmZQtolTUgmisJSLZKAcAb5iOqEDztaXxANbWKVbkUoDZo4rGtVZKRo3XLs0KFFeKYk0eO8pLL/jU6fS9Zz1fUcb21o/t7GkDsCUAZTvuvcHHoIeu2Mfwa3drhCPw7KNc+nLpNqKyUJ7d+EOXy1e1jv/eTTkoT5876Z5/KfmgnYaT0j7R1ohg3C+481w/Z2vXWjP8sR/6PQ//Hcx08wAAAABJRU5ErkJggg=="
    },
    {
      "position": 4,
      "title": "Scott Chrismer - Owner at Peachtree Roofing",
      "link": "https://www.zoominfo.com/p/Scott-Chrismer/9725133073",
      "source": "Zoominfo",
      "domain": "www.zoominfo.com",
      "displayed_link": "https://www.zoominfo.com › Scott-Chrismer",
      "snippet": "Scott Chrismer, the Owner of Peachtree Roofing, based in Marietta, United States. They were previously a Realtor at Chrismer Realty Group.",
      "snippet_highlighted_words": [
        "Scott Chrismer, the Owner of Peachtree Roofing"
      ],
      "favicon": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAA90lEQVR4AWMAgfcKEgqvpEX3v5YRfQ+k/9Mav5QSWw+yE245zGI64/dgR7yWEVkPF6Q/3s+AKkD/UBhoB/wf/A4YdQARAJ/a4eMAooLzrYXx/z+PH9HbAZiW/338kF4OwLT895VLQL4RBQ7AxCRZ/lpTmX7Z8J2bE9zyn8eOwiyntQMQlv/9+BFs+feVyyksByi3nH4O+FSYC09g32bPoFdRjGn5l94u+tYFn+trSLGcutnwa28XuuU0dABhy+nrAByAkPxQcsBoi2jUAcBu2UCHwP6BsvyFlNgGhucSEgoDEQqgDjHIbgYQADFAnVR6WQz08H6Y5QAohh4QgciXDwAAAABJRU5ErkJggg=="
    },
    {
      "position": 5,
      "title": "Scott Chrismer - Realtor",
      "link": "https://www.linkedin.com/in/scott-chrismer-1083002a",
      "source": "LinkedIn · Scott Chrismer",
      "domain": "www.linkedin.com",
      "displayed_link": "500+ followers",
      "snippet": "Scott Chrismer. Owner, Peachtree Roofing & Exteriors/ Realtor w/ Keller Williams/ The Chrismer Group. Chrismer Realty Group. Atlanta, Georgia, United States.",
      "snippet_highlighted_words": [
        "Owner, Peachtree Roofing & Exteriors"
      ],
      "favicon": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAm0lEQVR4AWP4//8/RRhMyLfs3sNQvOk/KRikB24ATNB2yhEQJtoQuAEwzVAAYtPVAMJe4Cjf8l+0bsd/RkIGQAGc/ej9t/+TDt/7/+vPXzD/6Yfv/+2nHSXWAAT49P33/z9//4HZl559JM2Aqm3XwXyXGcfA/H///pFmgFj9DjCfp3IrTIgkA5ADbbAbQA6mKDPp9x7YBTOAIgwAVba5DGceMlQAAAAASUVORK5CYII="
    },
    {
      "position": 6,
      "title": "Peachtree Roofing & Exteriors | BBB Business Profile",
      "link": "https://www.bbb.org/us/ga/roswell/profile/roofing-contractors/peachtree-roofing-exteriors-0443-27468703",
      "source": "Better Business Bureau",
      "domain": "www.bbb.org",
      "displayed_link": "https://www.bbb.org › ... › Roofing Contractors",
      "snippet": "Principal Contacts: Mr. Michael Johnson, CEO ; Fax numbers: Primary Fax: (855) 264-0207 ; Additional Email Addresses: Primary: Email this Business ...",
      "snippet_highlighted_words": [
        "Mr. Michael Johnson, CEO"
      ],
      "rich_snippet": {
        "detected_extensions": {
          "rating": 5.0,
          "reviews": 90
        },
        "extensions": [
          "5.0",
          "(90)"
        ]
      },
      "favicon": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAMAAABEpIrGAAAAbFBMVEX////d5ery9fcAW4T2+Pl9nrMAUn4+dZXL198ATHoAX4a/zthLfZsATnt1mK4AV4EeZ4tGepkAWYKctMMAUHzW4OYAQXNjjKaLp7osbY/k6u4AR3e4yNNWhKCqvssAPXGUrr8ARXZ4mrBmjqeJhfooAAABCUlEQVR4AZ3PBYKFIBQF0KuUPLsVGXP/e5zfjROHbh7+yvOxj3HsElL52BFoYjKEW8SIKE7gxOgozTgc8vOOIoJDqOlE+3Aozzsqz7WOmorjP11RNgHQSpIlPktJC6CTuesCSZT2nDeuKM1wDLGtLVzEMYYUO2zF2Bf2+Er72FWPcDL1kXesDD6ppqaSB1UzMXzCAWJELDt2HTpGVMz4Dz9OKxqhZCwTzDLWuXnZsIx1N0EltW3Ckuoga183WDMzqNUEiynJeP38+kQ8NBuUHJbML+Uw6PBlQ+MB2qoZ2L7GDLCTGe3TE8m8NqHK5y5NxmKeVWVK6+OGt1u7WYitbWfYQy0MNwa/8Q2RghFlBR1TuAAAAABJRU5ErkJggg=="
    },
    {
      "position": 7,
      "title": "Profile for Peachtree Restorations",
      "link": "https://www.facebook.com/peachtreerestorationsatl/",
      "source": "Facebook · Peachtree Restorations",
      "domain": "www.facebook.com",
      "displayed_link": "780+ followers",
      "snippet": "Don't be jealous of The Jones, Call 855-448-7663 for your free inspection from Peachtree Restorations and get your upgrade started today. # ...",
      "snippet_highlighted_words": [
        "Peachtree"
      ],
      "rich_snippet": {
        "detected_extensions": {
          "rating": 4.8,
          "reviews": 37
        },
        "extensions": [
          "4.8",
          "(37)"
        ]
      },
      "favicon": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAA+UlEQVR4AZ2TLwyCQBTGr4GNaLTZe7F3uwHBSLCY7ZOiFWYzSi8E81VN0GUzOPPnvTnfgMch89vexo57v/eHD9WWu8JsFCJ2AxQmQDEKoN0QiXk3UTZ5ETwnwI4S+oLueAt4Ipmq/Equd9SA2CqvT0BZgZXpZiffmSddyX4Cofzaumf2pcxD2gXIb2Cd9Qc4P7RGWSJWjmX28g7WOLLuo1DiUAD6FyoAxwus2mbdgGIoYL4XntDKMYuoH9KiqNLj1axMMd00AeRO5fqY/bsDtjZ3MRDAn5BlbEnzDAGwlaOalRliqBIgK8tkFls7rZ7QNUBBvzjtS7X0BtPFWgZg70LHAAAAAElFTkSuQmCC"
    },
    {
      "position": 8,
      "title": "PEACHTREE ROOFING & EXERIORS - Updated March 2025",
      "link": "https://www.yelp.com/biz/peachtree-roofing-and-exeriors-roswell",
      "source": "Yelp",
      "domain": "www.yelp.com",
      "displayed_link": "https://www.yelp.com › ... › Home Services › Roofing",
      "snippet": "In 2011, Michael sold American Roofing and Vinyl to his business partner and in 2012, M.W. Michael founded Peachtree Roofing & Exteriors in Atlanta, Georgia.",
      "snippet_highlighted_words": [
        "M"
      ],
      "rich_snippet": {
        "detected_extensions": {
          "rating": 4.3,
          "reviews": 30
        },
        "extensions": [
          "4.3",
          "(30)"
        ]
      },
      "favicon": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAGe0lEQVR4AZWUA7AkSReFv5tVz4N4a1uxtm3btve3bdu2bdvG7o6x1uiNp7sr896tjIyujNfjE3HilvKck7hVsoGw2982GTdwLmX/SRTlgZTFTjg3CoDqGN4/Qqj+W9ffou0fySdetoQNwHoD2PVv2QOxlxPkSrBBTMECBMAMADRsimlNDkbtFtStshve/HWCvk2+9OoZrANurcbnvW7YrnrtuwnVFOBGNJmj0TzkGqman5lC0KE4BtMHo0bU2qgAdsmLd6e//Q+CvQCsTLO2xiib+8T0LIcxS0GwMmpErai5QQHsvOcdbN7+guo+NUGTcWIAX2GdFlYqVtRst6CqwHeDaGYeu0/UjNrrDGCnPWd3C/ZzTDczU4gMkQbBo5uOYBcdjbzqOuQ1N9a8Hjv/8BgoB2hWwyAkDauJ6mZRO3qsMYAdcvswhO8SbDPU0kDNS6ubT8C9/Hrk7GNhp21gk0k1J+NOPowQ2uk79Ykhb5XVzFtom4H/bvLqCcAke6MFn5Y9JBIF0qzQ0REYnQxOGIeyHH8Wsjm5Zk0Luk/0Ghegdcy1e1rQ54w/5UpimoX+bzo2tqbWNljVBq9QRabxFpnMe7okxHfPsWOv36MJ0BfkZYRQdg3zKnTDeMog+K/8CHrRiua+oYUqcs3dod2qpXp7OYCzQy6b7EyvIJ/ePMjnMGKC/fQv6GNPARm2ogWqmK8wrUB7tsPHms2znl5p0Ruzc039UDrx2bwRqQJJJFBS4j/+jZ4AKxHVxlgxuOp0uPlctDCyVj4Paav9YKi9HeZPSi88aE6bmETxkQEJhvz1QcJ/p9KgDtCdqaK4512FXH46cuFJyO0XYT51SNbOXkXt7Sz4g9IDn0P4JJhSV+CrJkTp+vAf+jKoAmDLVqQuMZ/MjzsYCgfO4U4/Gt1xS/BJkxDIXpF6oBMNO6KB/KJKVRUrBe6+HLvlfGyfHTBLh6uY/ST+R78FwB57GiMgz70SOeGwZN7FQD9y+D5ZW9P47r1ptVNpwY8CgJGKkRiwYw/FXXwqIgKXnAZPzUN/+w/kj//Fv+tzhN/9Hf47g/La83CnHEUyz7BFSwj/fhCXJgR5a1OtvUvUA8k0ofsXFNh1+yw6NAC7bI/baVu4/Czkx7/DPvA1BLCJI1AW6NPzCf+dQjwj9v9pyKxH6ZM+EEmGls9AN0QpGsYM2xSsMccVgGAO6IVzMHEYdt4GQoW4Ev+OT9P+6Jdwi5ZSlH21aYEAEs3NSOaB3hUQ1bES9Q+D2zQvf+pVcQ6bOmNcu4X/TSHOUOsZyqxH6N9sFJu3iKLenr7TjsHiufj5n5COJ2+lJvOQQyQPj2l4RGznQz8F5S3mCihqigOXqrdAOHAvojmzH6OQgqLox+rtKN77KmTXHaiuewHujqsoLj4DOhXUwfQz34Tf/BUJmg2zefNPEPynxbY78BqK4ku4EhOXQqQAgAMREuNzh2Hwwltx110ICNXVz0HbLQa+/fH4HgBaHex/09B3fxz34AxAQa1ZCbHujytc6+gvfkSoWoQOoumnQ9Uht2NuT3wbO+4Q3JXnZrP2Korpc/A/+iUNBvuRIw6g+PCb0BLSz6wD3iePEPX9qujtZO6/l6Dha4RkItoNUsVBqYbUw7rpJIpX3hf7mwSDlXUAjPCeT0CnQwMBnTcPW7Ec8VE3mkfjpBc9o7cDQMJbCd53X+YgdQ0piFVt5MV3wdab08AMli+H4Ckfe5LqC9/Ir8YWUz3n5RQaIBt3q4fq7QAlgDwxfaZtsdsHMPcCNKQzoA5EQQSpqWa4g/YGERqowbIlSFXhiKvwUcLee2CdDv5Vb6H/kScRANNEDd2f3Afk6dkzABxdlCtfTfBTcsrInNxpoHPTPYS//oMu7Ol5yNgYxPNTs2/ZSvSym+Ca2xl4+DGc+qyROSV6kYCQgU3abndK9xec2wxxIEXuAlIHeFPCtlshe+wK02fTP28hIgIGmAGJmJHZ7X1dgNejZenjs3oCZNjkHQ/G+Z8jKUQkkGoTRjBIxgDGGoy15z4sQMszZMkj/yEDYQ2wSZvvDuV3EdknGycCufbCrKmJSqo2BfxFsnT+LHogrAXGNsNM8m/EeA4iZV4JWctQy4XG3CN8gKXlq4UnV7IGCOuBTdxsT9ReClyJyND6A1hkC/gaTt4qyxbMZB0QNhDG6GQGORdnJwEHATsCoySMAQ8D/0Plt7T4kTC2hA3AsxNdOd2lU6M9AAAAAElFTkSuQmCC"
    },
    {
      "position": 9,
      "title": "Peachtree Roofing & Exteriors | Atlanta, GA Roof Company",
      "link": "https://www.peachtreerestorations.com/",
      "source": "Peachtree Restorations",
      "domain": "www.peachtreerestorations.com",
      "displayed_link": "https://www.peachtreerestorations.com",
      "snippet": "We opened our doors in 2012 and have proven to our customers that we'll always provide top-tier workmanship, high-quality products, and dependable customer ...",
      "sitelinks": {
        "inline": [
          {
            "title": "Atlanta, GA Roof Materials",
            "link": "https://www.peachtreerestorations.com/roofing/materials/"
          },
          {
            "title": "Atlanta, GA Gutter Guard...",
            "link": "https://www.peachtreerestorations.com/gutters/guards/"
          },
          {
            "title": "Roofing",
            "link": "https://www.peachtreerestorations.com/roofing/"
          },
          {
            "title": "Gutters",
            "link": "https://www.peachtreerestorations.com/gutters/"
          }
        ]
      },
      "favicon": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABwAAAAcCAMAAABF0y+mAAAAnFBMVEVHcEyNyEuQxEntXjDyWi7xWi/wWS3oYzCnr0TxWS+IzUz0VS2Qxkv0VC6LyUvxWS71Ui30VS3qXTCHzEz0VS2QxkrwWS/fbjGOyUrxWi6QxkuNykzvWi+G0E582lDyWC/xYC73kiH2iCT1gyeQxkvxUCTzajH4mh/zciv8Siv0din2nm30eyr6uXqQxUv6y5bze1P1j1R24FGSxErVAG5yAAAAH3RSTlMAkRjRNdudBQmjXtDG8HRtHVRCOoStjhdKLd38xOfcsS6FZAAAAOxJREFUKJG101dPwzAQAGAPwG727AS8nThNU8b//28kUiUkLjyA1Huy/Mnnu7OM0C04R78GT5I9uS0JwNbaJJq3eY0xSBJZa6cWEXy0mP1Ekthja/d4slMNb41OnxnOspcTzLro60e9I1kEjZUFqmgIIS53sJVn2qRBSClC/ABOPgnhZD/0Xoq4WEE/Gm1ML8UWoHu7GK2UNl4IiOeLVl2n9CD/jFejOqVMv5ZWXs9GaT1KQWG1zr8PZhzmeiqAKXVO+rnNNAdD2NCqScUccQ5ejG0eD+yQb5uyALbgMlIG5RvX407I/5927Tt8AYMlF9w0EpZLAAAAAElFTkSuQmCC"
    }
  ],
  "inline_images": {
    "images": [
      {
        "title": "PEACHTREE ROOFING & EXERIORS - Updated March 2025 - 39 ...",
        "source": {
          "name": "Yelp",
          "link": "https://m.yelp.com/biz/peachtree-roofing-and-exeriors-roswell"
        },
        "original": {
          "link": "https://s3-media0.fl.yelpcdn.com/bphoto/UbAZcPeNpPnptlAkees5LA/l.jpg",
          "height": 400,
          "width": 300,
          "size": "29KB"
        },
        "thumbnail": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTkKin2rmdxkiIuqFCL9b7wfEOJd0wROjSoEmzYqrKVlnjia1XiaqlpYLo&s"
      },
      {
        "title": "Scott Chrismer - Realtor - Chrismer Realty Group | LinkedIn",
        "source": {
          "name": "LinkedIn",
          "link": "https://www.linkedin.com/in/scott-chrismer-1083002a"
        },
        "original": {
          "link": "https://media.licdn.com/dms/image/v2/D4E03AQEH5Wtxf4mfmA/profile-displayphoto-shrink_200_200/profile-displayphoto-shrink_200_200/0/1718664950376?e=2147483647&v=beta&t=kABw3QjQ9goNdhnDD5LjqUve3CYcpkRS2o-b_9VwMo8",
          "height": 200,
          "width": 200,
          "size": "12KB"
        },
        "thumbnail": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQ4ysSFSileVxxtBplL_vWSwXNRUZnwVuWVFWD2duNKBTbY6b4fKll5VP8&s"
      },
      {
        "title": "Peachtree Roofing & Exteriors",
        "source": {
          "name": "www.peachtreerestorations.com",
          "link": "https://www.peachtreerestorations.com/"
        },
        "original": {
          "link": "https://cmsplatform.blob.core.windows.net/wwwpeachtreerestorationscom/gallery/original/ef633533-931d-4e49-bcb4-8b79d1a024df.jpg", 
          "height": 674,
          "width": 1000,
          "size": "289KB"
        },
        "thumbnail": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRN4GHKFruVZe39YhMhPv6KSl9FGpagVVZcschWdhF1Zr62uMVl-DMRvm0&s"
      }
    ]
  },
  "pagination": {
    "current": 1,
    "next": "https://www.google.com/search?q=owner+of+peachtree+roofing+in+atlanta+ga&oq=owner+of+peachtree+roofing+in+atlanta+ga&gl=us&hl=en&start=10&ie=UTF-8"
  }
}