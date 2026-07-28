# app/collectors/producthunt_collector.py

import os
import requests

from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()


class ProductHuntCollector:

    def get_token(self):

        response = requests.post(
            "https://api.producthunt.com/v2/oauth/token",
            json={
                "client_id": os.getenv(
                    "PRODUCTHUNT_CLIENT_ID"
                ),
                "client_secret": os.getenv(
                    "PRODUCTHUNT_CLIENT_SECRET"
                ),
                "grant_type": "client_credentials"
            }
        )

        response.raise_for_status()

        return response.json()[
            "access_token"
        ]

    async def collect(
        self,
        topic: str
    ):

        try:

            token = self.get_token()

            query = """
            {
              posts(first: 50) {
                edges {
                  node {
                    name
                    tagline
                    votesCount
                    commentsCount
                    createdAt
                    url

                    topics {
                      edges {
                        node {
                          name
                        }
                      }
                    }
                  }
                }
              }
            }
            """

            response = requests.post(
                "https://api.producthunt.com/v2/api/graphql",
                json={
                    "query": query
                },
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
            )

            response.raise_for_status()

            data = response.json()

            results = []

            posts = (
                data["data"]
                ["posts"]
                ["edges"]
            )

            for post in posts:

                node = post["node"]

                topics = [
                    topic_node["node"]["name"]
                    for topic_node
                    in node["topics"]["edges"]
                ]

                launch_date = node["createdAt"]

                launch_dt = datetime.fromisoformat(
                    launch_date.replace(
                        "Z",
                        "+00:00"
                    )
                )

                age_days = max(
                    1,
                    (
                        datetime.now(timezone.utc)
                        -
                        launch_dt
                    ).days
                )

                votes = node["votesCount"]
                comments = node["commentsCount"]

                votes_per_day = round(
                    votes / age_days,
                    2
                )

                comments_per_day = round(
                    comments / age_days,
                    2
                )

                results.append(
                    {
                        "source":
                        "producthunt",

                        "title":
                        node["name"],

                        "url":
                        node["url"],

                        "snippet":
                        node["tagline"],

                        "votes":
                        votes,

                        "comments":
                        comments,

                        "launch_date":
                        launch_date,

                        "age_days":
                        age_days,

                        "votes_per_day":
                        votes_per_day,

                        "comments_per_day":
                        comments_per_day,

                        "topics":
                        topics
                    }
                )

            print(
                f"PRODUCT HUNT RESULTS: {len(results)}"
            )

            return results

        except Exception as e:

            print(
                "PRODUCT HUNT ERROR:",
                e
            )

            return []