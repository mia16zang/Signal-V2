from googleapiclient.discovery import build
from dotenv import load_dotenv
from datetime import datetime, timezone
import os

print("LOADING:", __file__)


load_dotenv()


class YouTubeCollector:

    async def collect(
        self,
        topic: str
    ):

        try:

            youtube = build(
                "youtube",
                "v3",
                developerKey=os.getenv(
                    "YOUTUBE_API_KEY"
                )
            )

            search_request = youtube.search().list(
                q=topic,
                part="snippet",
                maxResults=10,
                type="video",
                order="relevance"
            )

            search_response = search_request.execute()

            video_ids = []

            for item in search_response["items"]:

                video_ids.append(
                    item["id"]["videoId"]
                )

            if not video_ids:
                return []

            videos_request = youtube.videos().list(
                part="snippet,statistics",
                id=",".join(video_ids)
            )

            videos_response = (
                videos_request.execute()
            )

            results = []

            for video in videos_response["items"]:

                stats = video.get(
                    "statistics",
                    {}
                )

                snippet = video.get(
                    "snippet",
                    {}
                )

            

                results.append(
                    {
                        "source":
                        "youtube",

                        "title":
                        snippet.get(
                            "title",
                            ""
                        ),

                        "url":
                        f"https://youtube.com/watch?v={video['id']}",

                        "snippet":
                        snippet.get(
                            "description",
                            ""
                        )[:500],

                        "channel":
                        snippet.get(
                            "channelTitle",
                            ""
                        ),

                        "published":
                        snippet.get(
                            "publishedAt",
                            ""
                        ),

                        "views":
                        int(
                            stats.get(
                                "viewCount",
                                0
                            )
                        ),

                        "likes":
                        int(
                            stats.get(
                                "likeCount",
                                0
                            )
                        ),

                        "comments":
                        int(
                            stats.get(
                                "commentCount",
                                0
                            )
                        )
                    }
                )

            return results

        except Exception as e:

            print(
                "YOUTUBE ERROR:",
                e
            )

            return []
        

