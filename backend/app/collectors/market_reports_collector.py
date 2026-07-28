from ddgs import DDGS


class MarketReportsCollector:

    async def collect(
        self,
        topic: str
    ):

        try:

            searches = [

                f"{topic} market size",

                f"{topic} market growth",

                f"{topic} market forecast",

                f"{topic} CAGR",

                f"{topic} industry report",

                f"{topic} market trends"
            ]

            results = []

            with DDGS() as ddgs:

                for query in searches:

                    search_results = list(
                        ddgs.text(
                            query,
                            max_results=10
                        )
                    )

                    for item in search_results:

                        results.append(
                            {
                                "source":
                                "market_report",

                                "title":
                                item.get(
                                    "title",
                                    ""
                                ),

                                "url":
                                item.get(
                                    "href",
                                    ""
                                ),

                                "snippet":
                                item.get(
                                    "body",
                                    ""
                                ),

                                "query":
                                query
                            }
                        )

            print(
                f"MARKET REPORT RESULTS: {len(results)}"
            )

            return results

        except Exception as e:

            print(
                "MARKET REPORT ERROR:",
                e
            )

            return []